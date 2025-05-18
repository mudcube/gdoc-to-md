#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('📦 Installing Python dependencies for @goobits/gdoc-to-md...');

try {
  // Check if Python is installed
  try {
    execSync('python3 --version', { stdio: 'ignore' });
  } catch (e) {
    console.error('❌ Error: Python 3 is not installed or not in PATH');
    console.error('Please install Python 3.x before using this package');
    process.exit(1);
  }

  // Install Python dependencies
  execSync('pip install -r requirements.txt', { stdio: 'inherit' });
  console.log('✅ Python dependencies installed successfully');

  // Check for Pandoc
  try {
    execSync('pandoc --version', { stdio: 'ignore' });
    console.log('✅ Pandoc is installed');
  } catch (e) {
    console.warn('⚠️  Warning: Pandoc is not installed or not in PATH');
    console.warn('Pandoc is required for converting Google Docs to Markdown');
    console.warn('Please install Pandoc: https://pandoc.org/installing.html');
  }

  // Check for credentials.json
  const credsPath = path.join(process.cwd(), 'credentials.json');
  if (!fs.existsSync(credsPath)) {
    console.warn('\n⚠️  Important: Google API credentials not found');
    console.warn('You need to set up Google Drive API credentials:');
    console.warn('1. Go to Google Cloud Console');
    console.warn('2. Enable Google Drive API');
    console.warn('3. Create OAuth 2.0 credentials');
    console.warn('4. Download and save as credentials.json in your project root');
  }

  console.log('\n✅ Installation complete!');
  console.log('Usage: gdoc-to-md /path/to/google/drive/files');

} catch (error) {
  console.error('❌ Error during installation:', error.message);
  process.exit(1);
}