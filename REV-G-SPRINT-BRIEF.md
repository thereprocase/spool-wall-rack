# Next sprint — reproducible evolutionary optimization of Rev F

**Queued, not started.** The September 10 checkpoint freezes the hand-tuned
exploration. Start from its [CAD](designs/rev-f/README.md),
[numerical evidence](analysis/rev-f/README.md) and
[candidate ledger](analysis/rev-f/constrained-screening.json).
No genetic optimizer or optimized winner is included in this checkpoint.

## Objective and hard constraints

Minimize **actual OrcaSlicer plastic volume**, with mass reported at a stated
density, within the serviceability and strength limits. Report stiffness per
gram and the mass/movement Pareto frontier. Matching E13 stiffness is not a
constraint.

- Preserve E13's exterior outline, width, rod seats, flexible fingers, relief
  pockets, screw lands and driver access. Through-windows may change only
  inside that envelope and outside the protected interfaces.
- At the 12 kg / 117.72 N reference load, total movement must be at most 5 mm,
  including bracket creep, rails and mounting movement. Retain the 1.0 GPa
  effective-modulus planning case. Start with an **explicit provisional 1 mm
  reserve for rails/mounts**, so the bracket screen is 4 mm; replace that reserve
  with rail/mount evidence before qualification. Also evaluate reserve sensitivity.
- Adding/removing a 1.25 kg full spool must change total movement by at most
  1 mm. Proportional scaling of the full-load solution is a preliminary screen;
  re-solve the load/contact changes for finalists.
- Requested nominal fracture factor of safety: **at least 4**. The present
  conservative coupon screen uses 40.5 MPa / peak tensile principal stress,
  hence a 10.125 MPa stress ceiling. It is not a measured part allowable.
  Finalists need a material/direction-specific check, retained finite 3D peaks,
  local mesh refinement, print bonding evidence and physical qualification.
- CAD validity, connected structural material, preserved interfaces, slicer
  modifier roles, empty windows and nonprinting tabs are mandatory gates.
  Thin-plate buckling and unsupported spans need explicit checks.

## Search variables and initial bounds

These are starting search bounds, not approved print settings.

| Variable | Proposed range / choices |
|---|---|
| Wall loops | Integer 1–8 |
| Broad skins / internal planes | Independently 3–6 layers at 0.2 mm |
| Internal planes | Full or shaped; shaped frame width 3–10 mm |
| Lower / diagonal dense chords | Independently 1.2–8 mm |
| Inner / outer seat dense bands | 2.5–13 mm / 2–5 mm |
| Tunnel reinforcement | Upper/lower collars and saddles, 0–5 mm |
| Sparse infill | 5–15%; zero structural credit |
| Window scale | 0.75–1.10, subject to exact interface and ligament checks |
| Helper organization | Regional density masks; merge into selectable parts only at export |

Keep material placement as explicit geometry and density variables. Extra
selection helpers do not improve structure by themselves; their clipped,
emitted paths must match the intended reinforcement.

## Implementation sequence

1. **Freeze the evaluator.** Pin code, dependencies, material inputs, slicer
   version, process, seed and candidate ordering. Hash every candidate and
   cache results with model/source hashes. Record failures as rejected ledger
   entries. Never reuse a result after its physics or geometry changes.
2. **Make the cheap screen fast and trustworthy.** Cache the fixed-window
   planar mesh and layer masks; reuse assembly information where applicable.
   Validate against E13, the shaped three-wall candidate, full-plane four-wall
   candidate and light one-wall candidate. Start with the existing evaluator
   if the accelerated version does not reproduce those cases.
3. **Run a seeded mixed-variable evolutionary search.** Use a repeatable
   population, crossover/mutation and discrete layer/wall variables. A fixed-seed
   differential-evolution implementation is also suitable; reproducibility
   requires pinned inputs and stable evaluation order, not merely a seed.
   Compare at least two seeds after the initial repeatability check.
4. **Validate finalists using real paths and 3D mechanics.** Replace estimated
   mass with Orca volume. Resolve the one-wall dense-helper STL connectivity
   failure before treating it as a slicable candidate. Reject CAD, slicing,
   contact, residual, force/moment, buckling or strength failures. Refine real
   hotspots; do not remove finite cells or substitute percentile stress for
   the fracture constraint. Feed 3D failures back into the search.
5. **Publish an evidence-backed selection.** Show actual CAD, modifier masks,
   toolpaths, mass/movement frontier, stress refinement, movement reserve and
   all rejected constraints. If no candidate satisfies every gate, publish
   that outcome and the limiting mechanism rather than naming a winner.

## Completion criteria

Two runs with the same locked inputs reproduce the candidate ledger and
selection within stated numerical tolerances. The selected design has actual
sliced mass, verified CAD/helper alignment, satisfactory 3D refinement and
explicit serviceability/strength/buckling results. Physical fit, process
bonding, sustained/hot loading and creep remain a separate qualification gate.

The current light candidate's approximately 4.6 ratio in 2D falls to 0.85
using its raw 3D peak. This discrepancy is the central evaluator problem to
solve before trusting an automated minimum-mass result.
