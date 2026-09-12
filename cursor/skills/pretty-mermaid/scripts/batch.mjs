#!/usr/bin/env node

import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { renderOfficialSvg, resolveTheme, OFFICIAL_THEMES } from './official-mermaid.mjs';

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    inputDir: null,
    outputDir: null,
    format: 'svg',
    theme: 'default',
    transparent: false,
    workers: 4,
  };

  for (let i = 0; i < args.length; i++) {
    const key = args[i];
    const val = args[i + 1];

    switch (key) {
      case '--input-dir': case '-i': opts.inputDir = val; i++; break;
      case '--output-dir': case '-o': opts.outputDir = val; i++; break;
      case '--format': case '-f': opts.format = val; i++; break;
      case '--theme': case '-t': opts.theme = val; i++; break;
      case '--transparent': opts.transparent = true; break;
      case '--workers': case '-w': opts.workers = parseInt(val, 10); i++; break;
      case '--bg':
      case '--fg':
        i++;
        break;
      case '--use-ascii':
        break;
      case '--help': case '-h':
        console.log(`Usage: node batch.mjs --input-dir <dir> --output-dir <dir> [options]

Options:
  -i, --input-dir <dir>    Input directory containing .mmd files [required]
  -o, --output-dir <dir>   Output directory for SVG files [required]
  -f, --format <fmt>       svg only
  -t, --theme <name>       Official theme: ${OFFICIAL_THEMES.join(', ')}
      --transparent        Transparent background
  -w, --workers <n>        Parallel workers (default: 4)`);
        process.exit(0);
    }
  }

  if (!opts.inputDir) {
    console.error('Error: --input-dir is required. Use --help for usage.');
    process.exit(1);
  }
  if (!opts.outputDir) {
    console.error('Error: --output-dir is required. Use --help for usage.');
    process.exit(1);
  }
  if (!existsSync(opts.inputDir)) {
    console.error(`Error: Input directory not found: ${opts.inputDir}`);
    process.exit(1);
  }

  return opts;
}

async function renderFile(file, inputDir, outputDir, opts) {
  const inputPath = join(inputDir, file);
  const outputPath = join(outputDir, file.replace(/\.mmd$/, '.svg'));
  const input = readFileSync(inputPath, 'utf8');
  const svg = await renderOfficialSvg(input, {
    theme: resolveTheme(opts.theme),
    transparent: opts.transparent,
  });
  writeFileSync(outputPath, svg);
}

async function main() {
  const opts = parseArgs();

  if (opts.format === 'ascii') {
    console.error(
      'ASCII Mermaid output was provided by beautiful-mermaid and has been removed.'
    );
    process.exit(1);
  }

  mkdirSync(opts.outputDir, { recursive: true });

  const files = readdirSync(opts.inputDir).filter((f) => f.endsWith('.mmd'));
  if (files.length === 0) {
    console.error(`No .mmd files found in ${opts.inputDir}`);
    process.exit(1);
  }

  console.log(`Found ${files.length} diagram(s) to render (official mermaid.js)…`);

  let success = 0;
  const failed = [];

  for (let i = 0; i < files.length; i += opts.workers) {
    const batch = files.slice(i, i + opts.workers);
    const results = await Promise.allSettled(
      batch.map((file) => renderFile(file, opts.inputDir, opts.outputDir, opts))
    );

    results.forEach((result, idx) => {
      const file = batch[idx];
      if (result.status === 'fulfilled') {
        console.log(`\u2713 ${file}`);
        success++;
      } else {
        console.error(`\u2717 ${file}: ${result.reason?.message || result.reason}`);
        failed.push([file, result.reason?.message || String(result.reason)]);
      }
    });
  }

  console.log(`\n${success}/${files.length} diagrams rendered successfully`);

  if (failed.length > 0) {
    console.error(`\n${failed.length} failed:`);
    for (const [file, error] of failed) {
      console.error(`  - ${file}: ${error}`);
    }
    process.exit(1);
  }
}

main().catch((e) => {
  console.error('Error:', e.message);
  process.exit(1);
});
