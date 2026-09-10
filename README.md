# Spool wall rack — E9 running prototype

**The front rail is now 12 mm higher than the rear. Both broad faces have 2 mm chamfers; exposed wall-facet changes have R2 fillets.** The back arm is reshaped to preserve spool clearance, and both retainers follow the new contact directions.

**[Download the current STEP](designs/closed-wall-e9/bracket-with-modifier-helpers.step)** · [Print setup and verified geometry](designs/closed-wall-e9/README.md) · [Previous level-rail engineering guide](E8-ENGINEERING-GUIDE.md)

![Current E9 CAD](designs/closed-wall-e9/progress-exterior.png)

![E9 profile and actual chamfer section](designs/closed-wall-e9/engineering-drawing.png)

## Latest checkpoint

E9 passes its STEP, hardware-clearance, mesh-closure and finish checks. The 180–220 mm spool sweep has **3.93 mm minimum nominal clearance**. Direct material probes verify both mirrored 2 mm face chamfers along nine structural edges. The exposed wall direction changes follow nominal R2 arcs. The raised seat connects continuously to the arm base without the bottom stub from the first lift attempt.

The revised 2D model and the 10-wall 3D refinement are complete. At 12 kg equivalent bracket load, the 10-wall model predicts **1.37 mm initial front-seat movement** using the PETG reference modulus, versus 1.66 mm for E8. The 500 N screw-landing model still supports retaining the 3.6 mm clamping thickness. The 8-wall whole-bracket solve is finishing; its E9 material and creep table will be published after verification.

![E9 2D stress field](analysis/e9/fem-2d.png)

![E9 10-wall 3D stress field](analysis/e9/fem-3d-10w.png)

These are isotropic numerical screening models with zero sparse-infill credit, not tested lifetime ratings.

## Printing

Use the supplied side-print orientation. Import the STEP as one object with three aligned parts. Choose body wall count and 15% infill; set six 0.2 mm top and bottom layers. Convert the two helper solids to **100% infill modifiers**, preserving Z = 7.6–8.8 and 15.2–16.4 mm. Inspect all four solid planes and the actual contour-wall thickness before printing.

Prototype starting settings remain **8 walls for PLA and 10 for PETG**, using the assumed 0.42/0.45 mm line widths at 0.2 mm layers. Sparse infill receives no strength credit. See the [complete setup](designs/closed-wall-e9/README.md); these are test settings, not a lifetime load rating.

## Loads, materials and serviceability

The analysis target remains 12 kg equivalent per bracket on the stated 16-inch support arrangement, with 85°F sustained and 100°F for six hours per year. Accept up to **5 mm total movement under full load** and **1 mm change when adding or removing one full spool**; check creep, cracking, retention and fastener behavior separately.

For a 200 mm spool, the +12 mm rail geometry shifts its center from 140 to about 128 mm from the wall. Vertical load splits approximately 65% rear / 35% front. Wall moment falls 8.6% and net moment about the rear rail falls 24%. The front rail remains a bearing support as well as a higher roll-out obstacle.

The [E8 full material and creep guide](E8-ENGINEERING-GUIDE.md) preserves source data, print rationale, screw-landing analysis and actual level-rail FEM images. Its numerical geometry coefficients must not be applied to E9. Updated E9 stress fields and creep margins will replace that baseline in this guide after solving.

## History and source

[Current E9 source and checks](designs/closed-wall-e9) · [E9 structural analysis](analysis/e9) · [E8 engineering baseline](E8-ENGINEERING-GUIDE.md) · [Design journal](DESIGN-JOURNAL.md) · [Separate future open-web path](future/open-web/README.md)
