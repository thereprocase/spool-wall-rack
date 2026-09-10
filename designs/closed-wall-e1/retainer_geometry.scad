// E1: load-aligned snap saddle, concept prototype. Units mm.
// Local XY is the print bed. Local +Y is the opening / spool-contact direction.
// Retainer is monolithic; flexible fingers bend in XY.
$fn=180;

snap_seat_r=13;
finger_t=1.35;
wrap=218;
bearing_arc=80;
bearing_t=5;
snap_width=24;
coupon_width=8;
reference_spool_d=200;
snap_rod_r=12.7;
rail_half_spacing=75;
snap_radial_clearance=snap_seat_r-snap_rod_r;
snap_contact_angle=acos(rail_half_spacing/(reference_spool_d/2+snap_rod_r-snap_radial_clearance));
rear_rotation=snap_contact_angle-90;
function p(r,a)=[r*cos(a),r*sin(a)];
module sector(ri,ro,a,b){polygon(concat([for(t=[a:1:b])p(ro,t)],[p(ro,b)],[for(t=[b:-1:a])p(ri,t)],[p(ri,a)]));}
module collar(){
 a=90+(360-wrap)/2;b=450-(360-wrap)/2;
 union(){
  sector(snap_seat_r,snap_seat_r+finger_t,a,b);
  // Rounded noses and thick central bearing sector.
  for(t=[a,b])translate(p(snap_seat_r+finger_t/2,t))circle(r=finger_t/2);
  sector(snap_seat_r,snap_seat_r+bearing_t,270-bearing_arc/2,270+bearing_arc/2);
  // Local root fillets outside the rod seating radius.
  for(t=[270-bearing_arc/2,270+bearing_arc/2])difference(){
   translate(p(snap_seat_r+finger_t+1.2,t))circle(r=1.6);
   circle(r=snap_seat_r);
  }
 }
}
module rear_collar(){rotate(rear_rotation)collar();}
module front_collar(){mirror([1,0,0])rear_collar();}
module coupon_profile(){
 union(){collar();translate([-7,-25])square([14,9]);}
}
