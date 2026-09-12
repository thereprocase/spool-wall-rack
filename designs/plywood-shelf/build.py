"""Mirrored solid-triangle plywood shelf brackets. Millimetres.
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
outline = [(0,-T),(D,-T),(D,P["toe_depth"]),(P["toe_depth"],H),(0,H)]
left = cq.Workplane("XY").polyline(outline).close().extrude(W)
left = left.union(box(0,-T,W,D,T,L))
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
assert bearing_area_left > D*(L-gap)*0.98
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

assembly=cq.Assembly(name="plywood_shelf")
assembly.add(left,name="left",color=cq.Color(0.22,0.28,0.31))
assembly.add(right.translate((0,0,S)),name="right",color=cq.Color(0.22,0.28,0.31))
assembly.add(ply,name="plywood",color=cq.Color(0.72,0.55,0.33))
assembly.save(str(OUT/"shelf-assembly.step"))

report={"status":"CAD checks passed; unsliced and physically unqualified",
        "revision":P["revision"],
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
