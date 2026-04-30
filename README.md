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