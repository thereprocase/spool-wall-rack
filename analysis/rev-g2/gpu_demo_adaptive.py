"""Two-level, volume-preserving hex coarsening with Q1 constraints.

Eight fully occupied sibling voxels may become one rectangular element.
The prolongation P maps independent nodes to ALL original fine nodes,
including hanging edge/face nodes. Material cells are never dropped or filled.
This is a preparation/verification module, not a whole-bracket solve.
"""
from itertools import product
from pathlib import Path
import argparse
import json
import time

import numpy as np
from scipy.sparse import csr_matrix, save_npz

from gpu_hex import CORNERS, element


OFFSETS = np.array(list(product(range(3), repeat=3)), dtype=np.int32)
WEIGHTS = np.prod(np.where(CORNERS[None] == 1,
                          OFFSETS[:,None,:]/2, 1-OFFSETS[:,None,:]/2), axis=2)


def coarsen(p, t, cells, spacing, origin, protect=None):
    """Return leaf connectivity using original node IDs and scalar-node P.

    Only one merge level is permitted, hence neighboring sizes differ by <=2.
    Fine-cell incidence IDs carry the audited separation of edge/corner bonds.
    protect is a boolean per fine cell, for interfaces or refinement studies.
    """
    start = time.perf_counter()
    shape = cells.max(axis=0)+1
    block_shape = (shape+1)//2
    block_key = np.ravel_multi_index((cells//2).T, block_shape)
    count = np.bincount(block_key, minlength=int(np.prod(block_shape)))
    allowed = count == 8
    # Local bond groups can change along a coarse edge: two solid blocks may
    # share a fine midpoint while their endpoints remain separate. Preserve
    # that topology by keeping cells incident to split vertices fine.
    coordinates = np.rint((p-origin)/spacing).astype(np.int32)
    vertex_key = np.ravel_multi_index(coordinates.T,shape+1)
    order = np.argsort(vertex_key,kind='stable')
    duplicates = np.flatnonzero(np.diff(vertex_key[order]) == 0)
    split = np.zeros(len(p),dtype=bool)
    split[order[duplicates]] = True
    split[order[duplicates+1]] = True
    topology_protected = np.zeros(len(t),dtype=bool)
    for corner in range(8):
        topology_protected |= split[t[:,corner]]
    allowed[np.unique(block_key[topology_protected])] = False
    del coordinates,vertex_key,order,split
    if protect is not None:
        allowed[np.unique(block_key[np.asarray(protect,dtype=bool)])] = False
    keys = np.flatnonzero(allowed)
    blocks = 2*np.column_stack(np.unravel_index(keys, block_shape))
    fine_key = np.ravel_multi_index(cells.T, shape)
    assert np.all(np.diff(fine_key) > 0), 'Fine cells must be unique and lexicographically ordered'

    def child_ids(offset):
        query = np.ravel_multi_index((blocks+offset).T, shape)
        index = np.searchsorted(fine_key, query)
        assert np.array_equal(fine_key[index],query)
        return index

    coarse_t = np.empty((len(blocks),8),dtype=np.int32)
    for c,offset in enumerate(CORNERS):
        coarse_t[:,c] = t[child_ids(offset),c]
    owner = np.full(len(p),-1,dtype=np.int32)
    local = np.zeros(len(p),dtype=np.uint8)
    duplicate_checks = 0
    for code,offset in enumerate(OFFSETS):
        if np.all(offset != 1):
            continue  # Eight independent coarse corners.
        child = np.minimum(offset,1)
        corner = int(np.flatnonzero(np.all(CORNERS == offset-child,axis=1))[0])
        nodes = t[child_ids(child),corner]
        old = owner[nodes] >= 0
        # Shared midpoint constraints must use exactly the same master IDs and
        # weights. Do not average inconsistent constraints or connect by XYZ.
        for begin in range(0,len(nodes),65536):
            selected = np.flatnonzero(old[begin:begin+65536])+begin
            if not len(selected):
                continue
            old_code = local[nodes[selected]]
            previous = np.where(WEIGHTS[old_code] > 0,coarse_t[owner[nodes[selected]]],-1)
            current = np.where(WEIGHTS[code] > 0,coarse_t[selected],-1)
            assert np.array_equal(np.sort(previous,axis=1),np.sort(current,axis=1)), 'Inconsistent coarse/fine tie'
            duplicate_checks += len(selected)
        owner[nodes] = np.arange(len(blocks),dtype=np.int32)
        local[nodes] = code
    master = np.flatnonzero(owner < 0)
    master_id = np.full(len(p),-1,dtype=np.int32)
    master_id[master] = np.arange(len(master),dtype=np.int32)
    assert np.all(master_id[coarse_t] >= 0), 'Unexpected constraint dependency'
    slave = np.flatnonzero(owner >= 0)
    lengths = np.ones(len(p),dtype=np.int32)
    lengths[slave] = np.count_nonzero(WEIGHTS[local[slave]],axis=1)
    indptr = np.r_[0,np.cumsum(lengths,dtype=np.int64)]
    assert indptr[-1] < 2**31
    indices = np.empty(indptr[-1],dtype=np.int32)
    values = np.empty(indptr[-1],dtype=np.float64)
    indices[indptr[master]] = master_id[master]
    values[indptr[master]] = 1.
    for code in range(len(OFFSETS)):
        selected = slave[local[slave] == code]
        columns = np.flatnonzero(WEIGHTS[code])
        for j,c in enumerate(columns):
            indices[indptr[selected]+j] = master_id[coarse_t[owner[selected],c]]
            values[indptr[selected]+j] = WEIGHTS[code,c]
    P = csr_matrix((values,indices,indptr.astype(np.int32)),shape=(len(p),len(master)))
    fine = ~allowed[block_key]
    leaf_t = np.concatenate([t[fine],coarse_t])
    scale = np.r_[np.ones(np.count_nonzero(fine),dtype=np.int8),np.full(len(blocks),2,dtype=np.int8)]
    leaf_cells = np.concatenate([cells[fine],blocks]).astype(np.int32)
    assert int(np.sum(scale.astype(np.int64)**3)) == len(cells)
    # Check every node, with no tolerance that could hide a real gap closure.
    assert np.max(abs(P @ p[master]-p)) < 1e-10
    assert np.max(abs(np.asarray(P.sum(axis=1)).ravel()-1)) < 1e-14
    report = {'status':'PASS_TWO_LEVEL_GEOMETRY_AND_CONSTRAINTS',
              'fine_cells':len(cells),'leaf_cells':len(leaf_t),'coarse_cells':len(blocks),
              'cell_reduction_fraction':1-len(leaf_t)/len(cells),
              'fine_nodes':len(p),'independent_nodes':len(master),'interpolated_nodes':len(slave),
              'duplicate_constraints_checked':duplicate_checks,
              'topology_protected_fine_cells':int(np.count_nonzero(topology_protected)),
              'retained_volume_mm3':float(len(cells)*np.prod(spacing)),
              'added_or_removed_volume_mm3':0.,'maximum_neighbor_size_ratio':2,
              'spacing_mm':np.asarray(spacing).tolist(),'origin_mm':np.asarray(origin).tolist(),
              'preparation_seconds':time.perf_counter()-start,
              'scope':'Exact same inscribed voxel union; Q1 interpolation constraints. Does not recover omitted boundary plastic or qualify mechanics.'}
    return {'t':leaf_t,'scale':scale,'cells':leaf_cells,'master':master,'P':P,'report':report}


def energy(p,t,scale,spacing,u):
    """Chunked independent scalar energy integral, retaining all elements."""
    ke,_,_,_ = element(spacing)
    value = 0.
    for begin in range(0,len(t),32768):
        v = u[t[begin:begin+32768]].reshape(-1,24)
        value += float(np.sum(np.einsum('ij,ij->i',v @ ke,v)*scale[begin:begin+32768]))
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--geometry',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--protect-g-interfaces',action='store_true')
    args = ap.parse_args()
    assert not args.output.exists(),'Use a fresh output directory'
    args.output.mkdir(parents=True)
    with np.load(args.geometry/'geometry.npz') as data:
        p,t,cells,spacing,origin = [data[k] for k in ['p','t','cells','spacing','origin']]
    protect = None
    if args.protect_g_interfaces:
        center = (cells+.5)*spacing+origin
        protect = center[:,0] < 5
        for x,y in [(90,0),(190,12)]:
            protect |= np.linalg.norm(center[:,:2]-[x,y],axis=1) < 17
    result = coarsen(p,t,cells,spacing,origin,protect)
    result['report']['protected_g_interfaces'] = args.protect_g_interfaces
    result['report']['source_geometry'] = json.loads((args.geometry/'geometry.json').read_text())
    save_npz(args.output/'prolongation.npz',result['P'],compressed=False)
    np.savez(args.output/'adaptive.npz',**{k:result[k] for k in ['t','scale','cells','master']})
    (args.output/'adaptive.json').write_text(json.dumps(result['report'],indent=2)+'\n')
    print(json.dumps({k:v for k,v in result['report'].items() if k != 'source_geometry'},indent=2),flush=True)


if __name__ == '__main__':
    main()
