"""Prepare a clearly identified excerpt from an official NASA video, not generated media."""
import hashlib
import json
from pathlib import Path
import ssl
import urllib.request
from clipagent.media import _run, probe

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'NHQ_2020_0302_AskNASA%20-%20How%20can%20I%20be%20an%20Astronaut'
URL = f'https://images-assets.nasa.gov/video/{SLUG}/{SLUG}~small.mp4'


def main():
    original = ROOT/'data/recording-source/nasa-ask.mp4'
    original.parent.mkdir(parents=True, exist_ok=True)
    if not original.exists():
        context = ssl.create_default_context(cafile='/etc/ssl/cert.pem') if Path('/etc/ssl/cert.pem').exists() else None
        with urllib.request.urlopen(URL, context=context, timeout=120) as response:
            original.write_bytes(response.read())
    folder = ROOT/'sample_data/nasa'
    folder.mkdir(parents=True, exist_ok=True)
    sample = folder/'astronaut-training.mp4'
    # Fixed preparation interval chosen for the training Q&A. This is disclosed,
    # and is not attributed to ClipAgent's planning or visual understanding.
    _run(['-ss','113','-i',str(original),'-t','61','-map','0:v:0','-map','0:a:0',
        '-vf','scale=640:360','-c:v','libx264','-crf','23','-preset','veryfast',
        '-c:a','aac','-b:a','128k','-movflags','+faststart',str(sample)])
    provenance = {
        'title':'#AskNASA - How Can I Be An Astronaut?', 'credit':'NASA',
        'nasa_id':'NHQ_2020_0302_AskNASA - How can I be an Astronaut',
        'official_asset_collection':f'https://images-assets.nasa.gov/video/{SLUG}/collection.json',
        'download_url':URL,
        'usage_policy':'https://www.nasa.gov/nasa-brand-center/images-and-media/',
        'usage':'Educational software demonstration with NASA attribution; no endorsement implied. NASA media usage guidelines apply; no rights to NASA insignia or third-party content are claimed.',
        'downloaded_at':'2026-11-17',
        'download_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
        'download_metadata':probe(original),
        'preparation':{'start_seconds':113,'end_seconds':174,'note':'A fixed 61-second training Q&A excerpt selected by the demo author before upload. Re-encoded at native 640x360; original moving images and audio retained.'},
        'sample_sha256':hashlib.sha256(sample.read_bytes()).hexdigest(),
        'sample_metadata':probe(sample),
        'evaluation_scope':'Curated demonstration, not a held-out benchmark or human quality rating. The author inspected an earlier transcript to select supported topics. The recorded run transcribes its uploaded source afresh; no transcript is supplied to the backend.'
    }
    (folder/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(provenance,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
