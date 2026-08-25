/* CS Gym — uninformed search practice. */

const RUN_TIMEOUT = 20000;
const TEST_TIMEOUT = 60000;
const STYLE_TIMEOUT = 90000;

const KEYWORDS = new Set([
  'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
  'def', 'del', 'elif', 'else', 'except', 'False', 'finally', 'for', 'from',
  'global', 'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not',
  'or', 'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield',
]);

const BUILTINS = new Set([
  'abs', 'all', 'any', 'bool', 'dict', 'divmod', 'enumerate', 'filter',
  'float', 'frozenset', 'int', 'isinstance', 'iter', 'len', 'list', 'map',
  'max', 'min', 'next', 'object', 'print', 'range', 'repr', 'reversed',
  'set', 'sorted', 'str', 'sum', 'super', 'tuple', 'type', 'zip',
]);

const $ = (id) => document.getElementById(id);

const el = {
  sidebar: $('sidebar'),
  briefBody: $('brief-body'),
  code: $('code'),
  highlight: $('highlight'),
  gutter: $('gutter'),
  codeScroll: $('code-scroll'),
  consoleBody: $('console-body'),
  consoleTitle: $('console-title'),
  consoleMeta: $('console-meta'),
  runtimeDot: $('runtime-dot'),
  runtimeLabel: $('runtime-label'),
  progressFill: $('progress-fill'),
  progressLabel: $('progress-label'),
  btnTest: $('btn-test'),
  btnRun: $('btn-run'),
  btnStyle: $('btn-style'),
  btnReset: $('btn-reset'),
  btnExport: $('btn-export'),
  importFile: $('import-file'),
  saveState: $('save-state'),
};

const state = {
  problems: [],
  tracks: [],
  byId: new Map(),
  current: null,
  view: 'brief',
  solved: new Set(),
  ready: false,
  busy: false,
  versionLabel: '',
  startedAt: 0,
};

/* ------------------------------------------------------------- storage */

const store = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem('csgym:' + key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (err) {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem('csgym:' + key, JSON.stringify(value));
    } catch (err) {
      /* private mode, quota — the gym still works, it just forgets. */
    }
  },
};

/* ------------------------------------------------------------ disk sync */

/* Progress lives in localStorage first, and is mirrored to cs-gym/progress.json
   whenever the gym is served by serve.py.  Plain `python3 -m http.server` has
   no PUT, so the mirror quietly turns itself off and localStorage still works. */

const sync = {
  available: false,
  timer: null,

  snapshot() {
    const code = {};
    const codeAt = {};
    state.problems.forEach((p) => {
      const saved = store.get('code:' + p.id, null);
      if (saved === null) return;
      code[p.id] = saved;
      codeAt[p.id] = store.get('codeAt:' + p.id, 0);
    });
    return {
      version: 1,
      updated: new Date().toISOString(),
      solved: Array.from(state.solved).sort(),
      last: store.get('last', null),
      code,
      codeAt,
    };
  },

  async pull() {
    try {
      const res = await fetch('progress', { cache: 'no-store' });
      if (!res.ok) return null;
      const data = await res.json();
      this.available = true;
      return data && typeof data === 'object' ? data : {};
    } catch (err) {
      return null;
    }
  },

  /* Merge a saved blob into localStorage.  Per problem, the newer copy wins,
     so opening the gym in a second browser never clobbers fresher work. */
  merge(blob, force) {
    if (!blob) return;
    (blob.solved || []).forEach((id) => state.solved.add(id));
    store.set('solved', Array.from(state.solved));
    const code = blob.code || {};
    const codeAt = blob.codeAt || {};
    Object.keys(code).forEach((id) => {
      const mine = store.get('codeAt:' + id, 0);
      const theirs = codeAt[id] || 0;
      if (force || theirs >= mine) {
        store.set('code:' + id, code[id]);
        store.set('codeAt:' + id, force ? Date.now() : theirs);
      }
    });
  },

  push() {
    if (!this.available) return;
    clearTimeout(this.timer);
    this.timer = setTimeout(async () => {
      try {
        const res = await fetch('progress', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.snapshot()),
        });
        flashSave(res.ok ? 'saved to disk' : 'not saved', !res.ok);
      } catch (err) {
        flashSave('not saved', true);
      }
    }, 600);
  },
};

let flashTimer = null;

function flashSave(text, warn) {
  el.saveState.textContent = text;
  el.saveState.className = 'save-state show' + (warn ? ' warn' : '');
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => {
    el.saveState.className = 'save-state';
  }, warn ? 4000 : 1600);
}

