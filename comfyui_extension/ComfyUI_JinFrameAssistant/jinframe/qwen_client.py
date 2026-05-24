"""Qwen / Ollama / OpenAI-compatible local LLM for chat."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def detect_qwen() -> dict[str, Any]:
    """Prefer Ollama with a qwen* model; fallback OpenAI-compatible /v1."""
    ollama = _env("JINFRAME_OLLAMA_URL", _env("OLLAMA_HOST", "http://127.0.0.1:11434"))
    if not ollama.startswith("http"):
        ollama = "http://" + ollama

    custom = _env("JINFRAME_QWEN_URL", "")
    if custom:
        return _probe_openai(custom, _env("JINFRAME_QWEN_MODEL", "qwen"))

    ok, model, detail = _probe_ollama(ollama)
    if ok:
        return {
            "ok": True,
            "backend": "ollama",
            "base_url": ollama,
            "model": model,
            "detail": detail,
        }

    for base in (
        _env("JINFRAME_LLM_URL", "http://127.0.0.1:8080/v1"),
        "http://127.0.0.1:8000/v1",
        "http://127.0.0.1:11434/v1",
    ):
        ok2, model2, detail2 = _probe_openai(base.rstrip("/"), _env("JINFRAME_QWEN_MODEL", "qwen"))
        if ok2:
            return {
                "ok": True,
                "backend": "openai",
                "base_url": base.rstrip("/"),
                "model": model2,
                "detail": detail2,
            }

    return {
        "ok": False,
        "backend": None,
        "base_url": ollama,
        "model": None,
        "detail": "未检测到 Qwen。请安装 Ollama 并执行: ollama pull qwen2.5:7b",
        "help_zh": [
            "1. 安装 Ollama: https://ollama.com",
            "2. 运行: ollama pull qwen2.5:7b",
            "3. 保持 Ollama 在后台运行后刷新本页",
        ],
    }


def _http_json(url: str, method: str = "GET", body: dict | None = None, timeout: float = 8) -> Any:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _probe_ollama(base: str) -> tuple[bool, str | None, str]:
    try:
        tags = _http_json(f"{base.rstrip('/')}/api/tags")
        models = [m.get("name", "") for m in tags.get("models", [])]
        qwen = next((m for m in models if "qwen" in m.lower()), None)
        if qwen:
            return True, qwen, f"Ollama 已就绪 ({qwen})"
        if models:
            return True, models[0], f"Ollama 无 qwen 模型，暂用 {models[0]}"
        return False, None, "Ollama 已启动但没有模型，请 ollama pull qwen2.5:7b"
    except Exception as e:
        return False, None, f"Ollama 未连接: {e}"


def _probe_openai(base_v1: str, prefer: str) -> tuple[bool, str | None, str]:
    base = base_v1.rstrip("/")
    if base.endswith("/v1"):
        url = f"{base}/models"
    else:
        url = f"{base}/v1/models"
    try:
        data = _http_json(url)
        ids = []
        for m in data.get("data", data.get("models", [])):
            if isinstance(m, dict):
                ids.append(m.get("id", m.get("name", "")))
            else:
                ids.append(str(m))
        qwen = next((i for i in ids if prefer.lower() in i.lower() or "qwen" in i.lower()), None)
        if qwen:
            return True, qwen, f"API 已就绪 ({qwen})"
        if ids:
            return True, ids[0], f"API 已就绪 ({ids[0]})"
        return False, None, "API 无可用模型"
    except Exception as e:
        return False, None, str(e)


def chat(messages: list[dict], system: str | None = None) -> dict[str, Any]:
    info = detect_qwen()
    if not info.get("ok"):
        return {"ok": False, "reply": info.get("detail", "LLM 不可用"), "llm": info}

    backend = info["backend"]
    model = info["model"]
    try:
        if backend == "ollama":
            return _chat_ollama(info["base_url"], model, messages, system)
        return _chat_openai(info["base_url"], model, messages, system)
    except Exception as e:
        return {"ok": False, "reply": f"对话失败: {e}", "llm": info}


def _chat_ollama(base: str, model: str, messages: list[dict], system: str | None) -> dict:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)
    body = {"model": model, "messages": msgs, "stream": False}
    data = _http_json(f"{base.rstrip('/')}/api/chat", method="POST", body=body, timeout=120)
    content = data.get("message", {}).get("content", "")
    return {"ok": True, "reply": content, "model": model, "backend": "ollama"}


def _chat_openai(base_v1: str, model: str, messages: list[dict], system: str | None) -> dict:
    base = base_v1.rstrip("/")
    url = f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)
    body = {"model": model, "messages": msgs, "stream": False}
    data = _http_json(url, method="POST", body=body, timeout=120)
    content = data["choices"][0]["message"]["content"]
    return {"ok": True, "reply": content, "model": model, "backend": "openai"}
