import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import "./jinframe_assistant.css";

const PANEL_ID = "jinframe-assistant-panel";
const BTN_ID = "jinframe-assistant-fab";

function el(tag, cls, html) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

async function fetchStatus() {
  const r = await api.fetchApi("/jinframe/api/status");
  return await r.json();
}

app.registerExtension({
  name: "JinFrame.Assistant",

  async setup() {
    if (document.getElementById(BTN_ID)) return;

    const fab = el("button", "jinframe-fab", "💬");
    fab.id = BTN_ID;
    fab.title = "JinFrame 助手（模型下载 + Qwen 对话）";
    document.body.appendChild(fab);

    const panel = el("div", "jinframe-panel");
    panel.id = PANEL_ID;
    panel.style.display = "none";

    const header = el("div", "jinframe-header");
    header.appendChild(el("span", "jinframe-title", "<b>JinFrame 助手</b>"));
    const closeBtn = el("button", "jinframe-close", "×");
    closeBtn.type = "button";
    header.appendChild(closeBtn);
    panel.appendChild(header);

    const qwenBar = el("div", "jinframe-qwen", "");
    qwenBar.id = "jinframe-qwen-bar";
    panel.appendChild(qwenBar);

    const modelSection = el("div", "jinframe-models", "");
    modelSection.id = "jinframe-model-section";
    const modelTitle = el("div", "jinframe-section-title", "模型安装状态（勾选后点一键下载）");
    modelSection.appendChild(modelTitle);
    const modelList = el("div", "jinframe-pack-list", "");
    modelList.id = "jinframe-pack-list";
    modelSection.appendChild(modelList);
    const dlBar = el("div", "jinframe-dl-bar", "");
    dlBar.innerHTML =
      '<button type="button" class="jinframe-btn-primary" id="jinframe-dl-btn">一键下载所选</button>' +
      '<span id="jinframe-dl-status"></span>';
    modelSection.appendChild(dlBar);
    panel.appendChild(modelSection);

    const chatSection = el("div", "jinframe-chat-wrap", "");
    const chatLog = el("div", "jinframe-chat-log", "");
    chatLog.id = "jinframe-chat-log";
    chatSection.appendChild(chatLog);
    const chatInput = el("textarea", "jinframe-chat-input", "");
    chatInput.id = "jinframe-chat-input";
    chatInput.placeholder = "问我：缺什么模型？怎么出图？…";
    chatInput.rows = 2;
    chatSection.appendChild(chatInput);
    const sendBtn = el("button", "jinframe-btn-primary", "发送");
    sendBtn.type = "button";
    sendBtn.id = "jinframe-send-btn";
    chatSection.appendChild(sendBtn);
    panel.appendChild(chatSection);

    document.body.appendChild(panel);

    let chatHistory = [];
    let pollTimer = null;

    const renderQwen = (qwen) => {
      const ok = qwen.ok;
      qwenBar.className = "jinframe-qwen " + (ok ? "ok" : "bad");
      qwenBar.innerHTML = ok
        ? `🟢 Qwen 已连接 · ${qwen.backend} · <code>${qwen.model}</code>`
        : `🔴 Qwen 未就绪 · ${qwen.detail || ""}<br><small>${(qwen.help_zh || []).join("<br>")}</small>`;
    };

    const renderPacks = (packs) => {
      modelList.innerHTML = "";
      let anyMissing = false;
      for (const p of packs) {
        if (!p.all_installed) anyMissing = true;
        const row = el("label", "jinframe-pack-row", "");
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "jinframe-pack-cb";
        cb.dataset.packId = p.id;
        cb.checked = p.missing_count > 0;
        cb.disabled = p.all_installed;
        row.appendChild(cb);
        const badge = p.all_installed
          ? '<span class="jinframe-badge ok">已安装</span>'
          : `<span class="jinframe-badge miss">缺 ${p.missing_count} 个文件</span>`;
        const files = p.files
          .map((f) => `<li class="${f.installed ? "ok" : "miss"}">${f.name}</li>`)
          .join("");
        const body = el("div", "jinframe-pack-body", "");
        body.innerHTML = `<strong>${p.label_zh}</strong> ${badge}<br><small>${p.workflow_hint}</small><ul>${files}</ul>${p.note_zh ? "<em>" + p.note_zh + "</em>" : ""}`;
        row.appendChild(body);
        modelList.appendChild(row);
      }
      modelSection.style.display = anyMissing ? "block" : "none";
      if (!anyMissing) {
        modelList.innerHTML = '<p class="jinframe-all-ok">✅ 常用模型包已就绪。可直接加载工作流。</p>';
        modelSection.style.display = "block";
      }
    };

    const refresh = async () => {
      try {
        const st = await fetchStatus();
        renderQwen(st.qwen);
        renderPacks(st.packs);
        const dl = st.download || {};
        const statusEl = document.getElementById("jinframe-dl-status");
        if (dl.active) {
          const items = Object.entries(dl.items || {})
            .map(([k, v]) => `${k}: ${v.pct ?? 0}%`)
            .join(" · ");
          statusEl.textContent = "下载中… " + items;
        } else if (dl.error) {
          statusEl.textContent = "下载错误: " + dl.error;
        } else {
          statusEl.textContent = "";
        }
      } catch (e) {
        qwenBar.className = "jinframe-qwen bad";
        qwenBar.textContent = "无法连接助手 API，请确认已安装 ComfyUI_JinFrameAssistant 并重启 ComfyUI";
      }
    };

    const toggle = () => {
      const open = panel.style.display !== "none";
      panel.style.display = open ? "none" : "flex";
      fab.classList.toggle("open", !open);
      if (!open) refresh();
    };

    fab.addEventListener("click", toggle);
    closeBtn.addEventListener("click", toggle);

    document.getElementById("jinframe-dl-btn").addEventListener("click", async () => {
      const ids = [...document.querySelectorAll(".jinframe-pack-cb:checked")].map(
        (c) => c.dataset.packId
      );
      if (!ids.length) {
        alert("请先勾选要下载的模型组");
        return;
      }
      await api.fetchApi("/jinframe/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pack_ids: ids }),
      });
      document.getElementById("jinframe-dl-status").textContent = "已开始下载，请保持 ComfyUI 窗口打开…";
      if (!pollTimer) pollTimer = setInterval(refresh, 3000);
    });

    const appendMsg = (role, text) => {
      const m = el("div", "jinframe-msg " + role, text.replace(/\n/g, "<br>"));
      chatLog.appendChild(m);
      chatLog.scrollTop = chatLog.scrollHeight;
    };

    const sendChat = async () => {
      const text = chatInput.value.trim();
      if (!text) return;
      chatInput.value = "";
      appendMsg("user", text);
      sendBtn.disabled = true;
      try {
        const r = await api.fetchApi("/jinframe/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, messages: chatHistory }),
        });
        const data = await r.json();
        if (data.ok) {
          chatHistory.push({ role: "user", content: text });
          chatHistory.push({ role: "assistant", content: data.reply });
          if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
          appendMsg("assistant", data.reply);
        } else {
          appendMsg("assistant", data.reply || "LLM 不可用");
        }
      } catch (e) {
        appendMsg("assistant", "请求失败: " + e);
      }
      sendBtn.disabled = false;
    };

    sendBtn.addEventListener("click", sendChat);
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChat();
      }
    });

    await refresh();
    setInterval(refresh, 15000);
  },
});
