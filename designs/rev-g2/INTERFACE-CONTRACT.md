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
| Matching bottom corner | Preserve G's lower wall corner at X=0, Y=-32 mm. The printed bracket slides down the wall until this underside touches the top of the closet crown moulding. Rod and mounting heights relative to that datum stay unchanged. |
| Horizontal moulding clearance | Keep the underside at Y=-32 mm for at least 25.4 mm outward from the wall. Moulding projects 19.05 mm; the one-inch design reach includes 6.35 mm extra allowance. No bracket material may descend below that level for X from 0 to 25.4 mm. Beyond it, this moulding imposes no downward limit. |

Installed X points out from the wall, Y is vertical relative to the rear rod,
and Z runs across the bracket and along the rods. The original wall plane is
X=0. Prototype geometry retains nominal 25.4 mm rods and 26 mm seats; measured
rod fit and positive capture still need physical verification.

The old local E13 underside floor and its 8 mm offset are not imposed as a
mandatory silhouette. The old 215 mm projection and 24 mm width are reference
dimensions. The earlier 15 mm estimate is replaced by the one-inch reach from
the wall along the bottom edge. It is not measured from the front rod or outer
tip. The moulding locates the bracket; no structural support from the moulding
is assumed in analysis. The exact nominal geometry is recorded in
`shape-seeds/moulding-clearance.json`.

Manufacturing and mechanical requirements in [G2-BRIEF](../../G2-BRIEF.md)
remain: P1S/0.4 mm, PETG or ASA, at least two walls, 0% base infill, 100%
helper regions, realistic hardware/contact and the stated load/movement gates.
Sacrificial bridges receive no structural or bond credit. All finite stress
samples and raw peaks survive. These requirements do not freeze material islands.

E plus F is the selected next implementation: E's deeper frame with F-derived
backing around the seat roots. A remains a comparison direction and D a visually
distinct exploratory alternative. This is design intent, not a solved ranking.

[Six initial body sketches](shape-seeds/README.md) are reproducible XY concepts,
not STEP handoffs or mechanically ranked candidates. Broader architectures need
fresh actual slicing and representative 3D feedback before trusting a reduced
model beyond the small G helper changes already checked.
