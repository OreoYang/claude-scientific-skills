---
name: onenote2markdown
description: Use this skill when the user wants to convert Microsoft OneNote notebooks to Markdown format. This includes converting entire notebooks, specific sections, or individual pages from OneNote to .md files. Supports both cloud-synced OneNote notebooks via Microsoft Graph API and manual export workflows. Trigger when user mentions OneNote conversion, .one files, or exporting OneNote content to Markdown.
license: MIT
---

# OneNote to Markdown Conversion Guide

## Overview

This guide covers converting Microsoft OneNote notebooks to Markdown format. The primary method uses the `onenote-dump` tool which leverages Microsoft Graph API to access OneNote content that has been synced to OneDrive.

## Quick Start

### Prerequisites
- OneNote notebook synced to OneDrive
- Python 3.6+
- Microsoft account with OneNote access

### Basic Conversion

```bash
# Clone the tool
git clone https://github.com/genericmoniker/onenote-dump.git
cd onenote-dump

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Convert notebook
python onenote_dump/main.py "Notebook Name" "/path/to/output"
```

## Installation

### Method 1: Using onenote-dump (Recommended)

The `onenote-dump` tool is the most reliable solution for converting OneNote notebooks that are synced to OneDrive.

**Features:**
- Converts entire notebooks to Markdown
- Preserves page hierarchy
- Downloads attachments (images, files)
- Maintains metadata (created/modified dates, tags)
- Compatible with Notable markdown format

**Installation Steps:**

```bash
# Clone repository
git clone https://github.com/genericmoniker/onenote-dump.git
cd onenote-dump

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### Method 2: Alternative Tools

If `onenote-dump` doesn't meet your needs, consider these alternatives:

```bash
# stephengrice/onenote-to-markdown
git clone https://github.com/stephengrice/onenote-to-markdown.git

# Manual export + Pandoc (for small number of pages)
# 1. Export OneNote pages to .docx
# 2. Convert using: pandoc input.docx -o output.md -t markdown
```

## Usage

### Basic Conversion

```bash
python onenote_dump/main.py "Notebook Name" "/path/to/output"
```

**What happens:**
1. Browser opens for Microsoft OAuth authorization
2. Tool accesses OneNote via Microsoft Graph API
3. Downloads all pages from specified notebook
4. Converts each page to individual .md file
5. Downloads attachments to `attachments/` folder

### Advanced Options

```bash
# Convert specific section
python onenote_dump/main.py "Notebook Name" "/output" --section "Section Name"

# Limit number of pages (for testing)
python onenote_dump/main.py "Notebook Name" "/output" --max-pages 5

# Start from specific page (for resuming)
python onenote_dump/main.py "Notebook Name" "/output" --start-page 10

# Force re-authorization
python onenote_dump/main.py "Notebook Name" "/output" --new-session

# Verbose output
python onenote_dump/main.py "Notebook Name" "/output" --verbose
```

### Expected Output Structure

```
output/
├── notes/              # Markdown files
│   ├── Page1.md
│   ├── Page2.md
│   └── ...
└── attachments/        # Images and embedded files
    ├── image1.png
    ├── document.pdf
    └── ...
```

## Output Format

### Markdown File Structure

Each converted page includes:

```markdown
---
title: "Page Title"
created: '2026-01-14T06:05:36.618Z'
modified: '2026-01-14T06:05:43Z'
tags: [Notebooks/notebook-name, Tag1, Tag2]
---

# Page Title

Page content here...

## Subheading

More content...

![Image](@attachment/unique-id.png)

Links are preserved as [text](url)
```

**Features preserved:**
- Headings and hierarchical structure
- Lists (bullet and numbered)
- Code blocks
- Tables
- Links (internal and external)
- Images (as attachments)
- Basic formatting (bold, italic, etc.)

## Troubleshooting

### "NotebookNotFound" Error

**Cause:** Notebook name doesn't match or not synced to OneDrive

**Solutions:**
1. Verify exact notebook name in OneNote
2. Ensure notebook is synced to OneDrive
3. Check OneDrive → Documents → OneNote Notebooks
4. Try using notebook display name exactly as shown

### Rate Limiting

**Symptom:** Tool pauses during conversion

**Cause:** Microsoft Graph API rate limits

**Solutions:**
- Tool automatically waits and retries
- For large notebooks: Use `--section` to process sections separately
- Use `--start-page` to resume from specific page
- Consider running during off-peak hours

### Authentication Issues

**Symptom:** OAuth fails or token expires

**Solutions:**
```bash
# Force re-authorization
python onenote_dump/main.py "Notebook" "/output" --new-session
```

### Missing Attachments

**Symptom:** Images not showing in Markdown

**Solutions:**
1. Check `attachments/` folder exists
2. Verify image references use `@attachment/` syntax
3. Some image formats may not be supported
4. Check download permissions in OneDrive

## Manual Export Method

If API method doesn't work, use manual export:

### For Small Numbers of Pages

```bash
# 1. In OneNote: Right-click page → Export → .docx
# 2. Convert using Pandoc
pandoc input.docx -o output.md -t markdown

