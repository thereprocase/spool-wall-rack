include <retainer_geometry.scad>
part="coupon";
if(part=="coupon")translate([21,27,0])linear_extrude(coupon_width)coupon_profile();
if(part=="collar")linear_extrude(snap_width)collar();
if(part=="profile")collar();
