"""Prepare a fresh 3D operator from an already-audited actual print-control slice."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
D=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--initial-scale',type=float,default=1.);args=ap.parse_args();r={'status':'RUNNING','steps':[]};start=time.perf_counter()
    assert not (args.run/'preparation.json').exists();env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    def run(name,cmd):
        tick=time.perf_counter()
        with (args.run/(name+'.log')).open('w') as log:proc=subprocess.run([str(v) for v in cmd],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=900)
        r['steps'].append(dict(name=name,returncode=proc.returncode,seconds=time.perf_counter()-tick));assert proc.returncode==0;print(json.dumps(r['steps'][-1]),flush=True)
    try:
        run('geometry',[sys.executable,D/'gpu_demo_geometry.py','--shape',args.run/'shape','--output',args.run/'geometry','--h','.2','--hz','.2','--max-grid-cells','165000000'])
        run('interfaces',[sys.executable,D/'gpu_demo_interfaces.py','--geometry',args.run/'geometry'])
        assert json.loads((args.run/'geometry/interfaces.json').read_text())['status']=='PASS_INTERFACE_PRECHECK'
        run('adaptive',[sys.executable,D/'gpu_demo_adaptive.py','--geometry',args.run/'geometry','--output',args.run/'adaptive','--protect-g-interfaces'])
        previous=D/'.work/gpu-demo'
        run('transfer',[sys.executable,D/'evo_transfer.py','--old-geometry',previous/'g-h0p2','--old-adaptive',previous/'g-h0p2-adaptive-v2','--old-state',previous/'g-contact-tight-v1/contact-00','--geometry',args.run/'geometry','--adaptive',args.run/'adaptive','--output',args.run/'initial'])
        if args.initial_scale!=1:
            import numpy as np
            initial=args.run/'initial';scaled=args.run/'scaled-initial';scaled.mkdir()
            np.save(scaled/'master_u.npy',np.load(initial/'master_u.npy')*args.initial_scale)
            __import__('shutil').copyfile(initial/'active_wall_indices.npy',scaled/'active_wall_indices.npy')
            r['initial_displacement_scale']=args.initial_scale;r['initial_scale_scope']='Initial guess only. All loads, stiffness and contact are recomputed; scaling is not a result or a material modulus.'
        r['status']='PREPARED_FOR_3D'
    except BaseException:r['status']='FAIL_PREPARATION';raise
    finally:
        r['elapsed_seconds']=time.perf_counter()-start;(args.run/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
if __name__=='__main__':main()
