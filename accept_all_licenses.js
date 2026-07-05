const { spawn } = require('child_process');
const sdkManager = spawn('D:\\AndroidSDK\\cmdline-tools\\latest\\bin\\sdkmanager.bat', ['--licenses'], { shell: true });

sdkManager.stdout.on('data', (data) => {
    const out = data.toString();
    process.stdout.write(out);
    if (out.includes('(y/N)')) {
        sdkManager.stdin.write('y\n');
    }
});

sdkManager.stderr.on('data', (data) => {
    process.stderr.write(data.toString());
});

sdkManager.on('close', (code) => {
    console.log(`sdkmanager exited with code ${code}`);
});
