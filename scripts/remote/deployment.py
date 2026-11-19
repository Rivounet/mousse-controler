"""MC-INIT-003 CLI: local Git preparation and filesystem/runtime simulation only."""
import argparse
import json
from pathlib import Path
import sys

from artifacts import SHA, git, no_links, prepare, write_bundle
from releases import LocalStore, ReleaseManager
from remote import Config, QualificationError, validate_root


def sync(repository, sha, include, remote_root, output=None, dry_run=False):
    root = validate_root(remote_root)
    archive, manifest = prepare(repository, sha, include)
    if output is not None:
        destination = no_links(output)
        repo_root = Path(git(repository, 'rev-parse','--show-toplevel').decode('utf-8').strip()).absolute()
        if destination == repo_root or repo_root in destination.parents or destination in repo_root.parents:
            raise QualificationError('BUNDLE_MUST_BE_OUTSIDE_REPOSITORY')
    result = {'mode':'LOCAL_DRY_RUN' if dry_run else 'LOCAL_PREPARATION',
              'git_sha':manifest['git_sha'], 'artifact_sha256':manifest['archive_sha256'],
              'files':manifest['files'], 'selection':manifest['selection'],
              'remote_target':root+'\\staging\\'+manifest['git_sha']+'-'+manifest['archive_sha256'],
              'remote_contacted':False, 'remote_synced':False,
              'remote_checks':'NON_EXÉCUTÉ',
              'required_remote_checks':['identity','authorized root','permissions','free space',
                                        'exclusive lock','source Git state if present','artifact integrity','existing release'],
              'planned_operations':['transfer to unique staging after authorization','verify SHA-256',
                                    'extract explicitly listed files','register release without overwriting'],
              'blockers':['REMOTE_TRANSPORT_NOT_IMPLEMENTED', 'DISTINCT_REMOTE_AUTHORIZATION_REQUIRED']}
    if not dry_run:
        if output is None:
            raise QualificationError('LOCAL_OUTPUT_REQUIRED')
        result['local_result'] = write_bundle(output, archive, manifest)
    else:
        result['local_result'] = 'NO_FILES_WRITTEN'
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('sync')
    build.add_argument('--repository',type=Path,required=True)
    build.add_argument('--ref',required=True)
    build.add_argument('--include',action='append',required=True)
    build.add_argument('--config',type=Path,required=True)
    build.add_argument('--output',type=Path)
    build.add_argument('--dry-run',action='store_true')
    model=sub.add_parser('model',help='Local simulation; never real deployment')
    model.add_argument('--root',type=Path,required=True)
    actions=model.add_subparsers(dest='action',required=True)
    for action in ['init','status','stop','rollback','recover']:
        actions.add_parser(action)
    register=actions.add_parser('ingest')
    register.add_argument('--bundle',type=Path,required=True)
    deploy=actions.add_parser('deploy')
    deploy.add_argument('--release',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='sync':
            config=Config(**json.loads(args.config.read_text(encoding='utf-8-sig')))
            value=sync(args.repository,args.ref,args.include,config.root,args.output,args.dry_run)
        else:
            store=LocalStore(args.root)
            if args.action=='init':
                value={'runtime':'SIMULATED','result':store.initialize()}
            elif args.action=='ingest':
                value=store.ingest(args.bundle)
            else:
                store.check()
                manager=ReleaseManager(store)
                if args.action=='deploy':
                    from artifacts import load_bundle
                    from releases import RELEASE_KEY, ref_for
                    if not RELEASE_KEY.fullmatch(args.release):
                        raise QualificationError('INVALID_RELEASE_REFERENCE')
                    _,manifest=load_bundle(store.root/'releases'/args.release/'bundle')
                    value=manager.deploy(ref_for(manifest))
                else:
                    value=getattr(manager,args.action)()
        print(json.dumps(value,ensure_ascii=False,indent=2))
        return 0
    except (QualificationError,OSError,ValueError,TypeError) as exc:
        error=str(exc) if isinstance(exc,QualificationError) else type(exc).__name__
        value={'result':'FAIL','error':error}
        if args.command=='sync':
            value.update({'requested_sha':args.ref if SHA.fullmatch(args.ref) else '[INVALID_SHA]',
                          'blockers':[error], 'remote_contacted':False, 'remote_synced':False})
        print(json.dumps(value,ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
