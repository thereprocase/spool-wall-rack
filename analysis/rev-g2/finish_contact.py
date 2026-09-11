"""Resume a saved contact guess, then independently verify tight equilibrium."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
D=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--initial',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--label',required=True);ap.add_argument('--discovery-seconds',type=float,default=240);ap.add_argument('--tight-seconds',type=float,default=120);args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);start=time.perf_counter();record={'status':'RUNNING','steps':[]}
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='1')
    def run(name,cmd):
        tick=time.perf_counter()
        with (args.output/(name+'.log')).open('w') as log:r=subprocess.run([str(v) for v in cmd],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=900)
        record['steps'].append(dict(name=name,returncode=r.returncode,seconds=time.perf_counter()-tick));assert r.returncode==0
    def solve(name,initial,rtol,limit,seconds):
        run(name,[sys.executable,D/'gpu_demo_solve.py','--geometry',args.run/'geometry','--adaptive',args.run/'adaptive','--output',args.output/name,'--initial',initial/'master_u.npy','--initial-active',initial/'active_wall_indices.npy','--coarse-ratio','8','--coarse-sweeps','6','--linear-rtol',rtol,'--true-residual-limit',limit,'--maxiter','9000','--max-seconds',seconds])
        result=json.loads((args.output/name/'solve.json').read_text())
        assert result['status']=='CONTACT_SCREEN_AT_STATED_TOLERANCE_ERODED_MATERIAL_ONLY', result['status']
        return sorted((args.output/name).glob('contact-[0-9][0-9]'))[-1]
    try:
        initial=solve('discovery',args.initial,'1e-4','1.01e-4',args.discovery_seconds)
        solve('solve',initial,'1e-5','1.01e-5',args.tight_seconds)
        run('audit',[sys.executable,D/'report_gpu_g.py','--geometry',args.run/'geometry','--adaptive',args.run/'adaptive','--result',args.output/'solve','--output',args.output/'audit','--compare',args.output/'discovery','--label',args.label])
        record['status']='CONTACT_SCREEN_AT_STATED_TOLERANCE_ERODED_MATERIAL_ONLY'
    except BaseException:
        record['status']='FAIL_COMPLETION_ATTEMPT';raise
    finally:
        record['elapsed_seconds']=time.perf_counter()-start
        (args.output/'completion.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)

if __name__=='__main__':main()
