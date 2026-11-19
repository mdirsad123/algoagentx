"""Windows-only rollback capture. Never prints credentials or alters DB rows."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from datetime import datetime, timezone


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def main():
    root = Path(__file__).resolve().parents[2]
    assert __import__('os').name == 'nt', 'Local Windows only'
    assert run('docker', 'context', 'show').strip() == b'desktop-linux'
    import sys
    resume = len(sys.argv) == 2
    backup = Path(sys.argv[1]) if resume else root.parent / ('recovery_rollback_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(exist_ok=resume)
    names = set(run('git', '-C', str(root), 'ls-files', '-z').decode().split('\0'))
    names.update(run('git', '-C', str(root), 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0'))
    with zipfile.ZipFile(backup / 'working-tree.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names - {''}):
            path = root / name
            if path.is_file() and not path.name.startswith('.env'):
                archive.write(path, name)
    with zipfile.ZipFile(backup / 'working-tree.zip') as archive:
        assert archive.testzip() is None
    (backup / 'working-tree.diff').write_bytes(run('git', '-C', str(root), 'diff', 'HEAD'))
    (backup / 'git-status.txt').write_bytes(run('git', '-C', str(root), 'status', '--short'))
    containers = json.loads(run('docker', 'ps', '-q') and run('docker', 'inspect', *run('docker', 'ps', '-q').decode().split()))
    safe = [{'name': c['Name'], 'image': c['Image'], 'status': c['State']['Status']} for c in containers]
    (backup / 'containers.json').write_text(json.dumps(safe, indent=2))
    # pg_dump uses the local container's existing authentication, not a remote URL.
    if not resume:
        run('docker', 'exec', 'algoagentx_postgres_prod', 'pg_dump', '-U', 'algoagentx_user',
            '-d', 'algoagentx_prod', '-Fc', '-f', '/tmp/nas100-recovery-rollback.dump')
    run('docker', 'exec', 'algoagentx_postgres_prod', 'pg_restore', '-f', '/dev/null', '/tmp/nas100-recovery-rollback.dump')
    toc = run('docker', 'exec', 'algoagentx_postgres_prod', 'pg_restore', '-l', '/tmp/nas100-recovery-rollback.dump')
    assert b'strategy_deployments' in toc and b'live_market_candles' in toc
    run('docker', 'cp', 'algoagentx_postgres_prod:/tmp/nas100-recovery-rollback.dump', str(backup / 'postgres.dump'))
    (backup / 'postgres-toc.txt').write_bytes(toc)
    run('docker', 'exec', 'algoagentx_redis', 'redis-cli', '--rdb', '/tmp/nas100-recovery-rollback.rdb')
    checked = run('docker', 'exec', 'algoagentx_redis', 'redis-check-rdb', '/tmp/nas100-recovery-rollback.rdb')
    assert b'Checksum OK' in checked
    run('docker', 'cp', 'algoagentx_redis:/tmp/nas100-recovery-rollback.rdb', str(backup / 'redis.rdb'))
    manifest = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()}
                for p in backup.iterdir() if p.is_file()}
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print('ROLLBACK_DIRECTORY=' + str(backup))
    print('Code archive CRC, PostgreSQL archive TOC, Redis RDB checksum verified.')
    print(json.dumps({k: v['bytes'] for k, v in manifest.items()}))


if __name__ == '__main__':
    main()