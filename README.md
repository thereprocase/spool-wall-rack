# Spool wall rack

A wall-mounted filament rack using nominal 1-inch wooden dowels. The bracket prints on its side so continuous L-shaped plates carry the principal bending load in the layer plane. Spools must slide across bracket locations without contacting the plastic.

**Current prototype: E1 — rotated snap retainers and a 2.4 mm structural perimeter.** Geometry checked; internal roof printing, snap insertion behavior, and structural/creep capacity remain unresolved. No safe spool count is assigned.

![E1 engineering drawing](designs/closed-wall-e1/retainer-engineering.png)

## Design journal

Latest checkpoint: **E1 geometry and snap-seat fit coupon.** Next: validate curved-finger insertion and resolve the unsupported internal roofs. Full bracket printing and load ratings remain blocked by those checks.

### E1 — align the snap opening with spool contact

Rotated each seat so its opening faces the spool contact and its rigid bearing sector lies directly opposite. Mirrored the two seats. This preserves the exposed track surface while directing the spool reaction into the thick bearing sector. Added separate 1.35 mm curved fingers and rounded noses, with a nominal 24.51 mm throat. A 185° concentric wrap was rejected because its capture disappears within the seat clearance.

The new profile passes the nominal 180–220 mm flange clearance sweep. Minimum retainer clearance is 6.91 mm; minimum full-profile clearance is 5.40 mm. These are seated geometric clearances, not insertion-path or tolerance validation. The thick bearing sector is 5 mm radially; the structural perimeter increases from 1.35 to 2.4 mm. Continuous side and internal plates remain 1.2 mm.

The drawing at the top of this page comes from the current CAD profile. The [8 mm coupon](designs/closed-wall-e1/snap-coupon-8mm.stl) makes the first fit trial smaller than a full bracket. It does not establish the 24 mm-wide bracket's insertion force.

### D — verify continuous internal planes

Established the upward wall leg and four full L-shaped plates. Rebuilt the delivered mesh, checked edge closure and all 120 layer-center sections, and independently checked nominal spool clearance. Found the main manufacturing issue: true empty cavities leave approximately 84 mm of unsupported region near the knee. A global infill percentage does not support those cavities.

![D continuous-plate section](designs/closed-wall-d/design-section.png)

[Exterior](designs/closed-wall-d/progress-exterior.png) · [Arm cutaway](designs/closed-wall-d/progress-cutaway.png) · [Separated plate explanation](designs/closed-wall-d/progress-plates.png)

### Deferred — open-web alternative

Archived the separate reference concept. It has no shared geometry changes or load claims with the current closed-wall path.

## Current files

- [Parametric bracket CAD](designs/closed-wall-e1/bracket.scad)
- [Bracket STL — prototype](designs/closed-wall-e1/bracket.stl)
- [Snap retainer CAD](designs/closed-wall-e1/retainer.scad)
- [8 mm wide snap coupon STL](designs/closed-wall-e1/snap-coupon-8mm.stl) — fit/behavior sample; the full bracket is 24 mm wide.
- [Geometric verification](designs/closed-wall-e1/verification.json)
- [Design decisions and pending work](DESIGN.md)
- [Revision D checkpoint and independent audit](designs/closed-wall-d/audit/VERIFICATION.md)
- [Separate future open-web reference](future/open-web/README.md)

## Geometry

| Feature | E1 value |
|---|---:|
| Nominal dowel diameter | 25.4 mm |
| Seat diameter / spacing | 26 / 150 mm |
| Single-part envelope | approximately 243.82 × 240 × 24 mm |
| Structural perimeter in print XY | 2.4 mm |
| Exterior side plates | 2 × 1.2 mm |
| Internal continuous plates | 2 × 1.2 mm |
| Intervening air-band height | 3 × 6.4 mm |
| Snap finger bending thickness | 1.35 mm |
| Rigid seat radial thickness | 5 mm |
| Nominal capture wrap / throat | 218° / approximately 24.51 mm |

The snap opening faces the spool contact. The thick seat lies 180° opposite that contact for the 200 mm reference spool. Front and rear retainers are mirrored. The contact direction varies with spool diameter; the nominal seated geometry was checked over 180–220 mm. Minimum computed clearance is 5.40 mm for the complete bracket and 6.91 mm for the rear retainer, with symmetry applying to the front retainer.

## Build and inspect

Install OpenSCAD and Python with NumPy and Matplotlib. Revision D's independent mesh audit also uses VTK and SciPy.

```sh
openscad -o designs/closed-wall-e1/bracket.stl designs/closed-wall-e1/bracket.scad
openscad -o designs/closed-wall-e1/profile.svg -D 'part="profile"' designs/closed-wall-e1/bracket.scad
openscad -o designs/closed-wall-e1/retainer-profile.svg -D 'part="profile"' designs/closed-wall-e1/retainer.scad
openscad -o designs/closed-wall-e1/snap-coupon-8mm.stl designs/closed-wall-e1/retainer.scad
python designs/closed-wall-e1/check_and_draw.py
```

The exported STL already lies broad-side-down. The coupon prints in a different, convenient flat orientation with the same in-plane flexure direction. A 3MF in the D checkpoint contains geometry only.

## Verification limits

Empty CAD cavities do not receive global slicer infill. Revision D's cavity includes an unsupported region approximately 84 mm across; E1's slightly thicker perimeter does not resolve this manufacturing problem. Internal plates need a validated printing method before the full bracket is released for printing.

Clearance checks use rigid nominal rods and concentric flanges. They exclude wood tolerances, rod sag, spool wobble, screw heads, and deflected fingers. No slicer or physical insertion test has verified the snap features. Main bracket loads, wall fixings, dowel spans, and long-term polymer creep still require analysis and testing.
