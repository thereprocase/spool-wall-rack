"""New EF body and aligned modifiers, preserving actual G bearing/capture CAD."""
from pathlib import Path
import hashlib
import json
import sys
import time
import cadquery as cq
import numpy as np
import vtk
from scipy.spatial import cKDTree
from shapely.geometry import shape, box

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / 'designs/rev-g'))
from build_body import prism
from repair_stl import repair
import repair_stl as mesh_tools
import layout
sys.path.insert(0, str(ROOT / 'designs/closed-wall-e13'))
from fastener_geometry import FIXINGS, LAND, access_profile, x_prism


def printed(body):
    return body.rotate((0,0,0), (0,0,1), 180).translate((250,182,0))


def repair_modifier(path, expected_components):
    """Same bounded STL weld, with disconnected modifier solids permitted."""
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    m = mesh_tools.read(path)
    p, f, edges = mesh_tools.boundary(m)
    clean = vtk.vtkCleanPolyData(); clean.SetInputData(m)
    clean.ToleranceIsAbsoluteOn(); clean.SetAbsoluteTolerance(mesh_tools.TOLERANCE_MM); clean.Update()
    tri = vtk.vtkTriangleFilter(); tri.SetInputData(clean.GetOutput())
    tri.PassLinesOff(); tri.PassVertsOff(); tri.Update()
    out = tri.GetOutput(); q, g, bad = mesh_tools.boundary(out)
    assert len(bad) == 0
    movement = float(cKDTree(q).query(p)[0].max())
    assert movement <= mesh_tools.TOLERANCE_MM*1.001
    delta = abs(mesh_tools.signed_volume(p,f)-mesh_tools.signed_volume(q,g))
    assert delta < .1 and delta/abs(mesh_tools.signed_volume(q,g)) < 1e-6
    conn = vtk.vtkPolyDataConnectivityFilter(); conn.SetInputData(out)
    conn.SetExtractionModeToAllRegions(); conn.Update()
    actual = conn.GetNumberOfExtractedRegions()
    assert actual == expected_components, (path.name, actual, expected_components)
    writer = vtk.vtkSTLWriter(); writer.SetFileName(str(path)); writer.SetFileTypeToBinary(); writer.SetInputData(out)
    assert writer.Write() == 1
    _, written, bad = mesh_tools.boundary(mesh_tools.read(path)); assert len(bad) == 0
    return dict(file=path.name, weld_tolerance_mm=mesh_tools.TOLERANCE_MM,
                maximum_vertex_movement_mm=movement, input_boundary_edges=len(edges), output_boundary_edges=0,
                connected_components=actual, expected_CAD_solids=expected_components,
                input_triangles=len(f), output_triangles=len(written), signed_volume_change_mm3=delta,
                input_sha256=original_hash, output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                closed_after_roundtrip=True, STEP_modified=False,
                scope='Modifier solids only. Disconnected dense regions are allowed; the printable body must remain one component.')


