// Concept units: shared behavior. No network access and no dependencies. Every part checks that its
// elements exist, so a page that lacks them runs without errors. Load with <script src="unit.js" defer>.
(() => {
  'use strict';

  // ---------- Python highlighting for <pre><code class="py">: keywords, comments and strings
  // (a triple-quoted string may span lines), plus line numbers. Optional attributes on <code>:
  // data-start="N" numbers the first line N; data-hl="3,4" highlights those line numbers.
  const KW = new Set(['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
    'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
    'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']);
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  function hlLine(src, st) {
    let out = '', i = 0;
    if (st.q) {
      const j = src.indexOf(st.q);
      if (j < 0) return '<span class="s">' + esc(src) + '</span>';
      out += '<span class="s">' + esc(src.slice(0, j + 3)) + '</span>';
      i = j + 3;
      st.q = null;
    }
    while (i < src.length) {
      const ch = src[i];
      if (ch === '#') { out += '<span class="c">' + esc(src.slice(i)) + '</span>'; break; }
      if (ch === '"' || ch === "'") {
        const tq = src.slice(i, i + 3);
        let j;
        if (tq === '"""' || tq === "'''") {
          j = src.indexOf(tq, i + 3);
          if (j < 0) { st.q = tq; j = src.length; } else j += 3;
        } else {
          j = i + 1;
          while (j < src.length && src[j] !== ch) { if (src[j] === '\\') j++; j++; }
          j = Math.min(src.length, j + 1);
        }
        out += '<span class="s">' + esc(src.slice(i, j)) + '</span>'; i = j; continue;
      }
      const m = /^[A-Za-z_][A-Za-z0-9_]*/.exec(src.slice(i));
      if (m) { out += KW.has(m[0]) ? '<span class="k">' + m[0] + '</span>' : m[0]; i += m[0].length; continue; }
      out += esc(ch); i++;
    }
    return out;
  }
  document.querySelectorAll('pre code.py').forEach(code => {
    const start = Number(code.dataset.start || 1), st = { q: null };
    const hl = new Set((code.dataset.hl || '').split(',').filter(Boolean).map(Number));
    const lines = code.textContent.replace(/^\n/, '').replace(/\n\s*$/, '').split('\n');
    code.innerHTML = lines.map((l, k) => {
      const n = start + k;
      return '<span class="ln' + (hl.has(n) ? ' hl' : '') + '" data-n="' + n + '">' + (hlLine(l, st) || ' ') + '</span>';
    }).join('');
  });

  // ---------- captions that work from disk. Chrome refuses <track src="..."> on a page opened over file://,
  // so a page can put the WebVTT text in <script type="text/vtt" id="X"> and mark the video with
  // data-vtt="X" (optional data-vtt-label, data-vtt-lang). This turns the text into a caption track.
  document.querySelectorAll('video[data-vtt]').forEach(video => {
    const src = document.getElementById(video.dataset.vtt);
    if (!src) return;
    const url = URL.createObjectURL(new Blob([src.textContent.trim() + '\n'], { type: 'text/vtt' }));
    const track = document.createElement('track');
    track.kind = 'captions';
    track.label = video.dataset.vttLabel || 'English';
    track.srclang = video.dataset.vttLang || 'en';
    track.src = url;
    track.default = true;
    video.appendChild(track);
  });

  // ---------- the prerequisite graph on index.html: hovering or focusing a unit lights its links
  document.querySelectorAll('svg.prereq-graph').forEach(svg => {
    const edges = [...svg.querySelectorAll('.edge')];
    svg.querySelectorAll('.node[data-id]').forEach(node => {
      const id = node.dataset.id;
      const mine = edges.filter(e => e.dataset.from === id || e.dataset.to === id);
      const near = new Set(mine.flatMap(e => [e.dataset.from, e.dataset.to]));
      const nodes = [...svg.querySelectorAll('.node[data-id]')].filter(n => near.has(n.dataset.id));
      const on = v => { mine.forEach(e => e.classList.toggle('on', v)); nodes.forEach(n => n.classList.toggle('on', v)); };
      const target = node.closest('a') || node;
      target.addEventListener('pointerenter', () => on(true));
      target.addEventListener('pointerleave', () => on(false));
      target.addEventListener('focus', () => on(true));
      target.addEventListener('blur', () => on(false));
    });
  });
})();
