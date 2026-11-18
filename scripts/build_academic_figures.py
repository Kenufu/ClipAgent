"""One diagram specification shared by vector report figures and editable slides."""
import json
from pathlib import Path
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon
from reportlab.graphics import renderPDF, renderSVG
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/figures'
INK='#152C46'; BLUE='#245FA5'; TEAL='#087E82'; GRAY='#516477'; RED='#A53F35'
FIGS=[]

def figure(name,title,caption,source):
    f=dict(name=name,title=title,caption=caption,source=source,width=1120,height=500,items=[])
    FIGS.append(f);return f
def text(f,t,x,y,size=22,color=INK):
    f['items'].append(dict(kind='text',text=t,x=x,y=y,size=size,color=color))
def rect(f,x,y,w,h,fill='#EDF3F9',stroke=BLUE):
    f['items'].append(dict(kind='rect',x=x,y=y,w=w,h=h,fill=fill,stroke=stroke))
def box(f,title,body,x,y,w=230,h=90):
    rect(f,x,y,w,h);text(f,title,x+14,y+24,24)
    for i,line in enumerate(body.split('\n')):text(f,line,x+14,y+52+i*25,20,GRAY)
def arrow(f,x1,y1,x2,y2,color=BLUE):
    f['items'].append(dict(kind='arrow',x1=x1,y1=y1,x2=x2,y2=y2,color=color))

