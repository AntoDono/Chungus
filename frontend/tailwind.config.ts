import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: [
    './app/**/*.{vue,js,ts}',
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.{vue,js,ts}',
    './pages/**/*.{vue,js,ts}',
    './plugins/**/*.{js,ts}',
    './nuxt.config.ts',
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: '#f3ece1',
          muted: '#e8dfd2',
          rule: '#d9cfc0',
          ink: '#1c1814',
          faint: '#6f675c',
        },
        night: {
          DEFAULT: '#141210',
          muted: '#1e1b18',
          rule: '#2e2923',
          ink: '#efe6d8',
          faint: '#9a9083',
        },
        oxide: {
          DEFAULT: '#2d6a4f',
          deep: '#1b4332',
          glow: '#52b788',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'Menlo', 'monospace'],
      },
      letterSpacing: {
        ledger: '0.18em',
      },
    },
  },
} satisfies Config
