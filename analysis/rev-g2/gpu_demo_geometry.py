"""Bounded whole-G inscribed voxels; CPU preparation without tetrahedral meshing.

All occupied cells survive, including disconnected fragments. Local vertex
incidence masks split edge/corner-only bonds, matching gpu_hex.mesh_from_cells.
"""
from pathlib import Path
from itertools import product
import argparse
import hashlib
import json
import time

import numpy as np
import shapely
from scipy.ndimage import label

from plastic_shape import PlasticShape
from gpu_hex import CORNERS

# Outward oriented hexahedron faces: -X,+X,-Y,+Y,-Z,+Z.
FACES = np.array([[0,4,7,3],[1,2,6,5],[0,1,5,4],[3,7,6,2],[0,3,2,1],[4,5,6,7]])
NORMALS = np.array([[-1,0,0],[1,0,0],[0,-1,0],[0,1,0],[0,0,-1],[0,0,1]])


def incidence_table():
    counts = np.zeros(256,dtype=np.uint8)
    groups = np.full((256,8),-1,dtype=np.int8)
    adjacent = np.abs(CORNERS[:,None]-CORNERS[None,:]).sum(axis=2) == 1
    for mask in range(256):
        remaining = {i for i in range(8) if mask & (1 << i)}
        while remaining:
            seed = min(remaining)
            remaining.remove(seed)
            queue = [seed]
            groups[mask,seed] = counts[mask]
            while queue:
                current = queue.pop()
                for j in list(remaining):
                    if adjacent[current,j]:
                        remaining.remove(j)
                        queue.append(j)
                        groups[mask,j] = counts[mask]
            counts[mask] += 1
    return counts,groups


def fast_mesh(occupancy,spacing,origin):
    start = time.perf_counter()
    counts,groups = incidence_table()
    shape = np.array(occupancy.shape)
    mask = np.zeros(shape+1,dtype=np.uint8)
    for c,offset in enumerate(CORNERS):
        sl = tuple(slice(int(o),int(o+n)) for o,n in zip(offset,shape))
        mask[sl] |= occupancy.astype(np.uint8)*np.uint8(1 << c)
    n = int(counts[mask].sum(dtype=np.int64))
    assert n < 2**31
    starts = np.cumsum(counts[mask].ravel(),dtype=np.int32).reshape(mask.shape)
    starts -= counts[mask]
    vertices = np.flatnonzero(mask)
    vertices = np.repeat(vertices,counts[mask.ravel()[vertices]])
    p = np.column_stack(np.unravel_index(vertices,mask.shape))*spacing+origin
    cells = np.argwhere(occupancy).astype(np.int32)
    t = np.empty((len(cells),8),dtype=np.int32)
    for c,offset in enumerate(CORNERS):
        index = tuple((cells+offset).T)
        t[:,c] = starts[index]+groups[mask[index],c]
    report = {'nodes':n,'cells':len(cells),
              'split_edge_corner_vertices':int(np.count_nonzero(counts[mask] > 1)),
              'mesh_build_seconds':time.perf_counter()-start}
    return p,t,cells,report


def boundary_faces(occupancy,t,spacing):
    ids = np.full(occupancy.shape,-1,dtype=np.int32)
    ids[occupancy] = np.arange(len(t),dtype=np.int32)
    pad = np.pad(occupancy,1)
    faces,normal,owners = [],[],[]
    for side,direction in enumerate(NORMALS):
        sl = tuple(slice(int(1+d),int(1+d+n)) for d,n in zip(direction,occupancy.shape))
        selected = occupancy & ~pad[sl]
        cell = ids[selected]
        faces.append(t[cell][:,FACES[side]])
        owners.append(cell)
        normal.append(np.tile(direction,(len(cell),1)))
    faces = np.concatenate(faces)
    normal = np.concatenate(normal)
    axis = np.argmax(abs(normal),axis=1)
    area = np.prod(spacing)/np.asarray(spacing)[axis]
    return faces,normal,area,np.concatenate(owners)


