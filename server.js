'use strict'

const fs = require('fs')
const http = require('http')
const path = require('path')
const { spawn } = require('child_process')
const httpProxy = require('http-proxy')

const ROOT = __dirname
const BACKEND = path.join(ROOT, 'backend')
const STATIC_DIR = path.join(ROOT, 'frontend', '.output', 'public')

const PUBLIC_PORT = Number(process.env.PORT || 3000)
const DJANGO_HOST = process.env.DJANGO_HOST || '127.0.0.1'
const DJANGO_PORT = Number(process.env.DJANGO_PORT || 8000)
const NUXT_DEV = process.env.NUXT_DEV === '1'
const NUXT_PORT = Number(process.env.NUXT_PORT || 3001)
const HEALTH_TIMEOUT_MS = Number(process.env.DJANGO_HEALTH_TIMEOUT_MS || 60_000)

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json',
}

let djangoChild = null
let shuttingDown = false

function djangoOrigin() {
  return `http://${DJANGO_HOST}:${DJANGO_PORT}`
}

function nuxtOrigin() {
  return `http://127.0.0.1:${NUXT_PORT}`
}

function pathnameOf(req) {
  const host = req.headers.host || `127.0.0.1:${PUBLIC_PORT}`
  try {
    return new URL(req.url || '/', `http://${host}`).pathname
  } catch {
    return '/'
  }
}

function isDjangoPath(pathname) {
  return (
    pathname === '/v1' ||
    pathname.startsWith('/v1/') ||
    pathname === '/api/v1' ||
    pathname.startsWith('/api/v1/') ||
    pathname === '/internal' ||
    pathname.startsWith('/internal/') ||
    pathname === '/admin' ||
    pathname.startsWith('/admin/')
  )
}

function rewriteDjangoUrl(reqUrl) {
  const qIndex = reqUrl.indexOf('?')
  const pathname = qIndex === -1 ? reqUrl : reqUrl.slice(0, qIndex)
  const search = qIndex === -1 ? '' : reqUrl.slice(qIndex)
  if (pathname === '/api/v1') return `/v1${search}`
  if (pathname.startsWith('/api/v1/')) return `/v1/${pathname.slice('/api/v1/'.length)}${search}`
  return reqUrl
}

function spawnDjango() {
  const bind = `${DJANGO_HOST}:${DJANGO_PORT}`
  const isProd = process.env.NODE_ENV === 'production' || process.env.DJANGO_SERVER === 'gunicorn'
  const env = { ...process.env }
  const opts = { cwd: BACKEND, stdio: 'inherit', env, detached: false }

  if (process.env.DJANGO_CMD) {
    return spawn(process.env.DJANGO_CMD, { ...opts, shell: true })
  }

  const venvPython = path.join(BACKEND, 'venv', 'bin', 'python')
  const venvPoetry = path.join(BACKEND, 'venv', 'bin', 'poetry')
  const venvGunicorn = path.join(BACKEND, 'venv', 'bin', 'gunicorn')

  if (isProd) {
    if (fs.existsSync(venvGunicorn)) {
      return spawn(venvGunicorn, ['Chungus.wsgi:application', '--bind', bind], opts)
    }
    if (fs.existsSync(venvPoetry)) {
      return spawn(venvPoetry, ['run', 'gunicorn', 'Chungus.wsgi:application', '--bind', bind], opts)
    }
    return spawn('poetry', ['run', 'gunicorn', 'Chungus.wsgi:application', '--bind', bind], opts)
  }

  // Prefer backend venv (poetry often not on global PATH)
  if (process.env.USE_VENV !== '0' && fs.existsSync(venvPython)) {
    return spawn(venvPython, ['manage.py', 'runserver', bind], opts)
  }
  if (fs.existsSync(venvPoetry)) {
    return spawn(venvPoetry, ['run', 'python', 'manage.py', 'runserver', bind], opts)
  }

  return spawn('poetry', ['run', 'python', 'manage.py', 'runserver', bind], opts)
}

async function waitForDjango() {
  const started = Date.now()
  const url = `${djangoOrigin()}/internal/health`
  while (Date.now() - started < HEALTH_TIMEOUT_MS) {
    try {
      const res = await fetch(url)
      if (res.ok) {
        const body = await res.json().catch(() => null)
        if (!body || body.status === 'ok') return
      }
    } catch {
      // still booting
    }
    await new Promise((resolve) => setTimeout(resolve, 400))
  }
  throw new Error(`Django did not become healthy at ${url} within ${HEALTH_TIMEOUT_MS}ms`)
}

