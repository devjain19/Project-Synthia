# Synthia

Synthia is a portable offline AI assistant with:

- a browser-based GUI (`synthia.html` + `backend.py`)
- local model execution through Ollama
- optional terminal client (`scripts/synthia-terminal.py`)

## Quick Start

### 1) Start the GUI backend

```cmd
start-synthia.bat
```

Then open `http://127.0.0.1:3333` in your browser.

### 2) Start the terminal client (optional)

```cmd
scripts\start-terminal-synthia.bat
```

## Setup and Model Guides

- Portable setup: `docs/README_SETUP.md`
- Offline model import and routing: `docs/MODEL_SETUP.md`

## Project Layout

- `backend.py`: local API server and Ollama integration
- `synthia.html`: GUI frontend
- `scripts/`: setup and launch scripts (GUI + terminal)
- `assets/`: GUI logos/assets
- `docs/`: user documentation
- `chat_data/`: local runtime chat/settings storage
- `Shared/`: local Ollama binary and model data

## Notes

- Synthia is intended to run locally/offline.
- Runtime data (chat history, imported models, Ollama cache) is machine-local.
- `scripts/setup-portable.ps1 -NonInteractive` now bootstraps the USB bundle automatically by downloading portable Python, installing Ollama when available, and verifying both tools.

## Running from USB with an embedded Python (Windows)

If you plan to copy the repository onto a USB drive and run it on machines that do not have Python installed, use the bundled bootstrap flow.

- Run `scripts\setup-portable.ps1 -NonInteractive` once on the USB copy. It will download the Windows embeddable Python into `python-embed` and prepare the local Ollama binary when `scripts\install-local-ollama.bat` is present.
- If you prefer a manual bundle, you can still place the Windows embeddable ZIP contents into `python-embed` yourself.

Files to include on the USB for a portable experience:

- the project files (the repo root with `synthia.html`, `backend.py`, `scripts`, etc.)
- `python-embed\` (the extracted Windows embeddable distribution) OR `venv\` (a copied venv)
- `Shared\bin\ollama.exe` and the `Shared\models\` folder if you want Ollama and model data available offline

We included a helper launcher that tries to find a bundled Python and run the backend for you:

- `scripts\launch-with-embedded-python.bat` — looks for `python.exe` under `python-embed\`, `python\`, `venv\Scripts\`, or `python.exe` in the repo root and starts `backend.py` in a new window.

How to prepare and run (summary):

1. On your dev machine, download the Windows embeddable ZIP for your Python version from https://www.python.org and extract it into the repository root as `python-embed`.

2. Copy the repo root to your USB drive, then run `scripts\setup-portable.ps1 -NonInteractive` from that USB copy.

3. On the target machine (from the USB drive), run:

```powershell
cd <USB_DRIVE>\<repo_root>\scripts
.\launch-with-embedded-python.bat
```

4. If the backend starts successfully, open `synthia.html` in a local browser and connect to `http://127.0.0.1:3333`.

Important caveats:

- Ollama binaries and model files are large and platform-specific. If you want full offline model inference, include the correct `Shared\bin` and `Shared\models` data for the target machine.
- Performance from a slow USB stick will be poor and may make large model loading fail.
- Some systems block execution from removable media or require admin privileges.
- A Windows exe built with PyInstaller is an alternative if you prefer a single-file launcher and want to avoid shipping Python itself.

If you want, I can produce a ready-to-copy packaging checklist and a small PowerShell script to assemble the USB bundle automatically. Which would you like me to add?