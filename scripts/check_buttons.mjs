// Press every button on the concept-unit pages in headless Chrome over CDP (no npm packages), and report each
// button after which nothing on the page changed, and each press that raised an error.
//
// Usage: node check_buttons.mjs <out dir> [--port N] [--only id1,id2] [--dir <folder of pages>]
//   --port  Chrome's debugging port (default 9338); give parallel runs different ports.
//   --only  check only these pages (unit ids).
//   --dir   the folder to check (default: units/ in this repo).
// Writes <out dir>/buttons.json. Exit status: 0 no problem; 1 a button reported, or a press that raised an error;
// 2 the check cannot run.
//
// A button is any <button>, <input type=button|submit>, or element with role="button", such as an edge of a graph
// drawn in SVG. For each button, the check loads the page fresh, scrolls the button into view, waits until the page
// stops changing (up to 20 s), and records the page's state. It then clicks the button with a real mouse event, and
// records the state again 0.3 s and 1.5 s later. The state is: each canvas's pixels; each figure's markup, which
// holds each SVG, each <output> and each readout; the markup outside the figures; and each input's value. Every
// <button> and <input> button is left out of the markup, so that no button's label or aria-pressed counts as a
// change. An element with role="button" is part of a drawing, so it stays. Web fonts are blocked, so that every
// canvas draws with the same font each time.
//
// On a page with more than one button, a button after which nothing changed gets a second try: on a fresh load,
// the check first presses every other button on the page once, in page order, then presses this one. A Reset
// button, or a mode button that is on when the page loads, then shows that it works. A button with no change in
// both tries is reported.
//
// Some buttons act only after another control has moved. button_prep.json, next to this script, maps a page's id
// to a script that runs on each fresh load of that page before the trial, and to the reason the page needs it.
import { spawn } from 'node:child_process';
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const port = Number(opt('--port', '9338'));
const only = opt('--only', '');
const here = dirname(fileURLToPath(import.meta.url));
const dir = resolve(opt('--dir', join(here, '..', 'units')));
const outDir = args[0] ? resolve(args[0]) : null;
if (!outDir || args.length !== 1) {
  console.error('usage: node check_buttons.mjs <out dir> [--port N] [--only id1,id2] [--dir <folder>]');
  process.exit(2);
}
let prep;
try { prep = JSON.parse(readFileSync(join(here, 'button_prep.json'), 'utf8')); } catch (e) {
  console.error('check_buttons: cannot read button_prep.json: ' + e.message);
  process.exit(2);
}
let pages;
try { pages = readdirSync(dir).filter(f => f.endsWith('.html') && f !== '_template.html').sort(); } catch (e) {
  console.error('check_buttons: cannot read ' + dir + ': ' + e.message);
  process.exit(2);
}
if (only) { const want = new Set(only.split(',').map(s => s.trim() + '.html')); pages = pages.filter(f => want.has(f)); }
if (!pages.length) { console.error('no pages to check in ' + dir); process.exit(2); }
mkdirSync(outDir, { recursive: true });
const profile = join(outDir, '.chrome-profile');

const chrome = spawn('google-chrome', ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const quit = code => { try { chrome.kill(); } catch (e) { /* gone */ } try { rmSync(profile, { recursive: true, force: true }); } catch (e) { /* keep */ } process.exit(code); };
// A failure after Chrome has started, such as a prep script whose element a page no longer has: name the page,
// stop Chrome, and exit with status 2.
let current = null;
const fail = e => { console.error(`check_buttons: cannot check ${current ?? 'the pages'}: ${e?.message ?? e}`); quit(2); };
process.on('uncaughtException', fail);
process.on('unhandledRejection', fail);
let targets = null;
for (let i = 0; i < 75 && !targets; i++) { await sleep(200); try { targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); } catch (e) { /* not up */ } }
if (!targets) { console.error(`Chrome did not start on port ${port}`); quit(2); }
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0;
const pending = new Map(), events = [];
let errors = [];
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') { const d = m.params.exceptionDetails; errors.push('exception: ' + (d.exception?.description || d.text)); }
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push('console.error: ' + m.params.args.map(a => a.value ?? a.description).join(' '));
  if (m.method === 'Page.loadEventFired') events.push('load');
});
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJS = async expr => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) throw new Error('evaluate failed: ' + (r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text));
  return r.result?.result?.value;
};
await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable');
// Block the web fonts. Otherwise a canvas drawn before its font arrived changes on its next redraw, whatever the
// button does.
await send('Network.setBlockedURLs', { urls: ['*fonts.googleapis.com*', '*fonts.gstatic.com*'] });
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

