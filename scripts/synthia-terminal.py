#!/usr/bin/env python3
"""Minimal terminal client for Synthia.

The session is intentionally plain and low-noise. A single mode is selected at
startup and stays fixed for the life of the terminal session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


ROOT_URL = os.environ.get("SYNTHIA_BASE_URL", "http://127.0.0.1:3333").rstrip("/")
MODES = ["lite", "heavy", "video", "image", "pdf", "code", "pentest", "research"]


def request_json(path: str, payload: dict | None = None, timeout: float = 60.0):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{ROOT_URL}{path}", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip()


def wrap_block(text: str, width: int = 88) -> str:
    lines = []
    for paragraph in clean_text(text).split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        if paragraph.lstrip().startswith(("- ", "* ", ">", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            lines.append(paragraph)
            continue
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    return "\n".join(lines)


def print_line(text: str = "") -> None:
    print(text)


def divider(char: str = "-") -> None:
    print(char * 78)


@dataclass
class SessionState:
    mode: str
    settings: dict
    chats: dict
    models: list[dict]
    registry: list[dict]
    history: list[dict] = field(default_factory=list)


def normalize_mode(mode: str) -> str:
    mode = mode.strip().lower()
    if mode in {"light", "lite"}:
        return "lite"
    if mode not in MODES:
        raise ValueError(f"Unsupported mode: {mode}")
    return mode


def select_mode() -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mode", "-m", choices=MODES)
    args, _ = parser.parse_known_args()
    if args.mode:
        return args.mode

    print_line("Synthia terminal")
    divider()
    print_line("Select one session mode. It stays fixed in this terminal.")
    for index, mode in enumerate(MODES, start=1):
        print_line(f"  {index}. {mode}")
    print_line()
    while True:
        choice = input("Mode number or name: ").strip().lower()
        if not choice:
            continue
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(MODES):
                return MODES[index - 1]
        try:
            return normalize_mode(choice)
        except ValueError:
            print_line("Invalid mode. Try again.")


def bootstrap() -> SessionState:
    payload = request_json("/api/bootstrap", timeout=20.0)
    settings = payload.get("settings") or {}
    chats = payload.get("chats") or {}
    models = payload.get("models") or []
    registry = payload.get("registry") or []
    return SessionState(mode="lite", settings=settings, chats=chats, models=models, registry=registry)


def get_session_model(state: SessionState) -> str | None:
    settings = state.settings if isinstance(state.settings, dict) else {}
    models = state.models if isinstance(state.models, list) else []

    if state.mode == "lite":
        selected = str(settings.get("liteModel", "") or "")
        if selected:
            for model in models:
                if model.get("name") == selected:
                    return selected
    elif state.mode == "heavy":
        selected = str(settings.get("heavyModel", "") or "")
        if selected:
            for model in models:
                if model.get("name") == selected:
                    return selected
    else:
        model_profiles = settings.get("modelProfiles") if isinstance(settings.get("modelProfiles"), dict) else {}
        mapped = model_profiles.get(state.mode)
        if mapped:
            for model in models:
                if model.get("name") == mapped:
                    return mapped
    return None


def send_chat(state: SessionState, message: str) -> dict:
    history = state.history[-24:]
    backend_mode = state.mode if state.mode in {"lite", "heavy"} else "heavy"
    payload = {"mode": backend_mode, "message": message, "history": history}
    if state.mode not in {"lite", "heavy"}:
        payload["tile"] = state.mode
    return request_json("/api/chat", payload=payload, timeout=600.0)


def show_header(state: SessionState) -> None:
    divider()
    model_name = get_session_model(state) or "not selected"
    print_line(f"Synthia terminal | mode: {state.mode} | model: {model_name}")
    print_line("Type /help for commands. One mode per terminal session.")
    divider()


def show_help() -> None:
    print_line("Commands:")
    print_line("  /help     show commands")
    print_line("  /models   list available models")
    print_line("  /history  show session history")
    print_line("  /settings show current settings")
    print_line("  /clear    clear session history")
    print_line("  /import   import a GGUF model")
    print_line("  /delete   delete an imported model")
    print_line("  /quit     exit")


def show_models(state: SessionState) -> None:
    if not state.models:
        print_line("No models available.")
        return
    for model in state.models:
        name = model.get("name", "unknown")
        family = model.get("family") or "?"
        size = model.get("parameter_size") or model.get("size") or "?"
        quant = model.get("quantization_level") or "?"
        print_line(f"- {name} | {family} | {size} | {quant}")


def show_settings(state: SessionState) -> None:
    settings = state.settings if isinstance(state.settings, dict) else {}
    print_line(f"theme: {settings.get('theme', '')}")
    print_line(f"liteModel: {settings.get('liteModel', '')}")
    print_line(f"heavyModel: {settings.get('heavyModel', '')}")
    print_line(f"temperature: {settings.get('temperature', '')}")
    model_profiles = settings.get("modelProfiles") if isinstance(settings.get("modelProfiles"), dict) else {}
    if model_profiles:
        print_line("task routing:")
        for key, value in sorted(model_profiles.items()):
            print_line(f"  {key}: {value}")


def show_history(state: SessionState) -> None:
    if not state.history:
        print_line("Session history is empty.")
        return
    for index, entry in enumerate(state.history, start=1):
        role = entry.get("role", "?")
        content = entry.get("content", "")
        print_line(f"{index}. {role}: {content}")


def update_backend_settings(settings: dict) -> None:
    request_json("/api/settings", payload=settings, timeout=20.0)


def refresh_state(state: SessionState) -> None:
    payload = request_json("/api/bootstrap", timeout=20.0)
    state.settings = payload.get("settings") or {}
    state.chats = payload.get("chats") or {}
    state.models = payload.get("models") or []
    state.registry = payload.get("registry") or []


def handle_import(state: SessionState) -> None:
    gguf_url = input("GGUF URL: ").strip()
    model_name = input("Model name: ").strip()
    model_type = input("Model type (lite/heavy/video/image/pdf/code/pentest/research/other): ").strip().lower() or "other"
    if not gguf_url or not model_name:
        print_line("Import cancelled.")
        return
    result = request_json(
        "/api/model/import",
        payload={"ggufUrl": gguf_url, "modelName": model_name, "modelType": model_type},
        timeout=900.0,
    )
    if result.get("ok"):
        print_line("Import complete.")
        refresh_state(state)
    else:
        print_line(f"Import failed: {result.get('error', 'unknown error')}")


def handle_delete(state: SessionState) -> None:
    model_name = input("Model name to delete: ").strip()
    if not model_name:
        print_line("Delete cancelled.")
        return
    result = request_json("/api/model/delete", payload={"modelName": model_name}, timeout=300.0)
    if result.get("ok"):
        print_line("Model deleted.")
        refresh_state(state)
    else:
        print_line(f"Delete failed: {result.get('error', 'unknown error')}")


def print_reply(role: str, text: str) -> None:
    prefix = "You" if role == "user" else "Synthia"
    print_line(f"{prefix}: {wrap_block(text)}")


def main() -> int:
    try:
        state = bootstrap()
    except Exception as exc:
        print_line(f"Could not contact Synthia backend: {exc}")
        return 1

    state.mode = select_mode()
    refresh_state(state)

    history_key = state.mode if state.mode in {"lite", "heavy"} else "heavy"
    state.history = list((state.chats.get(history_key) or [])[-24:])

    show_header(state)
    if state.history:
        print_line("Loaded previous session messages.")

    while True:
        try:
            message = input("synthia> ").strip()
        except (EOFError, KeyboardInterrupt):
            print_line()
            break

        if not message:
            continue

        if message.startswith("/"):
            command = message.lower()
            if command in {"/quit", "/exit"}:
                break
            if command == "/help":
                show_help()
            elif command == "/models":
                show_models(state)
            elif command == "/history":
                show_history(state)
            elif command == "/settings":
                show_settings(state)
            elif command == "/clear":
                state.history = []
                print_line("Session history cleared.")
            elif command == "/import":
                handle_import(state)
            elif command == "/delete":
                handle_delete(state)
            else:
                print_line("Unknown command. Type /help.")
            continue

        state.history.append({"role": "user", "content": message})
        print_reply("user", message)

        try:
            response = send_chat(state, message)
        except urllib.error.HTTPError as exc:
            print_line(f"Request failed: {exc}")
            state.history.pop()
            continue
        except Exception as exc:
            print_line(f"Request failed: {exc}")
            state.history.pop()
            continue

        reply = str(response.get("reply", "")).strip()
        if not reply:
            reply = "No response received."
        state.history.append({"role": "assistant", "content": reply})
        print_line()
        print_reply("assistant", reply)
        print_line()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())