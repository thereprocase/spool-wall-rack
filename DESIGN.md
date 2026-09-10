# Design decisions

## Closed-wall load path

The wall mounting leg extends upward. Four continuous planes span the arm, knee and wall leg: two exterior faces and two internal plates. Hollow bands force these internal planes into the modeled solid. They lie in printer XY. The principal installed bending load acts in those planes; local bearing, load transfer between planes and buckling still need evaluation.

## Structural thickness

E6 retains a 2.4 mm perimeter around the L profile while retaining 1.2 mm side faces and internal plates. This is a prototype choice, not an optimized thickness or load rating. The arm's upper and lower perimeter bands lie far from its bending neutral axis, so thickening them is useful. External and internal side planes also carry in-plane stress; do not describe all material as equally effective or infer proportional strength gains from perimeter thickness.

A modeled 2.4 mm wall does not guarantee a particular number of extrusion paths. The original three-wall setting must be revised or verified for the 2.4 mm perimeter. The snap fingers remain 1.35 mm in bending thickness. Their stiffness and strain requirements differ from those of the structural perimeter.

## Rotated snap seats

The current E6 geometry uses a 200 mm spool on 25.4 mm rods with 100 mm seat-center spacing. With 0.3 mm radial seat clearance, the rear contact direction is 63.587° from +X; the rigid bearing sector is centered at 243.587°. The front is mirrored. A 218° curved retainer leaves a 142° opening toward the spool. Rounded noses form an approximately 24.51 mm throat, giving about 0.89 mm nominal diametral interference. E1–E5 used 150 mm seat spacing.

The lower/outside bearing sector is 6 mm thick radially. Local relief pockets free the curved fingers from the bracket body. Finger deflection stays in the print layer plane. The ideal seated rod relaxes into the saddle; the design avoids relying on sustained finger clamping.

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

## E2 root correction

Removed the stepped annular root and intersecting circular bumps. The finger outer boundary now uses a quintic radial transition with zero first and second derivative at its joins to the thin finger and thick bearing sector. This gives tangent and curvature continuity in the analytic profile. The model discretizes that curve at 0.25-degree intervals.

The complete bracket profile receives R1.5 concave blends and R0.45 convex rounds. A 17.75 mm relief-pocket radius leaves clearance around the finger while a 6 mm radial bearing sector maintains attachment to the bracket. The coupon base also has rounded corners and blended connections. These changes remove the previous sharp re-entrant roots; they do not establish zero local stress concentration or a safe snap strain.

The larger roots shorten/change the effective flexible length relative to E1. Validate the curved finger as modeled, rather than reusing the earlier straight-cantilever screening example.

## E3 obsolete saddle removal

The old open-saddle lip sectors and round support nodes remained in the base profile after snap retainers were added. They produced an unnecessary secondary prong beneath the working finger. Removed those old features at both rail locations. A new buttress joins a patch of the rigid bearing sector to a rounded anchor inside the arm. It does not use the old lip as a stop or load-bearing feature.

The complete profile retains the concave and convex blends established in E2. The local retainer coupon is unchanged; the integrated support geometry is different and still requires its own compliance and insertion checks.

## E4 angular outline and smoothly terminating face bevels

The large outline uses straight facets with nominal R2 corner blends. Both broad faces have mirrored 3 mm chamfers on selected structural edges. Their depth falls to zero over 20 mm before small features. The quintic Bezier control values 3, 3, 3, 0, 0, 0 ensure zero slope and curvature at each end; the thin snap noses retain their smaller local rounds. The integrated concave root blends are R2.

The final solid is built from the OpenSCAD profile by `finish_cad.py`. A raw SCAD bracket export omits the finished bevels and their matching internal rim reinforcement. The cavity keepout lies 1.8 mm beyond the bevel in the sum of inward distance and face depth. Including the maximum runout gradient of 0.28125, its normal spacing exceeds 1.2 mm. This retains a conservative solid ligament behind the bevel; it is a geometric design rule, not a load allowable. The middle hollow band and both 1.2 mm internal load-plane plates remain continuous.

The finished CAD passes single-solid validity and STL edge closure. Full-profile nominal clearance is 5.34 mm for 180–220 mm spool flanges. Internal bridge spans, toolpaths, fasteners, snap force, fatigue and creep remain unvalidated.

## E5/E6 vertical efficiency

E5 explored simply raising the arm underside while keeping the old rail spacing. Its 18 mm-deep arm had only 18% of the old midpoint section inertia; it was not selected as an equivalent structural replacement.

E6 moves the seats to X=90 and 190 mm, keeping a roughly 28 mm-deep arm between them. The back is flat at X=0 from Y=−32 to +176 mm. The upper fixing moves to Y=164 mm and the lower remains at Y=12 mm. The central 18 mm of the back width reaches both ends of that height after broad-face chamfering; screw holes interrupt its bearing area. A full-height plane is a fit condition, not a claim of full or uniform contact pressure under load.

For 180/200/220 mm flanges, the bracket extends 31.4/32.7/33.7 mm below the spool and never extends above its top. Loaded rack envelopes are 211.4/232.7/253.7 mm before adding handling space. The 200 mm case saves 40.1 mm over E4. The single bracket occupies approximately 206.73 × 208 × 24 mm on the bed.

The section-property script reads final STEP solids. Its midpoint `I/L³` comparison suggests that the shorter forearm can recover the stiffness lost through reduced depth, but it does not model the complete bracket. The idealized bolt-force screen assumes equal rail loading, a point wall-compression reaction and one upper tension fixing. Neither calculation provides a spool rating.

The 100 mm rail spacing reduces the ideal rise needed to rock the spool over one rod to about 12 mm, from 29 mm in E4. This is the main handling compromise; the rail snap does not restrain the spool. Check bumps, off-center loading and sliding with real spools. The closed-wall internal printing issue remains unresolved. The separate open-web path is unchanged.
