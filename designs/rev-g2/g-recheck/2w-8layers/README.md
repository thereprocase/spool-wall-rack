# G recheck: 2 walls, 8 top/bottom layers

Printable geometry is the unchanged Rev G body with its three aligned helpers.
This case is a slicer-material study, not a released structural design.

- [Body plus three named helper solids, STEP](../../../rev-g/bracket-with-modifiers.step)
- [Body alone, STEP](../../../rev-g/body-only.step)
- [Dense chords/seats helper](../../../rev-g/dense-chords-and-seats.step)
- [Lower internal plane](../../../rev-g/rib-plane-lower.step)
- [Upper internal plane](../../../rev-g/rib-plane-upper.step)
- [Original geometry and modifier illustrations](../../../rev-g/README.md)
- [Exact slice evidence ZIP](slice-evidence.zip)
- [Geometry hash verification](source-verification.json)
- [Current corrected analysis](../../../../analysis/rev-g2/README.md)

Keep every part in its supplied position. Only the body prints. Convert all three
helpers to **100% infill modifiers**; external selection tabs must not print.
STEP does not contain process settings. Use OrcaSlicer with:

| Setting | Value |
|---|---|
| Layer height | 0.2 mm |
| Wall loops | 2 |
| Top shell layers | 8 |
| Bottom shell layers | 8 |
| Top/bottom minimum thickness | 1.6 mm each |
| Base sparse infill | 0% |
| All three helper regions | 100% infill |

The ZIP preserves the actual audit G-code, audit 3MF, effective settings and hash
manifest. It is a neutral geometry audit, not a calibrated P1S PETG/ASA profile.
The earlier G 3MF uses different defaults; use this case's settings and evidence.
Sacrificial 0.4 mm bridge extrusion counts as spent plastic but receives zero
stiffness, strength or bonded-connection credit. Physical fit, print quality,
creep and strength remain unqualified.