def specs():
    FIGS.clear()
    f=figure('01-architecture','System architecture and persistence',
      'Implemented data path: user actions enter through FastAPI; one worker executes analysis, selection and verified rendering. SQLite stores the latest job state and events; media artifacts remain on disk. Cached transcripts support revisions, not cross-session preference memory.',
      'app.py; clipagent/service.py; clipagent/storage.py; clipagent/media.py')
    for a in [('Workbench','Brief + manual edits',20),('FastAPI','Validate + queue',310),('Single worker','Stage orchestration',600)]:box(f,*a[:2],a[2],25,250)
    arrow(f,270,70,310,70);arrow(f,560,70,600,70)
    box(f,'SQLite','Jobs / events\nLatest timeline',880,25,220,120)
    arrow(f,850,70,880,70)
    for a in [('Whisper ASR','Words + timestamps',20),('Lexical planner','Source-linked clips',310),('FFmpeg + checks','Render / decode',600)]:box(f,*a[:2],a[2],210,250)
    arrow(f,725,115,725,170);arrow(f,725,170,145,170);arrow(f,145,170,145,210);text(f,'calls stages',740,170,20)
    arrow(f,270,255,310,255);arrow(f,560,255,600,255)
    box(f,'Local files','Inputs / model cache\nMP4 / SRT exports',880,210,220,120);arrow(f,850,255,880,255)
    text(f,'Revision: reuse stored transcript -> re-plan or accept a manual timeline',30,390,25,TEAL)
    text(f,'Not implemented: generative LLM planner, VLM, embeddings, LangGraph or MCP',30,445,22,GRAY)

    f=figure('02-state-machine','Job status and execution phases',
      'Status and phase are separate fields. queued/running/complete/needs_review/failed describe job readiness; transcribing/planning/rendering/verifying/repairing are phase events while running. A revision starts a new queued run and reuses the transcript. Restart recovery is not implemented.',
      'clipagent/service.py::_process; clipagent/storage.py::event; app.py::revise')
    box(f,'queued','Accepted task',20,20,200);arrow(f,220,65,270,65)
    text(f,'running  /  phase events',295,48,25)
    phases=[('transcribing','or cached reuse'),('planning','or manual input'),('rendering','attempt 1..3'),('verifying','observe output')]
    for i,(a,b) in enumerate(phases):
        box(f,a,b,290+i*198,85,180,85)
        if i<3:arrow(f,470+i*198,127,488+i*198,127)
    text(f,'repairing: change timeline, then render again (at most two repairs)',305,235,22,TEAL)
    arrow(f,960,170,960,204);arrow(f,960,204,770,204);arrow(f,770,204,770,170)
    for x,t,b in [(30,'complete','No unresolved checks'),(400,'needs_review','Export + unresolved needs'),(770,'failed','Tool or processing exception')]:box(f,t,b,x,365,320,90)
    arrow(f,500,285,190,365);arrow(f,680,285,560,365);arrow(f,920,285,930,365,RED)
    text(f,'Terminal complete/review -> user revision -> queued (new version)',30,495,21,GRAY)

    f=figure('03-selection','Lexical scoring and constrained assembly',
      'The equation restates _score; it is not a learned objective or an optimality claim. Each topic independently selects the highest-scoring cue when score >= 0.35. Chronological context fills duration, nearby intervals merge, and an optional first-topic instruction reorders a whole clip. Negation and visual meaning are outside this scoring model.',
      'clipagent/planning.py::_tokens, _score, build_timeline')
    text(f,'Q = topic tokens; C = cue tokens; N = number of transcript cues',30,35,25)
    text(f,'w(t) = log(1 + (N + 1) / (df(t) + 1))',30,95,30,BLUE)
    text(f,'score(Q,C) = sum[ w(t), t in Q intersect C ] / sum[ w(t), t in Q ]',30,155,26,BLUE)
    text(f,'                     + 0.5 * I[ exact topic phrase occurs in cue ]',30,200,26,BLUE)
    text(f,'df(t): cue count containing t; I: indicator; empty Q returns score 0',30,244,21,GRAY)
    for i,(a,b) in enumerate([('Rank cues','Per topic; threshold 0.35'),('Build intervals','-0.18s / +0.22s padding'),('Assemble edit','Context / merge / order')]):
        box(f,a,b,30+i*365,280,320,95)
        if i<2:arrow(f,350+i*365,326,395+i*365,326)
    text(f,'Constraints: 0 <= start < end <= source duration; no same-source overlap',30,430,24)
    text(f,'Greedy heuristic; no global optimum and no semantic-entailment guarantee',30,480,23,RED)

    f=figure('04-provenance','Source-to-output time mapping',
      'Illustrative numbers, not a measured task. Clip A keeps source [10,14] and clip B keeps [30,36]. Their output intervals are [0,4] and [4,10]. A word at source t=32 maps to output 6 seconds. After trimming, retained word midpoints determine which topic evidence remains; subtitle remapping is related but uses its own boundary logic.',
      'clipagent/planning.py::make_srt, review_timeline_evidence; illustrative intervals')
    text(f,'SOURCE TIME (s)',25,40,22,GRAY)
    arrow(f,40,100,1070,100,GRAY)
    for x,label in [(40,'0'),(300,'10'),(404,'14'),(820,'30'),(976,'36')]:text(f,label,x-8,80,20)
    rect(f,300,110,104,65,'#DCEBFA');text(f,'A',337,151,27)
    rect(f,820,110,156,65,'#DCF1EB',TEAL);text(f,'B',882,151,27)
    text(f,'OUTPUT TIME (s)',25,244,22,GRAY)
    rect(f,300,275,240,70,'#DCEBFA');text(f,'A: [0,4]',355,318,25)
    rect(f,540,275,360,70,'#DCF1EB',TEAL);text(f,'B: [4,10]',645,318,25)
    arrow(f,352,175,420,275);arrow(f,898,175,720,275,TEAL)
    text(f,'output(t) = sum(previous clip durations) + t - source_start',30,405,27,BLUE)
    text(f,'Example: 4 + (32 - 30) = 6 seconds; retain asset ID + source bounds',30,458,24)

    f=figure('05-verification','Bounded observation and repair',
      'Automatic timelines allow three render attempts. A duration mismatch can remove an optional clip or add unused nonoverlapping speech. Manual timelines bypass duration repair. Evidence is recomputed after editing; unresolved requirements produce needs_review. This loop does not repair semantic, framing or audio-quality defects.',
      'clipagent/service.py::_process; planning.py::repair_duration; media.py::verify')
    box(f,'Timeline','Validate bounds',20,30,230);box(f,'Render','Temporary staging',320,30,230);box(f,'Observe','Decode / duration / ratio',620,30,290)
    arrow(f,250,75,320,75);arrow(f,550,75,620,75)
    box(f,'Repair duration','Remove optional clip\nor add unused speech',320,210,310,120)
    arrow(f,765,120,765,265);arrow(f,765,265,630,265);text(f,'duration mismatch',805,220,20);text(f,'+ action available',805,249,20)
    arrow(f,475,210,475,120);text(f,'max 2 repairs',325,184,21,TEAL)
    text(f,'Stop repair: within tolerance / no action / 3rd render / manual edit',25,380,24)
    box(f,'Final evidence check','Retained speech -> complete OR needs_review',20,410,650,85)
    box(f,'Exception -> failed','Clear report; hide stale export',735,410,365,85)

    f=figure('06-evaluation','Evaluation design and evidence boundaries',
      'Controlled comparison uses the same 18 developer-authored transcript cases: 14 feasible and four expected failures. The interval oracle is separate from production keyword reporting, but labels are not independently authored or held out. Duration observations are simulated. Real media and browser tests establish execution, not benchmark accuracy.',
      'evaluation/run.py; evaluation/cases.json; evaluation/results/results.json; browser_results/summary.json')
    box(f,'18 curated cases','Transcript + constraints\nAccepted intervals',20,120,250,120)
    for y,t in [(20,'Chronological baseline'),(175,'Lexical planner'),(330,'Planner + repair')]:
        box(f,t,'Same input cases',355,y,310,90);arrow(f,270,180,355,y+45)
        arrow(f,665,y+45,790,205)
    box(f,'Interval oracle','Coverage / duration\nOrder / false-complete',790,145,310,120)
    text(f,'Feasible passes: 1/14 -> 8/14 -> 10/14; remaining false-complete: 2',25,465,24,BLUE)
    return FIGS

