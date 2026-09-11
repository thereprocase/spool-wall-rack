"""Independent, evidence-bounded audit of a tetrahedral volume mesh.

The audit deliberately does not call a solver and never promotes a boundary or
occupancy check to a mesh-quality/structural qualification claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import shapely

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plastic_shape import PlasticShape  # noqa: E402


def hist(values, bins):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    counts, edges = np.histogram(finite, bins=bins)
    return {"bins": [float(x) if np.isfinite(x) else None for x in edges], "counts": [int(x) for x in counts],
            "finite_count": int(len(finite)), "nonfinite_count": int(len(values)-len(finite))}


def mesh_metrics(points, cells, chunk=50000):
    n = len(cells)
    volume = np.empty(n)
    signed = np.empty(n)
    normvol = np.empty(n)
    ratio = np.empty(n)
    finite = np.ones(n, dtype=bool)
    distinct = np.ones(n, dtype=bool)
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        q = points[cells[a:b]]
        det = np.einsum("ij,ij->i", q[:, 1]-q[:, 0], np.cross(q[:, 2]-q[:, 0], q[:, 3]-q[:, 0]))
        signed[a:b] = det / 6.0
        volume[a:b] = np.abs(signed[a:b])
        lengths = np.linalg.norm(q[:, :, None, :] - q[:, None, :, :], axis=-1)
        edge = lengths[:, np.triu_indices(4, 1)[0], np.triu_indices(4, 1)[1]]
        maxedge = edge.max(axis=1)
        minedge = edge.min(axis=1)
        normvol[a:b] = volume[a:b] / np.maximum(maxedge**3, np.finfo(float).tiny)
        # Circumradius R = abc/(4*area of opposite face); use a stable
        # linear solve for each tetrahedron, falling back to infinity.
        m = q[:, 1:] - q[:, :1]
        rhs = (m**2).sum(axis=2)
        try:
            center2 = np.linalg.solve(2*m, rhs[..., None])[..., 0]
            radius = np.linalg.norm(center2, axis=1)
        except np.linalg.LinAlgError:
            radius = np.full(b-a, np.inf)
        ratio[a:b] = radius / np.maximum(minedge, np.finfo(float).tiny)
        finite[a:b] = np.isfinite(q).all(axis=(1, 2)) & np.isfinite(volume[a:b])
        distinct[a:b] = np.all(np.diff(np.sort(cells[a:b], axis=1), axis=1) > 0, axis=1)
    return volume, signed, normvol, ratio, finite, distinct


def topology(points, cells, valid):
    c = cells[valid]
    faces = np.sort(np.stack((c[:, [0, 1, 2]], c[:, [0, 1, 3]],
                              c[:, [0, 2, 3]], c[:, [1, 2, 3]]), axis=1).reshape(-1, 3), axis=1)
    unique_faces, face_counts = np.unique(faces, axis=0, return_counts=True)
    boundary_faces = unique_faces[face_counts == 1]
    edges = np.sort(np.stack((boundary_faces[:, [0, 1]], boundary_faces[:, [0, 2]],
                              boundary_faces[:, [1, 2]]), axis=1).reshape(-1, 2), axis=1)
    _, edge_counts = np.unique(edges, axis=0, return_counts=True)
    # Tetrahedra connected through a shared triangular facet.
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    order = np.lexsort((faces[:, 2], faces[:, 1], faces[:, 0]))
    sf = faces[order]
    joins = np.flatnonzero(np.all(sf[1:] == sf[:-1], axis=1))
    left, right = order[joins] // 4, order[joins+1] // 4
    graph = coo_matrix((np.ones(len(left)*2),
                        (np.r_[left, right], np.r_[right, left])), shape=(len(c), len(c)))
    count, labels = connected_components(graph, directed=False) if len(c) else (0, np.array([], dtype=int))
    return {"valid_tetrahedra": int(len(c)), "shared_face_components": int(count),
            "face_count_histogram": {str(k): int(v) for k, v in zip(*np.unique(face_counts, return_counts=True))},
            "boundary_faces_incidence_one": int(np.count_nonzero(face_counts == 1)),
            "nonmanifold_faces_incidence_gt_two": int(np.count_nonzero(face_counts > 2)),
            "boundary_edges_incidence_one": int(np.count_nonzero(edge_counts == 1)),
            "nonmanifold_edges_incidence_gt_two": int(np.count_nonzero(edge_counts > 2))}


def occupancy_audit(points, cells, shape, tolerance, chunk=50000):
    # Centroids plus four fixed barycentric samples catch many cut-through
    # cells while bounding memory and retaining deterministic evidence.
    weights = np.array([[.25,.25,.25,.25], [.55,.15,.15,.15], [.15,.55,.15,.15],
                        [.15,.15,.55,.15], [.15,.15,.15,.55]])
    strict = outside = outside_tol = total = 0
    prepared = [(z0, z1, simple) for z0, z1, _raw, simple in shape.layers]
    for a in range(0, len(cells), chunk):
        q = points[cells[a:a+chunk]]
        samples = np.einsum('sk,akj->saj', weights, q).reshape(-1, 3)
        raw_ok = shape.contains(samples, continuum=True)
        near_ok = np.zeros(len(samples), dtype=bool)
        for k, (z0, z1, expanded) in enumerate(prepared):
            sel = (samples[:, 2] >= z0-tolerance) & (samples[:, 2] <= z1+tolerance)
            if np.any(sel):
                dz = np.maximum(np.maximum(z0-samples[sel, 2], samples[sel, 2]-z1), 0.)
                radius = np.sqrt(np.maximum(tolerance*tolerance-dz*dz, 0.))
                pts = shapely.points(samples[sel, 0], samples[sel, 1])
                near_ok[sel] |= shapely.distance(pts, expanded) <= radius
        total += len(samples); strict += int(raw_ok.sum()); outside += int((~raw_ok).sum()); outside_tol += int((~near_ok).sum())
    return {"sample_points": int(total), "strict_inside_samples": strict,
            "outside_strict_samples": outside,
            "outside_after_explicit_geometry_tolerance": outside_tol,
            "occupancy_status": "PASS" if outside_tol == 0 else "FAIL",
            "sampling": "centroid plus four deterministic barycentric points per tetrahedron",
            "tolerance_mm": tolerance}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", type=Path, required=True)
    ap.add_argument("--shape-directory", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--geometry-tolerance-mm", type=float, default=.03)
    args = ap.parse_args()
    with np.load(args.mesh) as data:
        points, cells = np.asarray(data["p"], float), np.asarray(data["t"], np.int64)
    shape = PlasticShape.load(args.shape_directory)
    volume, signed, normvol, ratio, finite, distinct = mesh_metrics(points, cells)
    valid = finite & distinct & (volume > 0)
    occupancy = occupancy_audit(points, cells[valid], shape, args.geometry_tolerance_mm)
    topo = topology(points, cells, valid)
    expected = float(shape.volume(continuum=True))
    raw_expected = float(shape.volume(continuum=False))
    total = float(volume[valid].sum())
    relative_volume_error = abs(total/expected-1) if expected else None
    gates = {
        'finite_coordinates': bool(np.isfinite(points).all()),
        'finite_distinct_positive_absolute_volume_cells': bool(valid.all()),
        'consistent_signed_orientation': bool(np.all(signed > 0) or np.all(signed < 0)),
        'one_shared_face_material_component': topo['shared_face_components'] == 1,
        'manifold_volume_faces': topo['nonmanifold_faces_incidence_gt_two'] == 0,
        'closed_manifold_boundary': topo['boundary_edges_incidence_one'] == 0 and topo['nonmanifold_edges_incidence_gt_two'] == 0,
        'volume_matches_layers_within_0p1_percent': relative_volume_error is not None and relative_volume_error < .001,
        'sampled_material_occupancy': occupancy['occupancy_status'] == 'PASS',
    }
    result = {
        "audit": "independent volume mesh audit; diagnostic evidence only",
        "mesh": str(args.mesh.name), "mesh_sha256": hashlib.sha256(args.mesh.read_bytes()).hexdigest(),
        "nodes": int(len(points)), "tetrahedra": int(len(cells)), "finite_nodes": bool(np.isfinite(points).all()),
        "all_cells_finite": bool(finite.all()), "all_cells_four_distinct_nodes": bool(distinct.all()),
        "positive_volume_cells": int(valid.sum()), "zero_or_negative_volume_cells": int((~(volume > 0)).sum()),
        "signed_volume_positive_cells": int((signed > 0).sum()), "signed_volume_negative_cells": int((signed < 0).sum()),
        "total_absolute_tet_volume_mm3": total, "shape_continuum_layer_volume_mm3": expected,
        "shape_raw_layer_volume_mm3": raw_expected,
        "relative_volume_error_vs_continuum_layers": relative_volume_error,
        "volume_histogram_mm3": hist(volume, np.geomspace(max(volume[volume>0].min(),1e-15), max(volume.max(),1e-14), 16)) if np.any(volume>0) else {},
        "normalized_volume_histogram_volume_over_max_edge_cubed": hist(normvol, np.geomspace(max(normvol[normvol>0].min(),1e-15), max(normvol.max(),1e-14), 16)) if np.any(normvol>0) else {},
        "radius_edge_ratio_histogram": hist(ratio, [0,.7,1,1.2,1.4143,1.6,2,3,5,10,25,100,np.inf]),
        "quality_counts": {"ratio_gt_2": int(np.count_nonzero(ratio > 2)), "ratio_gt_5": int(np.count_nonzero(ratio > 5)),
                           "normalized_volume_lt_1e-4": int(np.count_nonzero(normvol < 1e-4)),
                           "normalized_volume_lt_1e-6": int(np.count_nonzero(normvol < 1e-6))},
        "topology": topo,
        "occupancy": occupancy,
        "numerical_geometry_gates": gates,
        "quality_qualification": "NOT ASSESSED: no solver, convergence, material law, or stress claim",
        "status": "PASS_NUMERICAL_BOUNDARY_VOLUME_ONLY" if all(gates.values()) else "FAIL_NUMERICAL_GEOMETRY_GATES",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
