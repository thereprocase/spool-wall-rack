# E13 matched comparison with E10 and E12

E13 uses **11 mm added depth**, up from E12's 9.5 mm and within the
12.67 mm maximum. Straight flanks and a short flat underside replace the broad
curve. The flanks extend from X=35 to 76 and X=104 to 145 mm, with small
corner blends. The 50° finish, rigid shoulder blends, fingers, seats and
hardware are retained. No holes are added.

The new depth cap supersedes the earlier demand that the inner-seat section
exceed both adjacent arms. The adjacent-section ratios are reported openly in
[the section audit](../../designs/closed-wall-e13/section-verification.json).

| Revision | Walls | Near-seat p99 (MPa) | Front movement at E1000 (mm) | Stress refinement change | Movement refinement change |
|---|---:|---:|---:|---:|---:|
| E10 | 8 | 6.506 | 3.557 | +1.58% | +0.71% |
| E12 | 8 | 4.441 | 2.457 | +0.20% | +0.27% |
| E13 | 8 | 3.891 | 2.054 | +0.09% | +0.47% |
| E10 | 10 | 6.128 | 3.242 | +1.37% | +0.86% |
| E12 | 10 | 4.136 | 2.223 | +0.26% | +0.44% |
| E13 | 10 | 3.606 | 1.856 | -0.14% | +0.41% |

| Walls | Stress reduction vs E10 | Movement reduction vs E10 | Stress change vs E12 | Movement change vs E12 |
|---:|---:|---:|---:|---:|
| 8 | 40.19% | 42.25% | -12.39% | -16.40% |
| 10 | 41.15% | 42.77% | -12.81% | -16.52% |

![Actual matched stress fields](seat-stress-comparison.png)

## Outer rod only

| Revision | Near-seat p99 (MPa) | Front movement at E1000 (mm) |
|---|---:|---:|
| E10 | 6.611 | 3.293 |
| E12 | 4.282 | 2.185 |
| E13 | 3.781 | 1.799 |

E13 reduces this outer-only near-seat statistic by **42.81%** relative to E10.

## Scope and reproduction

All cases use the same finished-layer integration, plane-stress law, load
patches and projected fixing/contact assumptions. The volume-weighted p99
window is fixed at X=75–110 mm, Y=−24–0 mm, excluding the added underside
volume from its denominator. Refinement uses h=2 and h=1 mm; these changes are
numerical sensitivity, not asymptotic convergence or independent validation.

The E10 fields are retained in [the E11 package](../e11/README.md) and E12 fields
in [the E12 package](../e12/README.md); only E13
was newly solved here. Every referenced field passes independent residual,
force and moment checks. The affine/beam verification is separate from these
bracket solves. Run `solve_comparison.py e13 8 1` (and the other documented
wall/mesh/load cases), then `report_comparison.py` to regenerate this report.

Stress percentiles are comparison metrics, not rupture allowables. The model
does not establish layer adhesion, snap insertion force, actual rod contact,
creep or a safe spool count. [Current 3D/material results](RESULTS.md).
