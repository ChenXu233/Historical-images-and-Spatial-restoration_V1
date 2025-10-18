// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  modules: ['@element-plus/nuxt'],
  postcss: {
    plugins: {
      '@tailwindcss/postcss': {},
      autoprefixer: {},
    },
  },
  css: ['~/assets/css/tailwind.css'],
  vite: {
    build: {
      rollupOptions: {
        external: [], // 确保 dayjs 不被 externalize
      },
    },
    optimizeDeps: {
      include: ['dayjs', 'element-plus']
    }
  },
})