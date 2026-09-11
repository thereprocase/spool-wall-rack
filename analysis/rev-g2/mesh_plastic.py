"""Tetrahedralize a closed, slicer-derived structural surface without old CAD."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import time

import gmsh
import numpy as np

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(ROOT/'analysis/rev-g'))
from mesh_quality import clean


def archive_and_clean(nodes, cells, raw_output=None):
    """Retain the native result before any cleanup or acceptance assertion."""
    if raw_output is not None:
        np.savez_compressed(raw_output, p=nodes, t=cells)
    nodes, cells, report = clean(nodes, cells)
    q = nodes[cells]
    det = np.einsum('ij,ij->i', q[:, 1]-q[:, 0],
                    np.cross(q[:, 2]-q[:, 0], q[:, 3]-q[:, 0]))
    reverse = det < 0
    cells[reverse, :2] = cells[reverse, 1::-1]
    report['cells_reoriented_without_geometric_change'] = int(reverse.sum())
    return nodes, cells, report


def cavity_seeds(layers):
    """Air-component seeds at layer midplanes, verified clear of material.

    The outer air region is connected through the bounding rectangle and
    through either exposed Z face. Each remaining component is an enclosed
    cavity. This avoids seeds offset an arbitrary epsilon from a triangle.
    """
    import shapely
    from shapely.geometry import box
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from plastic_shape import polygons
    bounds = np.array([row[3].bounds for row in layers if not row[3].is_empty])
    frame = box(bounds[:, 0].min()-1, bounds[:, 1].min()-1,
                bounds[:, 2].max()+1, bounds[:, 3].max()+1)
    regions = [polygons(frame.difference(row[3])) for row in layers]
    offsets = np.r_[0, np.cumsum([len(row) for row in regions])]
    links = []
    for k in range(1, len(regions)):
        tree = shapely.STRtree(regions[k-1])
        for i, poly in enumerate(regions[k]):
            for j in tree.query(poly, predicate='intersects'):
                if poly.intersection(regions[k-1][j]).area > 1e-8:
                    links.append((offsets[k]+i, offsets[k-1]+j))
    links = np.asarray(links, dtype=int).reshape(-1, 2)
    graph = coo_matrix((np.ones(len(links)), (links[:, 0], links[:, 1])), shape=(offsets[-1], offsets[-1]))
    count, labels = connected_components(graph, directed=False)
    outside = set(labels[:offsets[1]]) | set(labels[offsets[-2]:])
    choices = {}
    for k, parts in enumerate(regions):
        z0, z1, raw, material = layers[k]
        for i, poly in enumerate(parts):
            label = labels[offsets[k]+i]
            if poly.intersects(frame.boundary):
                outside.add(label)
            pt = poly.representative_point()
            clearance = min(pt.distance(poly.boundary), (z1-z0)/2)
            if label not in choices or clearance > choices[label][0]:
                assert not material.contains(pt)
                choices[label] = (clearance, [pt.x, pt.y, (z0+z1)/2])
    records = [{'clearance_to_current_layer_air_boundary_mm': float(choices[k][0]),
                'point_mm': choices[k][1]} for k in range(count) if k not in outside]
    assert all(row['clearance_to_current_layer_air_boundary_mm'] > 1e-6 for row in records)
    return records


def tetrahedralize(p, triangles, h, layers=None, quality=True, raw_output=None):
    """Keep the PLC, seed every enclosed air component, audit the full output."""
    sys.path.insert(0, str(D/'.work/python'))
    import tetgen
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    edges = triangles[:, [(0, 1), (1, 2), (2, 0)]].reshape(-1, 2)
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(p), len(p)))
    count, labels = connected_components(graph, directed=False)
    component = labels[triangles[:, 0]]
    v = p[triangles]
    normal = np.cross(v[:, 1]-v[:, 0], v[:, 2]-v[:, 0])
    signed = np.einsum('ij,ij->i', v[:, 0], normal)/6
    volumes = np.bincount(component, weights=signed)
    tet = tetgen.TetGen(p, triangles.astype(np.int32))
    seeds = cavity_seeds(layers) if layers is not None else []
    assert len(seeds) == int(np.count_nonzero(volumes < -1e-8)), 'Air graph and closed cavity shells disagree'
    for row in seeds:
        tet.add_hole(row['point_mm'])
    print('TetGen input', len(p), len(triangles), 'enclosed voids', len(seeds), flush=True)
    result = tet.tetrahedralize(plc=True, quality=quality, minratio=2.,
                               maxvolume=h**3/6 if quality else -1., fixedvolume=quality,
                               steinerleft=1000000, docheck=True, quiet=False)
    nodes, cells = result[:2]
    nodes, cells, audit = archive_and_clean(nodes, cells, raw_output)
    audit['enclosed_void_seeds'] = seeds
    audit['surface_component_signed_volumes_mm3'] = volumes.tolist()
    audit['requested_maximum_tetrahedron_volume_mm3'] = h**3/6 if quality else None
    return nodes, cells, audit


def wild_mesh(p, triangles, h, epsilon_mm, iterations, simplify_input=False, raw_output=None):
    sys.path.insert(0, str(D/'.work/python'))
    import pytetwild
    diagonal = np.linalg.norm(p.max(axis=0)-p.min(axis=0))
    epsilon = epsilon_mm/diagonal
    print('fTetWild input', len(p), len(triangles), 'absolute envelope', epsilon_mm, flush=True)
    nodes, cells = pytetwild.tetrahedralize(
        # The nanobind input signature requires writable arrays, even when
        # the source Manifold mesh is a contiguous read-only view.
        np.array(p, dtype=np.float64, order='C', copy=True), np.array(triangles, dtype=np.uint32, order='C', copy=True), edge_length_abs=float(h),
        epsilon=float(epsilon), simplify=simplify_input, optimize=True,
        num_threads=4, num_opt_iter=iterations, loglevel=2, quiet=False,
        disable_filtering=False)
    nodes, cells, audit = archive_and_clean(nodes, cells, raw_output)
    audit['requested_absolute_surface_envelope_mm'] = epsilon_mm
    audit['bounding_box_diagonal_mm'] = float(diagonal)
    audit['epsilon_relative_to_bounding_diagonal'] = float(epsilon)
    audit['optimization_iteration_limit'] = iterations
    audit['ideal_edge_length_mm'] = h
    audit['surface_pre_simplification'] = simplify_input
    audit['pytetwild_version'] = '0.4.2'
    return nodes, cells, audit


def mesh(p, triangles, h, algorithm=1, remesh_surface=False, raw_output=None):
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', 4)
        gmsh.model.add('slicer-derived-material')
        surface = gmsh.model.addDiscreteEntity(2)
        gmsh.model.mesh.addNodes(2, surface, np.arange(1, len(p)+1), p.ravel())
        gmsh.model.mesh.addElementsByType(surface, 2, [], (triangles+1).ravel())
        if remesh_surface:
            gmsh.model.mesh.classifySurfaces(np.deg2rad(40), True, True, np.pi)
            gmsh.model.mesh.createGeometry()
            surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
        else:
            surfaces = [surface]
        loop = gmsh.model.geo.addSurfaceLoop(surfaces)
        gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeMin', .05)
        gmsh.option.setNumber('Mesh.MeshSizeMax', h)
        gmsh.option.setNumber('Mesh.MeshSizeFromPoints', 0)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 0)
        gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary', 0)
        field = gmsh.model.mesh.field.add('MathEval')
        gmsh.model.mesh.field.setString(field, 'F', str(h))
        gmsh.model.mesh.field.setAsBackgroundMesh(field)
        gmsh.option.setNumber('Mesh.Algorithm3D', algorithm)
        gmsh.model.mesh.generate(3)
        tags, p, _ = gmsh.model.mesh.getNodes()
        p = np.asarray(p).reshape(-1, 3)
        kinds, _, cells = gmsh.model.mesh.getElements(3)
        assert 4 in kinds, 'No volume tetrahedra generated'
        t = np.asarray(cells[list(kinds).index(4)]).reshape(-1, 4)
        lookup = np.zeros(int(max(tags))+1, dtype=int)
        lookup[tags] = np.arange(len(tags))
        p, t, audit = archive_and_clean(p, lookup[t], raw_output)
        return p, t, audit
    finally:
        gmsh.finalize()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--surface', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--h', type=float, default=2.)
    parser.add_argument('--algorithm', type=int, choices=[1, 10], default=1)
    parser.add_argument('--validate-box', action='store_true')
    parser.add_argument('--validate-hollow-box', action='store_true')
    parser.add_argument('--remesh-surface', action='store_true')
    parser.add_argument('--backend', choices=['gmsh', 'tetgen', 'ftetwild'], default='gmsh')
    parser.add_argument('--epsilon-mm', type=float, default=.03)
    parser.add_argument('--opt-iterations', type=int, default=40)
    parser.add_argument('--simplify-input', action='store_true', help='Use fTetWild surface preprocessing within its requested envelope; output still needs an independent geometry audit.')
    parser.add_argument('--no-quality', action='store_true', help='Boundary-recovery diagnostic only, no size or quality claim.')
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.surface is not None:
        args.surface = args.surface.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.validate_box or args.validate_hollow_box:
        sys.path.insert(0, str(D/'.work/python'))
        import manifold3d as mf
        shape = mf.Manifold.cube((10., 8., 6.))
        if args.validate_hollow_box:
            shape -= mf.Manifold.cube((8., 6., 4.)).translate((1, 1, 1))
        m = shape.to_mesh64()
        p, tri = np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts)
        expected = 288. if args.validate_hollow_box else 480.
    else:
        with np.load(args.surface) as data:
            p, tri = data['p'], data['t']
        v = p[tri]
        expected = np.einsum('ij,ij->i', v[:, 0], np.cross(v[:, 1], v[:, 2])).sum()/6
        assert expected > 0
    start = time.perf_counter()
    runtime = args.output.parent/'.work'/args.output.name
    runtime.mkdir(parents=True, exist_ok=True)
    old_cwd = Path.cwd()
    try:
        # Native debug files and raw meshes belong to this attempt. Concurrent
        # runs must not overwrite each other's fixed-name backend artifacts.
        os.chdir(runtime)
        raw_output = runtime/'native-result.npz'
        if args.backend == 'ftetwild':
            p, t, report = wild_mesh(p, tri, args.h, args.epsilon_mm, args.opt_iterations, args.simplify_input, raw_output)
        elif args.backend == 'tetgen':
            from plastic_shape import PlasticShape
            layers = None if args.validate_box else PlasticShape.load(args.surface.parent).layers
            p, t, report = tetrahedralize(p, tri, args.h, layers, not args.no_quality, raw_output)
        else:
            p, t, report = mesh(p, tri, args.h, args.algorithm, args.remesh_surface, raw_output)
    finally:
        os.chdir(old_cwd)
    report['reference_surface_signed_volume_mm3'] = float(expected)
    report['relative_surface_volume_error'] = abs(report['total_absolute_volume_mm3']/expected-1)
    report['h_mm'] = args.h
    report['gmsh_3d_algorithm'] = args.algorithm
    report['surface_remeshed'] = args.remesh_surface
    report['backend'] = args.backend
    report['quality_refinement_requested'] = not args.no_quality
    report['elapsed_seconds'] = time.perf_counter()-start
    report['surface_sha256'] = hashlib.sha256(args.surface.read_bytes()).hexdigest() if args.surface else None
    np.savez_compressed(args.output.with_suffix('.npz'), p=p, t=t)
    passed = report['relative_surface_volume_error'] < .001
    report['status'] = ('BOUNDARY VOLUME CHECK PASSED; mesh quality and mechanics require independent review.'
                        if passed else 'FAILED BOUNDARY VOLUME CHECK; retained for diagnostic review only.')
    report['nodes'] = len(p)
    report['tetrahedra'] = len(t)
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['status', 'backend', 'nodes', 'tetrahedra', 'relative_surface_volume_error', 'elapsed_seconds']}, indent=2), flush=True)
    assert passed, 'Boundary volume mismatch; diagnostic mesh and report were retained'


if __name__ == '__main__':
    main()
