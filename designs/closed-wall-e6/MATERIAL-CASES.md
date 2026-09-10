# E6 material cases: 85°F storage, 100°F excursions

**Decision: use ASA for the first full-load prototype.** This is an engineering selection for its thermal headroom and an unfilled material for the integrated snap fingers. It is not a demonstrated creep advantage over every PLA, PETG or nylon formulation. PA6-GF is an alternative requiring moisture-conditioned evaluation and separate snap testing. No material currently has a verified full-row rating.

Geometry remains E6: four continuous 1.2 mm load-plane plates, a 2.4 mm modeled structural perimeter, 24 mm overall width and 100 mm rail spacing. All modeled solid must actually print solid; 15% infill receives zero structural credit. The original three-perimeter setting does not itself ensure the modeled perimeter is filled. The unresolved empty-cavity roofs remain a manufacturing gate for every material.

## Service and qualification loads

Use 85°F (29.4°C) for sustained storage, with the same full load at 100°F (37.8°C) for six hours per year. Do not substitute an annual average temperature. No intended service life was specified, so this study does not claim a multi-year life.

| Case | Vertical load per bracket | Purpose |
|---|---:|---|
| Six 1.25 kg gross spools per 16-inch bay; two equal continuous spans | 9.375 kg equivalent at the middle support, before self-weight | Original packed-row service example |
| Continuous full row at 60 mm pitch | 10.583 kg equivalent, before self-weight | Denser packing sensitivity |
| Sustained at 85°F | **12 kg equivalent / 117.72 N** | Rounded design and qualification target |
| Hot excursion at 100°F | **12 kg equivalent / 117.72 N** | Full-load temperature case, six hours/year |
| Proposed brief proof case | **24 kg equivalent / 235.44 N** | Chosen 2× test target; not a code safety factor or capacity |

The 12 kg target leaves 1.42 kg above the 60 mm pitch example for self-weight and modest variation. Actual self-weight must fit that budget. For this screen the entire equivalent load acts at the rod seats, conservatively placing bracket self-weight farther from the wall than its actual center of mass. This does not cover arbitrary heavier/narrower spools, clustered loads, overhangs, impact or uneven support settlement. The two-span reaction factor is not a universal bound. Six spools fit per bay when their effective pitch is at most 67.7 mm; gross mass includes the empty spool.

At 12 kg and equal rail sharing, each seat carries 58.86 N downward and approximately 26–33 N outward over 220–180 mm spool diameters. Wall moment is 16.48 N·m. An ideal bottom compression point gives 84 N upper-fixing tension; actual fastener bearing, pull-through, substrate and wall contact still need checking.

The final CAD section screen samples the knee and forearm at ten stations. The largest sampled nominal combined stress is **3.47 MPa**, including outward seat thrust and axial load; linear scaling gives **6.93 MPa** at the proposed proof load. The knee and the forearm near the rear seat are more demanding than the old midpoint-only screen. These are beam estimates, not peak stresses or failure predictions. They exclude local concentrations, seat/root deformation, connection behavior, shear, plate buckling and creep. Symmetric rod loads are assumed.

[Reproducible load cases](work_material_cases.py) · [Calculated results](material-work-cases.json) · [CAD section extraction](check_material_sections.py) · [Section properties](section-load-screen.json).

## Material comparison

These are specific reference grades, not universal properties of the polymer families. Published typical specimen data are not design allowables. In particular, HDT is a short-duration standardized deflection test, not a continuous temperature rating.

| Material and reference | Typical XY flexural modulus | HDT at 1.8 MPa | Assessment for this temperature envelope |
|---|---:|---:|---|
| [PLA, PolyLite V5.4](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/PolyLite_PLA_TDS_EN_V5.4.pdf?v=1731949179) | 3.23 GPa | 58°C | Stiff initially, least thermal headroom here. Keep as a monitored trial; not the first choice for unattended long-term storage without creep evidence. |
| [PETG, current Polymaker formula](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/PETG_TDS_Polymaker_297e875c-5d38-4d2b-ba68-eef8916de183.pdf?v=1761581533) | 2.28 GPa | 65°C | Candidate, but lower reference stiffness and still needs sustained-load measurement. No substantiated blanket claim that PETG creeps more or less than PLA. |
| [ASA, PolyLite/Polymaker](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/PolyLite_ASA_TDS_EN_V5.4.pdf?v=1731955208) | 3.21 GPa | 100°C | First prototype choice: useful thermal headroom with reference bending stiffness similar to PLA. Printed warp, adhesion and snap behavior must be checked. |
| [PA6-GF25, Fiberon V1.1](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/TDS_FIBERON_PA6-GF25_V1.1_EN.pdf), annealed dry → water-conditioned | 4.31 → 1.45 GPa | 157°C dry; wet not reported | Dry headline stiffness is unsuitable as the sole basis. Evaluate both conditioning states; the dry material's low elongation also makes snap insertion a distinct concern. |

