# Synthia Offline Model Setup

## 1) Install local Ollama into this folder

Run `scripts/install-local-ollama.bat`.

This installs the Ollama executable to:
- `Shared/bin/ollama-windows.exe`

And creates the portable model cache folder:
- `Shared/models/ollama_data`

## 2) Launch Synthia

Run `scripts/start-synthia.bat`.

The launcher will:
- start local Ollama from `Shared/bin/ollama-windows.exe` if present
- wait for Ollama API to respond
- start `backend.py`

## 3) Download any GGUF model from URL

Open Synthia -> Settings and use **Import GGUF model**:
- `GGUF URL`: direct link ending in `.gguf`
- `Model name`: local Ollama model name (example: `qwen3-4b-local`)
- `Model type`: `light/lite`, `heavy`, `video`, `image`, `pdf`, `code`, `pentest`, `research`, or `other`

When imported, Synthia will:
1. Download the `.gguf` into `Shared/models/gguf`
2. Create an Ollama Modelfile in `Shared/models/modelfiles`
3. Run `ollama create <name> -f <Modelfile>`
4. Save metadata into `chat_data/model_registry.json`

## 4) Recommended model sources

- Ollama registry: https://ollama.com/library
- Hugging Face GGUF collections: https://huggingface.co/models?library=gguf
- Bartowski GGUF repos (popular quantized models)

Recommended Synthia models:

- Lite: [Gemma 2](https://huggingface.co/bartowski/gemma-2-2b-it-abliterated-GGUF/resolve/main/gemma-2-2b-it-abliterated-Q4_K_M.gguf) for fast everyday chat and lightweight local use.
- Heavy: [Gemma 4](https://huggingface.co/llmfan46/gemma-4-E4B-it-ultra-uncensored-heretic-GGUF/resolve/main/gemma-4-E4B-it-ultra-uncensored-heretic-Q4_K_M.gguf) for larger, more capable local responses.

Important: use direct file URLs that resolve to a `.gguf` file.

## 5) Model routing behavior

- Lite chat uses the selected Lite model and warms it on startup.
- Heavy chat uses Heavy model by default.
- Tile tasks (`video`, `image`, `pdf`, etc.) can be mapped to dedicated models in Settings.
