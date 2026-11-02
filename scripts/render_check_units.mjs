// Render every concept-unit page in headless Chrome over CDP (no npm packages) and report problems:
// console errors and uncaught exceptions, sideways overflow, broken images, videos and caption tracks.
// Saves screenshots of each page: light at 1280 px (answers opened), dark at 1280 px, and light at 390 px.
//
// Usage: node render_check_units.mjs <out dir> [--port N] [--only id1,id2] [--dir <folder of pages>]
//   --port  Chrome's debugging port (default 9334); give parallel runs different ports.
//   --only  check only these pages (unit ids, or "index").
//   --dir   the folder to check (default: units/ in this repo).
// Exit status 1 means at least one problem.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const port = Number(opt('--port', '9334'));
const only = opt('--only', '');
const dir = resolve(opt('--dir', join(dirname(fileURLToPath(import.meta.url)), '..', 'units')));
const outDir = args[0] ? resolve(args[0]) : null;
if (!outDir || args.length !== 1) {
  console.error('usage: node render_check_units.mjs <out dir> [--port N] [--only id1,id2] [--dir <folder>]');
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

async function screenshot(name) {
  const h = await evalJS('Math.ceil(document.documentElement.scrollHeight)');
  const w = await evalJS('document.documentElement.clientWidth');
  const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: w, height: Math.min(h, 16000), scale: 1 } });
  writeFileSync(join(outDir, name + '.png'), Buffer.from(r.result.data, 'base64'));
}

const MEDIA_FACTS = `(() => {
  const out = [];
  document.querySelectorAll('img').forEach(i => { if (!i.complete || i.naturalWidth === 0) out.push('broken image: ' + (i.getAttribute('src') || '(no src)')); });
  document.querySelectorAll('video').forEach(v => {
    const name = v.currentSrc || v.getAttribute('src') || (v.querySelector('source') || {}).src || '(no source)';
    if (v.error) out.push('video error ' + v.error.code + ': ' + name);
    else if (v.networkState === 3) out.push('video has no usable source: ' + name);
    else if (v.readyState < 1) out.push('video metadata did not load: ' + name);
    else if (!v.videoWidth) out.push('video has no picture: ' + name);
    [...v.textTracks].forEach((t, k) => { if (t.mode === 'disabled') t.mode = 'hidden'; });
  });
  return out;
})()`;
const TRACK_FACTS = `(() => [...document.querySelectorAll('video track')].filter(t => t.readyState !== 2)
  .map(t => 'caption track ' + (t.readyState === 3 ? 'failed to load' : 'did not load') + ': ' + (t.getAttribute('src') || t.src).slice(0, 80)
  + (location.protocol === 'file:' && !t.src.startsWith('blob:') ? ' (Chrome blocks <track src> over file://; use data-vtt, see README)' : '')))()`;
const OVERFLOW = `(() => {
  const vw = document.documentElement.clientWidth, sw = document.documentElement.scrollWidth;
  const scrollsInside = e => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
    const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return true; } return false; };
  const wide = [...document.body.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect();
    return r.width > 0 && (r.right > vw + 1 || r.left < -1) && !scrollsInside(e); })
    .slice(0, 6).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].join('.') : ''));
  return { vw, sw, wide };
})()`;

let failures = 0;
for (const file of pages) {
  const base = file.replace(/\.html$/, '');
  const problems = [];
  logs = [];
  await load(file, 1280, false);
  problems.push(...await evalJS(MEDIA_FACTS));
  await sleep(500);
  problems.push(...await evalJS(TRACK_FACTS));
  const wideDesk = await evalJS(OVERFLOW);
  if (wideDesk.sw > wideDesk.vw) problems.push(`scrolls sideways at 1280 px (page is ${wideDesk.sw} px wide): ${wideDesk.wide.join(', ')}`);
  await evalJS(`document.querySelectorAll('details').forEach(d => { d.open = true; }); true`);
  await sleep(150);
  await screenshot(`${base}-1280`);
  await load(file, 1280, true);
  await screenshot(`${base}-1280-dark`);
  await load(file, 390, false);
  const phone = await evalJS(OVERFLOW);
  if (phone.sw > phone.vw) problems.push(`scrolls sideways at 390 px (page is ${phone.sw} px wide): ${phone.wide.join(', ')}`);
  else if (phone.wide.length) problems.push(`elements stick out past the 390 px screen: ${phone.wide.join(', ')}`);
  await screenshot(`${base}-390`);
  problems.push(...[...new Set(logs)]);
  if (problems.length) { failures++; console.log(`FAIL ${file}`); problems.forEach(p => console.log('  ' + p)); }
  else console.log(`ok   ${file}`);
}
console.log(`render_check_units: ${pages.length} pages, ${failures} with problems; screenshots in ${outDir}`);
ws.close();
quit(failures ? 1 : 0);
