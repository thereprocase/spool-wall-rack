# E12 solved engineering results

The reinforced inner seat and mirrored 50° finish have been re-solved in 2D and
3D. The printable body stays solid CAD with two separate modifier helpers; only
the analysis domains remove sparse core material.

## Quarter-depth tradeoff

E12 reduces added depth from **38 to 9.5 mm**, meeting the one-quarter target
and one-third maximum. The broader smooth blend retains the fingers, R6 rigid
shoulders, continuous plates and mirrored 50° chamfers. No relief holes were
needed for the measured improvement.

The matched reduced model gives **31.7–32.5% lower near-seat stress than E10**,
versus E11's 37.4–37.6%. Movement is 5.6–7.1% higher than E11, while the added
protrusion is 75% smaller. The outer-rod-only statistic improves about 35% over
E10. [All three revisions, exact values and mesh checks](COMPARISON.md).

The local finished section improves over E10 but no longer exceeds both
adjacent plain-arm bands. This is the explicit tradeoff from the new depth
cap; the adjacent arms were not weakened to manufacture a favorable ratio.
[Section audit](../../designs/closed-wall-e12/section-verification.json).

## Current 3D solution and refinement

12 kg equivalent per bracket; E = 1,000 MPa and ν = 0.35. The near-seat window is
X = 75–110 mm, Y = −24–0 mm, over the full width.

| Walls | Tetrahedra, coarse → fine | Front movement at E1000 (mm) | Movement change | Near-seat p99, coarse → fine (MPa) | p99 change |
|---:|---:|---:|---:|---:|---:|
| 8 | 136,844 → 209,627 | 2.473 | 2.35% | 3.99 → 4.34 | 8.80% |
| 10 | 159,490 → 211,444 | 2.242 | 1.43% | 3.94 → 4.10 | 3.87% |

![8-wall 3D stress and cutaway](fem-3d.png)

![Cuts through the actual solved tetrahedra](fem-sections.png)

[10-wall 3D view](fem-3d-10w.png). The 6 MPa colour cap makes the working field
visible; saved fields retain every solved value. Percentiles and raw peaks are
not stress allowables. These meshes do not establish asymptotic convergence,
printed orthotropy, layer adhesion, snap insertion, rupture or lifetime strength.

| Walls | Raw peak, coarse (MPa) | Raw peak, fine (MPa) | Fine free residual | 2D front coefficient relative to 3D |
|---:|---:|---:|---:|---:|
| 8 | 41.6 | 35.2 | 6.75e-08 | -0.61% |
| 10 | 19.5 | 38.9 | 5.35e-08 | -0.85% |

Raw peaks remain sensitive to small cells at chamfer, tunnel and analysis-core
intersections. Their locations and volumes are in `engineering-summary.json`.
All published 3D fields pass independently recomputed free residual, force and
moment balance below 1e-6. The affine test checks displacement, recovered stress
and strain energy; PARDISO agrees with an independent SuperLU patch solution.
The reduced solver has separate affine and beam checks.

All four global domains use audited same-domain CAD face cleanup. The initial
10-wall h3 HXT field failed the residual gate (2.19e-4); it was rejected. A
surface-mesher retry crashed before producing an accepted field. The accepted
10-wall pair uses h2.5/h2 Delaunay meshes on the same geometry. The 8-wall pair
uses h3/h2. No finite cells were deleted for their stress values.
`analysis-topology-cleanup.json` and mesh audits record volumes and any
numerically zero-volume removal. Saved fields retain raw peaks.

## Material movement and creep margin

The retained grade-specific room-temperature XY moduli are applied to E12's new
coefficients. They are not measured hot or aged properties.

| Material | Walls | E (MPa) | K (MPa·mm) | Initial front (mm) | One 1.25 kg roll (mm) | Ec for 5 mm bracket-only (MPa) | Compliance growth limit |
|---|---:|---:|---:|---:|---:|---:|---:|
| PLA | 8 | 3427 | 2472.5 | 0.722 | 0.075 | 495 | 6.93× |
| PETG | 10 | 2311 | 2241.9 | 0.970 | 0.101 | 448 | 5.15× |
| ASA | 8 | 2379 | 2472.5 | 1.039 | 0.108 | 495 | 4.81× |
| PA6-GF dry | 8 | 5357 | 2472.5 | 0.462 | 0.048 | 495 | 10.83× |
| PA6-GF wet | 8 | 1794 | 2472.5 | 1.379 | 0.144 | 495 | 3.63× |

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
| 8 | 8.68 | 4.945 |
| 10 | 8.19 | 4.484 |

## Screw landings and contact

The global model uses compression-only wall contact, rigid washer axial
restraints and rigid shank shear restraints. No tightening friction or arbitrary
preload is credited. The lower washer carries substantial outward demand.

| Walls | Upper washer outward demand (N) | Lower washer outward demand (N) |
|---:|---:|---:|
| 8 | 15.4 | 207.7 |
| 10 | 14.8 | 202.9 |

The separate **500 N upper-landing submodel** uses the actual 3.6 mm land and flat rear support. Its 33,749 → 83,876 tetrahedron refinement changes washer movement by 1.68%. Fine mean movement is **0.01207 mm at E1000**, with a **5.00 MPa** raw peak. This constant-force scenario does not predict installed clamp-force retention.

![E12 screw-landing stress](fem-landing.png)

Retain the backed 3.6 mm land. A gap behind it creates bending/punching conditions
outside this submodel. Use the checked washer dimensions and substrate-appropriate
fixings. Separate scalar von Mises maxima from service and tightening cannot be
added as if they were stress tensors.

## Creep sensitivity with E12 coefficients

The retained [PETG study](https://doi.org/10.3390/polym17152075) supplies a short-time
example at about 21.3°C, tested to 20 hours. Its approximate Figure 26 spectrum
gives compliance multipliers near 1.07 at five hours and 1.10 at twenty hours.
The formal 1.14 plateau is built into the finite fit and does not prove years of
behavior at 85°F for these bracket grades.

![Short-time evidence and unmeasured tails](creep-sensitivity.png)

These deliberately different long-time tails use E12's new movement coefficients.
They are **not PLA/PETG service-life forecasts**.

| Years | Assumed extra compliance / year | Multiplier | PLA front (mm) | PETG front (mm) |
|---:|---:|---:|---:|---:|
| 1 | 0.00 | 1.14 | 0.82 | 1.11 |
| 1 | 0.02 | 1.16 | 0.84 | 1.13 |
| 1 | 0.10 | 1.24 | 0.89 | 1.20 |
| 5 | 0.00 | 1.14 | 0.82 | 1.11 |
| 5 | 0.02 | 1.24 | 0.89 | 1.20 |
| 5 | 0.10 | 1.64 | 1.18 | 1.59 |
| 10 | 0.00 | 1.14 | 0.82 | 1.11 |
| 10 | 0.02 | 1.34 | 0.97 | 1.30 |
| 10 | 0.10 | 2.14 | 1.54 | 2.08 |

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
[CAD and toolpath evidence](../../designs/closed-wall-e12/README.md).

The 5 mm total loaded-movement and 1 mm per-roll-change limits include dowels and
mounts. Rod fit, snap behavior, extrusion quality, sustained/hot movement and
creep rupture still need physical qualification. No lifetime safe spool count
is assigned by this revision.

[Reproduce](README.md) · [Current print and engineering guide](../../README.md).
