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
import pickle
import datetime
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Google API libraries
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# OAuth 2.0 scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def authenticate() -> Credentials:
    """Authenticate with Google Drive API using OAuth 2.0."""
    creds = None
    
    # Check if token.pickle exists with saved credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials don't exist or are invalid, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found.")
                print("Please download OAuth client credentials from Google Cloud Console")
                print("and save them as 'credentials.json' in the same directory as this script.")
                sys.exit(1)
                
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
    return creds


def _clean_file_content(content: str, debug_mode: bool = False) -> str:
    """
    Clean Google Drive file content by removing comments and preserving URLs.
    
    Args:
        content: Raw file content
        debug_mode: Whether to print debug info
        
    Returns:
        Cleaned content
    """
    # Remove any JavaScript-style comments (//...)
    lines = content.split('\n')
    clean_lines = [line for line in lines if not line.strip().startswith('//')]
    
    # Be careful with handling inline comments - don't split URLs that contain //
    processed_lines = []
    for line in clean_lines:
        # Don't split if the line contains a URL
        if 'http://' in line or 'https://' in line:
            processed_lines.append(line)
        else:
            # Handle inline comments
            processed_lines.append(line.split('//')[0])
            
    clean_content = '\n'.join(processed_lines)
    
    if debug_mode:
        print(f"Debug - Clean content length: {len(clean_content)}")
        
    return clean_content


def _extract_document_info(content: str, debug_mode: bool = False) -> Dict:
    """
    Extract document information from Google Drive file content.
    
    Args:
        content: Cleaned file content
        debug_mode: Whether to print debug info
        
    Returns:
        Dictionary with document information
        
    Raises:
        Exception: If document ID cannot be extracted
    """
    try:
        # Try to parse as JSON directly
        file_content = json.loads(content)
        if debug_mode:
            print(f"Debug - Successfully parsed JSON. Keys: {list(file_content.keys())}")
        return file_content
    except json.JSONDecodeError as e:
        if debug_mode:
            print(f"Debug - JSON parse error: {e}")
        
        # If that fails, try to extract the doc_id using regex
        doc_id_match = re.search(r'"doc_id"\s*:\s*"([^"]+)"', content)
        url_match = re.search(r'"url"\s*:\s*"([^"]+)"', content)
        
        if debug_mode:
            print(f"Debug - Regex doc_id match: {doc_id_match is not None}")
            print(f"Debug - Regex url match: {url_match is not None}")

        if doc_id_match:
            file_content = {
                'doc_id': doc_id_match.group(1),
                'url': url_match.group(1) if url_match else ""
            }
            if debug_mode:
                print(f"Debug - Extracted with regex: {file_content}")
            return file_content
        else:
            # Try alternate regex patterns as a last resort
            doc_id_match = re.search(r'id=([^"&\s]+)', content)
            if doc_id_match:
                file_content = {
                    'doc_id': doc_id_match.group(1),
                    'url': f"https://docs.google.com/document/d/{doc_id_match.group(1)}/edit"
                }
                if debug_mode:
                    print(f"Debug - Extracted with alt regex: {file_content}")
                return file_content
            else:
                if debug_mode:
                    print(f"Debug - All regex extraction attempts failed")
                raise Exception("Could not extract doc_id")


