import ja from '../i18n/ja.json';
import en from '../i18n/en.json';
import zh from '../i18n/zh.json';

export type Lang = 'ja' | 'en' | 'zh';
export const LANGS: Lang[] = ['ja', 'en', 'zh'];
export const DEFAULT_LANG: Lang = 'ja';

const dicts: Record<Lang, Record<string, string>> = { ja, en, zh };

/** Translate a key. Falls back to ja, then to the key itself. */
export function t(lang: Lang, key: string): string {
  return dicts[lang]?.[key] ?? dicts.ja[key] ?? key;
}

/** Build a locale-aware internal path (respects Astro `base`). */
export function localePath(lang: Lang, path: string = ''): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const clean = path.replace(/^\//, '');
  return `${base}/${lang}/${clean}`.replace(/\/+$/, '/') || '/';
}

/** Extract locale from URL pathname. */
export function getLangFromPath(pathname: string): Lang {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const stripped = pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
  const seg = stripped.split('/').filter(Boolean)[0] as Lang | undefined;
  return LANGS.includes(seg as Lang) ? (seg as Lang) : DEFAULT_LANG;
}
