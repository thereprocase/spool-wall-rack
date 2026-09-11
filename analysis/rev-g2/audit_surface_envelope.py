"""Bidirectional distance audit for a meshed surface against its input.

Checks every surface vertex and triangle centroid plus deterministic area
samples. This is stronger than volume alone, but remains a sampled bound.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray


def polydata(points, triangles):
    vertices = vtk.vtkPoints()
    vertices.SetData(numpy_to_vtk(np.ascontiguousarray(points, dtype=np.float64), deep=True))
    cells = vtk.vtkCellArray()
    cells.SetData(numpy_to_vtkIdTypeArray(np.arange(0, 3*len(triangles)+1, 3, dtype=np.int64), deep=True),
                  numpy_to_vtkIdTypeArray(np.ascontiguousarray(triangles, dtype=np.int64).ravel(), deep=True))
    result = vtk.vtkPolyData()
    result.SetPoints(vertices)
    result.SetPolys(cells)
    return result


def boundary(cells):
    faces = np.sort(np.stack([cells[:, i] for i in ([0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3])], axis=1).reshape(-1, 3), axis=1)
    faces, counts = np.unique(faces, axis=0, return_counts=True)
    assert counts.max() <= 2, 'Nonmanifold volume faces'
    return faces[counts == 1]


def query_points(points, triangles, samples, seed):
    q = points[triangles]
    areas = np.linalg.norm(np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0]), axis=1)/2
    assert np.all(areas > 0)
    rng = np.random.default_rng(seed)
    selected = rng.choice(len(q), samples, p=areas/areas.sum())
    uv = rng.random((samples, 2))
    uv[uv.sum(axis=1) > 1] = 1-uv[uv.sum(axis=1) > 1]
    random = q[selected, 0]+uv[:, :1]*(q[selected, 1]-q[selected, 0])+uv[:, 1:]*(q[selected, 2]-q[selected, 0])
    return np.vstack([points[np.unique(triangles)], q.mean(axis=1), random])


def distance(target_p, target_t, queries, tolerance):
    locator = vtk.vtkStaticCellLocator()
    locator.SetDataSet(polydata(target_p, target_t))
    locator.BuildLocator()
    nearest = [0., 0., 0.]
    cell_id, sub_id, squared = vtk.reference(0), vtk.reference(0), vtk.reference(0.)
    distances = np.empty(len(queries))
    for i, point in enumerate(queries):
        locator.FindClosestPoint(point, nearest, cell_id, sub_id, squared)
        distances[i] = np.sqrt(max(float(squared), 0.))
    maximum = int(np.argmax(distances))
    return {'query_count': len(queries), 'maximum_distance_mm': float(distances[maximum]),
            'maximum_query_mm': queries[maximum].tolist(),
            'mean_distance_mm': float(distances.mean()),
            'p99_distance_mm': float(np.percentile(distances, 99)),
            'samples_beyond_tolerance': int(np.count_nonzero(distances > tolerance+1e-8))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tolerance-mm', type=float, default=.03)
    parser.add_argument('--area-samples', type=int, default=50000)
    args = parser.parse_args()
    start = time.perf_counter()
    source, result = np.load(args.reference), np.load(args.mesh)
    p0, t0 = source['p'], source['t']
    p1, t1 = result['p'], result['t']
    if t1.shape[1] == 4:
        t1 = boundary(t1)
    forward = distance(p1, t1, query_points(p0, t0, args.area_samples, 20260911), args.tolerance_mm)
    print('reference to mesh', forward, flush=True)
    reverse = distance(p0, t0, query_points(p1, t1, args.area_samples, 20260912), args.tolerance_mm)
    report = {
        'reference_sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
        'mesh_sha256': hashlib.sha256(args.mesh.read_bytes()).hexdigest(),
        'sampling': 'Every boundary vertex and triangle centroid, plus area-weighted deterministic samples in each direction.',
        'is_global_Hausdorff_bound': False,
        'tolerance_mm': args.tolerance_mm, 'random_area_samples_per_direction': args.area_samples,
        'reference_to_mesh': forward, 'mesh_to_reference': reverse,
        'elapsed_seconds': time.perf_counter()-start,
        'status': 'PASS_SAMPLED_SURFACE_DISTANCE' if not (forward['samples_beyond_tolerance']+reverse['samples_beyond_tolerance']) else 'FAIL_SAMPLED_SURFACE_DISTANCE',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
