"""PRELIMINARY V4 DRAFT — NOT EXECUTED AT CHECKPOINT.
Closet model remains uninspected. See ../PROGRESS.md before use.
Mirrored solid-triangle plywood shelf brackets. Millimetres.
CAD/fit checks only: this does not establish structural capacity or printability.
Installed axes: X away from wall, Y up, Z along shelf.
"""
import json
import math
from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / "parameters.json").read_text())
OUT = ROOT / "exports"
OUT.mkdir(exist_ok=True)
D, H, W = P["arm_depth"], P["wall_height"], P["body_width"]

def box(x, y, z, dx, dy, dz):
    return cq.Workplane("XY").box(dx, dy, dz, centered=False).translate((x,y,z))

def cylinder(origin, direction, diameter, length):
    return cq.Workplane("XY").newObject([
        cq.Solid.makeCylinder(diameter/2, length, cq.Vector(*origin), cq.Vector(*direction))
    ])

def teardrop(x, y, diameter, length):
    # Circle plus tangent 45-degree roof; roof points toward print +Z.
    r = diameter / 2
    c = W / 2
    circle = cq.Workplane("YZ", origin=(x,0,0)).center(y,c).circle(r).extrude(length)
    roof = (cq.Workplane("YZ", origin=(x,0,0))
            .polyline([(y-r/math.sqrt(2),c+r/math.sqrt(2)),
                       (y,c+r*math.sqrt(2)),
                       (y+r/math.sqrt(2),c+r/math.sqrt(2))])
            .close().extrude(length))
    return circle.union(roof)

# Side triangles rise above Y=0, the plywood underside datum.
# Only the 12 mm bearing ledge extends beneath the shelf.
L, T = P["ledge_width"], P["ledge_thickness"]
assert P["stud_spacing"] > W + 2*L
assert 0 < P["retention_pilot_depth"] < T
assert all(y > P["plywood_thickness"] for y in P["stud_hole_y"])
C, R = P["molding_clearance_depth"], P["molding_vertical_relief"]
assert C >= P["molding_projection"]
assert C < D
outline = [(0,R),(C,R),(C,-T),(D,-T),(D,P["toe_depth"]),(P["toe_depth"],H),(0,H)]
left = cq.Workplane("XY").polyline(outline).close().extrude(W)
left = left.union(box(C,-T,W,D-C,T,L))
cap_y = P["plywood_thickness"] + P["retainer_clearance"]
rear_cap = box(0,cap_y,W,P["retainer_reach"],
               P["retainer_thickness"],P["retainer_inboard"])
left = left.union(rear_cap)
retention_z = W + L/2
for y in P["stud_hole_y"]:
    left = left.cut(teardrop(-1,y,P["stud_hole_diameter"],D+2))
    left = left.cut(teardrop(P["wall_land"],y,P["access_diameter"],D+2))
for x in P["retention_x"]:
    left = left.cut(cylinder((x,-P["retention_pilot_depth"],retention_z),
                             (0,1,0),P["retention_pilot_diameter"],
                             P["retention_pilot_depth"]+1))
left = left.clean()
right = left.mirror("XY", basePointVector=(0,0,W/2))
S = P["stud_spacing"]
gap = P["plywood_clearance"]
ply_start = W + gap
ply_length = S - W - 2*gap
ply = box(0,0,ply_start,
          P["shelf_depth"],P["plywood_thickness"],ply_length)

def solids_volume(obj):
    return sum(s.Volume() for s in obj.solids().vals())

def valid_single(obj):
    assert obj.val().isValid(), "Invalid BRep"
    assert len(obj.solids().vals()) == 1, "Disconnected bracket"

def on_bed(obj, flip=False):
    # Mirrored right bracket prints with its outer face down too.
    if flip:
        obj = obj.rotate((0,0,0),(1,0,0),180)
    choices=[]
    for deg in range(0,3600):
        angle=deg/10
        candidate=obj.rotate((0,0,0),(0,0,1),angle)
        b=candidate.val().BoundingBox()
        choices.append((max(b.xlen,b.ylen),angle))
    _, angle=min(choices)
    part=obj.rotate((0,0,0),(0,0,1),angle)
    b=part.val().BoundingBox()
    part=part.translate(((P["bed"]-b.xlen)/2-b.xmin,
                         (P["bed"]-b.ylen)/2-b.ymin,-b.zmin))
    b=part.val().BoundingBox()
    assert max(b.xlen,b.ylen)+2*P["brim"] < P["bed"]
    assert b.zlen < P["bed"]
    return part, dict(rotation_degrees=angle,
                      bounding_box_mm=[b.xlen,b.ylen,b.zlen],
                      nominal_bed_and_brim_pass=True,
                      machine_exclusions_and_actual_slice_checked=False)

