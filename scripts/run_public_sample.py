"""Offline public-audio integration run; reference text is opened only after execution.

Run from repository root: .venv/bin/python -B scripts/run_public_sample.py
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SAMPLE = ROOT / 'sample_data'
OUT = ROOT / 'evaluation/public_results'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['CLIPAGENT_WHISPER_MODEL'] = 'tiny.en'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def distance(a, b):
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (x != y)))
        previous = current
    return previous[-1]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((SAMPLE / 'provenance.json').read_text())
    audio = SAMPLE / '6930-75918-0003.wav'
    if sha(audio) != provenance['audio_sha256']:
        raise ValueError('Audio checksum mismatch')
    from clipagent import config
    from clipagent.media import _run, probe, transcribe, preview_frame
    video = SAMPLE / 'static_audio_wrapper.mp4'
    labels = [
        ('PUBLIC SPEECH SAMPLE - STATIC AUDIO WRAPPER', 42, 150),
        ('NOT AN ORIGINAL VIDEO BENCHMARK', 40, 250),
        ('LibriSpeech 6930-75918-0003 | CC BY 4.0', 32, 350),
        ('Synthetic title card; downloaded English audiobook speech', 28, 430),
    ]
    vf = ','.join(f"drawtext=text='{text}':fontcolor=white:fontsize={size}:x=(w-text_w)/2:y={y}" for text, size, y in labels)
    _run(['-f', 'lavfi', '-i', 'color=c=0x19334a:s=1280x720:r=30',
          '-i', str(audio), '-t', str(provenance['duration_seconds']), '-vf', vf,
          '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast',
          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(video)])
    # Run the actual service with isolated storage, entirely within the owned output directory.
    with tempfile.TemporaryDirectory(prefix='runtime-', dir=OUT) as temp:
        config.DATABASE = Path(temp) / 'jobs.sqlite3'
        config.JOBS = Path(temp) / 'jobs'
        from clipagent import storage, service
        storage.init_db()
        asset = {'id': 'public-speech', 'name': video.name, 'path': str(video), **probe(video)}
        instruction = 'Create a landscape recap lasting 20-25 seconds with subtitles.'
        storage.create_job('public-sample', instruction, {'topics': []}, [asset])
        started = time.perf_counter()
        service._process('public-sample', False, None)
        elapsed = time.perf_counter() - started
        job = storage.get_job('public-sample')
        if job['status'] != 'failed':
            for name in ('final.mp4', 'captions.srt'):
                shutil.copyfile(config.JOBS / 'public-sample/output' / name, OUT / name)
        clean = json.loads(json.dumps(job).replace(str(ROOT), '<PROJECT>').replace(str(Path.home()), '<HOME>'))
        save(OUT / 'sanitized_trace.json', clean)
        save(OUT / 'transcript.json', job['transcript'])
        save(OUT / 'timeline.json', job['timeline'])
        if job['status'] == 'failed':
            raise RuntimeError(clean['error'])
    # Frozen pipeline output precedes all reference access. No prompts, topics, captions,
    # timing boundaries or verification expectations are taken from the reference.
    reference = (SAMPLE / 'reference.txt').read_text().strip() if (SAMPLE / 'reference.txt').exists() else ''
    hypothesis = ' '.join(cue['text'] for cue in job['transcript'])
    words = lambda text: re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.lower())
    ref_words, hyp_words = words(reference), words(hypothesis)
    errors = distance(ref_words, hyp_words)
    # Additional real ASR of exported media provides a diagnostic, not human validation.
    output_transcript = transcribe(OUT / 'final.mp4', 'rendered-public-speech')
    save(OUT / 'output_transcript.json', output_transcript)
    output_hypothesis = ' '.join(cue['text'] for cue in output_transcript)
    result = {
        'evaluation_kind': 'single public speech sample in synthetic static video; integration smoke test',
        'status': job['status'], 'instruction': instruction, 'reference_used_by_pipeline': False,
        'human_labeled_or_reviewed': False, 'topic_coverage_tested': False,
        'source_audio_sha256': sha(audio), 'wrapper_sha256': sha(video),
        'model': 'Systran/faster-whisper-tiny.en', 'device': 'cpu', 'compute_type': 'int8',
        'beam_size': 5, 'language': 'en', 'word_timestamps': True,
        'model_revision': (ROOT / 'data/models/models--Systran--faster-whisper-tiny.en/refs/main').read_text().strip(),
        'versions': {p: importlib.metadata.version(p) for p in ('faster-whisper', 'ctranslate2', 'av', 'imageio-ffmpeg')},
        'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'clipagent').glob('*.py'))},
        'pipeline_wall_seconds': round(elapsed, 3), 'report': job['report'],
        'reference': reference, 'hypothesis': hypothesis,
        'scoring': {'normalization': "lowercase; regex [a-z0-9]+ with internal apostrophes retained", 'reference_words': len(ref_words),
                    'word_edit_distance': errors if ref_words else None, 'wer': errors / len(ref_words) if ref_words else None,
                    'rendered_audio_wer_vs_full_reference': distance(ref_words, words(output_hypothesis)) / len(ref_words) if ref_words else None,
                    'rendered_audio_wer_note': 'Diagnostic only: editing can intentionally omit words; same ASR model is reused.'},
        'limitations': [
            'One clean read-English utterance; no statistical generalization or held-out training-contamination guarantee.',
            'Synthetic static title card, not original video; visual semantics and scene selection untested.',
            'Generic duration brief with no topic requirements; semantic retrieval and multi-source ordering untested.',
            'No complete independent reference was retrieved; WER is unavailable. No manual listening or subjective quality assessment.',
            'Built-in verification checks media properties and transcript-linked evidence, not independent semantic truth.',
            'Direct service execution bypasses HTTP/UI; only this local CPU/model configuration was exercised.',
            'Audio provenance relies on NVIDIA fixture documentation; full OpenSLR archive was not downloaded for byte comparison.'
        ],
    }
    preview_frame(OUT / 'final.mp4', 1, OUT / 'preview.jpg')
    save(OUT / 'results.json', result)
    save(OUT / 'artifact_sha256.json', {str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'artifact_sha256.json'})
    print(json.dumps({'status': result['status'], 'wer': result['scoring']['wer'], 'checks': result['report']['checks']}, indent=2))


if __name__ == '__main__':
    main()