def get_gdrive_info(file_path: str) -> Optional[Dict]:
    """
    Extract document ID and resource URL from a .gdoc or .gsheet file.
    
    Args:
        file_path: Path to the Google Drive file (.gdoc or .gsheet)
        
    Returns:
        Dictionary containing id, url, name, and type of the document
        or None if extraction fails
    """
    filename = os.path.basename(file_path)
    debug_mode = (filename == "Roadmap.gdoc")
    
    if debug_mode:
        print(f"Debug - Processing file: {filename}")
    
    try:
        # Read file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        if debug_mode:
            print(f"Debug - Raw file content length: {len(content)}")
            print(f"Debug - First 50 chars: {repr(content[:50])}")

        # Process and clean file content
        clean_content = _clean_file_content(content, debug_mode)

        # Extract document info from content
        file_content = _extract_document_info(clean_content, debug_mode)
            
        # Get document ID
        doc_id = file_content.get('doc_id')
        if not doc_id and 'resourceid' in file_content:
            doc_id = file_content.get('resourceid')
            if debug_mode:
                print(f"Debug - Found resourceid instead of doc_id: {doc_id}")
        
        if debug_mode:
            print(f"Debug - Final doc_id value: {doc_id}")
            print(f"Debug - File content after processing: {file_content}")

        # Determine file type based on extension
        file_type = ""
        if file_path.endswith('.gdoc'):
            file_type = "document"
        elif file_path.endswith('.gsheet'):
            file_type = "spreadsheet"

        return {
            'id': doc_id,
            'url': file_content.get('url', ''),
            'name': os.path.splitext(os.path.basename(file_path))[0],
            'type': file_type
        }
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error parsing {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
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


def export_gdoc_to_docx(service, doc_id: str, output_path: str) -> bool:
    """Export a Google Document to DOCX format using Drive API."""
    try:
        request = service.files().export_media(
            fileId=doc_id, 
            mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        with open(output_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%")
        
        return True
    except Exception as e:
        print(f"Error exporting document {doc_id}: {e}")
        return False


def export_gsheet_to_csv(service, sheet_id: str, output_path: str) -> bool:
    """Export a Google Sheet to CSV format using Drive API."""
    try:
        request = service.files().export_media(
            fileId=sheet_id, 
            mimeType='text/csv'
        )
        
        with open(output_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%")
        
        return True
    except Exception as e:
        print(f"Error exporting spreadsheet {sheet_id}: {e}")
        return False


def convert_docx_to_markdown(docx_path: str, md_path: str) -> bool:
    """Convert DOCX file to Markdown using Pandoc."""
    try:
        # Check if pandoc is installed
        try:
            subprocess.run(['pandoc', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Pandoc is not installed or not in PATH")
            print("Please install Pandoc: https://pandoc.org/installing.html")
            return False
        
        # Run pandoc to convert DOCX to Markdown
        result = subprocess.run(
            ['pandoc', docx_path, '-f', 'docx', '-t', 'markdown', '-o', md_path],
            check=True,
            capture_output=True
        )
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {docx_path} to Markdown: {e}")
        print(f"Pandoc stderr: {e.stderr.decode()}")
        return False


def sanitize_filename(filename: str) -> str:
    """Create a sanitized filename (remove invalid chars)."""
    return ''.join(c for c in filename if c.isalnum() or c in '._- ')


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
        print(f"Error adding frontmatter to {md_path}: {e}")
        return False


def process_gdoc_file(service, file_path: str, keep_intermediates: bool = False, dry_run: bool = False) -> bool:
    """Process a single Google Doc file and convert to Markdown."""
    gdoc_info = get_gdrive_info(file_path)
    if not gdoc_info or not gdoc_info['id'] or gdoc_info['type'] != "document":
        print(f"Could not extract document ID from {file_path} or not a Google Doc")
        return False
    
    doc_id = gdoc_info['id']
    doc_name = gdoc_info['name']
    
    # Create sanitized filename
    safe_name = sanitize_filename(doc_name)
    
    # Place markdown file in the same directory as the .gdoc file
    md_filename = os.path.join(os.path.dirname(file_path), f"{safe_name}.md")
    
    print(f"Processing Google Doc: {doc_name} (ID: {doc_id})")
    print(f"Output file: {md_filename}")
    
    if dry_run:
        print(f"Would convert: {file_path} -> {md_filename}")
        return True
    
    # Create intermediate directory if needed
    final_docx_path = None
    if keep_intermediates:
        intermediates_dir = os.path.join(os.path.dirname(file_path), 'intermediates')
        os.makedirs(intermediates_dir, exist_ok=True)
        final_docx_path = os.path.join(intermediates_dir, f"{safe_name}.docx")
    
    # Export and convert
    if keep_intermediates:
        # Export directly to the final docx location
        docx_path = final_docx_path
        if not export_gdoc_to_docx(service, doc_id, docx_path):
            return False
            
        # Convert DOCX to Markdown
        success = convert_docx_to_markdown(docx_path, md_filename)
        if not success:
            return False
            
    else:
        # Use temporary directory for DOCX export
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = os.path.join(temp_dir, f"{safe_name}.docx")
            if not export_gdoc_to_docx(service, doc_id, docx_path):
                return False
            
            # Convert DOCX to Markdown
            success = convert_docx_to_markdown(docx_path, md_filename)
            if not success:
                return False
    
    print(f"Successfully converted to {md_filename}")
    
    # Add YAML frontmatter with metadata
    add_frontmatter_to_markdown(
        md_filename, 
        doc_name, 
        doc_id, 
        final_docx_path if keep_intermediates else None
    )
    
    print(f"Added metadata frontmatter to {md_filename}")
    if keep_intermediates and final_docx_path:
        print(f"Kept DOCX file: {final_docx_path}")
    
    return True


def process_gsheet_file(service, file_path: str, keep_intermediates: bool = False, dry_run: bool = False) -> bool:
    """Process a single Google Sheet file and export to CSV format."""
    gsheet_info = get_gdrive_info(file_path)
    if not gsheet_info or not gsheet_info['id'] or gsheet_info['type'] != "spreadsheet":
        print(f"Could not extract spreadsheet ID from {file_path} or not a Google Sheet")
        return False
    
    sheet_id = gsheet_info['id']
    sheet_name = gsheet_info['name']
    
    # Create sanitized filename
    safe_name = sanitize_filename(sheet_name)
    
    # Place CSV file in the same directory as the .gsheet file
    csv_filename = os.path.join(os.path.dirname(file_path), f"{safe_name}.csv")
    
    print(f"Processing Google Sheet: {sheet_name} (ID: {sheet_id})")
    print(f"Output file: {csv_filename}")
    
    if dry_run:
        print(f"Would convert: {file_path} -> {csv_filename}")
        return True
    
    # Export to CSV
    if not export_gsheet_to_csv(service, sheet_id, csv_filename):
        return False
    
    print(f"Successfully exported to {csv_filename}")
    
    # Nothing additional needed for keep_intermediates as 
    # CSV is already the final output format
    
    return True


def main():
    """Main function to run the Google Drive to Markdown/CSV migration."""
    import argparse

    # Parse command-line arguments
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

    args = parser.parse_args()

    source_dir = args.source_dir

    # Validate directories
    if not os.path.isdir(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist")
        sys.exit(1)

    # Check if Pandoc is installed (only needed for gdoc conversion)
    if not args.gsheet_only:
        try:
            subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
            print("Pandoc is installed and working correctly")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Pandoc is not installed or not in PATH")
            print("Please install Pandoc: https://pandoc.org/installing.html")
            sys.exit(1)

    # Authenticate with Google Drive API (skip if dry-run)
    service = None
    if not args.dry_run:
        print("Authenticating with Google Drive API...")
        try:
            credentials = authenticate()
            service = build('drive', 'v3', credentials=credentials)
            print("Authentication successful!")
        except Exception as e:
            print(f"Authentication failed: {e}")
            print("Please check your credentials.json file and try again.")
            sys.exit(1)
    else:
        print("Dry run mode - skipping authentication with Google API")

    # Find all .gdoc and .gsheet files
    print(f"Finding Google Drive files in {source_dir}...")
    gdrive_files = find_gdrive_files(source_dir, args.gdoc_only, args.gsheet_only)

    if not gdrive_files:
        print("No Google Drive files found in the specified directory")
        sys.exit(0)

    # Apply limit if specified
    if args.limit and 0 < args.limit < len(gdrive_files):
        print(f"Limiting to {args.limit} files (of {len(gdrive_files)} found)")
        gdrive_files = gdrive_files[:args.limit]
    else:
        print(f"Found {len(gdrive_files)} Google Drive files")

    # Process each file
    success_count = 0
    skip_count = 0
    error_count = 0
    gdocs_processed = 0
    gsheets_processed = 0

    for i, file_path in enumerate(gdrive_files, 1):
        file_type = "Google Doc" if file_path.endswith('.gdoc') else "Google Sheet"
        print(f"\nProcessing file {i} of {len(gdrive_files)}: {os.path.basename(file_path)} ({file_type})")

        try:
            # Get output path
            file_info = get_gdrive_info(file_path)
            if not file_info:
                print(f"Could not extract info from {file_path}")
                error_count += 1
                continue

            # Determine output file path
            output_ext = ".md" if file_path.endswith('.gdoc') else ".csv"
            safe_name = sanitize_filename(file_info['name'])
            output_path = os.path.join(os.path.dirname(file_path), f"{safe_name}{output_ext}")

            # Skip if file exists and --skip-existing is specified
            if args.skip_existing and os.path.exists(output_path):
                print(f"Skipping {file_path} (output file already exists)")
                skip_count += 1
                continue

            # Process the file based on its type
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
            print(f"Error processing {file_path}: {e}")
            error_count += 1

    # Print summary
    print(f"\nConversion Summary:")
    if args.dry_run:
        print(f"DRY RUN - No files were actually converted")
    print(f"Total files found: {len(gdrive_files)}")
    if args.dry_run:
        print(f"Would convert: {success_count}")
    else:
        print(f"Successfully converted: {success_count}")
        print(f"  - Google Docs processed: {gdocs_processed}")
        print(f"  - Google Sheets processed: {gsheets_processed}")
    if skip_count > 0:
        print(f"Skipped (already exist): {skip_count}")
    print(f"Failed: {error_count}")

    if success_count > 0 and not args.dry_run:
        print(f"\nFiles have been saved next to their Google Drive counterparts")
        if args.keep_intermediates:
            print(f"Intermediate files have been saved in 'intermediates/' subdirectories")
        print("Done!")
    elif args.dry_run:
        print(f"\nTo perform the actual conversion, run the command without --dry-run")


if __name__ == "__main__":
    main()