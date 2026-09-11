# GPU replacement for the whole-part tetrahedral meshing route

**Follow-up:** [tested GPU execution checkpoint](GPU-VALIDATION.md) selects
Warp 1.17.0 with verified Apache-2.0 licensing, successful local GPU execution,
independent small 3D fixtures and raw-slice crop patch tests. DTU reuse permission
was not established. Whole-G material fidelity and mechanics remain unresolved.
The research review below preserves the pre-installation findings.

Reviewed September 11, 2026. Both long G fTetWild attempts have been stopped;
their existing inputs and diagnostics are preserved. No replacement solver
has been installed or run on G. The local GPU is an RTX 3080 Ti with 12 GiB.

## Finding and recommendation

Use a voxel/hexahedral or immersed finite-element discretization with a GPU
solver. This avoids recovering a conforming tetrahedral boundary from every
small extrusion facet. It is an established numerical approach, with published
elasticity and engineering comparisons. It still requires explicit geometric
resolution, equilibrium and contact checks; GPU execution does not supply those
checks automatically.

**The closest existing application is Ansys Discovery Explore.** It has an
actual GPU structural solver, contact with separation, and published verification
cases. For a source-based automated pipeline, **DTU's published GPU Cartesian
elasticity implementations are the strongest starting point found**, but they
are topology-optimization research codes and require an application adapter.
Neither recommendation is a claim that G has passed, that its thin material is
resolved on 12 GiB, or that its requested 4x fracture margin is established.

## Existing application: Ansys Discovery Explore

The [current structural capability table](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/discovery/UDA/user_manual/environment/topics/r_stage_diff_structural.html)
includes bearing loads, distributed forces, displacements and sliding contact
in Explore. It explicitly permits separation. The
[contact setup documentation](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/discovery/UDA/user_manual/physics/structural/topics/t_structural_contact_define.html)
distinguishes idealized sliding without separation from contact allowing
separation, and supports retaining an initial gap. The reference wall must use
the latter behavior with zero friction; a frictionless support constrains both
directions of normal movement and is not the same condition.

Ansys publishes [structural verification cases](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/Ansys_3D_VM/Discovery/VM_3D_Design/disco_vm/c_VM_3D_disco_test_cases.html),
including a plate with a hole, a tapered beam, frictionless contact and a fillet
stress concentration. The
[2024 R2 fillet case](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/Ansys_3D_VM/Discovery/VM_3D_Design/disco_vm/topics/r_VM_3D_disco_struct_006.html)
reports 6.5% maximum-shear error in Explore on an 8 GB Quadro RTX4000 versus
1.7% in Refine with local refinement. That is real validation evidence with a
visible accuracy limit, not a promise of those errors for this bracket.

Remaining adoption checks are practical: license/access, import of the credited
material, thin-skin resolution, accessible unsmoothed stress and reaction fields,
repeatable scripting, and the actual wall-gap behavior. Structural local fidelity
and GPU memory limits must be assessed on this geometry. The application is a
credible GPU screening route; full stress acceptance remains conditional on
those checks. Detailed Refine results using Mechanical/MAPDL are a different
solver and cannot be presented as GPU Explore validation.

## Source-based pipeline: DTU GPU Cartesian elasticity

