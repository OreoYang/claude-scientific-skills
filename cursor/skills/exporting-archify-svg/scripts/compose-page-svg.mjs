#!/usr/bin/env node
/**
 * Turn a delivered Archify HTML into viewer-matching SVGs.
 * Replicates Archify serializeSvg() CSS injection, then optionally wraps
 * title + diagram + info cards into one page SVG for wiki attachments.
 *
 *   node compose-page-svg.mjs <delivered.html> [--out-dir DIR] [--stem NAME]
 *     [--theme light|dark] [--preset classic|signal-flow|blueprint|editorial]
 *     [--diagram-only]
 */
import fs from 'node:fs';
import path from 'node:path';

const FONT =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', 'Liberation Mono', 'Noto Sans Mono CJK SC', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', monospace";
const KEEP_SEL = /(^|,)\s*(svg|:root|\[data-theme|\[data-preset|\.c-|\.t-|\.a-|\.m-)/;
const DOT_FILL = {
  cyan: '#0891b2',
  emerald: '#059669',
  amber: '#d97706',
  rose: '#e11d48',
  violet: '#7c3aed',
  orange: '#ea580c',
  slate: '#64748b',
};
const PAD = 32;
const TITLE_Y = 44;
const DIAGRAM_Y = 72;
const CARD_GAP = 16;
const CARD_TOP_GAP = 20;

function usage(msg) {
  if (msg) console.error(msg);
  console.error(`Usage: node compose-page-svg.mjs <delivered.html> [options]
  --out-dir DIR     default: same directory as the HTML
  --stem NAME       default: HTML basename without .html
  --theme light|dark                 default: light
  --preset classic|signal-flow|blueprint|editorial   default: classic
  --diagram-only    skip the title/cards page SVG`);
  process.exit(2);
}

function parseArgs(argv) {
  const args = { theme: 'light', preset: 'classic', diagramOnly: false };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--out-dir') args.outDir = argv[++i];
    else if (a === '--stem') args.stem = argv[++i];
    else if (a === '--theme') args.theme = argv[++i];
    else if (a === '--preset') args.preset = argv[++i];
    else if (a === '--diagram-only') args.diagramOnly = true;
    else if (a === '-h' || a === '--help') usage();
    else if (a.startsWith('-')) usage(`unknown option: ${a}`);
    else rest.push(a);
  }
  if (rest.length !== 1) usage('expected exactly one HTML path');
  args.htmlPath = path.resolve(rest[0]);
  if (!['light', 'dark'].includes(args.theme)) usage(`bad --theme ${args.theme}`);
  if (!['classic', 'signal-flow', 'blueprint', 'editorial'].includes(args.preset)) {
    usage(`bad --preset ${args.preset}`);
  }
  return args;
}

function stripComments(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, '');
}

function readBlock(css, braceIndex) {
  if (css[braceIndex] !== '{') throw new Error('expected {');
  let depth = 0;
  for (let i = braceIndex; i < css.length; i++) {
    const ch = css[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) return { block: css.slice(braceIndex, i + 1), end: i + 1 };
    }
  }
  throw new Error('unbalanced CSS brace');
}

function walkCss(css) {
  css = stripComments(css);
  const rules = [];
  let i = 0;
  while (i < css.length) {
    while (i < css.length && /\s/.test(css[i])) i++;
    if (i >= css.length) break;
    if (css[i] === '@') {
      const brace = css.indexOf('{', i);
      if (brace < 0) break;
      const header = css.slice(i, brace).trim();
      const { block, end } = readBlock(css, brace);
      if (/^@(-webkit-)?keyframes\s+archify-/i.test(header)) {
        rules.push({ kind: 'kf', text: `${header} ${block}` });
      }
      i = end;
      continue;
    }
    const brace = css.indexOf('{', i);
    if (brace < 0) break;
    const sel = css.slice(i, brace).trim();
    const { block, end } = readBlock(css, brace);
    rules.push({ kind: 'style', sel, compact: sel.replace(/\s+/g, ' '), text: `${sel} ${block}` });
    i = end;
  }
  return rules;
}

