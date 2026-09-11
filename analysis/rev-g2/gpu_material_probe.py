"""Conservative raw-slice voxel mapping and a manufactured CUDA patch test.

This is an inscribed diagnostic: removed boundary material is measured, never
replaced by weak material. The crop and imposed affine motion are not G loads.
"""
from pathlib import Path
from itertools import product
import argparse
import hashlib
import json
import time

import numpy as np
import shapely
import warp as wp

from plastic_shape import PlasticShape, layer_shapes
from gpu_hex import HexOperator, mesh_from_cells, stress_tensors
from gpu_benchmark import MemorySampler
from validate_gpu_hex import save_fields, equilibrium


def inscribed_cells(shape, lower, upper, spacing):
    """Retain a cell only when its entire volume is in every intersected raw slab."""
    start = time.perf_counter()
    lower,upper,spacing = map(lambda x: np.asarray(x,dtype=float), (lower,upper,spacing))
    counts = np.rint((upper-lower)/spacing).astype(int)
    assert np.all(counts > 0) and np.allclose(lower+counts*spacing,upper,atol=1e-9,rtol=0)
    if np.prod(counts) > 2_000_000:
        raise ValueError('Bounded crop only: refusing more than two million candidate cells')
    ij = np.array(list(product(range(counts[0]),range(counts[1]))))
    lo = lower[:2]+ij*spacing[:2]
    boxes = shapely.box(lo[:,0],lo[:,1],lo[:,0]+spacing[0],lo[:,1]+spacing[1])
    covers = {}
    selected = []
    for k in range(counts[2]):
        z0,z1 = lower[2]+k*spacing[2], lower[2]+(k+1)*spacing[2]
        mask = np.ones(len(ij),dtype=bool)
        covered_height = 0.
        for index,(a,b,raw,_) in enumerate(shape.layers):
            height = min(z1,b)-max(z0,a)
            if height <= 1e-10:
                continue
            covered_height += height
            if index not in covers:
                covers[index] = shapely.covers(raw,boxes)
            mask &= covers[index]
        if abs(covered_height-spacing[2]) > 1e-9:
            mask[:] = False
        if np.any(mask):
            selected.append(np.column_stack([ij[mask],np.full(mask.sum(),k)]))
    cells = np.concatenate(selected) if selected else np.empty((0,3),dtype=int)
    crop = shapely.box(lower[0],lower[1],upper[0],upper[1])
    exact = sum(raw.intersection(crop).area*max(0.,min(b,upper[2])-max(a,lower[2]))
                for a,b,raw,_ in shape.layers)
    volume = len(cells)*float(np.prod(spacing))
    assert volume <= exact+1e-8
    return cells,{"spacing_mm":spacing.tolist(),"crop_lower_mm":lower.tolist(),"crop_upper_mm":upper.tolist(),
                  "candidate_cells":int(np.prod(counts)),"retained_cells":len(cells),
                  "raw_slice_crop_volume_mm3":exact,"inscribed_volume_mm3":volume,
                  "omitted_boundary_material_mm3":exact-volume,
                  "omitted_fraction":(exact-volume)/exact if exact else 0.,
                  "extra_material_volume_mm3":0.,"mapping_seconds":time.perf_counter()-start,
                  "policy":"Every retained XY cell is covered by every raw slab intersecting its Z interval; no centroid rule, closing, pore fill, density floor, or thick-bridge credit."}


def bridge_fixture():
    # Two structural beads with a thick bridge that would join them if credited.
    data = {'paths':np.array([[[0,0],[1,0]],[[2,0],[3,0]],[[.8,0],[2.2,0]]],dtype=float),
            'width':np.array([.4,.4,.4]),'top':np.array([.2,.2,.4]),
            'height':np.array([.2,.2,.4]),'structural':np.array([True,True,False])}
    layers = layer_shapes(data,workers=1,simplify_mm=0.,close_gap_mm=0.,
                          homogenize_holes_mm2=0.,coordinate_grid_mm=0.)
    shape = PlasticShape(layers)
    cells,report = inscribed_cells(shape,(0,-.2,0),(3,.2,.4),(.1,.1,.2))
    assert not np.any((cells[:,0] >= 12)&(cells[:,0] < 18)) and np.all(cells[:,2] == 0)
    p,t,topology = mesh_from_cells(cells,(.1,.1,.2),(0,-.2,0))
    # Components are counted using cell/node incidence, including split nodes.
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    rows = np.repeat(np.arange(len(t)),8)
    incidence = coo_matrix((np.ones(t.size),(rows,t.ravel())),shape=(len(t),len(p))).tocsr()
    components,_ = connected_components(incidence@incidence.T,directed=False)
    assert components == 2
    return {"status":"PASS","material_components":int(components),
            "bridge_only_cells":0,"note":"Supplied credited-path mask exercises the existing layer_shapes exclusion; upstream G-code classification is covered by the preserved slice validation.",
            **report,**topology}


