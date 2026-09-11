"""Disposable worker for native CAD/VTK stacks with teardown crashes.

Usage: python analysis/rev-g/run_native.py script.py [script arguments]
Outputs must be explicitly saved by the script before it returns. Exceptions
and failed assertions retain nonzero status; only native finalization is skipped.
"""
from pathlib import Path
import os
import sys
import traceback

runtime = Path(__file__).resolve().parent / '.work' / 'runtime'
runtime.mkdir(parents=True, exist_ok=True)
if os.name == 'nt' and not os.environ.get('USERPROFILE') and not os.environ.get('HOMEPATH'):
    # Some restricted workers omit home variables; keep generated font/cache
    # files inside this disposable workspace instead of assuming a user path.
    worker_home = runtime / 'home'
    worker_home.mkdir(exist_ok=True)
    os.environ['USERPROFILE'] = str(worker_home)
if os.name == 'nt' and not os.environ.get('WINDIR'):
    import ctypes
    windows_path = ctypes.create_unicode_buffer(32768)
    assert ctypes.windll.kernel32.GetWindowsDirectoryW(windows_path, len(windows_path))
    os.environ['WINDIR'] = windows_path.value
    os.environ.setdefault('SYSTEMROOT', windows_path.value)
for key, folder in [('MPLCONFIGDIR', 'matplotlib'),
                    ('XDG_CONFIG_HOME', 'config'), ('XDG_CACHE_HOME', 'cache')]:
    os.environ.setdefault(key, str(runtime / folder))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

target = str(Path(sys.argv.pop(1)).resolve())
sys.argv[0] = target
sys.path.insert(0, str(Path(target).parent))
# Own the namespace before execution and retain traceback frames on failure.
task_globals = {'__name__': '__main__', '__file__': target,
                '__package__': None, '__cached__': None, '__spec__': None,
                '__builtins__': __builtins__}
failure_info = None
status = 0
try:
    with open(target, 'rb') as source_file:
        code = compile(source_file.read(), target, 'exec')
    exec(code, task_globals)
except SystemExit as failure:
    failure_info = sys.exc_info()
    if failure.code is None:
        status = 0
    elif isinstance(failure.code, int):
        status = failure.code
    else:
        print(failure.code, file=sys.stderr)
        status = 1
except BaseException as failure:
    failure_info = sys.exc_info()
    status = 130 if isinstance(failure, KeyboardInterrupt) else 1
    traceback.print_exception(*failure_info)
finally:
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        os._exit(status)
