#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const { Command } = require('commander');

const program = new Command();

program
  .name('gdoc-to-md')
  .description('Convert Google Drive documents to Markdown and CSV')
  .version('1.0.0')
  .argument('<source_dir>', 'Directory containing .gdoc and .gsheet files')
  .option('--limit <number>', 'Limit the number of files to process', parseInt)
  .option('--skip-existing', 'Skip files that already exist')
  .option('--dry-run', 'Show what would be done without converting')
  .option('--keep-intermediates', 'Keep intermediate DOCX files')
  .option('--gdoc-only', 'Process only Google Docs files')
  .option('--gsheet-only', 'Process only Google Sheets files')
  .action((sourceDir, options) => {
    // Build Python script arguments
    const pythonScript = path.join(__dirname, '..', 'gdrive_to_md.py');
    const args = [pythonScript, sourceDir];

    if (options.limit) args.push('--limit', options.limit);
    if (options.skipExisting) args.push('--skip-existing');
    if (options.dryRun) args.push('--dry-run');
    if (options.keepIntermediates) args.push('--keep-intermediates');
    if (options.gdocOnly) args.push('--gdoc-only');
    if (options.gsheetOnly) args.push('--gsheet-only');

    // Check for Python
    const checkPython = spawn('python3', ['--version']);
    checkPython.on('error', () => {
      console.error('Error: Python 3 is required but not found in PATH');
      process.exit(1);
    });

    checkPython.on('close', (code) => {
      if (code !== 0) {
        console.error('Error: Python 3 is required but not found in PATH');
        process.exit(1);
      }

      // Run the Python script
      const python = spawn('python3', args, { stdio: 'inherit' });

      python.on('error', (err) => {
        console.error('Failed to start Python script:', err);
        process.exit(1);
      });

      python.on('close', (code) => {
        process.exit(code);
      });
    });
  });

program.parse();