"""Create a portable PDF from the validated presentation's rendered slides."""
from pathlib import Path
from reportlab.pdfgen import canvas

ROOT=Path(__file__).resolve().parents[1]
output=ROOT/'deliverables/ClipAgent_Demo.pdf'
slides=sorted((ROOT/'.presentation-build').glob('slide-*.png'))
if len(slides)!=10:
    raise ValueError('Expected 10 reviewed presentation renders')
doc=canvas.Canvas(str(output),pagesize=(960,540))
doc.setTitle('ClipAgent demonstration - Group 59')
for image in slides:
    doc.drawImage(str(image),0,0,width=960,height=540)
    doc.showPage()
doc.save()
print(output)
