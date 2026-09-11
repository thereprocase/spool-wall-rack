# Slicer material reconstruction and meshing evidence

The G correction uses emitted Orca paths. It does not inherit the old manually
cut core. The plastic ledger integrates extrusion E; the structural geometry
unions the credited paths' declared width and height. These are different
quantities: nominal footprint union includes a continuum approximation of
bead contact and porosity. The difference is measured, not silently erased.
Thick sacrificial bridges contribute only to the plastic ledger.

## Relevant prior work

- [Rivet et al., G-code-driven material-extrusion mechanics (2023)](https://cervera.rmee.upc.edu/papers/2023-ADDMAN-Gcode_driven.pdf)
  builds a layerwise FE representation from manufacturing paths and distinguishes
  print-pattern material properties. It supports using manufacturing geometry
  and a stated continuum model. Its statistical optimization criterion is not
  adopted here: G2 retains every finite stress cell and reports raw peaks.
- [OrcaSlicer 2.4.2 vertical-shell implementation](https://github.com/OrcaSlicer/OrcaSlicer/blob/v2.4.2/src/libslic3r/PrintObject.cpp)
  projects classified top/bottom regions through neighboring layers. A simple
  rectangular core subtraction does not reproduce that operation on sloping
  geometry. Reading the emitted paths avoids maintaining a second slicer.
- [Gmsh's closed-STL topology example](https://onelab.info/pipermail/gmsh/2019/013378.html)
  provides an alternative topology-building route when surface classification
  fails. It is a diagnostic lead, not proof that this input will mesh.
- [TetGen's manual](https://www.wias-berlin.de/software/tetgen/files/tetgen-manual.pdf)
  distinguishes boundary recovery, hole deletion and quality refinement. Hole
  seeds must lie within their intended cavities. G2 derives seeds from connected
  air regions at layer midplanes and cross-checks the enclosed shell count.
- [pytetwild 0.4.2 documentation and provenance](https://pypi.org/project/pytetwild/0.4.2/)
  describes the available fTetWild wrapper and its surface-envelope parameter.
  `epsilon` is relative to bounding-box diagonal; the G2 wrapper converts the
  requested absolute millimetres explicitly. Its output still requires a
  separate material, topology and quality audit.

## Recorded G attempts

| Method | Outcome | Interpretation |
|---|---|---|
| Manifold surface simplification | Overlapping facets found by Gmsh | Rejected geometry preprocessing |
| Unsimplified layer union, Gmsh Delaunay/HXT | Boundary recovery failed | No mechanics result |
| Gmsh classified surface remeshing | Repeated partition failure on a two-triangle patch | Worker stopped; no result |
| TetGen with quality refinement | Boundary recovered; `split_segment` failed during refinement | No accepted mesh |
| TetGen boundary-only run | Volume and cavity occupancy matched; poor cells and nonmanifold boundary edges remained after numerical-degeneracy audit | Diagnostic mesh, unsuitable for stress acceptance |
| Gmsh/Netgen optimization of raw TetGen mesh | Access violation during optimization; no output | Rejected repair attempt |
| fTetWild hollow box | Enclosed void retained; volume error about 0.0002% | Small-fixture check only |
| fTetWild G material | Both long CPU jobs stopped without a returned mesh | No stress result; GPU voxel/immersed FEM investigation supersedes this route |

The reference continuum experiment uses a 0.03 mm closing radius, 0.16 mm²
maximum homogenized planar pore area, 0.02 mm XY simplification and 0.01 mm
coordinate grid. The untouched nominal footprints remain available for every
layer. Its integrated symmetric difference from them is 206.314 mm³, about
0.287% of the nominal footprint volume. The FEM solid is 71,949.034 mm³;
credited E volume is 70,979.802 mm³. These values are not interchangeable.

The boundary-only TetGen run preserved 39 enclosed voids and one material
component. Its tetrahedral volume matched the layer continuum to numerical
precision. The independent audit nevertheless rejected its boundary topology
and recorded poor element quality. Successful volume accounting is not enough
to justify a stress solve.

A raw-versus-cleaned repeat found no nonmanifold boundary edges before removing
268 numerically collapsed tetrahedra. All 67 resulting incidence-four edges
adjoin removed cells. The two-way surface audit also finds new internal boundary
faces: 54 of 655,224 mesh-boundary samples lie beyond the 0.03 mm envelope,
with a maximum distance of 0.4 mm from the intended surface. Reference-to-mesh
samples match to numerical precision. These are additional reasons to reject
the cleaned mesh for mechanics; its nearly exact total volume is insufficient.
[Distance report](validation/surface-audit-tetgen-boundary-only.json).

New meshing attempts archive their native result before cleanup and retain
failed-volume outputs for diagnosis. Each attempt has its own directory for
native debug files. The independent audit checks finite cells, orientation,
one material component, closed boundary topology, volume and sampled occupancy.
Surface distance and element quality remain separate checks.

The actual unilateral-contact routine now passes analytic spring fixtures for
initially open, closing, touching and releasing contact. Elastic assembly and
stress recovery pass an affine tetrahedron fixture and rigid-motion checks.
[Numerical fixture report](validation/mechanics-fixtures.json). These checks
do not replace the G mesh solve or physical qualification.

Dependencies are isolated from the established CAD environment. The meshing
wrapper needs writable contiguous arrays; Manifold may return read-only views.
The small-fixture failure caused by that array contract was fixed by copying
the inputs, without altering their coordinates or connectivity.
