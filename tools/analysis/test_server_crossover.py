"""Linux lifecycle checks use only synthetic children, never the research trajectory."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import termination_server_crossover as server


def host(steal=0, pressure=0, throttled=0):
    record = {'status': 'AVAILABLE', 'text': f'some avg10=0.0 avg60=0.0 avg300=0.0 total={pressure}\n'}
    return {'affinity': [0, 1], 'cgroup': '0::/test',
            'cpu': {'cpu': [0] * 7 + [steal, 0, 0]},
            'pressure': {n: dict(record) for n in ('cpu', 'memory', 'io')},
            'ancestors': {'/sys/fs/cgroup/test': {'cpu.stat': {
                'status': 'AVAILABLE', 'text': f'nr_throttled {throttled}\nthrottled_usec 0\n'}}}}


class DesignTests(unittest.TestCase):
    def test_all_random_allocations_and_rejection(self):
        self.assertEqual({tuple(server.assignment(bytes([i]) + bytes(31))) for i in range(4)},
                         {('C0', 'C1', 'C0', 'C1'), ('C0', 'C1', 'C1', 'C0'),
                          ('C1', 'C0', 'C0', 'C1'), ('C1', 'C0', 'C1', 'C0')})
        with self.assertRaises(ValueError):
            server.assignment(b'')

    def test_environment_signals_and_missing_are_preserved(self):
        self.assertEqual(server.interference_flags(host(), host()), [])
        flags = server.interference_flags(host(), host(steal=1, pressure=1, throttled=1))
        self.assertEqual(set(flags), {'HOST_STEAL_OBSERVED', 'CGROUP_THROTTLING_OBSERVED',
                         'CPU_PRESSURE_OBSERVED', 'MEMORY_PRESSURE_OBSERVED', 'IO_PRESSURE_OBSERVED'})
        missing = host()
        missing['pressure']['cpu'] = {'status': 'UNAVAILABLE'}
        missing['ancestors'] = {}
        flags = server.interference_flags(host(), missing)
        self.assertIn('CPU_PSI_UNAVAILABLE', flags)
        self.assertIn('CGROUP_CPU_ACCOUNTING_UNAVAILABLE', flags)


@unittest.skipUnless(sys.platform == 'linux', 'Linux lifecycle is validated on the designated server')
class LifecycleTests(unittest.TestCase):
    def test_complete_and_timeout_keep_only_owned_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            other = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'], start_new_session=True)
            try:
                ok = server.owned(['--worker', 'smoke-ok'], root / 'ok', 3, time.monotonic() + 10)
                self.assertEqual(ok['status'], 'COMPLETE')
                bootstrap = server.load(root / 'ok/bootstrap.json')
                self.assertEqual(bootstrap['pgrp'], bootstrap['pid'])
                self.assertEqual(bootstrap['limits']['RLIMIT_AS'], [512 * 1024**2] * 2)
                timeout = server.owned(['--worker', 'smoke-hang'], root / 'timeout', .5, time.monotonic() + 10)
                self.assertEqual(timeout['status'], 'BUDGET_INCOMPLETE')
                self.assertEqual(timeout['returncode'], -signal.SIGKILL)
                self.assertEqual(timeout['active_processes'], 0)
                self.assertIsNone(other.poll())
                self.assertTrue((root / 'timeout/bootstrap.json').exists())
                self.assertFalse((root / 'timeout/final.json').exists())
            finally:
                other.kill()
                other.wait()

    def test_parent_death_kills_only_fixture_child(self):
        with tempfile.TemporaryDirectory() as directory:
            # This fixture is the only parent killed; its child has its own process group.
            fixture = '''import json,os,pathlib,subprocess,sys,time
out=pathlib.Path(sys.argv[1]);script=sys.argv[2]
p=subprocess.Popen([sys.executable,'-B',script,'--worker','smoke-hang','--parent',str(os.getpid())],stdin=subprocess.PIPE,start_new_session=True)
p.stdin.write(json.dumps({'start':time.monotonic(),'deadline':time.monotonic()+20,'out':str(out)}).encode()+b'\\n');p.stdin.close()
while not (out/'bootstrap.json').exists():
 if p.poll() is not None:raise RuntimeError('fixture child failed')
 time.sleep(.01)
print(p.pid,flush=True)
time.sleep(30)
'''
            parent = subprocess.Popen([sys.executable, '-c', fixture, directory, str(server.SELF)],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            child_pid = None
            try:
                child_pid = int(parent.stdout.readline())
                parent.kill()
                parent.wait(timeout=3)
                limit = time.monotonic() + 3
                while time.monotonic() < limit:
                    record = server.process_record(child_pid)
                    if record is None or record['state'] == 'Z':
                        break
                    time.sleep(.01)
                self.assertTrue(record is None or record['state'] == 'Z')
            finally:
                if parent.poll() is None:
                    parent.kill()
                parent.wait()
                if child_pid and server.live_group(child_pid):
                    server.kill_owned_group(child_pid)


if __name__ == '__main__':
    unittest.main()
