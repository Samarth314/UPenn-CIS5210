/* Python runtime for CS Gym.  Runs off the main thread so a runaway search
   can be killed by terminating the worker instead of freezing the page. */

const PYODIDE_VERSION = 'v0.27.5';
const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/' + PYODIDE_VERSION + '/full/';

let pyodide = null;
let styleReady = false;

const HARNESS = String.raw`
import io
import json
import linecache
import sys
import traceback

_GYM_LIMIT = 40000


def _gym_clip(text):
    if len(text) > _GYM_LIMIT:
        return text[:_GYM_LIMIT] + "\n... output truncated ..."
    return text


def _gym_register(name, source):
    linecache.cache[name] = (len(source), None, source.splitlines(True), name)


def _gym_trace():
    """Format the current exception with the gym's own frames stripped off."""
    exc_type, exc, tb = sys.exc_info()
    while tb is not None and tb.tb_frame.f_code.co_filename == "<exec>":
        tb = tb.tb_next
    return _gym_clip("".join(traceback.format_exception(exc_type, exc, tb)))


def _gym_brief():
    exc_type, exc, tb = sys.exc_info()
    text = "".join(traceback.format_exception_only(exc_type, exc)).strip()
    text = " ".join(text.split())
    if exc_type is AssertionError and not str(exc):
        frames = traceback.extract_tb(tb)
        if frames and frames[-1].line:
            text = "failed: " + frames[-1].line.strip()
    return _gym_clip(text)


class _Capture(object):
    def __enter__(self):
        self.buffer = io.StringIO()
        self._saved = (sys.stdout, sys.stderr)
        sys.stdout = sys.stderr = self.buffer
        return self

    def __exit__(self, *exc):
        sys.stdout, sys.stderr = self._saved
        return False

    def text(self):
        return _gym_clip(self.buffer.getvalue())


def _gym_exec(code, namespace):
    _gym_register("your_code.py", code)
    exec(compile(code, "your_code.py", "exec"), namespace)


def _gym_run(code):
    namespace = {"__name__": "__main__"}
    with _Capture() as cap:
        try:
            _gym_exec(code, namespace)
            error = None
        except BaseException:
            error = _gym_trace()
    return json.dumps({"output": cap.text(), "error": error})


def _gym_test(code, tests_json):
    tests = json.loads(tests_json)
    namespace = {"__name__": "__main__"}
    with _Capture() as cap:
        try:
            _gym_exec(code, namespace)
            fatal = None
        except BaseException:
            fatal = _gym_trace()
    if fatal is not None:
        return json.dumps({"fatal": fatal, "output": cap.text(), "results": []})

    results = []
    for index, test in enumerate(tests):
        name = "test_%02d.py" % (index + 1)
        _gym_register(name, test["src"])
        scope = dict(namespace)
        with _Capture() as tcap:
            try:
                exec(compile(test["src"], name, "exec"), scope)
                entry = {"name": test["name"], "ok": True}
            except BaseException:
                entry = {"name": test["name"], "ok": False,
                         "brief": _gym_brief(), "trace": _gym_trace()}
        text = tcap.text()
        if text:
            entry["output"] = text
        results.append(entry)
    return json.dumps({"fatal": None, "output": cap.text(), "results": results})


def _gym_style(code):
    import pycodestyle

    class _Collector(pycodestyle.BaseReport):

        def __init__(self, options):
            pycodestyle.BaseReport.__init__(self, options)
            self.problems = []

        def error(self, line_number, offset, text, check):
            found = pycodestyle.BaseReport.error(self, line_number, offset,
                                                 text, check)
            if found:
                message = text[len(found):].strip() or text
                self.problems.append({"line": line_number, "col": offset + 1,
                                      "code": found, "text": message})
            return found

    lines = code.splitlines(True)
    guide = pycodestyle.StyleGuide()
    report = _Collector(guide.options)
    checker = pycodestyle.Checker(filename="your_code.py", lines=lines,
                                  options=guide.options, report=report)
    checker.check_all()
    report.problems.sort(key=lambda item: (item["line"], item["col"]))
    return json.dumps({"problems": report.problems})
`;

function post(id, payload) {
  self.postMessage(Object.assign({ id: id }, payload));
}

async function boot(id) {
  post(id, { type: 'status', text: 'Downloading Python…' });
  importScripts(PYODIDE_URL + 'pyodide.js');
  pyodide = await self.loadPyodide({ indexURL: PYODIDE_URL });
  post(id, { type: 'status', text: 'Starting interpreter…' });
  pyodide.runPython(HARNESS);
  post(id, { type: 'ready', version: pyodide.version });
}

function callPython(name, args) {
  const fn = pyodide.globals.get(name);
  try {
    return JSON.parse(fn(...args));
  } finally {
    fn.destroy();
  }
}

async function ensureStyle(id) {
  if (styleReady) return true;
  post(id, { type: 'status', text: 'Fetching pycodestyle…' });
  await pyodide.loadPackage('micropip');
  const micropip = pyodide.pyimport('micropip');
  try {
    await micropip.install('pycodestyle');
    styleReady = true;
  } finally {
    micropip.destroy();
  }
  return styleReady;
}

self.onmessage = async (event) => {
  const { id, type, code, tests } = event.data;
  try {
    if (type === 'init') {
      await boot(id);
      return;
    }
    if (!pyodide) throw new Error('Python is not ready yet.');

    if (type === 'run') {
      post(id, { type: 'result', kind: 'run', data: callPython('_gym_run', [code]) });
    } else if (type === 'test') {
      post(id, {
        type: 'result',
        kind: 'test',
        data: callPython('_gym_test', [code, JSON.stringify(tests)]),
      });
    } else if (type === 'style') {
      await ensureStyle(id);
      post(id, { type: 'result', kind: 'style', data: callPython('_gym_style', [code]) });
    } else {
      throw new Error('unknown request: ' + type);
    }
  } catch (err) {
    post(id, { type: 'error', message: (err && err.message) || String(err) });
  }
};