def main():
    start = time.perf_counter()
    geometries = {v['properties']['name']: shape(v['geometry'])
                  for v in json.loads((D / 'geometry.geojson').read_text())['features']}
    outline, protected = geometries['hybrid_body_projection'], geometries['protected_G_interfaces']
    source = ROOT / 'designs/rev-g/body-only.step'
    original = cq.importers.importStep(str(source)).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
    mask = prism(protected, -1, 26)
    body = prism(outline, 0, 24).cut(mask).fuse(original.intersect(mask)).clean()
    print('new frame and original bearing/capture volumes joined', flush=True)
    for y in FIXINGS:
        body = body.cut(x_prism(access_profile(y), LAND, 250))
        bore = access_profile(y, radius=2.6, roof_z=12+2.6*2**.5, round_top=0)
        body = body.cut(x_prism(bore, -1, LAND+1.01))
    body = body.clean()
    assert body.isValid() and len(body.Solids()) == 1, ('body', body.isValid(), len(body.Solids()))
    original_interface = original.intersect(mask)
    actual_interface = body.intersect(mask)
    interface_xor = actual_interface.cut(original_interface).Volume() + original_interface.cut(actual_interface).Volume()
    assert interface_xor < 1e-5, interface_xor
    moulding = cq.Solid.makeBox(25.4, 968, 26, cq.Vector(0, -1000, -1))
    moulding_overlap = body.intersect(moulding).Volume()
    assert moulding_overlap < 1e-6, moulding_overlap
    washer = []
    for y in FIXINGS:
        outer = cq.Solid.makeCylinder(6.5, 3.4, cq.Vector(.1,y,12), cq.Vector(1,0,0))
        bore = cq.Solid.makeCylinder(2.75, 3.4, cq.Vector(.1,y,12), cq.Vector(1,0,0))
        ring = outer.cut(bore)
        fraction = body.intersect(ring).Volume() / ring.Volume()
        driver_overlap = body.intersect(x_prism(access_profile(y), LAND+.01, 250)).Volume()
        assert fraction >= .98 and driver_overlap < 1e-6, (y, fraction, driver_overlap)
        washer.append(dict(axis_YZ_mm=[y,12], support_fraction=fraction, driver_overlap_mm3=driver_overlap))
    delivered = printed(body)
    cq.exporters.export(delivered, str(D / 'body-only.step'))
    cq.exporters.export(body.copy(), str(D / 'body-mounted.stl'), tolerance=.02, angularTolerance=.08)
    cq.exporters.export(delivered.copy(), str(D / 'body-only.stl'), tolerance=.02, angularTolerance=.08)
    body_mesh = repair(D / 'body-only.stl')
    roundtrip = cq.importers.importStep(str(D / 'body-only.step')).val()
    assert roundtrip.isValid() and len(roundtrip.Solids()) == 1
    assert abs(roundtrip.Volume()-body.Volume()) < 1e-4
    print('body exported, one valid solid; interface and moulding checks pass', flush=True)
    params = json.loads((D / 'selected-layout.json').read_text())
    # Use actual new body boundaries to define reinforcement, rather than the
    # frozen G outline. Air-only connections make helpers easy to select.
    halo = outline.buffer(1.2, quad_segs=8).difference(outline.buffer(-.05, quad_segs=8))
    dense = layout.dense_region(outline, params).union(halo).union(box(-16,65,.1,75))
    bands = layout.plate_bands(params)
    helper_defs = [('dense-chords-and-seats', dense, 0, 24),
                   ('rib-plane-lower', outline.union(box(-16,105,1,115)), bands[1][0], bands[1][1]-bands[1][0]),
                   ('rib-plane-upper', outline.union(box(-16,125,1,135)), bands[2][0], bands[2][1]-bands[2][0])]
    assembly = cq.Assembly(name='EF-HYBRID-BODY-AND-MODIFIERS')
    assembly.add(delivered, name='BODY-print', color=cq.Color(.23,.52,.54))
    rows = []
    for name, region, z, h in helper_defs:
        helper = prism(region, z, h)
        if name == 'dense-chords-and-seats':
            for _, profile, length in layout.tunnel_saddles(params):
                saddle = x_prism(profile, 0, length).intersect(cq.Solid.makeBox(250,280,24,cq.Vector(-1,-80,0)))
                helper = helper.fuse(saddle)
        helper = helper.clean()
        assert helper.isValid() and all(s.isValid() for s in helper.Solids())
        part = printed(helper)
        cq.exporters.export(part, str(D / (name+'.step')))
        cq.exporters.export(part.copy(), str(D / (name+'.stl')), tolerance=.02, angularTolerance=.08)
        mesh_check = repair_modifier(D / (name+'.stl'), len(helper.Solids()))
        reread = cq.importers.importStep(str(D / (name+'.step'))).val()
        assert reread.isValid() and abs(reread.Volume()-helper.Volume()) < 1e-3
        assembly.add(part, name=name+'-MODIFIER-100pct', color=cq.Color(.88,.63,.22))
        rows.append(dict(name=name, valid=True, solid_count=len(helper.Solids()),
                         helper_volume_mm3=helper.Volume(), body_intersection_mm3=helper.intersect(body).Volume(),
                         z_min_mm=z, z_max_mm=z+h, role='100% infill modifier; never a printable part', STL_check=mesh_check))
        print('helper exported', name, flush=True)
    assembly.save(str(D / 'bracket-with-modifiers.step'))
    combined = cq.importers.importStep(str(D / 'bracket-with-modifiers.step')).val()
    assert all(s.isValid() for s in combined.Solids())
    assert len(combined.Solids()) == 1 + sum(r['solid_count'] for r in rows)
    report = dict(status='PASS_CAD_AND_NOMINAL_INTERFACE_CHECKS; PRINT_AND_MECHANICS_UNQUALIFIED',
                  body_valid=True, body_solids=1, body_CAD_envelope_volume_mm3=body.Volume(),
                  G_source_STEP_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  protected_interface_symmetric_difference_mm3=interface_xor,
                  crown_moulding_keepout_overlap_mm3=moulding_overlap,
                  fixed_rod_centers_XY_mm=[[90,0],[190,12]], fixing_checks=washer,
                  installed_bounds_mm=[getattr(body.BoundingBox(), k) for k in ['xmin','ymin','zmin','xmax','ymax','zmax']],
                  body_print_bounds_mm=[getattr(delivered.BoundingBox(), k) for k in ['xmin','ymin','zmin','xmax','ymax','zmax']],
                  body_STL_check=body_mesh, helpers=rows, assembly_solid_count=len(combined.Solids()),
                  elapsed_seconds=time.perf_counter()-start,
                  note='The frame and seat backing are new. Original G bearing bores and upper capture geometry are preserved by exact STEP intersection. CAD volume is not printed volume. New member broad faces are unchamfered in this first prototype.')
    (D / 'cad-verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
