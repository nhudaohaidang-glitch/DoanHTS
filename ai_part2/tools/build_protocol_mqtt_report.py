"""Render the evidence-backed MQTT/IoT23 protocol review; no traffic generation."""
from pathlib import Path
import hashlib,importlib.util,json,textwrap,zipfile
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import CondPageBreak,Paragraph,Preformatted,SimpleDocTemplate,Spacer,Table,TableStyle
REPO=Path(__file__).resolve().parents[2];ROOT=REPO/'ai_part2/research/protocol_mqtt_iot23';STEM='BAO_CAO_GIAO_THUC_TAN_CONG'
spec=importlib.util.spec_from_file_location('learning_renderer',Path(__file__).with_name('build_ai_v6_learning.py'));render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)
for name,file in [('Noto','NotoSans-Regular.ttf'),('NotoBold','NotoSans-Bold.ttf'),('NotoItalic','NotoSans-Italic.ttf'),('NotoMono','NotoSansMono-Regular.ttf')]:pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/noto/'+file))
pdfmetrics.registerFontFamily('Noto',normal='Noto',bold='NotoBold',italic='NotoItalic',boldItalic='NotoBold')
body=ParagraphStyle('Body',fontName='Noto',fontSize=10.4,leading=15.8,spaceAfter=8,allowWidows=0,allowOrphans=0)
title=ParagraphStyle('Title',fontName='NotoBold',fontSize=21,leading=28,spaceAfter=15,keepWithNext=True)
heading=ParagraphStyle('Heading',fontName='NotoBold',fontSize=14,leading=20,spaceBefore=12,spaceAfter=9,keepWithNext=True)
sub=ParagraphStyle('Sub',parent=heading,fontSize=11.5,leading=17,spaceBefore=8)
cell=ParagraphStyle('Cell',fontName='Noto',fontSize=9,leading=13,splitLongWords=True)
code=ParagraphStyle('Code',fontName='NotoMono',fontSize=8,leading=12,spaceAfter=10)
doc=SimpleDocTemplate(str(ROOT/(STEM+'.pdf')),pagesize=(21*cm,29.7*cm),leftMargin=1.7*cm,rightMargin=1.7*cm,topMargin=1.6*cm,bottomMargin=1.7*cm,title='Làm rõ giao thức tấn công: IoT-23, scan và MQTT',author='Đối chiếu nguồn và mã dự án DoanHTS')
story=[]
for kind,value in render.blocks((ROOT/(STEM+'.md')).read_text()):
 if kind=='h1':story.append(Paragraph(render.inline(value,True),title))
 elif kind=='h2':story.extend([CondPageBreak(5*cm),Paragraph(render.inline(value,True),heading)])
 elif kind=='h3':story.append(Paragraph(render.inline(value,True),sub))
 elif kind=='p':story.append(Paragraph(render.inline(value,True),body))
 elif kind in ('ul','ol'):
  for i,item in enumerate(value):story.append(Paragraph(('• ' if kind=='ul' else str(i+1)+'. ')+render.inline(item,True),body))
 elif kind=='code':story.append(Preformatted('\n'.join('\n'.join(textwrap.wrap(x,100)) for x in value.splitlines()),code))
 elif kind=='table':
  cells=[[Paragraph(('<b>'+render.inline(v,True)+'</b>') if i==0 else render.inline(v,True),cell) for v in row] for i,row in enumerate(value)]
  widths=[doc.width/len(value[0])]*len(value[0])
  if len(widths)==2:widths=[doc.width*.33,doc.width*.67]
  t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2f1f7')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7fafb')]),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#c9d7df')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([t,Spacer(1,9)])
def footer(canvas,doc):
 canvas.setFont('Noto',8);canvas.setFillColor(colors.HexColor('#637789'));canvas.drawString(1.7*cm,1*cm,'Đối chiếu giao thức • 09/11/2026 • Không thay đổi model');canvas.drawRightString(19.3*cm,1*cm,str(doc.page))
doc.build(story,onFirstPage=footer,onLaterPages=footer)
paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name!='FILE_SHA256.json')
(ROOT/'FILE_SHA256.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
archive=REPO/'bao_cao_giao_thuc_iot23_mqtt.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(paths+[ROOT/'FILE_SHA256.json']):
  entry=zipfile.ZipInfo('bao_cao_giao_thuc_iot23_mqtt/'+p.relative_to(ROOT).as_posix(),(2000,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,p.read_bytes())
archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print('Report ZIP',archive.stat().st_size,'bytes',hashlib.sha256(archive.read_bytes()).hexdigest())
