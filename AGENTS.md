# Project instructions

Keep this repository current as the design progresses. Checkpoint completed geometry and its verification with clear commit messages. Keep the current prototype obvious in README; preserve superseded useful revisions separately.

Do not commit personal information, private conversation transcripts, credentials, local absolute workspace paths, or identifying account data in project content. Use a generic project identity for git commits.

Current path is the closed-wall, continuous-plate bracket. Keep the future open-web exploration separate. Preserve full L-shaped internal plates parallel to printer XY and installed bending plane. Do not replace them with transverse grids.

Print assumptions: 0.2 mm layers; 1.2 mm top and bottom; 15% infill gets zero structural credit. E6 uses 2.4 mm modeled structural perimeter, superseding the original three-perimeter assumption locally; verify actual sliced paths. Internal and exterior side plates remain 1.2 mm. Snap fingers are separately dimensioned.

Do not assign safe spool counts from generic tensile strengths. State limits of geometric checks and distinguish geometry, slicing, mechanical analysis and physical validation. Never label prototype G-code or a geometry-only 3MF as a validated print profile.

Update the README design journal at meaningful checkpoints. Include actual CAD screenshots or drawings, the reason for each change, validation outcomes and the concrete next step. Keep the newest prototype and image prominent so a reader can follow progress by refreshing GitHub. Do not substitute a plan for completing authorized work.

Snap roots must transition smoothly into the bearing seat. Do not use intersecting circles over a stepped profile as a substitute for tangent root blends. Round relief-slot ends and inspect the actual integrated bracket profile, not just an isolated retainer. Current reference is E8.

When replacing a feature, remove its obsolete precursor geometry. Do not leave redundant lips, support nodes or prongs behind a new retainer. Inspect the full integrated outline at both seats.

E6 final geometry requires finish_cad.py after profile export. Preserve matching cavity-rim reinforcement behind the mirrored 3 mm broad-face chamfers. Smoothly taper large edge treatments to zero before small features; do not apply their nominal radii to thin snap noses.

E6 uses 100 mm rail spacing, 90/190 mm rail centers, a full wall plane from -32 to +176 mm, and screw centers at 164/12 mm. E5 is a rejected fixed-span thinning study. Preserve the stated handling-stability tradeoff; the I/L^3 comparison is a screening proxy, not whole-bracket stiffness or a load rating.

Service envelope: 85°F sustained; 100°F for six hours/year, fully loaded. Work PLA, PETG, ASA and PA6-GF cases. E6 material report selects ASA for the first prototype, not a released rating. The 12 kg sustained/hot and 24 kg brief proof cases are qualification targets. Preserve PA6-GF annealed dry and water-conditioned cases separately; published typical properties and short tests do not establish years of creep life.

E7 adds 10 × 10 mm maximum cavity boxes with 1.2 mm manufacturing dividers and R2 full-cell corners, preserving four continuous 1.2 mm plates. Dividers receive no assigned structural credit. Current fixings are Y=164/40 mm; clamping lands are 3.6 mm from the wall, with Ø5.2 mm screw clearance and Ø16 mm nominal driver access. Preserve the sloping access roofs. #8/#10 and M5 shank clearance are intended; confirm printed M5 fit with the coupon. E7 STEP is distributed as bracket-step.zip; do not publish the ignored 46 MB intermediate uncompressed file. Keep the three-step build chain: SCAD profiles, finish_cad.py, verification/rendering. E7 changes the connection and does not inherit a validated E6 load rating. The 34 mm arm-depth study remains unimplemented.

Current E8 delivery supersedes the E7 grid: one solid STEP body plus two separate 1.2 mm helper slabs at print Z=7.6–8.8 and 15.2–16.4 mm. User chooses body wall count and infill and converts helpers to 100% infill modifiers. Do not model infill cells or large internal void bands, fuse the helpers into the body, or imply STEP encodes slicer settings. Keep body/helper positions aligned. Wall thickness is now slicer-controlled, not a 2.4 mm CAD shell. Preserve E7 fastener geometry. No extra helper systems or slicer project are required unless requested.
