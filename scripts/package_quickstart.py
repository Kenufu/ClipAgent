"""Mac source installer bundle; no Python runtime, model, credentials or user jobs."""
import hashlib
import json
import zipfile
from pathlib import Path
from scripts.package_submission import candidates, ROOT


def main():
    destination = ROOT/'downloads/ClipAgent-macOS-Quickstart.zip'
    destination.parent.mkdir(exist_ok=True)
    files = set(candidates(ROOT))
    files.update(ROOT/name for name in ['README_EN.md','安装 ClipAgent.command','启动 ClipAgent.command'])
    files.update((ROOT/'deliverables').glob('*.pdf'))
    files.update((ROOT/'deliverables').glob('*.pptx'))
    for name in ['README.md','ClipAgent-real-demo.mp4','NASA-edited.mp4','NASA-edited.srt']:
        files.add(ROOT/'deliverables/demo'/name)
    manifest = {}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            relative = path.relative_to(ROOT).as_posix()
            manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            archive.write(path, 'ClipAgent/'+relative)
        archive.writestr('ClipAgent/QUICKSTART_MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for name in ['安装 ClipAgent.command','启动 ClipAgent.command']:
            assert (archive.getinfo('ClipAgent/'+name).external_attr >> 16) & 0o111
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.zip.sha256').write_text(f'{digest}  {destination.name}\n')
    print(json.dumps({'files':len(files),'bytes':destination.stat().st_size,'sha256':digest}))


if __name__ == '__main__': main()
