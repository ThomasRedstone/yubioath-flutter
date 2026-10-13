#!/usr/bin/env python3
"""Build isolated JIT assets, optionally package against declared matching runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent

def validate_runtime(runtime,version,engine):
 if runtime.get('schema_version')!=1 or runtime.get('target_arch')!='aarch64':raise ValueError('requires schema1 aarch64 runtime metadata')
 if tuple(map(int,runtime.get('runtime_version','0.0.0').split('.'))) < (0,3,4):raise ValueError('requires runtime>=0.3.4')
 if version['frameworkVersion']!=runtime['flutter_version'] or engine!=runtime['engine_revision']:raise ValueError('Flutter SDK/engine mismatch with supplied runtime')

def output_path(path):
 path=Path(path).absolute()
 if path.exists() or path.is_symlink():raise ValueError('output exists; preserve it before rebuilding')
 path.parent.mkdir(parents=True,exist_ok=True)
 return path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--flutter-sdk',required=True,type=Path)
 p.add_argument('--runtime-metadata',type=Path)
 p.add_argument('--assets-only',action='store_true',help='Build source assets only; no runtime/device compatibility claim')
 p.add_argument('--output',type=Path,default=ROOT/'build/ut-public-click')
 a=p.parse_args()
 if not a.assets_only and not a.runtime_metadata:p.error('--runtime-metadata required to package; use --assets-only for isolated source build')
 try:out=output_path(a.output)
 except ValueError as error:p.error(str(error))
 sdk=a.flutter_sdk.resolve();flutter=sdk/'bin/flutter'
 if subprocess.run(['git','-C',str(sdk),'diff','--quiet']).returncode or subprocess.run(['git','-C',str(sdk),'diff','--cached','--quiet']).returncode:p.error('SDK source is dirty; use a separate clean reviewed SDK')
 version=json.loads(subprocess.check_output([str(flutter),'--suppress-analytics','--version','--machine'],text=True))
 engine=(sdk/'bin/cache/engine.stamp').read_text().strip()
 if a.runtime_metadata:
  try:validate_runtime(json.loads(a.runtime_metadata.read_text()),version,engine)
  except ValueError as error:p.error(str(error))
 subprocess.run([str(flutter),'--suppress-analytics','pub','get','--enforce-lockfile'],cwd=ROOT,check=True)
 with tempfile.TemporaryDirectory(prefix='.yubico-assets-',dir=out.parent) as work:
  work=Path(work);assets=work/'flutter_assets'
  subprocess.run([str(flutter),'--suppress-analytics','build','bundle','--debug','--no-pub','--target-platform','linux-arm64','--asset-dir',str(assets),'--depfile',str(work/'snapshot.d')],cwd=ROOT,check=True)
  for name in ('kernel_blob.bin','AssetManifest.bin','NOTICES.Z'):
   if not (assets/name).is_file():p.error('missing built asset/notice: '+name)
  stage=work/'payload';stage.mkdir()
  for name in ('manifest.json','clickable.yaml','run.sh','preflight.py','yubioath-flutter.desktop','yubioath-flutter.apparmor','icon.png'):
   file=ROOT/'click-arm64/payload'/name
   if not file.is_file() or file.is_symlink():p.error('missing/linked package template: '+name)
   shutil.copy2(file,stage/name)
  shutil.copytree(assets,stage/'flutter_assets')
  shutil.copy2(ROOT/'LICENSE',stage/'UPSTREAM-LICENSE')
  metadata={'schema_version':1,'engine_revision':engine,'flutter_version':version['frameworkVersion'],'target_arch':'aarch64','source_snapshot_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'framework_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=sdk,text=True).strip(),'build_mode':'debug','release_status':'source-assets-only' if a.assets_only else 'unverified-candidate','notices_sha256':hashlib.sha256((assets/'NOTICES.Z').read_bytes()).hexdigest()}
  (stage/'app-build.json').write_text(json.dumps(metadata,indent=2)+'\n')
  # Target must still be absent; stage lives on the same filesystem.
  import ctypes,os
  libc=ctypes.CDLL(None,use_errno=True)
  if libc.renameat2(-100,os.fsencode(stage),-100,os.fsencode(out),1):raise OSError(ctypes.get_errno(),'atomic candidate publication failed; existing output preserved')
 if not a.assets_only:subprocess.run(['clickable','build','--arch','arm64'],cwd=out,check=True)
 print('Built '+str(out)+('; source assets only; matching ARM64 runtime/device acceptance pending' if a.assets_only else '; candidate still requires artifact/device review'))

if __name__=='__main__':main()
