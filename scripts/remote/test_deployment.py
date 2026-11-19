"""Real temporary Git/filesystem tests; runtime model only, no SSH or real app."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

import artifacts
from artifacts import canonical, digest, load_bundle, prepare, verify, write_bundle
from deployment import sync
from releases import LocalStore, ReleaseManager, SimulatedRuntime, ref_for, read_json, atomic_json
from remote import QualificationError


def command(repo, *args):
    result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=True)
    return result.stdout.decode().strip()


def temporary():
    return tempfile.TemporaryDirectory(prefix='mc3-', dir=os.environ.get('MC_TEST_TMP'))


def make_repo(root):
    repo=root/'git-source'
    repo.mkdir()
    command(repo,'init','-q')
    (repo/'payload').mkdir()
    (repo/'payload/a.txt').write_bytes(b'version A\n')
    (repo/'payload/b.txt').write_bytes('été\n'.encode())
    (repo/'README.md').write_text('unselected documentation')
    (repo/'.gitignore').write_text('*.local\n')
    command(repo,'add','.')
    command(repo,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture A')
    first=command(repo,'rev-parse','HEAD')
    (repo/'payload/a.txt').write_bytes(b'version B\n')
    command(repo,'add','.')
    command(repo,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture B')
    return repo,first,command(repo,'rev-parse','HEAD')


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=temporary()
        cls.root=Path(cls.temporary.name)
        cls.repo,cls.sha_a,cls.sha_b=make_repo(cls.root)
        cls.archive,cls.manifest=prepare(cls.repo,cls.sha_a,['payload'])

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_exact_old_commit_not_current_worktree(self):
        files=verify(self.archive,self.manifest)
        self.assertEqual(files['payload/a.txt'],b'version A\n')
        self.assertEqual((self.repo/'payload/a.txt').read_bytes(),b'version B\n')
        self.assertEqual(set(files),{'payload/a.txt','payload/b.txt'})

    def test_reproducible_bytes_and_manifest(self):
        archive,manifest=prepare(self.repo,self.sha_a,['payload'])
        self.assertEqual(archive,self.archive)
        self.assertEqual(canonical(manifest),canonical(self.manifest))
        self.assertEqual(digest(archive),manifest['archive_sha256'])

    def test_unknown_and_invalid_sha(self):
        for sha in ['main','a'*39,'a'*40,'A'*40,'--help']:
            with self.subTest(sha=sha),self.assertRaises(QualificationError):
                prepare(self.repo,sha,['payload'])

    def test_explicit_selection_required(self):
        for include in [[],['missing'],['payload','missing'],['payload','payload'],['../outside'],['.env']]:
            with self.subTest(include=include),self.assertRaises(QualificationError):
                prepare(self.repo,self.sha_a,include)

    def test_dirty_index_worktree_untracked_refused(self):
        with temporary() as directory:
            repo,sha,_=make_repo(Path(directory))
            (repo/'payload/a.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(QualificationError,'NOT_CLEAN'):
                prepare(repo,sha,['payload'])
            command(repo,'add','payload/a.txt')
            with self.assertRaisesRegex(QualificationError,'NOT_CLEAN'):
                prepare(repo,sha,['payload'])
            # A separate clean fixture with an untracked file.
        with temporary() as directory:
            repo,sha,_=make_repo(Path(directory))
            (repo/'unknown.txt').write_bytes(b'unknown')
            with self.assertRaisesRegex(QualificationError,'NOT_CLEAN'):
                prepare(repo,sha,['payload'])

    def test_ignored_worktree_file_never_packed(self):
        ignored=self.repo/'payload/ignored.local'
        ignored.write_bytes(b'not a tracked Git object')
        try:
            archive,manifest=prepare(self.repo,self.sha_a,['payload'])
            self.assertEqual(archive,self.archive)
            self.assertEqual(manifest,self.manifest)
        finally:
            ignored.unlink()

    def test_forbidden_paths_and_windows_names(self):
        for name in ['../evil','/root','a\\b','a//b','a/./b','a/../b','CON.txt','folder/NUL',
                     'bad./x','.env','.env.production','keys/id_ed25519','cert.pem','config.local.json','a:ads','trailing./file']:
            with self.subTest(name=name),self.assertRaises(QualificationError):
                artifacts.safe_name(name)

    def test_tracked_secret_and_symlink_refused(self):
        with temporary() as directory:
            repo,_,_=make_repo(Path(directory))
            (repo/'payload/key.txt').write_bytes(b'-----BEGIN PRIVATE KEY-----\nfixture')
            command(repo,'add','.')
            command(repo,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','secret fixture')
            with self.assertRaisesRegex(QualificationError,'SUSPECTED_SECRET'):
                prepare(repo,command(repo,'rev-parse','HEAD'),['payload'])
        # Inject a real Git symlink object into an index without OS symlink privileges.
        with temporary() as directory:
            repo,_,_=make_repo(Path(directory))
            oid=command(repo,'rev-parse','HEAD:payload/a.txt')
            command(repo,'update-index','--add','--cacheinfo','120000,'+oid+',payload/link')
            command(repo,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','link fixture')
            # Index link differs from absent working tree: prepare must fail closed either way.
            with self.assertRaises(QualificationError):
                prepare(repo,command(repo,'rev-parse','HEAD'),['payload'])

    def test_git_mode_link_and_case_collision_via_tree(self):
        original=artifacts.git
        for mode,kind,name in [('120000','blob','payload/link'),('160000','commit','payload/module')]:
            def fake(repo,*args):
                if args[0]=='ls-tree':
                    return (f'{mode} {kind} '+'a'*40+'\t'+name+'\0').encode()
                return original(repo,*args)
            with self.subTest(mode=mode),patch.object(artifacts,'git',side_effect=fake),self.assertRaisesRegex(QualificationError,'SYMLINK_OR_SUBMODULE'):
                prepare(self.repo,self.sha_a,['payload'])
        def collision(repo,*args):
            if args[0]=='ls-tree':
                tree=original(repo,*args)
                entry=next(e for e in tree.split(b'\0') if e.endswith(b'payload/a.txt'))
                return entry+b'\0'+entry.replace(b'payload/a.txt',b'payload/A.txt')+b'\0'
            return original(repo,*args)
        with patch.object(artifacts,'git',side_effect=collision),self.assertRaisesRegex(QualificationError,'CASE_COLLISION'):
            prepare(self.repo,self.sha_a,['payload'])

    def test_wrong_archive_hash(self):
        with self.assertRaisesRegex(QualificationError,'HASH_MISMATCH'):
            verify(self.archive+b'extra',self.manifest)

    def test_wrong_file_hash(self):
        manifest=copy.deepcopy(self.manifest)
        manifest['files'][0]['sha256']='0'*64
        with self.assertRaisesRegex(QualificationError,'FILE_HASH_MISMATCH'):
            verify(self.archive,manifest)

    def test_incomplete_manifest_or_extra_zip_entries(self):
        for changes in [{'files':[]},{'schema':99},{'selection':['missing']}]:
            manifest={**self.manifest,**changes}
            with self.subTest(changes=changes),self.assertRaises(QualificationError):
                verify(self.archive,manifest)
        buf=io.BytesIO(self.archive)
        with zipfile.ZipFile(buf,'a') as zipped:zipped.writestr('extra.txt',b'not allowed')
        value=buf.getvalue()
        manifest={**self.manifest,'archive_sha256':digest(value)}
        with self.assertRaisesRegex(QualificationError,'CONTENT_MISMATCH'):
            verify(value,manifest)

    def test_bundle_reuse_conflict_and_incomplete(self):
        with temporary() as directory:
            output=Path(directory)/'bundle'
            self.assertEqual(write_bundle(output,self.archive,self.manifest),'PREPARED_LOCAL')
            self.assertEqual(write_bundle(output,self.archive,self.manifest),'REUSED_IDENTICAL')
            self.assertEqual(load_bundle(output),(self.archive,self.manifest))
            (output/'manifest.json').write_bytes(b'{}')
            with self.assertRaises(QualificationError):write_bundle(output,self.archive,self.manifest)
            (output/'manifest.json').unlink()
            with self.assertRaisesRegex(QualificationError,'INCOMPLETE'):load_bundle(output)

    def test_dry_run_no_output_or_network(self):
        with temporary() as directory:
            output=Path(directory)/'bundle'
            with patch('remote.Client.ssh',side_effect=AssertionError('network forbidden')):
                result=sync(self.repo,self.sha_a,['payload'],'X:\\Authorized\\Mousse-controler',output,True)
            self.assertFalse(output.exists())
            self.assertFalse(result['remote_synced'])
            self.assertEqual(result['local_result'],'NO_FILES_WRITTEN')

    def test_local_sync_distinct_from_remote_sync(self):
        with temporary() as directory:
            output=Path(directory)/'bundle'
            result=sync(self.repo,self.sha_a,['payload'],'X:\\Authorized\\Mousse-controler',output,False)
            self.assertEqual(result['local_result'],'PREPARED_LOCAL')
            self.assertFalse(result['remote_contacted'])
            self.assertIn('REMOTE_TRANSPORT_NOT_IMPLEMENTED',result['blockers'])
        with self.assertRaises(QualificationError):
            sync(self.repo,self.sha_a,['payload'],'X:\\Authorized\\Mousse-controler',self.repo/'bundle',False)


class SimulatedCrash(BaseException):
    pass


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=temporary()
        cls.fixture_root=Path(cls.fixture.name)
        repo,a,b=make_repo(cls.fixture_root)
        cls.bundles=[]
        for index,sha in enumerate([a,b]):
            archive,manifest=prepare(repo,sha,['payload'])
            path=cls.fixture_root/('bundle-'+str(index))
            write_bundle(path,archive,manifest)
            cls.bundles.append((path,ref_for(manifest)))

    @classmethod
    def tearDownClass(cls):cls.fixture.cleanup()

    def setUp(self):
        self.temp=temporary()
        self.addCleanup(self.temp.cleanup)
        self.store=LocalStore(Path(self.temp.name)/'mousse-controler-sim')
        self.store.initialize()
        for bundle,_ in self.bundles:self.store.ingest(bundle)
        self.a,self.b=[r for _,r in self.bundles]
        self.runtime=SimulatedRuntime(self.store)
        self.manager=ReleaseManager(self.store,self.runtime)

    def test_local_only_root_and_marker(self):
        with self.assertRaises(QualificationError):LocalStore(Path(self.temp.name)/'Mousse-controler')
        (self.store.root/'.simulation.json').write_bytes(b'{}')
        with self.assertRaises(QualificationError):self.manager.status()

    def test_existing_valid_version_reused_immutable(self):
        before=load_bundle(self.store.root/'releases'/self.a['key']/'bundle')
        result=self.store.ingest(self.bundles[0][0])
        self.assertEqual(result['result'],'REUSED_IDENTICAL')
        self.assertEqual(load_bundle(self.store.root/'releases'/self.a['key']/'bundle'),before)

    def test_existing_corrupt_version_never_overwritten(self):
        file=self.store.root/'releases'/self.a['key']/'files/payload/a.txt'
        file.write_bytes(b'tampered')
        with self.assertRaisesRegex(QualificationError,'CONTENT_CHANGED'):
            self.store.ingest(self.bundles[0][0])
        self.assertEqual(file.read_bytes(),b'tampered')

    def test_interrupted_transfer_no_registration(self):
        before=list((self.store.root/'staging').iterdir())
        with self.assertRaisesRegex(QualificationError,'TRANSFER_NOT_COMPLETE'):
            self.store.ingest(Path('does-not-exist'),transfer_code=255)
        self.assertEqual(list((self.store.root/'staging').iterdir()),before)

    def test_incomplete_ingest_preserves_staging(self):
        with temporary() as directory:
            other=LocalStore(Path(directory)/'mousse-controler-sim');other.initialize()
            with patch('releases.write_bundle',side_effect=QualificationError('interrupted')):
                with self.assertRaises(QualificationError):other.ingest(self.bundles[0][0])
            self.assertEqual(list((other.root/'releases').iterdir()),[])
            self.assertEqual(len(list((other.root/'staging').iterdir())),1)

    def test_deploy_status_and_idempotence(self):
        self.manager.deploy(self.a)
        status=self.manager.status()
        self.assertEqual(status['state']['active'],self.a)
        self.assertEqual(status['application'],'RUNNING_SIMULATED')
        first=status['state']['process']
        self.assertEqual(self.manager.deploy(self.a)['result'],'ALREADY_ACTIVE')
        self.assertEqual(self.manager.status()['state']['process'],first)
        self.assertEqual(len(self.runtime.data()['processes']),1)

    def test_previous_kept_and_rollback(self):
        self.manager.deploy(self.a);self.manager.deploy(self.b)
        self.assertEqual(self.manager.status()['state']['previous'],self.a)
        self.manager.rollback()
        state=self.manager.status()['state']
        self.assertEqual((state['active'],state['previous']),(self.a,self.b))
        self.assertTrue(self.manager.status()['healthy'])

    def test_no_previous_release(self):
        before=self.store.state()
        with self.assertRaisesRegex(QualificationError,'NO_PREVIOUS_RELEASE'):self.manager.rollback()
        self.assertEqual(self.store.state(),before)

    def test_first_health_failure_stays_inactive(self):
        failing=ReleaseManager(self.store,SimulatedRuntime(self.store,unhealthy=[self.a['key']]))
        with self.assertRaisesRegex(QualificationError,'PREVIOUS_RESTORED'):failing.deploy(self.a)
        self.assertIsNone(self.store.state()['active'])
        self.assertEqual(self.runtime.data()['processes'],[])

    def test_failed_candidate_restores_previous_health(self):
        self.manager.deploy(self.a)
        failing=ReleaseManager(self.store,SimulatedRuntime(self.store,unhealthy=[self.b['key']]))
        with self.assertRaisesRegex(QualificationError,'PREVIOUS_RESTORED'):failing.deploy(self.b)
        state=self.manager.status()['state']
        self.assertEqual(state['active'],self.a)
        self.assertTrue(self.manager.status()['healthy'])
        self.assertEqual(len(self.runtime.data()['processes']),1)

    def test_activation_failure_before_commit(self):
        self.manager.deploy(self.a)
        def fail(name):
            if name=='before_commit':raise OSError('simulated activation failure')
        failing=ReleaseManager(self.store,self.runtime,fail)
        with self.assertRaisesRegex(QualificationError,'PREVIOUS_RESTORED'):failing.deploy(self.b)
        self.assertEqual(self.store.state()['active'],self.a)

    def test_failed_rollback_stays_explicit_recovery_required(self):
        self.manager.deploy(self.a)
        failing=ReleaseManager(self.store,SimulatedRuntime(self.store,unhealthy=[self.a['key'],self.b['key']]))
        with self.assertRaisesRegex(QualificationError,'RESTORE_FAILED'):failing.deploy(self.b)
        self.assertEqual(self.store.state()['phase'],'recovery_required')
        with self.assertRaisesRegex(QualificationError,'RECOVERY_REQUIRED'):self.manager.deploy(self.a)
        self.manager.recover()
        self.assertEqual(self.store.state()['active'],self.a)
        self.assertEqual(self.store.state()['phase'],'stable')
        self.assertEqual(len(self.runtime.data()['processes']),1)

    def test_interruption_after_start_recovered_without_duplicate(self):
        self.manager.deploy(self.a)
        def fail(name):
            if name=='after_start':raise SimulatedCrash()
        manager=ReleaseManager(self.store,self.runtime,fail)
        with self.assertRaises(SimulatedCrash):manager.deploy(self.b)
        self.assertEqual(self.store.state()['phase'],'pending')
        self.assertEqual(len(self.runtime.data()['processes']),1)
        self.assertEqual(self.manager.recover()['result'],'PREVIOUS_RESTORED')
        self.assertEqual(self.store.state()['active'],self.a)
        self.assertEqual(len(self.runtime.data()['processes']),1)
        self.assertEqual(self.manager.recover()['result'],'NO_RECOVERY_NEEDED')

    def test_interrupt_before_stop_reuses_old_identity(self):
        self.manager.deploy(self.a)
        first=self.store.state()['process']
        def fail(name):
            if name=='after_intent':raise SimulatedCrash()
        with self.assertRaises(SimulatedCrash):ReleaseManager(self.store,self.runtime,fail).deploy(self.b)
        self.manager.recover()
        self.assertEqual(self.store.state()['process'],first)

    def test_real_cooperating_concurrency_refused(self):
        entered,finish=threading.Event(),threading.Event()
        def holder():
            with self.store.lock():entered.set();finish.wait(5)
        thread=threading.Thread(target=holder)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            with self.assertRaisesRegex(QualificationError,'OPERATION_LOCKED'):self.manager.deploy(self.a)
        finally:
            finish.set();thread.join(5)
        self.assertFalse(thread.is_alive())

    def test_stale_lock_not_auto_deleted(self):
        lock=self.store.root/'state/operation.lock';lock.mkdir()
        (lock/'owner.json').write_bytes(canonical({'token':'unknown-owner'}))
        with self.assertRaisesRegex(QualificationError,'MANUAL_REVIEW'):self.manager.status()
        self.assertTrue(lock.exists())

    def test_missing_process_and_identity_mismatch(self):
        self.manager.deploy(self.a)
        data=self.runtime.data();data['processes'][0]['start']='different-start';self.runtime.write(data)
        self.assertEqual(self.manager.status()['application'],'IDENTITY_MISMATCH')
        with self.assertRaisesRegex(QualificationError,'NO_STOP'):self.manager.stop()
        with self.assertRaisesRegex(QualificationError,'NO_ACTIVATION'):self.manager.deploy(self.b)
        self.assertEqual(len(self.runtime.data()['processes']),1)
        data=self.runtime.data();data['processes']=[];self.runtime.write(data)
        self.assertEqual(self.manager.status()['application'],'ABSENT')
        self.assertEqual(self.manager.stop()['result'],'ALREADY_ABSENT')

    def test_stop_failure_preserves_identity(self):
        self.manager.deploy(self.a);before=self.store.state()
        failing=ReleaseManager(self.store,SimulatedRuntime(self.store,fail_stop=True))
        with self.assertRaisesRegex(QualificationError,'STOP_FAILED'):failing.stop()
        self.assertEqual(self.store.state(),before)

    def test_release_extra_file_and_invalid_state_fail_closed(self):
        self.manager.deploy(self.a)
        (self.store.root/'releases'/self.a['key']/'files/extra.txt').write_bytes(b'extra')
        with self.assertRaisesRegex(QualificationError,'CONTENT_CHANGED'):self.manager.status()
        atomic_json(self.store.root/'state/active.json',{'phase':'stable'})
        with self.assertRaisesRegex(QualificationError,'INVALID_STATE'):self.manager.stop()

    def test_long_release_path_refused_before_staging(self):
        parent=Path(self.temp.name)/('p'*80);parent.mkdir()
        store=LocalStore(parent/'mousse-controler-sim');store.initialize()
        with self.assertRaisesRegex(QualificationError,'PATH_BUDGET'):
            store.ingest(self.bundles[0][0])
        self.assertEqual(list((store.root/'staging').iterdir()),[])

    def test_failed_explicit_rollback_restores_current(self):
        self.manager.deploy(self.a);self.manager.deploy(self.b)
        failing=ReleaseManager(self.store,SimulatedRuntime(self.store,unhealthy=[self.a['key']]))
        with self.assertRaisesRegex(QualificationError,'PREVIOUS_RESTORED'):failing.rollback()
        self.assertEqual(self.store.state()['active'],self.b)
        self.assertEqual(self.store.state()['previous'],self.a)

    def test_start_failure_restores_previous(self):
        self.manager.deploy(self.a)
        failing=ReleaseManager(self.store,SimulatedRuntime(self.store,fail_start=[self.b['key']]))
        with self.assertRaisesRegex(QualificationError,'PREVIOUS_RESTORED'):failing.deploy(self.b)
        self.assertEqual(self.store.state()['active'],self.a)

    def test_bundle_extra_file_and_inconsistent_process_reference(self):
        extra=self.store.root/'releases'/self.a['key']/'bundle/unlisted.txt'
        extra.write_bytes(b'unlisted')
        with self.assertRaisesRegex(QualificationError,'UNEXPECTED_BUNDLE'):
            self.store.release(self.a)
        extra.unlink()
        self.manager.deploy(self.a)
        state=self.store.state();state['process']['release']=self.b['key'];self.store.save(state)
        with self.assertRaisesRegex(QualificationError,'STATE_PROCESS_RELEASE_MISMATCH'):
            self.manager.status()


if __name__=='__main__':unittest.main(verbosity=2)
