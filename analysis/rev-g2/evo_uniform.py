"""Unmerge every adaptive leaf for a same-material 0.2 mm refinement check.

This removes Q1 coarsening constraints without changing any occupied cell or
split bond. It tests discretization sensitivity, not omitted boundary plastic.
"""
from pathlib import Path
import argparse,json,time
import numpy as np
from scipy.sparse import eye,load_npz,save_npz


def main():
    ap=argparse.ArgumentParser()
    for name in ['geometry','from-adaptive','from-state','output']:
        ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args();start=time.perf_counter()
    assert not args.output.exists();args.output.mkdir(parents=True)
    with np.load(args.geometry/'geometry.npz') as data:
        t,cells,spacing,origin=data['t'],data['cells'],data['spacing'],data['origin'];n=len(data['p'])
    P=eye(n,format='csr',dtype=np.float64)
    save_npz(args.output/'prolongation.npz',P,compressed=False)
    np.savez(args.output/'adaptive.npz',t=t,cells=cells,scale=np.ones(len(t),dtype=np.int8),master=np.arange(n,dtype=np.int32))
    u=load_npz(args.from_adaptive/'prolongation.npz')@np.load(args.from_state/'master_u.npy').reshape(-1,3)
    np.save(args.output/'initial_master_u.npy',u.ravel())
    np.save(args.output/'initial_active_wall_indices.npy',np.load(args.from_state/'active_wall_indices.npy'))
    report={'status':'ALL_ORIGINAL_FINE_CELLS_WITH_IDENTITY_CONSTRAINTS','fine_cells':len(t),'leaf_cells':len(t),
            'fine_nodes':n,'independent_nodes':n,'cell_reduction_fraction':0.,'added_or_removed_volume_mm3':0.,
            'retained_volume_mm3':float(len(t)*np.prod(spacing)),'spacing_mm':spacing.tolist(),'origin_mm':origin.tolist(),
            'source_geometry':json.loads((args.geometry/'geometry.json').read_text()),'elapsed_seconds':time.perf_counter()-start,
            'scope':'Same exact inscribed material and split-bond connectivity. Independent solve required. Does not recover omitted boundary material.'}
    (args.output/'adaptive.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_geometry'}),flush=True)


if __name__=='__main__':main()
