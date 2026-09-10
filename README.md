# Spool wall rack — print setup and engineering guide

**Current printable prototype: E8, with level rails.** Print the bracket on its broad side so the principal bending load stays in the layer plane. Two aligned helper solids create continuous internal plates through slicer modifiers.

**[Download the STEP assembly](designs/closed-wall-e8/bracket-with-modifier-helpers.step)** · [Aligned STL fallback and rebuild](designs/closed-wall-e8/README.md) · [Solved results and stress images](analysis/e8/RESULTS.md) · [Analysis run](https://github.com/thereprocase/spool-wall-rack/actions/workflows/engineering-analysis.yml)

The **front rail raised 12 mm** is a separate statics study, described below. It is not incorporated in this STEP and does not inherit the level-rail FEM results.

![Current E8 CAD](designs/closed-wall-e8/progress-exterior.png)

## Current engineering decision

Use **8 walls for the PLA prototype or 10 for the PETG prototype**, plus the four 1.2 mm solid plates described below. At the assumed extrusion widths, these provide about **3.27 and 4.08 mm** of contour wall. These are deliberate prototype settings; they are not material-independent lifetime ratings.

The initial whole-bracket calculations give approximately **1.2 mm front-seat movement for PLA and 1.7 mm for PETG** at the 12 kg equivalent bracket load. That initial flexibility is acceptable against the project serviceability criteria:

- **5 mm maximum total movement under full load**, including creep.
- **1 mm maximum change when adding or removing one full spool.**
- No cracking, loss of rod capture, fastener pull-through or progressive instability. Creep must remain within the movement budget over the chosen service life; an accelerating rate requires investigation.

Movement is measured from the unloaded geometry, relative to a stable wall reference. Decorative camber does not erase actual deformation. Measure at the bracket and between supports so dowel sag and wall/fastener movement are included.

**The remaining material question is creep and rupture over time, not whether 1.2 mm of elastic movement looks large.** No retrieved source establishes an indefinite-life rating for the exact printed grades at this rack's temperatures. The calculations below quantify how much compliance growth the design can tolerate instead of assigning an invented creep factor.

## Print setup

| Setting | Working value |
|---|---|
| Orientation | Supplied broad side down; bracket width is printer Z |
| Layer height | 0.20 mm, including the first layer for the stated band alignment |
| Nozzle used for wall-count mapping | 0.4 mm |
| Assumed outer / inner line width | 0.42 / 0.45 mm; explicit analysis inputs, not asserted slicer defaults |
| PLA contour walls | 8 |
| PETG contour walls | 10 |
| Body infill | 15%; **zero strength or stiffness credit** in the analysis |
| Body top / bottom solid thickness | 1.2 / 1.2 mm, six layers each |
| Helper 1 | 100% infill modifier, print Z = 7.6–8.8 mm |
| Helper 2 | 100% infill modifier, print Z = 15.2–16.4 mm |
| Solid infill | A pattern the slicer supports at 100%, with bonded adjoining lines |
| Filament profile | Exact grade's manufacturer profile, calibrated for the machine |
| Temperature, cooling and flow | Follow that grade's profile; verify bonding and flow before load testing |
| Print envelope | Approximately 206.73 × 208 × 24 mm; pair-print constraint removed |

1. Import the STEP as **one object with three aligned parts**. Do not arrange its components independently.
2. Keep `MAIN_BODY_SET_WALLS_AND_INFILL` as the printable body. Set its walls, 15% infill and six top/bottom layers.
3. Convert each named `MODIFIER_…` helper to **modifier geometry** and set its infill to **100%**. A helper is a finite 1.2 mm slab, not a zero-thickness STEP surface.
4. Inspect the toolpaths at each band. Confirm four continuous solid planes, contour thickness through the knee and beneath both seats, and uninterrupted solid plastic in the screw landings.
5. Confirm the helpers do not print as extra exterior slabs. Check driver tunnels, screw clearance, thin snap fingers and internal bridging over the sparse infill.
6. Save the configured slicer project with the filament identity and settings. The STEP itself stores geometry, not these settings.

![Solid-band layout](designs/closed-wall-e8/modifier-stack.png)

The body is solid **in CAD** so the slicer can generate its internal structure. It is not an instruction to print the body at 100%. Sparse infill supports the internal bands during printing even though it receives no structural credit. Do not reintroduce modeled hollow bands or an internal grid into the printable STEP.

Use the supplied orientation for all mechanical comparisons. Standing the bracket upright changes the layer-load relationship. A 0.6 mm nozzle may suit abrasive filament, but the wall **count** must then be recalculated to achieve the modeled thickness. Do not silently carry over the 0.4 mm mapping.

### Walls versus millimetres

A rounded-rectangle bead-spacing estimate at 0.2 mm layers is:

`t(n) = 0.42 + (n − 1) × [0.45 − 0.2 × (1 − π/4)] mm`

| Walls | Approximate thickness |
|---:|---:|
| 3 | 1.23 mm |
| 5 | 2.05 mm |
| 6 | 2.46 mm |
| 8 | 3.27 mm |
| 9 | 3.68 mm |
| 10 | 4.08 mm |
| 12 | 4.90 mm |

Inspect the real slice; variable line width, thin-wall handling and local geometry alter this estimate. The two exterior and two interior plates stay 1.2 mm thick. More perimeters add material near bending-section edges and reduce working stress, but gains diminish. They do not establish a material's creep-rupture law. The main arm remains approximately 28 mm deep; the earlier 34 mm depth proposal has not been implemented.

## Material choice at 85°F sustained / 100°F for six hours per year

Both temperature cases retain full load. The following are **reference-grade comparisons**, not universal polymer properties. [Datasheet values, exact sources and hashes](designs/closed-wall-e6/material-reference-data.json).

| Material case | Prototype setup | Engineering implication |
|---|---|---|
| PLA | 8 walls; four 1.2 mm plates | Initially stiff. Least thermal headroom of these reference grades. Plausible candidate under the 5 mm criterion, with a grade-specific sustained/hot load trial. |
| PETG | 10 walls; same plates | More compliant initially, accommodated by thicker walls. A useful candidate; published short-time PETG creep evidence does not determine this grade's multi-year behavior. |
| ASA | Start with 8-wall geometry for comparison | First higher-temperature prototype choice. Thermal headroom is useful, but ASA is not automatically creep-qualified. |
| PA6-GF, annealed/dry | Compare the 8-wall effective thickness | High dry stiffness; match the datasheet's conditioning and annealing before using its properties. Integrated snaps need their own insertion/retention check. |
| PA6-GF, moisture-conditioned | Same geometry, conditioned properties | The reference Young's modulus falls from about 5.36 to 1.79 GPa. Treat this as a separate case, not as dry nylon with a small correction. |

The PA6-GF source specifies 100°C / 16-hour annealing for its reported properties. Its water-conditioned specimens are a deliberate sensitivity case, not a claim about equilibrium moisture in a particular room. Annealing can change fit. Use suitable abrasion-resistant extrusion hardware for glass-filled material and recheck the dowel and screw coupons after conditioning.

HDT and glass-transition temperature help compare thermal sensitivity; neither is a sustained-load allowable. Generic tensile strength divided by a convenient factor is not a creep design method. “PLA+”, “PETG HF” and other modified products need their own data.

## Loads and spool count

The design case uses 406.4 mm (16-inch) support spacing and an assumed **1.25 kg gross mass per full spool**, including the empty spool.

Six spools per bay weigh 7.5 kg and require pitch no greater than 67.7 mm. An interior support between simple spans receives about one bay's load. For two equal continuous spans under uniform load, the middle reaction is **1.25 times one bay's load**, or 9.375 kg equivalent before self-weight. At a continuous 60 mm spool pitch, that estimate becomes about 10.58 kg. The **12 kg equivalent / 117.72 N per bracket** analysis target allows additional demand for that example. It is not a universal bound on uneven loading, overhangs or arbitrary continuous spans.

For the level-rail model, each seat receives 58.86 N downward. The 180 mm spool case adds 32.93 N outward at each seat and produces about 16.48 N·m at the wall. Loads act over bearing arcs, not at the thin finger tips. The older load formula used an effective 12.4 mm rail radius; the separate raised-front statics uses nominal 12.7 mm radius. These are explicitly different inputs.

**Six per bay is the full-row test arrangement, not a released safe count.** No maximum safe spool count is yet assigned for PLA, PETG, ASA or PA6-GF. A capacity must satisfy the printed bracket, snaps, dowels, screws and wall, including creep and the specified serviceability limits.

For a tested material with usable creep compliance, scale bracket movement linearly within this small-deflection model:

`δ(m,t,T) = δ(12 kg,t,T) × m / 12 kg`

Then check the actual support reactions for the installation. Do not equate “six spools per bay” with “six spools carried solely by one bracket.”

## What the FEM resolves

The **2D plane-stress model** integrates the ideal printed material across the width. It includes contour walls, the four solid bands and fastener opening effects. It omits broad-face chamfers and projects the mounting restraints onto the wall, so it is a reduced comparison model.

The **3D model** starts with the actual chamfered E8 exterior and functional holes, then removes an analysis-only sparse core. It retains the ideal contour walls, four continuous plates and tunnel surrounds. These analysis cavities are not printable CAD changes.

Both models use compression-only wall contact. Rigid washer patches restrain outward movement and ideal screw shanks carry shear. The wall cannot pull the bracket inward. The 3D material is small-strain, homogeneous and isotropic with Poisson ratio 0.35; the reference solve uses E = 1,000 MPa and scales displacement to each grade's published XY Young's modulus. This does not resolve actual FFF orthotropy, bead defects, layer adhesion, screw/stud compliance or changing snap contact.

![2D solved FEM](analysis/e8/fem-2d.png)

![3D solved FEM](analysis/e8/fem-3d.png)

**Takeaways:** the reduced section beneath the rear dowel seat contributes substantial rotation. The earlier 0.22/0.27 mm numbers described only an idealized forearm and must not be used as whole-bracket movement. The first 8-wall 3D solve placed about 48% of the elastic strain energy in the rear-seat region, versus about 14% in the forward arm region. The recessed lower fixing also attracts significant outward reaction; assuming the upper screw alone takes the overturning couple misses that connection behavior.

The refined rear-seat regional volume-p99 von Mises stresses are approximately **7.6 MPa for 8 walls and 7.0 MPa for 10 walls**. Refinement increased these regional values by about 19% and 12%, while front movement increased about 5% and 6%. Global field percentiles changed less. The stress field is not demonstrated to be asymptotically converged. Raw peaks depend on tiny mesh cells at tool-tunnel/chamfer intersections as well as idealized restraint edges. For example, the regenerated 8-wall coarse maximum sits in a roughly 0.0000046 mm³ element at a tunnel-mouth intersection; that value is not a reliable rupture demand. The refined maxima move into the analysis-only inner-wall transitions beneath the rear seat, reaching approximately 25–27 MPa in very small cells. Those sharp core transitions approximate slicer-generated geometry; this analysis neither resolves their physical printed radii nor establishes a notch/rupture allowable. Different meshes can reverse the ranking of raw peak stress between the 8- and 10-wall cases. **Neither raw peaks nor percentile summaries are material allowables.** Use the [regenerated results](analysis/e8/RESULTS.md) for current mesh comparisons, actual stress fields, reactions and residuals.

An affine uniaxial patch test checks stiffness assembly, recovered stress and strain energy. Whole-bracket force/moment balance, residuals and refinement checks accompany the result files. A mesh comparison supports numerical interpretation; it does not validate years of service.

## Creep calculation and available margin

For a constant load and a common linear-viscoelastic compliance throughout a model with unchanged contact state:

`δ(t,T) = K × J(t,T) = K / Ec(t,T)`

Here K is the geometry/load coefficient in MPa·mm, J is creep compliance in MPa⁻¹ and Ec is the **secant creep modulus**, not the instantaneous unloading modulus. For the refined level-rail solves:

| Case | K, approximately | Initial movement | Ec needed for 5 mm bracket-only movement | Maximum compliance growth relative to reference E |
|---|---:|---:|---:|---:|
| PLA, 8 walls | 4,226 MPa·mm | 1.23 mm | 845 MPa | 4.05× |
| PETG, 10 walls | 3,839 MPa·mm | 1.66 mm | 768 MPa | 3.01× |

Refinement updates live in [RESULTS.md](analysis/e8/RESULTS.md). These thresholds spend the full 5 mm on the bracket. For the complete rack, use **Ec ≥ K / (5 mm − dowel movement − wall/fastener movement)**. The earlier 1-inch wood-rail example gave about 0.22 mm instantaneous sag with an assumed 8 GPa modulus; wood grade, moisture, defects and long-term behavior remain installation inputs.

For a material-data screening target, use **at least 1.0 GPa effective creep modulus at the intended age and loaded temperature history**. This rounds above the bracket-only thresholds and preserves some movement budget for the dowels, mounting and reaction redistribution. It is a project screening target, not a published grade allowable or a rupture criterion.

The tabulated correspondence calculation keeps the original seat reactions. Deformation changes those reactions: with a 200 mm spool and the front seat 4.65 mm lower relative to the rear, the front vertical load share rises from 50% to about 55.8%. That modest positive feedback needs a deformed-contact check near the movement limit; do not treat the linear threshold as an exact nonlinear capacity.

A one-roll change assigning an entire 1.25 kg reaction to one bracket gives approximately **0.13 mm for PLA and 0.17 mm for PETG** with the reference instantaneous modulus. For simple spans and the stated two-equal-span geometry, a single point load's reaction at the relevant support does not exceed the whole load. This estimate excludes overhangs, unusual continuity and handling impact. Fast removal of a roll depends on the aged unloading modulus; it is not correctly modeled by simply reversing all accumulated creep.

Even a settled, linear response at the full 5 mm limit gives a proportional one-roll change of about 0.52 mm for this load assumption. The 5 mm full-load criterion is therefore more restrictive than the 1 mm per-roll criterion in that simplified case.

### Published creep evidence and its limit

[Stankevics et al., 2025](https://doi.org/10.3390/polym17152075) tested unidirectional, 100%-filled Devil Design PETG at approximately 21.3°C, with tests extending to 20 hours. Its Figure 26 Prony spectrum provides a short-time benchmark. Graphically transcribed amplitudes are approximately 0.005, 0.010, 0.015, 0.010, 0.020 and 0.080 at time constants 1 through 100,000 seconds in decades.

`J(t)/J0 = 1 + Σ Ai[1 − exp(−t/τi)]`

That spectrum gives roughly 1.07 at five hours, 1.10 at 20 hours and a formal asymptote of 1.14. **The asymptote is a property of the fitted finite series, not proof that a rack at 85°F stops creeping.** Longer-time mechanisms were not calibrated by that experiment.

[Fischbach and Weinberg, 2023](https://arxiv.org/abs/2302.11240) tested a different printed PLA at room temperature. After approximately one week, measured flexural creep modulus was 1,040 MPa, about 56% of its 1,860 MPa datasheet flexural modulus, and deformation was still increasing. That demonstrates meaningful sub-Tg creep; it cannot be transferred unchanged to this PLA grade, temperature or service life.

The [calculation file](analysis/e8/engineering-summary.json) reports one-, five- and ten-year **sensitivity cases**, including unmeasured long-time compliance tails of 0, 0.02 and 0.10 per year. These are explicitly assumed continuations of a short-time example, not claimed PLA/PETG forecasts.

![Creep sensitivity](analysis/e8/creep-sensitivity.png)

A long-time viscous tail can be almost invisible in a 20-hour test yet add appreciable deformation over ten years. Conversely, slow creep that remains inside the movement budget need not make the rack unusable. The release question is whether the grade's measured compliance and creep-rupture behavior support the intended life.

### Six hot hours each year

With 85°F as the reference temperature, reduced annual time is:

`ξyear = 8,754 + 6 × Ahot hours`

Ahot is the material's creep-rate shift at 100°F relative to 85°F. It is not known for these print/grade combinations. An **assumed Arrhenius sensitivity**, using activation energies of 50, 100 and 200 kJ/mol, gives Ahot about 1.70, 2.90 and 8.42. The six hot hours then add about 0.048%, 0.130% or 0.508% to annual equivalent time.

Those small percentages do not establish thermal adequacy: the shift law is uncalibrated, reversible hot softening still occurs during the excursion, and nonlinear creep or damage may invalidate simple time shifting. Check loaded movement during the actual hot exposure. Do not replace the cycle with an average temperature or use a universal WLF constant as grade data.

## Screw landings and installation

| Feature | Current design |
|---|---:|
| Screw clearance | Nominal Ø5.2 mm with small printable roof relief |
| Compatible shank envelopes | #8, #10 and nominal M5; printed M5 fit needs confirmation |
| Washer face to wall | **3.6 mm** |
| Nominal driver access | Ø16 mm with sloping roof |
| Checked straight driver envelope | Ø15.8 mm |
| Analysis washer | Ø13 OD / Ø5.5 ID; 1.2 mm thick for geometric fit |
| Screw axes | Y = 164 and 40 mm; Z = 12 mm |

Use flat-bearing heads and washers. A countersunk head introduces wedging that these models do not cover. Do not assume every washer sold for M5 has the analyzed outside diameter. For a different washer, check fit and recalculate bearing area.

The actual CAD supports approximately 99.1% of the specified washer annulus. The small loss comes from the printable roof relief in the screw hole. The available bearing area is about **108 mm²**:

`A ≈ 0.991 × π/4 × (13² − 5.5²)`

| Assumed clamp force per screw | Mean pressure on supported annulus |
|---:|---:|
| 250 N | 2.3 MPa |
| 500 N | 4.6 MPa |
| 1,000 N | 9.3 MPa |

These forces are scenarios. Driving torque into wood does not reliably determine the clamp force because thread cutting and friction consume torque.

![Screw-landing FEM](analysis/e8/fem-landing.png)

The local 3D submodel uses the actual **upper 3.6 mm land**, a 500 N distributed washer force and flat rear support. Refining that submodel from approximately 27,500 to 81,300 tetrahedra changed average axial washer movement from 0.0118 to 0.0121 mm at E = 1,000 MPa; the raw von Mises peak changed from about 4.83 to 4.98 MPa. At the PLA reference modulus that axial movement is about 0.0035 mm; at PETG's, about 0.0052 mm. These are constant-force calculations, not predictions of installed clamp-force retention.

**Retain the 3.6 mm land for now.** The backed compression case does not justify making it thicker. More thickness would add creep compression travel and violate the compact clamp intent without addressing the governing bracket region. This is a reasoned decision to retain the geometry, not a claim that every washer, tightening force or wall surface is acceptable.

The whole-bracket service model checks both fixings. The refined 8-wall solve attracted approximately 187 N outward reaction at the lower washer and 25 N at the upper; those demands depend on wall contact and connection stiffness. They replace the earlier upper-screw-only assumption for this specific model. They do not include an arbitrary tightening preload, and maxima from separate cases cannot simply be added as scalar von Mises stresses.

Mount against a flat, firm surface with full back contact. A gap behind a landing changes it into a bending/punching problem and invalidates the backed compression case. Seat the washer firmly without crushing the print; inspect for embedment and loosening. The load path does not rely on sustained clamp friction alone.

Use screws intended for the actual stud substrate, with manufacturer-specified pilot drilling and embedment. Required length includes the 3.6 mm plastic, washer, wall finish and required stud engagement. M5 **shank clearance** does not mean an M5 machine screw can be driven directly into wood. Install the screws before loading the rack. The checked tool is a straight cylindrical envelope, not an arbitrary drill body.

## Raised-front rail study: +12 mm

Raising the front rail changes support geometry and reactions; it is more than cosmetic camber. For nominal 25.4 mm dowels, 100 mm horizontal spacing, frictionless contacts and a 200 mm spool:

| Quantity | Level rails | Front rail +12 mm |
|---|---:|---:|
| Spool center from wall | 140.0 mm | 128.0 mm |
| Rear / front vertical load fractions | 50% / 50% | 64.8% / 35.2% |
| Wall moment at 12 kg equivalent | 16.48 N·m | 15.07 N·m |
| Net moment about rear rail | 5.89 N·m | 4.47 N·m |

This reduces wall moment about **8.6%** and the net moment about the rear rail about **24%**. The front rail still carries roughly 35% of the weight. Across 180–220 mm spools, the wall-moment reduction is about 7.6–9.5%. The front rail also presents a higher obstacle to forward roll-out.

![Raised-front statics study](analysis/e8/raised-front-statics.png)

**The unmodified back arm fails the raised-front clearance check.** With the front rail +12 mm, nominal clearance is about 4.65 mm for a 180 mm spool, only 0.22 mm for a 200 mm spool, and **−9.45 mm (interference)** for a 220 mm spool. These values come from point-to-segment distances on the exported E8 profile, using nominal dowel geometry. [Clearance results](analysis/e8/raised-front-clearance.json). Reshape the back arm toward the wall or move the rails outward before adopting this option; moving the rails outward returns some of the moment reduction.

The cost also includes greater rear-seat vertical load. That seat is already an important flexible region. Moving the front seat without remaking its supporting arm and rotating both snap openings to the new contact directions would be incomplete. The closer spool also needs a renewed wall-arm clearance sweep over the full diameter range.

**This option is not yet printable or FEM-qualified.** Complete its geometry, contact/clearance checks and load cases as a separate revision before replacing E8. Cosmetic camber remains an optional separate adjustment: half of a defensible one-year **front-minus-rear differential sag**, not half an unsupported life estimate.

## Qualification before assigning a lifetime spool rating

Record the actual filament grade, print settings, dry/conditioned state, washer, screws, dowel diameter/grade, spool mass/pitch and support arrangement. Confirm the slice matches the structural assumptions.

Measure unloaded position, immediate loaded movement and loaded drift at increasing elapsed times, including a sustained 85°F trial and a six-hour loaded 100°F exposure. Log the temperature at the bracket. Track the rear and front seats, span-center rail sag, washer embedment and any movement relative to the wall.

Use **5 mm total full-load movement and 1 mm per-roll change** as the project limits. Compare creep rates over equal time intervals; a plateau should emerge from measurements, not from forcing a finite Prony fit. Inspect for cracks, whitening, layer separation, permanent snap opening, loss of capture and increasing screw embedment. A 24 kg brief proof case is a proposed separate test; passing it does not establish long-term creep life.

A 1,000-hour trial is useful screening and model calibration. It is not automatically a ten-year rating. Extrapolation requires justified temperature/time shifts, the grade's creep behavior and a rupture check.

## Reproduction and design history

[Analysis scripts](analysis/e8) include the material-domain construction, 2D/3D solvers, known-solution verification, stress rendering, creep calculations and raised-front statics. [GitHub Actions](.github/workflows/engineering-analysis.yml) runs and publishes the calculated fields, then repeats the bracket and landing checks with finer meshes. The result JSON files retain force/moment balance, residuals and mesh details. Analysis-only BREP files and base meshes are regenerated; they are not print deliverables.

The CAD geometry verification is separate: [E8 STEP and hardware checks](designs/closed-wall-e8/verification.json). Physical printing and mechanical tests have not been performed in this repository.

[Design journal and superseded calculations](DESIGN-JOURNAL.md) · [Design decisions](DESIGN.md) · [Separate future open-web exploration](future/open-web/README.md)