/* --------------------------------------------------------- highlighting */

function esc(text) {
  return text.replace(/[&<>]/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]
  ));
}

const TOKENS = /(#[^\n]*)|("""[\s\S]*?(?:"""|$)|'''[\s\S]*?(?:'''|$)|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\b\d[\d_]*\.?[\d_]*(?:[eE][+-]?\d+)?\b)|([A-Za-z_]\w*)/g;

function highlightPython(source) {
  let out = '';
  let last = 0;
  let prev = null;
  let match;
  TOKENS.lastIndex = 0;
  while ((match = TOKENS.exec(source)) !== null) {
    out += esc(source.slice(last, match.index));
    last = TOKENS.lastIndex;
    if (match[1]) {
      out += '<span class="tok-com">' + esc(match[1]) + '</span>';
      prev = null;
    } else if (match[2]) {
      out += '<span class="tok-str">' + esc(match[2]) + '</span>';
      prev = null;
    } else if (match[3]) {
      out += '<span class="tok-num">' + esc(match[3]) + '</span>';
      prev = null;
    } else {
      const word = match[4];
      let cls = null;
      if (prev === 'def' || prev === 'class') cls = 'tok-def';
      else if (KEYWORDS.has(word)) cls = 'tok-kw';
      else if (word === 'self' || word === 'cls') cls = 'tok-self';
      else if (BUILTINS.has(word)) cls = 'tok-bi';
      out += cls ? '<span class="' + cls + '">' + word + '</span>' : esc(word);
      prev = word;
    }
  }
  out += esc(source.slice(last));
  return out;
}

function codeBlock(source) {
  return '<pre class="block">' + highlightPython(source) + '</pre>';
}

/* --------------------------------------------------------------- editor */

let gutterInner = null;

function paintEditor() {
  const source = el.code.value;
  el.highlight.innerHTML = highlightPython(source) + '\n ';
  const lines = source.split('\n').length;
  if (!gutterInner) {
    gutterInner = document.createElement('div');
    gutterInner.className = 'gutter-inner';
    el.gutter.appendChild(gutterInner);
  }
  const wanted = gutterInner.childElementCount;
  if (wanted !== lines) {
    let html = '';
    for (let i = 1; i <= lines; i += 1) html += '<div>' + i + '</div>';
    gutterInner.innerHTML = html;
  }
  syncScroll();
}

function syncScroll() {
  const x = el.code.scrollLeft;
  const y = el.code.scrollTop;
  el.highlight.style.transform = 'translate(' + -x + 'px,' + -y + 'px)';
  if (gutterInner) gutterInner.style.transform = 'translateY(' + -y + 'px)';
}

function replaceSelection(text) {
  el.code.focus();
  let handled = false;
  try {
    handled = document.execCommand('insertText', false, text);
  } catch (err) {
    handled = false;
  }
  if (!handled) {
    const start = el.code.selectionStart;
    const end = el.code.selectionEnd;
    el.code.setRangeText(text, start, end, 'end');
    el.code.dispatchEvent(new Event('input'));
  }
}

function shiftLines(dedent) {
  const value = el.code.value;
  const start = value.lastIndexOf('\n', el.code.selectionStart - 1) + 1;
  let end = value.indexOf('\n', el.code.selectionEnd);
  if (end === -1) end = value.length;
  const block = value.slice(start, end);
  const shifted = block.split('\n').map((line) => (
    dedent ? line.replace(/^ {1,4}/, '') : '    ' + line
  )).join('\n');
  el.code.setRangeText(shifted, start, end, 'preserve');
  el.code.dispatchEvent(new Event('input'));
}

function onEditorKeydown(event) {
  const meta = event.metaKey || event.ctrlKey;

  if (meta && event.key === 'Enter') {
    event.preventDefault();
    runTests();
    return;
  }
  if (meta && event.key.toLowerCase() === 's') {
    event.preventDefault();
    saveCode();
    return;
  }
  if (event.key === 'Tab') {
    event.preventDefault();
    const multi = el.code.selectionStart !== el.code.selectionEnd
      && el.code.value.slice(el.code.selectionStart, el.code.selectionEnd).includes('\n');
    if (multi || event.shiftKey) shiftLines(event.shiftKey);
    else replaceSelection('    ');
    return;
  }
  if (event.key === 'Enter') {
    const upto = el.code.value.slice(0, el.code.selectionStart);
    const line = upto.slice(upto.lastIndexOf('\n') + 1);
    const indent = (line.match(/^[ ]*/) || [''])[0];
    const deeper = /:\s*(#.*)?$/.test(line) ? '    ' : '';
    if (indent || deeper) {
      event.preventDefault();
      replaceSelection('\n' + indent + deeper);
    }
    return;
  }
  if (event.key === 'Backspace'
      && el.code.selectionStart === el.code.selectionEnd) {
    const upto = el.code.value.slice(0, el.code.selectionStart);
    const line = upto.slice(upto.lastIndexOf('\n') + 1);
    if (line.length >= 4 && /^ +$/.test(line) && line.length % 4 === 0) {
      event.preventDefault();
      const at = el.code.selectionStart;
      el.code.setRangeText('', at - 4, at, 'end');
      el.code.dispatchEvent(new Event('input'));
    }
  }
}

let saveTimer = null;

function saveCode() {
  if (!state.current) return;
  const id = state.current.id;
  if (store.get('code:' + id, null) === el.code.value) return;
  store.set('code:' + id, el.code.value);
  store.set('codeAt:' + id, Date.now());
  sync.push();
}

function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveCode, 400);
}

