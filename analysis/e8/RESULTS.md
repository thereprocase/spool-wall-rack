# Solved E8 engineering results

These results apply to the level-rail E8 prototype. Raised-front statics are a separate study.

| Material | Walls | Reference E (MPa) | Initial front movement (mm) | One 1.25 kg roll (mm) | Creep modulus needed for 5 mm (MPa) | Compliance limit |
|---|---:|---:|---:|---:|---:|---:|
| PLA | 8 | 3427 | 1.18 | 0.122 | 806 | 4.25× |
| PETG | 10 | 2311 | 1.57 | 0.163 | 724 | 3.19× |
| ASA | 8 | 2379 | 1.69 | 0.176 | 806 | 2.95× |
| PA6-GF dry | 8 | 5357 | 0.75 | 0.078 | 806 | 6.65× |
| PA6-GF wet | 8 | 1794 | 2.25 | 0.234 | 806 | 2.23× |

Moduli are room-temperature reference values. The creep-modulus limits apply to bracket movement alone; subtract dowel and wall movement from the 5 mm system allowance. The one-roll column assigns the entire roll reaction to one bracket, for the stated simple/two-equal-span arrangement, and uses the reference instantaneous modulus. It is not a measured aged unloading modulus.

## Numerical checks

Whole-bracket refinement is pending.

A percentile is a field summary, not a stress allowable. Restraint-edge peaks and FFF anisotropy require separate interpretation. See individual result JSON files for force/moment balance, residuals, patch movements and regional stresses.

![2D FEM](fem-2d.png)

![3D FEM](fem-3d.png)

![Landing FEM](fem-landing.png)

![Creep sensitivity](creep-sensitivity.png)

![Raised-front study](raised-front-statics.png)

## Conditional one-, five- and ten-year calculation

| Years | Assumed extra compliance / year | Total compliance multiplier | PLA movement (mm) | PETG movement (mm) |
|---:|---:|---:|---:|---:|
| 1 | 0.00 | 1.14 | 1.34 | 1.79 |
| 1 | 0.02 | 1.16 | 1.36 | 1.82 |
| 1 | 0.10 | 1.24 | 1.46 | 1.94 |
| 5 | 0.00 | 1.14 | 1.34 | 1.79 |
| 5 | 0.02 | 1.24 | 1.46 | 1.94 |
| 5 | 0.10 | 1.64 | 1.93 | 2.57 |
| 10 | 0.00 | 1.14 | 1.34 | 1.79 |
| 10 | 0.02 | 1.34 | 1.58 | 2.10 |
| 10 | 0.10 | 2.14 | 2.52 | 3.35 |

These curves intentionally demonstrate different long-term continuations that a short test cannot distinguish. They are neither PLA nor PETG life predictions at 85°F. No creep-rupture allowable is inferred.
