# 🔄 GDrive to MD/CSV

Convert Google Drive files to local formats:
- 📝 Google Docs → Markdown (.md)
- 📊 Google Sheets → CSV (.csv)

## ✨ Features

- Converts files in-place (next to originals)
- Preserves complete directory structure
- Recursively processes all subdirectories
- Adds YAML frontmatter with metadata to Markdown
- Handles special characters in filenames
- Provides detailed conversion reports

## ⚙️ Requirements

- `credentials.json` (Google API OAuth credentials)
- Pandoc (for DOCX → Markdown conversion)
- Python packages: `google-auth`, `google-api-python-client`

## 🛠️ Setup

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Pandoc**:
   ```bash
   # macOS
   brew install pandoc
   
   # Ubuntu/Debian
   sudo apt install pandoc
   
   # Windows
   choco install pandoc
   ```

3. **Configure Google API**:
   - Create project in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Google Drive API
   - Create OAuth client ID (Desktop app)
   - Download credentials as `credentials.json`
   - Place in same directory as script

## 📋 Usage

### Basic Usage

```bash
python gdrive_to_md.py /path/to/google/drive/files
```

On first run, the script will:
1. Open browser for authentication
2. Ask for Drive access permissions
3. Store token for future use (`token.pickle`)

### 🎛️ Options

```bash
# Process only Google Docs
python gdrive_to_md.py --gdoc-only /path/to/files

# Process only Google Sheets
python gdrive_to_md.py --gsheet-only /path/to/files

# Skip already converted files
python gdrive_to_md.py --skip-existing /path/to/files

# Keep intermediate DOCX files
python gdrive_to_md.py --keep-intermediates /path/to/files

# Preview without converting (dry run)
python gdrive_to_md.py --dry-run /path/to/files

# Process only first 5 files
python gdrive_to_md.py --limit 5 /path/to/files
```

## 📂 Output Format

### 📝 Google Docs (.gdoc)

Converted to Markdown with YAML frontmatter:

```yaml
---
title: "Document Title"
source_doc_id: "google_doc_id"
source_url: "https://docs.google.com/document/d/doc_id/edit"
converted_on: "YYYY-MM-DD HH:MM:SS"
---

Document content in Markdown...
```

### 📊 Google Sheets (.gsheet)

Exported directly as CSV format, preserving data and structure.

## 🔐 Security Notes

- The script requests only read-only access to Google Drive
- No content is sent to external servers
- Authentication token stored locally as `token.pickle`
- Access can be revoked anytime in Google Account settings