"""Model-only 3MF for one printable body and any number of named modifiers."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np

CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
BAMBU='http://schemas.bambulab.com/package/2021'
ET.register_namespace('',CORE); ET.register_namespace('BambuStudio',BAMBU)
N=lambda name:'{'+CORE+'}'+name


def main():
    ap=argparse.ArgumentParser();ap.add_argument('cad',type=Path);args=ap.parse_args();folder=args.cad
    params=json.loads((folder/'selected-layout.json').read_text())
    names=['body-only']+params['modifier_names'];parent_id=len(names)+1
    model=ET.Element(N('model'),{'unit':'millimeter','xmlns:BambuStudio':BAMBU})
    for key,value in [('Application','Spool rack geometry packager'),('BambuStudio:3mfVersion','1'),
                      ('Title',params['name']),('Description','Model-only prototype. Body prints; all named helper parts are 100% infill modifiers. Select calibrated printer and filament profiles.')]:
        ET.SubElement(model,N('metadata'),{'name':key}).text=value
    resources=ET.SubElement(model,N('resources'));config=ET.Element('config')
    obj=ET.SubElement(config,'object',{'id':str(parent_id)})
    def setting(parent,key,value): ET.SubElement(parent,'metadata',{'key':key,'value':str(value)})
    setting(obj,'name',params['name']);setting(obj,'extruder',1)
    skin=params['skin_mm'];layers=round(skin/.2);assert abs(layers*.2-skin)<1e-8
    for key,value in dict(wall_loops=params['walls'],layer_height='.2',sparse_infill_density=f"{params['infill_percent']}%",
                          sparse_infill_pattern='gyroid',top_shell_layers=layers,bottom_shell_layers=layers,
                          top_shell_thickness=skin,bottom_shell_thickness=skin,wall_generator='arachne',gap_fill_target='everywhere').items():
        setting(obj,key,value)
    rows=[]
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    for i,name in enumerate(names,1):
        path=folder/(name+'.stl');data=path.read_bytes();count=int.from_bytes(data[80:84],'little')
        assert len(data)==84+50*count
        triangles=np.frombuffer(data,offset=84,dtype=dtype,count=count)['vertices']
        points,index=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True);faces=index.reshape(-1,3)
        part=ET.SubElement(resources,N('object'),{'id':str(i),'type':'model','name':name})
        mesh=ET.SubElement(part,N('mesh'));vertices=ET.SubElement(mesh,N('vertices'));facets=ET.SubElement(mesh,N('triangles'))
        for point in points: ET.SubElement(vertices,N('vertex'),dict(zip(['x','y','z'],[f'{v:.8g}' for v in point])))
        for face in faces: ET.SubElement(facets,N('triangle'),dict(zip(['v1','v2','v3'],map(str,face))))
        role='normal_part' if i==1 else 'modifier_part'
        part_settings=ET.SubElement(obj,'part',{'id':str(i),'subtype':role})
        setting(part_settings,'name','BODY print' if i==1 else name+' MODIFIER 100%')
        setting(part_settings,'matrix','1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')
        setting(part_settings,'source_file',path.name)
        for key in ['source_offset_x','source_offset_y','source_offset_z']: setting(part_settings,key,0)
        if i>1:
            setting(part_settings,'sparse_infill_density','100%');setting(part_settings,'sparse_infill_pattern','rectilinear')
        rows.append(dict(name=name,role=role,vertices=len(points),triangles=len(faces),STL_sha256=hashlib.sha256(data).hexdigest()))
    parent=ET.SubElement(resources,N('object'),{'id':str(parent_id),'type':'model'});components=ET.SubElement(parent,N('components'))
    for i in range(1,parent_id): ET.SubElement(components,N('component'),{'objectid':str(i),'transform':'1 0 0 0 1 0 0 0 1 0 0 0'})
    build=ET.SubElement(model,N('build'))
    ET.SubElement(build,N('item'),{'objectid':str(parent_id),'transform':'0 -1 0 1 0 0 0 0 1 12.5 274.2465 0','printable':'1'})
    plate=ET.SubElement(config,'plate')
    for key,value in [('plater_id',1),('plater_name',params['name']),('locked','false')]:setting(plate,key,value)
    instance=ET.SubElement(plate,'model_instance')
    for key,value in [('object_id',parent_id),('instance_id',0),('identify_id',1)]:setting(instance,key,value)
    ET.SubElement(config,'assemble')
    types=b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>'
    rels=b'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    output=folder/params['model_file']
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,value in [('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True)),
                           ('Metadata/model_settings.config',ET.tostring(config,encoding='utf-8',xml_declaration=True)),
                           ('[Content_Types].xml',types),('_rels/.rels',rels)]:
            info=zipfile.ZipInfo(name,date_time=(2026,9,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,value)
    receipt=dict(parts=rows,modifier_count=len(names)-1,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                 includes_machine_or_filament_profile=False,includes_Gcode=False,status='Requires actual Orca role and path audit')
    (folder/'3mf-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Packaged',output.name,'with',len(names)-1,'modifiers',flush=True)


if __name__=='__main__': main()
