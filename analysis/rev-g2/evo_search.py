"""Bounded, reproducible helper search with explicit unbuilt proposal status."""
from pathlib import Path
import argparse,csv,hashlib,json,time
import numpy as np
from evo_screen import Screen,BASE,GENES,D,ROOT


def ident(values):
    return hashlib.sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest()[:12]


def mutation(rng,parent):
    child=np.array(parent,dtype=float)
    for k in rng.choice(len(GENES),size=int(rng.integers(1,4)),replace=False):
        base=BASE[GENES[k]]
        options=np.arange(np.ceil(base*.8/.05),np.floor(base*1.2/.05)+1)*.05
        ratio=abs(options/child[k]-1)
        options=options[(ratio>=.05-1e-9)&(ratio<=.1+1e-9)]
        if len(options):child[k]=rng.choice(options)
    return [round(float(v),2) for v in child]


def seed_change(value,sign):
    options=np.arange(np.floor(value*.9/.05),np.ceil(value*1.1/.05)+1)*.05
    changes=(options/value-1)*sign
    options=options[(changes>=.05-1e-9)&(changes<=.1+1e-9)]
    assert len(options)
    return round(float(options[np.argmax(abs(options/value-1))]),2)


def metrics(row,baseline,reference_3d,fitness='legacy-stress-proxy'):
    r=row['result']
    values={key:r[key]/baseline[key] for key in ['nominal_material_proxy_mm3','maximum_movement_mm','raw_peak_tensile_MPa','inner_seat_raw_peak_MPa','compliance_Nmm']}
    values['G_calibrated_movement_indicator_mm']=reference_3d*values['maximum_movement_mm']
    values['breeding_score']=values['nominal_material_proxy_mm3']+12*max(0,values['G_calibrated_movement_indicator_mm']/4-1)**2
    if fitness=='legacy-stress-proxy':
        values['breeding_score']+=2*max(0,values['raw_peak_tensile_MPa']-1)**2+2*max(0,values['inner_seat_raw_peak_MPa']-1)**2
    values['fitness_policy']=fitness
    values['stress_inspection_flags']={'global_raw_peak_increased':values['raw_peak_tensile_MPa']>1,
                                       'inner_seat_raw_peak_increased':values['inner_seat_raw_peak_MPa']>1}
    values['interpretation']='Ratios and a single-baseline movement indicator for screening only; predictive ordering requires actual-slice 3D checks.'
    return values


