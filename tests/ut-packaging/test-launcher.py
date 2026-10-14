#!/usr/bin/env python3
"""Exercise the real launcher/preflight with synthetic executables, no helper/device."""
import hashlib,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class LauncherPaths(unittest.TestCase):
 def run_fixture(self,override):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);app=root/'relative app with spaces';app.mkdir();runtime=app/'runtime';runtime.mkdir();(app/'flutter_assets').mkdir();home=root/'home';home.mkdir()
   for name in ['run.sh','preflight.py']:shutil.copy2(ROOT/'click-arm64/payload'/name,app/name)
   embedder=runtime/'flutter-ut-embedder';embedder.write_text('#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["LAUNCH_RECORD"]).write_text(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd(),"library":os.environ["LD_LIBRARY_PATH"]}))\n');embedder.chmod(0o755)
   (runtime/'libflutter_engine.so').write_bytes(b'synthetic engine');(runtime/'icudtl.dat').write_bytes(b'synthetic ICU')
   artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.iterdir()}
   metadata={'schema_version':1,'target_arch':'aarch64','runtime_version':'0.3.4','flutter_version':'synthetic','engine_revision':'synthetic','artifacts':artifacts};(runtime/'runtime.json').write_text(json.dumps(metadata));(app/'app-build.json').write_text(json.dumps(metadata))
   helper=root/'synthetic helper';helper.write_text('#!/bin/sh\nexit 99\n');helper.chmod(0o755);record=root/'record';env={**os.environ,'HOME':str(home),'YUBIOATH_HELPER_PATH':str(helper),'LAUNCH_RECORD':str(record)};env.pop('APP_DIR',None);env.pop('MIR_SERVER_WAYLAND_HOST',None)
   if override:env['APP_DIR']=app.name;command=[str(app/'run.sh')];cwd=root
   else:command=['./run.sh'];cwd=app
   subprocess.run(command,cwd=cwd,env=env,check=True,timeout=10,capture_output=True)
   result=json.loads(record.read_text());self.assertEqual(result['args'],['--app-id','yubioath-flutter.thomasredstone','--assets',str(app/'flutter_assets'),'--icu',str(runtime/'icudtl.dat')]);self.assertEqual(result['cwd'],str(home/'.cache/yubioath-flutter.thomasredstone/cwd'));self.assertTrue(result['library'].startswith(str(runtime)+':'))
 def test_relative_script_with_spaces(self):self.run_fixture(False)
 def test_relative_app_dir_override_with_spaces(self):self.run_fixture(True)
if __name__=='__main__':unittest.main()
