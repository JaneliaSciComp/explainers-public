// Screenshot every <figure> of each concept-unit page, light and dark, at 1280 px, one PNG per figure:
// <out>/<page>-fig<N>-light.png and -dark.png. Reviewers read figures at full size this way.
// --sel <css> picks other elements (default 'figure'), e.g. '#learn figure, #learn canvas'.
// Usage: node figshots.mjs <out dir> [--port N] [--only id1,id2] [--dir <folder of pages>]
//   --port  Chrome's debugging port (default 9350); give parallel runs different ports.
//   --only  shoot only these pages (page names without .html).
//   --dir   the folder of pages (default: units/ in this repo).
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const port = Number(opt('--port', '9350'));
const only = opt('--only', '');
const sel = opt('--sel', 'figure');
const dir = resolve(opt('--dir', join(dirname(fileURLToPath(import.meta.url)), '..', 'units')));
const outDir = args[0] ? resolve(args[0]) : null;
if (!outDir || args.length !== 1) {
  console.error('usage: node figshots.mjs <out dir> [--port N] [--only id1,id2] [--dir <folder>] [--sel <css>]');
  process.exit(2);
}
mkdirSync(outDir, { recursive: true });
let pages = readdirSync(dir).filter(f => f.endsWith('.html') && f !== '_template.html').sort();
if (only) { const want = new Set(only.split(',').map(s => s.trim() + '.html')); pages = pages.filter(f => want.has(f)); }
if (!pages.length) { console.error('no pages to check in ' + dir); process.exit(2); }

const profile = join(outDir, '.chrome-profile');
const chrome = spawn('google-chrome', ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--autoplay-policy=no-user-gesture-required', 'about:blank'],
  { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const quit = code => { try { chrome.kill(); } catch (e) { /* already gone */ } try { rmSync(profile, { recursive: true, force: true }); } catch (e) { /* keep */ } process.exit(code); };
let targets = null;
for (let i = 0; i < 75 && !targets; i++) {
  await sleep(200);
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); } catch (e) { /* not up yet */ }
}
if (!targets) { console.error(`Chrome did not start on port ${port}`); quit(2); }
const target = targets.find(t => t.type === 'page');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0;
const pending = new Map(), events = [];
let logs = [];
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails;
    logs.push('exception: ' + (d.exception?.description || d.text) + (d.url ? ` (${d.url}:${d.lineNumber + 1})` : ''));
  }
  if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'assert'))
    logs.push('console.' + m.params.type + ': ' + m.params.args.map(a => a.value ?? a.description).join(' '));
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
    const e = m.params.entry;
    // Google Fonts may be unreachable offline; that is the network, not the page.
    if (!/fonts\.(googleapis|gstatic)\.com/.test(e.url || '')) logs.push('log: ' + e.text + (e.url ? ' ' + e.url : ''));
  }
  if (m.method === 'Page.loadEventFired') events.push('load');
});
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJS = async expr => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) throw new Error('evaluate failed: ' + JSON.stringify(r.result.exceptionDetails.exception?.description));
  return r.result?.result?.value;
};
await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');

async function load(file, width, dark) {
  await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: dark ? 'dark' : 'light' }] });
  events.length = 0;
  await send('Page.navigate', { url: 'file://' + join(dir, file) });
  for (let i = 0; i < 100 && !events.includes('load'); i++) await sleep(100);
  // let deferred scripts, fonts and media metadata settle
  await evalJS(`(async () => {
    try { await Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 3000))]); } catch (e) {}
    const vids = [...document.querySelectorAll('video')];
    await Promise.race([Promise.all(vids.map(v => v.readyState >= 1 || v.error ? 0 : new Promise(r => {
      v.addEventListener('loadedmetadata', r, { once: true }); v.addEventListener('error', r, { once: true });
      const s = v.querySelector('source:last-of-type'); if (s) s.addEventListener('error', r, { once: true });
    }))), new Promise(r => setTimeout(r, 4000))]);
    await new Promise(r => setTimeout(r, 300));
    return true;
  })()`);
}


const FIGS = `(() => [...document.querySelectorAll(${JSON.stringify(sel)})].map((f, i) => { const r = f.getBoundingClientRect();
  return { i: i + 1, x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; }))()`;
let n = 0;
for (const file of pages) {
  const base = file.replace(/\.html$/, '');
  for (const dark of [false, true]) {
    await load(file, 1280, dark);
    const figs = await evalJS(FIGS);
    for (const f of figs) {
      if (f.w < 2 || f.h < 2) continue;
      const pad = 8;
      const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
        clip: { x: Math.max(0, f.x - pad), y: Math.max(0, f.y - pad), width: f.w + 2 * pad, height: Math.min(f.h + 2 * pad, 2400), scale: 1 } });
      writeFileSync(join(outDir, `${base}-fig${f.i}-${dark ? 'dark' : 'light'}.png`), Buffer.from(r.result.data, 'base64'));
      n++;
    }
  }
}
console.log(`figshots: ${pages.length} pages, ${n} figure shots in ${outDir}`);
ws.close();
quit(0);