/* -------------------------------------------------------------- sidebar */

function renderSidebar() {
  const html = state.tracks.map((track) => {
    const items = state.problems.filter((p) => p.track === track.name);
    const links = items.map((p) => {
      const classes = ['plink'];
      if (state.current && p.id === state.current.id) classes.push('is-active');
      if (state.solved.has(p.id)) classes.push('is-solved');
      return '<button class="' + classes.join(' ') + '" data-id="' + p.id + '">'
        + '<span class="check">&#10003;</span>'
        + '<span class="name">' + esc(p.title) + '</span>'
        + '<span class="pill ' + p.difficulty + '">' + p.difficulty + '</span>'
        + '</button>';
    }).join('');
    return '<div class="track"><div class="track-head"><h2>' + esc(track.name)
      + '</h2><p>' + esc(track.blurb) + '</p></div>' + links + '</div>';
  }).join('');
  el.sidebar.innerHTML = html;
  el.sidebar.querySelectorAll('.plink').forEach((node) => {
    node.addEventListener('click', () => selectProblem(node.dataset.id));
  });
}

function renderProgress() {
  const total = state.problems.length;
  const done = state.problems.filter((p) => state.solved.has(p.id)).length;
  const points = state.problems
    .filter((p) => state.solved.has(p.id))
    .reduce((sum, p) => sum + p.points, 0);
  el.progressFill.style.width = total ? (100 * done / total) + '%' : '0';
  el.progressLabel.textContent = done + ' / ' + total + ' solved · ' + points + ' pts';
}

/* ----------------------------------------------------------- brief pane */

function renderBrief() {
  const p = state.current;
  if (!p) {
    el.briefBody.innerHTML = '<div class="empty-state">Pick a problem to begin.</div>';
    return;
  }
  if (state.view === 'brief') {
    const checks = p.tests.map((t) => '<li>' + esc(t.name) + '</li>').join('');
    el.briefBody.innerHTML = '<div class="brief">'
      + '<h2>' + esc(p.title) + '</h2>'
      + '<div class="brief-meta"><span class="pill ' + p.difficulty + '">'
      + p.difficulty + '</span><span>' + p.points + ' points</span>'
      + '<span>·</span><span>' + esc(p.track) + '</span></div>'
      + p.statement
      + '<h3 style="font-size:12px;letter-spacing:.07em;text-transform:uppercase;'
      + 'color:var(--dim);margin:26px 0 8px">What the tests check</h3>'
      + '<ul>' + checks + '</ul>'
      + '</div>';
  } else if (state.view === 'examples') {
    el.briefBody.innerHTML = '<div class="brief">'
      + '<p class="muted">Interpreter transcripts. They illustrate the contract; '
      + 'the graded tests are broader.</p>' + codeBlock(p.examples) + '</div>';
  } else if (state.view === 'hints') {
    const hints = p.hints.map((h, i) => (
      '<details class="hint"><summary>Hint ' + (i + 1) + '</summary>'
      + '<div class="hint-body">' + esc(h) + '</div></details>'
    )).join('');
    el.briefBody.innerHTML = '<div class="brief">' + hints + '</div>';
  } else {
    el.briefBody.innerHTML = '<div class="brief"><div class="reveal">'
      + '<p>Reference solutions are one way to write it, not the only way.<br>'
      + 'Worth a look once your own attempt runs — or once you are stuck.</p>'
      + '<button class="btn" id="btn-reveal">Show the reference solution</button>'
      + '</div></div>';
    $('btn-reveal').addEventListener('click', () => {
      el.briefBody.innerHTML = '<div class="brief">' + codeBlock(p.solution) + '</div>';
    });
  }
}

