#!/usr/bin/env python3
"""Check rendered workload contracts and built image budgets without mutation."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess

import yaml


def workload_errors(document):
    if not isinstance(document, dict):
        return []
    kind, spec = document.get('kind'), document.get('spec', {})
    errors = []
    if kind == 'List':
        return [e for item in document.get('items', []) for e in workload_errors(item)]
    if kind == 'CronJob':
        for key in ('successfulJobsHistoryLimit', 'failedJobsHistoryLimit'):
            if type(spec.get(key)) is not int or spec[key] < 0:
                errors.append('cronjob.explicit_' + key)
        if spec.get('concurrencyPolicy') not in ('Forbid', 'Allow', 'Replace'):
            errors.append('cronjob.explicit_concurrencyPolicy')
        spec = spec.get('jobTemplate', {}).get('spec', {})
    if kind in ('Job', 'CronJob'):
        if type(spec.get('ttlSecondsAfterFinished')) is not int or spec['ttlSecondsAfterFinished'] <= 0:
            errors.append('job.positive_ttlSecondsAfterFinished')
    if kind not in ('Job', 'CronJob', 'Deployment', 'StatefulSet', 'DaemonSet', 'ReplicaSet', 'Pod'):
        return errors
    pod = spec if kind == 'Pod' else spec.get('template', {}).get('spec', {})
    if not pod.get('containers'):
        errors.append('pod.containers_missing')
    shared = pod.get('securityContext', {})
    for container in pod.get('containers', []) + pod.get('initContainers', []):
        name = container.get('name', 'unnamed')
        security = dict(shared, **container.get('securityContext', {}))
        for key in ('cpu', 'memory'):
            for level in ('requests', 'limits'):
                if not container.get('resources', {}).get(level, {}).get(key):
                    errors.append(name + '.resources.' + level + '.' + key)
        if security.get('runAsNonRoot') is not True or security.get('runAsUser') == 0:
            errors.append(name + '.security.non_root')
        for key, expected in (('readOnlyRootFilesystem', True), ('allowPrivilegeEscalation', False)):
            if container.get('securityContext', {}).get(key) is not expected:
                errors.append(name + '.security.' + key)
    prefix = kind + '/' + document.get('metadata', {}).get('name', 'unnamed') + ':'
    return [prefix + error for error in errors]


def docker_errors(text, ignore):
    errors = []
    # Join continuations before interpreting instructions, ignoring comments.
    lines = [line.strip() for line in text.replace('\\\n', ' ').splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    stages = [line for line in lines if re.match(r'FROM\s', line, re.I)]
    if len(stages) < 2 or not any(re.match(r'COPY\s+.*--from=', line, re.I) for line in lines):
        errors.append('docker.multistage_artifact_copy')
    stage_names = set()
    for stage in stages:
        parts = stage.split()
        image = next((p for p in parts[1:] if not p.startswith('--')), '')
        if image not in stage_names and image != 'scratch' and '@sha256:' not in image:
            errors.append('docker.base_digest:' + image)
        if len(parts) >= 4 and parts[-2].lower() == 'as':
            stage_names.add(parts[-1])
    runtime = lines[lines.index(stages[-1]) + 1:] if stages else []
    users = [line.split(None, 1)[1] for line in runtime if re.match(r'USER\s', line, re.I)]
    if not users or users[-1].split(':')[0] in ('0', 'root'):
        errors.append('docker.runtime_non_root')
    rules = [line.strip() for line in ignore.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if not rules or rules[0] != '**':
        errors.append('dockerignore.default_deny')
    for rule in rules:
        if rule in ('!**', '!*', '!**/*', '!/', '!.'):
            errors.append('dockerignore.unrestricted_include')
        if rule.startswith('!') and re.search(r'(^|/)(\.git|\.env[^/]*|node_modules|vendor|credentials)(/|$)', rule[1:]):
            errors.append('dockerignore.sensitive_include:' + rule)
    return errors


def image_errors(image, limit):
    if type(limit) is not int or limit <= 0:
        return ['image.positive_budget_required']
    result = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{.Size}}'],
                            text=True, capture_output=True, timeout=30, check=True)
    size = int(result.stdout.strip())
    return ['image.size_exceeds_budget:' + str(size) + '>' + str(limit)] if size > limit else []


def apply_exceptions(errors, exceptions, today=None):
    today = today or date.today()
    exempt = set()
    for entry in exceptions:
        if (type(entry) is not dict or set(entry) != {'error', 'reason', 'expires'}
                or not isinstance(entry['error'], str) or not isinstance(entry['reason'], str)
                or len(entry['reason']) < 40
                or date.fromisoformat(entry['expires']) < today):
            raise ValueError('invalid or expired explicit exception')
        exempt.add(entry['error'])
    return [error for error in errors if error not in exempt]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', action='append', default=[])
    parser.add_argument('--dockerfile', type=Path)
    parser.add_argument('--ignore', type=Path)
    parser.add_argument('--image')
    parser.add_argument('--exceptions', type=Path)
    parser.add_argument('--max-image-bytes', type=int)
    args = parser.parse_args()
    if not (args.manifest or args.dockerfile or args.image):
        parser.error('at least one check target required')
    if bool(args.dockerfile) != bool(args.ignore):
        parser.error('--dockerfile and --ignore are a pair')
    errors = []
    for path in args.manifest:
        documents = [d for d in yaml.safe_load_all(Path(path).read_text()) if d is not None]
        if not documents:
            errors.append('manifest.empty:' + path)
        for document in documents:
            errors.extend(workload_errors(document))
    if args.dockerfile:
        errors.extend(docker_errors(args.dockerfile.read_text(), args.ignore.read_text()))
    if args.image:
        errors.extend(image_errors(args.image, args.max_image_bytes))
    original = list(errors)
    if args.exceptions:
        errors = apply_exceptions(errors, json.loads(args.exceptions.read_text()))
    print(json.dumps({'passed': not errors, 'errors': errors,
                      'explicit_exceptions_used': sorted(set(original) - set(errors))}, indent=2))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
