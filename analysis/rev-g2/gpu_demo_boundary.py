"""Bounded quadtree boundary-refinement census over actual raw slice slabs.

Entirely covered rectangles stay coarse. Only boundary-crossing rectangles
split; unresolved crossing cells are omitted at each reported finest scale.
No material is filled, closed, homogenized, or bridged. This is a geometry
census; multilevel grading/constraints and a mechanical error estimator are
not implemented by this script.
"""
from pathlib import Path
import argparse
import json
import time

import numpy as np
import shapely

from plastic_shape import PlasticShape


def census(shape,base=.8,levels=5,max_seconds=180):
    start = time.perf_counter()
    counts = np.zeros(levels+1,dtype=np.int64)
    volumes = np.zeros(levels+1)
    refined = np.zeros(levels+1,dtype=np.int64)
    bounds = np.array([layer[2].bounds for layer in shape.layers])
    lower = np.floor(bounds[:,:2].min(axis=0)/base)*base
    upper = bounds[:,2:].max(axis=0)
    n = np.ceil((upper-lower)/base).astype(int)
    grid = np.column_stack(np.unravel_index(np.arange(np.prod(n)),n))
    corners = np.array([[0,0],[1,0],[0,1],[1,1]])
    for slab,(z0,z1,raw,_) in enumerate(shape.layers):
        index = grid
        for level in range(levels+1):
            h = base/2**level
            xy = lower+index*h
            boxes = shapely.box(xy[:,0],xy[:,1],xy[:,0]+h,xy[:,1]+h)
            inside = shapely.covers(raw,boxes)
            count = int(inside.sum())
            counts[level] += count
            volumes[level] += count*h*h*(z1-z0)
            partial = ~inside & shapely.intersects(raw,boxes)
            refined[level] += int(partial.sum())
            index = (2*index[partial,None,:]+corners[None]).reshape(-1,2)
        if slab%10 == 0 or slab == len(shape.layers)-1:
            print(json.dumps({'stage':'boundary_census','slab':slab+1,'slabs':len(shape.layers),
                              'elapsed_seconds':time.perf_counter()-start}),flush=True)
        if time.perf_counter()-start > max_seconds:
            raise TimeoutError('Boundary census budget exceeded')
    cumulative = volumes.cumsum()
    return {'status':'PASS_GEOMETRY_CENSUS_ONLY','raw_volume_mm3':shape.volume(),
            'elapsed_seconds':time.perf_counter()-start,
            'levels':[{'boundary_xy_mm':base/2**i,'retained_volume_mm3':float(cumulative[i]),
                       'omitted_fraction':float(1-cumulative[i]/shape.volume()),
                       'fully_inside_leaf_prisms':int(counts[:i+1].sum()),
                       'unresolved_crossing_prisms':int(refined[i]),
                       'uniform_fine_equivalent_cells':int(round(sum(counts[j]*4**(i-j) for j in range(i+1))))}
                      for i in range(levels+1)],
            'scope':'Raw layer slabs and only fully covered XY cells; no added material. Counts precede mesh grading, hanging-node constraints, interface protection, and mechanical refinement. Not a mechanics-ready mesh or speedup measurement.'}


def validate():
    from types import SimpleNamespace
    shapes = [shapely.box(0,0,4,4).difference(shapely.box(1,1,3,3)),
              shapely.union(shapely.box(.03,.02,1.995,4.01),shapely.box(2.005,.02,4.01,4.01))]
    results = []
    for raw in shapes:
        model = SimpleNamespace(layers=[(0.,.2,raw,raw)],volume=lambda:raw.area*.2)
        result = census(model)
        for row in result['levels']:
            h = row['boundary_xy_mm']
            lower = np.floor(np.array(raw.bounds[:2])/.8)*.8
            size = np.ceil((np.array(raw.bounds[2:])-lower)/h).astype(int)
            ij = np.column_stack(np.unravel_index(np.arange(np.prod(size)),size))
            xy = lower+ij*h
            boxes = shapely.box(xy[:,0],xy[:,1],xy[:,0]+h,xy[:,1]+h)
            cells = int(shapely.covers(raw,boxes).sum())
            assert cells == row['uniform_fine_equivalent_cells']
            assert abs(cells*h*h*.2-row['retained_volume_mm3']) < 1e-10
            assert row['retained_volume_mm3'] <= model.volume()+1e-10
        results.append(result)
    return {'status':'PASS','checks':'Independent uniform full-cell coverage agrees at all six scales for an enclosed hole and a 0.01 mm separating gap. No material added.', 'fixtures':results}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--shape',type=Path,default=Path('analysis/rev-g2/g-recheck/2w-5layers/validated-shape'))
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--levels',type=int,default=5)
    ap.add_argument('--fixtures-only',action='store_true')
    args = ap.parse_args()
    assert not args.output.exists(),'Retain earlier evidence'
    result = validate() if args.fixtures_only else census(PlasticShape.load(args.shape),levels=args.levels)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
