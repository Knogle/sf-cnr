#!/usr/bin/env python3
"""Reproducible local SA-MP 0.3.7 setup; Python standard library only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import struct
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/downloads'
RUNTIME = ROOT / '.runtime'
LOCAL = ROOT / '.local'
LABEL = 'org.sfcnr.workspace'
DB = 'sf-cnr-db'
SERVER = 'sf-cnr-server'
IMAGE = 'localhost/sf-cnr-runtime'
DB_IMAGE = 'docker.io/library/mariadb:10.11@sha256:5ae7fc7b20f8e07c0ee169ff24617b39cb99b4bfc147555cea758baa69834d9e'


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def engine():
    value = os.environ.get('CONTAINER_ENGINE') or shutil.which('podman') or shutil.which('docker')
    if not value:
        raise RuntimeError('Install Podman or Docker, or set CONTAINER_ENGINE.')
    return value


def inspect(name):
    result = subprocess.run([engine(), 'container', 'inspect', name], capture_output=True, text=True)
    if result.returncode:
        return None
    data = json.loads(result.stdout)[0]
    if data['Config'].get('Labels', {}).get(LABEL) != str(ROOT):
        raise RuntimeError(f'{name} belongs to another setup; refusing to change it.')
    return data


def stopped():
    data = inspect(SERVER)
    if data and data['State']['Running']:
        raise RuntimeError('Stop the local server with tools/local.py down before setup/build.')


def download(item):
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / item['name']
    if not target.exists():
        partial = target.with_suffix('.part')
        print(f"Downloading {item['name']}", flush=True)
        with urllib.request.urlopen(item['url'], timeout=60) as src, partial.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        partial.replace(target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
        raise RuntimeError(f"Checksum mismatch: {target}. Remove it before retrying.")
    return target


def install(item):
    source = download(item)
    matched = set()

    def copy_member(name, stream, mode=0o644):
        for prefix, destination in item['files'].items():
            if name == prefix or (prefix.endswith('/') and name.startswith(prefix)):
                suffix = name[len(prefix):] if prefix.endswith('/') else ''
                out = ROOT / destination / suffix if prefix.endswith('/') else ROOT / destination
                if not out.resolve().is_relative_to(ROOT):
                    raise RuntimeError(f'Unsafe archive path: {name}')
                out.parent.mkdir(parents=True, exist_ok=True)
                with out.open('wb') as dst:
                    shutil.copyfileobj(stream, dst)
                out.chmod(mode & 0o777)
                matched.add(prefix)
                break

    if item['kind'] == 'file':
        with source.open('rb') as src:
            copy_member('', src)
    elif item['kind'] == 'zip':
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                if not member.is_dir():
                    with archive.open(member) as src:
                        copy_member(member.filename, src)
    else:
        with tarfile.open(source) as archive:
            for member in archive:
                if member.isfile():
                    with archive.extractfile(member) as src:
                        copy_member(member.name, src, member.mode)
    if matched != set(item['files']):
        raise RuntimeError(f"Missing archive members in {item['name']}: {set(item['files']) - matched}")


def clear_execstack(path):
    """Clear the obsolete GNU_STACK X bit on MerRandom's ELF32 header only."""
    data = bytearray(path.read_bytes())
    if data[:6] != b'\x7fELF\x01\x01':
        raise RuntimeError(f'Expected little-endian ELF32: {path}')
    offset = struct.unpack_from('<I', data, 28)[0]
    size, count = struct.unpack_from('<HH', data, 42)
    for i in range(count):
        pos = offset + size * i
        if struct.unpack_from('<I', data, pos)[0] == 0x6474e551:
            flags = struct.unpack_from('<I', data, pos + 24)[0]
            struct.pack_into('<I', data, pos + 24, flags & ~1)
            path.write_bytes(data)
            return
    raise RuntimeError('MerRandom GNU_STACK header not found')


def settings():
    path = LOCAL / 'settings.json'
    if not path.exists():
        LOCAL.mkdir(exist_ok=True)
        path.write_text(json.dumps({'db_password': secrets.token_hex(24),
                                    'rcon_password': secrets.token_hex(24)}, indent=2) + '\n')
        path.chmod(0o600)
    return json.loads(path.read_text())


def configure():
    config = settings()
    db_path = ROOT / 'gamemodes/irresistible/config/database.pwn'
    if not db_path.exists():
        content = db_path.with_suffix('.pwn.sample').read_text()
        for key, value in {'HOST': '127.0.0.1', 'USER': 'sfcnr',
                           'PASS': config['db_password'], 'DATABASE': 'sfcnr'}.items():
            content = re.sub(r'(#define MYSQL_' + key + r'\s+)"[^"]*"',
                             lambda m: m[1] + '"' + value + '"', content)
        content = content.replace('MYSQL_DATABASE, MYSQL_PASS )', 'MYSQL_DATABASE, MYSQL_PASS, 3307 )')
        db_path.write_text(content)
        db_path.chmod(0o600)
    cfg = RUNTIME / 'server.cfg'
    if not cfg.exists():
        cfg.write_text((ROOT / 'tools/server.cfg.in').read_text().format(**config))
        cfg.chmod(0o600)
    env = LOCAL / 'database.env'
    env.write_text('MARIADB_RANDOM_ROOT_PASSWORD=1\nMARIADB_DATABASE=sfcnr\nMARIADB_USER=sfcnr\n'
                   f"MARIADB_PASSWORD={config['db_password']}\n")
    env.chmod(0o600)


