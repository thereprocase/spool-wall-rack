# G2 prerequisite: correct the sliced-material model

**In progress. No corrected G stress result or accepted G2 architecture exists
yet.** [G2-BRIEF.md](../../G2-BRIEF.md) defines the broader study and current
material-mapping prerequisite. E13 and G files remain unchanged.

The new [plastic_shape.py](plastic_shape.py) reads actual extrusion paths,
widths, heights and E values. It excludes 0.4 mm bridge paths from structural
material while retaining their full plastic use. The two-wall, five-layer
reference has 77.9203 cm³ spent plastic, including 6.9405 cm³ of thick bridges;
70.9798 cm³ is credited extrusion. The nominal continuous footprint volume
differs from the extrusion accounting and is reported separately.

The five actual Orca cases are two/eight walls crossed with two/eight top and
bottom layers, plus the two-wall, five-layer reference. Base infill is zero;
the original three helpers remain at 100%. The minimum is two walls. A prior
one-wall diagnostic is not the current reference.

![Archived G material-mapping diagnostic](g-slicer-mapping/mapping-sections.png)

The [archived comparison](g-slicer-mapping/comparison.json) checks G's saved h1
finite cells against its original emitted paths. It is diagnostic only.
The new reference's layer-derived material forms one connected structural
component without thick-bridge credit. Surface-to-volume meshing is still
being resolved: a surface simplification produced overlapping facets and
was rejected; the subsequent unsimplified, coordinate-grid representation
passed the surface incidence check but failed volume-boundary recovery.
Neither failure is a strength result.

The raw nominal footprint reference is retained separately from continuum
meshing experiments. Those experiments explicitly report gap closing,
sub-bead void homogenization, coordinate precision and geometric differences.
No approximation has yet passed the full wall/skin validation and mechanical
recheck. Do not equate a manifold surface, a successful slice or a coverage
check with a verified mechanical material model.

## Reproduce the current work

Use the established [analysis environment](../e13/requirements.txt) plus
[the additional dependency](requirements-extra.txt). Native scripts run through
G's unchanged worker. `slice_matrix.py` runs in Orca's installed environment.

```text
python designs/rev-g2/prepare_g_recheck.py --case 2w-5layers
python designs/rev-g2/prepare_g_recheck.py --case 8w-2layers
python designs/rev-g2/prepare_g_recheck.py --case 2w-8layers
python designs/rev-g2/prepare_g_recheck.py --case 2w-2layers
python designs/rev-g2/prepare_g_recheck.py --case 8w-8layers
python designs/rev-g2/slice_matrix.py /path/to/OrcaSlicer
python analysis/rev-g/run_native.py analysis/rev-g2/plastic_shape.py designs/rev-g2/g-recheck/2w-5layers/.work/audit-2w analysis/rev-g2/g-recheck/2w-5layers --solid
python analysis/rev-g/run_native.py analysis/rev-g2/mesh_plastic.py --validate-box --output analysis/rev-g2/validation/box-mesh --h 2
```

The shape tool produces path data, per-layer raw and simplified polygons,
separate spent/credited volume accounting and optional structural STL/mesh.
These are analysis artifacts. Printing uses the original body and modifiers,
with a separately selected and calibrated P1S PETG or ASA process.
