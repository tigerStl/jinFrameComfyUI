"""Cursor SDK local agent — edit workflows/ in jinFrameComfyUI repo."""
from __future__ import annotations

import os
import threading
from typing import Any

from . import registry
from .settings import get_api_key, public_settings

_AGENT_SYSTEM = """你是 JinFrame ComfyUI 工作流编辑助手。工作目录是 jinFrameComfyUI 仓库。

硬性规则：
1. 只允许修改 workflows/ 目录下的 .json 与 .md 说明文件
2. 不要修改 install/、模型权重、色情或露骨 prompt
3. 修改后简要说明改了哪些文件；提醒用户在 ComfyUI 里重新 Load 工作流
4. 保持 JSON 合法（UTF-8，缩进 2 空格）

用户用中文提问时，用简单中文回复。"""

_SESSIONS: dict[str, str] = {}
_SESSION_LOCK = threading.Lock()
_SDK_OK: bool | None = None


def sdk_available() -> bool:
    global _SDK_OK
    if _SDK_OK is not None:
        return _SDK_OK
    try:
        import cursor_sdk  # noqa: F401

        _SDK_OK = True
    except ImportError:
        _SDK_OK = False
    return _SDK_OK


def _format_history(messages: list[dict]) -> str:
    lines = []
    for m in messages[-10:]:
        role = m.get("role", "user")
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"[{role}]\n{content}")
    return "\n\n".join(lines)


def _build_prompt(user_message: str, messages: list[dict]) -> str:
    hist = _format_history(messages)
    parts = [_AGENT_SYSTEM]
    if hist:
        parts.append("--- 对话历史 ---\n" + hist)
    parts.append("--- 当前请求 ---\n" + user_message.strip())
    return "\n\n".join(parts)


def _extract_reply(result: Any, run: Any | None = None) -> str:
    if run is not None:
        try:
            return (run.text() or "").strip()
        except Exception:
            pass
    if result is None:
        return ""
    for attr in ("result", "summary", "output"):
        val = getattr(result, attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return str(result)


def _run_agent_sync(
    api_key: str,
    user_message: str,
    messages: list[dict],
    session_id: str | None,
) -> dict[str, Any]:
    if not sdk_available():
        return {
            "ok": False,
            "reply": (
                "未安装 cursor-sdk。请让管理员执行：\n"
                f'  "{registry.comfy_models_root().parent.parent / "python_embeded" / "python.exe"}" '
                "-m pip install cursor-sdk\n"
                "然后重启 ComfyUI。"
            ),
            "backend": "cursor_sdk_missing",
        }

    from cursor_sdk import Agent, AgentOptions, LocalAgentOptions

    cwd = str(registry.repo_root())
    if not (registry.repo_root() / "workflows").is_dir():
        return {
            "ok": False,
            "reply": f"仓库路径不存在或缺少 workflows/: {cwd}",
            "backend": "cursor",
        }

    model = os.environ.get("JINFRAME_CURSOR_MODEL", "composer-2.5")
    local = LocalAgentOptions(cwd=cwd)
    opts = AgentOptions(api_key=api_key, model=model, local=local)
    prompt = _build_prompt(user_message, messages)
    sid = (session_id or "default").strip() or "default"

    def _forget_session() -> None:
        with _SESSION_LOCK:
            _SESSIONS.pop(sid, None)

    def _is_socket_error(err_text: str) -> bool:
        t = (err_text or "").lower()
        # Windows socket/stream teardown seen when the underlying connection is closed
        return ("winerror 10038" in t) or ("not a socket" in t) or ("10038" in t)

    def _run_fresh() -> dict[str, Any]:
        with Agent.create(opts) as agent:
            new_id = getattr(agent, "id", None) or getattr(
                getattr(agent, "summary", None), "id", None
            )
            if new_id:
                with _SESSION_LOCK:
                    _SESSIONS[sid] = str(new_id)
            run = agent.send(prompt)
            result = run.wait()
            if getattr(result, "status", None) == "error":
                return {
                    "ok": False,
                    "reply": f"Agent 运行失败: {result}",
                    "backend": "cursor",
                }
            text = _extract_reply(result, run)
            return {
                "ok": True,
                "reply": text or "（Agent 已完成，请查看 workflows 目录变更）",
                "backend": "cursor",
                "agent_id": new_id,
                "repo_root": cwd,
            }

    try:
        with _SESSION_LOCK:
            agent_id = _SESSIONS.get(sid)

        if agent_id:
            # Resume must keep the same local cwd/model, otherwise the SDK may treat it as
            # a different context and the streaming socket can error on Windows.
            with Agent.resume(agent_id, opts) as agent:
                run = agent.send(prompt)
                result = run.wait()
                if getattr(result, "status", None) == "error":
                    return {
                        "ok": False,
                        "reply": f"Agent 运行失败: {result}",
                        "backend": "cursor",
                        "agent_id": agent_id,
                    }
                text = _extract_reply(result, run)
                return {
                    "ok": True,
                    "reply": text or "（Agent 已完成，请查看 workflows 目录变更）",
                    "backend": "cursor",
                    "agent_id": agent_id,
                    "repo_root": cwd,
                }

        return _run_fresh()
    except Exception as e:
        import traceback

        err = str(e)
        tb = traceback.format_exc(limit=12)
        if "401" in err or "auth" in err.lower() or "api key" in err.lower():
            return {
                "ok": False,
                "reply": "Cursor API Key 无效或未授权。请在 Cursor 设置 → Integrations 中创建 Key 后重新保存。",
                "backend": "cursor",
            }
        # WinError 10038 is commonly a broken/closed streaming socket. Drop session and retry once.
        if _is_socket_error(err):
            _forget_session()
            try:
                retry = _run_fresh()
                if retry.get("ok"):
                    retry["reply"] = (
                        "（检测到连接中断，已自动重试成功）\n\n" + str(retry.get("reply") or "")
                    ).strip()
                return retry
            except Exception as e2:
                err2 = str(e2)
                tb2 = traceback.format_exc(limit=12)
                return {
                    "ok": False,
                    "reply": (
                        "Cursor Agent 连接异常（WinError 10038）。\n"
                        "已尝试清空会话并重试，仍失败。\n\n"
                        f"错误: {err2}\n"
                        "建议：关闭并重启 ComfyUI / Cursor，确认网络未被防火墙拦截。\n"
                    ),
                    "backend": "cursor",
                    "debug": {"error": err2, "trace": tb2},
                }
        return {
            "ok": False,
            "reply": f"Cursor Agent 错误: {err}",
            "backend": "cursor",
            "debug": {"error": err, "trace": tb},
        }


def chat(
    api_key: str | None,
    user_message: str,
    messages: list[dict] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    key = get_api_key(api_key)
    if not key:
        return {
            "ok": False,
            "reply": "请先填写并保存 Cursor API Key（Cursor 设置 → Integrations → User API Keys）。",
            "backend": "cursor",
        }
    if not user_message.strip():
        return {"ok": False, "reply": "请输入内容", "backend": "cursor"}
    return _run_agent_sync(key, user_message, messages or [], session_id)


def agent_status() -> dict[str, Any]:
    return {
        "sdk_installed": sdk_available(),
        "repo_root": str(registry.repo_root()),
        **public_settings(),
    }
