// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://nanahira.dinlon5566.com',
  base: '/',
  output: 'static',
  trailingSlash: 'always',
  devToolbar: { enabled: false },
  i18n: {
    defaultLocale: 'ja',
    locales: ['ja', 'en', 'zh'],
    routing: {
      prefixDefaultLocale: true,
      redirectToDefaultLocale: false,
    },
  },
  integrations: [
    sitemap({
      i18n: {
        defaultLocale: 'ja',
        locales: {
          ja: 'ja-JP',
          en: 'en-US',
          zh: 'zh-Hant',
        },
      },
      // root `/` is a noindex JS-redirect shim — exclude from sitemap
      filter: (page) => page !== 'https://nanahira.dinlon5566.com/',
    }),
  ],
});
