# Next study after Rev G — resolve local strength before reducing mass further

Rev G's [original genetic-search sprint](REV-G-SPRINT-BRIEF.md) is complete.
It evaluated 1,458 distinct parameter sets, verified deterministic replay and
examined actual CAD, slicing and 3D finalists. **No tested finalist satisfies
all gates.** The optimizer is implemented; another population run alone does
not resolve the observed 2D/3D discrepancy.
[Completed results](analysis/rev-g/README.md).

## Evidence that sets the next scope

The 103.76 g full-plane finalist meets the provisional bracket movement
screen but fails the raw 3D tensile screen at h2, h1.5 and h1. The peak rises
32.29 → 37.99 → 55.05 MPa and migrates to a preserved exterior forearm
chamfer. A CAD-face comparison locates the fine peak approximately 0.00162 mm
from that surface. Wider inner-seat support improves the coarse result but
does not pass strength.

This does not prove the peaks are artifacts, nor does it establish the
part's physical rupture load. It identifies the geometry and material
evidence needed before an automated mass optimum can be trusted.

## Proposed sequence

1. **Reproduce the local mechanism.** Build a displacement-driven submodel
   around the seat and forearm hotspots using the saved full-bracket fields.
   Compare actual STEP facets, nominal emitted bead boundaries and a
   physically justified printed corner geometry. Require mesh refinement and
   balanced reactions; retain the existing unmodified model as a control.
2. **Resolve the geometry boundary.** E13's exterior is protected by the F/G
   scope. Any exterior smoothing or larger local blend is a new design-scope
   decision, not an implicit optimizer mutation. First determine whether
   a modifier-only reinforcement can pass with that exterior unchanged.
3. **Establish material/process evidence.** Select the actual grade and print
   process, measure printed sections and test representative layer-bond,
   corner and fixing coupons. Keep the 85°F sustained and brief 100°F service
   envelope, dry/conditioned cases where relevant, and creep uncertainty.
4. **Improve the acceptance evaluator.** Validate local 3D stress and
   quadratic stability against the refined model and available tests. The
   four-case 2D equivalence check remains a regression guard, not proof that
   2D predicts fracture.
5. **Resume constrained optimization.** Use the existing seeded ledger,
   add validated 3D information, and rank only feasible finalists by actual
   Orca volume. Keep walls, layer thicknesses and modifiers manufacturable.
   Report the Pareto tradeoff and all rejection reasons.

## Unchanged acceptance boundaries

Use 5 mm total loaded movement, including rails/mounts/creep; 1 mm change per
1.25 kg spool; and the requested nominal fracture factor of at least four at
the 12 kg reference case. The 1 mm rail/mount reserve is provisional. The
40.5 MPa typical coupon value is a screening input, not a tested part allowable.
Do not substitute percentiles, remove finite stress cells or relax the
fracture limit to select a winner. Report buckling separately, including
imperfection and nonlinear-model limits.

The next milestone is a reproducible, physically defensible local strength
assessment and a candidate that passes the resulting computational gates.
Physical fit, calibrated printing and sustained/hot qualification remain
separate. No next-study design or test is represented as already complete.
