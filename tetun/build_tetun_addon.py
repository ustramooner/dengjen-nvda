#!/usr/bin/env python3
"""Build a Tetun (tdt) variant of the Dengjen Neural Voices NVDA add-on from the stock release package.

Usage: build_tetun_addon.py <stock dengjen_neural_voices-X.nvda-addon> <out .nvda-addon> --espeak-data <dir named espeak-ng-data>
           --voice-onnx <tdt voice .onnx> --voice-json <its .onnx.json> --tetun-text <tetun_text.py> [--version 4.2.1]

What is added to the stock package (no compiled code, nothing of theirs is removed):
  * synthDrivers/dengjen_neural_voices/domain/tetun_text.py   our text normaliser (numbers, dates, times, units, abbreviations)
  * domain/tts_system.py        SpeechOptions.speak_text runs the normaliser for voices whose language is `tdt`
  * adapters/dengjen_grpc/__init__.py   the engine reads espeak data from bin/espeak-ng-data when it exists (ours holds the Tetun
                                         `tdt` language), else from NVDA's own folder as before
  * bin/espeak-ng-data          our espeak-ng data (Tetun dictionary and rules)
  * bundled_voices/tdt-tetun-medium/   the voice, with the add-on's voice.json sidecar
  * installTasks.py             installs the bundled voice into %APPDATA%\\nvda\\dengjen\\voices\\piper (replaces it when the model differs)
  * const.py                    DEFAULT_RATE 10 (natural speed) instead of 50 (2.5 times speed on the NVDA slider)
  * manifest.ini                version and summary
Every patch asserts that the text it replaces is present exactly once, so a changed stock package fails loudly.
"""
import argparse, hashlib, json, os, re, shutil, sys, zipfile

ap = argparse.ArgumentParser()
ap.add_argument("stock"); ap.add_argument("out")
ap.add_argument("--espeak-data", required=True); ap.add_argument("--voice-onnx", required=True); ap.add_argument("--voice-json", required=True)
ap.add_argument("--tetun-text", required=True); ap.add_argument("--version", default="4.2.1")
a = ap.parse_args()
D = "synthDrivers/dengjen_neural_voices/"
files = {}
with zipfile.ZipFile(a.stock) as z:
    for i in z.infolist(): files[i.filename] = z.read(i.filename)

def patch(name, old, new):
    text = files[name].decode("utf-8")
    assert text.count(old) == 1, f"{name}: expected exactly one occurrence of: {old[:70]!r}, found {text.count(old)}"
    files[name] = text.replace(old, new).encode("utf-8")

# 1. normaliser
files[D + "domain/tetun_text.py"] = open(a.tetun_text, "rb").read()

# 2. hook in speak_text (language `tdt`; the voice language is normalised from the voice name or its sidecar)
patch(D + "domain/tts_system.py", "from .model_profiles import SCALE_NAMES, profile_for\n",
      "from . import tetun_text\nfrom .model_profiles import SCALE_NAMES, profile_for\n")
patch(D + "domain/tts_system.py", "    def speak_text(self, text):\n        return self.voice.synthesize(",
      "    def speak_text(self, text):\n        if self.voice.language.split(\"-\")[0].split(\"_\")[0] == \"tdt\":\n            text = tetun_text.normalise(text)\n        return self.voice.synthesize(")

# 3. espeak data folder
patch(D + "adapters/dengjen_grpc/__init__.py",
      '    nvda_espeak_dir = os.path.join(globalVars.appDir, "synthDrivers")\n',
      '    # The data bundled with this add-on holds the Tetun `tdt` language; otherwise use the copy shipped with NVDA.\n'
      '    if os.path.isdir(os.path.join(BIN_DIRECTORY, "espeak-ng-data")):\n'
      '        nvda_espeak_dir = BIN_DIRECTORY\n'
      '    else:\n'
      '        nvda_espeak_dir = os.path.join(globalVars.appDir, "synthDrivers")\n')

