"""Offline safety/error tests. No SSH/SFTP invocation or remote writes."""
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import remote
import plan_witness


ROOT = 'C:\\Qualification\\Mousse-controler'


def valid_doctor(**updates):
    data = dict(computer='mini-pc-backend', ps_version='5.1', administrator=True,
                root_exists=False, parent_exists=True, ancestor_reparse_point=False,
                parent_acl_readable=True, write_access_tested=False, git_version='git version test',
                utf8='été — témoin')
    data.update(updates)
    return remote.Result(0, json.dumps(data, ensure_ascii=False), '', 0.01)


class Tests(unittest.TestCase):
    def setUp(self):
        self.config = remote.Config('mini-pc-backend', 'mini-pc-backend', ROOT)

    def test_path_rejections(self):
        for root in ['C:\\', '\\\\server\\share', 'C:relative', ROOT + '\\..',
                     ROOT + ':stream', ROOT + "';exit 0;#", 'C:\\NUL\\Mousse-controler',
                     'C:\\other', 'C:\\parent \\Mousse-controler', 'C:/Mousse-controler']:
            with self.subTest(root=root), self.assertRaises(remote.QualificationError):
                remote.validate_root(root)

    def test_child_rejections(self):
        for child in ['..\\elsewhere', 'C:\\outside', 'state\\..\\elsewhere', 'logs:ads',
                      '\\absolute', '', 'state/../logs', 'state\\file.json;exit']:
            with self.subTest(child=child), self.assertRaises(remote.QualificationError):
                remote.child_path(ROOT, child)

    def test_allowed_spaces_and_containment(self):
        root = 'C:\\Test space\\Mousse-controler'
        self.assertEqual(remote.child_path(root, 'staging\\token'), root + '\\staging\\token')

    def test_host_and_timeout_validation(self):
        for host in ['-oProxyCommand=x', 'host;exit', 'host name', 'host\nname', 'user@host']:
            with self.subTest(host=host), self.assertRaises(remote.QualificationError):
                remote.Config(host, 'expected', ROOT)
        for timeout in [0, -1, 61, True, '20']:
            with self.subTest(timeout=timeout), self.assertRaises(remote.QualificationError):
                remote.Config('host', 'expected', ROOT, timeout)

    def test_remote_encoding_and_strict_options(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append((argv, kwargs))
            return valid_doctor()
        data = remote.Client(self.config, fake).doctor()
        self.assertTrue(data['administrator'])
        argv, options = calls[0]
        self.assertIn('StrictHostKeyChecking=yes', argv)
        self.assertIn('UpdateHostKeys=no', argv)
        self.assertIn('BatchMode=yes', argv)
        self.assertIn('PasswordAuthentication=no', argv)
        self.assertEqual(options['timeout'], 20)
        encoded = argv[-1].split()[-1]
        script = base64.b64decode(encoded).decode('utf-16-le')
        self.assertIn(ROOT, script)
        self.assertIn('été — témoin', script)
        self.assertLess(len(argv[-1]), 7501)

    def test_identity_mismatch(self):
        with self.assertRaisesRegex(remote.QualificationError, 'IDENTITY_MISMATCH'):
            remote.Client(self.config, lambda *a, **k: valid_doctor(computer='wrong-host')).doctor()

    def test_reparse_point_blocks(self):
        with self.assertRaisesRegex(remote.QualificationError, 'UNSAFE_REMOTE_ROOT'):
            remote.Client(self.config, lambda *a, **k: valid_doctor(ancestor_reparse_point=True)).doctor()

    def test_parent_access_blocks(self):
        for changes in [dict(parent_exists=False), dict(parent_acl_readable=False)]:
            with self.subTest(changes=changes), self.assertRaises(remote.QualificationError):
                remote.Client(self.config, lambda *a, **k: valid_doctor(**changes)).doctor()

    def test_schema_rejections(self):
        for changes in [dict(administrator='true'), dict(computer=None), dict(utf8='garbled')]:
            with self.subTest(changes=changes), self.assertRaises(remote.QualificationError):
                remote.Client(self.config, lambda *a, **k: valid_doctor(**changes)).doctor()
        for text in ['not json', '{}', '[]']:
            with self.subTest(text=text), self.assertRaises(remote.QualificationError):
                remote.Client(self.config, lambda *a, **k: remote.Result(0, text, '', 0)).doctor()

    def test_ssh_error_preserved_without_sensitive_stderr(self):
        with self.assertRaisesRegex(remote.QualificationError, '^SSH_DOCTOR_FAILED:255$'):
            remote.Client(self.config, lambda *a, **k: remote.Result(255, '', 'private details', 0)).doctor()

    def test_utf8_and_nonzero_streams(self):
        with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 37, 'été stdout'.encode(), 'échec stderr'.encode())):
            result = remote.run_process(['fake'])
        self.assertEqual(result.code, 37)
        self.assertEqual(result.stdout, 'été stdout')
        self.assertEqual(result.stderr, 'échec stderr')

    def test_bad_utf8_fails_closed(self):
        with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'\xff', b'')):
            with self.assertRaisesRegex(remote.QualificationError, 'INVALID_UTF8'):
                remote.run_process(['fake'])

    def test_ssh_timeout(self):
        with patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired(['ssh'], 1)):
            with self.assertRaisesRegex(remote.QualificationError, 'CLIENT_TIMEOUT'):
                remote.run_process(['ssh'], timeout=1)

    def test_missing_client(self):
        with patch.object(subprocess, 'run', side_effect=FileNotFoundError('private path')):
            with self.assertRaisesRegex(remote.QualificationError, '^CLIENT_START_FAILED$'):
                remote.run_process(['missing'])

    def test_sftp_readonly_batch(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append((argv, kwargs))
            return valid_doctor() if argv[0] == 'ssh' else remote.Result(0, 'pwd result', '', 0)
        self.assertEqual(remote.Client(self.config, fake).sftp_listing().code, 0)
        self.assertEqual(calls[-1][1]['input_bytes'], b'pwd\nquit\n')
        self.assertIn('StrictHostKeyChecking=yes', calls[-1][0])

    def test_sftp_permission_error(self):
        def fake(argv, **kwargs):
            return valid_doctor() if argv[0] == 'ssh' else remote.Result(1, '', 'denied', 0)
        with self.assertRaisesRegex(remote.QualificationError, 'SFTP_READ_FAILED:1'):
            remote.Client(self.config, fake).sftp_listing()

    def test_probe_identity_checked_first(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append(argv)
            return valid_doctor(computer='other')
        with self.assertRaises(remote.QualificationError):
            remote.Client(self.config, fake).probe('streams')
        self.assertEqual(len(calls), 1)

    def test_probes_bounded_and_fixed(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append((argv, kwargs))
            return valid_doctor()
        client = remote.Client(self.config, fake)
        client.probe('timeout')
        self.assertEqual(calls[-1][1]['timeout'], 1)
        script = base64.b64decode(calls[-1][0][-1].split()[-1]).decode('utf-16-le')
        self.assertIn('Start-Sleep -Seconds 4', script)
        with self.assertRaisesRegex(remote.QualificationError, 'UNKNOWN_PROBE'):
            client.probe('arbitrary command')

    def test_status_does_not_claim_active_release(self):
        result = remote.Client(self.config, lambda *a, **k: valid_doctor()).status()
        self.assertIsNone(result['active_sha'])
        self.assertEqual(result['application_status'], 'NON_EXÉCUTÉ')

    def test_sync_requires_full_known_sha_and_clean_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / '.git').mkdir()
            for sha in ['main', '-option', 'a' * 39, 'A' * 40, None]:
                with self.subTest(sha=sha), self.assertRaises(remote.QualificationError):
                    remote.sync_plan(self.config, repo, sha, dry_run=True)
            with patch.object(remote, 'run_process', return_value=remote.Result(1, '', '', 0)):
                with self.assertRaisesRegex(remote.QualificationError, 'UNKNOWN_COMMIT'):
                    remote.sync_plan(self.config, repo, 'a' * 40, dry_run=True)
            with patch.object(remote, 'run_process', side_effect=[remote.Result(0, 'a'*40, '', 0), remote.Result(0, '?? unknown', '', 0)]):
                with self.assertRaisesRegex(remote.QualificationError, 'NOT_CLEAN'):
                    remote.sync_plan(self.config, repo, 'a' * 40, dry_run=True)

    def test_sync_plan_idempotent_without_remote_contact(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / '.git').mkdir()
            def fake(argv, **kwargs):
                self.assertEqual(argv[0], 'git')
                return remote.Result(0, 'a'*40 if 'rev-parse' in argv else '', '', 0)
            with patch.object(remote, 'run_process', side_effect=fake):
                a = remote.sync_plan(self.config, repo, 'a'*40, dry_run=True)
                b = remote.sync_plan(self.config, repo, 'a'*40, dry_run=True)
            self.assertEqual(a, b)
            self.assertFalse(a['remote_contacted'])
            self.assertFalse(a['artifact_created'])

    def test_sync_real_execution_refused_before_git_or_network(self):
        with patch.object(remote, 'run_process') as runner:
            with self.assertRaises(remote.NotImplementedOperation):
                remote.sync_plan(self.config, Path('.'), 'a'*40, dry_run=False)
            runner.assert_not_called()

    def test_interrupted_transfer_never_passes_even_if_hash_matches(self):
        payload = b'complete-looking content'
        with self.assertRaisesRegex(remote.QualificationError, 'TRANSFER_FAILED:255'):
            remote.verify_transfer(remote.Result(255, '', 'interrupted', 0), payload, hashlib.sha256(payload).hexdigest())

    def test_wrong_hash_and_partial_payload(self):
        good = b'known full content'
        digest = hashlib.sha256(good).hexdigest()
        for payload in [good[:-1], b'', b'corrupt']:
            with self.subTest(payload=payload), self.assertRaisesRegex(remote.QualificationError, 'HASH_MISMATCH'):
                remote.verify_transfer(remote.Result(0, '', '', 0), payload, digest)
        self.assertEqual(remote.verify_transfer(remote.Result(0, '', '', 0), good, digest)['integrity'], 'PASS')

    def test_unimplemented_cli_no_network_and_explicit_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'config.json'
            config.write_text(json.dumps(self.config.__dict__))
            for operation in ['stop', 'deploy', 'rollback', 'logs']:
                with self.subTest(operation=operation), patch.object(remote, 'run_process') as runner:
                    with contextlib.redirect_stderr(io.StringIO()) as stderr:
                        code = remote.main(['--config', str(config), operation])
                    self.assertEqual(code, 3)
                    self.assertIn('NON_EXÉCUTÉ', stderr.getvalue())
                    runner.assert_not_called()

    def test_witness_plan_is_local_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(subprocess, 'run') as runner:
                plan, payload = plan_witness.build_plan(self.config, Path(folder), 'a'*32)
                runner.assert_not_called()
                self.assertEqual(list(Path(folder).iterdir()), [])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), plan['sha256'])
            self.assertEqual(plan['status'], 'REQUIRES_EXPLICIT_AUTHORIZATION')
            self.assertTrue(plan['remote_witness'].startswith(ROOT + '\\staging\\MC-INIT-002-'))

    def test_witness_creation_refuses_reuse_and_reparse(self):
        plan, _ = plan_witness.build_plan(self.config, Path('.'), 'b'*32)
        script = plan['scripts']['01-create-exclusive-directory.ps1']
        self.assertIn('Existing test directory: refuse', script)
        self.assertIn('Reparse point refused', script)
        self.assertNotIn('-Force', script.split('New-Item')[-1])

    def test_witness_delete_is_hash_guarded_and_never_recursive(self):
        plan, _ = plan_witness.build_plan(self.config, Path('.'), 'c'*32)
        script = plan['scripts']['06-remove-only-witness.ps1']
        self.assertLess(script.index('Get-FileHash'), script.index('Remove-Item'))
        self.assertIn('Remove-Item -LiteralPath $f', script)
        self.assertNotIn('-Recurse', script)
        self.assertNotIn('Remove-Item -LiteralPath $d', script)
        self.assertIn('Unexpected file: no deletion', script)

    def test_witness_process_is_bounded_and_stop_requires_identity(self):
        plan, _ = plan_witness.build_plan(self.config, Path('.'), 'd'*32)
        start = plan['scripts']['07-start-bounded-process.ps1']
        self.assertIn('-WindowStyle Hidden', start)
        self.assertIn('creation=', start)
        stop = plan['scripts']['08-stop-process.TEMPLATE.ps1']
        self.assertIn('Incomplete process identity', stop)
        self.assertIn('Process identity mismatch: no stop', stop)
        self.assertIn('PID reused', stop)
        self.assertNotIn('Stop-Process -Name', stop)

    def test_witness_token_refusals(self):
        for token in ['../other', 'a'*31, 'A'*32, 'x'*32, None]:
            with self.subTest(token=token), self.assertRaises(remote.QualificationError):
                plan_witness.build_plan(self.config, Path('.'), token)

    def test_actual_local_client_timeout_and_exit_capture(self):
        # Real subprocess behavior, no network or remote process.
        result = remote.run_process([sys.executable, '-c', "import sys;sys.stdout.buffer.write('été'.encode());sys.stderr.buffer.write('échec'.encode());sys.exit(37)"])
        self.assertEqual((result.code, result.stdout, result.stderr), (37, 'été', 'échec'))
        with self.assertRaisesRegex(remote.QualificationError, 'CLIENT_TIMEOUT'):
            remote.run_process([sys.executable, '-c', 'import time;time.sleep(2)'], timeout=0.1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
