"""Provision one reviewed profile. No shell, runtime socket, overwrite or removal."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

PROFILE_SHA256 = '6a1e2c43f45b4a5ed038355a4533ce3cdb033178491a3e9c969861079bc7c233'
PROFILE_BYTES = 9218
FILENAME = f'patchright-{PROFILE_SHA256}.json'


def checked_profile(data):
    """Admit only the reviewed, cap-drop-ALL amd64 OCI bytes."""
    if len(data) != PROFILE_BYTES or hashlib.sha256(data).hexdigest() != PROFILE_SHA256:
        raise ValueError('profile bytes differ from reviewed input')
    return data


def validate_request(request, actual_node, expected_node_uid, now):
    """Require the exact reviewed node/profile and short-lived operation identity."""
    keys = {'schema_version', 'node', 'node_uid', 'run_id', 'profile_sha256', 'expires_at'}
    if not isinstance(request, dict) or set(request) != keys or type(request['schema_version']) is not int or request['schema_version'] != 1:
        raise ValueError('request schema rejected')
    if request['node'] != 'pc2' or actual_node != 'pc2' or request['node_uid'] != expected_node_uid or not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', expected_node_uid):
        raise ValueError('node binding rejected')
    if request['profile_sha256'] != PROFILE_SHA256:
        raise ValueError('profile binding rejected')
    if not isinstance(request['run_id'], str) or not re.fullmatch(r'patchright-[a-z0-9-]{1,30}', request['run_id']):
        raise ValueError('run identity rejected')
    expires = datetime.fromisoformat(request['expires_at'])
    if expires.tzinfo is None or not 0 < (expires - now).total_seconds() <= 3600:
        raise ValueError('expired or overlong operation')


def read_exact(dir_fd, name):
    """Read a single regular no-follow file through a bound directory descriptor."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o222 or info.st_uid != os.geteuid():
            raise ValueError('profile must be regular, single-link and read-only')
        return checked_profile(stream.read(PROFILE_BYTES + 1))


def write_new(path, value):
    """Create and flush durable evidence without replacing another run."""
    with path.open('xb') as out:
        out.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
        out.flush()
        os.fsync(out.fileno())
    fd = os.open(path.parent, os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def provision(request, data, target, receipts, actual_node, expected_node_uid, clock=None):
    """Persist intent, atomically link exact bytes, read back and persist completion."""
    clock = clock or (lambda: datetime.now(timezone.utc))
    validate_request(request, actual_node, expected_node_uid, clock())
    checked_profile(data)
    target_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(target_fd)
        if info.st_mode & 0o022 or info.st_uid != os.geteuid():
            raise ValueError('target directory is writable by another identity')
        run = receipts / request['run_id']
        run.mkdir(mode=0o700)  # Existing run means uncertain/repeated execution: stop.
        receipts_fd = os.open(receipts, os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(receipts_fd)
        finally:
            os.close(receipts_fd)
        write_new(run / 'intent.json', dict(request=request, state='intent', installed=False))
        try:
            read_exact(target_fd, FILENAME)
            action = 'existing_exact_read_only_profile'
        except FileNotFoundError:
            pending = '.pending-' + request['run_id']
            fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o444, dir_fd=target_fd)
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            validate_request(request, actual_node, expected_node_uid, clock())
            # link() never replaces a destination; profile becomes visible complete.
            os.link(pending, FILENAME, src_dir_fd=target_fd, dst_dir_fd=target_fd,
                    follow_symlinks=False)
            os.unlink(pending, dir_fd=target_fd)
            os.fsync(target_fd)
            action = 'installed_new_profile'
        read_exact(target_fd, FILENAME)
        result = dict(request=request, state='complete', action=action,
                      profile_sha256=PROFILE_SHA256, profile_bytes=PROFILE_BYTES,
                      localhost_profile='captcha-lab/' + FILENAME,
                      node_uid_binding='expected; operator must verify actual Node UID',
                      native_qualified=False, observed_at=clock().isoformat())
        write_new(run / 'receipt.json', result)
        return result
    finally:
        os.close(target_fd)


def main():
    """Use fixed mounts and the actual scheduled node, never arbitrary host paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, default=Path('/profile/request.json'))
    args = parser.parse_args()
    if os.getuid() != 0:
        raise ValueError('scoped root-owned directory provisioning requires UID 0')
    result = provision(json.loads(args.request.read_text()),
                       Path('/profile/profile.json').read_bytes(), Path('/host-seccomp'),
                       Path('/receipts'), os.environ['NODE_NAME'], os.environ['EXPECTED_NODE_UID'])
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
