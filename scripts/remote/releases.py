"""Local filesystem release model with a SIMULATED runtime; no OS process/network."""
from __future__ import annotations

from contextlib import contextmanager
import datetime
import json
from pathlib import Path
import os
import re
import uuid

from artifacts import canonical, digest, load_bundle, no_links, verify, write_bundle
from remote import QualificationError


MARKER = {'model': 'MC-INIT-003-SIMULATION', 'schema': 1}
RELEASE_KEY = re.compile(r'[0-9a-f]{40}-[0-9a-f]{64}')


def valid_identity(value):
    return (isinstance(value,dict) and set(value) == {'pid','start','release','owner','operation'}
            and type(value['pid']) is int and value['pid'] > 0
            and all(isinstance(value[k],str) for k in ['start','release','owner','operation'])
            and bool(RELEASE_KEY.fullmatch(value['release'])))


def atomic_json(path, value):
    path = no_links(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('xb') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_json(path):
    try:
        return json.loads(no_links(path).read_bytes())
    except (OSError, ValueError) as exc:
        raise QualificationError('INVALID_LOCAL_STATE') from exc


def walk_files(root):
    stack, files = [root], {}
    while stack:
        current = no_links(stack.pop())
        for path in current.iterdir():
            no_links(path)
            if path.is_dir():
                stack.append(path)
            elif path.is_file():
                files[path.relative_to(root).as_posix()] = path.read_bytes()
            else:
                raise QualificationError('UNEXPECTED_RELEASE_ENTRY')
    return files


def ref_for(manifest):
    return {'key': manifest['git_sha'] + '-' + manifest['archive_sha256'],
            'git_sha': manifest['git_sha'], 'artifact_sha256': manifest['archive_sha256']}


class LocalStore:
    def __init__(self, root):
        self.root = no_links(root)
        if self.root.name.casefold() != 'mousse-controler-sim':
            raise QualificationError('DEDICATED_LOCAL_SIMULATION_ROOT_REQUIRED')

    def initialize(self):
        if self.root.exists():
            self.check()
            return 'REUSED_LOCAL_SIMULATION'
        self.root.mkdir(exist_ok=False)
        # No implicit import of pre-existing directories or files.
        with (self.root / '.simulation.json').open('xb') as stream:
            stream.write(canonical(MARKER))
        for name in ['source', 'staging', 'releases', 'state', 'logs']:
            (self.root/name).mkdir()
        atomic_json(self.root/'state/active.json', {'phase':'stable', 'active':None, 'previous':None, 'process':None})
        atomic_json(self.root/'state/runtime-model.json', {'next_pid':1, 'processes':[]})
        return 'INITIALIZED_LOCAL_SIMULATION'

    def check(self):
        no_links(self.root)
        if read_json(self.root/'.simulation.json') != MARKER:
            raise QualificationError('SIMULATION_MARKER_REQUIRED')
        for name in ['source','staging','releases','state','logs']:
            if not no_links(self.root/name).is_dir():
                raise QualificationError('INCOMPLETE_SIMULATION_STORE')

    @contextmanager
    def lock(self):
        self.check()
        path = no_links(self.root/'state/operation.lock')
        token = uuid.uuid4().hex
        try:
            path.mkdir(exist_ok=False)
        except FileExistsError as exc:
            raise QualificationError('OPERATION_LOCKED_MANUAL_REVIEW_REQUIRED') from exc
        try:
            with (path/'owner.json').open('xb') as stream:
                stream.write(canonical({'token':token}))
            yield
        finally:
            if read_json(path/'owner.json') != {'token':token}:
                raise QualificationError('LOCK_OWNER_CHANGED_NO_CLEANUP')
            # Only our marker and our now-empty lock, never recursive cleanup.
            (path/'owner.json').unlink()
            path.rmdir()

    def event(self, operation, event, **values):
        path = no_links(self.root/'logs/events.jsonl')
        value = {'operation':operation, 'event':event,
                 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), **values}
        with path.open('ab') as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())

    def state(self):
        value = read_json(self.root/'state/active.json')
        if not isinstance(value, dict) or value.get('phase') not in ['stable','pending','recovery_required'] or not {'active','previous','process'} <= value.keys():
            raise QualificationError('INVALID_STATE_SCHEMA')
        expected = {'phase','active','previous','process'}
        if value['phase'] != 'stable':
            expected |= {'candidate','operation','restore_operation'}
        if set(value) != expected or (value['process'] is not None and not valid_identity(value['process'])):
            raise QualificationError('INVALID_STATE_SCHEMA')
        if value['phase'] != 'stable' and any(not isinstance(value[k],str) or not re.fullmatch(r'[0-9a-f]{32}',value[k]) for k in ['operation','restore_operation']):
            raise QualificationError('INVALID_STATE_SCHEMA')
        for field in ['active','previous','candidate']:
            ref = value.get(field)
            if ref is not None and (not isinstance(ref,dict) or set(ref) != {'key','git_sha','artifact_sha256'} or not RELEASE_KEY.fullmatch(ref.get('key','')) or ref['key'] != ref['git_sha']+'-'+ref['artifact_sha256']):
                raise QualificationError('INVALID_RELEASE_REFERENCE')
        if value['process'] is not None and (value['active'] is None or value['process']['release'] != value['active']['key'] or value['process']['owner'] != 'Mousse-controler-SIMULATED'):
            raise QualificationError('STATE_PROCESS_RELEASE_MISMATCH')
        return value

    def save(self, value):
        atomic_json(self.root/'state/active.json', value)

    def release(self, ref):
        if not isinstance(ref,dict) or not RELEASE_KEY.fullmatch(ref.get('key','')):
            raise QualificationError('INVALID_RELEASE_REFERENCE')
        path = no_links(self.root/'releases'/ref['key'])
        archive, manifest = load_bundle(path/'bundle')
        if ref_for(manifest) != ref:
            raise QualificationError('RELEASE_REFERENCE_MISMATCH')
        expected = verify(archive, manifest)
        if walk_files(path/'files') != expected:
            raise QualificationError('RELEASE_CONTENT_CHANGED')
        if {p.name for p in path.iterdir()} != {'bundle','files'}:
            raise QualificationError('UNEXPECTED_RELEASE_ENTRY')
        return path

    def ingest(self, bundle, transfer_code=0):
        """A local received bundle models transfer; never calls SSH/SFTP."""
        if transfer_code != 0:
            raise QualificationError('TRANSFER_NOT_COMPLETE')
        archive, manifest = load_bundle(bundle)
        ref = ref_for(manifest)
        with self.lock():
            if self.state()['phase'] != 'stable':
                raise QualificationError('RECOVERY_REQUIRED')
            final = self.root/'releases'/ref['key']
            if final.exists():
                self.release(ref)
                return {'result':'REUSED_IDENTICAL', 'release':ref, 'runtime':'SIMULATED'}
            destinations = [final/'bundle/artifact.zip', final/'bundle/manifest.json']
            destinations += [final/'files'/entry['path'] for entry in manifest['files']]
            if any(len(str(path)) > 240 for path in destinations):
                raise QualificationError('WINDOWS_PATH_BUDGET_EXCEEDED')
            operation = uuid.uuid4().hex
            stage = self.root/'staging'/operation
            stage.mkdir(exist_ok=False)
            self.event(operation, 'ingest_begin', release=ref['key'])
            write_bundle(stage/'bundle', archive, manifest)
            files = verify(archive, manifest)
            (stage/'files').mkdir()
            for name, value in files.items():
                target = stage/'files'/name
                if len(str(target)) > 240:
                    raise QualificationError('WINDOWS_PATH_BUDGET_EXCEEDED')
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write(value)
            if walk_files(stage/'files') != files:
                raise QualificationError('STAGED_RELEASE_INCOMPLETE')
            # Cooperating operations are locked. Stale staging remains on failure.
            if final.exists():
                raise QualificationError('RELEASE_APPEARED_NO_OVERWRITE')
            stage.rename(final)
            self.event(operation, 'ingest_complete', release=ref['key'])
            return {'result':'REGISTERED_LOCAL', 'release':ref, 'runtime':'SIMULATED'}


