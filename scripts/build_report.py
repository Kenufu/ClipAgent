"""Render the reviewed Markdown report to a paginated PDF. Requires reportlab."""
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, KeepTogether

ROOT = Path(__file__).resolve().parents[1]


def inline(text):
    text = escape(text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    return text


def build():
    source = ROOT / 'docs' / 'FINAL_REPORT.md'
    output = ROOT / 'deliverables' / 'Group59-ClipAgent-Final-Report.pdf'
    output.parent.mkdir(exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Body', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=7, textColor=colors.HexColor('#263348')))
    styles.add(ParagraphStyle(name='Cell', parent=styles['Body'], fontSize=8, leading=11, spaceAfter=0, wordWrap='CJK'))
    styles.add(ParagraphStyle(name='CodeSmall', fontName='Courier', fontSize=7, leading=10, spaceAfter=8))
    for name, size in [('Title',26), ('Heading1',17), ('Heading2',12), ('Heading3',10)]:
        styles[name].fontName='Helvetica-Bold'
        styles[name].fontSize=size
        styles[name].leading=size*1.25
        styles[name].textColor=colors.HexColor('#234c8a')
        styles[name].spaceBefore=12
        styles[name].spaceAfter=7
    flow=[]
    lines=source.read_text().splitlines()
    i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:
            i+=1; continue
        if line.startswith('```'):
            language=line[3:]; code=[]; i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i+=1
            if language != 'mermaid':
                flow.append(Preformatted('\n'.join(code), styles['CodeSmall'], maxLineLength=90))
            else:
                flow.append(Paragraph('Architecture diagram source is included in docs/ARCHITECTURE.md and the editable presentation. The component table below describes the same implemented system.', styles['Body']))
            i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',x) for x in cells):
                    rows.append([Paragraph(inline(x),styles['Cell']) for x in cells])
                i+=1
            count=max(map(len,rows))
            rows=[row+[Paragraph('',styles['Cell'])]*(count-len(row)) for row in rows]
            table=Table(rows,colWidths=[468/count]*count,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7eef8')),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#a7b7cf')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f6f8fb')])]))
            flow.extend([table,Spacer(1,9)])
            continue
        if line.startswith('#'):
            level=len(line)-len(line.lstrip('#'))
            style='Title' if level==1 else 'Heading'+str(min(level-1,3))
            flow.append(Paragraph(inline(line.lstrip('#').strip()),styles[style]))
        else:
            flow.append(Paragraph(inline(line),styles['Body']))
        i+=1
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#ccd5e2'));canvas.line(72,44,540,44)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#66758b'))
        canvas.drawString(72,31,'Group 59   /   ClipAgent   /   COMP7608B')
        canvas.drawRightString(540,31,str(doc.page))
    SimpleDocTemplate(str(output),pagesize=(612,792),leftMargin=72,rightMargin=72,topMargin=48,bottomMargin=62,title='ClipAgent Final Report',author='Group 59').build(flow,onFirstPage=footer,onLaterPages=footer)
    print(output)


if __name__=='__main__':
    build()
