#!/usr/bin/env node
/**
 * Claude Code Plugin Test using node-pty
 *
 * This script uses node-pty to create a pseudo-terminal (PTY) and test
 * the Claude Code plugin installation by:
 * 1. Spawning Claude Code with --plugin-dir flag
 * 2. Sending /plugin command
 * 3. Verifying "amplihack" appears in the output
 *
 * node-pty provides a real PTY, allowing Claude Code to detect it's running
 * in a terminal and enabling proper TUI behavior.
 */

const pty = require('node-pty');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Configuration
const HOME = os.homedir();
const PLUGIN_DIR = path.join(HOME, '.amplihack', '.claude');
const TIMEOUT = 60000; // 60 seconds
const EVIDENCE_DIR = path.join(__dirname, 'evidence', `pty-test-${Date.now()}`);

// Create evidence directory
if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

// Colors for output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function log(msg) {
  console.log(`${colors.blue}[${new Date().toLocaleTimeString()}]${colors.reset} ${msg}`);
}

function logSuccess(msg) {
  console.log(`${colors.green}✓${colors.reset} ${msg}`);
}

function logError(msg) {
  console.log(`${colors.red}✗${colors.reset} ${msg}`);
}

function logWarning(msg) {
  console.log(`${colors.yellow}⚠${colors.reset} ${msg}`);
}

// Main test function
async function testClaudeCodePlugin() {
  log('Starting Claude Code Plugin PTY Test');

  // Check prerequisites
  if (!fs.existsSync(PLUGIN_DIR)) {
    logError(`Plugin directory not found: ${PLUGIN_DIR}`);
    logError('Run: uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack --help');
    process.exit(1);
  }

  logSuccess(`Plugin directory found: ${PLUGIN_DIR}`);

  // Check AMPLIHACK.md
  const amplihackMd = path.join(PLUGIN_DIR, 'AMPLIHACK.md');
  if (!fs.existsSync(amplihackMd)) {
    logError('AMPLIHACK.md not found');
    process.exit(1);
  }

  const stats = fs.statSync(amplihackMd);
  logSuccess(`AMPLIHACK.md exists (${(stats.size / 1024).toFixed(1)}KB)`);

  // Create PTY with Claude Code
  log('Spawning Claude Code with PTY...');

  const ptyProcess = pty.spawn('claude', [
    '--plugin-dir', PLUGIN_DIR,
    '--add-dir', '/tmp'
  ], {
    name: 'xterm-256color',
    cols: 120,
    rows: 40,
    cwd: '/tmp',
    env: {
      ...process.env,
      TERM: 'xterm-256color',
      COLORTERM: 'truecolor'
    }
  });

  logSuccess(`PTY spawned (PID: ${ptyProcess.pid})`);

  // Output buffer
  let outputBuffer = '';
  let testPassed = false;
  let testComplete = false;

  // Set up timeout
  const timeoutHandle = setTimeout(() => {
    if (!testComplete) {
      logError('Test timeout after 60 seconds');
      ptyProcess.kill();
      saveEvidence(outputBuffer, false);
      process.exit(1);
    }
  }, TIMEOUT);

  // Capture output
  ptyProcess.onData((data) => {
    outputBuffer += data;
    process.stdout.write(data); // Echo to console

    // Check if amplihack appears in output
    if (data.includes('amplihack')) {
      logSuccess('Found "amplihack" in output!');
      testPassed = true;
    }
  });

  // Handle exit
  ptyProcess.onExit(({ exitCode, signal }) => {
    clearTimeout(timeoutHandle);
    testComplete = true;

    log(`Process exited (code: ${exitCode}, signal: ${signal})`);

    saveEvidence(outputBuffer, testPassed);

    if (testPassed) {
      console.log('\n' + '='.repeat(50));
      logSuccess('TEST PASSED: amplihack plugin detected!');
      console.log('='.repeat(50) + '\n');
      process.exit(0);
    } else {
      console.log('\n' + '='.repeat(50));
      logError('TEST FAILED: amplihack not detected');
      console.log('='.repeat(50) + '\n');
      process.exit(1);
    }
  });

  // Wait for Claude Code to initialize
  log('Waiting for Claude Code to initialize...');
  await sleep(3000);

  // Claude Code asks for permission to work in /tmp - press Enter to confirm
  log('Confirming folder permission...');
  ptyProcess.write('\r'); // Press Enter

  // Wait for Claude Code to fully load
  await sleep(3000);

  // Send /plugin command
  log('Sending /plugin command...');
  ptyProcess.write('/plugin');

  // Wait for autocomplete to show
  await sleep(1000);

  // Press Enter to execute
  log('Executing /plugin command...');
  ptyProcess.write('\r');

  // Wait for Plugins screen to load
  await sleep(3000);

  // Navigate to "Installed" tab (press Tab or Right arrow)
  log('Navigating to Installed tab...');
  ptyProcess.write('\t'); // Tab key to switch tabs

  // Wait for Installed tab to load
  await sleep(3000);

  // Try to exit gracefully
  log('Attempting graceful exit...');
  ptyProcess.write('\x04'); // Ctrl+D

  await sleep(2000);

  // Force kill if still running
  if (!testComplete) {
    log('Force killing process...');
    ptyProcess.kill();
  }
}

function saveEvidence(output, passed) {
  const evidenceFile = path.join(EVIDENCE_DIR, 'output.txt');
  const reportFile = path.join(EVIDENCE_DIR, 'REPORT.md');

  // Save raw output
  fs.writeFileSync(evidenceFile, output);
  logSuccess(`Evidence saved: ${evidenceFile}`);

  // Generate report
  const report = `# Claude Code Plugin PTY Test Report

**Date**: ${new Date().toISOString()}
**Result**: ${passed ? '✅ PASSED' : '❌ FAILED'}

## Test Details

- **Plugin Directory**: ${PLUGIN_DIR}
- **PTY Used**: node-pty (real pseudo-terminal)
- **Command**: \`claude --plugin-dir ${PLUGIN_DIR} --add-dir /tmp\`

## Test Steps

1. ✓ Verified plugin directory exists
2. ✓ Verified AMPLIHACK.md exists
3. ✓ Spawned Claude Code with PTY
4. ✓ Sent /plugin command
5. ${passed ? '✓' : '✗'} Detected "amplihack" in output

## Evidence

See \`output.txt\` for complete terminal output.

## Search for "amplihack"

${passed ? 'Found in output ✓' : 'NOT found in output ✗'}

---
*Generated by test-claude-plugin-pty.js*
`;

  fs.writeFileSync(reportFile, report);
  logSuccess(`Report saved: ${reportFile}`);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Run test
testClaudeCodePlugin().catch((error) => {
  logError(`Test failed with error: ${error.message}`);
  console.error(error);
  process.exit(1);
});
