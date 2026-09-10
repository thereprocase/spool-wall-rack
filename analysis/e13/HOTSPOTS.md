# E13 hotspot and mesh-refinement audit

E12 and E13 are both solved again at **h=1 mm**, with identical material,
loads, restraints, element formulation and requested mesh sizes. E13 additionally
has h=2 and h=1.5 mm fields. These runs spend resolution on the complete 3D
domain, including seats, chamfers, four plates and screw tunnels.

The 8-wall E12 baseline required the documented HXT retry after Delaunay
boundary recovery failed. The other fine meshes used Delaunay. Thus nominal
resolution is matched, while the meshes and this algorithm choice differ;
raw-peak changes must not be attributed solely to the design.

The long straight underside tapers carry the added depth into adjacent arms.
The physical fingers, small corner finish, bearing surfaces and screw access
remain. No finite elements are removed because of their stress values.

## Matched fine-mesh comparison

| Walls | Region | E12 p99 (MPa) | E13 p99 (MPa) | Change | E12 raw peak (MPa) | E13 raw peak (MPa) |
|---:|---|---:|---:|---:|---:|---:|
| 8 | whole body | 3.165 | 2.841 | -10.24% | 16.54 | 25.55 |
| 8 | inner seat | 4.385 | 3.803 | -13.28% | 10.14 | 16.67 |
| 8 | knee | 3.712 | 3.366 | -9.31% | 16.54 | 25.55 |
| 8 | outer arm | 2.107 | 1.698 | -19.41% | 3.23 | 4.13 |
| 8 | upper landing | 0.946 | 0.957 | +1.17% | 3.67 | 1.83 |
| 8 | lower landing | 3.920 | 3.914 | -0.17% | 10.93 | 9.62 |
| 10 | whole body | 2.856 | 2.573 | -9.91% | 26.90 | 24.16 |
| 10 | inner seat | 4.109 | 3.565 | -13.22% | 12.78 | 13.34 |
| 10 | knee | 3.335 | 2.989 | -10.37% | 26.90 | 24.16 |
| 10 | outer arm | 1.913 | 1.526 | -20.24% | 4.27 | 2.61 |
| 10 | upper landing | 0.985 | 0.974 | -1.12% | 1.86 | 1.96 |
| 10 | lower landing | 3.883 | 3.920 | +0.93% | 11.18 | 11.41 |

P99 is volume-weighted within fixed spatial windows, which are identical in
both revisions. The near-seat window excludes the added underside volume;
knee, arm and whole-body windows include material added within those windows.
Raw peaks retain all finite cells. Their coordinates, cell
volumes, p99.9 and material volume above 6 MPa are recorded in
[the complete audit](hotspot-verification.json). Six MPa is a visualization
threshold, not an allowable or a rejection limit.

![Matched fine 3D field details](hotspot-comparison.png)

## Three E13 mesh levels

| Walls | h (mm) | Tetrahedra | Front at E1000 (mm) | Change from previous | Inner-seat p99 (MPa) | Inner-seat p99 change |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 2 | 192,633 | 2.0673 | — | 3.813 | — |
| 8 | 1.5 | 323,629 | 2.1091 | +2.02% | 3.816 | +0.07% |
| 8 | 1 | 757,028 | 2.1480 | +1.84% | 3.803 | -0.34% |
| 10 | 2 | 195,838 | 1.8822 | — | 3.524 | — |
| 10 | 1.5 | 328,179 | 1.9005 | +0.97% | 3.605 | +2.30% |
| 10 | 1 | 787,137 | 1.9366 | +1.90% | 3.565 | -1.09% |

Every field passes independent force, moment and free-residual gates below
1e-6. Refinement is a numerical sensitivity study; it does not prove exact
asymptotic convergence, printed anisotropy, contact-pressure distribution or
rupture strength. A raw peak that changes location or magnitude still needs
interpretation. Tiny-cell location alone is insufficient to dismiss it.

The clamped washer/shank transitions, piecewise planar chamfers and ideal
wall-to-plate intersections can retain local peaks. This package does not
claim that all stress concentrations have been eliminated. The retained raw
fields make those limits visible rather than smoothing or clipping them away.
Physical rod fit, snap force, hot loading and lifetime qualification remain
unperformed. [Current material and 3D results](RESULTS.md).

Reproduce the fine E12 baseline using `mesh_model.py print-material 8 1 1
--clean --baseline-e12` followed by `solve3d.py
baseline-e12-print-material-8w-h1 --pardiso`; repeat for 10 walls. The preserved
E12 analysis domains must be built first. Run `audit_hotspots.py` after all
listed E13 refinement fields and both baseline fields are complete.
