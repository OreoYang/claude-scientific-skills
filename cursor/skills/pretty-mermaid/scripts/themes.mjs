#!/usr/bin/env node

import { OFFICIAL_THEMES, THEME_ALIAS } from './official-mermaid.mjs';

console.log('Official mermaid.js themes (same as mermaid.live):\n');
OFFICIAL_THEMES.forEach((theme, i) => {
  console.log(`${String(i + 1).padStart(2)}. ${theme}`);
});

console.log(`\nTotal: ${OFFICIAL_THEMES.length} themes`);
console.log('\nLegacy pretty-mermaid aliases → official:');
for (const [alias, official] of Object.entries(THEME_ALIAS)) {
  console.log(`  ${alias.padEnd(22)} → ${official}`);
}

console.log('\nUsage:');
console.log('  node scripts/render.mjs --input diagram.mmd --theme default --output output.svg');
console.log('  Preview: https://mermaid.live/');
