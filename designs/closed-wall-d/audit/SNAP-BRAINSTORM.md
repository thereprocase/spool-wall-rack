# Snap retention — concept discussion, no CAD change

Preferred concept: retain a stiff lower saddle and its lower outside shoulder, and add separate long, thin, tapered cantilever fingers with local retaining noses. Keep flexure bending in the printed XY plane. Relief slots must terminate with generous radii and stay clear of the main seat-to-arm load path. Use a shallow insertion ramp, deliberate retention flank, and accessible release if required. Design the fingers to relax after insertion rather than clamp the wood continuously. Design overtravel stops if they can be packaged without interfering with spool travel.

For a concentric circular cradle wrapping 185 degrees, throat width = seat diameter * cos(2.5 degrees). A matching 25.4 mm cradle provides only 0.0242 mm diametral interference. The current 26 mm seat gives a 25.9753 mm opening and therefore does not capture a nominal 25.4 mm dowel. A concentric 26 mm seat needs more than 204.67 degrees just to begin nominal capture. Independent hook noses allow clearance, capture and flexibility to be tuned separately.

Dowel bearing includes outward thrust: for the nominal geometry and symmetric rigid spool contact, horizontal/vertical rail force = 75 / sqrt((spool radius + 12.7)^2 - 75^2). This is approximately 1.069 for 180 mm flanges and 0.772 for 220 mm flanges. The lower outside shoulder must carry this load without depending on a flexible retainer.

Start with paired fingers for straight-down assembly. Compare an asymmetric arrangement with one flexible latch and a rigid locating lip if the spool-facing side lacks clearance; that alternative must also demonstrate an installation/removal path across multiple brackets. Independently check each rail's spool-facing hook against the full flange swept envelope. Do not assume adding wrap preserves the old clearance result.

Tolerance design should use measured smallest/largest dowel diameters including ovality, printing bias, and moisture variation. The largest printed throat must still capture the smallest rod. The smallest printed throat must allow the largest rod to pass without exceeding tested finger strain. The seated largest rod should leave the fingers essentially relaxed. A useful prototype sweep is 0.4–0.8 mm total throat interference relative to a measured representative rod, not a final tolerance specification.

For preliminary straight rectangular cantilever screening, maximum bending strain is about 3*t*delta/(2*L^2). With L=20 mm, t=1.4 mm and tip travel delta=0.4 mm this is 0.21%, before root concentration or print defects. This is not an allowable strain or prediction for a curved/tapered final finger. Use tested printed-material data for final design, not injection-molded handbook allowables.

Covestro's design guide supports unloaded seated snaps, tapered/extended flexures, and consideration of insertion and extraction loads: https://solutions.covestro.com/-/media/covestro/solution-center/brands/downloads/imported/1557218421.pdf . Its molded-resin property values are not printed-material allowables.

Next design gate: resolve the parent bracket's unsupported internal roofs while preserving continuous load-plane plates; then develop the seat/finger cross-section and a small material/tolerance coupon before revising the full bracket. Open-web concept remains separate.