[Traff et al., CMAME 410 (2023), 116043](https://doi.org/10.1016/j.cma.2023.116043)
publish three-dimensional regular-hexahedron elasticity with matrix-free
multigrid-preconditioned conjugate gradients. The paper compares GPU and CPU
implementations and demonstrates more than 50 million elements over 100 design
iterations on an A100. Those are published workload measurements, not a runtime
estimate for the 3080 Ti.

Released implementations:

- [TopOpt-in-OpenMP-GPU](https://github.com/topopt/TopOpt-in-OpenMP-GPU): C/OpenMP
  target offload, matrix-free GPU fine-grid operations and a CPU coarse solve;
  documented NVIDIA compiler/toolchain and A100/V100 tuning.
- [futtop](https://github.com/topopt/futtop): Futhark implementation of the same
  class of 3D Cartesian-grid problem, with its own compilation and solver setup.

These are candidates for reusing an existing elasticity kernel, not ready-made
bracket-analysis programs. Required changes include fixed material input rather
than optimization, arbitrary distributed loads and component-wise restraints,
full stress/reaction export, and the nonzero-gap unilateral wall solve. Their
SIMP/ersatz material treatment must not silently give voids or sacrificial
bridges structural credit. It cannot be called a zero-void-stiffness model
without a separate implementation and verification of that behavior.

## Other reviewed routes

| Route | Relevant evidence | Why it is not the immediate complete replacement |
|---|---|---|
| MFEM with CUDA, hypre and Tribol | Maintained GPU discretization and contact components | The current contact miniapp does not configure a CUDA device/partial assembly; separate capabilities do not prove the combined GPU contact application. A volume discretization is still needed. |
| NVIDIA Warp FEM | GPU FEM, sparse/adaptive grids and elasticity/contact examples | A programmable framework; the required 3D static problem and verification would be new integration work. |
| Voxsol | CUDA image-based elasticity, released source and unit/integration tests | Older CUDA 10.1 build; contact absent from reviewed formulation; published displacement discrepancy versus Abaqus and slow elongated bending cases require attention. |
| gQM3D | Released constrained GPU tetrahedral refinement | Its initial constrained triangulation relies on TetGen, so it retains a problematic front end. |
| gDel3D | Released GPU Delaunay triangulation | Point-set triangulation does not recover the required material boundary/cavities. |
| homo3d / chfem | Published GPU voxel elasticity and memory-efficient kernels | Periodic homogenization is a different boundary-value problem from a loaded bracket with wall contact. |
| VOXELCON | Commercial STL/image-based stress analysis with a GPU option | GPU support for the needed contact and complete finite-cover workflow was not established from the reviewed documentation. |

Sources: [MFEM contact implementation](https://github.com/mfem/mfem/blob/master/miniapps/contact/contact.cpp),
[MFEM solver documentation](https://mfem.org/tutorial/solvers/),
[Warp FEM examples](https://github.com/NVIDIA/warp/tree/main/warp/examples/fem),
[gQM3D implementation](https://github.com/chenzhenghai/GPU_3D_CDT_Refine),
[gDel3D](https://github.com/ashwin/gDel3D),
[homo3d](https://github.com/lavenklau/homo3d),
[chfem](https://github.com/cortezpedro/chfem),
[VOXELCON capabilities](https://www.quint.co.jp/eng/pro/vox/vox_fnc-ana.htm).

[Voxsol's paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0240813)
compares image-derived elasticity against Abaqus and an analytic axial beam.
The reported Abaqus displacement discrepancy levels off near 3.7%; the axial
beam reaches 0.15% at a tighter double-precision tolerance. A 63-million-voxel
bounding grid with about seven million nonvoid voxels took 8.9 minutes on a P100.
The paper notes slower convergence for long bodies under lateral bending.
[Source and tests](https://github.com/c3di/voxsol) are available. These details
make it a useful reference, but insufficient evidence for choosing it over
the multigrid-CG route for the present cantilever-like load path.

A particularly relevant [2024 Siemens research paper](https://doi.org/10.1186/s13362-024-00160-x)
uses GPU immersed voxel elasticity and multigrid, compares mesh convergence
against Simcenter 3D, and reports a bracket with 15 million degrees of freedom
solved in about 1.1 seconds on a 24 GB RTX4090. It is strong evidence for the
method. It is not a publicly released solver found during this review, and its
boundary approximation includes scaled cut cells and weak material in their
empty fractions. Its runtime and geometry policy must not be inherited by G.

## Bounded next experiment

First reproduce an upstream GPU elasticity benchmark and its numerical
reference on the local card. Then test a thin hollow structure and a known
opening/closing wall-contact fixture. Only after those pass should the adapter
consume the already validated credited layer polygons. Measure actual GPU
time and peak memory; retain every finite stress value and independent force,
moment and free-residual checks. Grid spacing must be refined against the raw
layer geometry, not accepted solely because total volume agrees.

The current research establishes the replacement method and credible software
candidates. It does not establish a tested drop-in source package for every G
requirement, or a completed GPU mechanics result.
