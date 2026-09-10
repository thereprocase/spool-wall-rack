from pathlib import Path
import json,cadquery as cq
D=Path(__file__).resolve().parent
rows=[]
for n in [8,10]:
 p=D/f'print-material-{n}w.brep';b=cq.importers.importBrep(str(p)).val();c=b.clean();before=b.Volume();after=c.Volume()
 r={'walls':n,'before_faces':len(b.Faces()),'after_faces':len(c.Faces()),'before_edges':len(b.Edges()),'after_edges':len(c.Edges()),'before_volume_mm3':before,'after_volume_mm3':after,'valid':c.isValid(),'solid_count':len(c.Solids())}
 assert c.isValid() and len(c.Solids())==1 and abs(after-before)<.001,r
 cq.exporters.export(c,str(D/f'print-material-clean-{n}w.brep'));rows.append(r);print(r,flush=True)
(D/'analysis-topology-cleanup.json').write_text(json.dumps(rows,indent=2))
