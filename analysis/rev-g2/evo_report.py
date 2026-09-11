"""Publish compact evolutionary-search receipts without deleting raw evidence."""
from pathlib import Path
import argparse,hashlib,json,shutil
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--batch',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--refine',type=Path,action='append',default=[])
    args=ap.parse_args();out=args.output;assert not out.exists();out.mkdir(parents=True)
    for name in ['summary.json','ledger.json','scores.csv','verification.json']:
        shutil.copyfile(args.batch/name,out/name)
    ledger=json.loads((args.batch/'ledger.json').read_text());summary=json.loads((args.batch/'summary.json').read_text())
    rows=ledger['records'];selected={r['id']:r['role'] for r in summary['selected_for_actual_slice_3d']}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    x=np.array([r['metrics']['nominal_material_proxy_mm3'] for r in rows])*100-100
    y=np.array([r['metrics']['maximum_movement_mm'] for r in rows])*100-100
    gen=np.array([r['generation'] for r in rows])+1
    sc=ax[0].scatter(x,y,c=gen,cmap='viridis',vmin=1,vmax=4,s=35,alpha=.8)
    ax[0].scatter([0],[0],marker='X',s=120,c='black',label='G control')
    for i,r in enumerate(rows):
        if r['id'] in selected:ax[0].annotate(selected[r['id']],(x[i],y[i]),xytext=(5,5),textcoords='offset points',fontsize=8)
    ax[0].axhline(0,color='.7',lw=.8);ax[0].axvline(0,color='.7',lw=.8)
    ax[0].set(xlabel='Estimated structural material change (%)',ylabel='Reduced-model movement change (%)',title='100 helper proposals; lower is stiffer')
    ax[0].legend();fig.colorbar(sc,ax=ax[0],ticks=[1,2,3,4],label='Generation')
    ax[1].scatter(y,[r['metrics']['inner_seat_raw_peak_MPa']*100-100 for r in rows],c=gen,cmap='viridis',vmin=1,vmax=4,s=35,alpha=.8)
    ax[1].axhline(0,color='.7',lw=.8);ax[1].axvline(0,color='.7',lw=.8)
    ax[1].set(xlabel='Reduced-model movement change (%)',ylabel='Inner-seat regional raw peak change (%)',title='Stiffer does not automatically mean lower stress')
    fig.suptitle('G-anchored 2D screen: proposals require actual slicing and 3D confirmation',fontsize=11)
    fig.savefig(out/'search.png',dpi=160);plt.close(fig)
    refined=[]
    for folder in args.refine:
        pipeline=json.loads((folder/'pipeline.json').read_text());name=pipeline['candidate_id'];target=out/name;target.mkdir()
        for rel in ['pipeline.json','slice/replay.json','slice/modifier-role-check.json','shape/shape-verification.json','geometry/geometry.json','geometry/interfaces.json',
                    'adaptive/adaptive.json','initial/transfer.json','solve/solve.json','audit/audit.json','audit/g-results.png','audit/projection.npz']:
            source=folder/rel
            if source.exists():
                dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        refined.append({'id':name,'pipeline':pipeline,'solve':json.loads((folder/'solve/solve.json').read_text()) if (folder/'solve/solve.json').exists() else None})
    failed=args.batch.parent/'batch-01';failure_ledger=failed/'ledger.json'
    failure={'status':'EXCLUDED_EXPLORATORY_BATCH','reason':'Initial 0.05 mm rounding could turn a nominal 10 percent change into 11.11 percent. Stopped, preserved, and replaced by quantized admissible 5-10 percent mutations.',
             'completed_proposals':len(json.loads(failure_ledger.read_text())['records']) if failure_ledger.exists() else 0,
             'ledger_sha256':hashlib.sha256(failure_ledger.read_bytes()).hexdigest() if failure_ledger.exists() else None,
             'interrupted_candidate_fields':'Incomplete after explicit interrupt; completed proposals and the raw interrupt log remain local.'}
    (out/'preserved-exploratory-failure.json').write_text(json.dumps(failure,indent=2)+'\n')
    receipt={'screened':len(rows),'screen_seconds':summary['elapsed_seconds'],'refined':refined,
             'raw_field_retention':'Every reduced field and all 3D stress chunks remain in ignored local evidence; published ledgers and solve receipts identify their hashes.',
             'predictive_ranking':'Compare actual-slice 3D outcomes before claiming a reliable surrogate. One baseline calibration alone does not validate ordering.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
