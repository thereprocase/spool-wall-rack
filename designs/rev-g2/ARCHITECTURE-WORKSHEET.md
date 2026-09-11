# G2 architecture family worksheet (provisional)

This is a preparatory architecture screen for G2. It does not select a family,
change E13 or Rev G, or claim mass, strength, movement, fit, or print tests.
The corrected Rev G material mapping and mechanical recheck are prerequisites
for ranking these families.

The common target is a single printable bracket for a Bambu P1S with a 0.4 mm
nozzle, PETG or ASA, and at least two walls. The bracket must accept nominal
one-inch dowels and 180–220 mm spools, positively retain the dowels, and let the
spool flanges slide along the dowels across the bracket positions. Dowel capture
must provide a feasible insertion and removal path without sustained clamping.
Rail centers and capture geometry are
design variables; measured dowel diameter/ovality and printed-coupon results
are fit inputs and acceptance checks, not assumed design values. The reference load is
12 kg / 117.72 N per bracket; 5 mm total loaded movement reserves 1 mm for
rails and mounts pending their own model or measurements, leaving a provisional
4 mm bracket allocation. The 1.25 kg spool movement-change limit is a separate
load/contact check. The 85 °F sustained and brief 100 °F conditions, effective
E = 1,000 MPa planning model, and requested nominal fracture factor of four are
screening assumptions, not lifetime or material allowables.

## Common parameter and audit vocabulary

Installed `X` points outward from the wall, `Y` is vertical, and `Z` runs along
the dowels and across the 24 mm bracket thickness (also the print-build
direction). The existing Rev G functional reference places the rear and front
seat centers near `(X,Y) = (90,0)` and `(190,12)`, with wall fixing lands near
`Y = 40` and `164`; these are starting coordinates only. A spool flange slides
along `Z`; the dowels are retained positively at the seats. Each family should
expose rail center spacing, seat radius, capture geometry, wall fixing land
size, web/rib width, wall-loop count, skin thickness, and helper regions as
parameters, while taking measured dowel dimensions only as fit-validation
inputs.

Every coarse model should represent the body as a union of finite 2D section
regions lofted or extruded through Z, with actual body intersections at each
0.2 mm layer. Wall and skin domains come from the corrected Orca-derived
material map; sparse base infill receives zero structural credit. Dense helper
regions are clipped to the body and counted once. Sacrificial 0.4 mm bridges
count as spent plastic but receive zero stiffness, strength, and bonded-connection credit.
Each candidate needs the same 3D equilibrium, force/moment, contact, movement,
mesh-refinement, retained-cell, buckling, and process-envelope gates.

## Family matrix

| Family | Primary load path | Main controllable variables | Main early risk | Coarse representation |
|---|---|---|---|---|
| A. Continuous wall with two full load plates | Both seats feed through continuous broad faces and internal plates parallel to installed XY, tied into the wall across Z; short diagonal chords close the seat load loops. | Plate count and thickness, wall loops, seat-band width, diagonal width, rail spacing/elevation, window size. | Printed solid volume and skin-to-wall transition may remain high; broad chamfers need continuous backing. | Body section intersections plus full XY plate regions at selected Z bands and seat collars; no sparse-core surrogate. |
| B. Open triangular web frame | Seat reactions travel through diagonal tension/compression webs in the installed XY plane to separated wall lands, leaving large low-load windows. | Web angle, web width, node radius, number of diagonals, wall gusset length, rail spacing. | Acute nodes can create thin Arachne beads, bridges, or stress concentrations; the spool flange slide corridor must remain open along Z. | 2D buffered centerlines with explicit rounded node solids, extruded through the 24 mm Z width; inspect each junction. |
| C. Local closed-section seat arm | Each seat uses a short closed rectangular or C-shaped section in the local X/Y wall-to-seat direction; its flanges wrap the seat root and return to the wall. This remains an isolated 24 mm bracket concept, not a spine extending along the rack. | Section depth/height, flange thickness, arm length, seat collar depth, window placement, capture feature. | Internal cavities need printable sloping roofs and end closures; unsupported spans or trapped support may defeat one-piece printing. | Offset X/Y section polygons for each local arm, capped cavities, and explicit seat-to-wall contact bands; no hidden infill credit. |
| D. Two-arm portal across local Z | Each arm has its own wall-root bending path; a brace across the bracket’s 24 mm Z width couples the two faces and limits local differential twist. | Arm depth, Z-brace width, brace-to-arm blend radius, rail spacing, wall-land separation. | A cross-width brace or portal can interfere with spool flange insertion along Z or driver access; test the full 180–220 mm sweep. | Two X/Y arm solids plus a finite Z-spanning brace and rounded wall-root gussets; apply separate seat loads and a torsional differential case. |
| E. Drop cradle using the lower 8 mm allowance | A lower cradle under the inner seat provides a deeper triangular moment arm, with a guided seat and positive dowel capture. | Additional downward allowance (0–8 mm), cradle depth, lower web angle, capture height, seat radius, rail elevation. | Added projection can enter the spool envelope; low roofs need a path audit. | Triangular cradle and upper guide extruded through Z; sweep dowels through installation and spool flanges through axial sliding. |
| F. Thick-seat portal without the thin forearm transition | A thick portal surrounds each seat and connects directly to the wall through rigid shoulders, avoiding dependence on the thin forearm chamfer/inner-seat transition. | Portal thickness, shoulder length, seat surround angle, rail spacing, opening width, capture feature. | More material around the seats and a larger silhouette; portal openings must not pinch the spool flange or remove driver access. | Rounded annular seat regions joined to wall shoulders, with the forearm/chamfer transition omitted from the primary path; compare to the same external envelope. |
| G. Layered shear-box with guided capture | Continuous wall roots feed a shallow shear box across Z; cheeks guide and positively retain the dowels while preserving spool sliding. | Cheek spacing, box depth, insertion slot angle, capture geometry, plate thickness, access openings. | Roofs need a path audit; fixed capture needs a feasible dowel installation path and clearance after installation. | Separated XY face sections, dowel-groove subtraction, guided entry, and explicit cheek/plate intersections; model dowel contact and spool sliding separately. |

