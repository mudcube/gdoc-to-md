#!/usr/bin/env python3
"""
✨ Google Drive Documents to Markdown/CSV Migration Tool ✨

🔄 Converts Google Drive files to local formats:
  • 📝 Google Docs → Markdown (.md)
  • 📊 Google Sheets → CSV (.csv)

🔍 Features:
  • Preserves directory structure
  • Processes files in-place (next to originals)
  • Adds YAML frontmatter to Markdown files
  • Handles special characters in filenames
  • Detailed conversion reports

⚙️ Requirements:
  • credentials.json (Google API OAuth credentials)
  • Pandoc (for DOCX → Markdown conversion)
  • Python packages: google-auth, google-api-python-client

📋 Usage:
  python gdrive_to_md.py [source_directory]

🎛️ Options:
  --keep-intermediates   Store DOCX files for Google Docs
  --skip-existing        Ignore already converted files
  --dry-run              Preview without converting
  --limit N              Process only N files
  --gdoc-only            Process only Google Docs
  --gsheet-only          Process only Google Sheets
"""

import os
import sys
import json
import tempfile
import subprocess
import datetime
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN_FILE = 'token.json'


def save_credentials_secure(creds: Credentials) -> None:
    """Securely save credentials to JSON file."""
    try:
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        if hasattr(creds, 'expiry') and creds.expiry:
            token_data['expiry'] = creds.expiry.isoformat()
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        os.chmod(TOKEN_FILE, 0o600)
        
    except Exception as e:
        logger.error(f"Error saving credentials: {e}")
        raise


