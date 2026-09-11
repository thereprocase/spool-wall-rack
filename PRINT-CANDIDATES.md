# Printable CAD checkpoint index

## Current print controls and connected brace

Eight deliberate print controls have aligned body/helper STEP, model-only 3MF, actual Orca slices, settings audits and source hashes. The successful recovered ASA print is associated with E13 and seven walls, not the eight-wall G control used as this study's denominator.

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/print-controls

https://github.com/thereprocase/spool-wall-rack/blob/main/designs/rev-g2/print-controls/RECOVERED-PRINTS.md

The direct-core E+F trial cuts 27.048% before reinvestment, adds back 5.406 cm3, and retains 22.492% net saving. Its 4.9818 mm intermediate movement diagnostic exceeds the 4 mm allocation. Numerical tightening fails its bound. The complete handoff is retained as an implemented, rejected stiffness trial.

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/print-controls/ef-core-asa-4w-1p6

The upper-mast cut and earlier connected helper trial also have complete CAD/slice handoffs. Their percentages use the older two-wall, 1.0 mm skin G reference.

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-cut-v4

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-reinvest-v2


## Implemented E + F material-allocation trials

These historical thin-reference schedules have aligned body/helper STEP files, model-only 3MF, actual P1S PETG
slicing, checks and hashes. They are experimental and physically unqualified.
The matched G slice spends 74.100 cm3. Sacrificial bridges count in these totals
and receive no structural or bond credit.

| Candidate | Spent extrusion, cm3 | Saving versus G | Role |
|---|---:|---:|---|
| ef-hybrid-v1 | 73.007 | 1.475% | First reinforced reference; accepted numerical screen is worse than G |
| ef-lean-v1 | 65.966 | 10.977% | Intermediate material trial; mechanics untested |
| ef-lean-v2 | 61.613 | 16.851% | Intermediate material trial; mechanics untested |
| ef-cut-v3 | 52.454 | 29.211% | Intermediate 1e-4 diagnostic; tight check failed |
| ef-reinvest-v1 | 58.796 | 20.653% | Adds 6.342 cm3; stiffness remains inadequate |

Browse each handoff for direct STEP/helper/3MF downloads and verification.

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-hybrid-v1

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-lean-v1

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-lean-v2

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-cut-v3

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-reinvest-v1

The six broader architecture seeds remain XY sketches. The selected E+F hybrid
is now built separately. Preserve G's lower locating datum and the 25.4 mm
horizontal underside from the wall; keep the fixed rod/mount positions and
spool clearance. Previous CAD handoffs remain preserved below.

## G evolutionary helper variants

[Screening workflow and measured timings](analysis/rev-g2/EVOLUTION.md).
The 100 reduced proposals are parameter evaluations. These three selected
variants have actual body/helper STEP assemblies and model-only 3MF files.
They use the G body, two walls, five top/bottom layers, 0% base infill and
100% helpers. These are experimental handoffs with unresolved qualification.

| Candidate | Aligned assembly | Notes and individual helpers |
|---|---|---|
| Balanced screen leader, f9ad9cdbc331 | [STEP](designs/rev-g2/evolution/f9ad9cdbc331/bracket-with-modifiers.step) | [Handoff](designs/rev-g2/evolution/f9ad9cdbc331/README.md) |
| Second stiffness candidate, 0c3bac68efa9 | [STEP](designs/rev-g2/evolution/0c3bac68efa9/bracket-with-modifiers.step) | [Handoff](designs/rev-g2/evolution/0c3bac68efa9/README.md) |
| Lighter inner-seat helper, 9be1dd4d87d3 | [STEP](designs/rev-g2/evolution/9be1dd4d87d3/bracket-with-modifiers.step) | [Handoff](designs/rev-g2/evolution/9be1dd4d87d3/README.md) |

Fresh 10.75 / 12 / 13.25 kg G contact checks are documented in [G results](analysis/rev-g2/G-RESULTS.md). One spool changes bracket movement by about 0.452 mm; material accuracy and physical qualification remain open.

Geometry handoffs with helper solids and notes. Keep all relative body/helper positions. Import each STEP assembly as one object with multiple parts: the body prints, helpers become 100% infill modifiers. External tabs/halos must never print. STEP carries geometry, not slicer settings. Use OrcaSlicer and a calibrated printer/material profile. These are experimental geometries, not released load ratings.

