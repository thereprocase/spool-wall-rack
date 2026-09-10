// E6: load-aligned snap saddle, concept prototype. Units mm.
// Local XY is the print bed. Local +Y is the opening / spool-contact direction.
// Retainer is monolithic; flexible fingers bend in XY.
$fn=180;

snap_seat_r=13;
finger_t=1.35;
wrap=218;
bearing_arc=80;
bearing_t=6;
root_blend_start=25;
root_blend_end=75;
root_fillet_r=2;
edge_round_r=.45;
relief_pocket_r=17.75;
snap_width=24;
coupon_width=8;
reference_spool_d=200;
snap_rod_r=12.7;
rail_half_spacing=50;
snap_radial_clearance=snap_seat_r-snap_rod_r;
snap_contact_angle=acos(rail_half_spacing/(reference_spool_d/2+snap_rod_r-snap_radial_clearance));
rear_rotation=snap_contact_angle-90;
function p(r,a)=[r*cos(a),r*sin(a)];
module sector(ri,ro,a,b){polygon(concat([for(t=[a:1:b])p(ro,t)],[p(ro,b)],[for(t=[b:-1:a])p(ri,t)],[p(ri,a)]));}
// Quintic radial transition: radius, tangent and curvature match at both ends.
function smooth5(u)=u*u*u*(10+u*(-15+6*u));
function root_weight(a)=smooth5(max(0,min(1,(root_blend_end-abs(a-270))/(root_blend_end-root_blend_start))));
function outer_r(a)=snap_seat_r+finger_t+(bearing_t-finger_t)*root_weight(a);
module rounded_profile(){
 // Concave R2 blends; convex R0.45 blends. The 1.35 mm fingers survive erosion.
 offset(r=edge_round_r,$fn=192) offset(r=-edge_round_r,$fn=192)
 offset(r=-root_fillet_r,$fn=192) offset(r=root_fillet_r,$fn=192)children();
}
module collar(){
 a=90+(360-wrap)/2;b=450-(360-wrap)/2;
 union(){
  polygon(concat([for(t=[a:.25:b])p(outer_r(t),t)],[p(outer_r(b),b)],
    [for(t=[b:-.25:a])p(snap_seat_r,t)],[p(snap_seat_r,a)]));
  // Semicircular noses tangent to the constant-thickness inner and outer arcs.
  for(t=[a,b])translate(p(snap_seat_r+finger_t/2,t))circle(r=finger_t/2,$fn=192);
 }
}
module rear_collar(){rotate(rear_rotation)collar();}
module front_collar(){mirror([1,0,0])rear_collar();}
module coupon_profile(){
 rounded_profile() union(){
  collar();
  hull()for(x=[-4,4],y=[-22,-18])translate([x,y])circle(r=3,$fn=192);
 }
}
