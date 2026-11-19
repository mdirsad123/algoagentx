"""Create an explicitly local diagnostic container using existing runtime env."""
import json
import subprocess
from pathlib import Path


def main():
    assert __import__('os').name == 'nt'
    def run(*args):
        return subprocess.check_output(args)
    assert run('docker', 'context', 'show').strip() == b'desktop-linux'
    source = json.loads(run('docker', 'inspect', 'algoagentx_live_history_worker'))[0]
    env = dict(item.split('=', 1) for item in source['Config']['Env'])
    from urllib.parse import urlsplit
    assert urlsplit(env['DATABASE_URL']).hostname == 'postgres_prod'
    assert urlsplit(env['REDIS_URL']).hostname == 'redis'
    args = ['docker', 'run', '-d', '--name', 'algoagentx_recovery_diagnostic',
            '--network', 'algoagentx_default', '--memory', '1600m', '--memory-swap', '2000m',
            '--mount', f'type=bind,source={Path(__file__).resolve().parents[1]},target=/app,readonly',
            '--entrypoint', 'sleep']
    env.update(LIVE_LEGACY_RUNNER_ENABLED='false', LIVE_INCREMENTAL_MONITOR_ONLY='true',
               PYTHONDONTWRITEBYTECODE='1')
    for key, value in env.items():
        args.extend(['-e', key + '=' + value])
    args.extend([source['Image'], 'infinity'])
    print('Diagnostic container:', run(*args).decode().strip())


if __name__ == '__main__':
    main()