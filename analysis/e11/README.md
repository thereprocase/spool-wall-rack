# E11 structural analysis and reproduction

[Solved results](RESULTS.md) · [Matched E10/E11 comparison](COMPARISON.md) ·
[Current print guide](../../README.md).

This is the reinforced inner seat with mirrored 50° chamfers. E9 remains an
earlier geometry/finish baseline. The current print deliverable is the solid
E11 STEP with aligned helpers; analysis BREP files are not printable models.

## Models and checks

- **Reduced 2D comparison:** actual finished E10/E11 layer outlines, 120 layer
  midpoints, ideal contour walls and four 1.2 mm solid bands. The fixing/contact
  conditions are projected into the side plane. Full-load and outer-rod-only
  cases use identical assumptions and a fixed near-seat statistic window.
- **3D global model:** finished E11 exterior and functional openings, with
  analysis-only sparse core removed. Ideal walls, four continuous plates and
  tunnel surrounds receive material credit. Chamfer guard planes shift inward
  by the XY wall thickness; the tunnel-surround idealization is retained from
  the earlier model. This is not a resolved bead/contact/orthotropy simulation.
- **Contact/load:** compression-only wall, rigid washer axial and shank shear
  restraints; no clamp friction or arbitrary preload. At 12 kg equivalent:
  rear/front 75.12/42.60 N downward, 31.29 N outward each. Forces act on bearing
  arcs, not thin snap tips. The reference material is E1000, ν=0.35.
- **Landing submodel:** actual upper 3.6 mm land, 500 N nominal washer load,
  backed by a flat support. Separate coarse/fine meshes assess its sensitivity.
- **Verification:** 2D affine/beam checks, 3D affine stress/energy check and
  cross-solver comparison, independent whole-model residual and force/moment
  balance, CAD/mesh volumes and local/global refinement statistics.

All published 3D fields pass the 1e-6 residual and balance gates. Same-domain
CAD face cleanup is audited in `analysis-topology-cleanup.json`. The published
8-wall fine and 10-wall coarse meshes use the cleaned topology; the other two
use the original valid domain. This merges redundant faces without deliberately
removing material; recorded CAD volume differences are below 0.001 mm³.

Only numerically zero-volume tetrahedra can be removed, using the normalized
determinant floor of 1e-12 and a total removal limit of 1e-8 mm³. Finite cells
remain, including those producing large raw stresses. A failed residual is not
accepted because the solver reports convergence. Rejected cases are summarized
in the results and machine-readable report.

## Reproduce

Use Python 3.12, `requirements.txt`, an OpenCASCADE-capable CadQuery build and
the system graphics libraries required by Gmsh. PARDISO/MKL is used for the
published direct solves; the script also supports AMG-preconditioned CG.
`environment.json` records the package versions used for this revision.

The delivered E11 and retained E10 STLs are sufficient for the comparison and
section audit. Rebuild the [E11 CAD](../../designs/closed-wall-e11/README.md) first
if changing geometry. From this directory:

```sh
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=8
python verify_solver.py
python verify_solver3d.py
python solve_comparison.py
python build_analysis_geometry.py 8 10
python clean_analysis.py
python mesh_model.py print-material 8 3 1
python solve3d.py print-material-8w-h3 --pardiso
python mesh_model.py print-material 8 2 1 --clean
python solve3d.py print-material-8w-h2 --pardiso
python mesh_model.py print-material 10 3 1 --clean
python solve3d.py print-material-10w-h3 --pardiso
python mesh_model.py print-material 10 2 10
python solve3d.py print-material-10w-h2 --pardiso
python mesh_model.py landing 8 1 1
python solve3d.py landing-8w-h1 --pardiso
python mesh_model.py landing 8 0.65 1
python solve3d.py landing-8w-h0.65 --pardiso
python report.py
python render_fields.py
```

In PowerShell set the same variables using `$env:NAME='value'`. Mesh algorithm
1 is Delaunay; 10 is HXT. The mesher can retry a failed Delaunay boundary with
HXT, preserving the source CAD. Valid coarse contact is used as an initial
guess for finer meshes; the final contact state must independently converge.
Direct factorization steps are stored as −2 in `linear_iterations`, with
`linear_solver` identifying PARDISO.

Saved `*-solution.npz` files contain the actual node coordinates, connectivity,
displacements, element stresses and volumes used by the figures. Result JSON
files retain loads, reactions, movements, residuals, contact and regional stress
statistics. Base meshes and analysis BREP files regenerate locally. Layer/core
caches are keyed to their source geometry and are ignored by git.

`report.py` regenerates the matched comparison, material/creep summary and
results document. `render_fields.py` intersects the actual solved tetrahedra
for the plate and transverse sections. A 6 MPa display cap does not discard
raw values. The E8 GitHub Actions workflow remains an archived baseline; the
commands here reproduce E11.

`python verify_release.py` checks the 16 saved fields against their result
files, source CAD hashes, material tables, section/toolpath gates and relative
Markdown links. `release-verification.json` records the handoff's artifact
hashes. After intentionally regenerating changed outputs, use `--write` to
record a new manifest. Text hashes normalize line endings to LF; delivered
STEP and binary files retain their exact bytes.

## Interpretation limits

The four model refinements are numerical sensitivity checks, not proof of
asymptotic convergence or material qualification. No actual print, measured rod
fit, snap insertion/retention, hot-load test or long-term creep-rupture test is
claimed. The isotropic and ideal-restraint assumptions remain explicit.

At 24 kg the elastic fields scale by two only while the load pattern/contact
remain unchanged. Creep scaling similarly assumes a common compliance and
fixed contact. The reference moduli, short-time PETG spectrum and uncalibrated
thermal/long-time sensitivities are separated in `engineering-summary.json`.