const BUTTONS = `[...document.querySelectorAll('button, input[type=button], input[type=submit], [role=button]')]`;
// The page's state, as one short hash per part. Buttons and scripts are removed from every markup copy.
const STATE = `(() => {
  const h = s => { let a = 0x811c9dc5, b = 5381;
    for (let i = 0; i < s.length; i++) { const c = s.charCodeAt(i); a = Math.imul(a ^ c, 16777619); b = (Math.imul(b, 33) + c) | 0; }
    return (a >>> 0).toString(16) + '.' + (b >>> 0).toString(16) + '.' + s.length; };
  const strip = el => { const c = el.cloneNode(true); c.querySelectorAll('button, input[type=button], input[type=submit], script').forEach(e => e.remove()); return c; };
  const st = {};
  [...document.querySelectorAll('figure')].forEach((f, k) => { st['figure ' + (k + 1) + ' markup'] = h(strip(f).outerHTML); });
  const body = strip(document.body); body.querySelectorAll('figure').forEach(f => f.remove());
  st['markup outside the figures'] = h(body.outerHTML);
  [...document.querySelectorAll('canvas')].forEach((c, k) => { let d; try { d = c.toDataURL(); } catch (e) { d = 'error ' + e; } st['canvas ' + (k + 1) + (c.id ? ' #' + c.id : '') + ' pixels'] = h(d); });
  [...document.querySelectorAll('input:not([type=button]):not([type=submit]), select, textarea')].forEach((e, k) => {
    st['input ' + (k + 1) + (e.id ? ' #' + e.id : '') + ' value'] = String(e.type === 'checkbox' || e.type === 'radio' ? e.checked : e.value); });
  return st;
})()`;
const diff = (a, b) => Object.keys({ ...a, ...b }).filter(k => a[k] !== b[k]);

async function load(file) {
  events.length = 0;
  await send('Page.navigate', { url: 'about:blank' });
  for (let i = 0; i < 40 && !events.includes('load'); i++) await sleep(50);
  events.length = 0; errors = [];
  await send('Page.navigate', { url: pathToFileURL(join(dir, file)).href });
  for (let i = 0; i < 100 && !events.includes('load'); i++) await sleep(100);
  await evalJS(`(async () => { try { await Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 3000))]); } catch (e) {} })()`);
  await sleep(300);
}
// Wait until two states 0.4 s apart are equal, for at most maxMs. Returns the last state and what kept changing.
async function settle(maxMs = 20000) {
  let prev = await evalJS(STATE);
  const t0 = Date.now();
  let moving = [];
  while (Date.now() - t0 < maxMs) {
    await sleep(400);
    const cur = await evalJS(STATE);
    moving = diff(prev, cur);
    prev = cur;
    if (!moving.length) return { state: cur, settled: true, waitedMs: Date.now() - t0 };
  }
  return { state: prev, settled: false, moving, waitedMs: Date.now() - t0 };
}
async function scrollTo(k) {
  await evalJS(`${BUTTONS}[${k}].scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' })`);
  await sleep(150);
}
// Click button k where it is drawn, with a real mouse event; fall back to element.click() if it is hidden or covered.
async function press(k) {
  const p = await evalJS(`(() => { const b = ${BUTTONS}[${k}]; const r = b.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2, hit = document.elementFromPoint(x, y);
    return { x, y, ok: (r.width > 0 || r.height > 0) && !!hit && (hit === b || b.contains(hit)), disabled: b.disabled }; })()`);
  if (p.ok) {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: p.x, y: p.y });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: p.x, y: p.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: p.x, y: p.y, button: 'left', clickCount: 1 });
  } else {
    // An SVG element has no click() method, so dispatch the event.
    await evalJS(`(() => { const b = ${BUTTONS}[${k}]; if (b.click) b.click(); else b.dispatchEvent(new MouseEvent('click', { bubbles: true })); })()`);
  }
  return { how: p.ok ? 'mouse' : 'click()', disabled: p.disabled };
}
async function trial(k, label) {
  await scrollTo(k);
  const before = await settle();
  errors = [];
  const how = await press(k);
  await sleep(300);
  const s1 = await evalJS(STATE);
  await sleep(1200);
  const s2 = await evalJS(STATE);
  const changed03 = diff(before.state, s1), changed15 = diff(before.state, s2);
  return { label, how: how.how, disabled: how.disabled, settled: before.settled, settleMs: before.waitedMs,
    stillMoving: before.moving || [], changed03, changed15, noChange: !changed03.length && !changed15.length,
    errors: [...errors] };
}

