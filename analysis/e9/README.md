# E9 structural analysis

This model uses the current +12 mm front rail, reshaped back arm and finished 2 mm chamfers. [Results](RESULTS.md) and the [main guide](../../README.md) distinguish numerical screening from physical qualification.

The printable STEP remains solid with helper modifiers. `build_analysis_geometry.py` creates separate analysis domains with the sparse core removed, ideal 8/10-wall contour thicknesses, four continuous 1.2 mm plates and reinforced chamfer/tunnel surrounds. Those domains are not print deliverables.

## Reproduce

Install `requirements.txt` in a Python environment with OpenCASCADE support and the system graphics libraries required by Gmsh. First rebuild the [E9 CAD](../../designs/closed-wall-e9/README.md). From this directory:

```sh
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
python build_analysis_geometry.py
python verify_solver.py
python solve2d.py 8 2
python solve2d.py 10 2
python solve2d.py 8 1
python mesh_model.py print-material 8 3
python solve3d.py print-material-8w-h3
python mesh_model.py print-material 10 3
python solve3d.py print-material-10w-h3
python mesh_model.py print-material 8 2
python solve3d.py print-material-8w-h2
python mesh_model.py print-material 10 2
python solve3d.py print-material-10w-h2
python mesh_model.py landing 8 0.65
python solve3d.py landing-8w-h0.65
python report.py
```

The fine models warm-start wall contact from the corresponding converged coarse solution. Gmsh uses Delaunay meshing; element ordering and algebraic multigrid can vary slightly between installations. The existing automated workflow targets the archived E8 baseline.

## Model limits

- Small-strain isotropic elasticity at E = 1,000 MPa, ν = 0.35; grade movement scales inversely with reference modulus.
- Compression-only wall contact, rigid washer axial restraints and rigid screw-shank shear restraints. No mounting friction or arbitrary tightening preload is credited.
- 180 mm spool contact forces, 12 kg equivalent bracket load: rear 75.12 N down, front 42.60 N down, 31.29 N outward at each seat.
- Ideal solid contour walls and plates; sparse infill contributes nothing. Actual sliced bead radii, anisotropy, defects and snap insertion are not resolved.
- Stress percentiles and raw maxima are not material allowables. Refinement, balance and the affine patch check assess the numerical implementation, not lifetime strength.
- Creep correspondence assumes a common compliance and unchanged contact geometry. Long-time tails and thermal shifts are explicit sensitivity assumptions, not calibrated grade forecasts.
