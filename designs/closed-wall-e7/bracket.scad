// Revision E7: angular profile, load-aligned snaps, 2.4 mm perimeter.
// Run finish_cad.py for compartments, recessed fasteners and finished chamfers.
// Raw SCAD bracket is an intermediate envelope, not the released DFM solid.
// upward L-shaped bracket with continuous in-plane laminations.
// SIDE-PRINT axes: X = projection from wall, Y = height on wall, Z = bracket width.
// No assigned safe working load or creep life. Prior A/B caps are withdrawn.
// Angular structural profile; snap geometry remains smoothly curved.
wall_bottom=-32; wall_top=176;
profile_points=[[0,176],[0,-32],[190,-32],[190,-4],[110,-4],[66,6],[24,114],[20,176]];
include <retainer_geometry.scad>
$fn=128;
part="profile"; // profile | hollow_profile; final DFM solids are built by finish_cad.py
rod_d=25.4;
clearance_d=.6;
rear=90;
front=190;
width=24;
side_wall=2.4;       // Proposed thicker structural perimeter; toolpath count requires slicing.
layer=.2;
face=1.2;             // Six 0.20 mm layers, including each internal plate.
internal_plates=2;     // 1 => 2 cavities; 2 => 3; 3 => 4.
fixings=[164,40];
wall_depth=20;
seat_r=(rod_d+clearance_d)/2;
plate_pitch=(width-face)/(internal_plates+1);
air_depth=(width-(internal_plates+2)*face)/(internal_plates+1);
assert(air_depth>0,"Too many plates for selected width");
assert(abs(air_depth/layer-round(air_depth/layer))<0.00001,"Align cavity heights to layers; use width=24.4 with 3 internal plates");
module capsule(a,b,d){hull(){translate(a)circle(d=d);translate(b)circle(d=d);}}
module arm_outline(){
 difference(){
  offset(r=2) offset(r=-2) offset(r=-2) offset(r=2) union(){
   polygon(profile_points);
   // E7 removes the obsolete projecting lower screw-head pad.

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
module hollow_profile(){offset(delta=-side_wall)outline();}
// Final void compartments and fastener features have one authoritative definition:
// dfm_geometry.py + finish_cad.py. Do not export an unfinished full bracket here.
if(part=="profile")outline();
if(part=="hollow_profile")hollow_profile();
if(part=="bracket")assert(false,"Build the finished E7 solid with finish_cad.py");