function safeJoin(root, urlPath) {
  const decoded = decodeURIComponent(urlPath.split('?')[0])
  const rel = decoded.replace(/^\/+/, '')
  const resolved = path.normalize(path.join(root, rel))
  if (!resolved.startsWith(root)) return null
  return resolved
}

function sendFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase()
  const type = MIME[ext] || 'application/octet-stream'
  const stream = fs.createReadStream(filePath)
  res.writeHead(200, { 'Content-Type': type })
  stream.pipe(res)
  stream.on('error', () => {
    if (!res.headersSent) res.writeHead(500)
    res.end('Internal Server Error')
  })
}

function serveNuxtStatic(req, res) {
  const pathname = pathnameOf(req)
  const candidates = []
  const direct = safeJoin(STATIC_DIR, pathname)
  if (direct) {
    candidates.push(direct)
    if (pathname.endsWith('/')) candidates.push(path.join(direct, 'index.html'))
    else candidates.push(`${direct}.html`)
  }
  candidates.push(path.join(STATIC_DIR, '200.html'))
  candidates.push(path.join(STATIC_DIR, 'index.html'))

  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
        sendFile(res, candidate)
        return
      }
    } catch {
      // try next
    }
  }

  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
  res.end('Not Found')
}

const proxy = httpProxy.createProxyServer({
  ws: true,
  xfwd: true,
  changeOrigin: true,
  proxyTimeout: 0,
  timeout: 0,
})

proxy.on('error', (err, req, res) => {
  console.error('[gateway] proxy error:', err.message)
  if (res && typeof res.writeHead === 'function' && !res.headersSent) {
    res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' })
    res.end('Bad Gateway')
  } else if (res && res.socket) {
    res.socket.end()
  }
})

function proxyToDjango(req, res) {
  req.url = rewriteDjangoUrl(req.url || '/')
  proxy.web(req, res, { target: djangoOrigin() })
}

function proxyToNuxt(req, res) {
  proxy.web(req, res, { target: nuxtOrigin() })
}

function shutdown(signal) {
  if (shuttingDown) return
  shuttingDown = true
  console.log(`[gateway] ${signal} — stopping Django`)
  if (djangoChild && djangoChild.pid && !djangoChild.killed) {
    try {
      djangoChild.kill('SIGTERM')
    } catch {
      // already gone
    }
    setTimeout(() => {
      if (djangoChild && !djangoChild.killed) {
        try {
          djangoChild.kill('SIGKILL')
        } catch {
          // ignore
        }
      }
      process.exit(0)
    }, 3000)
  } else {
    process.exit(0)
  }
}

async function main() {
  djangoChild = spawnDjango()
  djangoChild.on('error', (err) => {
    console.error('[gateway] failed to start Django:', err.message)
    if (err.code === 'ENOENT') {
      console.error(
        '[gateway] install backend deps: cd backend && python3 -m venv venv && ./venv/bin/pip install -e .',
      )
      console.error('[gateway] or set DJANGO_CMD to your runserver command')
    }
    process.exit(1)
  })
  djangoChild.on('exit', (code, signal) => {
    djangoChild = null
    if (shuttingDown) {
      process.exit(code || 0)
      return
    }
    console.error(`[gateway] Django exited (${signal || code})`)
    process.exit(code || 1)
  })

  console.log(`[gateway] waiting for Django at ${djangoOrigin()}/internal/health`)
  await waitForDjango()
  console.log('[gateway] Django is healthy')

  const server = http.createServer((req, res) => {
    const pathname = pathnameOf(req)
    if (isDjangoPath(pathname)) {
      proxyToDjango(req, res)
      return
    }
    if (NUXT_DEV) {
      proxyToNuxt(req, res)
      return
    }
    serveNuxtStatic(req, res)
  })

  server.on('upgrade', (req, socket, head) => {
    const pathname = pathnameOf(req)
    if (isDjangoPath(pathname)) {
      req.url = rewriteDjangoUrl(req.url || '/')
      proxy.ws(req, socket, head, { target: djangoOrigin() })
      return
    }
    if (NUXT_DEV) {
      proxy.ws(req, socket, head, { target: nuxtOrigin() })
      return
    }
    socket.destroy()
  })

  server.listen(PUBLIC_PORT, '0.0.0.0', () => {
    const mode = NUXT_DEV ? `Nuxt dev → :${NUXT_PORT}` : `static ${path.relative(ROOT, STATIC_DIR)}`
    console.log(`[gateway] listening on http://0.0.0.0:${PUBLIC_PORT} (${mode})`)
  })
}

process.on('SIGINT', () => shutdown('SIGINT'))
process.on('SIGTERM', () => shutdown('SIGTERM'))

main().catch((err) => {
  console.error('[gateway]', err)
  shutdown('ERROR')
})