valid_single(left)
valid_single(right)
assert abs(solids_volume(left)-solids_volume(right)) < 1e-5
assert solids_volume(left.intersect(ply)) < 1e-5
assert solids_volume(right.translate((0,0,S)).intersect(ply)) < 1e-5
assert abs(ply.val().BoundingBox().xmin) < 1e-6, "Plywood must touch wall X=0"
assert abs(ply.val().BoundingBox().xmax-P["shelf_depth"]) < 1e-6
assert left.val().BoundingBox().ymin >= -T - 1e-6
assert left.val().BoundingBox().ymax >= H - 1e-6
# Plywood has real underside bearing on both inward-facing ledges.
bearing_probe = ply.translate((0,-0.01,0))
bearing_area_left = solids_volume(left.intersect(bearing_probe))/0.01
bearing_area_right = solids_volume(right.translate((0,0,S)).intersect(bearing_probe))/0.01
assert bearing_area_left > (D-C)*(L-gap)*0.98
assert abs(bearing_area_left-bearing_area_right) < 1e-3
# Straight driver access from the front to each recessed washer seat.
for y in P["stud_hole_y"]:
    tool=cylinder((P["wall_land"]+0.01,y,W/2),(1,0,0),18.0,D+10)
    assert solids_volume(left.intersect(tool)) < 1e-5
    shank=cylinder((-1,y,W/2),(1,0,0),6.0,P["wall_land"]+2)
    assert solids_volume(left.intersect(shank)) < 1e-5
# A retained pilot requires continuous printed plastic around its full depth.
for x in P["retention_x"]:
    ring=cylinder((x,-P["retention_pilot_depth"],retention_z),(0,1,0),6,
                  P["retention_pilot_depth"]).cut(
         cylinder((x,-P["retention_pilot_depth"],retention_z),(0,1,0),
                  P["retention_pilot_diameter"],P["retention_pilot_depth"]))
    assert solids_volume(ring.cut(left)) < 1e-5


# Molding top is Y=0. Only the projection is supplied; height is illustrative.
molding = box(0,-P["molding_context_height"],-30,
              P["molding_projection"],P["molding_context_height"],S+W+60)
keepout = box(0,-T-1,-30,C,T+1,S+W+60)
right_installed = right.translate((0,0,S))
assert solids_volume(left.intersect(keepout)) < 1e-5
assert solids_volume(right_installed.intersect(keepout)) < 1e-5
molding_bearing_area = solids_volume(molding.intersect(bearing_probe))/0.01
assert abs(molding_bearing_area-P["molding_projection"]*ply_length) < 1e-3

def tilted_board(angle, slide=0):
    theta=math.radians(angle)
    # Rear bottom slides on Y=0; rear top remains against X=0 at slide=0.
    # Rotating about a fixed bottom corner at X=0 would drive the top into the wall.
    return (ply.rotate((0,0,0),(0,0,1),angle)
            .translate((P["plywood_thickness"]*math.sin(theta)+slide,0,0)))

tilt=P["insertion_tilt_degrees"]
# Bound the board's top beneath the rear cap for every angle in [0,tilt].
# y_top(x) = t*cos(theta) + x*tan(theta), at slide=0.
# A conservative interval bound uses cos(theta)<=1 and tan(theta)<=tan(tilt).
# Also evaluate the actual continuous maximum by its stationary points.
a=P["retainer_reach"];t=P["plywood_thickness"]
candidates=[0,math.radians(tilt)]
# dy/dtheta = -t*sin(theta) + a/cos(theta)^2.
# Search derivative roots with a fixed bracket then bisect; endpoints retained.
def deriv(q): return -t*math.sin(q)+a/math.cos(q)**2
for i in range(100):
    lo=math.radians(tilt)*i/100
    hi=math.radians(tilt)*(i+1)/100
    if deriv(lo)*deriv(hi)<0:
        for _ in range(50):
            mid=(lo+hi)/2
            if deriv(lo)*deriv(mid)<=0: hi=mid
            else: lo=mid
        candidates.append((lo+hi)/2)
