# EF reinvest v2 / tapered lower rail and bearing-to-keel tie

Implemented experimental CAD and actual Orca slice. Physical print and strength are unqualified.

Spent extrusion is **60.682 cm3**, versus matched P1S G at 74.100 cm3: **18.108% less**. This includes sacrificial bridges and startup extrusion; it is not CAD volume or a weighed print.

Gross cut: 32.032% of G. Added back: 10.318 cm3, or 13.924 percentage points of G. Net saving: 18.108%.

Retained-material contact screen: 10.493240 mm maximum movement and 59.759355 MPa raw tensile peak at 12 kg. Stated linear tolerance: 1e-04. Status: CONTACT_SCREEN_AT_STATED_TOLERANCE_ERODED_MATERIAL_ONLY. Material omission: 13.510%. All finite stress samples and failed attempts remain preserved. Isotropic planning properties, boundary omission and physical qualification remain unresolved. This is the intermediate 1e-4 diagnostic; it does not establish the tighter 1e-5 gate. See the retained tighter attempts separately.

The upper mast has a six-millimetre web on the print base, with tapered shoulders returning to full width before either mounting region. This removes low-energy material in the current planning load case. The outer XY projection is retained. Its protected G bearing and capture geometry has zero CAD symmetric difference. Mounting axes stay fixed, washer-land support is 99.08%, and driver clearance is checked. The locating underside stays at Y=-32 mm for the first 25.4 mm from the wall. Moulding supplies no assumed structural support.

Use OrcaSlicer, P1S, 0.4 mm nozzle, calibrated PETG or ASA, two walls, 3 top/bottom layers at 0.2 mm, zero base infill and 100% rectilinear helpers. This receipt is the PETG slice; ASA requires a fresh process check. Import one object with aligned parts. Only the body prints. Every helper and its external tabs/halos must remain an infill modifier. STEP preserves alignment but does not encode slicer roles. The model-only 3MF records roles but carries no printer/filament calibration. The slice archive is engineering evidence, not machine-ready G-code.

Sacrificial 0.4 mm bridges count as spent plastic and receive zero structural or bond credit. Nominal credited paths form one connected component; that is not a guarantee of successful unsupported printing.

Combined STEP

https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/ef-reinvest-v2/bracket-with-modifiers.step

Body STEP

https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/ef-reinvest-v2/body-only.step

Model-only 3MF

https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/ef-reinvest-v2/part-model-and-modifiers.3mf

Individual helper STEPs

https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/ef-reinvest-v2/dense-chords-and-seats.step

https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/ef-reinvest-v2/central-rib-plane.step

https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/ef-reinvest-v2/local-transition-backing.step

Actual slice and effective settings

https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/ef-reinvest-v2/slice-evidence.zip

All files and verification receipts

https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/ef-reinvest-v2

![Actual credited material sections](toolpath-sections.png)
