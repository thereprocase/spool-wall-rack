# E12 matched comparison with E10 and E11

E12 uses **9.5 mm added depth**, one-quarter of E11's 38 mm, with a broader
smooth blend. It retains the 50° finish, R6 rigid shoulder treatment, fingers,
rail centers and hardware. No strain-relief holes were added: the shallow
continuous section already retains most of the measured E11 benefit.

The new depth cap supersedes the earlier demand that the inner-seat section
exceed both adjacent arms. The adjacent-section ratios are reported openly in
[the section audit](../../designs/closed-wall-e12/section-verification.json).

| Revision | Walls | Near-seat p99 (MPa) | Front movement at E1000 (mm) | Stress refinement change | Movement refinement change |
|---|---:|---:|---:|---:|---:|
| E10 | 8 | 6.506 | 3.557 | +1.58% | +0.71% |
| E11 | 8 | 4.073 | 2.294 | +0.71% | +0.32% |
| E12 | 8 | 4.441 | 2.457 | +0.20% | +0.27% |
| E10 | 10 | 6.128 | 3.242 | +1.37% | +0.86% |
| E11 | 10 | 3.822 | 2.105 | +1.02% | +0.43% |
| E12 | 10 | 4.136 | 2.223 | +0.26% | +0.44% |

| Walls | Stress reduction vs E10 | Movement reduction vs E10 | Stress increase vs E11 | Movement increase vs E11 |
|---:|---:|---:|---:|---:|
| 8 | 31.74% | 30.92% | 9.05% | 7.14% |
| 10 | 32.51% | 31.44% | 8.23% | 5.61% |

![Actual matched stress fields](seat-stress-comparison.png)

## Outer rod only

| Revision | Near-seat p99 (MPa) | Front movement at E1000 (mm) |
|---|---:|---:|
| E10 | 6.611 | 3.293 |
| E11 | 3.732 | 2.004 |
| E12 | 4.282 | 2.185 |

E12 reduces this outer-only near-seat statistic by **35.23%** relative to E10.

## Scope and reproduction

All cases use the same finished-layer integration, plane-stress law, load
patches and projected fixing/contact assumptions. The volume-weighted p99
window is fixed at X=75–110 mm, Y=−24–0 mm, excluding the added underside
volume from its denominator. Refinement uses h=2 and h=1 mm; these changes are
numerical sensitivity, not asymptotic convergence or independent validation.

The E10/E11 fields are retained in [the E11 package](../e11/README.md); only E12
was newly solved here. Every referenced field passes independent residual,
force and moment checks. The affine/beam verification is separate from these
bracket solves. Run `solve_comparison.py e12 8 1` (and the other documented
wall/mesh/load cases), then `report_comparison.py` to regenerate this report.

Stress percentiles are comparison metrics, not rupture allowables. The model
does not establish layer adhesion, snap insertion force, actual rod contact,
creep or a safe spool count. [Current 3D/material results](RESULTS.md).
