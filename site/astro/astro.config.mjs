// @ts-check
import { defineConfig } from 'astro/config';

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
});
