# E8 — solid STEP body with modifier helpers

**[Download the STEP assembly](bracket-with-modifier-helpers.step).** It contains one solid bracket body and two named, overlapping helper solids. The user chooses wall count and infill for the body, then converts the helpers to modifiers set to 100% infill. No infill pattern or support grid is modeled in the CAD.

![Modifier locations](modifier-stack.png)

## Slicer setup

1. Import the STEP while preserving its three aligned components as parts of one object. Keep the supplied orientation and relative positions; do not arrange the helper parts separately.
2. Select `MAIN_BODY_SET_WALLS_AND_INFILL`. Choose the desired wall count and body infill percentage. The working assumptions remain 0.2 mm layers, 15% body infill and 1.2 mm top/bottom faces; wall count is user-selected.
3. Change both parts named `MODIFIER_…_100_PERCENT_INFILL_…` to **modifier geometry**, and set their infill to **100%**. Use an infill pattern supported by the slicer at that density. These helpers must not print as independent slabs or be fused into the body.
4. Inspect the sliced preview. Confirm two continuous 1.2 mm internal solid bands, sparse infill between them, the desired perimeter thickness, and clear fastener openings. Save the configured slicer project for repeat prints.

| Assembly component | Role | Print Z |
|---|---|---:|
| Main body | Solid CAD envelope; user-selected walls/infill | 0–24 mm |
| Helper 1 | Change to 100% infill modifier | 7.6–8.8 mm |
| Helper 2 | Change to 100% infill modifier | 15.2–16.4 mm |

The helpers are 1.2 mm-thick solids, not zero-thickness surfaces. Each covers the body's entire XY projection with 2 mm of margin on every side, so the slicer can intersect it with the body to create the full internal plate. At 0.2 mm layers each band is six layers thick. Top and bottom faces come from the body's normal solid-layer settings. The slicer generates sparse infill beneath and between the internal bands.

STEP preserves geometry and component names; it does **not** encode modifier status, wall count, infill density or a printer profile. If the slicer does not preserve STEP components, load [body-only.stl](body-only.stl), [helper-1.stl](helper-1.stl) and [helper-2.stl](helper-2.stl) as one object with aligned parts, then assign the helpers as modifiers. All three STL files share the STEP's coordinates.

[Modifier mesh concept and settings](https://help.prusa3d.com/article/modifiers_1767) · [Solid layers over sparse infill](https://help.prusa3d.com/article/layers-and-perimeters_1748).

## Retained bracket features

![Actual E8 body envelope](progress-exterior.png)

The body retains E7's dowel seats, smooth snap roots, tapered broad-face chamfers and full-height wall contact. The fixings retain 3.6 mm washer-to-wall clamping thickness, Ø5.2 mm screw clearance, Ø16 mm nominal driver access, sloping access roofs and axes at Y = 164/40 mm. Nominal #8/#10 screws and M5 shanks fit the same clearance geometry. The STEP roundtrip retains three valid solids; geometric checks confirm the M5 shank, Ø13 mm washer and Ø15.8 mm straight driver clearance at both fixings.

E7's modeled cell lattice and large hollow bands are removed. E8 does not adopt the separate 34 mm arm-depth proposal. **Structural wall thickness now comes from slicing**, rather than an assumed 2.4 mm CAD shell. The main body's solid CAD volume is not printed material volume or mass. Previous hollow-section calculations do not rate arbitrary user-selected print settings, and sparse infill still receives zero structural credit.

The delivered STEP is an aligned geometry package, not a preconfigured slicer project or a validated load rating. Confirm actual solid bands, bridge behavior and fastener fit in the preview and a representative print.

## Files and rebuild

- [STEP assembly with helpers](bracket-with-modifier-helpers.step) — preferred handoff.
- [Body-only STEP](body-only.step) — external/functional geometry without helpers.
- [STEP and clearance verification](verification.json).
- [Build dimensions and helper bounds](build-verification.json).

Use OpenSCAD and Python with CadQuery/OCP, NumPy, Shapely, Matplotlib, Pillow and VTK. From this directory:

```sh
openscad -o profile.svg -D 'part="profile"' bracket.scad
python build_step.py
python verify_step.py
python render_cpu.py
python draw_helpers.py
```

The two helper solids intentionally overlap the main body. Do not union them when exporting the assembly. Keep the separate open-web exploration isolated.
