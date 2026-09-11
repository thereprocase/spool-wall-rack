"""Sequential real CAD, Orca, raw material and bounded GPU finalist checks.

Each invocation preserves a fresh attempt. The solve budget is reported apart
from preparation and field export, so throughput cannot hide those costs.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,time

D=Path(__file__).resolve().parent
ROOT=D.parents[1]


def win(path):
    return subprocess.check_output(['wslpath','-w',str(path.resolve())],text=True).strip()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--batch',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--cad-python',type=Path,required=True);ap.add_argument('--orca',type=Path,required=True)
    ap.add_argument('--role',choices=['balanced','stiffest','economical'],required=True)
    ap.add_argument('--solve-seconds',type=float,default=420)
    ap.add_argument('--prepare-only',action='store_true')
    ap.add_argument('--resume',action='store_true')
    args=ap.parse_args();start=time.perf_counter()
    selected=next(r for r in json.loads((args.batch/'summary.json').read_text())['selected_for_actual_slice_3d'] if r['role']==args.role)
    cad=ROOT/'designs/rev-g2/evolution'/selected['id']
    source=ROOT/'designs/rev-g2/g-recheck/2w-5layers'
    report={'status':'RUNNING','candidate_id':selected['id'],'selection_role':args.role,'steps':[],
            'scope':'Actual helper CAD and P1S PETG slice; inscribed 0.2 mm adaptive mechanics remains a screening model.'}
    previous_elapsed=0.
    if args.resume:
        assert not args.prepare_only
        report=json.loads((args.output/'pipeline.json').read_text())
        assert report['status']=='PREPARED_FOR_3D' and report['candidate_id']==selected['id']
        assert json.loads((cad/'selected-layout.json').read_text())==selected['parameters']
        previous_elapsed=report['elapsed_seconds']
    else:
        assert not args.output.exists();args.output.mkdir(parents=True)
        assert not cad.exists();cad.mkdir(parents=True)
        for name in ['body-only.step','body-only.stl','body-mounted.stl']:
            shutil.copyfile(source/name,cad/name)
        (cad/'source-verification.json').write_text(json.dumps({'reference':'G 2w/5-layer body',
            'changes':'Selected helper parameters; body copied byte for byte. Helpers are rebuilt and verified separately.',
            'copied_body_sha256':{name:hashlib.sha256((cad/name).read_bytes()).hexdigest() for name in ['body-only.step','body-only.stl','body-mounted.stl']}},indent=2)+'\n')
        (cad/'selected-layout.json').write_text(json.dumps(selected['parameters'],indent=2)+'\n')
    def run(name,command,gpu=False):
        tick=time.perf_counter();env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='4' if gpu else '1';env['OMP_NUM_THREADS']='1'
        with (args.output/(name+'.log')).open('w') as log:
            result=subprocess.run([str(v) for v in command],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=900)
        report['steps'].append({'name':name,'returncode':result.returncode,'seconds':time.perf_counter()-tick})
        report['elapsed_seconds']=previous_elapsed+time.perf_counter()-start
        (args.output/'pipeline.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report['steps'][-1]),flush=True)
        if result.returncode:raise RuntimeError(name+' failed; log and partial evidence preserved')
    try:
        if not args.resume:
            run('cad',[args.cad_python,win(ROOT/'analysis/rev-g/run_native.py'),win(ROOT/'designs/rev-g/build_helpers.py'),win(cad)])
            run('package',[sys.executable,ROOT/'designs/rev-g/package_3mf.py',cad])
            run('slice',[sys.executable,D/'gpu_demo_slice.py','--orca',args.orca,'--source',cad,'--output',args.output/'slice','--p1s-petg'])
            run('raw-shape',[sys.executable,D/'plastic_shape.py',args.output/'slice',args.output/'shape','--simplify-mm','0','--workers','4'])
            run('geometry',[sys.executable,D/'gpu_demo_geometry.py','--shape',args.output/'shape','--output',args.output/'geometry','--h','.2','--hz','.2','--max-grid-cells','150000000'])
            run('interfaces',[sys.executable,D/'gpu_demo_interfaces.py','--geometry',args.output/'geometry'])
            assert json.loads((args.output/'geometry/interfaces.json').read_text())['status']=='PASS_INTERFACE_PRECHECK'
            run('adaptive',[sys.executable,D/'gpu_demo_adaptive.py','--geometry',args.output/'geometry','--output',args.output/'adaptive','--protect-g-interfaces'])
            previous=D/'.work/gpu-demo'
            run('transfer',[sys.executable,D/'evo_transfer.py','--old-geometry',previous/'g-h0p2','--old-adaptive',previous/'g-h0p2-adaptive-v2',
                '--old-state',previous/'g-contact-tight-v1/contact-00','--geometry',args.output/'geometry','--adaptive',args.output/'adaptive','--output',args.output/'initial'])
        if args.prepare_only:
            report['status']='PREPARED_FOR_3D';return
        run('solve',[sys.executable,D/'gpu_demo_solve.py','--geometry',args.output/'geometry','--adaptive',args.output/'adaptive','--output',args.output/'solve',
            '--initial',args.output/'initial/master_u.npy','--initial-active',args.output/'initial/active_wall_indices.npy','--coarse-ratio','8',
            '--linear-rtol','1e-5','--true-residual-limit','1.01e-5','--maxiter','6000','--max-seconds',str(args.solve_seconds)],gpu=True)
        report['status']=json.loads((args.output/'solve/solve.json').read_text())['status']
        run('audit',[sys.executable,D/'report_gpu_g.py','--geometry',args.output/'geometry','--adaptive',args.output/'adaptive',
            '--result',args.output/'solve','--output',args.output/'audit'])
    except BaseException:
        report['status']='FAIL_PIPELINE';raise
    finally:
        report['elapsed_seconds']=previous_elapsed+time.perf_counter()-start
        report['timing_scope']='Active pipeline stages; time parked between prepare-only and resume is excluded.'
        (args.output/'pipeline.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