function hostStyleFrom(css) {
  return walkCss(css)
    .filter((rule) => (rule.kind === 'kf' ? true : KEEP_SEL.test(rule.sel)))
    .map((rule) => rule.text)
    .join('\n');
}

function parseDecls(block) {
  const body = block.replace(/^\s*\{/, '').replace(/\}\s*$/, '');
  const out = [];
  for (const part of body.split(';')) {
    const idx = part.indexOf(':');
    if (idx < 0) continue;
    const name = part.slice(0, idx).trim();
    const value = part.slice(idx + 1).trim();
    if (name.startsWith('--') && value) out.push([name, value]);
  }
  return out;
}

function declsFromRule(rule) {
  const brace = rule.text.indexOf('{');
  return parseDecls(rule.text.slice(brace));
}

function mergeDecls(base, overlay) {
  const map = new Map(base);
  for (const [k, v] of overlay) map.set(k, v);
  return [...map.entries()];
}

function themeDecls(css, theme, preset) {
  const rules = walkCss(css).filter((r) => r.kind === 'style');
  let base;
  if (theme === 'light') {
    base = rules.find((r) => /^\[data-theme=["']light["']\]$/.test(r.compact));
  } else {
    base = rules.find(
      (r) => /\[data-theme=["']dark["']\]/.test(r.compact) && !/data-preset/.test(r.compact),
    );
  }
  if (!base) throw new Error(`missing [data-theme="${theme}"] rule`);
  let decls = declsFromRule(base);
  if (preset && preset !== 'classic') {
    const overlay = rules.find((r) => {
      const a = `\\[data-preset=["']${preset}["']\\]`;
      const b = `\\[data-theme=["']${theme}["']\\]`;
      return new RegExp(`${a}\\s*${b}|${b}\\s*${a}`).test(r.compact);
    });
    if (overlay) decls = mergeDecls(decls, declsFromRule(overlay));
  }
  return decls;
}

function extractStyle(html) {
  const blocks = [...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]);
  if (!blocks.length) throw new Error('no <style> in HTML');
  return blocks.join('\n');
}

function extractDiagramSvg(html) {
  const marker = html.indexOf('class="diagram-container"');
  const from = marker >= 0 ? marker : 0;
  const start = html.indexOf('<svg', from);
  if (start < 0) throw new Error('diagram svg not found');
  let i = start;
  let depth = 0;
  while (i < html.length) {
    const nextOpen = html.indexOf('<svg', i);
    const nextClose = html.indexOf('</svg>', i);
    if (nextClose < 0) throw new Error('unclosed svg');
    if (nextOpen >= 0 && nextOpen < nextClose) {
      depth++;
      i = nextOpen + 4;
      continue;
    }
    depth--;
    i = nextClose + 6;
    if (depth === 0) return html.slice(start, i);
  }
  throw new Error('unclosed svg');
}

function viewBoxSize(svg) {
  const m = svg.match(/\bviewBox="0 0 ([0-9.]+) ([0-9.]+)"/);
  if (!m) throw new Error('diagram svg missing viewBox="0 0 W H"');
  return { width: Number(m[1]), height: Number(m[2]) };
}

function stripTags(s) {
  return s.replace(/<[^>]+>/g, '');
}

function decodeEntities(s) {
  return s
    .replace(/&bull;/g, '')
    .replace(/&#8226;/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractTitle(html, svg) {
  const h1 = html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i);
  if (h1) return decodeEntities(stripTags(h1[1]));
  const t = svg.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  if (t) return decodeEntities(stripTags(t[1]));
  return 'Architecture';
}

function extractCards(html) {
  const cards = [];
  const re = /<div class="card">([\s\S]*?)<ul>([\s\S]*?)<\/ul>/g;
  let m;
  while ((m = re.exec(html))) {
    const head = m[1];
    const list = m[2];
    const title = decodeEntities(stripTags((head.match(/<h3\b[^>]*>([\s\S]*?)<\/h3>/i) || [])[1] || 'Card'));
    const dot = (head.match(/card-dot\s+([a-z]+)/i) || [])[1] || 'cyan';
    const bullets = [...list.matchAll(/<li\b[^>]*>([\s\S]*?)<\/li>/gi)].map((x) =>
      decodeEntities(stripTags(x[1])).replace(/^[•·]\s*/, ''),
    );
    cards.push({ title, dot, bullets });
  }
  return cards;
}

function fontFallback() {
  return [400, 500, 600, 700]
    .map(
      (w) =>
        `@font-face { font-family: 'JetBrains Mono'; font-weight: ${w}; src: local('JetBrains Mono'), local('JetBrainsMono-Regular'); }`,
    )
    .join('\n');
}

function xmlEscape(s) {
  return s.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[ch]));
}

function wrapLine(text, maxChars) {
  const words = text.split(/\s+/);
  const lines = [];
  let cur = '';
  for (const word of words) {
    const next = cur ? `${cur} ${word}` : word;
    if (next.length > maxChars && cur) {
      lines.push(cur);
      cur = word;
    } else {
      cur = next;
    }
  }
  if (cur) lines.push(cur);
  return lines;
}

function serializeLocked({ innerSvg, hostStyle, decls, theme, preset, width, height }) {
  const vars = decls.map(([n, v]) => `${n}: ${v};`).join(' ');
  const bg = decls.find(([n]) => n === '--bg')?.[1] || (theme === 'light' ? '#f8fafc' : '#020617');
  const styleText = [
    fontFallback(),
    `svg { font-family: ${FONT}; }`,
    hostStyle,
    `:root, svg { ${vars} }`,
    `svg[data-theme="${theme}"] { ${vars} }`,
    'rect.c-bg-rect { fill: var(--bg); }',
  ].join('\n');

  let svg = innerSvg
    .replace(
      /^<svg\b/,
      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${width}" height="${height}"`,
    )
    .replace(/\sdata-theme="[^"]*"/g, '')
    .replace(/\sdata-preset="[^"]*"/g, '');

  svg = svg.replace(/^(<svg\b[^>]*)>/, `$1 data-theme="${theme}" data-preset="${preset}">`);

  const injected =
    `<style><![CDATA[\n${styleText}\n]]></style>\n` +
    `<rect class="c-bg-rect" width="100%" height="100%" fill="${xmlEscape(bg)}"/>\n`;
  const gt = svg.indexOf('>');
  return `${svg.slice(0, gt + 1)}\n${injected}${svg.slice(gt + 1)}`;
}

function cardEl(x, y, w, h, dot, title, bullets, maxChars) {
  const fill = DOT_FILL[dot] || DOT_FILL.cyan;
  const parts = [
    `<g>`,
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="#ffffff" stroke="#e2e8f0" stroke-width="1"/>`,
    `<circle cx="${x + 18}" cy="${y + 22}" r="5" fill="${fill}"/>`,
    `<text x="${x + 32}" y="${y + 27}" fill="#0f172a" font-size="14" font-weight="700" font-family="${FONT}">${xmlEscape(title)}</text>`,
  ];
  let ty = y + 52;
  for (const bullet of bullets) {
    for (const line of wrapLine(`• ${bullet}`, maxChars)) {
      parts.push(
        `<text x="${x + 16}" y="${ty}" fill="#334155" font-size="11" font-family="${FONT}">${xmlEscape(line)}</text>`,
      );
      ty += 16;
    }
    ty += 8;
  }
  parts.push(`</g>`);
  return parts.join('\n');
}

function cardHeight(bullets, maxChars) {
  let lines = 0;
  for (const b of bullets) lines += wrapLine(`• ${b}`, maxChars).length;
  return Math.max(120, 52 + lines * 16 + bullets.length * 8 + 16);
}

function composePage({ diagramSvg, title, cards, width, height, theme, preset, bg }) {
  const pageW = width + PAD * 2;
  const n = Math.max(cards.length, 1);
  const cardW = cards.length ? (width - CARD_GAP * (cards.length - 1)) / cards.length : width;
  const maxChars = Math.max(24, Math.floor(cardW / 7.2));
  const cardH = cards.length
    ? Math.max(...cards.map((c) => cardHeight(c.bullets, maxChars)))
    : 0;
  const cardsY = DIAGRAM_Y + height + CARD_TOP_GAP;
  const pageH = cards.length ? cardsY + cardH + PAD : DIAGRAM_Y + height + PAD;

  const nested = diagramSvg.replace(/^<svg([^>]*)>/, (_, attrs) => {
    const cleaned = attrs.replace(/\s(x|y|width|height)="[^"]*"/g, '');
    return `<svg x="${PAD}" y="${DIAGRAM_Y}" width="${width}" height="${height}"${cleaned}>`;
  });

  const cardSvg = cards
    .map((c, i) =>
      cardEl(PAD + i * (cardW + CARD_GAP), cardsY, cardW, cardH, c.dot, c.title, c.bullets, maxChars),
    )
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 ${pageW} ${pageH}" width="${pageW}" height="${pageH}"
     data-theme="${theme}" data-preset="${preset}" role="img">
  <title>${xmlEscape(title)}</title>
  <desc>Full-page Archify export locked to ${theme} + ${preset}: title, diagram (serializeSvg stylesheet), and info cards. Toolbar omitted.</desc>
  <rect width="100%" height="100%" fill="${xmlEscape(bg)}"/>
  <text x="${PAD}" y="${TITLE_Y}" fill="${theme === 'light' ? '#0f172a' : '#f8fafc'}" font-size="22" font-weight="700" font-family="${FONT}">${xmlEscape(title)}</text>
${nested}
${cardSvg}
</svg>
`;
}

function requiredCssPresent(diagramSvg) {
  const missing = ['.c-mask', '.t-primary', '.semantic-sigil', '.c-region'].filter(
    (s) => !diagramSvg.includes(s),
  );
  if (missing.length) throw new Error(`export stylesheet missing ${missing.join(', ')}`);
}

const args = parseArgs(process.argv.slice(2));
if (!fs.existsSync(args.htmlPath)) usage(`not found: ${args.htmlPath}`);

const html = fs.readFileSync(args.htmlPath, 'utf8');
const css = extractStyle(html);
const hostStyle = hostStyleFrom(css);
const decls = themeDecls(css, args.theme, args.preset);
const innerSvg = extractDiagramSvg(html);
const { width, height } = viewBoxSize(innerSvg);
const title = extractTitle(html, innerSvg);
const cards = extractCards(html);
const bg = decls.find(([n]) => n === '--bg')?.[1] || '#f8fafc';

const diagramSvg = serializeLocked({
  innerSvg,
  hostStyle,
  decls,
  theme: args.theme,
  preset: args.preset,
  width,
  height,
});
requiredCssPresent(diagramSvg);

const stem = args.stem || path.basename(args.htmlPath).replace(/\.html?$/i, '');
const outDir = args.outDir ? path.resolve(args.outDir) : path.dirname(args.htmlPath);
fs.mkdirSync(outDir, { recursive: true });

const diagramPath = path.join(outDir, `${stem}.diagram.svg`);
fs.writeFileSync(diagramPath, `${diagramSvg}\n`);

let pagePath = null;
if (!args.diagramOnly) {
  const pageSvg = composePage({
    diagramSvg,
    title,
    cards,
    width,
    height,
    theme: args.theme,
    preset: args.preset,
    bg,
  });
  pagePath = path.join(outDir, `${stem}.page.svg`);
  fs.writeFileSync(pagePath, pageSvg);
}

console.log(
  JSON.stringify(
    {
      html: args.htmlPath,
      diagram: diagramPath,
      page: pagePath,
      title,
      theme: args.theme,
      preset: args.preset,
      viewBox: [width, height],
      cards: cards.length,
      diagramBytes: Buffer.byteLength(diagramSvg),
      lightLocked: args.theme === 'light',
    },
    null,
    2,
  ),
);