def run(output,cache,seconds=1200,count=100,seed=20260911,fitness='movement-material'):
    assert not output.exists();output.mkdir(parents=True)
    rng=np.random.default_rng(seed);started=time.perf_counter();model=Screen(cache)
    baseline=model.evaluate(BASE,output/'baseline')
    assert baseline['status']=='PASS_REDUCED_CONTACT'
    reference=model.reference_3d['maximum_resultant_displacement_mm']
    records=[];seen=set();base=[BASE[k] for k in GENES];generation=0
    baseline_id=ident(base);seen.add(baseline_id)
    intentions={
        'bottom_band':'Test whether lower-chord plastic can be moved to the seat transition.',
        'diagonal_band':'Test knee/diagonal stiffness and its cost.',
        'seat_band':'Test reinforcement at the measured inner-seat/forearm hotspot.',
        'front_seat_band':'Test outer-seat support and lip movement.',
        'lower_tunnel_collar_mm':'Test the heavily loaded lower fixing region.',
        'upper_tunnel_collar_mm':'Test trimming the lightly loaded upper fixing region.'}
    while len(records)<count and time.perf_counter()-started<seconds:
        batch=[]
        if generation==0:
            for k,key in enumerate(GENES):
                for sign in [-1,1]:
                    child=base.copy();child[k]=seed_change(child[k],sign)
                    batch.append((child,[baseline_id],intentions[key]))
        valid=[r for r in records if r['result']['status']=='PASS_REDUCED_CONTACT']
        elite=sorted(valid,key=lambda r:r['metrics']['breeding_score'])[:max(6,len(valid)//4)]
        while len(batch)<25:
            if elite and rng.random()<.75:
                first=elite[int(rng.integers(len(elite)))];parent=first['values'];parents=[first['id']]
                if rng.random()<.35:
                    second=elite[int(rng.integers(len(elite)))];parent=np.where(rng.random(len(GENES))<.5,parent,second['values']).tolist();parents.append(second['id'])
                child=mutation(rng,parent);reason='Retain promising allocations, recombine and make bounded local mutations.'
            else:
                child=mutation(rng,base);parents=[baseline_id];reason='Independent exploration around G to preserve diversity.'
            if ident(child) not in seen and ident(child) not in {ident(v[0]) for v in batch}:
                batch.append((child,parents,reason))
        for child,parents,reason in batch:
            if len(records)>=count or time.perf_counter()-started>=seconds:break
            name=ident(child)
            if name in seen:continue
            seen.add(name);params={**BASE,**dict(zip(GENES,child)), 'name':'evo-'+name}
            result=model.evaluate(params,output/name,max_seconds=min(30,seconds-(time.perf_counter()-started)))
            field=output/name/'fields.npz'
            row={'id':name,'generation':generation,'values':child,'parents':parents,'seed_reason':reason,
                 'cad_status':'UNBUILT_STAGE_1_HELPER_PROPOSAL','result':result,
                 'all_fields_sha256':hashlib.sha256(field.read_bytes()).hexdigest()}
            row['metrics']=metrics(row,baseline,reference,fitness)
            records.append(row)
            (output/'ledger.json').write_text(json.dumps({'seed':seed,'genes':GENES,'fitness_policy':fitness,'baseline':baseline,'records':records},indent=2)+'\n')
            print(json.dumps({'evaluated':len(records),'id':name,'generation':generation,'status':result['status'],
                   'candidate_seconds':result['total_evaluation_seconds'],'elapsed_seconds':time.perf_counter()-started,
                   'volume_ratio':row['metrics']['nominal_material_proxy_mm3'],'movement_indicator_mm':row['metrics']['G_calibrated_movement_indicator_mm']}),flush=True)
        generation+=1
    good=[r for r in records if r['result']['status']=='PASS_REDUCED_CONTACT']
    balanced=min(good,key=lambda r:r['metrics']['breeding_score'])
    stiffest=min((r for r in good if r['id']!=balanced['id']),key=lambda r:r['metrics']['maximum_movement_mm'])
    economical=[r for r in good if r['id'] not in [balanced['id'],stiffest['id']] and r['metrics']['maximum_movement_mm']<1.03 and (fitness!='legacy-stress-proxy' or r['metrics']['raw_peak_tensile_MPa']<1.05)]
    economical=min(economical or [r for r in good if r['id'] not in [balanced['id'],stiffest['id']]],key=lambda r:r['metrics']['nominal_material_proxy_mm3'])
    selected=[{'role':role,'id':r['id'],'parameters':r['result']['parameters'],'metrics':r['metrics']} for role,r in [('balanced',balanced),('stiffest',stiffest),('economical',economical)]]
    summary={'status':'PASS_100_PROPOSAL_THROUGHPUT' if len(records)==count else 'PARTIAL_TIME_BUDGET',
             'requested_proposals':count,'evaluated_proposals':len(records),'baseline_control_evaluated_separately':True,'fitness_policy':fitness,
             'elapsed_seconds':time.perf_counter()-started,'screen_setup_seconds':model.setup_seconds,
             'evaluated_contact_screens':len(good),'numerical_failures':len(records)-len(good),'selected_for_actual_slice_3d':selected,
             'scope':'Throughput and reduced-model numerical checks only. Prediction quality, CAD, slicing, 3D ranking and a winner remain unverified until the subsequent stages.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (output/'scores.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['id','generation','status',*GENES,'volume_ratio','movement_indicator_mm','raw_2d_peak_MPa','inner_seat_ratio','score'])
        for r in records:writer.writerow([r['id'],r['generation'],r['result']['status'],*r['values'],r['metrics']['nominal_material_proxy_mm3'],r['metrics']['G_calibrated_movement_indicator_mm'],r['result']['raw_peak_tensile_MPa'],r['metrics']['inner_seat_raw_peak_MPa'],r['metrics']['breeding_score']])
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cache',type=Path,required=True)
    ap.add_argument('--seconds',type=float,default=1200);ap.add_argument('--count',type=int,default=100);ap.add_argument('--seed',type=int,default=20260911)
    ap.add_argument('--fitness',choices=['movement-material','legacy-stress-proxy'],default='movement-material',
                    help='The pilot used legacy-stress-proxy; actual 3D feedback demoted cheap stresses to inspection flags.')
    args=ap.parse_args();run(args.output,args.cache,args.seconds,args.count,args.seed,args.fitness)
