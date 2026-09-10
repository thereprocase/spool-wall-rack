# E11 comparative stress screen

The reinforced inner seat is compared with the actual E10 finish using the
same plane-stress solver, contact assumptions and 12 kg equivalent bracket
load. The 120 layer-midpoint material sections include the finished chamfers,
ideal contour walls and four 1.2 mm solid plates. Sparse infill receives zero
credit. The E11 3D analysis and material scaling are in RESULTS.md.

| Walls | E10 near-seat p99 (MPa) | E11 near-seat p99 (MPa) | Reduction | Front movement reduction |
|---:|---:|---:|---:|---:|
| 8 | 6.51 | 4.07 | 37.4% | 35.5% |
| 10 | 6.13 | 3.82 | 37.6% | 35.1% |

The stress statistic uses the same fixed window, X=75–110 mm and Y=−24–0 mm,
in both designs. Added underside volume is not included in that percentile
denominator. Raw maxima and wider-region results remain in each result JSON.
These are stress-field summaries, not rupture allowables.

![Matched inner-seat stress fields](seat-stress-comparison.png)

## Outer-rod-only diagnostic

With no load applied at the inner seat, E10 still develops a near-seat p99 of **6.61 MPa**. E11 reduces that to **3.73 MPa**, a **43.5%** reduction. This supports the reduced-section bending diagnosis; it does not imply that real bearing/contact effects are absent.

## Numerical checks and limits

All reported cases pass independent force/moment balance and free-residual
checks below 1e-6. The affine/beam solver checks are recorded separately.

| Revision | Walls | Triangles, coarse → fine | Rear p99 change | Front movement change |
|---|---:|---:|---:|---:|
| E10 | 8 | 13,900 → 35,253 | 1.58% | 0.71% |
| E11 | 8 | 24,467 → 51,422 | 0.71% | 0.32% |
| E10 | 10 | 13,900 → 35,253 | 1.37% | 0.86% |
| E11 | 10 | 24,467 → 51,422 | 1.02% | 0.43% |

Two meshes provide a sensitivity check, not proof of asymptotic convergence.
The model averages stress across the printed width and projects the fixing
restraints onto the wall. It cannot resolve 3D bearing stress, layer adhesion,
FFF orthotropy, snap insertion, wall compliance or long-term creep. Do not
use these reductions to increase an allowed spool count without qualification.

The section-property checks in `designs/closed-wall-e11/section-verification.json`
separately demonstrate the required stiffness and elastic section-modulus
margins over both adjacent plain-arm reference bands.

## Reproduce

Use the pinned CAD/FEM packages in `requirements.txt`; build and verify the E10
and E11 STLs first. Run `python verify_solver.py`, `python solve_comparison.py`,
then `python report_comparison.py`. Set OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1.
Layer-outline caches under `.work/` are keyed to the finished STL SHA-256.
