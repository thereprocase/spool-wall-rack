# Revision D verification

CAD geometry verified; printability and structural capacity remain unresolved. Geometry was not changed by this audit.

- Rebuilt the source with OpenSCAD. The rebuilt and delivered STL vertex sets match exactly at reader precision.
- Checked 13,308 triangles: all mesh edges have exactly two incident faces. This checks edge closure, not every possible mesh defect.
- STL and 3MF contain 13,308 triangles each, with maximum vertex-set difference 0.000699 mm due to export precision.
- Independently intersected the exported STL at all 120 layer-center heights for 0.2 mm layers. Four full-profile solid plate bands exist at 0–1.2, 7.6–8.8, 15.2–16.4 and 22.8–24 mm. There are three intervening air bands; mounting sleeves locally subdivide the middle air band.
- The envelope is approximately 242.967 x 239.999 x 24 mm. Installed wall leg rises above the arm. The principal gravity bending plane is parallel to the printed plate planes; local bearing, interplate load transfer, buckling and joint behavior still need assessment.
- Independently measured rigid spool clearance from actual STL section segments at diameters 180–220 mm, in 0.025 mm diameter increments. Minimum clearance is 5.512 mm at diameter 180 mm. Nominal straight 25.4 mm rods, 150 mm center spacing, and 0.3 mm saddle settlement assumed. Screw heads, tolerances, rod deflection and flange wobble are excluded.
- The exterior render uses the delivered mesh. The cutaway uses a CAD intersection. The separated plates are an explanatory model that omits perimeter walls and screw details; it is not an exploded assembly of separable parts.

## Manufacturing findings

The cavities are actual empty CAD volumes. A global 15% infill setting will not fill them. Each internal plate begins with unsupported bridging. An actual empty-band section contains an inscribed circle approximately 83.97 mm in diameter near the knee; this establishes a broad unsupported region, not a prediction of a particular slicer's toolpath length. The 6.4 mm air-band dimension is vertical cavity height, not bridge span. No compatible slicer was available in the checked environment, and no G-code or physical print was verified. Do not treat this revision as print-ready.

Three selected perimeters do not establish an exact 1.35 mm printed wall. Extrusion overlap, perimeter generation and treatment of a thin modeled wall determine the actual paths. The model's 1.35 mm wall is a nominal CAD dimension. Prusa documents the distinction here: https://help.prusa3d.com/article/layers-and-perimeters_1748 . Bridging guidance: https://help.prusa3d.com/article/poor-bridging_1802 .

There is no supported material-specific maximum spool count or creep-life rating.
