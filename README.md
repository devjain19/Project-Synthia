# Synthia

Synthia is a portable, local-first AI assistant built for private offline use with:

- a browser-based GUI (`synthia.html` + `backend.py`)
- a terminal client (`scripts/synthia-terminal.py`) for fast keyboard-driven use
- local model execution through Ollama
- plug-and-play model loading for GGUF imports and local Ollama models

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

## Local Model Loading

To load a local model into Synthia:

1. Start Synthia and open the GUI.
2. Open the model import flow from the app settings.
3. Provide the GGUF URL or local model source.
4. Choose the model type, such as `lite`, `heavy`, or a task-specific profile.
5. Save the import and let Synthia register the model for local use.

Imported models are stored locally and can be routed from either the GUI or the terminal client.

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

## Portable USB Setup

`scripts/setup-portable.ps1 -NonInteractive` bootstraps the USB bundle by downloading the embeddable Python runtime, preparing Ollama when available, and verifying the install.

If you are running from a USB drive on a machine without Python installed, use the following flow:

1. Copy the repository to the USB drive.
2. Run `scripts\setup-portable.ps1 -NonInteractive` from the USB copy.
3. Launch the backend with `scripts\run-portable.bat` or `scripts\launch-with-embedded-python.bat`.
4. Open `synthia.html` in a browser and connect to `http://127.0.0.1:3333`.

Requirements for offline use:

- `python-embed\` for the bundled Python runtime.
- `Shared\bin\ollama-windows.exe` for the local Ollama binary.
- `Shared\models\` for downloaded or imported models.

## Terminal Workflow

The terminal client is useful when you want a compact, fast interface for local model access.

```cmd
scripts\start-terminal-synthia.bat
```

Use it to select a mode, send prompts, and work with local models without opening the GUI.