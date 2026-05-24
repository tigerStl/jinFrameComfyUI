"""
JinFrame Assistant — right-side chat + one-click model downloads + Qwen (Ollama).
Install: copy this folder to ComfyUI/custom_nodes/ComfyUI_JinFrameAssistant
"""
from __future__ import annotations

import os

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _register_routes() -> None:
    from aiohttp import web
    from server import PromptServer

    from .jinframe import qwen_client, registry

    routes = PromptServer.instance.routes

    @routes.get("/jinframe/api/status")
    async def jinframe_status(_request):
        packs = registry.scan_packs()
        qwen = qwen_client.detect_qwen()
        dl = registry.download_status()
        missing_total = sum(p["missing_count"] for p in packs)
        return web.json_response(
            {
                "packs": packs,
                "qwen": qwen,
                "download": dl,
                "missing_total": missing_total,
                "models_root": str(registry.comfy_models_root()),
            }
        )

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
        if user:
            messages = list(messages) + [{"role": "user", "content": user}]
        system = body.get("system") or (
            "你是 JinFrame ComfyUI 助手。用简单中文回答。帮助用户选择工作流、"
            "解释缺什么模型、如何点击「一键下载」。不要讨论色情内容。"
        )
        result = qwen_client.chat(messages, system=system)
        return web.json_response(result)


_register_routes()
