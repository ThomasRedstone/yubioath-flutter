#!/usr/bin/env python3
import importlib.util,tempfile,unittest
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
if __name__=='__main__':unittest.main()
