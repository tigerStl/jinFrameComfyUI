"""Cursor SDK local agent — edit workflows/ in jinFrameComfyUI repo."""
from __future__ import annotations

import os
import sys
import threading
from typing import Any

from . import registry
from .cursor_bridge_patch import apply_cursor_sdk_windows_patch, patch_status
from .debug_log import log_event, log_exception, log_file_path
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


def _use_resume() -> bool:
    """Agent.resume() 在部分 Windows 环境会触发 WinError 10038；默认关闭。"""
    v = os.environ.get("JINFRAME_CURSOR_AGENT_USE_RESUME", "").strip().lower()
    return v in ("1", "true", "yes", "on")


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


def _is_socket_error(err_text: str) -> bool:
    t = (err_text or "").lower()
    return ("winerror 10038" in t) or ("not a socket" in t) or ("10038" in t)


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

    apply_cursor_sdk_windows_patch()

    from cursor_sdk import AgentOptions, LocalAgentOptions
    from cursor_sdk._client import Client, close_default_client

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

    log_event(
        "cursor_agent_start",
        session_id=sid,
        use_resume=_use_resume(),
        model=model,
        cwd=cwd,
        python=sys.executable,
        prompt_len=len(prompt),
        message_preview=user_message.strip()[:200],
        log_file=str(log_file_path()) if log_file_path() else None,
        bridge_patch=patch_status(),
    )

    def _forget_session() -> None:
        with _SESSION_LOCK:
            _SESSIONS.pop(sid, None)

    def _run_with_client(mode: str, agent_id: str | None = None) -> dict[str, Any]:
        """Launch bridge in jinFrame repo (not ComfyUI cwd); avoid broken default client."""
        close_default_client()
        log_event("cursor_agent_run", mode=mode, session_id=sid, agent_id=agent_id, cwd=cwd)
        client = Client.launch_bridge(workspace=cwd, timeout=45)
        try:
            if mode == "resume" and agent_id:
                agent = client.resume_agent(agent_id, opts)
            else:
                agent = client.create_agent(opts)
            with agent:
                new_id = agent.agent_id or agent_id
                if new_id and _use_resume() and mode == "create":
                    with _SESSION_LOCK:
                        _SESSIONS[sid] = str(new_id)
                run = agent.send(prompt)
                result = run.wait()
                if getattr(result, "status", None) == "error":
                    return {
                        "ok": False,
                        "reply": f"Agent 运行失败: {result}",
                        "backend": "cursor",
                        "agent_id": new_id,
                    }
                text = _extract_reply(result, run)
                out = {
                    "ok": True,
                    "reply": text or "（Agent 已完成，请查看 workflows 目录变更）",
                    "backend": "cursor",
                    "agent_id": new_id,
                    "repo_root": cwd,
                }
                log_event(
                    "cursor_agent_ok",
                    mode=mode,
                    session_id=sid,
                    agent_id=new_id,
                    reply_len=len(text or ""),
                )
                return out
        finally:
            client.close()
            close_default_client()

    def _run_fresh() -> dict[str, Any]:
        return _run_with_client("create")

    def _run_resume(agent_id: str) -> dict[str, Any]:
        return _run_with_client("resume", agent_id)

    try:
        agent_id: str | None = None
        if _use_resume():
            with _SESSION_LOCK:
                agent_id = _SESSIONS.get(sid)

        if agent_id:
            try:
                return _run_resume(agent_id)
            except Exception as e:
                if not _is_socket_error(str(e)):
                    raise
                log_exception(
                    "cursor_agent_socket_error",
                    e,
                    phase="resume",
                    session_id=sid,
                    agent_id=agent_id,
                )
                _forget_session()

        return _run_fresh()
    except Exception as e:
        import traceback

        err = str(e)
        tb = traceback.format_exc(limit=12)
        log_exception(
            "cursor_agent_error",
            e,
            session_id=sid,
            use_resume=_use_resume(),
            is_socket=_is_socket_error(err),
        )
        if "401" in err or "auth" in err.lower() or "api key" in err.lower():
            return {
                "ok": False,
                "reply": "Cursor API Key 无效或未授权。请在 Cursor 设置 → Integrations 中创建 Key 后重新保存。",
                "backend": "cursor",
            }
        if _is_socket_error(err):
            _forget_session()
            log_event("cursor_agent_retry", session_id=sid, reason="socket_error_10038")
            try:
                retry = _run_fresh()
                if retry.get("ok"):
                    log_event("cursor_agent_retry_ok", session_id=sid)
                    retry["reply"] = (
                        "（检测到连接中断，已自动重试成功）\n\n" + str(retry.get("reply") or "")
                    ).strip()
                return retry
            except Exception as e2:
                err2 = str(e2)
                tb2 = traceback.format_exc(limit=12)
                log_exception(
                    "cursor_agent_retry_failed",
                    e2,
                    session_id=sid,
                    first_error=err,
                )
                hint = (
                    "若仍失败：1) 完全退出并重启 ComfyUI  2) 升级 cursor-sdk："
                    f'"{sys.executable}" -m pip install -U cursor-sdk\n'
                    "3) 确认已安装 Cursor 桌面版且 cursor-sdk-bridge 在 PATH\n"
                    "4) WinError 10038 需本插件 Windows 补丁（重新 install_jinframe_assistant）"
                )
                log_hint = ""
                lp = log_file_path()
                if lp:
                    log_hint = f"\n详细日志已写入: {lp}"
                return {
                    "ok": False,
                    "reply": (
                        "Cursor Agent 连接异常（WinError 10038）。\n"
                        "已尝试清空会话并重试，仍失败。\n\n"
                        f"错误: {err2}\n"
                        f"{hint}{log_hint}\n"
                    ),
                    "backend": "cursor",
                    "debug": {"error": err2, "trace": tb2, "log_file": str(lp) if lp else None},
                }
        log_hint = ""
        lp = log_file_path()
        if lp:
            log_hint = f"\n详细日志: {lp}"
        return {
            "ok": False,
            "reply": f"Cursor Agent 错误: {err}{log_hint}",
            "backend": "cursor",
            "debug": {"error": err, "trace": tb, "log_file": str(lp) if lp else None},
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
    lp = log_file_path()
    return {
        "sdk_installed": sdk_available(),
        "repo_root": str(registry.repo_root()),
        "agent_use_resume": _use_resume(),
        "debug_log_enabled": lp is not None,
        "debug_log_path": str(lp) if lp else None,
        "bridge_patch": patch_status(),
        **public_settings(),
    }
