"""Compare all nodal movements and unfiltered peaks across same-material meshes."""
from pathlib import Path
import argparse,json,time
import numpy as np
from scipy.sparse import load_npz


def main():
    ap=argparse.ArgumentParser()
    for name in ['adaptive','coarse-result','fine-result','output']:
        ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args();start=time.perf_counter();assert not args.output.exists()
    a=json.loads((args.coarse_result/'solve.json').read_text());b=json.loads((args.fine_result/'solve.json').read_text())
    def state(folder,report):return folder/f"contact-{report['contact_history'][-1]['contact_step']:02d}"
    sa,sb=state(args.coarse_result,a),state(args.fine_result,b)
    ua=np.load(sa/'master_u.npy');ub=np.load(sb/'master_u.npy')
    old=load_npz(args.adaptive/'prolongation.npz')@ua.reshape(-1,3)
    new=ub.reshape(-1,3);assert old.shape==new.shape
    delta=np.linalg.norm(new-old,axis=1)
    ca=float(np.load(sa/'master_force.npy')@ua);cb=float(np.load(sb/'master_force.npy')@ub)
    accepted=lambda r:r['status'] in ['CONTACT_SCREEN_AT_STATED_TOLERANCE_ERODED_MATERIAL_ONLY','PASS_CONTACT_NUMERICS_ERODED_MATERIAL_ONLY']
    passed=accepted(a) and accepted(b)
    report={'status':'COMPLETED_SAME_MATERIAL_MESH_SENSITIVITY' if passed else 'UNRESOLVED_FAILED_NUMERICS',
            'all_fine_nodes_compared':len(old),'maximum_nodal_movement_change_mm':float(delta.max()),
            'relative_displacement_l2_change':float(np.linalg.norm(new-old)/np.linalg.norm(new)),
            'adaptive_maximum_movement_mm':a['maximum_resultant_displacement_mm'],'uniform_maximum_movement_mm':b['maximum_resultant_displacement_mm'],
            'adaptive_raw_tensile_peak_MPa':a['raw_tensile_peak_MPa'],'uniform_raw_tensile_peak_MPa':b['raw_tensile_peak_MPa'],
            'adaptive_stress_samples':8*a['leaf_cells'],'uniform_stress_samples':8*b['leaf_cells'],
            'adaptive_compliance_Nmm':ca,'uniform_compliance_Nmm':cb,
            'compliance_monotonicity_check':bool(cb>=ca*(1-1e-6)),
            'elapsed_seconds':time.perf_counter()-start,
            'scope':'Every shared fine-node displacement and both full raw stress maxima are retained. Gauss sampling differs between meshes. This measures coarsening sensitivity on the same inscribed material, not boundary-material convergence or physical qualification.'}
    if passed:assert report['compliance_monotonicity_check'],'Unexpected stiffening after removing constraints; investigate before using result'
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
