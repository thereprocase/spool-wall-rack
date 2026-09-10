# E12 structural analysis and reproduction

[Solved results](RESULTS.md) · [E10/E11/E12 comparison](COMPARISON.md) ·
[Current print guide](../../README.md).

E12 limits the added underside depth to **9.5 mm**, meeting the quarter-depth
target and the 12.67 mm maximum. That cap supersedes E11's adjacent-section
margin requirement. Preserve the fingers, R6 rigid shoulders, mirrored 50°
chamfers, hardware and four continuous 1.2 mm plates.

## Models

- **Matched reduced model:** actual 120-layer finished STL outlines, ideal
  contour walls and plates, plane stress and projected fixing/contact conditions.
  E10/E11 solved fields are retained in `analysis/e11`; five E12 fields are new.
  The stress comparison window is fixed at X=75–110, Y=−24–0 mm.
- **Whole-bracket 3D:** finished E12 STEP, analysis-only sparse core removal,
  ideal 8/10-wall contours, four plates and retained tunnel surrounds. This is
  not a resolved bead, orthotropic, rod-contact or damage simulation.
- **Loads/restraints:** 12 kg equivalent / 117.72 N per bracket; rear/front
  seats receive 75.12/42.60 N downward and 31.29 N outward each. Compression-only
  wall contact, rigid washer axial and shank shear restraints; no clamp friction
  or arbitrary tightening preload. Reference E=1000 MPa, nu=0.35.
- **Landing:** the actual upper 3.6 mm land, flat rear support and a separate
  500 N nominal washer load. Two meshes assess this submodel's sensitivity.

## Numerical controls

All six published 3D fields pass independent free residual, force and moment
balance gates below 1e-6. The reduced solver has independent affine/beam checks;
the 3D affine stress/energy test includes PARDISO versus SuperLU.

All four global meshes use the audited same-domain face cleanup. CAD volume
changes remain below 0.001 mm3. Only numerically zero-volume cells may be
removed: normalized determinant below 1e-12, total removed volume below 1e-8 mm3.
Finite cells remain, including those producing raw stress peaks.

The initial 10-wall h3 HXT field failed the residual gate at 2.19e-4. A surface
algorithm 5 retry failed during mesh generation. Neither was accepted. The
published 10-wall pair is h2.5/h2 with surface algorithm 6 and Delaunay 3D, on
the unchanged cleaned analysis domain. The 8-wall pair is h3/h2. Raw peaks,
mesh sensitivities and rejected attempts are recorded in the results.

## Reproduce

Use Python 3.12 and `requirements.txt`; `environment.json` records the actual
versions and platform notes. Gmsh needs its system graphics libraries.
PARDISO/MKL is used for the published direct solves. Build the
[E12 CAD and geometry checks](../../designs/closed-wall-e12/README.md) first.
From this directory:

```sh
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=8
python verify_solver.py
python verify_solver3d.py
python solve_comparison.py e12 8 2
python solve_comparison.py e12 8 1
python solve_comparison.py e12 10 2
python solve_comparison.py e12 10 1
python solve_comparison.py e12 8 1 outer_only
python build_analysis_geometry.py 8 10
python clean_analysis.py
python mesh_model.py print-material 8 3 1 --clean
python solve3d.py print-material-8w-h3 --pardiso
python mesh_model.py print-material 8 2 1 --clean
python solve3d.py print-material-8w-h2 --pardiso
python mesh_model.py print-material 10 2.5 1 --clean
python solve3d.py print-material-10w-h2.5 --pardiso
python mesh_model.py print-material 10 2 1 --clean
python solve3d.py print-material-10w-h2 --pardiso
python mesh_model.py landing 8 1 1
python solve3d.py landing-8w-h1 --pardiso
python mesh_model.py landing 8 0.65 1
python solve3d.py landing-8w-h0.65 --pardiso
python report.py
python render_fields.py
python verify_release.py
```

In PowerShell set the environment variables with `$env:NAME='value'`. Algorithm
1 is Delaunay 3D; the mesher can retry failed boundary recovery with HXT.
Published global runs used Delaunay. Coarse or 8-wall contact can initialize a
new contact solve, but the final state must independently converge. PARDISO
steps are stored as -2 in `linear_iterations`.

Saved `*-solution.npz` files contain coordinates, connectivity, displacement,
element stress, material volume and contact data. Figures use these actual
fields; section views intersect the solved tetrahedra. The 6 MPa display cap
does not discard raw values. Geometry caches, BREP domains and base meshes
regenerate locally and are not printable deliverables.

`verify_release.py` checks the 11 new fields against their result files,
source hashes, material calculations, depth/section/toolpath gates and relative
Markdown links. It verifies the artifact manifest, including the archived
comparison inputs. After deliberately regenerating changed outputs, `--write`
records a new manifest. Earlier manifests apply to their original revision
checkout, since the root guide and project instructions evolve.

## Interpretation

Mesh refinement is numerical sensitivity, not proof of asymptotic convergence
or actual printed behavior. Neither percentiles nor raw peaks are allowables.
Linear 24 kg scaling and common-compliance creep scaling require an unchanged
load pattern and contact state. The grade-specific room-temperature moduli,
short-time PETG example and assumed thermal/long-time tails remain separate.

No physical print, rod fit, snap-force test, hot-load trial or long-term
creep-rupture qualification is claimed. The current criteria remain 5 mm total
loaded movement and 1 mm change per full spool, including dowels and mounts.
