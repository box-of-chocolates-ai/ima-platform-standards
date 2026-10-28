"""Archive opaque old journal files before exact, reviewed removal. No log parsing."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from node_retention import digest, require

SOURCE = '/host-journal'
ARCHIVE = '/journal-archive'
NAME = re.compile(r'(?:system|user-[0-9]+)@[0-9a-f]+-[0-9a-f]+-[0-9a-f]+\.journal\Z')
MIN_AGE = 7 * 86400
MAX_BYTES = 5 * 1024**3


def metadata(fd, name):
    s = os.stat(name, dir_fd=fd, follow_symlinks=False)
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'unsafe journal file')
    return {'name': name, 'device': s.st_dev, 'inode': s.st_ino, 'size': s.st_size,
            'blocks': s.st_blocks, 'mtime_ns': str(s.st_mtime_ns), 'ctime_ns': str(s.st_ctime_ns)}


def inventory(fd, now):
    names = os.listdir(fd)
    require(len(names) <= 1000, 'journal inventory bound exceeded')
    files = []
    for name in sorted(names):
        if NAME.fullmatch(name):
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and now - s.st_mtime >= MIN_AGE:
                files.append(metadata(fd, name))
    require(sum(f['size'] for f in files) <= MAX_BYTES, 'archive byte bound exceeded')
    return files


def stream(fd, output=None):
    h = hashlib.sha256()
    total = 0
    while chunk := os.read(fd, 1024**2):
        total += len(chunk)
        require(total <= MAX_BYTES, 'file byte bound exceeded')
        h.update(chunk)
        if output is not None:
            view = memoryview(chunk)
            while view:
                n = os.write(output, view)
                require(n > 0, 'archive write failed')
                view = view[n:]
    return h.hexdigest()


def check_archive(fd, files):
    for f in files:
        src = os.open(f['name'], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            s = os.fstat(src)
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_size == f['size'], 'archive identity changed')
            require(stream(src) == f['sha256'], 'archive integrity failed')
        finally:
            os.close(src)


def run(receipt, mode, policy, expected=None, source=SOURCE, archive=ARCHIVE, now=None):
    now = int(time.time()) if now is None else now
    require(mode in ('journal-archive', 'journal-apply'), 'invalid journal mode')
    require(policy and policy.get('node') == os.environ['NODE_NAME'], 'node not admitted')
    require(policy.get('approval_reference') and policy.get('approved_by') and
            policy.get('reference_inventory_complete') is True, 'journal retention authority required')
    created, expires = policy.get('created_at'), policy.get('expires_at')
    require(type(created) is int and type(expires) is int and created <= now < expires <= created + 86400, 'expired policy')
    archive_id = policy.get('archive_id', '')
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', archive_id), 'invalid archive id')
    srcfd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    rootfd = os.open(archive, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        files = inventory(srcfd, now)
        require(files, 'no eligible archived journals')
        started = time.monotonic()
        if mode == 'journal-archive':
            os.mkdir(archive_id, mode=0o700, dir_fd=rootfd)
            os.fsync(rootfd)
            afd = os.open(archive_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
            try:
                available = os.fstatvfs(afd).f_bavail * os.fstatvfs(afd).f_frsize
                require(available >= sum(f['size'] for f in files) + 64 * 1024**2, 'archive headroom missing')
                archived = []
                for f in files:
                    require(time.monotonic()-started < 1500 and time.time() < expires, 'archive expired')
                    require(metadata(srcfd, f['name']) == f, 'journal changed before archive')
                    src = os.open(f['name'], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=srcfd)
                    dst = os.open(f['name'], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=afd)
                    try:
                        s = os.fstat(src)
                        require((s.st_dev, s.st_ino, s.st_size, str(s.st_mtime_ns), str(s.st_ctime_ns)) ==
                                (f['device'], f['inode'], f['size'], f['mtime_ns'], f['ctime_ns']), 'opened source changed')
                        content_hash = stream(src, dst)
                        os.fsync(dst)
                    finally:
                        os.close(src)
                        os.close(dst)
                    require(metadata(srcfd, f['name']) == f, 'journal changed during archive')
                    archived.append({**f, 'sha256': content_hash})
                check_archive(afd, archived)
                require(inventory(srcfd, now) == files, 'journal inventory changed during archive')
                proposal = {'version': 1, 'node': os.environ['NODE_NAME'], 'archive_id': archive_id, 'files': archived}
                plan = {**proposal, 'plan_sha256': digest(proposal)}
                out = os.open('manifest.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=afd)
                with os.fdopen(out, 'w') as fp:
                    json.dump(plan, fp, sort_keys=True)
                    fp.flush(); os.fsync(fp.fileno())
                os.fsync(afd)
                receipt.save('journal-plan.json', plan)
                receipt.emit('journal_archive_verified', **plan)
            finally:
                os.close(afd)
            return
        plan = policy.get('plan', {})
        require(plan.get('archive_id') == archive_id and plan.get('node') == os.environ['NODE_NAME'], 'wrong archive plan')
        proposal = {k: v for k, v in plan.items() if k != 'plan_sha256'}
        require(expected == plan.get('plan_sha256') == digest(proposal), 'reviewed journal plan changed')
        reviewed = plan.get('files', [])
        require(files == [{k: v for k, v in f.items() if k != 'sha256'} for f in reviewed], 'source journal inventory changed')
        afd = os.open(archive_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
        try:
            manifest = os.open('manifest.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=afd)
            with os.fdopen(manifest) as fp:
                require(json.load(fp) == plan, 'archive manifest differs from review')
            check_archive(afd, reviewed)  # Verify every recovery copy before the first unlink.
            from retention_guard import validate
            guard = {'reference_inventory_complete': True, 'items': []}
            for f in reviewed:
                identity = 'obs2:journal/' + f['name']
                guard['items'].append({'id': identity, 'kind': 'run-log', 'contains': ['run-log'],
                    'references': ['node system journal history'], 'retention_decision': {
                        'id': identity, 'action': 'delete', 'approved_by': policy['approved_by'],
                        'reason': 'Reclaim node disk after verified private archival; preserve recent and active journals',
                        'approval_reference': policy['approval_reference'],
                        'loss_or_recovery_record': archive_id + '/' + f['name'] + '#sha256=' + f['sha256']}})
            require(not validate(guard), 'retention guard rejected journals')
            receipt.save('guard-proposal.json', guard)
            receipt.save('policy.json', policy)
            before = os.fstatvfs(srcfd).f_bavail * os.fstatvfs(srcfd).f_frsize
            for f in reviewed:
                require(time.monotonic()-started < 1500 and time.time() < expires, 'journal apply expired')
                original = {k: v for k, v in f.items() if k != 'sha256'}
                require(metadata(srcfd, f['name']) == original, 'journal identity changed before removal')
                receipt.emit('journal_remove_attempt', name=f['name'], archive_sha256=f['sha256'])
                os.unlink(f['name'], dir_fd=srcfd)
                os.fsync(srcfd)
                receipt.emit('journal_removed', name=f['name'])
            after = os.fstatvfs(srcfd).f_bavail * os.fstatvfs(srcfd).f_frsize
            receipt.emit('journal_completed', removed=len(reviewed), available_before=before,
                         available_after=after, observed_delta=after-before, archive_id=archive_id)
        finally:
            os.close(afd)
    finally:
        os.close(srcfd)
        os.close(rootfd)