## Family notes and screening questions

### A — continuous wall with two full load plates

This is the conservative reference architecture for interpreting the corrected
G result. The broad faces and internal plates parallel to installed XY should
remain continuous through both seat regions and terminate in broad wall bearing
and fixing lands across the 24 mm Z width. Windows may remove material between
the plates, but they must leave a direct path around every seat root. Dowel
retention must preserve spool sliding: any ramp, cheek, or stop must have a
verified dowel insertion path and leave the spool flange sliding corridor open.
Screen plate-to-wall shear, seat-root bending, and chamfer backing separately.

### B — open triangular web frame

This family trades plate area for explicit diagonals. Each web should have a
rounded start and finish and a width comfortably representable by two process
walls or a dense modifier. Webs should meet the wall at separated Y lands so
the load is not concentrated in one thin corner. The spool flange sweep along Z
must be checked against every diagonal, including the 220 mm maximum case.

### C — local closed-section seat arm

The local closed section is intended to resist twisting caused by unequal dowel
contact and seat loading without introducing a rack-length spine. Its cavity
must be shaped as printable sloping roofs or open windows; a nominal box that
relies on unsupported horizontal closure is not a valid one-piece candidate.
The seat arm should blend into the wall over a finite X/Y length, with no abrupt
thin shell termination.

### D — two-arm portal across local Z

The cross-width brace makes differential seat movement an explicit load case
rather than relying on one wall face alone. It must leave a feasible dowel
insertion path and a clear spool-flange slide along Z. Both high and low brace
positions need insertion, retention, and driver-access sweeps. If the brace
becomes a separate part, its fasteners, tolerance stack, and failure mode must
be analyzed separately; the initial family assumes it is integrated and
printable.

### E — drop cradle

This is the direct use of the permitted compactness allowance. Start with zero
additional drop and vary downward projection up to 8 mm only where the deeper
moment arm improves the load path. A guided dowel seat and a verified
positive dowel-capture feature should carry retention; the lower
cradle must not act as a spring clip.
Check the lower envelope against the spool, wall, fasteners, and neighboring
brackets before any strength ranking.

### F — thick-seat portal

This family deliberately avoids the thin forearm chamfer/inner-seat transition
dependency required by some slimmer architectures. It should make seat-root
backing visible in sections and preserve a generous rigid shoulder into the
wall. Its candidate capture feature is a cheek or stop only after a feasible
dowel insertion and release path is shown, with clearance after installation.
The larger seat portal is acceptable only if the spool slide envelope and
compactness comparison remain plausible.

### G — layered shear box

The cheeks provide a defined shear path and a candidate positive dowel-retention
interface. The groove and entry slot take measured dowel/rod data as fit inputs
and need printed-coupon results; they are not fixed from nominal diameter. Keep
the dowel-capture feature outside the flange slide corridor and demonstrate a
dowel insertion/release direction. Model the box roofs, cheek ends,
entry slot, and capture feature as actual surfaces for overhang, bridge, and
layer-interface checks.

## Shared interfaces and manufacturing checks

All families retain ordinary wall-fastener access as a requirement, but fixing
centers may move only with a documented wall-contact, washer-bearing, driver,
substrate, and embedment recheck. The wall must not be credited with ideal
capacity without a substrate/contact model. Dowel fits require measured
diameter and ovality distributions as acceptance inputs, not assumed design
values or a substitute for a feasible insertion path. Spool flanges must slide
along Z and must be checked independently from positive dowel retention.

For each family, inspect the actual 0.4 mm toolpaths for minimum wall widths,
thin Arachne transitions, unsupported roofs, bridge lengths, first-layer
contact, continuous seat backing, and capture-stop formation. Use the same
orientation and bed-exclusion audit as the G recheck. A multipart concept must
also carry assembly alignment, fastener, tolerance, and part-separation cases.

The next concrete step is to wait for corrected G material/mesh feedback,
choose representatives only after that evidence is available, and build
reproducible coarse models from this matrix. This worksheet intentionally does
not rank or select a family.
