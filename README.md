# Synthia

Synthia is a portable offline AI app with a browser UI, a local Python backend, and an optional terminal UI.

## Files to upload

- `backend.py`
- `synthia.html`
- `start-synthia.bat`
- `assets/`
- `docs/`
- `scripts/`
- `README.md`
- `.gitignore`

## Do not upload

- `chat_data/`
- `Shared/models/ollama_data/`
- `Shared/models/gguf/`
- `Shared/models/modelfiles/`
- `Shared/bin/ollama-windows.exe`
- `python-portable/`
- `.venv/`

## Run locally

GUI backend:

```cmd
start-synthia.bat
```

Terminal UI:

```cmd
scripts\start-terminal-synthia.bat
```

Portable setup:

```powershell
.\scripts\setup-portable.ps1
```

## GitHub upload

Use the commands below after you create a GitHub repository and replace the URL with your repo URL.