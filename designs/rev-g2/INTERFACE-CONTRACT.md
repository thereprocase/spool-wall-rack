# G2 current interface contract

The body outline is a design variable. The completed G helper pilot validated
the local screening workflow; its frozen body is not a constraint on this study.
Start with substantially different structural families, then mutate dimensions
within each family by 5–10%. Body depth, width, outer contour, braces, windows,
wall footprint, skin arrangement and helper count/shape may change.

The latest interface requirements supersede the older permission to relocate
rods and mounting holes:

| Interface | Current requirement |
|---|---|
| Rear and front rod axes | Keep `(X,Y) = (90,0)` and `(190,12)` mm; axes run along Z. |
| Mounting holes | Keep axes at `(Y,Z) = (164,12)` and `(40,12)` mm. Preserve the reference 5.2 mm screw clearance and functional washer/driver access. |
| Spool clearance | Preserve axial flange sliding for 180–220 mm spools, with at least 3.5 mm nominal clearance over the effective rail-radius interval 12.4–12.7 mm. |
| Matching bottom corner | Required. The exact corner/datum remains to be identified before finalizing new body dimensions. |
| 15 mm outboard | Required. The measurement origin remains to be identified before finalizing new body dimensions. |

Installed X points out from the wall, Y is vertical relative to the rear rod,
and Z runs across the bracket and along the rods. The original wall plane is
X=0. Prototype geometry retains nominal 25.4 mm rods and 26 mm seats; measured
rod fit and positive capture still need physical verification.

The old local E13 underside floor and its 8 mm offset are not imposed as a
mandatory silhouette. The old 215 mm projection and 24 mm width are reference
dimensions, not substitutes for the pending 15 mm datum. Sketches may explore
depth and width while those anchors are clarified; they must carry a provisional
dimension label and cannot pass a completed envelope check yet.

Manufacturing and mechanical requirements in [G2-BRIEF](../../G2-BRIEF.md)
remain: P1S/0.4 mm, PETG or ASA, at least two walls, 0% base infill, 100%
helper regions, realistic hardware/contact and the stated load/movement gates.
Sacrificial bridges receive no structural or bond credit. All finite stress
samples and raw peaks survive. These requirements do not freeze material islands.

[Six initial body sketches](shape-seeds/README.md) are reproducible XY concepts,
not STEP handoffs or mechanically ranked candidates. Broader architectures need
fresh actual slicing and representative 3D feedback before trusting a reduced
model beyond the small G helper changes already checked.
