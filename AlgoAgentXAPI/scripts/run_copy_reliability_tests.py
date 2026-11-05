r"""Run offline regressions with outbound socket connections disabled.

Usage: .venv\Scripts\python.exe scripts\run_copy_reliability_tests.py [pytest args]
"""
import os
from pathlib import Path
import socket
import sys
import inspect

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


def no_network(*args, **kwargs):
    raise AssertionError('Network disabled: reliability tests must mock broker/DB/Redis transport')


socket.create_connection = no_network
_connect = socket.socket.connect


def guarded_connect(sock, address):
    # Windows implements asyncio's private wakeup socketpair via localhost.
    # Allow only that stdlib caller, not arbitrary loopback DB/Redis traffic.
    caller = inspect.currentframe().f_back
    if caller.f_code.co_name == '_fallback_socketpair' and caller.f_globals.get('__name__') == 'socket':
        return _connect(sock, address)
    return no_network()


socket.socket.connect = guarded_connect
socket.socket.connect_ex = no_network

if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main(sys.argv[1:] or ['tests', '--ignore=tests/local_debug', '-q', '-ra']))