function setView(view) {
  state.view = view;
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.classList.toggle('is-active', tab.dataset.view === view);
  });
  renderBrief();
}

/* ------------------------------------------------------------- problems */

function selectProblem(id) {
  const p = state.byId.get(id);
  if (!p) return;
  saveCode();
  state.current = p;
  store.set('last', id);
  if (location.hash.slice(1) !== id) location.hash = id;
  const saved = store.get('code:' + id, null);
  el.code.value = saved === null ? p.starter + '\n' : saved;
  paintEditor();
  el.code.scrollTop = 0;
  setView('brief');
  renderSidebar();
  resetConsole();
}

function resetConsole() {
  el.consoleTitle.textContent = 'Console';
  el.consoleMeta.textContent = '';
  el.consoleBody.innerHTML = '<p class="muted">Write your solution, then '
    + '<strong>Run tests</strong>. <kbd>&#8984;&#9166;</kbd> works too.</p>';
}

/* --------------------------------------------------------------- worker */

let worker = null;
let seq = 0;
const pending = new Map();

function setRuntime(status, text) {
  el.runtimeDot.className = 'dot ' + status;
  el.runtimeLabel.textContent = text;
}

function bootWorker() {
  if (worker) worker.terminate();
  worker = new Worker('worker.js');
  worker.onmessage = (event) => {
    const msg = event.data;
    const entry = pending.get(msg.id);
    if (msg.type === 'status') {
      setRuntime('busy', msg.text);
      return;
    }
    if (msg.type === 'ready') {
      state.ready = true;
      state.versionLabel = 'Python ' + msg.version;
      setRuntime('ready', state.versionLabel);
      setBusy(false);
      return;
    }
    if (!entry) return;
    pending.delete(msg.id);
    clearTimeout(entry.timer);
    if (msg.type === 'error') entry.reject(new Error(msg.message));
    else entry.resolve(msg.data);
  };
  worker.onerror = (event) => {
    setRuntime('error', 'Runtime failed to load');
    pending.forEach((entry) => {
      clearTimeout(entry.timer);
      entry.reject(new Error(event.message || 'worker crashed'));
    });
    pending.clear();
    setBusy(false);
  };
  state.ready = false;
  setRuntime('busy', 'Booting Python…');
  worker.postMessage({ id: ++seq, type: 'init' });
}

function killWorker(reason) {
  pending.forEach((entry) => {
    clearTimeout(entry.timer);
    entry.reject(new Error(reason));
  });
  pending.clear();
  bootWorker();
}

function ask(type, payload, timeout) {
  return new Promise((resolve, reject) => {
    const id = ++seq;
    const timer = setTimeout(() => {
      pending.delete(id);
      killWorker('timeout');
      reject(new Error('timeout'));
    }, timeout);
    pending.set(id, { resolve, reject, timer });
    worker.postMessage(Object.assign({ id, type }, payload));
  });
}

/* ------------------------------------------------------------ execution */

let tick = null;

function setBusy(busy, label) {
  state.busy = busy;
  const enabled = state.ready && !busy;
  el.btnRun.disabled = !enabled;
  el.btnStyle.disabled = !enabled;
  el.btnTest.disabled = !state.ready;
  el.btnTest.innerHTML = busy
    ? 'Stop'
    : 'Run tests <kbd>&#8984;&#9166;</kbd>';
  el.btnTest.classList.toggle('btn-primary', !busy);
  clearInterval(tick);
  if (busy) {
    state.startedAt = Date.now();
    el.consoleTitle.textContent = label || 'Running';
    el.consoleMeta.textContent = '0.0s';
    tick = setInterval(() => {
      el.consoleMeta.textContent =
        ((Date.now() - state.startedAt) / 1000).toFixed(1) + 's';
    }, 100);
  } else {
    if (state.startedAt) {
      el.consoleMeta.textContent =
        ((Date.now() - state.startedAt) / 1000).toFixed(2) + 's';
      state.startedAt = 0;
    }
    if (state.ready) setRuntime('ready', state.versionLabel || 'Python ready');
  }
}

