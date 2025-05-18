# 🔄 GDrive to MD/CSV

Convert Google Drive files to local formats:
- 📝 Google Docs → Markdown (.md)
- 📊 Google Sheets → CSV (.csv)

## 🚀 Quick Start

```bash
npm install -g @goobits/gdoc-to-md
gdoc-to-md /path/to/google/drive/files
```

## ✨ Features

- Converts files in-place (next to originals)
- Preserves directory structure
- Adds YAML frontmatter to Markdown
- Handles special characters
- Detailed conversion reports

## ⚙️ Prerequisites

1. **Node.js** >= 14.0.0
2. **Python 3** with pip
3. **Pandoc** for Docs conversion
4. **Google API credentials** (`credentials.json`)

## 🛠️ Setup

### 1. Install the Package

```bash
npm install -g @goobits/gdoc-to-md
```

### 2. Install Pandoc

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt install pandoc

# Windows
choco install pandoc
```

### 3. Get Google API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Drive API
3. Create OAuth client ID (Desktop app)
4. Download as `credentials.json`
5. Place in your working directory (or use `--credentials-path` flag)

## 📋 Usage

### Basic

```bash
gdoc-to-md /path/to/files
```

### Options

```bash
gdoc-to-md --gdoc-only         # Only Google Docs
gdoc-to-md --gsheet-only       # Only Google Sheets
gdoc-to-md --skip-existing     # Skip converted files
gdoc-to-md --keep-intermediates # Keep DOCX files
gdoc-to-md --dry-run           # Preview only
gdoc-to-md --limit 5           # Process first 5 files
gdoc-to-md --credentials-path ~/.config/gdoc/creds.json  # Custom credentials path
```

## 📂 Output

### Google Docs → Markdown

```yaml
---
title: "Document Title"
source_doc_id: "google_doc_id"
source_url: "https://docs.google.com/..."
converted_on: "2024-01-15 10:30:00"
---

Your document content in Markdown...
```

### Google Sheets → CSV

Direct CSV export preserving all data and structure.

## 🔐 Security

- Read-only Google Drive access
- Local token storage (`token.pickle`)
- Never commit `credentials.json`
- Credentials excluded from npm package

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

Made with ❤️ by [mudcube](https://github.com/mudcube)