# For multiple files
for file in *.docx; do
  pandoc "$file" -o "${file%.docx}.md" -t markdown
done
```

### For Entire Notebooks

1. Export entire notebook to .docx (OneNote → File → Export)
2. Split document by sections if needed
3. Convert each section with Pandoc
4. Manually organize into desired file structure

## Best Practices

### Before Conversion

1. **Sync to OneDrive**: Ensure notebook is fully synced
2. **Check Notebook Name**: Verify exact name in OneNote
3. **Test Small**: Use `--max-pages 5` for initial test
4. **Backup**: Keep original OneNote notebook as backup

### During Conversion

1. **Monitor Output**: Watch for errors or rate limiting
2. **Check Progress**: Tool shows page count as it processes
3. **Attachments**: Verify `attachments/` folder is populated

### After Conversion

1. **Verify Content**: Check random .md files for quality
2. **Test Import**: Try importing to target tool (Obsidian, Logseq)
3. **Check Images**: Ensure attachments display correctly
4. **Compare Counts**: Verify page count matches original

## Integration with Note-Taking Tools

### Obsidian

```bash
# Copy converted notebook to Obsidian vault
cp -r /path/to/onenote_output/notes/* ~/Documents/ObsidianVault/

# Copy attachments
cp -r /path/to/onenote_output/attachments/* ~/Documents/ObsidianVault/
```

### Logseq

```bash
# Copy to Logseq pages directory
cp -r /path/to/onenote_output/notes/* ~/Documents/Logseq/pages/

# Handle attachments separately
```

### Notable

The tool outputs in Notable-compatible format by default:
- Metadata in YAML frontmatter
- `@attachment/` syntax for attachments
- `@note/` syntax for note links

## Advanced Scenarios

### Converting Multiple Notebooks

```bash
#!/bin/bash
# convert_all.sh

notebooks=("Notebook1" "Notebook2" "Notebook3")

for notebook in "${notebooks[@]}"; do
  echo "Converting $notebook..."
  python onenote_dump/main.py "$notebook" "/output/$notebook"
done
```

### Scheduled Conversions

```bash
# Run weekly conversion using cron
# Add to crontab: 0 2 * * 0 /path/to/convert.sh

#!/bin/bash
cd /path/to/onenote-dump
source .venv/bin/activate
python onenote_dump/main.py "My Notebook" "/output/$(date +%Y%m%d)"
```

### Filtering Content

```bash
# Convert only specific sections
sections=("Section1" "Section2" "Important Notes")

for section in "${sections[@]}"; do
  python onenote_dump/main.py "Notebook" "/output" --section "$section"
done
```

## Limitations

### Known Limitations

1. **Cloud Sync Required**: Notebook must be synced to OneDrive
2. **Formatting**: Complex formatting may not convert perfectly
3. **Tables**: Complex table structures may simplify
4. **Handwriting**: Ink/handwriting not supported
5. **Audio/Video**: Embedded media may not convert
6. **File Size**: Very large notebooks may hit rate limits

### Workarounds

- **Complex Formatting**: Manual cleanup after conversion
- **Large Notebooks**: Use `--section` to process in parts
- **Missing Content**: Compare with original and manually add
- **Handwritten Notes**: Export as images separately

## Quick Reference

| Task | Command |
|------|---------|
| Basic conversion | `python onenote_dump/main.py "Notebook" "/output"` |
| Specific section | `python onenote_dump/main.py "Notebook" "/output" --section "Section"` |
| Test with few pages | `python onenote_dump/main.py "Notebook" "/output" --max-pages 5` |
| Resume from page | `python onenote_dump/main.py "Notebook" "/output" --start-page 10` |
| Re-authorize | `python onenote_dump/main.py "Notebook" "/output" --new-session` |

## Resources

- **onenote-dump GitHub**: https://github.com/genericmoniker/onenote-dump
- **Microsoft Graph API**: https://learn.microsoft.com/en-us/graph/integrate-with-onenote
- **Alternative Tools**: https://github.com/stephengrice/onenote-to-markdown
- **Pandoc Documentation**: https://pandoc.org/

## Next Steps

For troubleshooting, advanced API usage, or manual conversion methods, see REFERENCE.md.
