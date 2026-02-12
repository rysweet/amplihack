// Launch Windows Edge with remote debugging from WSL2
// Usage: node launch_edge_debug.mjs <target-url>
import { execSync, spawn } from 'child_process';

const EDGE_PATH = '/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const TARGET_URL = process.argv[2] || 'about:blank';
const DEBUG_PORT = 9222;

// Kill all Edge processes - CRITICAL: existing Edge ignores debug flags
console.log('Closing all Edge instances...');
try {
  execSync('cmd.exe /c "taskkill /F /IM msedge.exe /T" 2>&1', { stdio: 'pipe' });
  console.log('Edge processes terminated.');
} catch (e) {
  console.log('No Edge processes found.');
}

await new Promise(r => setTimeout(r, 3000));

console.log(`Launching Edge with debugging on port ${DEBUG_PORT}...`);
const proc = spawn(EDGE_PATH, [
  `--remote-debugging-port=${DEBUG_PORT}`,
  '--remote-debugging-address=0.0.0.0',
  '--remote-allow-origins=*',
  TARGET_URL,
], { detached: true, stdio: 'ignore' });
proc.unref();

await new Promise(r => setTimeout(r, 5000));

// Verify CDP from Windows side
try {
  const result = execSync(
    `powershell.exe -Command "Invoke-RestMethod -Uri http://localhost:${DEBUG_PORT}/json/version -TimeoutSec 5 | ConvertTo-Json"`,
    { encoding: 'utf8', timeout: 10000 }
  );
  console.log('CDP is running:');
  console.log(result);
  console.log('\nPlease authenticate in Edge, then run the scraper.');
} catch (e) {
  console.error('CDP not accessible. Edge may need more time to start.');
  process.exit(1);
}
