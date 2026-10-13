# Unofficial Ubuntu Touch packaging

This is the Apache-2.0 Yubico app port, not an official Yubico UT product. Upstream branding and license remain intact. The UT target currently uses debug/JIT assets, not a production desktop binary. Upstream workflows pin Flutter 3.44.4; the separately packaged UT runtime must provide the exact same Flutter version and engine revision as the SDK used to build this app. Do not assume the locally installed runtime or the upstream workflow version matches.

From a clean clone with its pubspec.lock, provide a Flutter SDK and the runtime's published runtime.json, then run:

```sh
python3 click-arm64/build-public.py --flutter-sdk /path/to/flutter --runtime-metadata /path/to/runtime.json --output /new/click-candidate
```

Requires public Flutter/Dart package access, Clickable >=8.8, Docker, Linux ARM64-compatible assets/native dependencies and the runtime SDK. The script refuses SDK/engine mismatches dirty SDK source or an existing output, enforces pubspec.lock, builds linux-arm64 debug bundle, records build metadata, includes upstream license and packages the click. Move older staged artifacts to a private backup before rebuilding. Native assets/plugins still require ARM64 ELF/ABI inspection; build success is not hardware acceptance. Runtime and app artifact notices/source must be audited separately.

Install dependency order: (1) verified Noble ARM64 ut-pcscd/libccid payload, (2) ut-yubioath-helper built for ARM64 CPython 3.12, (3) matching flutter-ut-embedder-runtime >=0.3.4 with schema1 runtime.json, (4) this app click. Click manifests do not automatically install these dependencies. The launcher verifies metadata and required files, accepts FLUTTER_UT_RUNTIME/YUBIOATH_HELPER_PATH for independent installations, and passes a stable per-app storage identity. Keep helper RPC code from this same app source revision; cross-version protocol compatibility is unvalidated. See dependency repositories' removal/rollback guides; uninstall this app before removing shared dependencies used by other apps.

Historical local OATH listing succeeded. TOTP generation, protected keys, QR import, disconnect/reconnect, FIDO/PIV, cancellation and upgrade remain separate acceptance gates. The upstream desktop support matrix does not imply UT support. Do not upload key serials, account data or live helper transcripts to issues; use synthetic fixtures. App data lives in its per-app runtime namespace/cache; removing the click should not silently delete accounts or settings. Permission/confinement and account storage need real-device review before recommending installation.

Source-only build without a matching runtime is explicit: `python3 click-arm64/build-public.py --flutter-sdk /clean/flutter --assets-only --output /new/assets-candidate`. Output must be absent; staged assets/metadata are atomically published. The builder includes the original Apache license and Flutter's generated NOTICES.Z and records current source dirty state; do not claim uncommitted packaging equals its recorded HEAD.

An isolated linux-arm64 debug source build with enforced pubspec.lock completed 2026-10-13 using reviewed Flutter 3.44.9/engine 5a2a6a42. The app's lock was unchanged. Matching genuine ARM64 runtime metadata also produced a click. Default Clickable review failed on the hardcoded shared runtime path and unconfined template, with an assets-only architecture warning. A present click does not override that nonzero review result; this is not an OpenStore-cleared or installed release. Keep the shared dependency/unconfined trust model visible and complete permission/store/device review before recommendation.

Artifact inspection also caught an unspecified framework defaulting to ubuntu-sdk-20.04.1, incompatible with the Noble shared runtime/helper chain. Source packaging now explicitly pins ubuntu-touch-24.04-1.x (policy 2404.1, confirmed in installed Clickable framework mapping). The earlier candidate is preserved for diagnosis and must not be distributed. Regenerate a new candidate after the framework fix; source-only checks are not a replacement for that package/device review.
