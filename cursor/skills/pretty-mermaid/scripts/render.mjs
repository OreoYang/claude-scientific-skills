#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from 'fs';
import { renderOfficialSvg, resolveTheme, OFFICIAL_THEMES } from './official-mermaid.mjs';

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    input: null,
    output: null,
    format: 'svg',
    theme: 'default',
    transparent: false,
  };

  for (let i = 0; i < args.length; i++) {
    const key = args[i];
    const val = args[i + 1];

    switch (key) {
      case '--input': case '-i': opts.input = val; i++; break;
      case '--output': case '-o': opts.output = val; i++; break;
      case '--format': case '-f': opts.format = val; i++; break;
      case '--theme': case '-t': opts.theme = val; i++; break;
      case '--transparent': opts.transparent = true; break;
      case '--bg':
      case '--fg':
      case '--line':
      case '--accent':
      case '--muted':
      case '--surface':
      case '--border':
      case '--font':
      case '--padding-x':
      case '--padding-y':
      case '--box-border-padding':
        i++;
        break;
      case '--use-ascii':
        break;
      case '--help': case '-h':
        console.log(`Usage: node render.mjs --input <file> [options]

Renders Mermaid via official mermaid.js (mermaid.ink / mermaid.live).

Options:
  -i, --input <file>       Input Mermaid file (.mmd) [required]
  -o, --output <file>      Output SVG file (default: stdout)
  -f, --format <fmt>       svg only (ascii is not supported)
  -t, --theme <name>       Official theme: ${OFFICIAL_THEMES.join(', ')}
                           (aliases: github-light→default, tokyo-night→dark, …)
      --transparent        Transparent background (SVG)`);
        process.exit(0);
    }
  }

  if (!opts.input) {
    console.error('Error: --input is required. Use --help for usage.');
    process.exit(1);
  }

  if (!existsSync(opts.input)) {
    console.error(`Error: Input file not found: ${opts.input}`);
    process.exit(1);
  }

  return opts;
}

async function main() {
  const opts = parseArgs();

  if (opts.format === 'ascii') {
    console.error(
      'ASCII Mermaid output was provided by beautiful-mermaid and has been removed. ' +
      'Render SVG instead, or preview at https://mermaid.live/'
    );
    process.exit(1);
  }

  const input = readFileSync(opts.input, 'utf8');
  const svg = await renderOfficialSvg(input, {
    theme: resolveTheme(opts.theme),
    transparent: opts.transparent,
  });

  if (opts.output) {
    writeFileSync(opts.output, svg);
    console.log(`SVG diagram saved to ${opts.output}`);
  } else {
    process.stdout.write(svg);
  }
}

main().catch((e) => {
  console.error('Error:', e.message);
  process.exit(1);
});
