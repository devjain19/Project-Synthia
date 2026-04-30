# Synthia Portable Setup

This repository contains tools to prepare a portable, offline-capable Synthia installation.

The setup script lives in `scripts/setup-portable.ps1`.

What it does:

- Creates the required runtime folders under `Shared/` and `chat_data/`.
- Always downloads and refreshes the official embeddable Windows Python into `python-embed/`.
- Enables `site` for the embeddable runtime, installs `pip`, and prepares the bundled interpreter for use.
- If `scripts/install-local-ollama.bat` is present it runs it to install the local Ollama binary into `Shared/bin/`.
- Verifies the bundled Python and Ollama executable before completing.

Quick start:

PowerShell (recommended):

```powershell
.\scripts\setup-portable.ps1 -NonInteractive
```

Then run the backend using the portable Python that was installed into `python-embed/`:

```cmd
scripts\run-portable.bat backend.py
```

Notes:

- The script uses the Python embeddable zip from python.org by default (3.11.4 in this script). Update `scripts/setup-portable.ps1` to change version or URLs.
- The backend itself is dependency-free (stdlib). The portable Python is installed automatically so the USB bundle can run even when the host machine lacks Python.