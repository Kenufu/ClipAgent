"""Add Chinese chapter captions to a real screen recording; append its actual export."""
import hashlib
import json
import os
from pathlib import Path
from clipagent.media import _run, probe

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables/demo'


def stamp(seconds):
    cs = round(seconds*100)
    return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'


def srt_stamp(seconds):
    ms = round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


def main():
    font = Path(os.environ.get('CLIPAGENT_DEMO_FONT', '/System/Library/Fonts/STHeiti Medium.ttc'))
    if not font.is_file():
        raise FileNotFoundError('Set CLIPAGENT_DEMO_FONT to a Chinese font file for chapter captions')
    fonts = OUT/'.fonts'
    fonts.mkdir(exist_ok=True)
    link = fonts/font.name
    if not link.exists():
        link.symlink_to(font.resolve())
    recording = json.loads((OUT/'recording.json').read_text())
    raw = ROOT / recording['raw_path']
    chapters = json.loads((OUT/'chapters.json').read_text())
    duration = probe(raw)['duration']
    ass = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1440
PlayResY: 1000
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Heiti SC,25,&H00FFFFFF,&H000000FF,&H00141517,&H00141517,0,0,0,0,100,100,0,0,1,0,0,2,35,35,18,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    srt = []
    for i, chapter in enumerate(chapters):
        start = 0 if i == 0 else chapter['start']
        end = chapters[i+1]['start'] if i+1 < len(chapters) else duration
        text = chapter['title'] + r'\N' + chapter['detail']
        ass += f'Dialogue: 0,{stamp(start)},{stamp(end)},Default,,0,0,0,,{text}\n'
        srt.append(f"{i+1}\n{srt_stamp(start)} --> {srt_stamp(end)}\n{chapter['title']}\n{chapter['detail']}\n")
    (OUT/'guide.ass').write_text(ass)
    (OUT/'ClipAgent-real-demo.zh.srt').write_text('\n'.join(srt))
    ui = OUT/'annotated-ui.mp4'
    common = ['-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
              '-r','30','-c:a','aac','-ar','48000','-ac','2','-b:a','128k','-movflags','+faststart']
    _run(['-i',str(raw),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo',
          '-t',str(duration),'-vf',"fps=30,pad=1440:1000:0:0:color=0x141517,setsar=1,subtitles=guide.ass:fontsdir=.fonts",
          '-map','0:v:0','-map','1:a:0',*common,str(ui)], cwd=OUT, timeout=300)
    final_title = ass.split('[Events]')[0] + r'''[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:10:00.00,Default,,0,0,0,,完整导出成片 · 以下保留原声与生成字幕\NNASA公开素材 / ClipAgent实际剪辑输出 / 教学演示，无NASA背书
'''
    (OUT/'result-title.ass').write_text(final_title)
    output_section = OUT/'result-section.mp4'
    _run(['-i',str(OUT/'NASA-edited.mp4'),'-vf',
          'fps=30,scale=1440:810,pad=1440:1000:0:45:color=0x141517,setsar=1,subtitles=result-title.ass:fontsdir=.fonts',
          *common,str(output_section)],cwd=OUT, timeout=180)
    exported = probe(OUT/'NASA-edited.mp4')
    assert abs(probe(output_section)['duration']-exported['duration']) < 0.1
    (OUT/'concat.txt').write_text("file 'annotated-ui.mp4'\nfile 'result-section.mp4'\n")
    movie = OUT/'ClipAgent-real-demo.mp4'
    # Encode one continuous stream so players do not need to reconfigure at the
    # boundary between the browser capture and the original-audio result.
    _run(['-f','concat','-safe','0','-i','concat.txt',*common,str(movie)],cwd=OUT,timeout=300)
    _run(['-i',str(movie),'-f','null','-'],timeout=300)
    expected = probe(ui)['duration'] + probe(output_section)['duration']
    assert abs(probe(movie)['duration']-expected) < 0.1
    metadata = {'movie':movie.name, **probe(movie), 'sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),
                'screen_recording_seconds':duration, 'exported_result':exported,
                'editing':'Continuous real-time browser recording, Chinese chapter captions added below UI; actual downloaded export appended with original audio. No processing wait time removed.',
                'full_decode':'passed'}
    (OUT/'video-verification.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
