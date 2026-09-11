# G2: broad architecture study, preceded by a slicer-material correction

Find a credible, compact prototype architecture for the filament rack. Local
strength robustness, stiffness, practical printing and installation outrank
minimum mass. E13 and Rev G CAD, scripts, fields and published conclusions
remain unchanged historical records.

## Current prerequisite: correct the G material mapping

The next action is to recheck G's full-plane finalist using structural material
derived from actual Orca paths. The former hand-built shell/core and its
one-direction coverage check do not establish equivalence to printed material.
Do not use the old peak to demand special helpers or select G2 architecture.

Use at least **two walls**, 0% base infill, and the existing three 100% helpers.
The reference has five 0.2 mm top and bottom layers. Validate the new fast
plastic-shape tool with two/eight walls crossed with two/eight top and bottom
layers, as well as the reference. **Count 0.4 mm bridge extrusion in spent
plastic, but give it zero stiffness, strength and bonded-connection credit.**
Keep raw paths, per-path widths/heights, geometry hashes, layer comparisons,
timings, numerical fields and failures. Report extrusion volume separately
from any homogenized shape approximation and bound the difference explicitly.

## Hard functional and engineering requirements

- Target the **Bambu P1S, 0.4 mm nozzle**, PETG or ASA. Select a specific grade
  and process before physical qualification; reference-grade data are not
  universal material allowables. Two walls is the minimum process choice.
- Support nominal 1-inch dowels and 180–220 mm spools. Actual diameter and
  ovality measurements are pending. Establish tolerances from those
  measurements and printed coupons, not nominal supplier dimensions.
- Spools must slide across bracket positions without plastic interference.
  Retention must include positive capture, without depending on sustained
  snap clamping. Recheck insertion, strain, retention and repeated operation.
- Prefer one printed bracket and ordinary wall fasteners. Analyze any
  multipart or nonprinted structural alternative separately, including its
  assembly and failure modes. Verify orientation, printer exclusions,
  overhangs, bridges and inspectable load-bearing paths.
- Verify driver access, screw clearance, washer bearing, wall contact and
  realistic installation. State required substrate, hardware, embedment and
  contact condition; ideal capacity is not an assumption.
- Apply 12 kg / 117.72 N per reference bracket. Limit total loaded movement
  to 5 mm including bracket, rails, mounts and creep. Provisionally reserve
  1 mm for rails/mounts, leaving 4 mm for bracket resultant movement; this
  allocation requires replacement by measured or modeled contributions.
- Limit total movement change for one 1.25 kg spool to 1 mm. Finalists need
  a new load/contact solve for the changed load, including the non-bracket
  contribution; proportional scaling alone is insufficient.
- Retain sustained 85°F and brief loaded 100°F service conditions. The
  E = 1,000 MPa effective planning model is not a demonstrated lifetime law.
- Require a nominal fracture factor of at least four on a material/process
  basis. Retain every finite stress cell, raw peaks and mesh-refinement
  behavior. No percentile substitution or stress-based cell deletion.

## Geometry and density freedoms

E13's outline, arm depth, underside, knee, chamfers, windows, internal planes,
ribs and modifiers are soft. Wall-plate shape and fixing positions, local
seat/arm/wall transitions, rail spacing and rail elevation may change if the
functional requirements are re-established. No existing solid region is
mandatory. Material may be removed anywhere. Helpers have no fixed count,
shape or placement; their effective union is clipped to the body and counted
once. Integrated reinforcement is equally acceptable.

Keep the bracket and spools generally in the same vertical band. Permit up
to 8 mm additional downward projection relative to the preferred arrangement's
spool-relative lower envelope, only where it improves the load path. Changing
rail positions requires recomputing that reference comparison. The initial
post-G draft's fixed rails, local E13 silhouette floor and fixed fixing axes
are superseded; its drawing is a reference, not G2's mandatory design space.

Retained chamfers need sufficient continuous structural backing. Compare
actual slicer-generated backing before adding a helper. If a feature changes,
separate geometric changes from density changes in the evidence.

## Study sequence and decision gates

1. Correct and validate the slicer-material representation, then re-solve G.
2. Build at least six materially different, parameterized architecture
   families. Show sections, primary load paths, print orientation, interfaces
   and rough mass. Include useful use of the lower 8 mm allowance and a family
   without the thin forearm chamfer/inner-seat transition dependency.
3. Compare viable families with the same auditable reduced model for ranking
   only. Record geometry, contact, loads, material assumptions and failures.
   Reject early only for clear functional, geometry or manufacturing failures,
   or an evidently inferior load path.
4. Obtain 3D feedback for representatives from each surviving family before
   local optimization. Refine seats, knee, wall transition, fixing lands and
   high-gradient regions. The G 2D/3D discrepancy is a mandatory regression.
5. Optimize credible families and select by Pareto tradeoffs: local strength
   robustness, movement reserve, toolpaths, actual Orca mass, then compactness.

A preferred prototype must pass CAD validity, connected structural material,
spool/slide sweeps, hardware access/bearing, actual dense-path and unsupported-
feature audits, 3D equilibrium/force/moment gates, local refinement, relevant
buckling checks and explicit movement reserves. If none passes, publish that
result. A simulation-only pass is never a released spool rating.

## Required published evidence

Maintain a family matrix with sections, load paths and rejection reasons;
rebuildable CAD/scripts for viable families; finalist 3MF/STEP/STL; slicer
mass/path evidence; reproducible reduced/3D analysis; a complete candidate
ledger including failures; and a concise current README. Name a preferred
prototype only after all computational gates pass.

## Physical qualification plan

Measure dowels at several axial positions and clock angles, record moisture
condition, and test min/max fit coupons. Print process coupons in the chosen
orientation, with the actual filament, drying, chamber, flow and cooling
settings; measure walls, skins, interlayer bond and representative corners.
Use immediate static-load tests with separate bracket, rail and mount
displacement measurements, including adding/removing one full spool. Test
sustained 85°F loading and the planned brief 100°F loaded exposure while
logging time, temperature, movement and residual set after unloading.
Cycle installation and retention, verify capture after warm sustained loading,
measure rail sag and mount slip, and inspect seat roots, knees, washer lands,
layer separation and permanent distortion. Establish stop/reject criteria
before testing: visible cracks/separation, loss of retention, progressive
movement, hardware slip, or either serviceability limit exceeded. Destructive
strength testing requires a controlled fixture and a material/process-specific
acceptance basis; room-temperature coupon averages do not establish service life.
