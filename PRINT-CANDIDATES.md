# Printable CAD checkpoint index

Geometry handoffs with helper solids and notes. Keep all relative body/helper positions. Import each STEP assembly as one object with multiple parts: the body prints, helpers become 100% infill modifiers. External tabs/halos must never print. STEP carries geometry, not slicer settings. Use OrcaSlicer and a calibrated printer/material profile. These are experimental geometries, not released load ratings.

## Current G recheck schedules

All five use the same unchanged G body and aligned helpers. Their differences are slicer settings. Each page links the combined STEP, individual helpers, exact settings and raw slice evidence. The old G 3MF defaults are historical; the current recheck requires at least two walls and 0% base infill.

| Schedule | STEP, helpers and notes |
|---|---|
| 2 walls / 2 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/2w-2layers/README.md) |
| 2 walls / 5 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/2w-5layers/README.md) |
| 2 walls / 8 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/2w-8layers/README.md) |
| 8 walls / 2 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/8w-2layers/README.md) |
| 8 walls / 8 top and bottom layers | [Handoff](designs/rev-g2/g-recheck/8w-8layers/README.md) |

The 2w/5-layer reference has a corrected 2D diagnostic. No corrected 3D strength result exists for these schedules.

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
