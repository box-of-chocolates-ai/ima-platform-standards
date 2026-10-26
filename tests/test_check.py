from copy import deepcopy
import unittest

from check import docker_errors, workload_errors


def job():
    return {'kind': 'Job', 'metadata': {'name': 'fixture'}, 'spec': {
        'ttlSecondsAfterFinished': 86400, 'template': {'spec': {'containers': [{
            'name': 'app', 'securityContext': {'runAsNonRoot': True,
                'readOnlyRootFilesystem': True, 'allowPrivilegeEscalation': False},
            'resources': {'requests': {'cpu': '10m', 'memory': '16Mi'},
                'limits': {'cpu': '100m', 'memory': '64Mi'}}}]}}}}


class Workloads(unittest.TestCase):
    def test_qualified_job(self):
        self.assertEqual([], workload_errors(job()))

    def test_qualification_hook_without_ttl_fails(self):
        value = job()
        value['metadata']['annotations'] = {'helm.sh/hook': 'pre-install'}
        del value['spec']['ttlSecondsAfterFinished']
        self.assertTrue(any('positive_ttl' in x for x in workload_errors(value)))

    def test_explicit_cron_fields_required_even_if_defaults_exist(self):
        value = {'kind': 'CronJob', 'spec': {'jobTemplate': {'spec': job()['spec']}}}
        self.assertEqual(3, len(workload_errors(value)))
        value['spec'].update(successfulJobsHistoryLimit=0, failedJobsHistoryLimit=3,
                             concurrencyPolicy='Forbid')
        self.assertEqual([], workload_errors(value))

    def test_cron_job_template_ttl_required(self):
        value = {'kind': 'CronJob', 'spec': {'successfulJobsHistoryLimit': 2,
            'failedJobsHistoryLimit': 3, 'concurrencyPolicy': 'Forbid',
            'jobTemplate': {'spec': job()['spec']}}}
        del value['spec']['jobTemplate']['spec']['ttlSecondsAfterFinished']
        self.assertEqual(1, len(workload_errors(value)))

    def test_init_container_is_checked(self):
        value = job()
        value['spec']['template']['spec']['initContainers'] = [{'name': 'init'}]
        self.assertEqual(7, len(workload_errors(value)))

    def test_nonroot_cannot_be_overridden_to_root(self):
        value = job()
        value['spec']['template']['spec']['containers'][0]['securityContext']['runAsUser'] = 0
        self.assertEqual(1, len(workload_errors(value)))

    def test_list_recursion(self):
        self.assertEqual([], workload_errors({'kind': 'List', 'items': [job(), job()]}))

    def test_boolean_is_not_a_ttl(self):
        value = job()
        value['spec']['ttlSecondsAfterFinished'] = True
        self.assertEqual(1, len(workload_errors(value)))


class Docker(unittest.TestCase):
    dockerfile = 'FROM python@sha256:abc AS builder\nRUN build\nFROM python@sha256:abc\nCOPY --from=builder /out /app\nUSER 10001:10001\n'

    def test_good(self):
        self.assertEqual([], docker_errors(self.dockerfile, '**\n!src/\n!src/**\n'))

    def test_single_stage_and_default_open_context(self):
        errors = docker_errors('FROM python:3.12\nUSER root\n', '.git\n')
        self.assertEqual(4, len(errors))

    def test_host_vendor_and_unrestricted_include(self):
        self.assertEqual(2, len(docker_errors(self.dockerfile, '**\n!vendor/**\n!**\n')))

    def test_builder_alias_is_not_external_base(self):
        text = self.dockerfile.replace('FROM python@sha256:abc\nCOPY', 'FROM builder\nCOPY')
        self.assertEqual([], docker_errors(text, '**\n!src/**\n'))


if __name__ == '__main__':
    unittest.main()
