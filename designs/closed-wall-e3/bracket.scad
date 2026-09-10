// Revision E3: load-aligned snap seats, 2.4 mm perimeter; based on D.
// upward L-shaped bracket with continuous in-plane laminations.
// SIDE-PRINT axes: X = projection from wall, Y = height on wall, Z = bracket width.
// No assigned safe working load or creep life. Prior A/B caps are withdrawn.
include <../closed-wall-d/profile_points.scad>
include <retainer_geometry.scad>
$fn=128;
part="bracket"; // bracket | profile | hollow_profile | stack_section | exploded | bridge_coupon
rod_d=25.4;
clearance_d=.6;
rear=76;
front=226;
width=24;
side_wall=2.4;       // Proposed thicker structural perimeter; toolpath count requires slicing.
layer=.2;
face=1.2;             // Six 0.20 mm layers, including each internal plate.
internal_plates=2;     // 1 => 2 cavities; 2 => 3; 3 => 4.
fixings=[138,12];
wall_depth=20;
seat_r=(rod_d+clearance_d)/2;
plate_pitch=(width-face)/(internal_plates+1);
air_depth=(width-(internal_plates+2)*face)/(internal_plates+1);
assert(air_depth>0,"Too many plates for selected width");
assert(abs(air_depth/layer-round(air_depth/layer))<0.00001,"Align cavity heights to layers; use width=24.4 with 3 internal plates");
module capsule(a,b,d){hull(){translate(a)circle(d=d);translate(b)circle(d=d);}}
module arm_outline(){
 difference(){
  offset(r=-5) offset(r=5) union(){
   polygon(profile_points);
   // Flat front bearing face for the lower screw washer.
   capsule([50,2],[50,22],20);

  }
  for(x=[rear,front])translate([x,0])circle(r=seat_r);
  // Maintain >=3 mm nominal clearance to every specified rigid flange.
  for(R=[90:1:110]){
   h=sqrt(pow(R+rod_d/2,2)-75*75)-clearance_d/2;
   translate([(rear+front)/2,h])circle(r=R+3);
  }
 }
}
// Fresh bearing buttresses replace all former open-saddle lips and circular nodes.
module bearing_patch(){sector(snap_seat_r+2.5,snap_seat_r+bearing_t,245,295);}
module bearing_bridge(x,is_front=false){
 hull(){
  translate([x,-37])circle(r=7);
  translate([x,0])if(is_front)mirror([1,0,0])rotate(rear_rotation)bearing_patch();
  else rotate(rear_rotation)bearing_patch();
 }
}
module outline(){
 rounded_profile() union(){
  difference(){arm_outline();for(x=[rear,front])translate([x,0])circle(r=relief_pocket_r);}
  bearing_bridge(rear);
  bearing_bridge(front,true);
  translate([rear,0])rear_collar();
  translate([front,0])front_collar();
 }
}
module hollow_profile(){offset(delta=-side_wall)outline();}
module screw_holes(){for(y=fixings)translate([-1,y,width/2])rotate([0,90,0])cylinder(d=5.5,h=75);}
module sleeve_protection(){
 // Continuous sleeve joins the plates at each screw, without a transverse grid.
 for(y=fixings)translate([-1,y,width/2])rotate([0,90,0])cylinder(d=5.5+2*side_wall,h=75);
}
module air_volumes(){
 difference(){
  for(i=[0:internal_plates])translate([0,0,face+i*plate_pitch])
   linear_extrude(air_depth)hollow_profile();
  sleeve_protection();
 }
}
module bracket(){difference(){linear_extrude(width)outline();air_volumes();screw_holes();}}
if(part=="bracket") {
 // One part on P1S, broad side on bed, rotated 180 deg to clear front-left exclusion.
 translate([250,156,0])rotate([0,0,180])bracket();
}
if(part=="profile")outline();
if(part=="hollow_profile")hollow_profile();
if(part=="stack_section")intersection(){bracket();translate([105,-95,-1])cube([4,100,width+2]);}
if(part=="exploded") {
 // Visual explanation only, not an assembly or printable part.
 for(i=[0:internal_plates+1])color(i==0||i==internal_plates+1?"teal":"orange")
  translate([0,0,i*14])linear_extrude(face)outline();
}
if(part=="bridge_coupon") {
 // Actual root section, 90 mm in X, with the exact stacked cavities and faces.
 intersection(){bracket();translate([18,-95,-1])cube([90,92,width+2]);}
}
if(part=="arm_section") intersection(){bracket();translate([-1,-95,-1])cube([126,260,26]);}
