"""Run the five requested wall/skin contrasts with the same Orca executable."""
from pathlib import Path
import subprocess
import sys
from prepare_g_recheck import CASES

D = Path(__file__).resolve().parent
for name in CASES:
    subprocess.run([sys.executable, str(D.parent/'rev-g/slice_audit.py'),
                    sys.argv[1], str(D/'g-recheck'/name)], check=True)
    print('SLICED', name, flush=True)
