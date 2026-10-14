#!/usr/bin/env python3
import importlib.util,tempfile,unittest,json,hashlib
from pathlib import Path
spec=importlib.util.spec_from_file_location('build_public',Path(__file__).resolve().parents[2]/'click-arm64/build-public.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
class BuildSafety(unittest.TestCase):
 def test_host_runtime_not_relabelled(self):
  with self.assertRaises(ValueError):builder.validate_runtime({'schema_version':1,'target_arch':'x86_64','flutter_version':'3.44.9','engine_revision':'same'}, {'frameworkVersion':'3.44.9'},'same')
 def test_exact_sdk_engine_match(self):
  meta={'schema_version':1,'target_arch':'aarch64','runtime_version':'0.3.4','flutter_version':'3.44.9','engine_revision':'same'}
  builder.validate_runtime(meta,{'frameworkVersion':'3.44.9'},'same')
  with self.assertRaises(ValueError):builder.validate_runtime(meta,{'frameworkVersion':'3.44.4'},'same')
  with self.assertRaises(ValueError):builder.validate_runtime(meta,{'frameworkVersion':'3.44.9'},'different')
 def test_existing_artifact_and_dangling_link_preserved(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);out=root/'existing';out.mkdir();(out/'artifact').write_text('keep')
   with self.assertRaises(ValueError):builder.output_path(out)
   self.assertEqual((out/'artifact').read_text(),'keep')
   link=root/'link';link.symlink_to(root/'missing')
   with self.assertRaises(ValueError):builder.output_path(link)
   self.assertTrue(link.is_symlink());self.assertFalse((root/'missing').exists())
 def test_bundled_runtime_carries_hashes_and_notices(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=root/'runtime';source.mkdir();artifacts={}
   for name in ['flutter-ut-embedder','libflutter_engine.so','icudtl.dat','licenses/engine.txt']:
    file=source/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('owned fixture '+name);artifacts[name]=hashlib.sha256(file.read_bytes()).hexdigest()
   meta={'schema_version':1,'target_arch':'aarch64','runtime_version':'0.3.4','flutter_version':'3.44.9','engine_revision':'same','artifacts':artifacts}
   (source/'runtime.json').write_text(json.dumps(meta))
   staged=builder.stage_runtime(source,root/'bundled',{'frameworkVersion':'3.44.9'},'same')
   self.assertEqual(staged['distribution'],'app-local');self.assertTrue((root/'bundled/licenses/engine.txt').is_file())
   for name,digest in staged['artifacts'].items():self.assertEqual(hashlib.sha256((root/'bundled'/name).read_bytes()).hexdigest(),digest)
 def test_changed_runtime_is_refused(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=root/'runtime';source.mkdir()
   (source/'runtime.json').write_text(json.dumps({'schema_version':1,'target_arch':'aarch64','runtime_version':'0.3.4','flutter_version':'3.44.9','engine_revision':'same','artifacts':{'licenses/notice':'0'*64}}))
   with self.assertRaises(ValueError):builder.stage_runtime(source,root/'bundled',{'frameworkVersion':'3.44.9'},'same')
 def test_notice_build_binary_alignment(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=root/'notices';source.mkdir();runtime=root/'runtime';runtime.mkdir()
   (runtime/'runtime.json').write_text(json.dumps({'engine_revision':'engine','artifacts':{'flutter-ut-embedder':'binary'}}))
   data=b'original copyright';(source/'RUST-STANDARD-LIBRARY-COPYRIGHT.html').write_bytes(data)
   inventory={'target':'aarch64-unknown-linux-gnu','cargo_lock_sha256':'lock','rust_standard_library_copyright_sha256':hashlib.sha256(data).hexdigest(),'components':[]}
   (source/'components.json').write_text(json.dumps(inventory));record=root/'build.json';record.write_text(json.dumps({'target':'aarch64-unknown-linux-gnu','binary_sha256':'wrong','engine_revision':'engine','source_hashes':{'embedder/Cargo.lock':'lock'}}))
   with self.assertRaises(ValueError):builder.stage_runtime_notices(source,runtime,record)
   self.assertFalse((runtime/'licenses/native-worker').exists())
   record.write_text(record.read_text().replace('wrong','binary'));builder.stage_runtime_notices(source,runtime,record)
   meta=json.loads((runtime/'runtime.json').read_text());self.assertEqual(meta['native_worker_cargo_lock_sha256'],'lock')
   for name,digest in meta['artifacts'].items():
    if name.startswith('licenses/'):self.assertEqual(hashlib.sha256((runtime/name).read_bytes()).hexdigest(),digest)
if __name__=='__main__':unittest.main()