The PA6-GF reference specimens were annealed at 100°C for 16 hours. Water-conditioned specimens then underwent 48 hours in 60°C water; the retrieved TDS reports 4.57% moisture. This is a moisture sensitivity case, not an assertion that an indoor rack reaches that condition. Its wet flexural modulus is about one-third of dry. Annealing can change fit, so the dowel throat and flat wall face must be remeasured. A shop FAQ reports a different moisture percentage; this study uses the TDS. Neither the dry HDT nor dry stiffness is assigned to the wet case.

PETG formulations differ: the legacy PolyLite TDS lists 1.90 GPa flexural modulus and 75°C HDT at 1.8 MPa. Those values cannot be silently transferred to the current formula. [Reference values, source URLs and retrieved-document hashes](material-reference-data.json).

For scale only, a **vertical-load-only, constant-section 100 mm forearm** with the E6 midpoint inertia predicts initial reference deflections of 0.273 mm PLA, 0.387 mm PETG, 0.275 mm ASA and 0.204/0.609 mm dry/water-conditioned PA6-GF at the 12 kg case. These use the published typical flexural moduli. They are not whole-bracket deflections, do not include outward force or joint flexibility, and are not predictions at 85°F or after creep.

## Why there is no material-specific safe spool count yet

No grade-specific long-duration creep curves at 29.4°C and 37.8°C were obtained for these four reference formulations. Dividing their room-temperature tensile strengths by nominal bracket stress would miss local failure and time-dependent deformation. Elongation at break is likewise not allowable snap strain.

Published research on a different printed PLA grade found continuing flexural creep over 170 hours at approximately 20°C; its one-week creep modulus was substantially below its datasheet flexural modulus. That establishes why being below Tg does not eliminate creep. It does not supply a transferable derating factor for these grades, temperatures or years of storage. [Fischbach and Weinberg, 2023](https://arxiv.org/abs/2302.11240).

For **PLA, PETG, ASA and PA6-GF alike**, the proposed target is the full-row case above; maximum verified sustained spools remain **undetermined**. This means capacity is unestablished, not that all four have equal capacity or that any has failed.

## Concrete next qualification work

1. Resolve internal roof printing and inspect actual solid paths before testing a full bracket. Use final geometry, documented grade, layer orientation and extrusion widths. Include representative repeat prints; one passing part cannot establish production reliability.
2. Measure dowel fit and test full-width snap insertion/release at temperature. Include annealed dry and moisture-conditioned PA6-GF. Fingers should relax after insertion; sustained load belongs in the thick bearing seat. Check retention again after thermal/load exposure.
3. Apply the 12 kg equivalent case at 30°C for an initial 1,000-hour monitored trial. Use actual spool-rim contact or fixtures reproducing both vertical and outward seat forces. Hanging a vertical weight from each rod alone misses the outward thrust. Include the smaller-spool case and monitor both seats and the wall joint.
4. Under the same load, include a six-hour exposure at 38°C and record movement during the excursion and after return to 30°C. Repeat excursions as part of longer testing; six hours of heating alone does not reproduce years of prior creep.
5. Proposed serviceability screening targets: no more than 1 mm additional vertical seat movement from the initial loaded reading; no more than 0.5 mm residual movement 24 hours after unloading at 30°C; no visible cracks, loss of snap retention or spool/plastic interference. These are selected project acceptance targets, not published standards. Record creep slope as well as total movement.
6. After initial characterization, use a separate specimen for a proposed 24 kg, ten-minute proof case with the same force directions and controlled temperature. Inspect for damage and loss of function afterward. Passing a brief proof test or the 1,000-hour trial does not establish multi-year creep life: release requires an appropriate longer-term basis, critical-region analysis and verified mounting/dowel details.

Keep the closed-wall path separate from the deferred open-web concept. No geometry change or material-specific capacity release is made by this study.
