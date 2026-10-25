"""Extract a research directory from the supplied DOCX, never treating it as instructions.

Community names, addresses, layouts, reference prices and links are imported.
Word math text is read in order so price ranges are not lost. Guide figures
remain research observations, never verified offers or route guarantees.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
ZONES=['Campus and downtown','University City and Toms Creek','Prices Fork and Hethwood',
       'North Main and Givens','Harding Avenue and South Main','Private rentals and neighborhoods']
MATCHES={'Foxridge Apartment Homes':'foxridge','Alight Blacksburg':'alight','Union Blacksburg':'union',
         'Terrace View Apartments':'terrace','Windsor Hills Apartments':'windsor','The Mill at Blacksburg':'mill'}


def extract(path):
    with ZipFile(path) as z:
        root=ET.fromstring(z.read('word/document.xml'))
        relationships={r.attrib['Id']:r.attrib.get('Target','') for r in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
        bibliography={}
        numbered=[p for p in root.findall('./w:body/w:p',NS) if p.find('w:pPr/w:numPr',NS) is not None]
        for index,p in enumerate(numbered,1):
            links=[relationships.get(link.attrib.get('{'+NS['r']+'}id',''),'') for link in p.findall('w:hyperlink',NS)]
            bibliography[index]=[url for url in links if url.startswith('https://')]
        def references(cell):
            return [int(t.text) for run in cell.findall('.//w:r',NS)
                    if run.find('w:rPr/w:vertAlign',NS) is not None
                    for t in run.findall('w:t',NS) if (t.text or '').isdigit()]
        def text(cell):
            # Numbered hyperlink citations are not part of an address or price.
            parts=[]
            for paragraph in cell.findall('.//w:p',NS):
                for child in paragraph:
                    if child.tag.endswith('}pPr'):continue
                    if child.tag.endswith('}r') and child.find('w:rPr/w:vertAlign',NS) is not None:continue
                    for t in child.iter():
                        if t.tag in ('{'+NS['w']+'}t','{http://schemas.openxmlformats.org/officeDocument/2006/math}t'):
                            parts.append(t.text or '')
            return re.sub(r'\s+',' ',' '.join(parts)).strip()
        communities=[]
        for index,table in enumerate(root.findall('.//w:tbl',NS)[:6]):
            for row in table.findall('w:tr',NS)[1:]:
                cells=row.findall('w:tc',NS)
                name=text(cells[0])
                urls=[]
                for cell in cells:
                    for ref in references(cell):
                        for url in bibliography.get(ref,[]):
                            if url not in urls:urls.append(url)
                    for link in cell.findall('.//w:hyperlink',NS):
                        url=relationships.get(link.attrib.get('{'+NS['r']+'}id',''),'')
                        if url.startswith('https://') and url not in urls:urls.append(url)
                communities.append({'id':re.sub('[^a-z0-9]+','-',name.lower()).strip('-'),
                    'name':name,'address':text(cells[1]),'zone':ZONES[index],
                    'layouts':text(cells[3]),'catalog_property_id':MATCHES.get(name),
                    'guide_price_summary':text(cells[4]),
                    'source_urls':urls,'evidence_status':'guide_reference_only',
                    'price_status':'Research reference only; use current linked operator plans for comparisons.'})
        return {'format':'roomwise-guide-v1','document_sha256':sha256(Path(path).read_bytes()).hexdigest(),
                'source_name':Path(path).name,'communities':communities,
                'excluded':'Reputation rankings, demographic recommendations, legal interpretations and fixed transit times. Guide prices remain unverified research references.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('document',type=Path)
    args=parser.parse_args();data=extract(args.document)
    (ROOT/'data/housing-guide.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'communities':len(data['communities']),'matched_catalog_properties':sum(bool(c['catalog_property_id']) for c in data['communities'])}))
