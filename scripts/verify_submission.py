"""Verify ZIP hashes, extract to a fresh directory, and run tests using this Python."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def verify(archive_path, output):
    with tempfile.TemporaryDirectory(prefix='clipagent-submission-') as directory:
        with zipfile.ZipFile(archive_path) as archive:
            manifest=json.loads(archive.read('Group59-ClipAgent/SUBMISSION_MANIFEST.json'))
            for name, digest in manifest['files'].items():
                if Path(name).is_absolute() or '..' in Path(name).parts:
                    raise ValueError('Unsafe archive member')
                assert hashlib.sha256(archive.read('Group59-ClipAgent/'+name)).hexdigest()==digest, name
            archive.extractall(directory)
        root=Path(directory)/'Group59-ClipAgent'
        clean_env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        run=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,env=clean_env,text=True,capture_output=True,timeout=300)
        result={'archive':Path(archive_path).name,'sha256':hashlib.sha256(Path(archive_path).read_bytes()).hexdigest(),
                'files_verified':len(manifest['files']),'python':sys.version,'extracted_tests_exit_code':run.returncode,
                'test_log':run.stdout+run.stderr,'scope':'Fresh extracted source; dependencies are those installed in the interpreter that runs this command.'}
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2))
        print(json.dumps({k:v for k,v in result.items() if k!='test_log'},indent=2))
        return run.returncode


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path,default=Path('deliverables/package-verification.json'))
    args=parser.parse_args()
    raise SystemExit(verify(args.archive,args.output))
