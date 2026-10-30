"""Presentation of edited section text; never regenerate or restore stale claims."""
from __future__ import annotations

import re
from html import escape

VERSION = 'reference-2'
METADATA = re.compile(r'^(Client|Company name|Role|Target Role|Contribution|Platform|Operating System|Tools|Team Size):\s*(.*)', re.I)


def nodes(section):
    lines = section['text'].splitlines()
    rows = []
    def flush():
        if rows:
            value = list(rows)
            rows.clear()
            return ('table', value)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        plain = line.replace('**', '')
        metadata = METADATA.match(plain) if section['key'] == 'projects' else None
        if section['key'] == 'skills' and ':' in plain:
            label, value = plain.split(':', 1)
            rows.append([label.strip(), value.strip()])
            continue
        if section['key'] == 'education' and not line.startswith('#'):
            rows.append([line.removeprefix('- ')])
            continue
        if metadata:
            label = metadata[1] + (':' if metadata[1].casefold() == 'company name' else '')
            rows.append([label, metadata[2]])
            continue
        item = flush()
        if item: yield item
        if line.startswith('- '): yield ('bullet', line[2:])
        elif line.startswith('##### '): yield ('label', line[6:])
        elif line.startswith('#### '): yield ('project', line[5:])
        elif line.startswith('### '): yield ('employer', line[4:])
        else: yield ('paragraph', line)
    item = flush()
    if item: yield item


def html(document, include_jd=False):
    def rich(text):
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', escape(text))
    body = []
    for section in document.get('sections', []):
        body.append('<section>')
        if section['key'] == 'header':
            for i,line in enumerate(section['text'].splitlines()):
                body.append(('<h1>' if i == 0 else '<p align="center">') + rich(line) + ('</h1>' if i == 0 else '</p>'))
        else:
            body.append('<h2>'+escape(section['title'])+'</h2>')
            bullet_no = 0
            for kind,value in nodes(section):
                if kind == 'table':
                    body.append('<table width="100%" cellspacing="0" cellpadding="5" border="1">')
                    for row in value:
                        body.append('<tr>'+''.join('<td>'+('<strong>'+rich(v)+'</strong>' if j == 0 and len(row)>1 else rich(v))+'</td>' for j,v in enumerate(row))+'</tr>')
                    body.append('</table>')
                elif kind == 'bullet':
                    bullet_no += 1
                    body.append(f'<ul><li id="{section["key"]}-bullet-{bullet_no}">'+rich(value)+'</li></ul>')
                else:
                    tag = {'employer':'h3','project':'h4','label':'h5'}.get(kind,'p')
                    body.append('<'+tag+'>'+rich(value)+'</'+tag+'>')
        body.append('</section>')
    if include_jd:
        body.append('<h2>Original job description</h2><pre>'+escape(document.get('jd',''))+'</pre>')
    css = ('body{max-width:850px;margin:24px auto;padding:0 18px;font:15px/1.25 "Times New Roman",serif;color:#172b3a}'
           'h1{text-align:center;color:#315c91;font-size:24px}h2{background:#c6d9ee;padding:7px;font-size:18px;page-break-after:avoid}'
           'h3,h4,h5{margin:12px 0 5px;page-break-after:avoid}h5{font-size:15px}p{margin:5px 0}'
           'table{border-collapse:collapse;width:100%;margin:8px 0}td,th{border:1px solid #8995a2;padding:5px;vertical-align:top}'
           'tr{break-inside:avoid}ul{margin:4px 0;padding-left:22px}pre{white-space:pre-wrap}')
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body>'+''.join(body)+'</body></html>'


def docx(document, destination):
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docgen.reference_template import configure, rich, table
    doc = Document()
    configure(doc)
    doc.styles['ResumeName'].font.size = Pt(20)
    for section in document['sections']:
        if section['key'] == 'header':
            for i,line in enumerate(section['text'].splitlines()):
                rich(doc.add_paragraph(style='ResumeName' if i==0 else 'Headline' if i==1 else 'ContactInfo'),line)
            continue
        p = doc.add_paragraph(style='SectionHeading')
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(6)
        shade = OxmlElement('w:shd');shade.set(qn('w:fill'),'C6D9EE');p._p.get_or_add_pPr().append(shade)
        run = p.add_run(section['title']);run.bold=True;run.font.size=Pt(13);run.font.color.rgb=RGBColor.from_string('172B3A')
        for kind,value in nodes(section):
            if kind == 'table':
                table(doc,value)
                tbl=doc.tables[-1]
                if section['key'] == 'education' and all(len(row)==1 for row in value):
                    for row in tbl.rows:
                        for paragraph in row.cells[0].paragraphs:
                            for run in paragraph.runs:run.bold=False
                    if len(tbl.rows)>1:
                        # Chain the section heading and column-label row to the
                        # first qualification, rather than orphaning the header.
                        for paragraph in tbl.rows[0].cells[0].paragraphs:
                            paragraph.paragraph_format.keep_with_next=True
                if section['key'] == 'projects':
                    # Keep compact project metadata together. Some renderers
                    # lose continuation rows at a page boundary otherwise.
                    for index,row in enumerate(tbl.rows):
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                paragraph.paragraph_format.keep_with_next=index < len(tbl.rows)-1
                borders=OxmlElement('w:tblBorders')
                for side in ('top','left','bottom','right','insideH','insideV'):
                    border=OxmlElement('w:'+side)
                    for key,val in (('val','single'),('sz','4'),('color','8995A2')):border.set(qn('w:'+key),val)
                    borders.append(border)
                tbl._tbl.tblPr.append(borders)
                continue
            p=doc.add_paragraph(style='Bullet' if kind=='bullet' else 'Subheading' if kind in {'employer','project','label'} else 'Body')
            rich(p,value)
            if section['key']=='projects' and kind=='paragraph':
                p.paragraph_format.keep_with_next=True
            if kind in {'employer','project','label'}:
                p.paragraph_format.keep_with_next=True
                for run in p.runs:run.bold=True
    doc.save(str(destination))
    return destination
