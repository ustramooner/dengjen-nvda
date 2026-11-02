# Source for the Tetun build of Dengjen Neural Voices (4.2.1-tetun)

This add-on is **Dengjen Neural Voices 4.2.0** (https://github.com/ZirekHQ/dengjen-nvda, GPL v2, a continuation of Musharraf Omer's Sonata Neural Voices) with Tetun (Timor-Leste, `tdt`) added. Its speech engine `dengjen-tts-grpc.exe` is theirs and unchanged (source: https://github.com/ZirekHQ/dengjen, GPL-3.0-or-later). All credit for the add-on and the engine belongs to their authors.

**What we changed** (`patches/tetun-changes-to-dengjen-4.2.0.patch`, a unified diff against the 4.2.0 release package):
- `domain/tts_system.py`: for voices whose language is `tdt`, the text goes through `tetun_text.normalise` before synthesis.
- `adapters/dengjen_grpc/__init__.py`: the engine reads espeak data from the add-on's `bin/espeak-ng-data` when present (ours holds the Tetun language), otherwise from NVDA's folder as before.
- `const.py`: default rate 10 (natural speed) instead of 50 (2.5 times speed on the NVDA slider).
- `installTasks.py`: installs the bundled Tetun voice into `%APPDATA%\nvda\dengjen\voices\piper` (replaces it when the model differs).
- `manifest.ini`: version 4.2.1 and summary.
- **Added files:** `tetun_text.py` (text normaliser: numbers, dates, times, units, abbreviations), `bin/espeak-ng-data` (espeak-ng data including the Tetun `tdt` language), `bundled_voices/tdt-tetun-medium` (a Piper voice).

**Tetun pronunciation sources** (`espeak-ng-sources/`): `dictsource/tdt_rules`, `dictsource/tdt_list`, `phsource/ph_tetun`, `lang/poz/tdt` for espeak-ng (GPL v3+). Compile with espeak-ng's `espeak-ng --compile=tdt` (or build espeak-ng from a checkout with these files); the exceptions in `tdt_list` come from word lists by Catharina van Klinken.

**Rebuild:** `python build_tetun_addon.py <stock dengjen_neural_voices-4.2.0.nvda-addon> <out> --espeak-data <espeak-ng-data> --voice-onnx <voice.onnx> --voice-json <voice.onnx.json> --tetun-text tetun_text.py`.

**Voice:** a Piper VITS voice fine-tuned on recordings of one reader of Tetun (Bible and news text), from a Portuguese base model. The recordings are used with the permission of their owner; terms for wider release are still being agreed, so this is a test build.
