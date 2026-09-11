"""Reuse the established aligned 3MF packaging, with truthful EF labels."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
BAMBU = 'http://schemas.bambulab.com/package/2021'
ET.register_namespace('', CORE)
ET.register_namespace('BambuStudio', BAMBU)


def main():
    subprocess.run([sys.executable, str(ROOT/'designs/rev-g/package_3mf.py'), str(D)], check=True)
    path = D/'rev-g-model-and-modifiers.3mf'
    with zipfile.ZipFile(path) as z:
        items = [(v, z.read(v.filename)) for v in z.infolist()]
    updated = []
    for info, value in items:
        if info.filename in ['3D/3dmodel.model', 'Metadata/model_settings.config']:
            root = ET.fromstring(value)
            if info.filename == '3D/3dmodel.model':
                # Orca's reader expects the core tags without generated ns0
                # prefixes. Preserve the established packager's namespace form.
                root.set('xmlns:BambuStudio', BAMBU)
            for m in root.iter():
                if m.tag.endswith('metadata'):
                    if m.get('name') == 'Title': m.text = 'EF hybrid geometry and modifiers'
                    if m.get('key') in ['name','plater_name'] and m.get('value', '').startswith('Rev G'):
                        m.set('value', m.get('value').replace('Rev G', 'EF hybrid', 1))
            value = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        updated.append((info, value))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for info, value in updated: z.writestr(info, value)
    receipt = json.loads((D/'3mf-verification.json').read_text())
    receipt['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt['model_title'] = 'EF hybrid geometry and modifiers'
    receipt['filename_note'] = 'Legacy model filename retained for the tested slice runner; metadata identifies the new EF body.'
    (D/'3mf-verification.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Packaged EF body and three aligned modifier parts', flush=True)


if __name__ == '__main__': main()
