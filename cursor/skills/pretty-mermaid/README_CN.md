<div align="center">

# Pretty-Mermaid Skills

将 Mermaid 图表渲染为**官方 mermaid.js** SVG（与 [mermaid.live](https://mermaid.live) 相同）

无需 Chrome / Puppeteer，已移除 beautiful-mermaid。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**中文** | [English](README.md)

</div>

## 简介

面向 AI 的 Mermaid 渲染 Skill。SVG 由官方 **mermaid.js** 通过 [mermaid.ink](https://mermaid.ink) 生成（Kroki 为备选）。发布到 Confluence 时上传该 SVG，并在下方 expand 中保留源码。

## 功能

- **官方外观** — 与 mermaid.live 一致（`classDef`、标签内 `<br/>`、圆角节点）
- **主题** — `default`、`dark`、`forest`、`neutral`、`base`
- **批量渲染** — 并行 HTTP
- **Confluence** — `confluence/publish.py`

## 快速开始

```bash
node scripts/themes.mjs

node scripts/render.mjs --input diagram.mmd --output output.svg --theme default

python3 confluence/mermaid.py render diagram.mmd output.svg --theme default

node scripts/batch.mjs --input-dir ./diagrams --output-dir ./output --theme default
```

需要访问 mermaid.ink。可用环境变量 `MERMAID_INK_URL` 覆盖。

## Confluence

```bash
python3 ~/.cursor/skills/pretty-mermaid/confluence/publish.py \
  --config path/to/page.publish.json
```

详见 [references/CONFLUENCE.md](references/CONFLUENCE.md) 与 [SKILL.md](SKILL.md)。

## 系统要求

- Node.js 18+（CLI）或 Python 3.10+（`mermaid.py` / 发布）
- 无需 `npm install`

## 许可证

MIT License
