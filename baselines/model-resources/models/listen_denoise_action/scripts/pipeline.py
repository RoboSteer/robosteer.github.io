"""Portable command builders for the three validated pipeline stages."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def path(value):
    return Path(value).expanduser().resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['audio', 'retarget', 'sonic'])
    parser.add_argument('--lda-root', type=path, required=True)
    parser.add_argument('--input', type=path, required=True)
    parser.add_argument('--output', type=path, required=True)
    parser.add_argument('--lda-python', type=path)
    parser.add_argument('--gmr-root', type=path)
    parser.add_argument('--gmr-python', type=path)
    parser.add_argument('--checkpoint', type=path)
    parser.add_argument('--dataset-root', type=path)
    parser.add_argument('--reference-bounds-dir', type=path)
    parser.add_argument('--sonic-xml', type=path)
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--seed', type=int, default=150)
    parser.add_argument('--dry-run', action='store_true', help='Validate paths and print command without executing.')
    args = parser.parse_args()
    needed = {'audio':['lda_python','checkpoint','dataset_root','reference_bounds_dir'],
              'retarget':['gmr_root','gmr_python'], 'sonic':['gmr_root','gmr_python','sonic_xml']}[args.stage]
    for key in needed:
        if getattr(args, key) is None:
            parser.error('--' + key.replace('_', '-') + ' is required for ' + args.stage)
    for key in ['lda_root', 'input'] + needed:
        value = getattr(args,key)
        if not value.exists(): parser.error(f'{key}: path does not exist: {value}')
        if key.endswith('_python') and (not value.is_file() or not os.access(value,os.X_OK)):
            parser.error(f'{key}: expected executable file: {value}')
    for key in ['lda_root','gmr_root','dataset_root','reference_bounds_dir']:
        value=getattr(args,key)
        if value is not None and not value.is_dir(): parser.error(f'{key}: expected directory')
    if args.stage=='audio' and not args.input.is_dir(): parser.error('audio --input must be a directory')
    if args.output == args.input: parser.error('input and output must differ')
    env=os.environ.copy()
    roots=[str(args.lda_root)] + ([str(args.gmr_root)] if args.gmr_root else [])
    env['PYTHONPATH']=os.pathsep.join(roots + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    env['PYTHONUNBUFFERED']='1'
    if args.stage=='audio':
        script=args.lda_root/'utils/audio_dir_to_bvh.py'
        cmd=[str(args.lda_python),str(script),str(args.input),'--dest-dir',str(args.output),
             '--checkpoint',str(args.checkpoint),'--dataset-root',str(args.dataset_root),
             '--reference-bounds-dir',str(args.reference_bounds_dir),'--no-calibration',
             '--keep-features','--gpu',args.device,'--seed',str(args.seed),'--fps','30','--trim','0']
    elif args.stage=='retarget':
        script=args.lda_root/'utils/batch_lda_bvh_to_robot.py'
        cmd=[str(args.gmr_python),str(script),str(args.input),'--output-dir',str(args.output),
             '--gmr-root',str(args.gmr_root),'--gmr-python',str(args.gmr_python),
             '--device',args.device,'--keep-temp','--skip-sonic','--robot','unitree_g1',
             '--position-backend','pymo','--gender','neutral','--num-iters-stage1','60','--num-iters-stage2','180']
    else:
        script=args.lda_root/'utils/gmr_pkl_to_sonic_folder.py'
        cmd=[str(args.gmr_python),str(script),str(args.input),'--output-dir',str(args.output),
             '--sonic-xml',str(args.sonic_xml),'--target-fps','50','--ground-clearance','0.01',
             '--smooth-window','0','--height-correct-window','9','--velocity-sigma','1.5']
    if not script.is_file(): parser.error(f'Missing overlaid script: {script}')
    record=dict(stage=args.stage,command=cmd,cwd=str(args.lda_root),pythonpath=env['PYTHONPATH'])
    print(json.dumps(record,ensure_ascii=False,indent=2),flush=True)
    if args.dry_run: return
    if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
        parser.error('output must be absent or empty; use a new directory to avoid stale-output skips')
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'invocation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    with (args.output/'stage.log').open('w') as log:
        result=subprocess.run(cmd,cwd=args.lda_root,env=env,stdout=log,stderr=subprocess.STDOUT)
    print(f"Exit code: {result.returncode}; log: {args.output/'stage.log'}",flush=True)
    raise SystemExit(result.returncode)


if __name__=='__main__': main()