function reportFailure(err) {
  if (err.message === 'stopped') return;
  if (err.message === 'timeout') {
    el.consoleTitle.textContent = 'Timed out';
    el.consoleBody.innerHTML = '<div class="summary warn">Stopped after '
      + 'the time limit — the interpreter was restarted.</div>'
      + '<p class="muted">An unbounded search usually means a missing visited '
      + 'set, a goal test that never fires, or a successor function that '
      + 'returns the state it was given.</p>';
  } else {
    el.consoleTitle.textContent = 'Error';
    el.consoleBody.innerHTML = '<div class="summary fail">'
      + esc(err.message) + '</div>';
  }
}

async function runCode() {
  if (!state.ready || state.busy) return;
  saveCode();
  setBusy(true, 'Running your code');
  try {
    const data = await ask('run', { code: el.code.value }, RUN_TIMEOUT);
    el.consoleTitle.textContent = 'Output';
    const parts = [];
    if (data.output) parts.push('<pre class="stdout">' + esc(data.output) + '</pre>');
    if (data.error) parts.push('<pre class="stdout err">' + esc(data.error) + '</pre>');
    if (!parts.length) {
      parts.push('<p class="muted">Ran cleanly with no output. Add a '
        + '<code>print(...)</code> at the bottom to inspect something.</p>');
    }
    el.consoleBody.innerHTML = parts.join('');
  } catch (err) {
    reportFailure(err);
  } finally {
    setBusy(false);
  }
}

async function runTests() {
  if (!state.ready || !state.current) return;
  if (state.busy) {
    killWorker('stopped');
    el.consoleTitle.textContent = 'Stopped';
    el.consoleBody.innerHTML = '<div class="summary warn">Stopped. '
      + 'Restarting the interpreter…</div>';
    setBusy(false);
    return;
  }
  saveCode();
  const problem = state.current;
  setBusy(true, 'Running tests');
  try {
    const data = await ask(
      'test',
      { code: el.code.value, tests: problem.tests },
      TEST_TIMEOUT,
    );
    renderTestResults(problem, data);
  } catch (err) {
    reportFailure(err);
  } finally {
    setBusy(false);
  }
}

function renderTestResults(problem, data) {
  if (data.fatal) {
    el.consoleTitle.textContent = 'Your code did not run';
    el.consoleBody.innerHTML = '<div class="summary fail">'
      + 'The file itself raised before any test ran.</div>'
      + '<pre class="stdout err">' + esc(data.fatal) + '</pre>';
    return;
  }
  const passed = data.results.filter((r) => r.ok).length;
  const total = data.results.length;
  const allPassed = passed === total && total > 0;
  el.consoleTitle.textContent = 'Test results';

  const rows = data.results.map((r) => {
    const cls = r.ok ? 'pass' : 'fail';
    const mark = r.ok ? '&#10003;' : '&#10007;';
    const head = '<summary><span class="mark">' + mark + '</span>'
      + '<span>' + esc(r.name) + '</span>'
      + (r.ok ? '' : '<span class="muted"> — ' + esc(r.brief || '') + '</span>')
      + '</summary>';
    if (r.ok && !r.output) {
      return '<details class="result pass" data-static="1">' + head + '</details>';
    }
    const body = '<pre>' + esc((r.trace || '') + (r.output ? '\n' + r.output : ''))
      + '</pre>';
    return '<details class="result ' + cls + '"' + (r.ok ? '' : ' open') + '>'
      + head + body + '</details>';
  }).join('');

  const summary = '<div class="summary ' + (allPassed ? 'pass' : 'fail') + '">'
    + (allPassed
      ? '&#10003; All ' + total + ' tests passed — ' + problem.points + ' points.'
      : passed + ' of ' + total + ' tests passed.')
    + '</div>';

  const stdout = data.output
    ? '<pre class="stdout">' + esc(data.output) + '</pre>' : '';
  el.consoleBody.innerHTML = summary + stdout + rows;
  el.consoleBody.scrollTop = 0;

  if (allPassed && !state.solved.has(problem.id)) {
    state.solved.add(problem.id);
    store.set('solved', Array.from(state.solved));
    sync.push();
    renderSidebar();
    renderProgress();
  }
}

