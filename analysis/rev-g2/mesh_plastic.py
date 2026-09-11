"""Tetrahedralize a closed, slicer-derived structural surface without old CAD."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import gmsh
import numpy as np

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(ROOT/'analysis/rev-g'))
from mesh_quality import clean


def mesh(p, triangles, h, algorithm=1):
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', 4)
        gmsh.model.add('slicer-derived-material')
        surface = gmsh.model.addDiscreteEntity(2)
        gmsh.model.mesh.addNodes(2, surface, np.arange(1, len(p)+1), p.ravel())
        gmsh.model.mesh.addElementsByType(surface, 2, [], (triangles+1).ravel())
        loop = gmsh.model.geo.addSurfaceLoop([surface])
        gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeMin', .05)
        gmsh.option.setNumber('Mesh.MeshSizeMax', h)
        gmsh.option.setNumber('Mesh.MeshSizeFromPoints', 0)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 0)
        gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary', 0)
        gmsh.option.setNumber('Mesh.Algorithm3D', algorithm)
        gmsh.model.mesh.generate(3)
        tags, p, _ = gmsh.model.mesh.getNodes()
        p = np.asarray(p).reshape(-1, 3)
        kinds, _, cells = gmsh.model.mesh.getElements(3)
        assert 4 in kinds, 'No volume tetrahedra generated'
        t = np.asarray(cells[list(kinds).index(4)]).reshape(-1, 4)
        lookup = np.zeros(int(max(tags))+1, dtype=int)
        lookup[tags] = np.arange(len(tags))
        p, t, audit = clean(p, lookup[t])
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
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.validate_box:
        sys.path.insert(0, str(D/'.work/python'))
        import manifold3d as mf
        m = mf.Manifold.cube((10., 8., 6.)).to_mesh64()
        p, tri = np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts)
        expected = 480.
    else:
        with np.load(args.surface) as data:
            p, tri = data['p'], data['t']
        v = p[tri]
        expected = np.einsum('ij,ij->i', v[:, 0], np.cross(v[:, 1], v[:, 2])).sum()/6
        assert expected > 0
    p, t, report = mesh(p, tri, args.h, args.algorithm)
    report['reference_surface_signed_volume_mm3'] = float(expected)
    report['relative_surface_volume_error'] = abs(report['total_absolute_volume_mm3']/expected-1)
    report['h_mm'] = args.h
    report['gmsh_3d_algorithm'] = args.algorithm
    report['surface_sha256'] = hashlib.sha256(args.surface.read_bytes()).hexdigest() if args.surface else None
    assert report['relative_surface_volume_error'] < .001
    np.savez_compressed(args.output.with_suffix('.npz'), p=p, t=t)
    report['status'] = 'PASS: closed surface and volume mesh'
    report['nodes'] = len(p)
    report['tetrahedra'] = len(t)
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
