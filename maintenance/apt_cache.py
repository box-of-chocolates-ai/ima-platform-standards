"""Exact-plan APT download-cache cleanup. No shell or installed-package changes."""
import fcntl
import os
import re
import stat
import time
from node_retention import digest, require

CACHE = '/host-apt-archives'
NAME = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9.+_%:~=-]*\.deb\Z')
MIN_AGE = 7 * 86400


def inventory(fd, now):
    result = []
    names = os.listdir(fd)
    require(len(names) <= 10000, 'cache inventory bound exceeded')
    for name in sorted(names):
        if not NAME.fullmatch(name):
            continue
        s = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or now - s.st_mtime < MIN_AGE:
            continue
        result.append({'name': name, 'device': s.st_dev, 'inode': s.st_ino,
                       'size': s.st_size, 'blocks': s.st_blocks,
                       'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns})
    return result


def run(receipt, mode, policy=None, expected=None, path=CACHE, now=None):
    now = int(time.time()) if now is None else now
    require(mode in ('cache-plan', 'cache-apply'), 'invalid cache mode')
    started = time.monotonic()
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        # APT uses POSIX record locks, not BSD flock. Do not create or remove its lock.
        lock = os.open('lock', os.O_RDWR | os.O_NOFOLLOW, dir_fd=fd)
        try:
            s = os.fstat(lock)
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'unsafe apt lock')
            fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            files = inventory(fd, now)
            proposal = {'version': 1, 'node': os.environ['NODE_NAME'], 'files': files}
            plan = {**proposal, 'plan_sha256': digest(proposal)}
            receipt.save('cache-plan.json', plan)
            receipt.emit('cache_plan', **plan)
            if mode == 'cache-plan':
                return
            require(policy and policy.get('node') == os.environ['NODE_NAME'], 'node not admitted')
            require(policy.get('approval_reference') and policy.get('reference_inventory_complete') is True, 'cache authority and references required')
            created, expires = policy.get('created_at'), policy.get('expires_at')
            require(type(created) is int and type(expires) is int and created <= now < expires <= created + 86400, 'expired policy')
            require(plan == policy.get('plan') and expected == plan['plan_sha256'], 'reviewed cache plan changed')
            from retention_guard import validate
            guard = {'reference_inventory_complete': True, 'items': [
                {'id': '/var/cache/apt/archives/' + f['name'], 'kind': 'cache',
                 'contains': ['cache'], 'references': []} for f in files]}
            require(files and not validate(guard), 'retention guard rejected cache plan')
            receipt.save('guard-proposal.json', guard)
            receipt.save('policy.json', policy)
            before = os.fstatvfs(fd).f_bavail * os.fstatvfs(fd).f_frsize
            for item in files:
                require(time.monotonic() - started < 480 and time.time() < expires, 'cache operation expired')
                require(item in inventory(fd, now), 'cache file changed')
                receipt.emit('cache_remove_attempt', name=item['name'])
                os.unlink(item['name'], dir_fd=fd)
                os.fsync(fd)
                receipt.emit('cache_removed', name=item['name'])
            after = os.fstatvfs(fd).f_bavail * os.fstatvfs(fd).f_frsize
            receipt.emit('cache_completed', removed=len(files), available_before=before,
                         available_after=after, observed_delta=after-before)
        finally:
            os.close(lock)
    finally:
        os.close(fd)
