# E8 wall-count starting points

**For the first full-load prototype: PLA 8 walls; PETG 10 walls.** Use both 1.2 mm helpers as 100% infill modifiers, 1.2 mm top/bottom faces, 0.2 mm layers and 15% body infill. Sparse infill receives zero structural credit. A single starting setting for both materials can use 10 walls.

These are engineering prototype selections with additional section margin, not proven minimum counts or a claim that the fully packed rack is creep-qualified. E8 still has the approximately 28 mm arm depth; the previous 34 mm-depth proposal was not implemented.

## Counts versus thickness

The following mapping assumes a 0.4 mm nozzle, 0.42 mm outer lines, 0.45 mm inner lines and 0.2 mm layers. These line widths are explicit assumptions, not an assertion about every Bambu profile. Path overlap makes wall thickness smaller than wall count multiplied by nominal line width. Adaptive-width paths and local geometry can change the result; inspect actual sliced thickness. [Extrusion-spacing model](https://manual.slic3r.org/advanced/flow-math).

| Wall count | Approximate perimeter thickness | Use in this study |
|---:|---:|---|
| 3 | 1.23 mm | Original low-wall assumption; substantially thinner than the later 2.4 mm shell study |
| 4 | 1.64 mm | Light shell comparison |
| 6 | 2.46 mm | Roughly reproduces the old nominal 2.4 mm perimeter away from local details |
| **8** | **3.27 mm** | **PLA prototype starting point** |
| 9 | 3.68 mm | Closest listed count to the earlier 3.6 mm perimeter proposal |
| **10** | **4.08 mm** | **PETG prototype starting point** |
| 12 | 4.90 mm | Diminishing-return stiffness comparison |

Do not substitute nozzle diameter for extrusion width or assume the requested number of paths fits everywhere. Thin snap fingers cannot contain eight or ten full-width wall lines; the slicer fills the available geometry. The wall setting does not enlarge the finger's CAD outline.

## Strength and stiffness interpretation

The reference PLA flexural modulus is approximately 3.23 GPa; the current reference PETG is approximately 2.28 GPa. PETG therefore benefits from additional section to reduce initial flex. [Reference grades and sources](../closed-wall-e6/material-reference-data.json). This selection does not imply that PETG universally has lower strength or worse creep than PLA.

An ideal 24 mm-wide, 28 mm-deep rectangular forearm with four continuous 1.2 mm plates gives approximately **0.22 mm initial vertical deflection for PLA at 8 walls**, and **0.27 mm for PETG at 10 walls**, under half the 12 kg bracket load at the end of a 100 mm forearm. These are local, room-reference-modulus comparisons. They omit the varying arm section, outward thrust, knee, wall connection, bevels, shear and creep; they are not complete-bracket movements or service-temperature predictions. They also do not demonstrate equal stiffness between the two selections.

The 8/10 choice provides a useful first test configuration without adopting the much deeper arm. More perimeter helps the longitudinal load path, but it cannot establish a safe screw-land load, snap strain or long-term capacity by itself. Neither this screen nor the previous material study establishes an allowable stress or safe maximum spool count for E8.

At 85°F sustained and 100°F for six hours/year, grade-specific time-dependent deformation remains the outstanding material question. A successful short static load or a small initial deflection does not answer it. Preserve the full-row 12 kg qualification target and check the actual sliced/printed bracket before assigning adequacy.

[Calculation](check_wall_counts.py) · [Inputs and results](wall-count-screen.json). No CAD geometry changes accompany these settings.