const prepFor = file => prep[file.replace(/\.html$/, '')]?.script || null;
async function runPrep(file) {
  const js = prepFor(file);
  if (js) { await evalJS(`(() => { ${js}; })()`); await sleep(300); }
}
const results = [];
let fps = null;
for (const file of pages) {
  current = file;
  await load(file);
  if (fps === null) fps = await evalJS(`new Promise(res => { let n = 0; const t0 = performance.now();
    const f = now => { n++; if (now - t0 < 1000) requestAnimationFrame(f); else res(n); }; requestAnimationFrame(f); })`);
  const list = await evalJS(`${BUTTONS}.map((b, k) => ({ k, label: ((b.textContent || b.value || '').trim().replace(/\\s+/g, ' ') || b.getAttribute('aria-label') || '(no label)'),
    fig: (() => { const f = b.closest('figure'); return f ? [...document.querySelectorAll('figure')].indexOf(f) + 1 : 0; })() }))`);
  if (!list.length) continue;
  const loadErrors = [...errors];
  for (const b of list) {
    await load(file); await runPrep(file);
    const r1 = await trial(b.k, b.label);
    let r2 = null;
    if (r1.noChange && list.length > 1) {
      await load(file); await runPrep(file);
      for (const o of list) if (o.k !== b.k) { await scrollTo(o.k); await press(o.k); await sleep(300); }
      r2 = await trial(b.k, b.label);
    }
    const res = { page: file.replace(/\.html$/, ''), prep: prepFor(file), button: b.k + 1, figure: b.fig, label: b.label, stage1: r1, stage2: r2,
      reported: r1.noChange && (!r2 || r2.noChange), loadErrors };
    results.push(res);
    const fmt = r => r.noChange ? 'NO CHANGE' : 'changed: ' + [...new Set([...r.changed03, ...r.changed15])].join('; ');
    const notes = r => [r.how !== 'mouse' ? 'pressed with click()' : '', r.disabled ? 'disabled' : '',
      r.settled ? '' : 'page still changing before the press: ' + r.stillMoving.join('; '),
      r.errors.length ? 'errors: ' + r.errors.join(' | ') : ''].filter(Boolean).join('; ');
    console.log(`${res.reported ? 'REPORTED' : 'ok      '} ${res.page} button ${res.button} "${b.label}" (figure ${b.fig || '-'})`);
    console.log(`         stage 1: ${fmt(r1)}${notes(r1) ? ' [' + notes(r1) + ']' : ''}`);
    if (r2) console.log(`         stage 2: ${fmt(r2)}${notes(r2) ? ' [' + notes(r2) + ']' : ''}`);
  }
}
const reported = results.filter(r => r.reported);
const errored = results.filter(r => r.stage1.errors.length || (r.stage2 && r.stage2.errors.length));
writeFileSync(join(outDir, 'buttons.json'), JSON.stringify({ fps, results }, null, 1));
console.log(`\nframes per second: ${fps}`);
console.log(`check_buttons: ${results.length} buttons on ${new Set(results.map(r => r.page)).size} pages pressed; ` +
  `${reported.length} reported, ${results.filter(r => r.stage2).length} needed a second try, ` +
  `${errored.length} raised errors` + (reported.length || errored.length ? '' : ' - OK'));
for (const r of reported) console.log(`  reported: ${r.page} button ${r.button} "${r.label}"`);
for (const r of errored) console.log(`  raised an error: ${r.page} button ${r.button} "${r.label}"`);
quit(reported.length || errored.length ? 1 : 0);
