"""Manufacturing geometry in mounted coordinates; printer build axis is Z."""
import math
import cadquery as cq
from shapely.geometry import Polygon, Point, box

FIXINGS=[164,40]
LAND=3.6
CELL=10.0
DIVIDER=1.2

def polygons(shape):
    if shape.is_empty:return []
    if shape.geom_type=='Polygon':return [shape]
    return [p for g in shape.geoms for p in polygons(g)]

def cell_footprints(contours):
    seed=Polygon(contours[0],holes=contours[1:]).buffer(0)
    out=[]
    # Fixed lattice includes both X and Y directions: no uncontrolled long roof.
    for ix in range(-1,20):
        for iy in range(-4,17):
            x=ix*(CELL+DIVIDER);y=iy*(CELL+DIVIDER)
            rounded=box(x+2,y+2,x+CELL-2,y+CELL-2).buffer(2,quad_segs=8)
            for p in polygons(seed.intersection(rounded)):
                # Drop tiny air slivers; this adds solid rather than trapping thin holes.
                if p.area>.8 and min(p.bounds[2]-p.bounds[0],p.bounds[3]-p.bounds[1])>.8:
                    out.append(p)
    return out

def access_profile(y,radius=8,roof_z=22.4,round_top=.6):
    """YZ profile: circular clearance with tangent 45-degree shoulders and short roof cap."""
    z=12;r=radius;d=r/math.sqrt(2)
    circle=Point(y,z).buffer(r,quad_segs=24)
    top=Polygon([(y-d,z+d),(y+d,z+d),(y,z+r*math.sqrt(2))])
    shape=circle.union(top).intersection(box(y-r-1,-1,y+r+1,roof_z))
    if round_top:
        shape=shape.buffer(-round_top,quad_segs=12).buffer(round_top,quad_segs=12).union(circle)
    return shape

def x_prism(profile,x,length):
    w=cq.Wire.makePolygon([cq.Vector(x,y,z) for y,z in list(profile.exterior.coords)[:-1]],close=True)
    return cq.Solid.extrudeLinear(w,[],cq.Vector(length,0,0))
