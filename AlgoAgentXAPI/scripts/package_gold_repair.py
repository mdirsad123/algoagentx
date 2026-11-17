"""Package current project source (including uncommitted work), never credentials."""
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[2]
target = root.parent / 'AlgoAgentX_GOLD_V932_Recovery_Updated.zip'
paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z',
                                 '--cached', '--others', '--exclude-standard']).decode().split('\0')
excluded_dirs = {'.git', '.venv', 'node_modules', '.next', '__pycache__', '.pytest_cache',
                 'backup_db', 'storage', 'uploads', 'runtime_data', 'strategy_sources'}
manifest = {}
with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
    for name in sorted(set(paths)):
        if not name:
            continue
        relative = Path(name)
        path = root / relative
        if not path.is_file() or any(p in excluded_dirs for p in relative.parts):
            continue
        if (relative.name.startswith('.env') and not relative.name.endswith('example')):
            continue
        if relative.suffix.lower() in {'.pem', '.key', '.pfx', '.p12', '.dump', '.bak', '.db', '.sqlite', '.pyc', '.zip', '.log'}:
            continue
        data = path.read_bytes()
        manifest[relative.as_posix()] = hashlib.sha256(data).hexdigest()
        archive.writestr('algoagentx/' + relative.as_posix(), data)
    archive.writestr('algoagentx/ZIP_SOURCE_MANIFEST.json', json.dumps(manifest, indent=2))
with ZipFile(target) as archive:
    assert archive.testzip() is None
    for name, digest in manifest.items():
        assert hashlib.sha256(archive.read('algoagentx/' + name)).hexdigest() == digest
print(json.dumps({'zip': str(target), 'files': len(manifest), 'bytes': target.stat().st_size,
                  'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}, indent=2))