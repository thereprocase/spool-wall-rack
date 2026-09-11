# Post-G design envelope and material freedom

**Superseded initial draft.** [G2-BRIEF.md](../../G2-BRIEF.md) permits changes
to rail and fixing positions and uses a spool-relative compactness condition.
The fixed interfaces and local E13 underside floor below are a reference
illustration, not the mandatory G2 design domain.

The next search may change the structural body throughout this envelope.
**No existing solid region, wall, skin, rib, internal plane or window is
mandatory. Any number and shape of 100% infill helpers may redistribute
dense material.** Functional performance remains an acceptance requirement.

![Allowable design space and underside limit](design-envelope.png)

| Boundary | Limit |
|---|---|
| Extra downward extension | **8 mm below the current underside at each X** |
| Absolute lowest point | **Y = −51 mm**, relative to the rear rail center |
| Projection from wall | X = 0–215 mm |
| Upper extent | Y ≤ 180 mm |
| Printed width | Z = 0–24 mm |
| Seated spool exclusion | 180–220 mm flanges, at least 3.5 mm nominal clearance |

The underside cap follows the reference's lower silhouette with an 8 mm
offset. It therefore limits local hanging depth along the arm, rather than
allowing the whole arm to extend to the deepest central level. Beyond the
old forward tip, its final lower-limit height continues to X = 215 mm.
The body need not follow or touch this boundary. The old 12.67 mm added-depth
cap and exact-exterior preservation rule are superseded for the next search.

## Material and density freedom

Material may be removed anywhere or added anywhere inside the admissible
volume. Outer contours, chamfers, fillets, wall counts, skins, plates, ribs,
windows and sparse density are variables. There are no frozen solid islands
and no inherited full-plane architecture.

Helpers have no fixed count, shape or placement. They may overlap, include
disconnected regions or extend into air for selection. Their effective dense
region is **the union of all helpers intersected with the printable body**.
Overlaps count once. Helpers are modifiers, never extra printed parts; their
air-only portions must produce no extrusion. Actual Orca paths determine mass
and whether the intended density distribution is produced.

## Functional requirements

Keep the rail centers at (90, 0) and (190, 12) mm; nominal 25.4 mm rod fit,
13 mm seat radius and positive retention remain targets. Retainers may change,
but fit, capture, insertion force, strain and fatigue then need fresh checks.

Keep fixing axes at (Y, Z) = (164, 12) and (40, 12) mm, nominal 5.2 mm screw
clearance, 13 mm washer support at X = 3.6 mm and 15.8 mm driver access from
X = 3.61 mm. Wall contact must be coplanar at X = 0 and support the solved
load path; the former full-height strip is not mandatory. These are functional
targets, not exact retained volumes. Material behind or around an interface
may change if it still passes the relevant checks.

The 5 mm total movement limit, 1 mm change per 1.25 kg spool, requested 4×
fracture factor, stability and printability requirements remain. Sparse infill
has zero structural credit until a validated model supports otherwise.

## Machine-readable contract and scope

[Definition](definition.json) · [XY domain geometry](design-domain.geojson)
· [Construction and spatial probes](verification.json) · [Builder](build_envelope.py).

The flange exclusion covers continuous effective rail radii 12.4–12.7 mm.
A conservative 0.14 mm sampling guard covers intermediate spool diameters;
circumscribed circle polygons avoid underestimating exclusion. This remains
a seated nominal-clearance model, not insertion or loaded-contact validation.

The spatial checker verifies the envelope and explicit positive/negative
geometry probes. Screw/driver voids and washer support require separate 3D
checks; they are not represented as holes in the side-view illustration.
No new bracket has been optimized or qualified. The published G optimizer
and results remain an immutable prior study; the next implementation must
consume this expanded contract and support arbitrary helper collections.

From the repository root, using the existing pinned environment:

```text
python analysis/rev-g/run_native.py designs/design-envelope/build_envelope.py
```
