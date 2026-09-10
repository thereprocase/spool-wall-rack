# Solved E9 engineering results

These results apply to the raised-front E9 prototype, including its reshaped back arm and 2 mm broad-face chamfers. The rail-statics comparison isolates the effect of the 12 mm height change.

| Material | Walls | Reference E (MPa) | Initial front movement (mm) | One 1.25 kg roll (mm) | Creep modulus needed for 5 mm (MPa) | Compliance limit |
|---|---:|---:|---:|---:|---:|---:|
| PLA | 8 | 3427 | 1.01 | 0.105 | 693 | 4.94× |
| PETG | 10 | 2311 | 1.37 | 0.142 | 632 | 3.66× |
| ASA | 8 | 2379 | 1.46 | 0.152 | 693 | 3.43× |
| PA6-GF dry | 8 | 5357 | 0.65 | 0.067 | 693 | 7.73× |
| PA6-GF wet | 8 | 1794 | 1.93 | 0.201 | 693 | 2.59× |

Moduli are room-temperature reference values. The creep-modulus limits apply to bracket movement alone; subtract dowel and wall movement from the 5 mm system allowance. The one-roll column assigns the entire roll reaction to one bracket, for the stated simple/two-equal-span arrangement, and uses the reference instantaneous modulus. It is not a measured aged unloading modulus.

## Numerical checks

The initial 8-wall mesh contained numerically zero-volume cells and failed its independently recomputed residual check; that result was rejected. The published 8-wall meshes remove one coarse and six fine degenerate cells, totaling less than 1.4e-12 mm³. The corrected 8/10-wall solves have relative free residuals below 4e-9. See the mesh-quality JSON files and peak_diagnostics in engineering-summary.json for the audit and raw-peak cell locations.

- 8 walls: 108,604 → 183,495 tetrahedra; front movement changes 4.50%. Volume p99 stress: 4.19 → 4.27 MPa. Raw peak: 62.99 → 11.24 MPa.
- 10 walls: 103,938 → 186,126 tetrahedra; front movement changes 6.44%. Volume p99 stress: 3.69 → 3.82 MPa. Raw peak: 17.69 → 19.84 MPa.

A percentile is a field summary, not a stress allowable. The refinement changes listed above do not establish asymptotic convergence. Regional stress changes must also be considered; global percentiles can hide local changes. Tiny cells at tunnel/chamfer intersections, sharp analysis-core transitions and restraint edges affect peaks; actual sliced radii and FFF anisotropy require separate interpretation. See individual result JSON files for force/moment balance, residuals, patch movements and regional stresses.

![2D FEM](fem-2d.png)

![3D FEM](fem-3d.png)

![Landing FEM](fem-landing.png)

![Creep sensitivity](creep-sensitivity.png)

![Raised-front study](raised-front-statics.png)

## Conditional one-, five- and ten-year calculation

| Years | Assumed extra compliance / year | Total compliance multiplier | PLA movement (mm) | PETG movement (mm) |
|---:|---:|---:|---:|---:|
| 1 | 0.00 | 1.14 | 1.15 | 1.56 |
| 1 | 0.02 | 1.16 | 1.17 | 1.59 |
| 1 | 0.10 | 1.24 | 1.25 | 1.70 |
| 5 | 0.00 | 1.14 | 1.15 | 1.56 |
| 5 | 0.02 | 1.24 | 1.25 | 1.70 |
| 5 | 0.10 | 1.64 | 1.66 | 2.24 |
| 10 | 0.00 | 1.14 | 1.15 | 1.56 |
| 10 | 0.02 | 1.34 | 1.36 | 1.83 |
| 10 | 0.10 | 2.14 | 2.16 | 2.93 |

These curves intentionally demonstrate different long-term continuations that a short test cannot distinguish. They are neither PLA nor PETG life predictions at 85°F. No creep-rupture allowable is inferred.
