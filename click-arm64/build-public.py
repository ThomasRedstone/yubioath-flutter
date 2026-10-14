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

def stage_runtime(source, destination, version, engine):
 source=Path(source).resolve();raw=(source/'runtime.json').read_bytes();runtime=json.loads(raw)
 validate_runtime(runtime,version,engine)
 required={'flutter-ut-embedder','libflutter_engine.so','icudtl.dat'}
 records=runtime.get('artifacts',{})
 selected=required|{name for name in records if name.startswith('licenses/')}
 if not selected-required:raise ValueError('runtime license inventory missing')
 destination.mkdir()
 copied={}
 for name in sorted(selected):
  relative=Path(name)
  if relative.is_absolute() or '..' in relative.parts or name not in records:raise ValueError('invalid/missing runtime artifact inventory')
  file=source/relative
  if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(source):raise ValueError('invalid runtime artifact path: '+name)
  digest=hashlib.sha256(file.read_bytes()).hexdigest()
  if digest!=records[name]:raise ValueError('runtime artifact hash mismatch: '+name)
  out=destination/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,out);copied[name]=digest
 (destination/'source-runtime.json').write_bytes(raw)
 copied['source-runtime.json']=hashlib.sha256(raw).hexdigest()
 runtime={**runtime,'artifacts':copied,'distribution':'app-local','source_runtime_manifest_sha256':copied['source-runtime.json']}
 (destination/'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n')
 return runtime

def stage_runtime_notices(source, runtime, build_record):
 source=Path(source).resolve();inventory=json.loads((source/'components.json').read_text())
 if inventory.get('target')!='aarch64-unknown-linux-gnu':raise ValueError('requires ARM64 runtime notice inventory')
 meta=json.loads((runtime/'runtime.json').read_text());record=json.loads(Path(build_record).read_text())
 if record.get('target')!='aarch64-unknown-linux-gnu' or record.get('binary_sha256')!=meta['artifacts']['flutter-ut-embedder'] or record.get('engine_revision')!=meta['engine_revision'] or record.get('source_hashes',{}).get('embedder/Cargo.lock')!=inventory['cargo_lock_sha256']:raise ValueError('native-worker notice/build/binary alignment mismatch')
 target=runtime/'licenses/native-worker';target.mkdir(parents=True)
 def copy(relative, digest):
  relative=Path(relative)
  if relative.is_absolute() or '..' in relative.parts:raise ValueError('invalid notice path')
  file=source/relative
  if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(source):raise ValueError('invalid notice file')
  if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise ValueError('runtime notice hash mismatch')
  out=target/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,out)
 copy('RUST-STANDARD-LIBRARY-COPYRIGHT.html',inventory['rust_standard_library_copyright_sha256'])
 for component in inventory['components']:
  name=f"{component['name']}-{component['version']}"
  for path,digest in component.get('notice_sha256',{}).items():copy(Path('components')/name/'notices'/path,digest)
 shutil.copy2(source/'components.json',target/'components.json')
 shutil.copy2(build_record,target/'runtime-build.json')
 meta=json.loads((runtime/'runtime.json').read_text())
 for file in target.rglob('*'):
  if file.is_file():meta['artifacts'][str(file.relative_to(runtime))]=hashlib.sha256(file.read_bytes()).hexdigest()
 meta['native_worker_cargo_lock_sha256']=inventory['cargo_lock_sha256']
 (runtime/'runtime.json').write_text(json.dumps(meta,indent=2)+'\n')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--flutter-sdk',required=True,type=Path)
 p.add_argument('--runtime-metadata',type=Path,help='Metadata in the verified runtime directory (legacy input name)')
 p.add_argument('--runtime-dir',type=Path,help='Verified ARM64 runtime to bundle into this app')
 p.add_argument('--runtime-build-record',type=Path,help='Reviewed source build record binding runtime binary and Cargo.lock hashes')
 p.add_argument('--runtime-notices',type=Path,help='Matching ARM64 native-worker component notice/source inventory')
 p.add_argument('--assets-only',action='store_true',help='Build source assets only; no runtime/device compatibility claim')
 p.add_argument('--output',type=Path,default=ROOT/'build/ut-public-click')
 a=p.parse_args()
 if not a.assets_only and not a.runtime_build_record:p.error('--runtime-build-record required to bind source/notices to the binary')
 if not a.assets_only and not a.runtime_notices:p.error('--runtime-notices required: generate matching native-worker license/source inventory')
 if not a.assets_only and not (a.runtime_dir or a.runtime_metadata):p.error('--runtime-dir required to package; use --assets-only for isolated source build')
 runtime_dir=a.runtime_dir or (a.runtime_metadata.parent if a.runtime_metadata else None)
 try:out=output_path(a.output)
 except ValueError as error:p.error(str(error))
 sdk=a.flutter_sdk.resolve();flutter=sdk/'bin/flutter'
 if subprocess.run(['git','-C',str(sdk),'diff','--quiet']).returncode or subprocess.run(['git','-C',str(sdk),'diff','--cached','--quiet']).returncode:p.error('SDK source is dirty; use a separate clean reviewed SDK')
 version=json.loads(subprocess.check_output([str(flutter),'--suppress-analytics','--version','--machine'],text=True))
 engine=(sdk/'bin/cache/engine.stamp').read_text().strip()
 if runtime_dir:
  try:validate_runtime(json.loads((runtime_dir/'runtime.json').read_text()),version,engine)
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
  if not a.assets_only:
   try:
    stage_runtime(runtime_dir,stage/'runtime',version,engine)
    stage_runtime_notices(a.runtime_notices,stage/'runtime',a.runtime_build_record)
   except ValueError as error:p.error(str(error))
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
