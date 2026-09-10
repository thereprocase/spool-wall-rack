// Revision E11: solid exterior profile with load-aligned snaps.
// Run build_step.py for solid envelope, recessed fasteners and helper solids.
// Raw SCAD bracket is an intermediate envelope, not the released DFM solid.
// upward L-shaped bracket with continuous in-plane laminations.
// SIDE-PRINT axes: X = projection from wall, Y = height on wall, Z = bracket width.
// No assigned safe working load or creep life. Prior A/B caps are withdrawn.
// Angular structural profile; snap geometry remains smoothly curved.
wall_bottom=-32; wall_top=176;
front_lift=12;
// Broad C2 underside reinforcement, sized by verify_sections.py.
// Functional seat centers and the spool-facing outline stay fixed.
seat_extra_depth=38;
seat_spread=18;
function blend5(u)=u*u*u*(10+u*(-15+6*u));
function belly(x)=seat_extra_depth*exp(-pow((x-90)/seat_spread,2))*
 (1-blend5(max(0,min(1,(abs(x-90)-35)/20))));
profile_points=concat([[0,176],[0,-32]],
 [for(x=[35:.5:145])[x,-32-belly(x)]],
 [[190,-32],[190,7.2],[110,-2.4],[66,6],[30,48],[17.5,82],[12,108],[12,128],[18,176]]);
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
   // E11 removes the obsolete projecting lower screw-head pad.

  }
  for(c=[[rear,0],[front,front_lift]])translate(c)circle(r=seat_r);
  // Maintain >=3 mm nominal clearance to every specified rigid flange.
  for(R=[90:1:110]){
   S=sqrt(100*100+front_lift*front_lift);
   q=sqrt(pow(R+rod_d/2-clearance_d/2,2)-S*S/4);
   translate([140-front_lift*q/S,front_lift/2+100*q/S])circle(r=R+3.5);
  }
 }
}
// Fresh bearing buttresses replace all former open-saddle lips and circular nodes.
module bearing_patch(){sector(snap_seat_r+2.5,snap_seat_r+bearing_t,245,295);}
module bearing_bridge(x,is_front=false){
 hull(){
  translate([x,-24])circle(r=6);
  translate([x,is_front ? front_lift : 0])if(is_front)rotate(front_rotation)bearing_patch();
  else rotate(rear_rotation)bearing_patch();
 }
}
module seat_structure(){
 union(){
  difference(){arm_outline();for(c=[[rear,0],[front,front_lift]])translate(c)circle(r=relief_pocket_r);}
  bearing_bridge(rear);
  bearing_bridge(front,true);
 }
}
module blended_outline(){
 rounded_profile() union(){
  seat_structure();
  // Larger rigid shoulder blends; retain the relief pockets around the snaps.
  intersection(){
   difference(){
    offset(r=-6,$fn=192)offset(r=6,$fn=192)seat_structure();
    for(c=[[rear,0],[front,front_lift]])translate(c)circle(r=relief_pocket_r);
   }
   // Localize the addition to the rear shoulders; other body corners stay R2.
   translate([55,-25])square([70,70]);
  }
  translate([rear,0])rear_collar();
  translate([front,front_lift])front_collar();
 }
}
// Square wall-side end lands keep the back coplanar for its full height.
// Exposed body and snap edges retain their existing blends.
module outline(){union(){blended_outline();translate([0,wall_bottom])square([4,wall_top-wall_bottom]);}}
// Final solid body, fastener features and helper slabs are built by:
// fastener_geometry.py + build_step.py. Do not export an unfinished full bracket here.
if(part=="profile")outline();
if(part=="bracket")assert(false,"Build the finished E11 solid with build_step.py");
