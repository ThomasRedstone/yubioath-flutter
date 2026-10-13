#!/usr/bin/env python3
import json, sys
from pathlib import Path
def fail(message):
 print('Yubico UT launch: '+message,file=sys.stderr); sys.exit(1)
runtime=Path(sys.argv[1]); app=Path(__file__).resolve().parent
try:
 meta=json.loads((runtime/'runtime.json').read_text()); build=json.loads((app/'app-build.json').read_text())
 if meta['schema_version']!=1 or meta['target_arch']!='aarch64': fail('unsupported runtime metadata')
 if tuple(map(int,meta['runtime_version'].split('.'))) < (0,3,4): fail('requires Flutter UT runtime >=0.3.4')
 if meta['engine_revision']!=build['engine_revision'] or meta['flutter_version']!=build['flutter_version']: fail('app/runtime SDK mismatch; rebuild or restore matching runtime')
 for name in ('flutter-ut-embedder','libflutter_engine.so','icudtl.dat'):
  if not (runtime/name).is_file(): fail('runtime missing '+name)
except (OSError,KeyError,ValueError): fail('install a compatible runtime and build this app with click-arm64/build-public.py')