# 4. espeak data
n = 0
for root, _, names in os.walk(a.espeak_data):
    for f in names:
        p = os.path.join(root, f); rel = os.path.relpath(p, os.path.dirname(a.espeak_data)).replace(os.sep, "/")
        files[D + "bin/" + rel] = open(p, "rb").read(); n += 1
assert D + "bin/espeak-ng-data/tdt_dict" in files and D + "bin/espeak-ng-data/lang/poz/tdt" in files, "espeak data has no Tetun (tdt) files"

# 5. voice
vdir = D + "bundled_voices/tdt-tetun-medium/"
files[vdir + "tdt-tetun-medium.onnx"] = open(a.voice_onnx, "rb").read()
cfg = json.load(open(a.voice_json, encoding="utf-8")); cfg.setdefault("phoneme_map", {})
files[vdir + "tdt-tetun-medium.onnx.json"] = json.dumps(cfg, indent=2).encode()
files[vdir + "voice.json"] = json.dumps({"model_type": "piper", "name": "tetun", "language": "tdt",
                                          "description": "Tetun (Timor-Leste)"}).encode()

# 6. installer step
patch("installTasks.py", "def onInstall():\n    for step in (\n        warn_if_old_addon_installed,\n        migrate_speech_config,\n    ):",
'''def _same_model(src, dst):
    import hashlib
    for name in os.listdir(src):
        if not name.endswith(".onnx"):
            continue
        a, b = os.path.join(src, name), os.path.join(dst, name)
        if not os.path.isfile(b) or os.path.getsize(a) != os.path.getsize(b):
            return False
        digests = []
        for path in (a, b):
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            digests.append(h.digest())
        if digests[0] != digests[1]:
            return False
    return True


def install_bundled_voices():
    """Copy the voices bundled with this add-on (Tetun) into the voices folder; replace one of the same name when the model differs."""
    import globalVars
    bundled = os.path.join(_SYNTH_DRIVER_DIR_PATH, "bundled_voices")
    if not os.path.isdir(bundled):
        return False
    voices_dir = os.path.join(globalVars.appArgs.configPath, "dengjen", "voices", "piper")
    os.makedirs(voices_dir, exist_ok=True)
    for name in os.listdir(bundled):
        src, dst = os.path.join(bundled, name), os.path.join(voices_dir, name)
        if not os.path.isdir(src):
            continue
        if os.path.exists(dst):
            if _same_model(src, dst):
                continue
            shutil.rmtree(dst)
            log.info(f"Replacing installed voice with the bundled one: {name}")
        shutil.copytree(src, dst)
        log.info(f"Installed bundled voice: {name}")
    return True


def onInstall():
    for step in (
        install_bundled_voices,
        warn_if_old_addon_installed,
        migrate_speech_config,
    ):''')
patch("installTasks.py", 'del _DIR, _SYNTH_DRIVER_DIR\n', '_SYNTH_DRIVER_DIR_PATH = _SYNTH_DRIVER_DIR\ndel _DIR, _SYNTH_DRIVER_DIR\n')

# 6b. natural default speed: the stock default rate of 50 is clamped to 40 by the slider's range, so the add-on started at 100 on the
# NVDA slider (2.5 times normal speed); 10 is the engine's natural speed (NVDA slider 25)
patch(D + "const.py", "DEFAULT_RATE = 50\n", "DEFAULT_RATE = 10  # natural speed (the stock 50 started at 2.5 times speed)\n")

# 7. manifest
m = files["manifest.ini"].decode("utf-8")
m = re.sub(r'(?m)^version = .*$', f"version = {a.version}", m, count=1)
m = re.sub(r'(?m)^summary = .*$', 'summary = "Dengjen Neural Voices (Tetun build)"', m, count=1)
files["manifest.ini"] = m.encode("utf-8")

with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
    for name, data in files.items(): z.writestr(name, data)
h = hashlib.sha256(open(a.out, "rb").read()).hexdigest(); open(a.out + ".sha256", "w").write(f"{h}  {os.path.basename(a.out)}\n")
print(f"wrote {a.out}: {len(files)} entries ({n} espeak data files), sha256 {h[:16]}")
