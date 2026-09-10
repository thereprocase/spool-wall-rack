// Revision E8: solid exterior profile with load-aligned snaps.
// Run build_step.py for solid envelope, recessed fasteners and helper solids.
// Raw SCAD bracket is an intermediate envelope, not the released DFM solid.
// upward L-shaped bracket with continuous in-plane laminations.
// SIDE-PRINT axes: X = projection from wall, Y = height on wall, Z = bracket width.
// No assigned safe working load or creep life. Prior A/B caps are withdrawn.
// Angular structural profile; snap geometry remains smoothly curved.
wall_bottom=-32; wall_top=176;
profile_points=[[0,176],[0,-32],[190,-32],[190,-4],[110,-4],[66,6],[24,114],[20,176]];
include <retainer_geometry.scad>
$fn=128;
part="profile"; // profile only; final STEP assembly is built by build_step.py
rod_d=25.4;
clearance_d=.6;
rear=90;
front=190;
width=24;
seat_r=(rod_d+clearance_d)/2;
module capsule(a,b,d){hull(){translate(a)circle(d=d);translate(b)circle(d=d);}}
module arm_outline(){
 difference(){
  offset(r=2) offset(r=-2) offset(r=-2) offset(r=2) union(){
   polygon(profile_points);
   // E8 removes the obsolete projecting lower screw-head pad.

  }
  for(x=[rear,front])translate([x,0])circle(r=seat_r);
  // Maintain >=3 mm nominal clearance to every specified rigid flange.
  for(R=[90:1:110]){
   h=sqrt(pow(R+rod_d/2-clearance_d/2,2)-50*50);
   translate([(rear+front)/2,h])circle(r=R+3.5);
  }
 }
}
// Fresh bearing buttresses replace all former open-saddle lips and circular nodes.
module bearing_patch(){sector(snap_seat_r+2.5,snap_seat_r+bearing_t,245,295);}
module bearing_bridge(x,is_front=false){
 hull(){
  translate([x,-24])circle(r=6);
  translate([x,0])if(is_front)mirror([1,0,0])rotate(rear_rotation)bearing_patch();
  else rotate(rear_rotation)bearing_patch();
 }
}
module blended_outline(){
 rounded_profile() union(){
  difference(){arm_outline();for(x=[rear,front])translate([x,0])circle(r=relief_pocket_r);}
  bearing_bridge(rear);
  bearing_bridge(front,true);
  translate([rear,0])rear_collar();
  translate([front,0])front_collar();
 }
}
// Square wall-side end lands keep the back coplanar for its full height.
// Exposed body and snap edges retain their existing blends.
module outline(){union(){blended_outline();translate([0,wall_bottom])square([4,wall_top-wall_bottom]);}}
// Final solid body, fastener features and helper slabs are built by:
// fastener_geometry.py + build_step.py. Do not export an unfinished full bracket here.
if(part=="profile")outline();
if(part=="bracket")assert(false,"Build the finished E8 solid with build_step.py");