def setup():
    stopped()
    items = json.loads((ROOT / 'tools/dependencies.lock.json').read_text())
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(install, items))
    clear_execstack(RUNTIME / 'plugins/merrandom.so')
    shutil.copy2(ROOT / 'plugins/TPoker.so', RUNTIME / 'plugins/TPoker.so')
    for folder in ['gamemodes', 'npcmodes/recordings', 'filterscripts', 'scriptfiles/logs']:
        (RUNTIME / folder).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'scriptfiles/changelogs', RUNTIME / 'scriptfiles/changelogs', dirs_exist_ok=True)
    for recording in (ROOT / 'npcmodes/recordings').glob('*.rec'):
        shutil.copy2(recording, RUNTIME / 'npcmodes/recordings' / recording.name)
    for name in ['samp03svr', 'samp-npc']:
        (RUNTIME / name).chmod(0o755)
    configure()
    print('Includes, compiler, 14 plugins, GPS, height maps and NPC recordings installed.')


def build():
    stopped()
    compiler = ROOT / '.deps/compiler/bin/pawncc'
    env = dict(os.environ, LD_LIBRARY_PATH=str(ROOT / '.deps/compiler/lib'), LC_ALL='C')
    (ROOT / '.cache').mkdir(exist_ok=True)
    for folder, name in [('gamemodes', 'sf-cnr'), ('npcmodes', 'secureguard')]:
        output = RUNTIME / folder / f'{name}.amx'
        temporary = output.with_suffix('.build.amx')
        args = [compiler, f'{name}.pwn', f'-D{ROOT / folder}', f'-i{ROOT / "include"}',
                '-Z', '-;+', '-(+', '-d3', '-E', f'-o{temporary}']
        result = subprocess.run([str(x) for x in args], env=env, capture_output=True, text=True)
        (ROOT / '.cache' / f'build-{name}.log').write_text(result.stdout + result.stderr)
        print(result.stdout + result.stderr, end='')
        if result.returncode:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f'{name} build failed; previous AMX retained.')
        temporary.replace(output)


def sql(query):
    env = dict(os.environ, MYSQL_PWD=settings()['db_password'])
    result = run([engine(), 'exec', '-i', '--env', 'MYSQL_PWD', DB,
                  'mariadb', '-usfcnr', '-N', '-B', 'sfcnr'],
                 input=query, text=True, capture_output=True, env=env)
    return result.stdout.strip()


def database():
    data = inspect(DB)
    if not data:
        run([engine(), 'run', '-d', '--name', DB, '--label', f'{LABEL}={ROOT}',
             '-p', '127.0.0.1:3307:3306', '--env-file', LOCAL / 'database.env',
             '-v', 'sf-cnr-db-data:/var/lib/mysql', DB_IMAGE, '--sql-mode=NO_ENGINE_SUBSTITUTION'])
    elif not data['State']['Running']:
        run([engine(), 'start', DB])
    for _ in range(60):
        ready = subprocess.run([engine(), 'exec', DB, 'healthcheck.sh', '--connect', '--innodb_initialized'],
                               capture_output=True)
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('MariaDB did not become ready; inspect container logs.')
    sql('CREATE TABLE IF NOT EXISTS _SFCNR_SETUP_MIGRATIONS '
        '(name VARCHAR(100) PRIMARY KEY, sha256 CHAR(64) NOT NULL);')
    for path in sorted((ROOT / 'gamemodes/irresistible/config/migrations/cnr').glob('*.sql')):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        existing = sql(f"SELECT sha256 FROM _SFCNR_SETUP_MIGRATIONS WHERE name='{path.stem}';")
        if existing:
            if existing != digest:
                raise RuntimeError(f'Previously applied migration changed: {path.name}')
            continue
        print(f'Applying {path.name}', flush=True)
        sql(path.read_text())
        sql(f"INSERT INTO _SFCNR_SETUP_MIGRATIONS VALUES ('{path.stem}', '{digest}');")


def up():
    data = inspect(SERVER)
    if data and data['State']['Running']:
        print('Server already running at 127.0.0.1:7777')
        return
    if not (RUNTIME / 'gamemodes/sf-cnr.amx').exists():
        raise RuntimeError('Run setup and build first.')
    database()
    run([engine(), 'build', '-t', IMAGE, '-f', ROOT / 'tools/Dockerfile.runtime', ROOT / 'tools'])
    if data:
        run([engine(), 'rm', SERVER])
    # Preserve previous diagnostics while keeping each smoke check specific to this boot.
    for name in ['server_log.txt', 'mysql_log.txt']:
        log = RUNTIME / name
        if log.exists():
            log.replace(ROOT / '.cache' / f'{name}.{time.time_ns()}')
    run([engine(), 'run', '-d', '--name', SERVER, '--label', f'{LABEL}={ROOT}',
         '--network', 'host', '--stop-signal', 'SIGINT',
         '-v', f'{RUNTIME}:/server:Z', IMAGE])
    run([sys.executable, ROOT / 'tools/smoke.py', '--wait', '45'])


def down():
    for name in [SERVER, DB]:
        data = inspect(name)
        if data and data['State']['Running']:
            run([engine(), 'stop', '--time', '15', name])
    print('Stopped. Database volume and server files retained.')


def status():
    for name in [SERVER, DB]:
        data = inspect(name)
        print(f"{name}: {data['State']['Status'] if data else 'not created'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup', 'build', 'up', 'down', 'status', 'smoke'])
    command = parser.parse_args().command
    if command == 'smoke':
        run([sys.executable, ROOT / 'tools/smoke.py'])
    else:
        globals()[command]()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(1)
