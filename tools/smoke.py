#!/usr/bin/env python3
"""Check real SA-MP UDP responses and this boot's initialization logs.
Protocol: https://open.mp/docs/tutorials/QueryMechanism
"""
import argparse
import json
from pathlib import Path
import re
import socket
import struct
import time

ROOT = Path(__file__).resolve().parents[1]


def query(opcode, extra=b''):
    header = b'SAMP' + socket.inet_aton('127.0.0.1') + struct.pack('<H', 7777) + opcode
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(2)
        sock.connect(('127.0.0.1', 7777))
        sock.send(header + extra)
        response = sock.recv(65535)
    if not response.startswith(header):
        raise RuntimeError('Invalid SA-MP query response header')
    return response[len(header):]


def information():
    data = query(b'i')
    password, players, maxplayers = struct.unpack_from('<BHH', data)
    offset = 5
    result = dict(password=bool(password), players=players, maxplayers=maxplayers)
    for key in ['hostname', 'gamemode', 'language']:
        size, = struct.unpack_from('<I', data, offset)
        offset += 4
        result[key] = data[offset:offset + size].decode('cp1252')
        offset += size
    return result


def check():
    info = information()
    if info['hostname'] != 'San Fierro Cops And Robbers (0.3.7)':
        raise RuntimeError(f'Unexpected gamemode: {info}')
    # SA-MP excludes the 210 reserved NPC slots from the public player capacity.
    if info['maxplayers'] != 125 or 'Cops And Robbers' not in info['gamemode']:
        raise RuntimeError(f'Unexpected query information: {info}')
    if query(b'p', b'SFCN') != b'SFCN':
        raise RuntimeError('SA-MP ping payload mismatch')
    log = (ROOT / '.runtime/server_log.txt').read_text(errors='replace')
    log = log[log.rfind('Loaded log file:'):]
    for message in ['Loaded 14 plugins.', '[MYSQL]: Connection to database is successful.',
                    'SF-CnR has been successfully initialized.', '[npc:join] ChuffSec']:
        if message not in log:
            raise RuntimeError(f'Missing startup message: {message}')
    npcs = log.count('[npc:join]')
    if npcs != 210:
        raise RuntimeError(f'Expected 210 NPC joins; found {npcs}')
    failures = [line for line in log.splitlines() if re.search(
        r'Run time error|\[debug\]|\[ERROR\]|\[FCNPC\] Error|Failed|not found|Couldn.t connect',
        line, re.IGNORECASE)]
    mysql = ROOT / '.runtime/mysql_log.txt'
    if mysql.exists():
        failures += [line for line in mysql.read_text(errors='replace').splitlines()
                     if re.search(r'\[(ERROR|WARNING)\]', line)]
    if failures:
        raise RuntimeError('\n'.join(failures[:20]))
    info['npc_joins'] = npcs
    info['plugins'] = 14
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait', type=int, default=0, help='Seconds to allow for initialization')
    parser.add_argument('--duration', type=int, default=5, help='Seconds of repeated liveness checks')
    args = parser.parse_args()
    deadline = time.monotonic() + args.wait
    while True:
        try:
            result = check()
            break
        except (OSError, RuntimeError, struct.error):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    for _ in range(args.duration):
        time.sleep(1)
        result = check()
    report = ROOT / '.cache/smoke-result.json'
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print(f'PASS: UDP info/ping, 14 plugins, MySQL, 210 NPCs, clean logs, {args.duration}s stable.')


if __name__ == '__main__':
    main()
