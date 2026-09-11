# G helper candidate 9be1dd4d87d3

Selection role: **economical**. Experimental CAD, not a qualified bracket or load rating.

[Combined body/helper STEP](bracket-with-modifiers.step) · [Model-only 3MF](rev-g-model-and-modifiers.3mf) · [Body STEP](body-only.step) · [Actual Orca slice and settings](slice-evidence.zip)

![Helper allocation comparison](../../../../analysis/rev-g2/evolution-results/batch-02/helper-directions.png)

The exterior body is byte-identical to G. These dimensions change the aligned 100% infill helper allocation:

| Parameter | mm |
|---|---:|
| bottom band | 1.6 |
| diagonal band | 1.8 |
| seat band | 4.5 |
| front seat band | 2 |
| lower tunnel collar mm | 3.5 |
| upper tunnel collar mm | 2.5 |

Import the model-only 3MF as one object with multiple parts. The body prints; the three helpers are 100% rectilinear infill modifiers. External tabs and halos must stay modifiers. Use OrcaSlicer, P1S/0.4 mm, calibrated PETG settings, at least two walls, five 0.2 mm top/bottom layers and 0% base infill. STEP carries geometry and alignment, not slicer roles.

Individual helpers: [dense chords and seats](dense-chords-and-seats.step), [lower internal plane](rib-plane-lower.step), [upper internal plane](rib-plane-upper.step). [CAD checks](helper-verification.json), [body provenance](source-verification.json), [3MF role checks](3mf-verification.json), [hashes](SHA256SUMS.json).

At 12 kg, the retained-material screen gives **4.3778 mm** maximum movement and **19.4607 MPa** raw tensile stress. Contact and equilibrium pass at the stated 1e-5 screen tolerance. The model omits 8.05% of nominal raw plastic.

[Detailed 3D audit](../../../../analysis/rev-g2/evolution-results/batch-02/9be1dd4d87d3/audit/audit.json) · [Search workflow and qualification limits](../../../../analysis/rev-g2/EVOLUTION.md).

![Retained-material movement and raw stress](../../../../analysis/rev-g2/evolution-results/batch-02/9be1dd4d87d3/audit/g-results.png)
