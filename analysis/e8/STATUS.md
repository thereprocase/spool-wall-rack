# E8 engineering analysis checkpoint

The current analysis resolves the full load path, including the reduced section below each dowel seat and the recessed screw landings. The printable E8 geometry is unchanged at this checkpoint.

- Actual E8 exterior and functional holes are retained in a separate analysis-only CAD surrogate.
- Contour walls represent the 8-wall PLA and 10-wall PETG prototype settings; four 1.2 mm plates remain. Sparse infill receives zero credit. These analysis cavities are not printable design geometry.
- 3D tetrahedral and independent 2D plane-stress models are being solved for the 12 kg bracket target.
- Wall contact can carry compression only. Washer seats restrain outward movement; screw shanks carry shear.
- The landing submodel applies a stated 500 N washer load to the actual 3.6 mm land, with the rear face supported against a flat wall. Results will also be scaled to 250 and 1,000 N. These are preload scenarios, not torque-derived values.
- Published PETG creep data extend to 20 hours near 21°C; the PLA source includes one week near 20°C. Neither alone establishes years at 85°F plus annual 100°F excursions.

Solver files and result images are being added here. Numerical results must pass equilibrium and mesh checks before becoming README recommendations.
