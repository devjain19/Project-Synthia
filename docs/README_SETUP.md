# Synthia Portable Setup

This repository contains tools to prepare a portable, offline-capable Synthia installation.

The setup script lives in `scripts/setup-portable.ps1`.

What it does:

- Creates the required runtime folders under `Shared/` and `chat_data/`.
- If no system `python` is found it can download the official embeddable Windows Python, extract it to `python-portable/`, and install `pip` plus `requests`.
- If `scripts/install-local-ollama.bat` is present it can run it to install the local Ollama binary into `Shared/bin/`.

Quick start:

PowerShell (recommended):
```powershell
.\scripts\setup-portable.ps1
```

Then run the backend using the portable Python if created:
```cmd
scripts\run-portable.bat backend.py
```

Notes:
- The script uses the Python embeddable zip from python.org by default (3.11.4 in this script). Update `scripts/setup-portable.ps1` to change version or URLs.
- The backend itself is dependency-free (stdlib). The portable Python is optional and mainly useful when the host machine lacks Python or you want an isolated interpreter.