max_board_top=max(t*math.cos(q)+a*math.tan(q) for q in candidates)
cap_vertical_clearance=cap_y-max_board_top
assert cap_vertical_clearance > 0.5
motion_cases=[]
for step in range(26):
    motion_cases.append(("slide",tilt,P["insertion_slide_mm"]*(25-step)/25))
for step in range(61):
    motion_cases.append(("lower",tilt*(60-step)/60,0))
max_front=max_top=0
for phase,angle,slide in motion_cases:
    moving=tilted_board(angle,slide)
    b=moving.val().BoundingBox()
    assert b.xmin >= -1e-6 and b.ymin >= -1e-6
    for obstacle in (left,right_installed,molding):
        assert solids_volume(moving.intersect(obstacle)) < 1e-5, (phase,angle,slide)
    max_front=max(max_front,b.xmax)
    max_top=max(max_top,b.ymax)
motion_receipt=dict(sampled_positions=len(motion_cases),
                    slide_then_lower=True,
                    maximum_tilt_degrees=tilt,
                    wall_and_obstacle_checks_pass=True,
                    retainer_vertical_clearance_bound_mm=cap_vertical_clearance,
                    maximum_front_x_mm=max_front,maximum_board_y_mm=max_top,
                    actual_closet_model_checked=False)

assembly=cq.Assembly(name="plywood_shelf")
assembly.add(left,name="left",color=cq.Color(0.22,0.28,0.31))
assembly.add(right.translate((0,0,S)),name="right",color=cq.Color(0.22,0.28,0.31))
assembly.add(ply,name="plywood",color=cq.Color(0.72,0.55,0.33))
assembly.save(str(OUT/"shelf-assembly.step"))
# Separate context assembly keeps the illustrative trim out of print exports.
context=cq.Assembly(name="shelf_with_molding_context")
context.add(left,name="left")
context.add(right_installed,name="right")
context.add(ply,name="plywood")
context.add(molding,name="molding_reference_only")
context.save(str(OUT/"shelf-with-molding-context.step"))

report={"status":"CAD checks passed; unsliced and physically unqualified",
        "revision":P["revision"],
        "molding_clearance_depth_mm":C,"molding_clearance_pass":True,
        "rear_molding_bearing_area_mm2":molding_bearing_area,
        "installation_motion":motion_receipt,
        "above_shelf_height_mm":H,"below_shelf_ledge_mm":T,
        "plywood_bearing_area_mm2":[bearing_area_left,bearing_area_right],
        "parameters":P,"plywood_cut_mm":[ply_length,P["shelf_depth"],P["plywood_thickness"]],
        "front_overhang_mm":P["shelf_depth"]-D,
        "plywood_wall_gap_mm":ply.val().BoundingBox().xmin,
        "wall_flush_pass":True,
        "mirrored_volume_match":True,"plywood_interference_pass":True,
        "three_straight_driver_paths_pass":True,"retention_pilot_backing_pass":True,
        "parts":{}}
for hand,body in [("left",left),("right",right)]:
    part,check=on_bed(body,hand=="right")
    cq.exporters.export(body,str(OUT/f"{hand}-installed.step"))
    cq.exporters.export(part,str(OUT/f"{hand}-print.step"))
    cq.exporters.export(part,str(OUT/f"{hand}-print.stl"),tolerance=0.05,angularTolerance=0.1)
    # Whole-body helper explicitly specifies a conservative 100% filled first trial.
    helper=cq.Assembly(name=f"{hand}_body_and_helper")
    helper.add(part,name="body")
    helper.add(part,name="whole_body_100_percent_modifier")
    helper.save(str(OUT/f"{hand}-with-helper.step"))
    cq.exporters.export(part,str(OUT/f"{hand}-100-percent-helper.step"))
    check["solid_CAD_volume_cm3"]=solids_volume(body)/1000
    report["parts"][hand]=check
(OUT/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