def drawing(f):
    d=Drawing(f['width'],f['height'])
    H=f['height']
    for o in f['items']:
        if o['kind']=='rect':d.add(Rect(o['x'],H-o['y']-o['h'],o['w'],o['h'],fillColor=HexColor(o['fill']),strokeColor=HexColor(o['stroke']),strokeWidth=1.3))
        elif o['kind']=='text':d.add(String(o['x'],H-o['y'],o['text'],fontName='Helvetica',fontSize=o['size'],fillColor=HexColor(o['color'])))
        else:
            import math
            x,y=o['x2'],H-o['y2'];a=math.atan2(y-(H-o['y1']),x-o['x1'])
            d.add(Line(o['x1'],H-o['y1'],x,y,strokeColor=HexColor(o['color']),strokeWidth=2))
            d.add(Polygon([x,y,x-11*math.cos(a-.4),y-11*math.sin(a-.4),x-11*math.cos(a+.4),y-11*math.sin(a+.4)],fillColor=HexColor(o['color']),strokeColor=None))
    return d

def main():
    OUT.mkdir(exist_ok=True);figs=specs()
    (OUT/'figures.json').write_text(json.dumps(figs,indent=2)+'\n')
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    c=canvas.Canvas(str(ROOT/'deliverables/ClipAgent_Academic_Figures.pdf'),pagesize=(1200,760))
    for i,f in enumerate(figs,1):
        d=drawing(f);renderSVG.drawToFile(d,str(OUT/(f['name']+'.svg')))
        c.setFont('Helvetica-Bold',30);c.setFillColor(HexColor(INK));c.drawString(40,710,f'Figure {i}. '+f['title'])
        renderPDF.draw(d,c,40,170)
        p=Paragraph(f['caption'],ParagraphStyle('caption',fontName='Helvetica',fontSize=16,leading=23));w,h=p.wrap(1120,130);p.drawOn(c,40,140-h)
        c.setFont('Helvetica',11);c.drawString(40,26,'Source: '+f['source']);c.showPage()
    c.save()

if __name__=='__main__':main()
