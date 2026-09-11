"""Transfer a converged displacement/contact guess; never transfer a verdict.

Exact lattice matches retain the old displacement. New material uses a nearest
node guess. Split-node ambiguities are counted, not used to join new geometry.
The new operator must independently solve its own loads and contact problem.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from scipy.sparse import load_npz
from scipy.spatial import cKDTree


def transfer(old_p,new_p,old_u,spacing):
    lower=np.minimum(old_p.min(axis=0),new_p.min(axis=0))
    old=np.rint((old_p-lower)/spacing).astype(np.int32)
    new=np.rint((new_p-lower)/spacing).astype(np.int32)
    assert np.max(abs(old*spacing+lower-old_p))<1e-8
    assert np.max(abs(new*spacing+lower-new_p))<1e-8
    shape=np.maximum(old.max(axis=0),new.max(axis=0))+1
    key=np.ravel_multi_index(old.T,shape);target=np.ravel_multi_index(new.T,shape)
    order=np.argsort(key,kind='stable');sorted_key=key[order]
    where=np.searchsorted(sorted_key,target)
    safe=np.minimum(where,len(order)-1)
    matched=(where<len(order))&(sorted_key[safe]==target)
    source=order[safe]
    distance=np.zeros(len(new))
    if not matched.all():
        distance[~matched],source[~matched]=cKDTree(old_p).query(new_p[~matched],workers=2)
    values=old_u[source].copy()
    duplicate=np.r_[False,np.diff(sorted_key)==0]
    ambiguous=np.isin(target,np.unique(sorted_key[duplicate]))
    return values,{'exact_coordinate_matches':int(matched.sum()),'target_nodes':len(new),
                   'nearest_guesses':int((~matched).sum()),'maximum_nearest_distance_mm':float(distance.max()),
                   'ambiguous_split_coordinate_guesses':int(ambiguous.sum())}


def main():
    ap=argparse.ArgumentParser()
    for key in ['old-geometry','old-adaptive','old-state','geometry','adaptive','output']:
        ap.add_argument('--'+key,type=Path,required=True)
    args=ap.parse_args();start=time.perf_counter()
    assert not args.output.exists();args.output.mkdir(parents=True)
    with np.load(args.old_geometry/'geometry.npz') as data:old_p=data['p'];spacing=data['spacing']
    old_u=load_npz(args.old_adaptive/'prolongation.npz')@np.load(args.old_state/'master_u.npy').reshape(-1,3)
    with np.load(args.geometry/'geometry.npz') as data:new_p=data['p'];assert np.array_equal(data['spacing'],spacing)
    with np.load(args.adaptive/'adaptive.npz') as data:master=data['master']
    values,report=transfer(old_p,new_p[master],old_u,spacing)
    with np.load(args.old_geometry/'interfaces.npz') as data:
        active_p=old_p[data['wall'][np.load(args.old_state/'active_wall_indices.npy')]]
    with np.load(args.geometry/'interfaces.npz') as data:
        wall_p=new_p[data['wall']];gap=data['gap'];base=data['base']
    # Contact state is only seeded where a new surface node matches an old
    # active surface coordinate and has the same zero installation gap.
    distances,_=cKDTree(active_p).query(wall_p,workers=2)
    active=np.flatnonzero((distances<1e-8)&(gap<1e-12))
    mapping=np.full(len(new_p),-1,dtype=np.int32);mapping[master]=np.arange(len(master))
    assert np.all(mapping[base//3]>=0)
    values.ravel()[3*mapping[base//3]+base%3]=0.
    np.save(args.output/'master_u.npy',values.ravel());np.save(args.output/'active_wall_indices.npy',active)
    report.update({'status':'INITIAL_GUESS_ONLY','active_contact_guesses':len(active),
                   'source_state_sha256':hashlib.sha256((args.old_state/'master_u.npy').read_bytes()).hexdigest(),
                   'elapsed_seconds':time.perf_counter()-start,
                   'scope':'New connectivity, stiffness, load and contact must be recomputed. Nearest or duplicate-coordinate guesses confer no bond credit.'})
    (args.output/'transfer.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
