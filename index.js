const { PythonShell } = require('python-shell');
const path = require('path');

/**
 * Run the gdrive_to_md.py script with the provided arguments
 * @param {string[]} args - Command line arguments to pass to the Python script
 * @returns {Promise<void>}
 */
function runGDriveToMd(args = []) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, 'gdrive_to_md.py');
    
    const options = {
      mode: 'text',
      pythonPath: 'python3',
      pythonOptions: ['-u'], // Unbuffered output
      scriptPath: __dirname,
      args: args
    };

    const pyshell = new PythonShell(scriptPath, options);
    
    // Handle output from Python script
    pyshell.on('message', (message) => {
      console.log(message);
    });
    
    // Handle errors
    pyshell.on('stderr', (stderr) => {
      console.error(stderr);
    });
    
    // End of script
    pyshell.end((err) => {
      if (err) {
        reject(err);
      } else {
        resolve();
      }
    });
  });
}

module.exports = { runGDriveToMd };