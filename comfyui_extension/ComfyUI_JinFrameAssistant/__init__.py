"""
JinFrame Assistant — right-side chat + model downloads + Qwen + Cursor Agent.
"""
from __future__ import annotations

import asyncio
import os

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _register_routes() -> None:
    from aiohttp import web
    from server import PromptServer

    from .jinframe import cursor_agent, qwen_client, registry, settings

    routes = PromptServer.instance.routes

    @routes.get("/jinframe/api/status")
    async def jinframe_status(_request):
        packs = registry.scan_packs()
        qwen = qwen_client.detect_qwen()
        dl = registry.download_status()
        agent = cursor_agent.agent_status()
        missing_total = sum(p["missing_count"] for p in packs)
        return web.json_response(
            {
                "packs": packs,
                "qwen": qwen,
                "agent": agent,
                "download": dl,
                "missing_total": missing_total,
                "models_root": str(registry.comfy_models_root()),
            }
        )

    @routes.post("/jinframe/api/settings")
    async def jinframe_settings(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        patch = {}
        if "cursor_api_key" in body:
            key = (body.get("cursor_api_key") or "").strip()
            if key:
                patch["cursor_api_key"] = key
        if "agent_enabled" in body:
            patch["agent_enabled"] = bool(body["agent_enabled"])
        if "clear_key" in body and body["clear_key"]:
            patch["cursor_api_key"] = ""
        data = settings.save_config(patch) if patch else settings.load_config()
        agent = cursor_agent.agent_status()
        return web.json_response({"ok": True, "agent": agent, "saved": bool(patch)})

    @routes.post("/jinframe/api/download")
    async def jinframe_download(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        pack_ids = body.get("pack_ids") or []
        file_ids = body.get("file_ids") or []
        result = registry.start_downloads(pack_ids=pack_ids, file_ids=file_ids)
        return web.json_response(result)

    @routes.post("/jinframe/api/chat")
    async def jinframe_chat(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        messages = body.get("messages") or []
        user = (body.get("message") or "").strip()
        use_agent = bool(body.get("use_agent"))
        api_key = body.get("cursor_api_key")
        session_id = body.get("session_id")

        if use_agent:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: cursor_agent.chat(api_key, user, messages, session_id),
            )
            return web.json_response(result)

        if user:
            messages = list(messages) + [{"role": "user", "content": user}]
        system = body.get("system") or (
            "你是 JinFrame ComfyUI 助手。用简单中文回答。帮助用户选择工作流、"
            "解释缺什么模型、如何点击「一键下载」。不要讨论色情内容。"
        )
        result = qwen_client.chat(messages, system=system)
        return web.json_response(result)


_register_routes()
