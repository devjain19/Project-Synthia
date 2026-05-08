#!/usr/bin/env python3
"""Synthia portable backend.

This server is intentionally small and dependency-free so the USB folder can
run on any machine with Python available. It serves synthia.html, persists
chats/settings on disk, and talks to a local Ollama instance when present.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "synthia.html"
DATA_DIR = ROOT / "chat_data"
CHATS_FILE = DATA_DIR / "chats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
MODEL_REGISTRY_FILE = DATA_DIR / "model_registry.json"

SHARED_DIR = ROOT / "Shared"
BIN_DIR = SHARED_DIR / "bin"
MODELS_DIR = SHARED_DIR / "models"
OLLAMA_MODELS_DIR = MODELS_DIR / "ollama_data"
GGUF_DIR = MODELS_DIR / "gguf"
MODELFILES_DIR = MODELS_DIR / "modelfiles"
LOCAL_OLLAMA_EXE = BIN_DIR / "ollama-windows.exe"

MODEL_TYPES = ["lite", "heavy", "video", "image", "pdf", "code", "pentest", "research", "other"]
MODEL_TYPE_ALIASES = {"light": "lite", "lite": "lite"}

PORT = int(os.environ.get("SYNTHIA_PORT", "3333"))
HOST = os.environ.get("SYNTHIA_HOST", "127.0.0.1")
OLLAMA_HOST = os.environ.get("SYNTHIA_OLLAMA_HOST", "http://127.0.0.1:11434")
OPEN_BROWSER = os.environ.get("SYNTHIA_OPEN_BROWSER", "1") != "0"
LITE_MODEL_ENV = os.environ.get("SYNTHIA_LITE_MODEL", "").strip()
HEAVY_MODEL_ENV = os.environ.get("SYNTHIA_HEAVY_MODEL", "").strip()

MODEL_WARMED = {"lite": False, "heavy": False}
MODEL_WARM_LOCK = threading.Lock()

DEFAULT_SETTINGS = {
    "theme": "light",
    "liteModel": "",
    "heavyModel": "",
    "modelProfiles": {},
    "temperature": 0.7,
    "liteSystemPrompt": (
        "You are Synthia Lite, a compact offline assistant. Answer quickly, "
        "clearly, and in a concise tone."
    ),
    "heavySystemPrompt": (
        "You are Synthia Heavy, a full offline assistant. Give detailed, "
        "structured answers and ask clarifying questions when needed."
    ),
}

IMPORT_JOBS: dict[str, dict] = {}
IMPORT_JOBS_LOCK = threading.Lock()

DEFAULT_CHATS = {
    "lite": [
        {
            "role": "assistant",
            "content": "Hello! I'm Synthia Lite. Ask me anything quick.",
        }
    ],
    "heavy": [],
    "savedSessions": [],
}

TILE_PROMPTS = {
    "pdf": (
        "You are in PDF analysis mode. Summarize documents, extract key facts, "
        "and answer questions from uploaded PDF text."
    ),
    "video": (
        "You are in video editing mode. Help with scene breakdowns, captions, "
        "script edits, and edit planning."
    ),
    "image": (
        "You are in image generation mode. Help with prompts, edits, style "
        "transfer ideas, and image workflow planning."
    ),
    "code": (
        "You are in coding assistant mode. Be precise, technical, and focused "
        "on implementation details, debugging, and architecture."
    ),
    "pentest": (
        "You are in security audit mode. Focus on defensive analysis, safe "
        "testing, hardening, and vulnerability explanation."
    ),
    "research": (
        "You are in research mode. Give synthesis, structure, caveats, and "
        "clear source-aware reasoning."
    ),
}


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OLLAMA_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    MODELFILES_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
    if not CHATS_FILE.exists():
        CHATS_FILE.write_text(json.dumps(DEFAULT_CHATS, indent=2), encoding="utf-8")
    if not MODEL_REGISTRY_FILE.exists():
        MODEL_REGISTRY_FILE.write_text("[]", encoding="utf-8")


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def get_registry() -> list[dict]:
    data = load_json(MODEL_REGISTRY_FILE, [])
    return data if isinstance(data, list) else []


def resolve_ollama_command() -> str | None:
    if LOCAL_OLLAMA_EXE.exists():
        return str(LOCAL_OLLAMA_EXE)
    return shutil.which("ollama")


def ollama_env() -> dict:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = urllib.parse.urlparse(OLLAMA_HOST).netloc or "127.0.0.1:11434"
    env["OLLAMA_MODELS"] = str(OLLAMA_MODELS_DIR)
    env.setdefault("OLLAMA_ORIGINS", "*")
    return env


def sanitize_model_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.:-]+", "-", name.strip())
    cleaned = cleaned.strip("-._:")
    if not cleaned:
        raise ValueError("Model name is required")
    return cleaned.lower()


def model_name_base(name: str) -> str:
    return name.split(":", 1)[0].lower()


def model_names_match(left: str, right: str) -> bool:
    return model_name_base(left) == model_name_base(right) or left.lower() == right.lower()


def build_modelfile_text(gguf_path: Path) -> str:
    path_text = str(gguf_path.resolve()).replace("\\", "/")
    return f"FROM {path_text}\n\nPARAMETER num_ctx 4096\n"


def fetch_file(url: str, target_path: Path, progress_callback=None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Synthia-Portable/1.0"})
    with urllib.request.urlopen(request, timeout=300.0) as response, target_path.open("wb") as out_file:
        total_bytes = response.headers.get("Content-Length")
        try:
            total_bytes_int = int(total_bytes) if total_bytes is not None else None
        except Exception:
            total_bytes_int = None

        downloaded = 0
        started_at = time.monotonic()
        chunk_size = 1024 * 1024
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if progress_callback:
                elapsed = max(time.monotonic() - started_at, 0.001)
                progress_callback(downloaded, total_bytes_int, elapsed)

        if progress_callback:
            elapsed = max(time.monotonic() - started_at, 0.001)
            progress_callback(downloaded, total_bytes_int, elapsed)


def create_ollama_model(model_name: str, modelfile_path: Path) -> None:
    cmd = resolve_ollama_command()
    if not cmd:
        raise RuntimeError("Ollama CLI not found. Place ollama-windows.exe in Shared/bin or install Ollama system-wide.")
    result = subprocess.run(
        [cmd, "create", model_name, "-f", str(modelfile_path)],
        env=ollama_env(),
        cwd=str(ROOT),
        capture_output=True,
        text=False,
        timeout=600,
    )
    if result.returncode != 0:
        raw = result.stderr or result.stdout or b""
        try:
            stderr = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        except Exception:
            stderr = "model create failed"
        raise RuntimeError(stderr.strip())


def import_gguf_model(gguf_url: str, model_name: str, model_type: str, progress_callback=None) -> dict:
    parsed = urllib.parse.urlparse(gguf_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("GGUF URL must start with http:// or https://")
    if ".gguf" not in gguf_url.lower():
        raise ValueError("URL must point to a .gguf file")

    model_name = sanitize_model_name(model_name)
    model_type = MODEL_TYPE_ALIASES.get(model_type.lower().strip(), model_type.lower().strip())
    if model_type not in MODEL_TYPES:
        raise ValueError(f"Invalid model type: {model_type}")

    filename = Path(parsed.path).name or f"{model_name}.gguf"
    if not filename.lower().endswith(".gguf"):
        filename = f"{filename}.gguf"

    gguf_path = GGUF_DIR / filename
    modelfile_path = MODELFILES_DIR / f"{model_name}.Modelfile"

    fetch_file(gguf_url, gguf_path, progress_callback=progress_callback)
    modelfile_path.write_text(build_modelfile_text(gguf_path), encoding="utf-8")
    create_ollama_model(model_name, modelfile_path)

    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    model_profiles = settings.get("modelProfiles") if isinstance(settings.get("modelProfiles"), dict) else {}
    if model_type == "lite":
        settings["liteModel"] = model_name
    elif model_type == "heavy":
        settings["heavyModel"] = model_name
    elif model_type != "other":
        model_profiles[model_type] = model_name
        settings["modelProfiles"] = model_profiles
    save_json(SETTINGS_FILE, settings)

    registry = get_registry()
    registry.append(
        {
            "name": model_name,
            "type": model_type,
            "url": gguf_url,
            "ggufFile": str(gguf_path.relative_to(ROOT)),
            "addedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_json(MODEL_REGISTRY_FILE, registry)

    return {
        "name": model_name,
        "type": model_type,
        "ggufFile": str(gguf_path),
        "settings": settings,
    }


def make_import_job_payload(job_id: str) -> dict:
    with IMPORT_JOBS_LOCK:
        job = dict(IMPORT_JOBS.get(job_id) or {})
    if not job:
        return {"ok": False, "error": "job not found"}
    return {"ok": True, "job": job}


def _update_import_job(job_id: str, **updates) -> None:
    with IMPORT_JOBS_LOCK:
        job = IMPORT_JOBS.get(job_id)
        if not job:
            return
        job.update(updates)


def _run_import_job(job_id: str, gguf_url: str, model_name: str, model_type: str) -> None:
    started_at = time.monotonic()

    def progress_callback(downloaded_bytes: int, total_bytes: int | None, elapsed_seconds: float) -> None:
        percent = None
        eta_seconds = None
        speed_bps = None
        if total_bytes and total_bytes > 0:
            percent = min(100.0, (downloaded_bytes / total_bytes) * 100.0)
            if elapsed_seconds > 0 and downloaded_bytes > 0:
                speed_bps = downloaded_bytes / elapsed_seconds
                remaining = max(total_bytes - downloaded_bytes, 0)
                eta_seconds = remaining / speed_bps if speed_bps > 0 else None
        elif elapsed_seconds > 0 and downloaded_bytes > 0:
            speed_bps = downloaded_bytes / elapsed_seconds

        _update_import_job(
            job_id,
            state="downloading",
            downloadedBytes=downloaded_bytes,
            totalBytes=total_bytes,
            percent=percent,
            speedBytesPerSecond=speed_bps,
            etaSeconds=eta_seconds,
            elapsedSeconds=max(time.monotonic() - started_at, 0.0),
        )

    try:
        _update_import_job(job_id, state="starting", message="Preparing download...", startedAt=datetime.now(timezone.utc).isoformat())
        result = import_gguf_model(gguf_url, model_name, model_type, progress_callback=progress_callback)
        _update_import_job(
            job_id,
            state="completed",
            message="Import complete.",
            finishedAt=datetime.now(timezone.utc).isoformat(),
            result=result,
            models=discover_models(),
        )
    except Exception as exc:
        _update_import_job(
            job_id,
            state="failed",
            message=str(exc),
            finishedAt=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )


def delete_imported_model(model_name: str) -> dict:
    requested_name = sanitize_model_name(model_name)
    models = discover_models()
    matched_model = None
    for model in models:
        name = str(model.get("name", ""))
        if model_names_match(name, requested_name):
            matched_model = name
            break

    if not matched_model:
        matched_model = requested_name

    cmd = resolve_ollama_command()
    if not cmd:
        raise RuntimeError("Ollama CLI not found. Place ollama-windows.exe in Shared/bin or install Ollama system-wide.")

    result = subprocess.run(
        [cmd, "rm", matched_model],
        env=ollama_env(),
        cwd=str(ROOT),
        capture_output=True,
        text=False,
        timeout=300,
    )
    if result.returncode != 0:
        raw = result.stderr or result.stdout or b""
        try:
            stderr = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        except Exception:
            stderr = "model delete failed"
        raise RuntimeError(stderr.strip())

    registry = get_registry()
    kept_registry = []
    removed_files: list[str] = []
    for item in registry:
        item_name = str(item.get("name", ""))
        if model_names_match(item_name, requested_name) or model_names_match(item_name, matched_model):
            gguf_file = item.get("ggufFile")
            if gguf_file:
                gguf_path = (ROOT / str(gguf_file)).resolve()
                if gguf_path.exists():
                    gguf_path.unlink()
                    removed_files.append(str(gguf_path.relative_to(ROOT)))

            modelfile_path = MODELFILES_DIR / f"{sanitize_model_name(item_name)}.Modelfile"
            if modelfile_path.exists():
                modelfile_path.unlink()
                removed_files.append(str(modelfile_path.relative_to(ROOT)))
        else:
            kept_registry.append(item)

    save_json(MODEL_REGISTRY_FILE, kept_registry)

    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    changed = False
    for key in ("liteModel", "heavyModel"):
        current = str(settings.get(key, "") or "")
        if current and model_names_match(current, requested_name):
            settings[key] = ""
            changed = True

    model_profiles = settings.get("modelProfiles") if isinstance(settings.get("modelProfiles"), dict) else {}
    if isinstance(model_profiles, dict):
        profile_updates = {k: v for k, v in model_profiles.items() if not model_names_match(str(v), requested_name)}
        if profile_updates != model_profiles:
            settings["modelProfiles"] = profile_updates
            changed = True

    if changed:
        save_json(SETTINGS_FILE, settings)

    return {
        "name": matched_model,
        "removedFiles": removed_files,
        "settings": settings,
    }


def read_request_json(handler: BaseHTTPRequestHandler):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def http_json(url: str, payload=None, timeout: float = 30.0):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_alive() -> bool:
    try:
        http_json(f"{OLLAMA_HOST}/api/tags", timeout=1.5)
        return True
    except Exception:
        return False


def discover_models():
    try:
        payload = http_json(f"{OLLAMA_HOST}/api/tags", timeout=2.0)
    except Exception:
        return []

    models = payload.get("models", []) if isinstance(payload, dict) else []
    normalized = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("name") or model.get("model")
        if not name:
            continue
        details = model.get("details") or {}
        normalized.append(
            {
                "name": name,
                "size": model.get("size"),
                "parameter_size": details.get("parameter_size"),
                "quantization_level": details.get("quantization_level"),
                "family": details.get("family"),
            }
        )

    def sort_key(item):
        size = item.get("parameter_size") or ""
        try:
            numeric = float(str(size).rstrip("Bb"))
        except Exception:
            numeric = 0.0
        return (numeric, item["name"].lower())

    normalized.sort(key=sort_key)
    return normalized


def choose_model(mode: str, settings: dict, models: list[dict], tile: str | None = None) -> str | None:
    if not models:
        return None

    def matches_model_name(candidate: str, target: str) -> bool:
        candidate_base = candidate.split(":", 1)[0].lower()
        target_base = target.split(":", 1)[0].lower()
        return candidate.lower() == target.lower() or candidate_base == target_base

    if mode == "lite" and LITE_MODEL_ENV:
        for model in models:
            if matches_model_name(model["name"], LITE_MODEL_ENV):
                return LITE_MODEL_ENV

    if mode == "heavy" and HEAVY_MODEL_ENV:
        for model in models:
            if matches_model_name(model["name"], HEAVY_MODEL_ENV):
                return HEAVY_MODEL_ENV

    explicit = settings.get(f"{mode}Model")
    if explicit:
        for model in models:
            if matches_model_name(model["name"], explicit):
                return model["name"]

    if mode == "heavy" and tile:
        model_profiles = settings.get("modelProfiles") if isinstance(settings.get("modelProfiles"), dict) else {}
        typed_name = model_profiles.get(tile)
        if typed_name:
            for model in models:
                if model["name"] == typed_name:
                    return typed_name

    if mode == "lite":
        for model in models:
            name = model["name"].lower()
            if any(token in name for token in ("phi", "mini", "small", "2b", "3b", "1b")):
                return model["name"]
        return models[0]["name"]

    return models[-1]["name"]


def warm_model(mode: str, settings: dict | None = None) -> bool:
    settings = settings or load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    models = discover_models()
    model_name = choose_model(mode, settings, models, None)
    if not model_name:
        return False

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": DEFAULT_SETTINGS[f"{mode}SystemPrompt"]},
            {"role": "user", "content": "Warm up and stay ready."},
        ],
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.0},
    }

    try:
        http_json(f"{OLLAMA_HOST}/api/chat", payload=payload, timeout=60.0)
        with MODEL_WARM_LOCK:
            MODEL_WARMED[mode] = True
        return True
    except Exception:
        return False


def build_messages(mode: str, prompt: str, history: list[dict], tile: str | None, settings: dict):
    system_prompt = settings.get(f"{mode}SystemPrompt") or DEFAULT_SETTINGS[f"{mode}SystemPrompt"]
    if tile in TILE_PROMPTS:
        system_prompt = f"{system_prompt}\n\n{TILE_PROMPTS[tile]}"

    messages = [{"role": "system", "content": system_prompt}]
    for entry in history[-24:]:
        if isinstance(entry, dict) and entry.get("role") in {"user", "assistant"}:
            messages.append({"role": entry["role"], "content": str(entry.get("content", ""))})
    messages.append({"role": "user", "content": prompt})
    return messages


def generate_fallback(mode: str, message: str, tile: str | None) -> str:
    if mode == "lite":
        return (
            "Synthia Lite is running in offline fallback mode. "
            "The local model engine is not available yet, but your message was "
            f"received: {message}"
        )

    tile_text = f" for {tile} mode" if tile else ""
    return (
        "Synthia Heavy is ready, but the local model engine is not reachable "
        f"right now{tile_text}. Your prompt was: {message}"
    )


def chat_with_ollama(mode: str, message: str, tile: str | None, history: list[dict], settings: dict):
    models = discover_models()
    model_name = choose_model(mode, settings, models, tile)
    if not model_name:
        return {"reply": generate_fallback(mode, message, tile), "model": None, "engine": "unavailable"}

    payload = {
        "model": model_name,
        "messages": build_messages(mode, message, history, tile, settings),
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": float(settings.get("temperature", DEFAULT_SETTINGS["temperature"]))},
    }

    try:
        response = http_json(f"{OLLAMA_HOST}/api/chat", payload=payload, timeout=600.0) #was 120.0 before
        if isinstance(response, dict):
            message_block = response.get("message") or {}
            reply = message_block.get("content") if isinstance(message_block, dict) else None
            if reply:
                # Strip accidental fallback-prefixes that may be injected into model output
                try:
                    reply = re.sub(r"(?i)Synthia\s+(Lite|Heavy).*?received:\s*", "", reply).strip()
                except Exception:
                    pass
                return {"reply": reply, "model": model_name, "engine": "ollama"}
    except Exception:
        pass

    return {"reply": generate_fallback(mode, message, tile), "model": model_name, "engine": "fallback"}


class SynthiaHandler(BaseHTTPRequestHandler):
    server_version = "SynthiaBackend/1.0"

    def log_message(self, format, *args):
        message = format % args
        stamp = time.strftime("%H:%M:%S")
        if "500" in message or "404" in message:
            prefix = "[ERR]"
        elif "200" in message or "204" in message:
            prefix = "[ OK]"
        else:
            prefix = "[---]"
        print(f"{prefix} {stamp} {message}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: int, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self._cors()
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._serve_html()
            return
        if path == "/api/bootstrap":
            self._bootstrap()
            return
        if path == "/api/settings":
            self._send_json(200, load_json(SETTINGS_FILE, DEFAULT_SETTINGS))
            return
        if path == "/api/chats":
            self._send_json(200, load_json(CHATS_FILE, DEFAULT_CHATS))
            return
        if path == "/api/models":
            self._send_json(200, {"models": discover_models(), "available": ollama_alive()})
            return
        if path == "/api/model-registry":
            self._send_json(200, {"items": get_registry(), "types": MODEL_TYPES})
            return
        if path == "/api/model/import/status":
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            job_id = str((query.get("jobId") or [""])[0]).strip()
            if not job_id:
                self._send_json(400, {"ok": False, "error": "jobId is required"})
                return
            payload = make_import_job_payload(job_id)
            if not payload.get("ok"):
                self._send_json(404, payload)
                return
            self._send_json(200, payload)
            return
        if path == "/api/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "ollama": ollama_alive(),
                    "port": PORT,
                    "storage": str(DATA_DIR),
                    "ollamaBinary": str(LOCAL_OLLAMA_EXE),
                    "ollamaBinaryPresent": LOCAL_OLLAMA_EXE.exists(),
                    "ollamaModelsDir": str(OLLAMA_MODELS_DIR),
                },
            )
            return
        self._serve_static(path)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/settings":
            self._update_settings()
            return
        if path == "/api/chats":
            self._save_chats()
            return
        if path == "/api/chat":
            self._handle_chat()
            return
        if path == "/api/model/import":
            self._handle_import_model()
            return
        if path == "/api/model/delete":
            self._handle_delete_model()
            return
        self._send_json(404, {"error": "not found"})

    def _serve_html(self):
        try:
            content = HTML_FILE.read_bytes()
        except FileNotFoundError:
            self._send_json(404, {"error": "synthia.html not found"})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._cors()
        self.end_headers()
        self.wfile.write(content)

    def _serve_static(self, path: str):
        safe = (ROOT / path.lstrip("/")).resolve()
        try:
            safe.relative_to(ROOT.resolve())
        except ValueError:
            self._send_json(403, {"error": "forbidden"})
            return

        if not safe.is_file():
            self._send_json(404, {"error": "not found"})
            return

        content = safe.read_bytes()
        content_type = mimetypes.guess_type(str(safe))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self._cors()
        self.end_headers()
        self.wfile.write(content)

    def _bootstrap(self):
        settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self._send_json(
            200,
            {
                "settings": settings,
                "chats": load_json(CHATS_FILE, DEFAULT_CHATS),
                "models": discover_models(),
                "registry": get_registry(),
                "modelTypes": MODEL_TYPES,
                "engine": {"ollama": ollama_alive()},
            },
        )

    def _update_settings(self):
        try:
            incoming = read_request_json(self)
            settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
            settings.update(incoming if isinstance(incoming, dict) else {})
            save_json(SETTINGS_FILE, settings)
            self._send_json(200, {"ok": True, "settings": settings})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _save_chats(self):
        try:
            incoming = read_request_json(self)
            if not isinstance(incoming, dict):
                raise ValueError("Expected an object with lite/heavy histories")
            save_json(CHATS_FILE, incoming)
            self._send_json(200, {"ok": True})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _handle_chat(self):
        try:
            incoming = read_request_json(self)
            mode = str(incoming.get("mode", "lite")).lower()
            if mode not in {"lite", "heavy"}:
                mode = "lite"
            message = str(incoming.get("message", "")).strip()
            if not message:
                self._send_json(400, {"ok": False, "error": "message is required"})
                return

            tile = incoming.get("tile")
            history = incoming.get("history") or []
            settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

            if mode == "heavy":
                threading.Thread(target=warm_model, args=("heavy", settings), daemon=True).start()

            chats = load_json(CHATS_FILE, DEFAULT_CHATS)
            mode_history = chats.get(mode)
            if not isinstance(mode_history, list):
                mode_history = []

            mode_history.append({"role": "user", "content": message})
            result = chat_with_ollama(mode, message, tile, history, settings)
            mode_history.append({"role": "assistant", "content": result["reply"]})

            chats[mode] = mode_history
            save_json(CHATS_FILE, chats)
            self._send_json(
                200,
                {
                    "ok": True,
                    "mode": mode,
                    "model": result.get("model"),
                    "engine": result.get("engine"),
                    "reply": result["reply"],
                    "history": mode_history,
                },
            )
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _handle_import_model(self):
        try:
            incoming = read_request_json(self)
            gguf_url = str(incoming.get("ggufUrl", "")).strip()
            model_name = str(incoming.get("modelName", "")).strip()
            model_type = str(incoming.get("modelType", "other")).strip().lower()
            if not gguf_url or not model_name:
                self._send_json(400, {"ok": False, "error": "ggufUrl and modelName are required"})
                return

            job_id = uuid.uuid4().hex
            with IMPORT_JOBS_LOCK:
                IMPORT_JOBS[job_id] = {
                    "jobId": job_id,
                    "state": "queued",
                    "message": "Queued for import.",
                    "downloadedBytes": 0,
                    "totalBytes": None,
                    "percent": None,
                    "speedBytesPerSecond": None,
                    "etaSeconds": None,
                    "startedAt": None,
                    "finishedAt": None,
                    "result": None,
                    "error": None,
                }

            threading.Thread(
                target=_run_import_job,
                args=(job_id, gguf_url, model_name, model_type),
                daemon=True,
            ).start()
            self._send_json(202, {"ok": True, "jobId": job_id})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _handle_delete_model(self):
        try:
            incoming = read_request_json(self)
            model_name = str(incoming.get("modelName", "")).strip()
            if not model_name:
                self._send_json(400, {"ok": False, "error": "modelName is required"})
                return

            result = delete_imported_model(model_name)
            self._send_json(200, {"ok": True, "result": result, "models": discover_models(), "registry": get_registry()})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})


def open_browser(url: str) -> None:
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass


def maybe_launch_ollama() -> None:
    bundled = ROOT / "Shared" / "bin" / "ollama-windows.exe"
    if bundled.exists():
        try:
            subprocess.Popen([str(bundled), "serve"], cwd=str(bundled.parent))
        except Exception:
            pass


def main() -> int:
    ensure_storage()
    if os.environ.get("SYNTHIA_AUTO_LAUNCH_OLLAMA", "1") != "0":
        maybe_launch_ollama()

    server = ThreadingHTTPServer((HOST, PORT), SynthiaHandler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Synthia backend running at {url}")
    print(f"Chat data: {DATA_DIR}")

    threading.Thread(target=warm_model, args=("lite",), daemon=True).start()

    if OPEN_BROWSER:
        threading.Timer(0.8, open_browser, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())