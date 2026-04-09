# OneNote to Markdown - Technical Reference

## Microsoft Graph API Details

### Authentication Flow

The `onenote-dump` tool uses OAuth 2.0 authorization code flow:

1. **Initial Request**: Tool launches browser with authorization URL
2. **User Consent**: User logs in and grants permissions
3. **Token Exchange**: Tool receives authorization code via local server
4. **Access Token**: Exchanges code for access token
5. **API Calls**: Uses access token for OneNote API requests

### Required Permissions

The tool requests `Notes.Read` permission which allows:
- Reading all notebooks
- Accessing all sections and pages
- Downloading page content and attachments

### Token Management

- **Token Storage**: Saved locally for subsequent runs
- **Token Lifetime**: Typically 1 hour
- **Refresh**: Automatic when possible
- **Re-auth**: Use `--new-session` to force new authorization

### API Endpoints Used

```python
# Get notebooks
GET /me/onenote/notebooks

# Get sections in notebook
GET /me/onenote/notebooks/{id}/sections

# Get pages in section
GET /me/onenote/pages?sectionId={id}

# Get page content (HTML)
GET /me/onenote/pages/{id}/content

# Get page attachment
GET /me/onenote/pages/{id}/$value
```

## Rate Limiting

### Microsoft Graph API Limits

- **Default Limit**: ~10,000 requests per 10 minutes
- **Per Notebook**: ~120 requests per minute
- **Retry Handling**: Tool uses `tenacity` library for automatic retries

### Rate Limiting Strategy

```python
# From onenote-dump source
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(requests.exceptions.HTTPError)
)
def api_call():
    # API request here
    pass
```

### Best Practices to Avoid Limits

1. **Process Sections Separately**: Use `--section` flag
2. **Off-Peak Hours**: Run during night or weekends
3. **Batch Processing**: Process multiple notebooks in separate sessions
4. **Resume Capability**: Use `--start-page` to continue interrupted jobs

## HTML to Markdown Conversion

### Conversion Process

```
OneNote Content → HTML (via API) → BeautifulSoup → Markdown
```

### Handling Specific Elements

#### Headers
```html
<h1>Title</h1> → # Title
<h2>Subtitle</h2> → ## Subtitle
```

#### Lists
```html
<ul><li>Item</li></ul> → - Item
<ol><li>Item</li></ol> → 1. Item
```

#### Code Blocks
```html
<pre><code>code</code></pre> → `code` or ```code```
```

#### Tables
```html
<table>
  <tr><th>Header</th></tr>
  <tr><td>Data</td></tr>
</table>
```
Converts to Markdown table format.

#### Images
```html
<img src="url" />
```
Becomes:
```markdown
![Alt Text](@attachment/filename.ext)
```

#### Links
```html
<a href="url">Text</a>
```
Becomes:
```markdown
[Text](url)
```

### Limitations in Conversion

1. **Complex Tables**: Nested tables may simplify
2. **Styling**: Colors, fonts, sizes not preserved
3. **Indentation**: May not match original exactly
4. **Special Characters**: Some Unicode may need manual fixing
5. **Handwriting**: Ink/ drawings not converted

## Troubleshooting Guide

### Common Errors and Solutions

#### "ModuleNotFoundError: No module named 'onenote_dump'"

**Cause**: Python path not set correctly

**Solution**:
```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/onenote-dump
python onenote_dump/main.py "Notebook" "/output"

# Or use -m flag
python -m onenote_dump.main "Notebook" "/output"
```

#### "NotebookNotFound" Exception

**Cause**: Notebook name mismatch or not accessible

**Debug Steps**:
1. List available notebooks:
```python
import requests
from onenote_dump.onenote_auth import get_session

s = get_session(True)
response = s.get("https://graph.microsoft.com/v1.0/me/onenote/notebooks")
print(response.json())
```

2. Check exact name in OneNote
3. Verify sync status in OneDrive

#### HTTP 401 Unauthorized

**Cause**: Token expired or invalid

