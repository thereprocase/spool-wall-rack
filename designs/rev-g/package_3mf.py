"""Geometry/part-settings handoff: body plus three non-printing Orca modifiers.

No printer or filament preset, G-code, credentials or external resources.
"""
from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET,hashlib,sys
import numpy as np
D=Path(__file__).resolve().parent
if len(sys.argv)>1:D=Path(sys.argv[1]).resolve()
CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
BAMBU='http://schemas.bambulab.com/package/2021'
ET.register_namespace('',CORE);ET.register_namespace('BambuStudio',BAMBU)
N=lambda s:'{'+CORE+'}'+s

def stl(path):
    data=path.read_bytes();count=int.from_bytes(data[80:84],'little')
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    assert len(data)==84+50*count
    triangles=np.frombuffer(data,offset=84,dtype=dtype,count=count)['vertices']
    points,index=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
    return points,index.reshape(-1,3)

def xml(root):return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def main():
    params=json.loads((D/'selected-layout.json').read_text())
    names=['body-only','dense-chords-and-seats','rib-plane-lower','rib-plane-upper']
    model=ET.Element(N('model'),{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US','xmlns:BambuStudio':BAMBU})
    # Identify this generator truthfully. OrcaSlicer-* marks a complete native
    # project; its v2.4.2 CLI dereferences printer/filament settings immediately
    # on that path, before --load-settings, so it requires a full preset bundle.
    # Generic model import still reads model_settings.config and volume roles.
    for key,value in [('Application','Spool rack geometry packager'),('BambuStudio:3mfVersion','1'),('Title','Rev G geometry and modifiers'),('Description','Model-only prototype handoff. Select your calibrated printer and filament. Three parts are 100% infill modifiers; their tabs must not print.')]:
        ET.SubElement(model,N('metadata'),{'name':key}).text=value
    resources=ET.SubElement(model,N('resources'))
    config=ET.Element('config');objsettings=ET.SubElement(config,'object',{'id':'5'})
    def setting(parent,key,value):ET.SubElement(parent,'metadata',{'key':key,'value':str(value)})
    setting(objsettings,'name','Rev G body + 3 modifiers');setting(objsettings,'extruder',1)
    skin=params.get('skin_mm',1.2);skin_layers=int(round(skin/.2))
    assert abs(skin_layers*.2-skin)<1e-7
    for key,value in {'wall_loops':params['walls'],'layer_height':'.2','sparse_infill_density':f"{params['infill_percent']}%",'sparse_infill_pattern':'gyroid','top_shell_layers':skin_layers,'bottom_shell_layers':skin_layers,'top_shell_thickness':str(skin),'bottom_shell_thickness':str(skin),'wall_generator':'arachne','gap_fill_target':'everywhere'}.items():setting(objsettings,key,value)
    rows=[]
    for i,name in enumerate(names,1):
        path=D/(name+'.stl');points,triangles=stl(path)
        obj=ET.SubElement(resources,N('object'),{'id':str(i),'type':'model','name':name})
        mesh=ET.SubElement(obj,N('mesh'));vertices=ET.SubElement(mesh,N('vertices'));faces=ET.SubElement(mesh,N('triangles'))
        for p in points:ET.SubElement(vertices,N('vertex'),dict(zip(['x','y','z'],[f'{v:.8g}' for v in p])))
        for t in triangles:ET.SubElement(faces,N('triangle'),dict(zip(['v1','v2','v3'],map(str,t))))
        subtype='normal_part' if i==1 else 'modifier_part'
        part=ET.SubElement(objsettings,'part',{'id':str(i),'subtype':subtype})
        setting(part,'name','BODY — print' if i==1 else name+' — MODIFIER 100%')
        setting(part,'matrix','1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')
        setting(part,'source_file',path.name)
        for key in ['source_offset_x','source_offset_y','source_offset_z']:setting(part,key,0)
        if i>1:
            setting(part,'sparse_infill_density','100%');setting(part,'sparse_infill_pattern','rectilinear')
        rows.append({'name':name,'role':subtype,'vertices':len(points),'triangles':len(triangles),'STL_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    parent=ET.SubElement(resources,N('object'),{'id':'5','type':'model'})
    components=ET.SubElement(parent,N('components'))
    for i in range(1,5):ET.SubElement(components,N('component'),{'objectid':str(i),'transform':'1 0 0 0 1 0 0 0 1 0 0 0'})
    build=ET.SubElement(model,N('build'))
    ET.SubElement(build,N('item'),{'objectid':'5','transform':'0 -1 0 1 0 0 0 0 1 12.5 274.2465 0','printable':'1'})
    plate=ET.SubElement(config,'plate');setting(plate,'plater_id',1);setting(plate,'plater_name','Rev G — choose calibrated profiles');setting(plate,'locked','false')
    instance=ET.SubElement(plate,'model_instance');setting(instance,'object_id',5);setting(instance,'instance_id',0);setting(instance,'identify_id',1)
    ET.SubElement(config,'assemble')
    types=b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>'
    rels=b'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    output=D/'rev-g-model-and-modifiers.3mf'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in [('3D/3dmodel.model',xml(model)),('Metadata/model_settings.config',xml(config)),('[Content_Types].xml',types),('_rels/.rels',rels)]:
            info=zipfile.ZipInfo(name,date_time=(2026,9,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
    (D/'3mf-verification.json').write_text(json.dumps({'parts':rows,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'includes_machine_or_filament_profile':False,'includes_Gcode':False,'status':'Requires Orca round-trip and toolpath verification.'},indent=2)+'\n')
    print('Packaged',output.name,flush=True)

if __name__=='__main__':main()
