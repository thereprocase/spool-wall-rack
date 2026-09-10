# Dowel fit: source dimensions and outstanding measurements

**The snap fit is not yet qualified against measured retail dowels.** The design uses a nominal 25.4 mm rod and a 26.0 mm CAD seat. That is 0.6 mm diametral design clearance, not a supplier tolerance and not proof that every 1-inch dowel fits.

## Source check — 10 September 2026

| Lowe's product | Identification | Published actual diameter | Published diameter/ovality tolerance found |
|---|---|---:|---|
| [Madison Mill poplar, 48 inches long](https://www.lowes.com/pd/Madison-Mill-Round-Wood-Poplar-Dowel-Actual-48-in-L-x-1-in-dia/3040774) | Item 19386; model 436513 | 1 inch / 25.4 mm | None on the checked listing |
| [Madison Mill oak, 36 inches long](https://www.lowes.com/pd/Madison-Mill-Round-Wood-Oak-Dowel-Actual-36-in-L-x-1-in-Dia/3040784) | Item 19425; model 432513 | 1 inch / 25.4 mm | None on the checked listing |

The manufacturer's [dowel page](https://www.madisonmill.com/dowels-accessories-2/) describes its products as true to size, but gives no numeric tolerance. Its [FAQ](https://www.madisonmill.com/faqs/) also provides no dimensional acceptance band. These pages do not establish minimum/maximum diameters, ovality, moisture condition or batch variation. No physical caliper measurements have been taken for this project.

The poplar listing pools reviews across multiple dowel diameters. Neither those pooled ratings nor the site's generated review summary establishes a measured 1-inch diameter range. Tolerances for another manufacturer's joinery pins must not be substituted for these retail rods.

## Dimensions to keep separate

- **Rod envelope:** measured minimum and maximum diameter, including ovality and locations along the actual rods. These values remain unknown.
- **Seat:** current CAD diameter 26.0 mm. The printed diameter also depends on the actual filament, flow, shrinkage and hole compensation.
- **Snap throat:** the unblended collar construction targets approximately 24.51 mm between rounded noses. Measure the finished/printed opening; do not treat that construction value as a production tolerance.
- **Finger section:** nominal 1.35 mm in the flexible region, with thickened bearing sectors and blended roots. Insertion strain and retained opening are separate from whole-bracket gravity FEM.

The current approximately 218° collar wrap is not itself a tolerance specification. Capture depends on the actual narrowest opening, rod diameter, finger flexibility and insertion direction. The chamfers taper out before the thin fingers so the edge finish does not consume their section.

## Fit conditions

For an initially relaxed cradle with positive geometric capture:

`smallest printed seat − largest conditioned rod > selected running clearance`

`smallest conditioned rod − largest printed throat > selected capture margin`

The largest rod and smallest throat govern required insertion opening. Half the total opening is only a symmetric-finger approximation; the integrated bracket has unequal local restraints. The seated rod should rest on the thick bearing region without holding the fingers permanently sprung apart. Confirm that the rod cannot escape after repeated insertion/removal and after the loaded temperature exposure.

No numeric production rod envelope, guaranteed insertion force, allowable snap strain or lifetime retention margin is assigned until the missing measurements are available. The 26.0 mm seat remains provisional; widening it blindly can reduce capture and bearing-location control.

## Practical measurements

Use gentle caliper pressure. At each intended bracket contact station, rotate the rod to find the minimum and maximum diameter. Repeat along each rod, including both ends and the middle; do not infer ovality from only one orientation. Record the SKU/species, finish and room condition. Measure again after any applied finish and after the rod has stabilized in the installation environment.

Print the fit coupons using the intended printer, filament and orientation before printing full brackets. Check insertion, seating, rotation, axial sliding, removal and repeat insertion. A coupon checks fit and handling; it does not establish bracket load capacity or creep life. Small-batch measurements describe that batch, not the manufacturer's complete production tolerance.
