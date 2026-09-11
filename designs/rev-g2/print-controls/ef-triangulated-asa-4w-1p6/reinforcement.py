"""Rounded tapered helper strips joining specified body load-path anchors."""
from shapely.geometry import Point
from shapely import union_all

def tapered_regions(params):
    regions=[]
    for row in params['local_reinforcement']:
        points=row['points_XY_mm'];radii=row['radii_mm'];assert len(points)==len(radii)
        disks=[Point(p).buffer(r,quad_segs=16) for p,r in zip(points,radii)]
        region=union_all([union_all([a,b]).convex_hull for a,b in zip(disks,disks[1:])])
        assert region.is_valid and region.geom_type=='Polygon';regions.append(region)
    return regions