async function runStyle() {
  if (!state.ready || state.busy) return;
  saveCode();
  setBusy(true, 'Checking style');
  try {
    const data = await ask('style', { code: el.code.value }, STYLE_TIMEOUT);
    el.consoleTitle.textContent = 'PEP 8 (pycodestyle)';
    if (!data.problems.length) {
      el.consoleBody.innerHTML = '<div class="summary pass">'
        + '&#10003; No style errors. That is the 5 free points.</div>';
      return;
    }
    const rows = data.problems.map((item) => (
      '<div class="style-row"><span class="loc">' + item.line + ':' + item.col
      + '</span><span class="msg"><span class="code">' + esc(item.code)
      + '</span> ' + esc(item.text) + '</span></div>'
    )).join('');
    el.consoleBody.innerHTML = '<div class="summary fail">'
      + data.problems.length + ' style '
      + (data.problems.length === 1 ? 'error' : 'errors') + '</div>' + rows;
  } catch (err) {
    if (err.message !== 'timeout') {
      el.consoleTitle.textContent = 'Style check unavailable';
      el.consoleBody.innerHTML = '<div class="summary warn">Could not fetch '
        + 'pycodestyle — that download needs network access.</div>'
        + '<p class="muted">' + esc(err.message) + '</p>';
    } else {
      reportFailure(err);
    }
  } finally {
    setBusy(false);
  }
}

/* ----------------------------------------------------------------- init */

function exportProgress() {
  const blob = new Blob([JSON.stringify(sync.snapshot(), null, 1)],
                        { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const stamp = new Date().toISOString().slice(0, 10);
  link.href = url;
  link.download = 'cs-gym-progress-' + stamp + '.json';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
  flashSave('exported');
}

function importProgress(file) {
  const reader = new FileReader();
  reader.onload = () => {
    let blob = null;
    try {
      blob = JSON.parse(reader.result);
    } catch (err) {
      window.alert('That file is not valid JSON.');
      return;
    }
    if (!blob || typeof blob !== 'object' || !blob.code) {
      window.alert('That does not look like a CS Gym export.');
      return;
    }
    const count = Object.keys(blob.code).length;
    if (!window.confirm('Restore ' + count + ' saved solution'
        + (count === 1 ? '' : 's') + ' and ' + (blob.solved || []).length
        + ' solved marks? This overwrites what is in this browser.')) {
      return;
    }
    sync.merge(blob, true);
    sync.available && sync.push();
    location.reload();
  };
  reader.readAsText(file);
}

function wire() {
  el.code.addEventListener('input', () => { paintEditor(); scheduleSave(); });
  el.code.addEventListener('scroll', syncScroll);
  el.code.addEventListener('keydown', onEditorKeydown);
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => setView(tab.dataset.view));
  });
  el.btnTest.addEventListener('click', runTests);
  el.btnRun.addEventListener('click', runCode);
  el.btnStyle.addEventListener('click', runStyle);
  el.btnExport.addEventListener('click', exportProgress);
  el.importFile.addEventListener('change', (event) => {
    const file = event.target.files && event.target.files[0];
    if (file) importProgress(file);
    event.target.value = '';
  });
  el.btnReset.addEventListener('click', () => {
    if (!state.current) return;
    if (!window.confirm('Replace the editor with the starter code?')) return;
    el.code.value = state.current.starter + '\n';
    paintEditor();
    saveCode();
  });
  window.addEventListener('hashchange', () => {
    const id = location.hash.slice(1);
    if (id && state.byId.has(id) && (!state.current || state.current.id !== id)) {
      selectProblem(id);
    }
  });
  window.addEventListener('beforeunload', () => {
    saveCode();
    if (sync.available) {
      clearTimeout(sync.timer);
      const body = JSON.stringify(sync.snapshot());
      navigator.sendBeacon('progress', new Blob([body], {
        type: 'application/json',
      }));
    }
  });
  document.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter'
        && document.activeElement !== el.code) {
      event.preventDefault();
      runTests();
    }
  });
}

async function start() {
  wire();
  setRuntime('busy', 'Loading problems…');
  const response = await fetch('problems.json');
  const payload = await response.json();
  state.tracks = payload.tracks;
  state.problems = payload.problems;
  state.problems.forEach((p) => state.byId.set(p.id, p));
  store.get('solved', []).forEach((id) => state.solved.add(id));

  const remote = await sync.pull();
  if (remote) {
    sync.merge(remote, false);
    sync.push();
  } else {
    el.saveState.textContent = 'browser only';
    el.saveState.className = 'save-state show warn';
    el.saveState.title = 'Run serve.py to mirror progress to cs-gym/progress.json';
  }
  renderProgress();

  const wanted = location.hash.slice(1) || store.get('last', null)
    || (remote && remote.last);
  selectProblem(state.byId.has(wanted) ? wanted : state.problems[0].id);
  bootWorker();
}

start();
