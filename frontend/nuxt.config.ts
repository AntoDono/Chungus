export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  ssr: false,
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@nuxt/icon', '@nuxtjs/color-mode'],
  icon: {
    clientBundle: {
      scan: true,
    },
  },
  css: ['~/assets/css/main.css'],
  colorMode: {
    classSuffix: '',
    preference: 'dark',
    fallback: 'dark',
    storageKey: 'chungus-color-mode-v2',
  },
  app: {
    head: {
      title: 'CHUNGUS',
      htmlAttrs: { lang: 'en' },
      meta: [
        {
          name: 'description',
          content:
            'Computing Hybrid Utilization Network for GPU Unified Scheduling — atelier console for inference, keys, and usage.',
        },
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650;9..144,720&family=IBM+Plex+Mono:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap',
        },
      ],
    },
  },
  nitro: {
    preset: 'static',
  },
  devServer: {
    port: 3001,
  },
})
