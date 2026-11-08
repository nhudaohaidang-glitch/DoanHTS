"""Render the grounded AI V6 study guide as offline HTML, PDF, DOCX and ZIP."""
import hashlib
import html
import json
import re
import textwrap
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                               Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'ai_part2/learning/ai_v6'
STEM = 'DE_CUONG_HOC_AI_V6'


def blocks(source):
    lines = source.splitlines(); i = 0; result = []
    special = re.compile(r'^(#{1,3} |```|\| |[-*] |\d+\. )')
    while i < len(lines):
        line = lines[i]
        if not line.strip(): i += 1; continue
        if line.startswith('```'):
            body = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                body.append(lines[i]); i += 1
            result.append(('code', '\n'.join(body))); i += 1
        elif line.startswith('#'):
            mark, title = line.split(' ', 1); result.append(('h' + str(len(mark)), title)); i += 1
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                row = [x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+', x) for x in row): rows.append(row)
                i += 1
            result.append(('table', rows))
        elif re.match(r'^([-*] |\d+\. )', line):
            ordered = bool(re.match(r'^\d+\.', line)); items = []
            pattern = r'^\d+\. ' if ordered else r'^[-*] '
            while i < len(lines) and re.match(pattern, lines[i]):
                items.append(re.sub(pattern, '', lines[i])); i += 1
            result.append(('ol' if ordered else 'ul', items))
        else:
            body = [line]; i += 1
            while i < len(lines) and lines[i].strip() and not special.match(lines[i]):
                body.append(lines[i]); i += 1
            result.append(('p', ' '.join(body)))
    return result


def inline(text, pdf=False):
    s = html.escape(text)
    s = re.sub(r'`([^`]+)`', lambda m: ('<font name="NotoMono">' + m[1] + '</font>') if pdf else '<code>' + m[1] + '</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return s


def network_drawing():
    d = Drawing(450, 245)
    positions = [[(95, 200-i*30) for i in range(6)], [(235, 225-i*27) for i in range(8)], [(375, 180-i*55) for i in range(3)]]
    for left, right in zip(positions, positions[1:]):
        for x, y in left:
            for u, v in right: d.add(Line(x, y, u, v, strokeColor=colors.HexColor('#cbd5e1'), strokeWidth=.45))
    for layer, points in enumerate(positions):
        for j, (x, y) in enumerate(points):
            d.add(Circle(x, y, 10, fillColor=colors.HexColor(['#dbeafe', '#ccfbf1', '#fef3c7'][layer]), strokeColor=colors.HexColor('#334155')))
            d.add(String(x-5, y-3, str(j), fontName='Noto', fontSize=8))
            if layer == 0: d.add(String(3, y-3, ['q0: N/8', 'q1: mean/2', 'q2: SYN ratio', 'q3: src', 'q4: dst', 'q5: port'][j], fontName='Noto', fontSize=8))
            if layer == 2: d.add(String(390, y-3, ['Normal', 'SYN', 'Scan'][j], fontName='Noto', fontSize=8))
    d.add(String(60, 8, '6 đầu vào', fontName='NotoBold', fontSize=9))
    d.add(String(200, 8, '8 hidden ReLU', fontName='NotoBold', fontSize=9))
    d.add(String(350, 8, '3 score', fontName='NotoBold', fontSize=9))
    return d


def pdf_document(items):
    fontroot = Path('/usr/share/fonts/truetype/noto')
    for name, file in [('Noto','NotoSans-Regular.ttf'), ('NotoBold','NotoSans-Bold.ttf'), ('NotoItalic','NotoSans-Italic.ttf'), ('NotoMono','NotoSansMono-Regular.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fontroot / file)))
    pdfmetrics.registerFontFamily('Noto', normal='Noto', bold='NotoBold', italic='NotoItalic', boldItalic='NotoBold')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TextVI', fontName='Noto', fontSize=10, leading=15, spaceAfter=7, splitLongWords=True, allowWidows=0, allowOrphans=0))
    styles.add(ParagraphStyle(name='ChapterVI', fontName='NotoBold', fontSize=17, leading=23, spaceAfter=15, keepWithNext=True))
    styles.add(ParagraphStyle(name='SubVI', fontName='NotoBold', fontSize=12, leading=17, spaceBefore=10, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name='CellVI', fontName='Noto', fontSize=8.4, leading=12.2, splitLongWords=True))
    styles.add(ParagraphStyle(name='CodeVI', fontName='NotoMono', fontSize=7.4, leading=11, spaceBefore=5, spaceAfter=10, leftIndent=8))
    styles.add(ParagraphStyle(name='TitleVI', fontName='NotoBold', fontSize=26, leading=34, spaceAfter=18))
    class GuideDoc(SimpleDocTemplate):
        def beforeDocument(self):
            self.chapter_counter = 0
        def afterFlowable(self, flow):
            if isinstance(flow, Paragraph) and flow.style.name == 'ChapterVI':
                name = 'chapter-' + str(getattr(self, 'chapter_counter', 0))
                self.chapter_counter = getattr(self, 'chapter_counter', 0) + 1
                self.canv.bookmarkPage(name); self.canv.addOutlineEntry(flow.getPlainText(), name, 0, False)
                self.notify('TOCEntry', (0, flow.getPlainText(), self.page, name))
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont('Noto', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(1.8*cm, 1.05*cm, 'Phần 2 • AI V6 • Model đã chốt, ví dụ đã đối chiếu')
        canvas.drawRightString(19.2*cm, 1.05*cm, str(doc.page)); canvas.restoreState()
    doc = GuideDoc(str(ROOT/(STEM+'.pdf')), pagesize=(21*cm,29.7*cm), rightMargin=1.8*cm, leftMargin=1.8*cm, topMargin=1.7*cm, bottomMargin=1.8*cm,
                   title='Đề cương học và hiểu phần AI V6', author='Tài liệu dự án DoanHTS — phần AI')
    story = [Spacer(1,1*cm), Paragraph('Học và hiểu<br/>phần AI V6 của bạn', styles['TitleVI']),
             Paragraph('Đề cương có giải thích, dữ liệu mẫu, thực hành và đáp án', styles['SubVI']),
             Paragraph('Normal IoT-23 • SYN flood capture 34 • Vertical scan Chris Sanders', styles['TextVI']),
             Spacer(1,.5*cm), network_drawing(), Spacer(1,.5*cm),
             Paragraph('10 buổi học • 6 đặc trưng • MLP 6–8–3 • 83 tham số', styles['SubVI']),
             Paragraph('Đối chiếu đúng model V6 và các file bàn giao. Có nêu nhãn xung đột, lỗi còn lại và giới hạn đánh giá. Ngày soạn: 08/11/2026.', styles['TextVI']),
             Paragraph('Đọc PDF để học; mở bản HTML để thay sáu đặc trưng và xem phép tính. Các PCAP/CSV mẫu nằm trong gói ZIP đi kèm.', styles['TextVI']), PageBreak(),
             Paragraph('Mục lục', styles['TitleVI'])]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle(name='TOCVI',fontName='Noto',fontSize=10,leading=16,spaceBefore=5)]
    story.extend([toc,PageBreak()])
    first_chapter=True
    for kind, body in items:
        if kind=='h1': continue
        if kind=='h2':
            if not first_chapter: story.extend([CondPageBreak(6*cm), Spacer(1,.3*cm)])
            first_chapter=False;story.append(Paragraph(inline(body,True),styles['ChapterVI']))
        elif kind=='h3':story.append(Paragraph(inline(body,True),styles['SubVI']))
        elif kind=='p':story.append(Paragraph(inline(body,True),styles['TextVI']))
        elif kind in ('ol','ul'):
            for j, item in enumerate(body):
                prefix=f'{j+1}. ' if kind=='ol' else '• '
                story.append(Paragraph(prefix+inline(item,True),styles['TextVI']))
        elif kind=='code':
            lines=[]
            for line in body.splitlines():lines.extend(textwrap.wrap(line,104,replace_whitespace=False,drop_whitespace=False) or [''])
            story.append(Preformatted('\n'.join(lines),styles['CodeVI']))
        elif kind=='table':
            width=doc.width/len(body[0])
            rows=[[Paragraph(('<b>'+inline(x,True)+'</b>') if j==0 else inline(x,True),styles['CellVI']) for x in row] for j,row in enumerate(body)]
            table=Table(rows,colWidths=[width]*len(body[0]),repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0f2fe')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),('VALIGN',(0,0),(-1,-1),'TOP'),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#cbd5e1')),('INNERGRID',(0,0),(-1,-1),.3,colors.HexColor('#cbd5e1')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([table,Spacer(1,10)])
    doc.multiBuild(story,onFirstPage=footer,onLaterPages=footer)


def word_document(items):
    doc=Document();section=doc.sections[0];section.top_margin=Cm(1.8);section.bottom_margin=Cm(1.8);section.left_margin=Cm(2);section.right_margin=Cm(2)
    for name in ('Normal','Title','Heading 1','Heading 2'):
        doc.styles[name].font.name='Noto Sans'
    normal=doc.styles['Normal'];normal.font.size=Pt(10.5);normal.paragraph_format.space_after=Pt(6)
    doc.core_properties.title='Đề cương học và hiểu phần AI V6'
    doc.core_properties.subject='Model 6–8–3, dữ liệu, thực hành và bàn giao phần AI'
    doc.add_heading('Học và hiểu phần AI V6 của bạn',0)
    doc.add_paragraph('Đề cương có giải thích, ví dụ PCAP/CSV thật, bài tập và đáp án.\nNgày 08/11/2026 • MLP 6–8–3 • 83 tham số')
    doc.add_paragraph('6 q → 8 hidden ReLU → 3 score [Normal, SYN flood, Vertical scan]')
    doc.add_paragraph('Bản Word để ghi chú. PDF có mục lục theo trang; HTML có bộ tính tương tác. Nguồn và phạm vi đánh giá được ghi trong tài liệu.')
    doc.add_page_break()
    for kind,body in items:
        if kind=='h1':continue
        if kind in ('h2','h3'):doc.add_heading(body,1 if kind=='h2' else 2)
        elif kind=='p':doc.add_paragraph(re.sub(r'`|\*\*','',body))
        elif kind=='code':
            p=doc.add_paragraph();run=p.add_run(body);run.font.name='Noto Sans Mono';run.font.size=Pt(8)
        elif kind in ('ol','ul'):
            for row in body:doc.add_paragraph(re.sub(r'`|\*\*','',row),style='List Number' if kind=='ol' else 'List Bullet')
        elif kind=='table':
            table=doc.add_table(rows=1,cols=len(body[0]));table.style='Light Shading Accent 1'
            for i,row in enumerate(body):
                cells=table.rows[0].cells if i==0 else table.add_row().cells
                for cell,value in zip(cells,row):cell.text=re.sub(r'`|\*\*','',value)
    footer=section.footer.paragraphs[0];footer.text='Phần 2 • AI V6    |    Trang '
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    doc.save(ROOT/(STEM+'.docx'))


def html_document(items):
    parts=[];toc=[];section_id=0
    for kind,body in items:
        if kind=='h1':continue
        if kind=='h2':
            key='s'+str(section_id);section_id+=1;toc.append(f'<a href="#{key}">{inline(body)}</a>');parts.append(f'<h2 id="{key}">{inline(body)}</h2>')
        elif kind=='h3':parts.append('<h3>'+inline(body)+'</h3>')
        elif kind=='p':parts.append('<p>'+inline(body)+'</p>')
        elif kind=='code':parts.append('<pre><code>'+html.escape(body)+'</code></pre>')
        elif kind in ('ol','ul'):parts.append('<'+kind+'>'+''.join('<li>'+inline(row)+'</li>' for row in body)+'</'+kind+'>')
        elif kind=='table':parts.append('<div class="table-wrap"><table>'+''.join('<tr>'+''.join(('<th>' if j==0 else '<td>')+inline(v)+('</th>' if j==0 else '</td>') for v in row)+'</tr>' for j,row in enumerate(body))+'</table></div>')
    model=json.loads((ROOT/'model/model.json').read_text());facts=json.loads((ROOT/'VI_DU_DA_DOI_CHIEU.json').read_text())
    template=(ROOT/'tools/learning_template.html').read_text()
    template=template.replace('<!--GUIDE-->', '\n'.join(parts)).replace('<!--TOC-->', '\n'.join(toc))
    template=template.replace('__FROZEN_MODEL__',json.dumps(model,ensure_ascii=False)).replace('__FACTS__',json.dumps(facts,ensure_ascii=False))
    (ROOT/(STEM+'.html')).write_text(template)


def package():
    candidates=sorted(p for p in ROOT.rglob('*') if p.is_file() and not {'__pycache__','pcap_da_giai_nen'}.intersection(p.relative_to(ROOT).parts))
    candidates=[p for p in candidates if p.name!='FILE_SHA256.json']
    (ROOT/'FILE_SHA256.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in candidates},indent=2)+'\n')
    out=REPO/'de_cuong_hoc_ai_v6.zip'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(candidates+[ROOT/'FILE_SHA256.json']):
            entry=zipfile.ZipInfo('de_cuong_hoc_ai_v6/'+p.relative_to(ROOT).as_posix(),(2000,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(entry,p.read_bytes())
    out.with_suffix('.zip.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
    print('ZIP',out.stat().st_size,'bytes',hashlib.sha256(out.read_bytes()).hexdigest())


if __name__=='__main__':
    text=(ROOT/(STEM+'.md')).read_text();items=blocks(text)
    pdf_document(items);word_document(items);html_document(items);package()