class SimulatedRuntime:
    """Persistent model identities, never real Windows PIDs or OS handles."""
    def __init__(self, store, unhealthy=(), fail_start=(), fail_stop=False):
        self.store = store
        self.unhealthy = set(unhealthy)
        self.fail_start = set(fail_start)
        self.fail_stop = fail_stop

    def data(self):
        value = read_json(self.store.root/'state/runtime-model.json')
        if not isinstance(value,dict) or set(value) != {'next_pid','processes'} or type(value['next_pid']) is not int or not isinstance(value['processes'],list):
            raise QualificationError('INVALID_RUNTIME_MODEL')
        if value['next_pid'] < 1 or any(not valid_identity(p) for p in value['processes']) or len({p['pid'] for p in value['processes']}) != len(value['processes']):
            raise QualificationError('INVALID_RUNTIME_MODEL')
        return value

    def write(self, value):
        atomic_json(self.store.root/'state/runtime-model.json', value)

    def owned_by(self, operation):
        return [p for p in self.data()['processes'] if p.get('operation') == operation]

    def observe(self, identity):
        return next((p for p in self.data()['processes'] if p.get('pid') == identity.get('pid')), None)

    def start(self, ref, operation):
        existing = self.owned_by(operation)
        if existing:
            if len(existing) != 1 or existing[0].get('release') != ref['key']:
                raise QualificationError('RUNTIME_OPERATION_CONFLICT')
            return existing[0]
        if ref['key'] in self.fail_start:
            raise QualificationError('SIMULATED_START_FAILED')
        data = self.data()
        identity = {'pid':data['next_pid'], 'start':uuid.uuid4().hex, 'release':ref['key'],
                    'owner':'Mousse-controler-SIMULATED', 'operation':operation}
        data['next_pid'] += 1
        data['processes'].append(identity)
        self.write(data)
        return identity

    def health(self, identity):
        return self.observe(identity) == identity and identity['release'] not in self.unhealthy

    def stop(self, identity):
        current = self.observe(identity)
        if current is None:
            return 'ALREADY_ABSENT'
        if current != identity or identity.get('owner') != 'Mousse-controler-SIMULATED':
            raise QualificationError('PROCESS_IDENTITY_MISMATCH_NO_STOP')
        if self.fail_stop:
            raise QualificationError('SIMULATED_STOP_FAILED')
        data = self.data()
        data['processes'].remove(identity)
        self.write(data)
        return 'STOPPED_SIMULATED'


