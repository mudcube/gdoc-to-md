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

- Node.js >= 14.0.0
- Python 3.x with pip
- `credentials.json` (Google API OAuth credentials)
- Pandoc (for DOCX → Markdown conversion)

## 🛠️ Setup

### NPM Installation (Recommended)

```bash
npm install -g @goobits/gdoc-to-md
```

This will automatically install Python dependencies during installation.

### Manual Installation

1. **Clone Repository**:
   ```bash
   git clone https://github.com/mudcube/gdrive-to-md.git
   cd gdrive-to-md
   npm install
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
   - Place in your working directory

## 📋 Usage

### Basic Usage

```bash
# If installed via npm
gdoc-to-md /path/to/google/drive/files

# If running locally
npm run gdoc-to-md /path/to/google/drive/files

# Or using Python directly
python gdrive_to_md.py /path/to/google/drive/files
```

On first run, the script will:
1. Open browser for authentication
2. Ask for Drive access permissions
3. Store token for future use (`token.pickle`)

### 🎛️ Options

```bash
# Process only Google Docs
gdoc-to-md --gdoc-only /path/to/files

# Process only Google Sheets  
gdoc-to-md --gsheet-only /path/to/files

# Skip already converted files
gdoc-to-md --skip-existing /path/to/files

# Keep intermediate DOCX files
gdoc-to-md --keep-intermediates /path/to/files

# Preview without converting (dry run)
gdoc-to-md --dry-run /path/to/files

# Process only first 5 files
gdoc-to-md --limit 5 /path/to/files
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
- **IMPORTANT**: Never commit `credentials.json` or `token.pickle` to version control
- The `.npmignore` file ensures credentials are not included when publishing to npm

## 📦 Publishing to NPM

This package (`@goobits/gdoc-to-md`) is configured to exclude all sensitive files:
- `credentials.json` - Your Google API credentials
- `token.pickle` - Your authentication token
- Test files and development artifacts

Users will need to provide their own `credentials.json` file after installation.

## Prerequisites

Before installing this package, ensure you have:
- Python 3.x with pip installed
- Pandoc installed (for Google Docs conversion)

The package will attempt to install Python dependencies during npm installation.