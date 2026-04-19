# Wendy — commands to run from the repo folder

Assume you are in the Wendy directory (`cd` to the repo root). If you use a virtualenv:

```bash
source .venv/bin/activate
```

---

## One-time setup

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
chmod +x wendy.sh
```

For the full daemon (wake word, optional camera): install a Vosk model as described in the README, and grant **Microphone** (and **Camera** if used) to your terminal in **System Settings → Privacy & Security**.

Optional ML stack (Python 3.12 venv recommended):

```bash
pip install -r requirements-ml.txt
```

---

## Config TUI (`settings.json`)

```bash
python3 main.py
```

---

## Daemon (wake word + mic + optional camera → `config.json` state)

```bash
python3 wendy_daemon.py
```

Say the wake word, then double-clap. **Ctrl+C** to stop.

---

## Clap listener only

Runs without the wake-word wrapper when invoked directly:

```bash
python3 clap_detector.py
```

---

## Apply workspace state manually (no clapping)

Uses `config.json` and runs the same logic as after a successful double-clap:

```bash
python3 state_runner.py
```

---

## Shell launcher (`settings.json`, legacy flow)

```bash
./wendy.sh
```

---

## Optional: ML clap classifier

Live test (needs a trained model under `ml/models/`):

```bash
python3 ml/test.py
```

If no model is present, collect data and train (see `ml/` and README):

```bash
python3 ml/collect.py
python3 ml/train.py
```

---

## Optional: LaunchAgent (background, login item)

```bash
python3 wendy_daemon.py --install-launchagent
launchctl load ~/Library/LaunchAgents/com.wendy.daemon.plist
```

Uninstall (when you want to remove it):

```bash
launchctl unload ~/Library/LaunchAgents/com.wendy.daemon.plist
rm ~/Library/LaunchAgents/com.wendy.daemon.plist
```

---

## Where settings live

| File | Role |
|------|------|
| `settings.json` | Written by `main.py` (TUI); used by `wendy.sh` |
| `config.json` | Profiles / trigger; clap daemon applies state via `state_runner.py` |

Clap timing and visual gate tuning: `config.json` → `settings` (see README).
