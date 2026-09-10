# E13 refined structural analysis and reproduction

[Results and material cases](RESULTS.md) · [Matched reduced comparison](COMPARISON.md) ·
[Fine-mesh hotspots](HOTSPOTS.md) · [Current guide](../../README.md).

E13 uses 11 mm added underside depth with long straight flanks and a short
flat. The 12.67 mm cap supersedes E11's adjacent-section margin target. Fingers,
R6 rigid shoulders, mirrored 50° bevels, hardware and four plates are retained.

## Models and refinement

- Five new reduced fields integrate the actual 120 finished STL layers with
  ideal contour walls and plates. E10/E12 comparison fields stay in their
  archived packages. The near-seat statistic uses fixed X75–110, Y−24–0 mm.
- Six current global 3D fields use h=2, 1.5 and 1 mm for 8 and 10 walls. Sparse
  core is removed only from the analysis domain. Two new h=1 mm E12 fields
  provide the matched fine-mesh comparison; they use the preserved E12 CAD.
- The actual upper 3.6 mm screw landing has two additional meshes at h=1 and
  0.65 mm with a separate 500 N washer-compression load and flat rear support.
- Global loads are 12 kg equivalent / 117.72 N per bracket: rear/front 75.12/
  42.60 N down and 31.29 N outward each. E=1000 MPa, nu=0.35. Wall contact is
  compression-only; washer axial and shank shear restraints are rigid. No
  friction or tightening preload is credited.

All ten 3D fields pass independent residual, force and moment balance below
1e-6. The reduced solver has separate affine/beam checks; the 3D patch checks
stress and energy and compares PARDISO with SuperLU. Same-domain face cleanup
preserves CAD volume within 0.001 mm3. Only numerically zero-volume cells may
be removed (normalized determinant below 1e-12, total volume below 1e-8 mm3).
All finite stress cells and their raw peaks remain.

## Reproduce

Use Python 3.12 and `requirements.txt`; `environment.json` records the actual
versions. Gmsh needs system graphics libraries; the published direct solves
use PARDISO/MKL. Build [E13 CAD](../../designs/closed-wall-e13/README.md) first.
Build and clean the preserved [E12 analysis domains](../e12/README.md) before
running the fine baseline commands. From this directory:

```sh
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=8
python verify_solver.py
python verify_solver3d.py
python solve_comparison.py
python build_analysis_geometry.py 8 10
python clean_analysis.py
for walls in 8 10; do
  for h in 2 1.5 1; do
    python mesh_model.py print-material "$walls" "$h" 1 --clean
    python solve3d.py "print-material-${walls}w-h${h}" --pardiso
  done
  python mesh_model.py print-material "$walls" 1 1 --clean --baseline-e12
  python solve3d.py "baseline-e12-print-material-${walls}w-h1" --pardiso
done
for h in 1 0.65; do
  python mesh_model.py landing 8 "$h" 1
  python solve3d.py "landing-8w-h${h}" --pardiso
done
python report.py
python audit_hotspots.py
python render_fields.py
python verify_release.py
```

PowerShell uses `$env:NAME='value'` for environment variables and equivalent
`foreach` loops. Mesher algorithm 1 is Delaunay; failed boundary recovery
retries HXT on the same geometry. Each mesh audit records the actual algorithm,
source and CAD-volume agreement. Contact can start from a completed coarser
field, but the final state must independently converge. PARDISO steps are
recorded as -2 in `linear_iterations`.

Saved `*-solution.npz` files contain coordinates, connectivity, displacement,
element stress, material volume and contact data. Figures intersect the actual
tetrahedra; their colour cap does not filter saved values. BREP domains, base
meshes, logs and caches regenerate locally and are not printable deliverables.

`verify_release.py` checks the 15 new fields, source hashes, material scaling,
geometry and toolpath gates, hotspot records and relative links. It verifies
the published artifact manifest, including archived comparison inputs. Use
`--write` only after deliberate regeneration. Earlier manifests apply to
their own revision checkout because root documentation evolves.

## Interpretation

Refinement measures numerical sensitivity, not physical validation. It does
not resolve printed anisotropy, bead bonding, actual rod/washer contact,
insertion force, damage or lifetime creep. Raw peaks are not allowables and
cannot be dismissed solely because their cells are tiny. Region statistics,
raw peaks and last-step changes are all published.

24 kg proof scaling and common-compliance creep scaling assume unchanged
contact and load pattern. Reference room-temperature moduli, a short PETG
creep example and assumed long-time/thermal tails remain distinct. No physical
print, hot-load trial or long-term creep-rupture qualification is claimed.
