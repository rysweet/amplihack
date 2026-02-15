// Scrape authenticated site via Edge CDP - runs on Windows side
// Usage: cmd.exe /c "cd C:\Temp && node scrape_site.mjs <output-dir> [start-url]"
// Prerequisites: npm install ws (on Windows side)
import http from 'http';
import fs from 'fs';

const OUTPUT_DIR = process.argv[2] || 'C:\\Temp\\scrape-output';
const START_URL = process.argv[3] || null;
const DEBUG_PORT = 9222;
const DELAY_MS = 2000;

fs.mkdirSync(OUTPUT_DIR, { recursive: true });
fs.mkdirSync(`${OUTPUT_DIR}\\pages`, { recursive: true });
fs.mkdirSync(`${OUTPUT_DIR}\\followed`, { recursive: true });

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

function cdpSend(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1000000);
    const timeout = setTimeout(() => {
      ws.removeListener('message', handler);
      reject(new Error(`CDP timeout: ${method}`));
    }, 30000);
    const handler = data => {
      const parsed = JSON.parse(data.toString());
      if (parsed.id === id) {
        clearTimeout(timeout);
        ws.removeListener('message', handler);
        parsed.error ? reject(new Error(parsed.error.message)) : resolve(parsed.result);
      }
    };
    ws.on('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

function urlToFilename(url) {
  return url.replace(/https?:\/\//, '').replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 150);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function scrapePage(ws, url, outputPath) {
  try {
    await cdpSend(ws, 'Page.navigate', { url });
    await sleep(3000);
    await cdpSend(ws, 'Runtime.evaluate', {
      expression: 'new Promise(r => setTimeout(r, 2000))',
      awaitPromise: true,
    });
  } catch (e) {
    console.log(`  Navigation error: ${e.message}`);
    return null;
  }

  let currentUrl, title, text, html;
  try {
    currentUrl = (await cdpSend(ws, 'Runtime.evaluate', {
      expression: 'window.location.href', returnByValue: true,
    })).result.value;
  } catch { currentUrl = url; }

  try {
    title = (await cdpSend(ws, 'Runtime.evaluate', {
      expression: 'document.title', returnByValue: true,
    })).result.value;
  } catch { title = ''; }

  try {
    text = (await cdpSend(ws, 'Runtime.evaluate', {
      expression: `(function() {
        const m = document.querySelector('main, article, [role="main"], .content');
        return m ? m.innerText : document.body.innerText;
      })()`,
      returnByValue: true,
    })).result.value;
  } catch { text = ''; }

  try {
    html = (await cdpSend(ws, 'Runtime.evaluate', {
      expression: 'document.documentElement.outerHTML', returnByValue: true,
    })).result.value;
  } catch { html = ''; }

  let pageLinks = [];
  try {
    const raw = (await cdpSend(ws, 'Runtime.evaluate', {
      expression: `JSON.stringify((function() {
        const r = [], seen = new Set();
        const c = document.querySelector('main, article, [role="main"], .content') || document.body;
        c.querySelectorAll('a[href]').forEach(el => {
          const h = el.href, t = el.textContent.trim();
          if (h && t && !seen.has(h) && t.length < 300 && h.startsWith('http')) { seen.add(h); r.push({href:h,text:t}); }
        });
        return r;
      })())`,
      returnByValue: true,
    })).result.value;
    pageLinks = JSON.parse(raw);
  } catch {}

  const base = urlToFilename(url);
  fs.writeFileSync(`${outputPath}\\${base}.txt`, `# ${title}\nURL: ${currentUrl}\n\n${text}`);
  fs.writeFileSync(`${outputPath}\\${base}.html`, html);
  fs.writeFileSync(`${outputPath}\\${base}_links.json`, JSON.stringify(pageLinks, null, 2));

  return { url: currentUrl, title, textLength: text.length, linkCount: pageLinks.length, links: pageLinks };
}

async function main() {
  console.log('Connecting to Edge CDP...');
  const pagesJson = await httpGet(`http://localhost:${DEBUG_PORT}/json/list`);
  const targets = JSON.parse(pagesJson);
  console.log(`Found ${targets.length} page(s)`);

  const target = START_URL
    ? targets.find(p => p.url.includes(new URL(START_URL).hostname)) || targets[0]
    : targets[0];

  const { WebSocket } = await import('ws');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.on('open', resolve); ws.on('error', reject); });
  console.log(`Connected to: ${target.title}`);

  await cdpSend(ws, 'Page.enable');

  // Phase 1: Extract nav links from current page
  const navRaw = (await cdpSend(ws, 'Runtime.evaluate', {
    expression: `JSON.stringify((function() {
      const r = [], seen = new Set();
      const sels = ['nav a[href]','.sidebar a[href]','aside a[href]','[role="navigation"] a[href]'];
      for (const s of sels) document.querySelectorAll(s).forEach(el => {
        const h=el.href, t=el.textContent.trim();
        if (h&&t&&!seen.has(h)&&t.length<300) { seen.add(h); r.push({href:h,text:t}); }
      });
      return r;
    })())`,
    returnByValue: true,
  })).result.value;
  const navLinks = JSON.parse(navRaw);
  fs.writeFileSync(`${OUTPUT_DIR}\\nav-links.json`, JSON.stringify(navLinks, null, 2));

  // Determine domain for scoping
  const domain = target.url ? new URL(target.url).hostname : '';

  // Filter to actual pages on same domain
  const sidebarPages = [...new Set(navLinks.filter(l => !l.href.includes('#') && l.href.includes(domain)).map(l => l.href))];
  console.log(`\n=== Phase 1: Scraping ${sidebarPages.length} nav pages ===\n`);

  const sidebarResults = [];
  const followSet = new Set();

  for (let i = 0; i < sidebarPages.length; i++) {
    const url = sidebarPages[i];
    console.log(`[${i + 1}/${sidebarPages.length}] ${url}`);
    const result = await scrapePage(ws, url, `${OUTPUT_DIR}\\pages`);
    if (result) {
      sidebarResults.push(result);
      console.log(`  ${result.title} | ${result.textLength} chars | ${result.linkCount} links`);
      result.links.filter(l => l.href.includes(domain) && !l.href.includes('#')).forEach(l => followSet.add(l.href));
    }
    await sleep(DELAY_MS);
  }

  // Phase 2: Follow links one level deep
  const sidebarSet = new Set(sidebarPages);
  const followLinks = [...followSet].filter(u => !sidebarSet.has(u));
  console.log(`\n=== Phase 2: Following ${followLinks.length} linked pages ===\n`);

  const followResults = [];
  for (let i = 0; i < followLinks.length; i++) {
    const url = followLinks[i];
    console.log(`[${i + 1}/${followLinks.length}] ${url}`);
    const result = await scrapePage(ws, url, `${OUTPUT_DIR}\\followed`);
    if (result) {
      followResults.push(result);
      console.log(`  ${result.title} | ${result.textLength} chars`);
    }
    await sleep(DELAY_MS);
  }

  fs.writeFileSync(`${OUTPUT_DIR}\\scrape-summary.json`, JSON.stringify({
    timestamp: new Date().toISOString(),
    sidebarPages: sidebarResults.map(r => ({ url: r.url, title: r.title, textLength: r.textLength })),
    followedPages: followResults.map(r => ({ url: r.url, title: r.title, textLength: r.textLength })),
    totalSidebarPages: sidebarResults.length,
    totalFollowedPages: followResults.length,
  }, null, 2));

  ws.close();
  console.log(`\n=== COMPLETE: ${sidebarResults.length} nav + ${followResults.length} followed = ${sidebarResults.length + followResults.length} pages ===`);
  console.log(`Output: ${OUTPUT_DIR}`);
}

main().catch(e => { console.error(e); process.exit(1); });