def probe(shape,spacing,out):
    lower,upper = (140.,-34.,0.),(148.,-26.,24.)
    cells,mapping = inscribed_cells(shape,lower,upper,spacing)
    start = time.perf_counter()
    p,t,topology = mesh_from_cells(cells,spacing,lower)
    topology['mesh_build_seconds'] = time.perf_counter()-start
    op = HexOperator(p,t,spacing)
    # Impose affine motion on every material boundary, including cavity walls.
    # Interior nodes remain free. This supports disconnected particles only as
    # part of this manufactured fixture; none are removed or bonded artificially.
    faces = np.array([[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
    tri = t[:,faces].reshape(-1,4)
    _,index,count = np.unique(np.sort(tri,axis=1),axis=0,return_index=True,return_counts=True)
    boundary = np.unique(tri[index[count == 1]])
    fixed = (3*boundary[:,None]+np.arange(3)).ravel()
    free = np.setdiff1d(np.arange(p.size),fixed)
    A = np.array([[.001,.0003,-.0002],[.0003,-.0004,.0001],[-.0002,.0001,.0006]])
    exact = ((p-np.array(lower))@A.T).ravel()
    prescribed = np.zeros(p.size)
    prescribed[fixed] = exact[fixed]
    f = np.zeros(p.size)
    with MemorySampler() as memory:
        u,r,solve = op.solve(f,fixed,prescribed)
        stress = op.stress(u)
    error = float(np.max(np.abs(u-exact)))
    sigma = 1000/1.35*A+1000*.35/(1.35*.3)*np.trace(A)*np.eye(3)
    stress_error = float(np.max(np.abs(stress_tensors(stress)-sigma)))
    label = 'g-crop-h'+str(spacing[0]).replace('.','p')
    fields = save_fields(out,label,p,t,u,f,r,stress,spacing,exact_u=exact.reshape(-1,3),
                         fixed_dofs=fixed,cells=cells,gauss_offsets_mm=op.q)
    balance = equilibrium(p,f,r,free)
    passed = (len(free) > 0 and error < 1e-8 and stress_error < 1e-5
              and max(balance['force_error_N'],balance['moment_error_Nmm']) < 1e-5)
    report = {"status":"PASS_NUMERICAL_PATCH_ONLY" if passed else "FAIL_NUMERICAL_PATCH",**mapping,**topology,**fields,
              "interior_free_dofs":len(free),"max_displacement_error_mm":error,
              "max_stress_error_MPa":stress_error,"solve":solve,"equilibrium":balance,
              "memory":memory.report(),"warp_cuda_mempool_used_high_bytes":wp.get_mempool_used_mem_high('cuda:0'),
              "load_scope":"Manufactured affine displacement on all material surfaces of an 8x8x24 mm G crop. Not bracket seat loads or physical fixing/contact conditions.",
              "geometry_scope":"Inscribed voxel approximation omits the reported boundary material; it is not accepted as the complete printed shape."}
    (out/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    assert passed, 'Material crop failed its numerical patch gates; fields retained'
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shape',type=Path,default=Path('analysis/rev-g2/g-recheck/2w-5layers/validated-shape'))
    ap.add_argument('--output',type=Path,default=Path('analysis/rev-g2/gpu-validation'))
    ap.add_argument('--h',type=float,nargs='+',default=[.4,.2])
    args = ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    wp.init()
    shape = PlasticShape.load(args.shape)
    report = {'status':'INCOMPLETE','source_layer_sha256':hashlib.sha256((args.shape/'layers.json.gz').read_bytes()).hexdigest(),
              'bridge_fixture':bridge_fixture(),'probes':[]}
    try:
        for h in args.h:
            report['probes'].append(probe(shape,(h,h,.2),args.output))
        report['status'] = 'PASS_NUMERICAL_PATCH_ONLY'
    finally:
        (args.output/'material-probe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
