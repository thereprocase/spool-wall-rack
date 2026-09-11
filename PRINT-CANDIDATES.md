# Printable CAD checkpoint index

**Current architecture direction: [six broader body sketches](designs/rev-g2/shape-seeds/README.md).**
These change the outer body and load paths while retaining rod/mount positions
and nominal spool clearance. They are unbuilt XY concepts, not printable STEP
handoffs. The bottom-corner and 15 mm outboard datums remain pending in the
[current contract](designs/rev-g2/INTERFACE-CONTRACT.md). Existing CAD downloads
below remain available unchanged.

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
