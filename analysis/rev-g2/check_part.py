"""Fresh slice/material/contact screen for an already-built fixed-interface part.

Uses the validated G rod/mount coordinates. No geometry is copied from G;
only an initial displacement/contact guess is transferred to the new operator.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
ROOT = D.parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cad', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--orca', type=Path, required=True)
    ap.add_argument('--solve-seconds', type=float, default=420)
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--reference-run', type=Path)
    ap.add_argument('--reference-result', default='contact-tight')
    ap.add_argument('--two-phase-contact', action='store_true')
    args = ap.parse_args()
    assert not (args.prepare_only and args.resume)
    start = time.perf_counter(); prior = 0.0
    params=json.loads((args.cad/'selected-layout.json').read_text())
    model_name=params.get('model_file','rev-g-model-and-modifiers.3mf')
    model = args.cad/model_name
    skin_layers=round(params.get('skin_mm',1.0)/.2)
    assert abs(skin_layers*.2-params.get('skin_mm',1.0)) < 1e-8
    modifier_count=len(params.get('modifier_names',['dense-chords-and-seats','rib-plane-lower','rib-plane-upper']))
    model_hash = hashlib.sha256(model.read_bytes()).hexdigest()
    if args.resume:
        report = json.loads((args.output/'pipeline.json').read_text())
        assert report['status'] == 'PREPARED_FOR_3D'
        assert report['input_model_sha256'] == model_hash
        prior = report['elapsed_seconds']
    else:
        assert not args.output.exists(), 'Use a fresh attempt directory'
        args.output.mkdir(parents=True)
        report = dict(status='RUNNING', candidate=args.cad.name, input_model_sha256=model_hash,
                      steps=[], scope='Fresh actual sliced material on a new CAD body. Fixed G interface coordinates; inscribed 0.2 mm material and isotropic planning law remain screening approximations.')
    def save():
        report['elapsed_seconds'] = prior+time.perf_counter()-start
        report['timing_scope'] = 'Active stages only. CAD/package and parked time before resume are separate.'
        (args.output/'pipeline.json').write_text(json.dumps(report, indent=2)+'\n')
    def run(name, command, gpu=False):
        tick = time.perf_counter(); env = os.environ.copy()
        env['OPENBLAS_NUM_THREADS'] = '4' if gpu else '1'; env['OMP_NUM_THREADS'] = '1'
        report['current_stage'] = name; save()
        with (args.output/(name+'.log')).open('w') as log:
            result = subprocess.run([str(v) for v in command], stdout=log, stderr=subprocess.STDOUT,
                                    env=env, timeout=900)
        row = dict(name=name, returncode=result.returncode, seconds=time.perf_counter()-tick)
        report['steps'].append(row); save(); print(json.dumps(row), flush=True)
        if result.returncode: raise RuntimeError(name+' failed; raw attempt retained')
    try:
        if not args.resume:
            run('slice', [sys.executable,D/'gpu_demo_slice.py','--orca',args.orca,'--source',args.cad,'--output',args.output/'slice','--p1s-petg',
                          '--skin-layers',skin_layers,'--expected-modifiers',modifier_count,'--model-name',model_name])
            run('raw-shape', [sys.executable,D/'plastic_shape.py',args.output/'slice',args.output/'shape','--simplify-mm','0','--workers','4'])
            run('geometry', [sys.executable,D/'gpu_demo_geometry.py','--shape',args.output/'shape','--output',args.output/'geometry',
                             '--h','.2','--hz','.2','--max-grid-cells','165000000'])
            run('interfaces', [sys.executable,D/'gpu_demo_interfaces.py','--geometry',args.output/'geometry'])
            assert json.loads((args.output/'geometry/interfaces.json').read_text())['status'] == 'PASS_INTERFACE_PRECHECK'
            run('adaptive', [sys.executable,D/'gpu_demo_adaptive.py','--geometry',args.output/'geometry','--output',args.output/'adaptive','--protect-g-interfaces'])
            previous = D/'.work/gpu-demo'
            old_geometry,old_adaptive,old_state=previous/'g-h0p2',previous/'g-h0p2-adaptive-v2',previous/'g-contact-tight-v1/contact-00'
            if args.reference_run:
                old_geometry,old_adaptive=args.reference_run/'geometry',args.reference_run/'adaptive'
                result=args.reference_run/args.reference_result
                accepted=json.loads((result/'solve.json').read_text())
                assert accepted['status'] in ['PASS_CONTACT_NUMERICS_ERODED_MATERIAL_ONLY','CONTACT_SCREEN_AT_STATED_TOLERANCE_ERODED_MATERIAL_ONLY']
                old_state=sorted(result.glob('contact-[0-9][0-9]'))[-1]
            run('transfer', [sys.executable,D/'evo_transfer.py','--old-geometry',old_geometry,'--old-adaptive',old_adaptive,
                             '--old-state',old_state,'--geometry',args.output/'geometry',
                             '--adaptive',args.output/'adaptive','--output',args.output/'initial'])
        if args.prepare_only:
            report['status'] = 'PREPARED_FOR_3D'; return
        initial=args.output/'initial'; final_seconds=args.solve_seconds
        if args.two_phase_contact:
            run('contact-discovery', [sys.executable,D/'gpu_demo_solve.py','--geometry',args.output/'geometry','--adaptive',args.output/'adaptive',
                          '--output',args.output/'contact-discovery','--initial',initial/'master_u.npy',
                          '--initial-active',initial/'active_wall_indices.npy','--coarse-ratio','8','--coarse-sweeps','6',
                          '--linear-rtol','1e-4','--true-residual-limit','1.01e-4','--maxiter','6000','--max-seconds',args.solve_seconds*.75], gpu=True)
            discovery=json.loads((args.output/'contact-discovery/solve.json').read_text())
            assert discovery['status']=='CONTACT_SCREEN_AT_STATED_TOLERANCE_ERODED_MATERIAL_ONLY', 'Intermediate contact did not settle; preserve failure and stop'
            initial=sorted((args.output/'contact-discovery').glob('contact-[0-9][0-9]'))[-1]
            final_seconds=args.solve_seconds*.25
        run('solve', [sys.executable,D/'gpu_demo_solve.py','--geometry',args.output/'geometry','--adaptive',args.output/'adaptive',
                      '--output',args.output/'solve','--initial',initial/'master_u.npy',
                      '--initial-active',initial/'active_wall_indices.npy','--coarse-ratio','8','--coarse-sweeps','6' if args.two_phase_contact else '3',
                      '--linear-rtol','1e-5','--true-residual-limit','1.01e-5','--maxiter','6000','--max-seconds',final_seconds], gpu=True)
        report['status'] = json.loads((args.output/'solve/solve.json').read_text())['status']
        run('audit', [sys.executable,D/'report_gpu_g.py','--geometry',args.output/'geometry','--adaptive',args.output/'adaptive',
                      '--result',args.output/'solve','--output',args.output/'audit','--label',params['name']])
        report['current_stage'] = 'complete'
    except BaseException:
        report['status'] = 'FAIL_PIPELINE'; raise
    finally:
        save()


if __name__ == '__main__': main()
