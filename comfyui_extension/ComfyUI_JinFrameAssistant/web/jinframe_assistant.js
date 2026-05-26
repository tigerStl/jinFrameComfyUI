import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const PANEL_ID = "jinframe-assistant-panel";
const BTN_ID = "jinframe-assistant-fab";
const CSS_HREF = "extensions/ComfyUI_JinFrameAssistant/jinframe_assistant.css";
let uiMounted = false;

function loadStylesheet() {
  const id = "jinframe-assistant-css-link";
  if (document.getElementById(id)) return;
  const link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.type = "text/css";
  link.href = CSS_HREF;
  document.head.appendChild(link);
}
const LS_AGENT = "jinframe_use_agent";
const LS_KEY = "jinframe_cursor_api_key";
const LS_SESSION = "jinframe_agent_session";

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

async function mountAssistantUi() {
  if (uiMounted || document.getElementById(BTN_ID)) {
    uiMounted = true;
    return;
  }
  loadStylesheet();

  const fab = el("button", "jinframe-fab", "💬");
    fab.id = BTN_ID;
    fab.title = "JinFrame 助手";
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

    const agentBar = el("div", "jinframe-agent-bar", "");
    agentBar.id = "jinframe-agent-bar";
    agentBar.innerHTML = `
      <label class="jinframe-agent-toggle">
        <input type="checkbox" id="jinframe-agent-enable" />
        <span>启用 <b>Cursor Agent</b> 修改工作流</span>
      </label>
      <div class="jinframe-key-row" id="jinframe-key-row">
        <input type="password" id="jinframe-cursor-key" class="jinframe-key-input"
          placeholder="Cursor API Key（cursor.com → Settings → Integrations）" autocomplete="off" />
        <button type="button" class="jinframe-btn-secondary" id="jinframe-save-key">保存 Key</button>
      </div>
      <div class="jinframe-agent-hint" id="jinframe-agent-status"></div>
    `;
    panel.appendChild(agentBar);

    const qwenBar = el("div", "jinframe-qwen", "");
    qwenBar.id = "jinframe-qwen-bar";
    panel.appendChild(qwenBar);

    const modelSection = el("div", "jinframe-models", "");
    modelSection.id = "jinframe-model-section";
    modelSection.appendChild(
      el(
        "div",
        "jinframe-section-title",
        "模型安装（可勾选单个文件，或点每行「下载」）"
      )
    );
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
    chatInput.placeholder = "例：把 Wan I2V 默认分辨率改成 768×432";
    chatInput.rows = 2;
    chatSection.appendChild(chatInput);
    const sendBtn = el("button", "jinframe-btn-primary", "发送");
    sendBtn.type = "button";
    sendBtn.id = "jinframe-send-btn";
    chatSection.appendChild(sendBtn);
    panel.appendChild(chatSection);

    document.body.appendChild(panel);

    const agentCb = document.getElementById("jinframe-agent-enable");
    const keyInput = document.getElementById("jinframe-cursor-key");
    const keyRow = document.getElementById("jinframe-key-row");
    const agentStatusEl = document.getElementById("jinframe-agent-status");
    const saveKeyBtn = document.getElementById("jinframe-save-key");

    agentCb.checked = localStorage.getItem(LS_AGENT) === "1";
    keyInput.value = localStorage.getItem(LS_KEY) || "";

    let chatHistory = [];
    let pollTimer = null;
    let agentSessionId = localStorage.getItem(LS_SESSION) || crypto.randomUUID();
    const fileSelection = new Set();
    let selectionTouched = false;

    const useAgent = () => agentCb.checked;

    const updateAgentUi = () => {
      keyRow.style.display = useAgent() ? "flex" : "none";
      qwenBar.style.display = useAgent() ? "none" : "block";
      chatInput.placeholder = useAgent()
        ? "描述要如何改 workflows/ 里的 json…"
        : "问我：缺什么模型？怎么出图？…";
    };

    agentCb.addEventListener("change", () => {
      localStorage.setItem(LS_AGENT, useAgent() ? "1" : "0");
      updateAgentUi();
    });

    const renderAgent = (agent) => {
      const parts = [];
      if (!agent.sdk_installed) {
        parts.push("⚠️ 需安装 cursor-sdk（见安装脚本 pip install）");
      }
      if (agent.has_key) {
        parts.push(`🔑 已保存 Key: <code>${agent.key_masked}</code>`);
      } else {
        parts.push("🔑 未保存 API Key");
      }
      parts.push(`📁 仓库: <code>${agent.repo_root || ""}</code>`);
      agentStatusEl.innerHTML = parts.join("<br>");
    };

    const renderQwen = (qwen) => {
      if (useAgent()) return;
      const ok = qwen.ok;
      qwenBar.className = "jinframe-qwen " + (ok ? "ok" : "bad");
      qwenBar.innerHTML = ok
        ? `🟢 Qwen 已连接 · ${qwen.backend} · <code>${qwen.model}</code>`
        : `🔴 Qwen 未就绪 · ${qwen.detail || ""}<br><small>${(qwen.help_zh || []).join("<br>")}</small>`;
    };

    const captureFileSelection = () => {
      if (!modelList.querySelector(".jinframe-file-cb")) return;
      fileSelection.clear();
      modelList.querySelectorAll(".jinframe-file-cb:checked").forEach((cb) => {
        if (!cb.disabled) fileSelection.add(cb.dataset.fileId);
      });
      selectionTouched = true;
    };

    const shouldCheckFile = (fileId, installed) => {
      if (installed) return false;
      if (!selectionTouched) return true;
      return fileSelection.has(fileId);
    };

    const syncPackHeader = (block) => {
      const packCb = block.querySelector(".jinframe-pack-cb");
      const fileCbs = [
        ...block.querySelectorAll(".jinframe-file-cb:not(:disabled)"),
      ];
      if (!fileCbs.length) {
        packCb.checked = false;
        packCb.disabled = true;
        packCb.indeterminate = false;
        return;
      }
      packCb.disabled = false;
      const n = fileCbs.filter((c) => c.checked).length;
      packCb.checked = n === fileCbs.length;
      packCb.indeterminate = n > 0 && n < fileCbs.length;
    };

    const startFileDownloads = async (fileIds) => {
      if (!fileIds.length) {
        alert("请先勾选要下载的模型，或点某一行的「下载」");
        return;
      }
      await api.fetchApi("/jinframe/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds }),
      });
      document.getElementById("jinframe-dl-status").textContent =
        "已开始下载 " + fileIds.length + " 个文件，请保持窗口打开…";
      if (!pollTimer) pollTimer = setInterval(refresh, 3000);
    };

    const renderPacks = (packs) => {
      if (modelList.querySelector(".jinframe-file-cb")) {
        captureFileSelection();
      }

      modelList.innerHTML = "";
      let anyMissing = false;
      for (const p of packs) {
        if (!p.all_installed) anyMissing = true;

        const block = el("div", "jinframe-pack-block", "");
        block.dataset.packId = p.id;

        const header = el("label", "jinframe-pack-header", "");
        const packCb = document.createElement("input");
        packCb.type = "checkbox";
        packCb.className = "jinframe-pack-cb";
        packCb.title = "全选/取消本组";
        header.appendChild(packCb);
        const badge = p.all_installed
          ? '<span class="jinframe-badge ok">已安装</span>'
          : `<span class="jinframe-badge miss">缺 ${p.missing_count} 个</span>`;
        header.insertAdjacentHTML(
          "beforeend",
          `<span class="jinframe-pack-title"><strong>${p.label_zh}</strong> ${badge}</span>`
        );
        block.appendChild(header);

        if (p.workflow_hint) {
          const hint = el("div", "jinframe-pack-hint", "");
          hint.textContent = p.workflow_hint;
          block.appendChild(hint);
        }

        const ul = el("ul", "jinframe-file-list", "");
        for (const f of p.files) {
          const li = el("li", "jinframe-file-row " + (f.installed ? "ok" : "miss"), "");
          if (f.installed) {
            li.innerHTML = `<span class="jinframe-file-name">✓ ${f.name}</span>`;
          } else {
            const row = el("div", "jinframe-file-actions", "");
            const lab = el("label", "jinframe-file-label", "");
            const fcb = document.createElement("input");
            fcb.type = "checkbox";
            fcb.className = "jinframe-file-cb";
            fcb.dataset.fileId = f.id;
            fcb.dataset.packId = p.id;
            fcb.checked = shouldCheckFile(f.id, false);
            lab.appendChild(fcb);
            const nameSpan = el("span", "jinframe-file-name", f.name);
            lab.appendChild(nameSpan);
            row.appendChild(lab);
            const oneBtn = el("button", "jinframe-file-dl-btn", "下载");
            oneBtn.type = "button";
            oneBtn.dataset.fileId = f.id;
            oneBtn.addEventListener("click", (ev) => {
              ev.preventDefault();
              ev.stopPropagation();
              startFileDownloads([f.id]);
            });
            row.appendChild(oneBtn);
            li.appendChild(row);

            fcb.addEventListener("change", () => {
              captureFileSelection();
              syncPackHeader(block);
            });
          }
          ul.appendChild(li);
        }
        block.appendChild(ul);

        if (p.note_zh) {
          const note = el("div", "jinframe-pack-note", "");
          note.textContent = p.note_zh;
          block.appendChild(note);
        }

        packCb.addEventListener("change", () => {
          const on = packCb.checked;
          block
            .querySelectorAll(".jinframe-file-cb:not(:disabled)")
            .forEach((fc) => {
              fc.checked = on;
            });
          captureFileSelection();
          syncPackHeader(block);
        });

        syncPackHeader(block);
        modelList.appendChild(block);
      }

      if (!anyMissing) {
        modelList.innerHTML =
          '<p class="jinframe-all-ok">✅ 常用模型包已就绪。</p>';
      }
    };

    const updateDownloadStatus = (dl) => {
      const statusEl = document.getElementById("jinframe-dl-status");
      if (!statusEl) return;
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
    };

    const refresh = async () => {
      try {
        const st = await fetchStatus();
        renderAgent(st.agent || {});
        renderQwen(st.qwen);
        const dl = st.download || {};
        updateDownloadStatus(dl);
        if (!dl.active) {
          renderPacks(st.packs);
        }
        if (st.agent?.has_key && !keyInput.value) {
          keyInput.placeholder = `已保存 ${st.agent.key_masked}，可输入新 Key 覆盖`;
        }
      } catch (e) {
        agentStatusEl.textContent = "无法连接助手 API，请重启 ComfyUI";
      }
    };

    saveKeyBtn.addEventListener("click", async () => {
      const key = keyInput.value.trim();
      if (!key) {
        alert("请粘贴 Cursor API Key");
        return;
      }
      await api.fetchApi("/jinframe/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cursor_api_key: key,
          agent_enabled: useAgent(),
        }),
      });
      localStorage.setItem(LS_KEY, key);
      await refresh();
      appendMsg("assistant", "✅ API Key 已保存到本机 ComfyUI 配置。");
    });

    const toggle = () => {
      const open = panel.style.display !== "none";
      panel.style.display = open ? "none" : "flex";
      fab.classList.toggle("open", !open);
      if (!open) {
        updateAgentUi();
        refresh();
      }
    };

    fab.addEventListener("click", toggle);
    closeBtn.addEventListener("click", toggle);

    document.getElementById("jinframe-dl-btn").addEventListener("click", async () => {
      const fileIds = [
        ...document.querySelectorAll(".jinframe-file-cb:checked:not(:disabled)"),
      ].map((c) => c.dataset.fileId);
      await startFileDownloads(fileIds);
    });

    const appendMsg = (role, text) => {
      const m = el("div", "jinframe-msg " + role, text.replace(/\n/g, "<br>"));
      chatLog.appendChild(m);
      chatLog.scrollTop = chatLog.scrollHeight;
    };

    const sendChat = async () => {
      const text = chatInput.value.trim();
      if (!text) return;
      if (useAgent() && !keyInput.value.trim()) {
        const st = await fetchStatus();
        if (!st.agent?.has_key) {
          alert("启用 Agent 前请先填写并保存 Cursor API Key");
          keyInput.focus();
          return;
        }
      }
      chatInput.value = "";
      appendMsg("user", text);
      sendBtn.disabled = true;
      if (useAgent()) {
        appendMsg(
          "assistant",
          "<em>Cursor Agent 运行中，可能需要 1–5 分钟，请稍候…</em>"
        );
      }
      try {
        const payload = {
          message: text,
          messages: chatHistory,
          use_agent: useAgent(),
          cursor_api_key: keyInput.value.trim() || undefined,
          session_id: agentSessionId,
        };
        const r = await api.fetchApi("/jinframe/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await r.json();
        if (chatLog.lastChild?.classList?.contains("assistant")) {
          const last = chatLog.lastChild;
          if (last.textContent.includes("运行中")) last.remove();
        }
        if (data.ok) {
          chatHistory.push({ role: "user", content: text });
          chatHistory.push({ role: "assistant", content: data.reply });
          if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
          appendMsg("assistant", data.reply);
          if (data.backend === "cursor") {
            localStorage.setItem(LS_SESSION, agentSessionId);
          }
        } else {
          appendMsg("assistant", data.reply || "请求失败");
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

    updateAgentUi();
    await refresh();
    setInterval(refresh, 15000);
    uiMounted = true;
    console.log("[JinFrame] Assistant UI ready (click the blue chat button on the right)");
}

app.registerExtension({
  name: "JinFrame.Assistant",

  async init() {
    try {
      await mountAssistantUi();
    } catch (e) {
      console.error("[JinFrame] Assistant init failed:", e);
    }
  },

  async setup() {
    try {
      await mountAssistantUi();
    } catch (e) {
      console.error("[JinFrame] Assistant setup failed:", e);
    }
  },
});