def load_credentials_secure() -> Optional[Credentials]:
    """Securely load credentials from JSON file."""
    try:
        if not os.path.exists(TOKEN_FILE):
            return None
            
        file_stat = os.stat(TOKEN_FILE)
        if file_stat.st_mode & 0o077:
            logger.warning(f"{TOKEN_FILE} has overly permissive permissions. Fixing...")
            os.chmod(TOKEN_FILE, 0o600)
            
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        expiry = None
        if 'expiry' in token_data:
            from datetime import datetime
            expiry = datetime.fromisoformat(token_data['expiry'])
        
        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes')
        )
        
        if expiry:
            creds.expiry = expiry
            
        return creds
        
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.debug(f"Could not load credentials: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None


def authenticate(credentials_path: str = 'credentials.json', client_id: str = None, client_secret: str = None) -> Credentials:
    """Authenticate with Google Drive API using OAuth 2.0."""
    creds = load_credentials_secure()
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if client_id and client_secret:
                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "project_id": "gdoc-to-md",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": ["http://localhost"]
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            else:
                if not os.path.exists(credentials_path):
                    logger.error(f"{credentials_path} not found.")
                    logger.error("Please provide credentials using one of these methods:")
                    logger.error("1. Download OAuth client credentials from Google Cloud Console")
                    logger.error(f"   and save them as '{credentials_path}'")
                    logger.error("2. Use --credentials-path flag to specify a different file")
                    logger.error("3. Use --client-id and --client-secret flags")
                    sys.exit(1)
                    
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        save_credentials_secure(creds)
            
    return creds


def get_gdrive_info(file_path: str) -> Optional[Dict]:
    """
    Extract document ID and resource URL from a .gdoc or .gsheet file.
    
    Args:
        file_path: Path to the Google Drive file (.gdoc or .gsheet)
        
    Returns:
        Dictionary containing id, url, name, and type of the document
        or None if extraction fails
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        doc_id = data.get('doc_id') or data.get('resourceid')
        if not doc_id:
            return None
            
        file_ext = Path(file_path).suffix
        file_type = "document" if file_ext == '.gdoc' else "spreadsheet"
        
        return {
            'id': doc_id,
            'url': data.get('url', ''),
            'name': Path(file_path).stem,
            'type': file_type
        }
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return None


def find_gdrive_files(source_dir: str, gdoc_only: bool = False, gsheet_only: bool = False) -> List[str]:
    """Find all .gdoc and .gsheet files in the source directory (recursive)."""
    gdrive_files = []
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            if (not gdoc_only and not gsheet_only) or \
               (gdoc_only and file.endswith('.gdoc')) or \
               (gsheet_only and file.endswith('.gsheet')):
                if file.endswith('.gdoc') or file.endswith('.gsheet'):
                    gdrive_files.append(os.path.join(root, file))
                
    return gdrive_files


def export_file(service, file_id: str, mime_type: str, output_path: str) -> bool:
    """Export a Google Drive file to the specified format."""
    try:
        request = service.files().export_media(fileId=file_id, mimeType=mime_type)
        
        with open(output_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.info(f"Download {int(status.progress() * 100)}%")
        
        return True
    except Exception as e:
        logger.error(f"Error exporting file {file_id}: {e}")
        return False


def convert_docx_to_markdown(docx_path: str, md_path: str) -> bool:
    """Convert DOCX file to Markdown using Pandoc."""
    try:
        try:
            subprocess.run(['pandoc', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Pandoc is not installed or not in PATH")
            logger.error("Please install Pandoc: https://pandoc.org/installing.html")
            return False
        
        result = subprocess.run(
            ['pandoc', docx_path, '-f', 'docx', '-t', 'markdown', '-o', md_path],
            check=True,
            capture_output=True
        )
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting {docx_path} to Markdown: {e}")
        logger.error(f"Pandoc stderr: {e.stderr.decode()}")
        return False


def secure_path_join(base_dir: str, *paths) -> str:
    """Safely join paths ensuring result is within base directory."""
    base_path = os.path.abspath(base_dir)
    
    target_path = os.path.abspath(os.path.join(base_path, *paths))
    
    if not target_path.startswith(base_path + os.sep) and target_path != base_path:
        raise ValueError(f"Path traversal attempt detected: {target_path} is outside {base_path}")
    
    return target_path


def validate_source_path(file_path: str, allowed_extensions: List[str] = ['.gdoc', '.gsheet']) -> bool:
    """Validate file path is safe to process."""
    abs_path = os.path.abspath(file_path)
    
    if not any(abs_path.endswith(ext) for ext in allowed_extensions):
        logger.error(f"Invalid file extension: {file_path}")
        return False
    
    if not os.path.isfile(abs_path):
        logger.error(f"File not found: {file_path}")
        return False
        
    if not os.access(abs_path, os.R_OK):
        logger.error(f"File not readable: {file_path}")
        return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """Create a sanitized filename (remove invalid chars)."""
    filename = os.path.basename(filename)
    
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    filename = ''.join(c for c in filename if c.isprintable())
    
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename


def add_frontmatter_to_markdown(md_path: str, doc_name: str, doc_id: str, docx_path: str = None) -> bool:
    """Add YAML frontmatter with metadata to a markdown file."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = f"""---
title: "{doc_name}"
source_doc_id: "{doc_id}"
source_url: "https://docs.google.com/document/d/{doc_id}/edit"
converted_on: "{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
"""
        
        if docx_path:
            docx_rel_path = os.path.relpath(docx_path, os.path.dirname(md_path))
            frontmatter += f"docx_path: \"{docx_rel_path}\"\n"
            
        frontmatter += "---\n\n"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + content)
        
        return True
    except Exception as e:
        logger.error(f"Error adding frontmatter to {md_path}: {e}")
        return False


def process_gdoc_file(service, file_path: str, keep_intermediates: bool = False, dry_run: bool = False) -> bool:
    """Process a single Google Doc file and convert to Markdown."""
    if not validate_source_path(file_path, ['.gdoc']):
        return False
    
    gdoc_info = get_gdrive_info(file_path)
    if not gdoc_info or not gdoc_info['id'] or gdoc_info['type'] != "document":
        logger.error(f"Could not extract document ID from {file_path} or not a Google Doc")
        return False
    
    doc_id = gdoc_info['id']
    doc_name = gdoc_info['name']
    
    safe_name = sanitize_filename(doc_name)
    
    source_dir = os.path.dirname(os.path.abspath(file_path))
    md_filename = secure_path_join(source_dir, f"{safe_name}.md")
    
    logger.info(f"Processing Google Doc: {doc_name} (ID: {doc_id})")
    logger.info(f"Output file: {md_filename}")
    
    if dry_run:
        logger.info(f"Would convert: {file_path} -> {md_filename}")
        return True
    
    final_docx_path = None
    if keep_intermediates:
        intermediates_dir = secure_path_join(source_dir, 'intermediates')
        os.makedirs(intermediates_dir, exist_ok=True)
        final_docx_path = secure_path_join(intermediates_dir, f"{safe_name}.docx")
    
    if keep_intermediates:
        docx_path = final_docx_path
        docx_mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        if not export_file(service, doc_id, docx_mime, docx_path):
            return False
            
        success = convert_docx_to_markdown(docx_path, md_filename)
        if not success:
            return False
            
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = secure_path_join(temp_dir, f"{safe_name}.docx")
            docx_mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            if not export_file(service, doc_id, docx_mime, docx_path):
                return False
            
            success = convert_docx_to_markdown(docx_path, md_filename)
            if not success:
                return False
    
    logger.info(f"Successfully converted to {md_filename}")
    
    add_frontmatter_to_markdown(
        md_filename, 
        doc_name, 
        doc_id, 
        final_docx_path if keep_intermediates else None
    )
    
    logger.info(f"Added metadata frontmatter to {md_filename}")
    if keep_intermediates and final_docx_path:
        logger.info(f"Kept DOCX file: {final_docx_path}")
    
    return True


def process_gsheet_file(service, file_path: str, keep_intermediates: bool = False, dry_run: bool = False) -> bool:
    """Process a single Google Sheet file and export to CSV format."""
    if not validate_source_path(file_path, ['.gsheet']):
        return False
    
    gsheet_info = get_gdrive_info(file_path)
    if not gsheet_info or not gsheet_info['id'] or gsheet_info['type'] != "spreadsheet":
        logger.error(f"Could not extract spreadsheet ID from {file_path} or not a Google Sheet")
        return False
    
    sheet_id = gsheet_info['id']
    sheet_name = gsheet_info['name']
    
    safe_name = sanitize_filename(sheet_name)
    
    source_dir = os.path.dirname(os.path.abspath(file_path))
    csv_filename = secure_path_join(source_dir, f"{safe_name}.csv")
    
    logger.info(f"Processing Google Sheet: {sheet_name} (ID: {sheet_id})")
    logger.info(f"Output file: {csv_filename}")
    
    if dry_run:
        logger.info(f"Would convert: {file_path} -> {csv_filename}")
        return True
    
    if not export_file(service, sheet_id, 'text/csv', csv_filename):
        return False
    
    logger.info(f"Successfully exported to {csv_filename}")
    
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert Google Drive documents to Markdown and CSV')
    parser.add_argument('source_dir', help='Directory containing .gdoc and .gsheet files (will be searched recursively)')
    parser.add_argument('--limit', type=int, help='Limit the number of files to process')
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip files that already exist in the output directory')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually converting files')
    parser.add_argument('--keep-intermediates', action='store_true',
                       help='Keep the intermediate files (DOCX) for Google Docs in an intermediates/ subdirectory')
    parser.add_argument('--gdoc-only', action='store_true',
                       help='Process only Google Docs files')
    parser.add_argument('--gsheet-only', action='store_true',
                       help='Process only Google Sheets files')
    parser.add_argument('--credentials-path', default='credentials.json',
                       help='Path to Google API credentials JSON file (default: credentials.json)')
    parser.add_argument('--client-id',
                       help='OAuth client ID (alternative to credentials file)')
    parser.add_argument('--client-secret',
                       help='OAuth client secret (alternative to credentials file)')

    args = parser.parse_args()

    source_dir = args.source_dir

    if not os.path.isdir(source_dir):
        logger.error(f"Source directory '{source_dir}' does not exist")
        sys.exit(1)

    if not args.gsheet_only:
        try:
            subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
            logger.info("Pandoc is installed and working correctly")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Pandoc is not installed or not in PATH")
            logger.error("Please install Pandoc: https://pandoc.org/installing.html")
            sys.exit(1)

    service = None
    if not args.dry_run:
        logger.info("Authenticating with Google Drive API...")
        try:
            credentials = authenticate(args.credentials_path, args.client_id, args.client_secret)
            service = build('drive', 'v3', credentials=credentials)
            logger.info("Authentication successful!")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            logger.error(f"Please check your credentials file at {args.credentials_path} and try again.")
            sys.exit(1)
    else:
        logger.info("Dry run mode - skipping authentication with Google API")

    logger.info(f"Finding Google Drive files in {source_dir}...")
    gdrive_files = find_gdrive_files(source_dir, args.gdoc_only, args.gsheet_only)

    if not gdrive_files:
        logger.warning("No Google Drive files found in the specified directory")
        sys.exit(0)

    if args.limit and 0 < args.limit < len(gdrive_files):
        logger.info(f"Limiting to {args.limit} files (of {len(gdrive_files)} found)")
        gdrive_files = gdrive_files[:args.limit]
    else:
        logger.info(f"Found {len(gdrive_files)} Google Drive files")

    success_count = 0
    skip_count = 0
    error_count = 0
    gdocs_processed = 0
    gsheets_processed = 0

    for i, file_path in enumerate(gdrive_files, 1):
        file_type = "Google Doc" if file_path.endswith('.gdoc') else "Google Sheet"
        logger.info(f"\nProcessing file {i} of {len(gdrive_files)}: {os.path.basename(file_path)} ({file_type})")

        try:
            file_info = get_gdrive_info(file_path)
            if not file_info:
                logger.error(f"Could not extract info from {file_path}")
                error_count += 1
                continue

            output_ext = ".md" if file_path.endswith('.gdoc') else ".csv"
            safe_name = sanitize_filename(file_info['name'])
            output_path = os.path.join(os.path.dirname(file_path), f"{safe_name}{output_ext}")

            if args.skip_existing and os.path.exists(output_path):
                logger.info(f"Skipping {file_path} (output file already exists)")
                skip_count += 1
                continue

            success = False
            if file_path.endswith('.gdoc'):
                success = process_gdoc_file(service, file_path, args.keep_intermediates, args.dry_run)
                if success:
                    gdocs_processed += 1
            elif file_path.endswith('.gsheet'):
                success = process_gsheet_file(service, file_path, args.keep_intermediates, args.dry_run)
                if success:
                    gsheets_processed += 1

            if success:
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            error_count += 1

    logger.info("\nConversion Summary:")
    if args.dry_run:
        logger.info("DRY RUN - No files were actually converted")
    logger.info(f"Total files found: {len(gdrive_files)}")
    if args.dry_run:
        logger.info(f"Would convert: {success_count}")
    else:
        logger.info(f"Successfully converted: {success_count}")
        logger.info(f"  - Google Docs processed: {gdocs_processed}")
        logger.info(f"  - Google Sheets processed: {gsheets_processed}")
    if skip_count > 0:
        logger.info(f"Skipped (already exist): {skip_count}")
    logger.info(f"Failed: {error_count}")

    if success_count > 0 and not args.dry_run:
        logger.info("\nFiles have been saved next to their Google Drive counterparts")
        if args.keep_intermediates:
            logger.info("Intermediate files have been saved in 'intermediates/' subdirectories")
        logger.info("Done!")
    elif args.dry_run:
        logger.info("\nTo perform the actual conversion, run the command without --dry-run")


if __name__ == "__main__":
    main()