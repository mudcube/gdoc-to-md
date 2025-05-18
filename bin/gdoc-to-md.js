#!/usr/bin/env node

const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');
const { runGDriveToMd } = require('../index');

// Parse command line arguments
const argv = yargs(hideBin(process.argv))
  .usage('Usage: $0 <source_dir> [options]')
  .positional('source_dir', {
    describe: 'Source directory containing Google Drive files',
    type: 'string'
  })
  .option('gdoc-only', {
    describe: 'Process only Google Docs files',
    type: 'boolean',
    default: false
  })
  .option('gsheet-only', {
    describe: 'Process only Google Sheets files',
    type: 'boolean',
    default: false
  })
  .option('skip-existing', {
    describe: 'Skip files that have already been converted',
    type: 'boolean',
    default: false
  })
  .option('keep-intermediates', {
    describe: 'Keep intermediate DOCX files',
    type: 'boolean',
    default: false
  })
  .option('dry-run', {
    describe: 'Preview what would be converted without actually converting',
    type: 'boolean',
    default: false
  })
  .option('limit', {
    describe: 'Limit the number of files to process',
    type: 'number'
  })
  .demandCommand(1, 'Please provide a source directory')
  .help()
  .argv;

// Convert yargs argv to array format for Python script
const args = [argv._[0]]; // source directory

if (argv.gdocOnly) args.push('--gdoc-only');
if (argv.gsheetOnly) args.push('--gsheet-only');
if (argv.skipExisting) args.push('--skip-existing');
if (argv.keepIntermediates) args.push('--keep-intermediates');
if (argv.dryRun) args.push('--dry-run');
if (argv.limit) args.push('--limit', argv.limit.toString());

// Run the Python script
runGDriveToMd(args)
  .then(() => {
    process.exit(0);
  })
  .catch((error) => {
    console.error('Error:', error);
    process.exit(1);
  });