def build(shape,spacing,progress=lambda event:None,max_seconds=180,max_grid_cells=70_000_000):
    start = time.perf_counter()
    spacing = np.asarray(spacing,dtype=float)
    bounds = np.asarray([r[2].bounds for r in shape.layers if not r[2].is_empty])
    lower = np.r_[bounds[:,:2].min(axis=0),shape.z0.min()]
    upper = np.r_[bounds[:,2:].max(axis=0),shape.z1.max()]
    origin = np.floor(lower/spacing)*spacing
    count = np.ceil((upper-origin)/spacing).astype(int)
    assert np.prod(count) <= max_grid_cells,'Dense preparation budget exceeded'
    occupancy = np.zeros(count,dtype=bool)
    ij = np.array(list(product(range(count[0]),range(count[1]))))
    lo = origin[:2]+ij*spacing[:2]
    boxes = shapely.box(lo[:,0],lo[:,1],lo[:,0]+spacing[0],lo[:,1]+spacing[1])
    cached = {}
    for k in range(count[2]):
        z0,z1 = origin[2]+k*spacing[2],origin[2]+(k+1)*spacing[2]
        keep = np.ones(len(boxes),dtype=bool)
        covered = 0.
        for index,(a,b,raw,_) in enumerate(shape.layers):
            overlap = min(z1,b)-max(z0,a)
            if overlap <= 1e-10:
                continue
            covered += overlap
            if index not in cached:
                cached[index] = shapely.covers(raw,boxes)
            keep &= cached[index]
        if abs(covered-spacing[2]) > 1e-9:
            keep[:] = False
        occupancy[:,:,k] = keep.reshape(count[:2])
        # At most the adjacent slabs need to remain cached for the next Z cell.
        cached = {i:v for i,v in cached.items() if shape.layers[i][1] > z1+1e-10}
        if k%10 == 0 or k == count[2]-1:
            progress({'stage':'mapping','layer':k+1,'layers':int(count[2]),
                      'elapsed_seconds':time.perf_counter()-start})
        if time.perf_counter()-start > max_seconds:
            raise TimeoutError('Whole-G material mapping time budget exceeded')
    volume = int(occupancy.sum())*float(np.prod(spacing))
    raw_volume = shape.volume()
    components,ncomponents = label(occupancy)  # six-neighbour face connectivity
    sizes = np.bincount(components[occupancy])
    component_ids = components[occupancy]-1
    del components
    report = {'spacing_mm':spacing.tolist(),'origin_mm':origin.tolist(),
              'grid_shape':count.tolist(),'grid_cells':int(np.prod(count)),
              'raw_nominal_volume_mm3':raw_volume,'retained_volume_mm3':volume,
              'omitted_fraction':1-volume/raw_volume,'extra_material_volume_mm3':0.,
              'material_components':ncomponents,'component_cell_counts':sizes[1:].tolist(),
              'mapping_and_components_seconds':time.perf_counter()-start,
              'policy':'Only full cells covered by every intersected raw slab; no bridge, pore-fill, closing or weak-void stiffness. Every retained cell, including disconnected components, survives.'}
    progress({'stage':'mapping_complete',**{k:report[k] for k in ['retained_volume_mm3','omitted_fraction','material_components']}})
    return occupancy,component_ids,origin,report


def validate_lookup():
    from gpu_hex import mesh_from_cells
    # Every possible local occupancy mask, compared by its cell-corner ties.
    for mask in range(1,256):
        cells = CORNERS[[bool(mask & (1 << i)) for i in range(8)]]
        occupancy = np.zeros((2,2,2),dtype=bool)
        occupancy[tuple(cells.T)] = True
        p,t,ordered,_ = fast_mesh(occupancy,np.array([.3,.4,.2]),np.zeros(3))
        refp,reft,_ = mesh_from_cells(ordered,(.3,.4,.2))
        assert len(p) == len(refp)
        for i in range(len(t)):
            for j in range(i,len(t)):
                assert np.array_equal(t[i,:,None] == t[j,None,:],reft[i,:,None] == reft[j,None,:])
        faces,normal,area,_ = boundary_faces(occupancy,t,(.3,.4,.2))
        volume = np.einsum('ij,ij->i',p[faces].mean(axis=1),normal)*area/3
        assert abs(volume.sum()-len(t)*.3*.4*.2) < 1e-12
    return {'status':'PASS','local_occupancy_patterns':255,
            'checks':['All cell-corner bonds match original audited constructor','Oriented boundary divergence matches material volume']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shape',type=Path,default=Path('analysis/rev-g2/g-recheck/2w-5layers/validated-shape'))
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--h',type=float,default=.8)
    ap.add_argument('--hz',type=float,default=.2)
    ap.add_argument('--max-grid-cells',type=int,default=70_000_000)
    ap.add_argument('--max-seconds',type=float,default=180)
    args = ap.parse_args()
    assert args.h > 0 and args.hz > 0
    assert not args.output.exists(),'Use a fresh output directory to retain previous evidence'
    args.output.mkdir(parents=True)
    def progress(event):
        print(json.dumps(event),flush=True)
        (args.output/'progress.json').write_text(json.dumps(event,indent=2)+'\n')
    fixture = validate_lookup()
    shape = PlasticShape.load(args.shape)
    spacing = np.array([args.h,args.h,args.hz])
    occupancy,components,origin,report = build(shape,spacing,progress,args.max_seconds,args.max_grid_cells)
    report['lookup_validation'] = fixture
    report['layer_cache_sha256'] = hashlib.sha256((args.shape/'layers.json.gz').read_bytes()).hexdigest()
    p,t,cells,mesh_report = fast_mesh(occupancy,spacing,origin)
    faces,normal,area,owners = boundary_faces(occupancy,t,spacing)
    report.update(mesh_report)
    report['boundary_faces'] = len(faces)
    report['status'] = 'ERODED_GEOMETRY_DIAGNOSTIC; NOT A QUALIFIED PRINT MODEL'
    np.savez(args.output/'geometry.npz',p=p,t=t,cells=cells,component=components,
             faces=faces,normal=normal,area=area,owners=owners,spacing=spacing,origin=origin)
    (args.output/'geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    progress({'stage':'geometry_complete','cells':len(t),'nodes':len(p),'components':report['material_components']})


if __name__ == '__main__':
    main()
