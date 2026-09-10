# E11 solved engineering results

The reinforced inner seat and mirrored 50° finish have been re-solved in 2D and
3D. The printable body stays solid CAD with two separate modifier helpers; only
the analysis domains remove sparse core material.

## Matched E10/E11 comparison

At identical load, wall count and solver assumptions, the reduced model gives
about **37% lower near-seat stress and 35% less front movement**. Loading only
the outer rod lowers the near-seat statistic **43.5%** in E11. The fixed comparison
window excludes added underside volume from its percentile denominator. This
supports reduced-section bending as the original mechanism, while real bearing
effects remain possible. [Comparison fields and refinement](COMPARISON.md).

The finished section model gives at least **1.539 times the bending I** and
**1.282 times the elastic section modulus** of the stronger adjacent plain-arm
reference band. This is local section margin, not a capacity rating.
[Section evidence](../../designs/closed-wall-e11/section-verification.json).

## Current 3D solution and refinement

12 kg equivalent per bracket; E = 1,000 MPa and ν = 0.35. The near-seat window is
X = 75–110 mm, Y = −24–0 mm, over the full width.

| Walls | Tetrahedra, coarse → fine | Front movement at E1000 (mm) | Movement change | Near-seat p99, coarse → fine (MPa) | p99 change |
|---:|---:|---:|---:|---:|---:|
| 8 | 180,806 → 235,089 | 2.306 | 2.56% | 3.56 → 3.79 | 6.37% |
| 10 | 149,156 → 242,810 | 2.098 | 2.27% | 3.79 → 3.79 | 0.10% |

![8-wall 3D stress and cutaway](fem-3d.png)

![Cuts through the actual solved tetrahedra](fem-sections.png)

[10-wall 3D view](fem-3d-10w.png). The 6 MPa colour cap makes the working field
visible; saved fields retain every solved value. Percentiles and raw peaks are
not stress allowables. These meshes do not establish asymptotic convergence,
printed orthotropy, layer adhesion, snap insertion, rupture or lifetime strength.

| Walls | Raw peak, coarse (MPa) | Raw peak, fine (MPa) | Fine free residual | 2D front coefficient relative to 3D |
|---:|---:|---:|---:|---:|
| 8 | 35.3 | 37.9 | 3.17e-08 | -0.55% |
| 10 | 75.3 | 51.1 | 3.11e-08 | +0.31% |

Raw peaks remain sensitive to small cells at chamfer, tunnel and analysis-core
intersections. Their locations and volumes are in `engineering-summary.json`.
All published 3D fields pass independently recomputed free residual, force and
moment balance below 1e-6. The affine test checks displacement, recovered stress
and strain energy; PARDISO agrees with an independent SuperLU patch solution.
The reduced solver has separate affine and beam checks.

An initial 10-wall coarse field failed the residual gate and was rejected. An
initial 8-wall refined topology produced a 335 MPa peak in a 3.10e-10 mm³
tunnel-mouth cell. Merging redundant same-domain CAD faces allowed new meshes
without deleting finite material for its stress value; front movement changed
only 0.13% in the 8-wall refined comparison. `analysis-topology-cleanup.json`
records CAD volume differences below 0.001 mm³. Mesh audits retain finite cells
and record only numerically zero-volume removal.

## Material movement and creep margin

The retained grade-specific room-temperature XY moduli are applied to E11's new
coefficients. They are not measured hot or aged properties.

| Material | Walls | E (MPa) | K (MPa·mm) | Initial front (mm) | One 1.25 kg roll (mm) | Ec for 5 mm bracket-only (MPa) | Compliance growth limit |
|---|---:|---:|---:|---:|---:|---:|---:|
| PLA | 8 | 3427 | 2306.3 | 0.673 | 0.070 | 461 | 7.43× |
| PETG | 10 | 2311 | 2098.2 | 0.908 | 0.095 | 420 | 5.51× |
| ASA | 8 | 2379 | 2306.3 | 0.969 | 0.101 | 461 | 5.16× |
| PA6-GF dry | 8 | 5357 | 2306.3 | 0.431 | 0.045 | 461 | 11.61× |
| PA6-GF wet | 8 | 1794 | 2306.3 | 1.286 | 0.134 | 461 | 3.89× |

`δ(t,T) = K × J(t,T) = K / Ec(t,T)` assumes common linear-viscoelastic compliance
and an unchanged load/contact state. For the whole rack use **Ec ≥ K / (5 mm −
dowel movement − wall/fastener movement)**. Retain the project screening target
of at least 1.0 GPa effective creep modulus at the intended age and loaded
temperature history; it is not a published allowable or rupture criterion.