class ReleaseManager:
    def __init__(self, store, runtime=None, failpoint=lambda name: None):
        self.store = store
        self.runtime = runtime or SimulatedRuntime(store)
        self.failpoint = failpoint

    def stable(self):
        state = self.store.state()
        if state['phase'] != 'stable':
            raise QualificationError('RECOVERY_REQUIRED')
        return state

    def status(self):
        # Readers also lock: no incoherent view halfway through an operation.
        with self.store.lock():
            state = self.store.state()
            for ref in [state['active'], state['previous']]:
                if ref is not None:
                    self.store.release(ref)
            identity = state['process']
            observed = self.runtime.observe(identity) if identity else None
            status = 'ABSENT' if observed is None else 'RUNNING_SIMULATED' if observed == identity else 'IDENTITY_MISMATCH'
            return {'runtime':'SIMULATED', 'state':state, 'application':status,
                    'healthy': bool(identity and self.runtime.health(identity))}

    def stop(self):
        with self.store.lock():
            state = self.stable()
            result = self.runtime.stop(state['process']) if state['process'] else 'ALREADY_ABSENT'
            state['process'] = None
            self.store.save(state)
            self.store.event(uuid.uuid4().hex, 'stop', result=result)
            return {'runtime':'SIMULATED', 'result':result}

    def restore(self, pending):
        # Called with the store lock. Durable operation IDs recover start-before-save gaps.
        candidate = self.runtime.owned_by(pending['operation'])
        if len(candidate) > 1:
            raise QualificationError('AMBIGUOUS_CANDIDATE_PROCESS')
        if candidate:
            self.runtime.stop(candidate[0])
        state = {k:pending[k] for k in ['active','previous','process']}
        state['phase'] = 'stable'
        if state['active'] is None:
            state['process'] = None
        else:
            self.store.release(state['active'])
            observed = self.runtime.observe(state['process']) if state['process'] else None
            if observed is not None and observed != state['process']:
                raise QualificationError('RESTORE_PROCESS_IDENTITY_MISMATCH')
            if observed is None:
                state['process'] = self.runtime.start(state['active'], pending['restore_operation'])
            if not self.runtime.health(state['process']):
                raise QualificationError('RESTORE_HEALTH_FAILED')
        self.store.save(state)
        return state

    def activate(self, ref, before):
        self.store.release(ref)
        for saved in [before['active'],before['previous']]:
            if saved is not None:
                self.store.release(saved)
        if before['process'] and self.runtime.observe(before['process']) not in (None, before['process']):
            raise QualificationError('PROCESS_IDENTITY_MISMATCH_NO_ACTIVATION')
        if before['active'] == ref and before['process'] and self.runtime.health(before['process']):
            return {'runtime':'SIMULATED', 'result':'ALREADY_ACTIVE', 'release':ref}
        operation = uuid.uuid4().hex
        pending = {**before, 'phase':'pending', 'candidate':ref,
                   'operation':operation, 'restore_operation':uuid.uuid4().hex}
        self.store.event(operation, 'activation_begin', release=ref['key'])
        self.store.save(pending)
        try:
            self.failpoint('after_intent')
            if before['process']:
                self.runtime.stop(before['process'])
            identity = self.runtime.start(ref, operation)
            self.failpoint('after_start')
            if not self.runtime.health(identity):
                raise QualificationError('CANDIDATE_HEALTH_FAILED')
            self.failpoint('before_commit')
            previous = before['active'] if before['active'] != ref else before['previous']
            state = {'phase':'stable', 'active':ref, 'previous':previous, 'process':identity}
            self.store.save(state)
            self.store.event(operation, 'activation_complete', release=ref['key'])
            return {'runtime':'SIMULATED', 'result':'ACTIVATED_LOCAL', 'release':ref}
        except Exception as error:
            try:
                self.restore(pending)
                self.store.event(operation, 'activation_failed_restored', error=type(error).__name__)
            except Exception as restore_error:
                pending['phase'] = 'recovery_required'
                self.store.save(pending)
                self.store.event(operation, 'restore_failed', error=type(restore_error).__name__)
                raise QualificationError('ACTIVATION_FAILED_RESTORE_FAILED') from restore_error
            raise QualificationError('ACTIVATION_FAILED_PREVIOUS_RESTORED') from error

    def deploy(self, ref):
        with self.store.lock():
            return self.activate(ref, self.stable())

    def rollback(self):
        with self.store.lock():
            before = self.stable()
            if before['previous'] is None:
                raise QualificationError('NO_PREVIOUS_RELEASE')
            return self.activate(before['previous'], before)

    def recover(self):
        with self.store.lock():
            state = self.store.state()
            if state['phase'] == 'stable':
                return {'runtime':'SIMULATED','result':'NO_RECOVERY_NEEDED'}
            self.restore(state)
            self.store.event(state['operation'], 'explicit_recovery_complete')
            return {'runtime':'SIMULATED','result':'PREVIOUS_RESTORED'}
