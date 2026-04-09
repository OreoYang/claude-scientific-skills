# OneNote to Markdown Skill

## Overview

This skill provides comprehensive tools and guides for converting Microsoft OneNote notebooks to Markdown format. It supports cloud-synced OneNote notebooks via Microsoft Graph API and includes automated conversion scripts.

## Quick Start

### Method 1: Interactive Script

```bash
# Run the interactive quick-start script
bash ~/.claude/skills/onenote2markdown/scripts/quick_start.sh
```

### Method 2: Manual Setup

```bash
# Clone the converter tool
git clone https://github.com/genericmoniker/onenote-dump.git
cd onenote-dump

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Convert your notebook
python onenote_dump/main.py "Your Notebook Name" "./output"
```

## Features

- ✅ **Full Notebook Conversion**: Convert entire OneNote notebooks to Markdown
- ✅ **Section-Level**: Convert specific sections instead of whole notebooks
- ✅ **Attachment Support**: Automatically downloads images and attachments
- ✅ **Metadata Preservation**: Maintains creation dates, modification times, and tags
- ✅ **Hierarchical Structure**: Preserves page hierarchy and organization
- ✅ **Multiple Formats**: Compatible with Notable, Obsidian, Logseq, etc.

## Usage Examples

### Basic Conversion

```bash
python onenote_dump/main.py "My Notebook" "/path/to/output"
```

### Convert Specific Section

```bash
python onenote_dump/main.py "My Notebook" "/output" --section "Work Notes"
```

### Test Conversion (Limited Pages)

```bash
python onenote_dump/main.py "My Notebook" "/output" --max-pages 5
```

### Resume from Page

```bash
python onenote_dump/main.py "My Notebook" "/output" --start-page 10
```

## Batch Conversion

Use the included batch conversion script:

```bash
# Convert multiple notebooks
python3 ~/.claude/skills/onenote2markdown/scripts/batch_convert.py \
    "Notebook1" "Notebook2" "Notebook3" \
    -o ./output

# Convert with config file
python3 ~/.claude/skills/onenote2markdown/scripts/batch_convert.py \
    "My Notebook" \
    -c config.json \
    --max-pages 50
```

## Output Structure

```
output/
├── notes/              # Markdown files (one per page)
│   ├── Page1.md
│   ├── Page2.md
│   └── ...
└── attachments/        # Downloaded images and files
    ├── image1.png
    ├── document.pdf
    └── ...
```

## Requirements

- **OneNote synced to OneDrive**: Notebook must be cloud-synced
- **Python 3.6+**: Required for the conversion tool
- **Microsoft Account**: For OAuth authentication
- **Virtual Environment**: Recommended for dependency isolation

## Troubleshooting

### "NotebookNotFound" Error

- Verify exact notebook name in OneNote
- Ensure notebook is synced to OneDrive
- Check OneDrive → Documents → OneNote Notebooks

### Rate Limiting

- Tool automatically waits and retries
- For large notebooks, use `--section` to process separately
- Try running during off-peak hours

### Authentication Issues

```bash
# Force re-authorization
python onenote_dump/main.py "Notebook" "/output" --new-session
```

## Advanced Features

### Custom Output Format

Modify the conversion logic to customize markdown formatting for your preferred note-taking app (Obsidian, Logseq, etc.).

### Automated Synchronization

Set up cron jobs or scheduled tasks for regular backups:

```bash
# Add to crontab for daily conversion
0 2 * * * /path/to/convert_script.sh
```

### Post-Processing

Apply custom transformations to converted markdown:

```python
# Fix links, clean tables, standardize formatting
python3 postprocess.py /path/to/output
```

## Integration with Note-Taking Tools

### Obsidian

```bash
# Copy to Obsidian vault
cp -r output/notes/* ~/Documents/ObsidianVault/
cp -r output/attachments/* ~/Documents/ObsidianVault/
```

### Logseq

```bash
# Copy to Logseq pages directory
cp -r output/notes/* ~/Documents/Logseq/pages/
```

### Notable

Output is already in Notable-compatible format by default.

## Documentation

- **SKILL.md**: Comprehensive usage guide
- **REFERENCE.md**: Technical details and troubleshooting
- **scripts/**: Helper scripts for automation

## Limitations

- **Cloud Sync Required**: Local-only notebooks not supported
- **Complex Formatting**: Some advanced formatting may simplify
- **Handwriting**: Ink/ drawings not converted
- **File Size**: Very large notebooks may hit API rate limits

## Alternative Methods

For notebooks not synced to OneDrive:

1. **Manual Export**: Export pages to .docx, convert with Pandoc
2. **OneNote Desktop API**: Use COM automation on Windows
3. **Copy-Paste**: Manual copy to Markdown editor

## Support

- **GitHub Issues**: https://github.com/genericmoniker/onenote-dump/issues
- **Microsoft Graph API**: https://learn.microsoft.com/en-us/graph/
- **Skill Documentation**: See SKILL.md and REFERENCE.md

## Contributing

To improve this skill:

1. Test with various notebook types and sizes
2. Document edge cases and solutions
3. Share scripts for post-processing or automation
4. Report bugs and feature requests

## License

MIT License - See LICENSE.txt for details

---

**Created**: 2026-04-08
**Version**: 1.0.0
**Maintained**: Claude Code Assistant