**Solution**:
```bash
python onenote_dump/main.py "Notebook" "/output" --new-session
```

#### HTTP 429 Too Many Requests

**Cause**: Rate limit exceeded

**Solution**:
- Wait for automatic retry (built-in)
- Process sections separately
- Try again later

#### Empty or Incomplete Markdown

**Cause**: API didn't return full content

**Debug**:
```bash
# Run with verbose flag
python onenote_dump/main.py "Notebook" "/output" --verbose
```

Check log output for:
- API response codes
- Content length
- Parsing errors

## Advanced Configuration

### Custom Output Format

Modify `convert.py` to change markdown formatting:

```python
# Original (Notable format)
frontmatter = f'''---
title: "{title}"
created: '{created}'
modified: '{modified}'
tags: {tags}
---
'''

# Custom format (Obsidian)
frontmatter = f'''---
title: {title}
created: {created}
tags: [{', '.join(tags)}]
---

# {title}

'''

# JupyterBook format
frontmatter = f'''(page-title)=
# {title

```python
class CustomConverter:
    def convert_page(self, page):
        # Custom conversion logic
        pass

# Use in pipeline.py
pipe = pipeline.Pipeline(session, notebook, output_dir, converter=CustomConverter())
```

### Logging Configuration

```python
import logging

# Detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('onenote.log'),
        logging.StreamHandler()
    ]
)
```

## Manual Conversion Methods

### Using Microsoft OneNote API Directly

```python
import requests
from msal import PublicClientApplication

# Authenticate
app = PublicClientApplication(
    client_id="your-client-id",
    authority="https://login.microsoftonline.com/common"
)

result = app.acquire_token_interactive(scopes=["Notes.Read"])

# Get pages
headers = {'Authorization': f'Bearer {result["access_token"]}'}
response = requests.get(
    'https://graph.microsoft.com/v1.0/me/onenote/pages',
    headers=headers
)

pages = response.json()['value']
```

### Export via OneNote Interop (Windows Only)

```python
# Requires OneNote 2016 installed
import win32com.client

onenote = win32com.client.Dispatch("OneNote.Application")
# Get notebook hierarchy
# Export pages to Word/HTML
# Convert with Pandoc
```

### Using OneNote REST API with curl

```bash
# Get access token via OAuth
# Then:

curl -X GET \
  'https://graph.microsoft.com/v1.0/me/onenote/notebooks' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'

# Get pages
curl -X GET \
  'https://graph.microsoft.com/v1.0/me/onenote/pages' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

## Performance Optimization

### Caching Strategy

```python
import pickle
import os

class CachedSession:
    def __init__(self, cache_file='.cache'):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'rb') as f:
                return pickle.load(f)
        return {}

    def get(self, url):
        if url in self.cache:
            return self.cache[url]
        response = requests.get(url)
        self.cache[url] = response
        return response

    def save(self):
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.cache, f)
```

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor

def convert_page_parallel(pages, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(convert_single_page, pages)
    return list(results)
```

### Incremental Updates

```bash
# Only convert pages modified after last run
# Requires tracking last conversion time

python onenote_dump/main.py "Notebook" "/output" \
  --after-date "2026-01-01T00:00:00Z"
```

## Integration Examples

### Git Version Control

```bash
# Initialize repo for converted notes
cd onenote_output
git init
git add .
git commit -m "Initial OneNote conversion"

# Subsequent conversions
python onenote_dump/main.py "Notebook" "/output"
git add .
git commit -m "Update from OneNote"
```

### Automated Sync Script

```bash
#!/bin/bash
# sync_onenote.sh

NOTEBOOK="My Notebook"
OUTPUT="/path/to/output"
LOG="/var/log/onenote-sync.log"

{
  echo "Starting sync at $(date)"
  cd /path/to/onenote-dump
  source .venv/bin/activate
  python onenote_dump/main.py "$NOTEBOOK" "$OUTPUT" 2>&1
  echo "Sync completed at $(date)"
} >> "$LOG" 2>&1

# Add to crontab for automatic sync
# 0 */6 * * * /path/to/sync_onenote.sh
```

### Post-Processing Pipeline

```python
import os
import re

def postprocess_markdown(directory):
    """Clean up markdown files after conversion"""
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Fix common issues
            content = fix_links(content)
            content = clean_tables(content)
            content = standardize_headers(content)
            
            with open(filepath, 'w') as f:
                f.write(content)

def fix_links(content):
    # Fix internal OneNote links
    return re.sub(r'\[([^\]]+)\]\(onenote:([^\)]+)\)', r'[\1](\2.md)', content)

def clean_tables(content):
    # Fix table formatting issues
    return content

def standardize_headers(content):
    # Ensure header spacing
    return re.sub(r'\n#+', r'\n\n\g<0>', content)
```

## Security Considerations

### Token Storage

Tokens are stored locally. Protect them:

```bash
# Set restrictive permissions
chmod 600 ~/.config/onenote-dump/token.json
```

### Sensitive Content

- Converted markdown may contain sensitive information
- Implement appropriate access controls on output directory
- Consider encryption for sensitive notebooks

### Permissions

The tool requests minimal permissions (`Notes.Read` only):
- ✅ Can read all notes
- ✅ Can download attachments
- ❌ Cannot create or modify notes
- ❌ Cannot share or delete notes

## API Alternatives

### OneNote REST API (Legacy)

```bash
# Legacy API (still functional)
GET https://www.onenote.com/api/v1.0/me/notes
```

### Microsoft Graph API (Current)

```bash
# Current recommended API
GET https://graph.microsoft.com/v1.0/me/onenote/pages
```

### Third-Party Services

- **OneNote Batch**: Batch operations
- **OneNote Webhook**: Real-time updates
- **Microsoft Power Automate**: Workflow integration

## Testing and Validation

### Unit Testing

```python
import unittest

class TestOneNoteConversion(unittest.TestCase):
    def test_html_to_markdown(self):
        html = "<h1>Title</h1>"
        expected = "# Title\n"
        result = convert_html_to_markdown(html)
        self.assertEqual(result, expected)

    def test_page_structure(self):
        page = load_test_page()
        self.assertIn('title', page)
        self.assertIn('content', page)
        self.assertIn('created', page)
```

### Integration Testing

```bash
# Test with small notebook first
python onenote_dump/main.py "Test Notebook" "/test_output" --max-pages 3

# Verify output
ls -la /test_output/notes/
wc -l /test_output/notes/*.md
```

### Quality Checks

```python
def validate_conversion(output_dir):
    """Check for common conversion issues"""
    issues = []
    
    for md_file in glob.glob(f"{output_dir}/*.md"):
        with open(md_file) as f:
            content = f.read()
        
        # Check for common issues
        if '@attachment' in content and not os.path.exists('attachments'):
            issues.append(f"Missing attachments in {md_file}")
        
        if 'onenote://' in content:
            issues.append(f"Uncorrected OneNote links in {md_file}")
    
    return issues
```

## Support and Resources

### Getting Help

1. **GitHub Issues**: https://github.com/genericmoniker/onenote-dump/issues
2. **Microsoft Graph Docs**: https://learn.microsoft.com/en-us/graph/
3. **OneNote Dev Blog**: https://devblogs.microsoft.com/onenote/

### Debug Mode

```bash
# Enable verbose logging
python onenote_dump/main.py "Notebook" "/output" --verbose

# Check logs
tail -f onenote.log
```

### Common Workarounds

1. **API Throttling**: Use `--section` to process separately
2. **Missing Pages**: Check OneNote sync status
3. **Broken Links**: Manual fix or post-processing script
4. **Large Notebooks**: Process in batches with `--max-pages`

## Future Enhancements

Potential improvements for the tool:

1. **Incremental Sync**: Only convert changed pages
2. **Two-way Sync**: Push markdown changes back to OneNote
3. **Custom Templates**: User-defined output formats
4. **Plugin System**: Extensible conversion pipeline
5. **GUI**: Desktop application for non-technical users
