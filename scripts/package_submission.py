"""Build an allowlisted source snapshot with hashes, excluding runtime/private files."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('clipagent', 'web', 'scripts', 'tests', 'evaluation', 'sample_data', 'docs')
TOP = ('README.md', 'requirements.txt', 'requirements-artifacts.txt', 'requirements-browser.txt', '.gitignore', 'app.py')
EXCLUDED = {'__pycache__', '.venv', 'node_modules', '.git', '.DS_Store', '.env', 'build', '.codex-finalizer'}


def candidates(root):
    for name in TOP:
        path = root / name
        if path.is_file():
            yield path
    for folder in FOLDERS:
        for path in sorted((root / folder).rglob('*')):
            if not path.is_file() or path.is_symlink():
                continue
            if any(part in EXCLUDED for part in path.relative_to(root).parts):
                continue
            if path.suffix in {'.pyc', '.sqlite3', '.db', '.aiff'}:
                continue
            if path.stat().st_size > 30 * 1024 * 1024:
                raise ValueError(f'Large file requires an explicit packaging decision: {path.relative_to(root)}')
            yield path


def build(destination):
    files = sorted(set(candidates(ROOT)))
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    manifest = {'base_commit': commit, 'worktree_dirty_at_packaging': dirty,
                'note': 'SHA256 values identify the exact packaged files even if the base commit predates edits.', 'files': {}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            payload = path.read_bytes()
            manifest['files'][relative] = hashlib.sha256(payload).hexdigest()
            archive.writestr('Group59-ClipAgent/' + relative, payload)
        archive.writestr('Group59-ClipAgent/SUBMISSION_MANIFEST.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    print(json.dumps({'zip': str(destination), 'files': len(files), 'bytes': destination.stat().st_size, 'base_commit': commit}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'deliverables' / 'Group59-ClipAgent-Submission.zip')
    build(parser.parse_args().output)