[Completed G contact screen](analysis/rev-g2/G-RESULTS.md): 4.3355 mm maximum
movement and 20.0254 MPa raw peak tensile stress at 12 kg in the retained-material
model. Contact and numerical sensitivity are checked; 8.02% material omission
and physical qualification remain unresolved. The existing aligned G body and
three helper exports below are the exact CAD handoff; no new architecture is added.

## Current G recheck schedules

All five use the same unchanged G body and aligned helpers. Their differences are slicer settings. Each page links the combined STEP, individual helpers, exact settings and raw slice evidence. The old G 3MF defaults are historical; the current recheck requires at least two walls and 0% base infill.

| Schedule | STEP, helpers and notes |
|---|---|
| 2 walls / 2 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/2w-2layers/README.md) |
| 2 walls / 5 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/2w-5layers/README.md) |
| 2 walls / 8 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/2w-8layers/README.md) |
| 8 walls / 2 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/8w-2layers/README.md) |
| 8 walls / 8 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/8w-8layers/README.md) |

The 2w/5-layer reference has a corrected 2D diagnostic and the eroded-material
3D contact screen linked above. Physical strength remains unqualified.

[Adaptive mesh and P1S/PETG demo checkpoint](analysis/rev-g2/ADAPTIVE-MESH.md):
the implemented coarse/fine GPU adapter passes independent fixtures and
halves the protected 0.2 mm G mesh. That checkpoint predates the completed contact screen linked above.
The separate fresh PETG slice reuses G's existing body and three helpers;
it adds no architecture or physical qualification to the handoffs below.

[GPU validation checkpoint](analysis/rev-g2/GPU-VALIDATION.md): an installed
free GPU backend passes small 3D fixtures and an actual-slice crop patch test.
The crop's voxel material loss remains unresolved. This adds analysis evidence;
the eight implemented handoffs and five slicing schedules below are unchanged.

## Implemented recent architecture alternatives

| Idea | Aligned STEP body plus helpers | Notes |
|---|---|---|
| G full-plane research finalist | [STEP](designs/rev-g/bracket-with-modifiers.step) | [Notes](designs/rev-g/README.md) |
| G thin shaped planes, seed 1 | [STEP](designs/rev-g/studies/seed1-best/bracket-with-modifiers.step) | [Notes](designs/rev-g/studies/seed1-best/README.md) |
| G archived full-plane best | [STEP](designs/rev-g/studies/full-plane-best/bracket-with-modifiers.step) | [Notes](designs/rev-g/studies/full-plane-best/README.md) |
| G wider inner-seat support | [STEP](designs/rev-g/studies/seat-support/bracket-with-modifiers.step) | [Notes](designs/rev-g/studies/seat-support/README.md) |
| G repaired F light helpers | [STEP](designs/rev-g/studies/repaired-f-light/bracket-with-modifiers.step) | [Notes](designs/rev-g/studies/repaired-f-light/README.md) |
| F shaped planes / three walls | [STEP](designs/rev-f/bracket-with-modifiers.step) | [Notes](designs/rev-f/README.md) |
| F full planes / four walls | [STEP](designs/rev-f/studies/full-plane-4w/bracket-with-modifiers.step) | [Notes](designs/rev-f/studies/full-plane-4w/README.md) |
| E13 continuous body and helpers | [STEP](designs/closed-wall-e13/bracket-with-modifier-helpers.step) | [Notes](designs/closed-wall-e13/README.md) |

Each notes page includes the original process choices, illustrations and geometry/slicing/mechanical status. Historical one-wall candidates remain evidence only; the G2 minimum of two walls requires a new slice and analysis before reuse. Old G material approximations do not establish failure or success of the corrected print.

## G2 concepts awaiting CAD

[Seven-family worksheet](designs/rev-g2/ARCHITECTURE-WORKSHEET.md): continuous plates, triangular frame, closed-section seat arms, cross-width portal, drop cradle, thick-seat portal, and layered shear box. These are concept notes, not printable candidates. Every future checkpoint must include its parameterized body, aligned STEP helpers, sections, process notes and actual slicing evidence. This remains explicit unfinished work in the restart handoff.
