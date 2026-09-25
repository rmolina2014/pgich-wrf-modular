from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'informes_ejecucion/auditoria_tesis_20260925'
OUT.mkdir(exist_ok=True)
SOURCE = Path('E:/Proyectos_2026/documentacion_tesis_wrf-master/documentacion_tesis_wrf-master/tesis_borrador_22092026_v7.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
if len(sys.argv)==1:
    with ZipFile(SOURCE) as z:
        root = ET.fromstring(z.read('word/document.xml'))
        lines=[]
        for i, el in enumerate(root.find('w:body', ns)):
            text=' '.join(t.text or '' for t in el.findall('.//w:t', ns))
            if text.strip():
                style=el.find('w:pPr/w:pStyle', ns)
                label=style.get('{'+ns['w']+'}val','') if style is not None else ''
                lines.append(f'[{i:04d} {label}] {text}')
        (OUT/'texto_extraido.txt').write_text('\n'.join(lines),encoding='utf-8')
        print('Bloques',len(lines),'Caracteres',sum(map(len,lines)))
        for l in lines:
            if any(k in l[:45].lower() for k in ('heading','titulo','ttulo')):
                print(l)
        print('Images',len([n for n in z.namelist() if n.startswith('word/media/')]))
else:
    lines=(OUT/'texto_extraido.txt').read_text(encoding='utf-8').splitlines()
    start,end=map(int,sys.argv[1:3])
    print('\n'.join(lines[start:end]))