The one-roll calculation assigns its entire reaction to one bracket for the
stated simple/two-equal-span case. Fast unloading uses aged instantaneous
modulus, not reversal of accumulated creep. Other support arrangements,
overhangs and impact need their actual reactions.

PLA/PETG remain prototype choices; ASA is the higher-temperature comparison.
PA6-GF dry and water-conditioned cases stay separate. Match the source's
100°C/16-hour annealing and conditioning before using its properties, and
recheck fit. [Exact grades, source URLs and hashes](../../designs/closed-wall-e6/material-reference-data.json).

## 24 kg brief proof scenario

Elastic stress and movement double at 24 kg with the same load pattern and
active contact. This is linear scaling, not a damage simulation or a performed
physical proof test.

| Walls | Near-seat p99 at 24 kg (MPa) | Front movement at E1000 (mm) |
|---:|---:|---:|
| 8 | 7.58 | 4.613 |
| 10 | 7.59 | 4.196 |

## Screw landings and contact

The global model uses compression-only wall contact, rigid washer axial
restraints and rigid shank shear restraints. No tightening friction or arbitrary
preload is credited. The lower washer carries substantial outward demand.

| Walls | Upper washer outward demand (N) | Lower washer outward demand (N) |
|---:|---:|---:|
| 8 | 15.6 | 207.7 |
| 10 | 14.8 | 208.5 |

The separate **500 N upper-landing submodel** uses the actual 3.6 mm land and flat rear support. Its 33,792 → 84,237 tetrahedron refinement changes washer movement by 1.66%. Fine mean movement is **0.01207 mm at E1000**, with a **5.00 MPa** raw peak. This constant-force scenario does not predict installed clamp-force retention.

![E11 screw-landing stress](fem-landing.png)

Retain the backed 3.6 mm land. A gap behind it creates bending/punching conditions
outside this submodel. Use the checked washer dimensions and substrate-appropriate
fixings. Separate scalar von Mises maxima from service and tightening cannot be
added as if they were stress tensors.

## Creep sensitivity with E11 coefficients

The retained [PETG study](https://doi.org/10.3390/polym17152075) supplies a short-time
example at about 21.3°C, tested to 20 hours. Its approximate Figure 26 spectrum
gives compliance multipliers near 1.07 at five hours and 1.10 at twenty hours.
The formal 1.14 plateau is built into the finite fit and does not prove years of
behavior at 85°F for these bracket grades.

![Short-time evidence and unmeasured tails](creep-sensitivity.png)

These deliberately different long-time tails use E11's new movement coefficients.
They are **not PLA/PETG service-life forecasts**.

| Years | Assumed extra compliance / year | Multiplier | PLA front (mm) | PETG front (mm) |
|---:|---:|---:|---:|---:|
| 1 | 0.00 | 1.14 | 0.77 | 1.03 |
| 1 | 0.02 | 1.16 | 0.78 | 1.05 |
| 1 | 0.10 | 1.24 | 0.83 | 1.13 |
| 5 | 0.00 | 1.14 | 0.77 | 1.03 |
| 5 | 0.02 | 1.24 | 0.83 | 1.13 |
| 5 | 0.10 | 1.64 | 1.10 | 1.49 |
| 10 | 0.00 | 1.14 | 0.77 | 1.03 |
| 10 | 0.02 | 1.34 | 0.90 | 1.22 |
| 10 | 0.10 | 2.14 | 1.44 | 1.94 |

At 85°F sustained and 100°F for six loaded hours/year, the uncalibrated Arrhenius
sensitivity assumes 50/100/200 kJ/mol activation energy. Hot-rate factors are
1.70/2.90/8.42, adding 0.048%/0.130%/0.508% to annual equivalent time. This does
not prove thermal adequacy; actual hot softening, nonlinear creep and rupture
remain unqualified. Full numerical values are in `engineering-summary.json`.

## Print evidence and qualification boundary

The delivered STEP contains one valid body and two aligned helpers. Both faces
measure 50°. Complete flexible-finger sectors match E10 at nine print depths;
hardware and nominal spool-clearance checks pass. Actual OrcaSlicer 8/10-wall
G-code verifies the four solid bands and seat-wall footprints.
[CAD and toolpath evidence](../../designs/closed-wall-e11/README.md).

The 5 mm total loaded-movement and 1 mm per-roll-change limits include dowels and
mounts. Rod fit, snap behavior, extrusion quality, sustained/hot movement and
creep rupture still need physical qualification. No lifetime safe spool count
is assigned by this revision.

[Reproduce](README.md) · [Current print and engineering guide](../../README.md).
