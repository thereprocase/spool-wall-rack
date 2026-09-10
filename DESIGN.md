# Design decisions

## Closed-wall load path

The wall mounting leg extends upward. Four continuous planes span the arm, knee and wall leg: two exterior faces and two internal plates. Hollow bands force these internal planes into the modeled solid. They lie in printer XY. The principal installed bending load acts in those planes; local bearing, load transfer between planes and buckling still need evaluation.

## Structural thickness

E1 proposes a 2.4 mm perimeter around the L profile while retaining 1.2 mm side faces and internal plates. This is a prototype choice, not an optimized thickness or load rating. The arm's upper and lower perimeter bands lie far from its bending neutral axis, so thickening them is useful. External and internal side planes also carry in-plane stress; do not describe all material as equally effective or infer proportional strength gains from perimeter thickness.

A modeled 2.4 mm wall does not guarantee a particular number of extrusion paths. The original three-wall setting must be revised or verified for E1. The snap fingers remain 1.35 mm in bending thickness. Their stiffness and strain requirements differ from those of the structural perimeter.

## Rotated snap seats

The reference geometry uses a 200 mm spool on 25.4 mm rods with 150 mm seat-center spacing. With 0.3 mm radial seat clearance, the rear contact direction is 48.144° from +X; the rigid bearing sector is centered at 228.144°. The front is mirrored. A 218° curved retainer leaves a 142° opening toward the spool. Rounded noses form an approximately 24.51 mm throat. This gives about 0.89 mm nominal diametral interference, shared between the fingers in a symmetric insertion idealization.

The lower/outside bearing sector is 5 mm thick radially. Local relief pockets free the curved fingers from the bracket body. Finger deflection stays in the print layer plane. The ideal seated rod relaxes into the saddle; the design avoids relying on sustained finger clamping.

The 8 mm coupon is a preliminary fit sample. At equal profile geometry, its width is one-third that of the full bracket, so it cannot establish the full part's insertion force. Curved-beam strain, root concentrations, release behavior, overtravel and actual filament behavior have not been validated.

For circular rigid contact, the dowel also receives outward thrust. Over the original 180–220 mm range that component is of similar magnitude to vertical load. Preserve the solid seat-to-arm path; do not route the main bearing load through thin fingers.

## Next work

1. Verify coupon fit against measured dowel diameter and ovality; analyze curved-finger insertion/release and tolerance extremes.
2. Resolve internal roof printing while retaining continuous load-plane plates. Any printing scaffold gets zero structural credit.
3. Inspect slicer paths with explicit line widths, plate thicknesses and printer profile.
4. Evaluate bracket, mounting fasteners and dowel spans together; derive material-specific creep-aware loads from defensible data and tests.

## References

- [Covestro snap-fit design guide](https://solutions.covestro.com/-/media/covestro/solution-center/brands/downloads/imported/1557218421.pdf): snap geometry and stress-free seated design principles. Molded-resin values are not printed-material allowables.
- [Prusa layers and perimeters](https://help.prusa3d.com/article/layers-and-perimeters_1748): extrusion overlap and solid layer behavior.
- [Prusa bridging guidance](https://help.prusa3d.com/article/poor-bridging_1802): unsupported extrusion and bridge quality.
