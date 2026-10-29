#!/usr/bin/env python3
"""Release setup/control. Preserve local environments, configuration and databases."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
REGISTRY = RUNTIME / 'processes.json'
SERVICES = {
    'translator': ('src/newTranslator', ['-m', 'uvicorn', 'newTranslator.service.api:app', '--host', '0.0.0.0', '--port', '9999'], 9999),
    'agent': ('src/agent/docker-rest-agent', ['-m', 'gunicorn', 'server:app', '-c', 'gunicorn.conf.py'], 7001),
    'worker': ('src/backend', ['-m', 'celery', '-A', 'config', 'worker', '--loglevel=INFO', '--concurrency=2'], None),
    'backend': ('src/backend', ['manage.py', 'runserver', '0.0.0.0:8000', '--noreload'], 8000),
    'front': ('src/front', ['npm', 'run', 'dev', '--', '--strictPort'], 3000),
    'relayer': ('src/relayer-node', ['-m', 'relayer_node.main'], 8082),
    'fabric-oracle': ('src/backend', ['manage.py', 'oracle'], None),
}
DEFAULT = ['translator', 'agent', 'worker', 'backend', 'front']


def env():
    result = os.environ.copy()
    result.setdefault('MODE', 'local')
    result['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + result.get('PYTHONPATH', '')
    result.update(BROWSER='none', PYTHONUNBUFFERED='1')
    return result


def run(command, cwd=ROOT):
    return subprocess.run(list(map(str, command)), cwd=cwd, env=env(), check=True)


def python_for(folder):
    for name in ['.venv', 'venv']:
        candidate = ROOT / folder / name / 'bin/python'
        if candidate.exists():
            return candidate
    raise RuntimeError(f'Missing environment in {folder}; run setup first.')


def configure():
    for folder, target in [('src/backend', '.env'), ('src/front', '.env.local')]:
        source, destination = ROOT / folder / '.env.example', ROOT / folder / target
        if not destination.exists():
            shutil.copy2(source, destination)
            print(f'Created {destination.relative_to(ROOT)}; review local settings.')
        else:
            print(f'Preserved {destination.relative_to(ROOT)}')


def setup(with_relayer=False):
    configure()
    folders = ['src/backend', 'src/agent/docker-rest-agent', 'src/newTranslator']
    if with_relayer:
        folders.append('src/relayer-node')
    for folder in folders:
        directory = ROOT / folder
        created = False
        try:
            executable = python_for(folder)
        except RuntimeError:
            interpreter = shutil.which('python3.10')
            if not interpreter:
                raise RuntimeError('Install Python 3.10 for the captured dependency locks.')
            executable = directory / '.venv/bin/python'
            run([interpreter, '-m', 'venv', directory / '.venv'])
            created = True
        lock = directory / 'requirements.release.txt'
        if not lock.exists():
            lock = directory / 'requirements.txt'
        installed = json.loads(subprocess.check_output([
            str(executable), '-c',
            'import importlib.metadata as m,json;print(json.dumps([d.metadata["Name"] for d in m.distributions() if d.metadata.get("Name")]))',
        ], text=True))
        normalize = lambda name: re.sub(r'[-_.]+', '-', name.lower())
        available = {normalize(name) for name in installed}
        required = []
        for line in lock.read_text().splitlines():
            match = re.match(r'^([A-Za-z0-9_.-]+)', line.strip())
            if match:
                required.append(normalize(match.group(1)))
        consistent = subprocess.run([str(executable), '-m', 'pip', 'check'], capture_output=True).returncode == 0
        if created or not set(required).issubset(available) or not consistent:
            run([executable, '-m', 'pip', 'install', '--timeout', '120', '-r', lock])
        else:
            print(f'Preserved healthy existing environment: {executable.parent.parent}')
        if folder.endswith('newTranslator'):
            probe = subprocess.run([str(executable), '-c', 'import b2cdsl,b2cdsl_go,b2cdsl_solidity'], capture_output=True)
            if probe.returncode:
                for package in ['DSL/B2CDSL', 'CodeGenerator/b2cdsl-go', 'CodeGenerator/b2cdsl-solidity']:
                    run([executable, '-m', 'pip', 'install', '-e', directory / package])
    if not (ROOT / 'src/front/node_modules/.bin/vite').exists():
        run(['npm', 'ci'], ROOT / 'src/front')
    print('Setup complete; run doctor, then up. Healthy existing environments were preserved.')


def compose(*args):
    if not shutil.which('docker'):
        raise RuntimeError('Docker unavailable. Start Docker Desktop and enable WSL integration, or install Docker Engine/Compose.')
    run(['docker', 'compose', '-f', ROOT / 'src/backend/docker-compose.yml', *args], ROOT / 'src/backend')


def doctor():
    checks = [
        ('Node >=20.19', ['node', '-e', "let v=process.versions.node.split('.').map(Number);if(v[0]<20||(v[0]===20&&v[1]<19))process.exit(1);console.log(process.versions.node)"]),
        ('Docker Engine', ['docker', 'info', '--format', '{{.ServerVersion}}']),
        ('Docker Compose', ['docker', 'compose', 'version', '--short']),
    ]
    for name, folder, imports in [
        ('Django', 'src/backend', 'django,environ,psycopg2,celery'),
        ('Agent', 'src/agent/docker-rest-agent', 'flask,docker,gunicorn,gevent'),
        ('Translator', 'src/newTranslator', 'fastapi,textx,jinja2,networkx,b2cdsl,b2cdsl_go,b2cdsl_solidity'),
    ]:
        try:
            checks.append((name, [str(python_for(folder)), '-c', f'import {imports};print("imports OK")']))
        except RuntimeError as error:
            print(f'FAIL {name}: {error}')
            return False
    passed = True
    for name, command in checks:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=15, env=env())
            ok = result.returncode == 0
            detail = (result.stdout if ok else result.stderr).strip().splitlines()
            print(f'{"PASS" if ok else "FAIL"} {name}: {detail[-1] if detail else result.returncode}')
        except (OSError, subprocess.TimeoutExpired) as error:
            ok = False
            print(f'FAIL {name}: {error}')
        passed = passed and ok
    print(f'Optional blockchain tools: Go={shutil.which("go")}; FireFly ff={shutil.which("ff")}')
    return passed


def records():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def save(value):
    RUNTIME.mkdir(exist_ok=True)
    temporary = REGISTRY.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(REGISTRY)


def token(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def alive(record):
    return bool(record and record.get('starttime') is not None and token(record['pid']) == record['starttime'])


def listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5):
            return True
    except OSError:
        return False


def command_for(name):
    folder, args, port = SERVICES[name]
    return ROOT / folder, args if name == 'front' else [str(python_for(folder)), *args], port


def stop(name):
    registry = records()
    record = registry.get(name)
    if alive(record):
        pid = record['pid']
        if os.getpgid(pid) != pid or Path(f'/proc/{pid}/cwd').resolve() != Path(record['cwd']).resolve():
            raise RuntimeError(f'{name}: process identity changed; refusing to signal it.')
        os.killpg(pid, signal.SIGTERM)
        print(f'{name}: stopped')
    registry.pop(name, None)
    save(registry)


def start(name):
    registry = records()
    if alive(registry.get(name)):
        print(f'{name}: already running')
        return False
    cwd, command, port = command_for(name)
    if port and listening(port):
        raise RuntimeError(f'Port {port} occupied; refusing to adopt an unrelated process.')
    RUNTIME.mkdir(exist_ok=True)
    with (RUNTIME / (name + '.log')).open('a') as log:
        process = subprocess.Popen(command, cwd=cwd, env=env(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    registry[name] = {'pid': process.pid, 'starttime': token(process.pid), 'cwd': str(cwd), 'command': command}
    save(registry)
    try:
        for attempt in range(100):
            if process.poll() is not None:
                raise RuntimeError(f'{name} exited; see .runtime/{name}.log')
            if (port and listening(port)) or (not port and attempt >= 10):
                print(f'{name}: running; PID={process.pid}, port={port or "background"}')
                return True
            time.sleep(0.2)
        raise RuntimeError(f'{name} not ready; see .runtime/{name}.log')
    except Exception:
        stop(name)
        raise


def migrate():
    run([python_for('src/backend'), 'manage.py', 'migrate', '--noinput'], ROOT / 'src/backend')


def up(args):
    if not args.no_db:
        compose('up', '-d')
        for service, probe in [('postgres', ['pg_isready']), ('redis', ['redis-cli', 'ping'])]:
            for attempt in range(60):
                result = subprocess.run(['docker', 'compose', '-f', str(ROOT / 'src/backend/docker-compose.yml'), 'exec', '-T', service, *probe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError(f'{service} not ready; inspect docker compose logs {service}.')
    if not args.no_migrate:
        migrate()
    started = []
    try:
        for name in args.services:
            if start(name):
                started.append(name)
    except Exception:
        for name in reversed(started):
            stop(name)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    setup_parser = sub.add_parser('setup')
    setup_parser.add_argument('--with-relayer', action='store_true')
    for name in ['configure', 'doctor', 'check', 'down', 'stop', 'status', 'db-up', 'db-stop', 'migrate']:
        sub.add_parser(name)
    up_parser = sub.add_parser('up', aliases=['start'])
    up_parser.add_argument('--services', nargs='+', choices=SERVICES, default=DEFAULT)
    up_parser.add_argument('--no-db', action='store_true', help='Use an already provisioned external database')
    up_parser.add_argument('--no-migrate', action='store_true')
    manage_parser = sub.add_parser('manage')
    manage_parser.add_argument('args', nargs=argparse.REMAINDER)
    run_parser = sub.add_parser('run')
    run_parser.add_argument('service', choices=SERVICES)
    args = parser.parse_args()
    if args.command == 'setup':
        setup(args.with_relayer)
    elif args.command == 'configure':
        configure()
    elif args.command == 'doctor':
        return 0 if doctor() else 1
    elif args.command == 'check':
        run([python_for('src/backend'), 'manage.py', 'check'], ROOT / 'src/backend')
        run([python_for('src/newTranslator'), '-m', 'unittest', 'discover', '-s', 'src/newTranslator/CodeGenerator/b2cdsl-solidity/tests', '-v'])
        run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], ROOT / 'src/front')
    elif args.command in ['up', 'start']:
        up(args)
    elif args.command in ['down', 'stop']:
        for name in reversed(list(records())):
            stop(name)
    elif args.command == 'status':
        registry = records()
        for name, (_, _, port) in SERVICES.items():
            print(f'{name}: {"running" if alive(registry.get(name)) else "stopped"}; port={port or "-"}')
    elif args.command == 'db-up':
        compose('up', '-d')
    elif args.command == 'db-stop':
        compose('stop')
    elif args.command == 'migrate':
        migrate()
    elif args.command == 'manage':
        run([python_for('src/backend'), 'manage.py', *args.args], ROOT / 'src/backend')
    elif args.command == 'run':
        cwd, command, _ = command_for(args.service)
        run(command, cwd)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
