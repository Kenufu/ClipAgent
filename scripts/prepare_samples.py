"""Install the included synthetic demo media without requiring macOS speech synthesis."""
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
destination=ROOT/'data/demo'
destination.mkdir(parents=True,exist_ok=True)
for source in sorted((ROOT/'sample_data/demo').glob('*.mp4')):
    target=destination/source.name
    if not target.exists():
        shutil.copyfile(source,target)
    print(f'Ready: {target.name}')
