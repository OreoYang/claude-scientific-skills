/**
 * Official mermaid.js SVG via mermaid.ink (same engine as mermaid.live).
 * No beautiful-mermaid, no Puppeteer, no local mermaid-cli.
 */

export const OFFICIAL_THEMES = ['default', 'dark', 'forest', 'neutral', 'base'];

export const THEME_ALIAS = {
  'github-light': 'default',
  'zinc-light': 'default',
  'solarized-light': 'default',
  'tokyo-night-light': 'default',
  'nord-light': 'default',
  'catppuccin-latte': 'default',
  'cappuccin-latte': 'default',
  'github-dark': 'dark',
  'tokyo-night': 'dark',
  'tokyo-night-storm': 'dark',
  'dracula': 'dark',
  'nord': 'dark',
  'one-dark': 'dark',
  'zinc-dark': 'dark',
  'solarized-dark': 'dark',
  'catppuccin-mocha': 'dark',
  'cappuccin-mocha': 'dark',
};

const DEFAULT_INK = process.env.MERMAID_INK_URL || 'https://mermaid.ink';
const KROKI_URL = process.env.KROKI_URL || 'https://kroki.io/mermaid/svg';
const USER_AGENT = 'pretty-mermaid/2.0 (official mermaid.js via mermaid.ink)';

export function resolveTheme(name) {
  if (!name) return 'default';
  const key = String(name).trim().toLowerCase();
  if (OFFICIAL_THEMES.includes(key)) return key;
  return THEME_ALIAS[key] || 'default';
}

export function injectTheme(mmd, theme) {
  if (/%%\{\s*init/i.test(mmd)) return mmd;
  const official = resolveTheme(theme);
  return `%%{init: {"theme": "${official}"}}%%\n${mmd}`;
}

export function encodeDiagram(mmd) {
  return Buffer.from(mmd, 'utf8').toString('base64url');
}

function fixSvgExplicitSize(svg) {
  const m = svg.match(/\bviewBox="([^"]+)"/i);
  if (!m) return svg;
  const parts = m[1].trim().split(/[\s,]+/);
  if (parts.length !== 4) return svg;
  const w = parts[2];
  const h = parts[3];
  return svg
    .replace(/\bwidth="100%"/i, `width="${w}"`)
    .replace(/\bheight="100%"/i, `height="${h}"`);
}

async function fetchText(url, { method = 'GET', body, headers = {} } = {}) {
  const resp = await fetch(url, {
    method,
    body,
    headers: { 'User-Agent': USER_AGENT, ...headers },
  });
  const text = await resp.text();
  if (!resp.ok) {
    const snippet = text.replace(/\s+/g, ' ').slice(0, 240);
    throw new Error(`HTTP ${resp.status} ${url.slice(0, 80)}… ${snippet}`);
  }
  return text;
}

export async function renderOfficialSvg(mmdText, { theme = 'default', transparent = false } = {}) {
  const mmd = injectTheme(mmdText.trim() + '\n', theme);
  const ink = DEFAULT_INK.replace(/\/$/, '');
  const qs = transparent ? '?bgColor=transparent' : '';
  const errors = [];

  const simpleUrl = `${ink}/svg/${encodeDiagram(mmd)}${qs}`;
  try {
    const svg = await fetchText(simpleUrl);
    if (!/<svg/i.test(svg)) throw new Error('response is not SVG');
    return fixSvgExplicitSize(svg);
  } catch (e) {
    errors.push(`mermaid.ink base64: ${e.message}`);
  }

  try {
    const { deflateSync } = await import('node:zlib');
    const state = JSON.stringify({
      code: mmdText.trim() + '\n',
      mermaid: { theme: resolveTheme(theme) },
    });
    const raw = deflateSync(Buffer.from(state, 'utf8'), { level: 9 }).subarray(2, -4);
    const pakoUrl = `${ink}/svg/pako:${raw.toString('base64url')}${qs}`;
    const svg = await fetchText(pakoUrl);
    if (!/<svg/i.test(svg)) throw new Error('response is not SVG');
    return fixSvgExplicitSize(svg);
  } catch (e) {
    errors.push(`mermaid.ink pako: ${e.message}`);
  }

  try {
    const svg = await fetchText(KROKI_URL, {
      method: 'POST',
      body: mmd,
      headers: {
        'Content-Type': 'text/plain',
        Accept: 'image/svg+xml',
      },
    });
    if (!/<svg/i.test(svg)) throw new Error('response is not SVG');
    return fixSvgExplicitSize(svg);
  } catch (e) {
    errors.push(`kroki: ${e.message}`);
  }

  throw new Error(`Official Mermaid render failed:\n  - ${errors.join('\n  - ')}`);
}
