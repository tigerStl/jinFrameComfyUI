import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const PANEL_ID = "jinframe-assistant-panel";
const BTN_ID = "jinframe-assistant-fab";
const CSS_HREF = "extensions/ComfyUI_JinFrameAssistant/jinframe_assistant.css";
/** Bump when UI changes; also forces browser to reload CSS after sync. */
const UI_BUILD = "20260527-chatux";
let uiMounted = false;

function loadStylesheet() {
  const id = "jinframe-assistant-css-link";
  let link = document.getElementById(id);
  const href = `${CSS_HREF}?v=${UI_BUILD}`;
  if (link) {
    if (link.getAttribute("href") !== href) link.href = href;
    return;
  }
  link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.type = "text/css";
  link.href = href;
  document.head.appendChild(link);
}
const LS_AGENT = "jinframe_use_agent";
const LS_SESSION = "jinframe_agent_session";
const LS_MODEL_COLLAPSE = "jinframe_models_collapsed";

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
    fab.title = "金帧AI助手";
    document.body.appendChild(fab);

    const panel = el("div", "jinframe-panel");
    panel.id = PANEL_ID;
    panel.style.display = "none";

    const header = el("div", "jinframe-header");
    header.appendChild(el("span", "jinframe-title", "<b>金帧AI助手</b>"));
    header.appendChild(el("span", "jinframe-version", UI_BUILD));
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
          placeholder="Cursor API Key（cursor.com → Integrations）" autocomplete="off" />
        <button type="button" class="jinframe-btn-secondary" id="jinframe-save-key">保存</button>
      </div>
      <div class="jinframe-key-compact" id="jinframe-key-compact" style="display:none">
        <button type="button" class="jinframe-key-icon-btn" id="jinframe-key-icon" title="API Key 已保存在本机 ComfyUI 配置">🔑</button>
        <button type="button" class="jinframe-btn-link" id="jinframe-update-key">更新 Key</button>
      </div>
      <div class="jinframe-agent-hint" id="jinframe-agent-status"></div>
    `;
    panel.appendChild(agentBar);

    const qwenBar = el("div", "jinframe-qwen", "");
    qwenBar.id = "jinframe-qwen-bar";
    panel.appendChild(qwenBar);

    const modelSection = el("div", "jinframe-models", "");
    modelSection.id = "jinframe-model-section";
    const modelHead = el("div", "jinframe-model-head", "");
    modelHead.innerHTML = `
      <span class="jinframe-section-title jinframe-model-head-text">模型安装（可勾选单个文件，或点每行「下载」）</span>
      <button type="button" class="jinframe-model-collapse-btn" id="jinframe-model-collapse" title="收起/展开">▼</button>
    `;
    const modelBody = el("div", "jinframe-model-body", "");
    modelBody.id = "jinframe-model-body";
    const modelList = el("div", "jinframe-pack-list", "");
    modelList.id = "jinframe-pack-list";
    modelBody.appendChild(modelList);
    const dlBar = el("div", "jinframe-dl-bar", "");
    dlBar.innerHTML =
      '<button type="button" class="jinframe-btn-primary" id="jinframe-dl-btn">一键下载所选</button>' +
      '<span id="jinframe-dl-status"></span>';
    modelBody.appendChild(dlBar);
    modelSection.appendChild(modelHead);
    modelSection.appendChild(modelBody);
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
    const keyCompact = document.getElementById("jinframe-key-compact");
    const updateKeyBtn = document.getElementById("jinframe-update-key");
    const agentStatusEl = document.getElementById("jinframe-agent-status");
    const saveKeyBtn = document.getElementById("jinframe-save-key");

    agentCb.checked = localStorage.getItem(LS_AGENT) === "1";
    keyInput.value = "";
    try {
      localStorage.removeItem("jinframe_cursor_api_key");
    } catch (_e) {
      /* ignore */
    }

    let lastAgent = {};
    let keyEditorMode = false;

    let chatHistory = [];
    let chatBusy = false;
    let pollTimer = null;
    let agentSessionId = localStorage.getItem(LS_SESSION) || crypto.randomUUID();
    const fileSelection = new Set();
    let selectionTouched = false;
    let lastDownloadState = { active: false, items: {}, error: null };
    const POLL_IDLE_MS = 15000;
    const POLL_DOWNLOAD_MS = 1000;

    const scheduleRefresh = (intervalMs) => {
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(refresh, intervalMs);
    };

    const setDownloadBusy = (busy) => {
      modelSection.classList.toggle("jinframe-dl-busy", busy);
      const mainBtn = document.getElementById("jinframe-dl-btn");
      if (mainBtn) mainBtn.disabled = busy;
      modelList
        .querySelectorAll(".jinframe-file-dl-btn, .jinframe-pack-dl-btn")
        .forEach((b) => {
          b.disabled = busy;
        });
    };

    const applyDownloadProgress = (dl) => {
      lastDownloadState = dl || { active: false, items: {}, error: null };
      setDownloadBusy(!!dl?.active);
      for (const [fid, info] of Object.entries(dl?.items || {})) {
        const btn = modelList.querySelector(
          `.jinframe-file-dl-btn[data-file-id="${fid}"]`
        );
        if (!btn) continue;
        btn.disabled = true;
        if (info.done) btn.textContent = "完成";
        else if (info.skipped) btn.textContent = "已有";
        else btn.textContent = `${info.pct ?? 0}%`;
      }
      modelList.querySelectorAll(".jinframe-pack-dl-btn").forEach((b) => {
        b.disabled = !!dl?.active;
        if (dl?.active) b.textContent = "下载中…";
        else b.textContent = "下载本组";
      });
    };

    async function postDownload(payload) {
      const resp = await api.fetchApi("/jinframe/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp || !resp.ok) {
        const txt = resp ? await resp.text() : "";
        throw new Error(
          `下载 API 失败 (${resp?.status || "?"}): ${txt.slice(0, 120)}`
        );
      }
      return resp.json();
    }

    const useAgent = () => agentCb.checked;

    const syncKeyUi = () => {
      if (!useAgent()) {
        keyRow.style.display = "none";
        keyCompact.style.display = "none";
        return;
      }
      const has = !!lastAgent.has_key;
      if (keyEditorMode || !has) {
        keyRow.style.display = "flex";
        keyCompact.style.display = "none";
      } else {
        keyRow.style.display = "none";
        keyCompact.style.display = "flex";
      }
    };

    const updateAgentUi = () => {
      syncKeyUi();
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
      if (!agent.has_key) {
        parts.push("🔑 未保存 API Key（请粘贴后点保存）");
      }
      parts.push(`📁 仓库: <code>${agent.repo_root || ""}</code>`);
      if (agent.agent_use_resume) {
        parts.push("<small>Agent 会话续接已开启（JINFRAME_CURSOR_AGENT_USE_RESUME）</small>");
      }
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
      const ids = [...new Set(fileIds.filter(Boolean))];
      if (!ids.length) {
        alert("没有可下载的模型（请勾选未安装项）");
        return;
      }
      if (lastDownloadState.active) {
        alert("已有下载任务进行中，请等待完成");
        return;
      }
      setDownloadBusy(true);
      document.getElementById("jinframe-dl-status").textContent =
        "正在启动下载…";
      ids.forEach((fid) => {
        const btn = modelList.querySelector(
          `.jinframe-file-dl-btn[data-file-id="${fid}"]`
        );
        if (btn) {
          btn.disabled = true;
          btn.textContent = "0%";
        }
      });
      try {
        const data = await postDownload({ file_ids: ids });
        if (!data.started) {
          setDownloadBusy(false);
          const msg =
            data.reason === "already_downloading"
              ? "已有下载任务进行中"
              : data.reason === "no_files_selected"
                ? "未选择有效文件"
                : "无法开始下载: " + (data.reason || "unknown");
          document.getElementById("jinframe-dl-status").textContent = msg;
          alert(msg);
          return;
        }
        document.getElementById("jinframe-dl-status").textContent =
          "已开始下载 " + ids.length + " 个文件，请保持 ComfyUI 窗口打开…";
        scheduleRefresh(POLL_DOWNLOAD_MS);
        await refresh();
      } catch (e) {
        setDownloadBusy(false);
        const err = String(e);
        document.getElementById("jinframe-dl-status").textContent =
          "下载启动失败: " + err;
        alert("下载启动失败:\n" + err);
        modelList.querySelectorAll(".jinframe-file-dl-btn").forEach((b) => {
          if (!b.closest(".jinframe-file-row.miss")) return;
          b.disabled = false;
          b.textContent = "下载";
        });
      }
    };

    const renderPacks = (packs, dl) => {
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
        const headerRow = el("div", "jinframe-pack-header-row", "");
        headerRow.appendChild(header);

        const packMeta = el("div", "jinframe-pack-meta", "");
        const metaParts = [];
        if (p.lock_version != null) metaParts.push(`锁定 v${p.lock_version}`);
        if (p.locked_at) metaParts.push(`@${String(p.locked_at).slice(0, 10)}`);
        if (p.pack_size_label && !p.all_installed) {
          metaParts.push(`待下载合计 ${p.pack_size_label}`);
        }
        if (metaParts.length) packMeta.textContent = metaParts.join(" · ");

        const packDlBtn = el("button", "jinframe-pack-dl-btn", "下载本组");
        packDlBtn.type = "button";
        packDlBtn.disabled = p.all_installed || !!dl?.active;
        if (p.all_installed) packDlBtn.textContent = "已就绪";
        packDlBtn.addEventListener("click", (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          const ids = [...block.querySelectorAll(".jinframe-file-cb")].map(
            (c) => c.dataset.fileId
          );
          startFileDownloads(ids);
        });
        headerRow.appendChild(packDlBtn);
        block.appendChild(headerRow);
        if (metaParts.length) block.appendChild(packMeta);

        if (p.workflow_hint) {
          const hint = el("div", "jinframe-pack-hint", "");
          hint.textContent = p.workflow_hint;
          block.appendChild(hint);
        }

        const ul = el("ul", "jinframe-file-list", "");
        for (const f of p.files) {
          const li = el("li", "jinframe-file-row " + (f.installed ? "ok" : "miss"), "");
          const metaBits = [];
          if (f.revision_short) metaBits.push(`rev ${f.revision_short}`);
          if (f.size_label) metaBits.push(f.size_label);
          const metaHtml = metaBits.length
            ? `<div class="jinframe-file-meta">${metaBits.join(" · ")}</div>`
            : "";

          if (f.installed) {
            const instMeta = [];
            if (f.size_gb != null) instMeta.push(`${f.size_gb} GB`);
            if (f.revision_short) instMeta.push(`rev ${f.revision_short}`);
            li.innerHTML =
              `<span class="jinframe-file-name">✓ ${f.name}</span>` +
              (instMeta.length
                ? `<div class="jinframe-file-meta">${instMeta.join(" · ")}</div>`
                : "");
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
            const nameCol = el("div", "jinframe-file-name-col", "");
            nameCol.appendChild(el("span", "jinframe-file-name", f.name));
            if (metaHtml) nameCol.insertAdjacentHTML("beforeend", metaHtml);
            lab.appendChild(nameCol);
            row.appendChild(lab);
            const itemProg = dl?.items?.[f.id];
            const oneBtn = el("button", "jinframe-file-dl-btn", "下载");
            oneBtn.type = "button";
            oneBtn.dataset.fileId = f.id;
            if (dl?.active) {
              oneBtn.disabled = true;
              if (itemProg?.done) oneBtn.textContent = "完成";
              else if (itemProg?.skipped) oneBtn.textContent = "已有";
              else if (itemProg) oneBtn.textContent = `${itemProg.pct ?? 0}%`;
            }
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
          .map(([k, v]) => {
            if (v.done) return `${k}: 完成`;
            if (v.skipped) return `${k}: 跳过`;
            return `${k}: ${v.pct ?? 0}%`;
          })
          .join(" · ");
        statusEl.textContent = "下载中… " + (items || "请稍候");
      } else if (dl.error) {
        statusEl.textContent = "下载错误: " + dl.error;
      } else if (dl._justFinished) {
        statusEl.textContent = "下载已完成";
      } else {
        statusEl.textContent = "";
      }
    };

    const refresh = async () => {
      try {
        const st = await fetchStatus();
        lastAgent = st.agent || {};
        renderAgent(lastAgent);
        renderQwen(st.qwen);
        syncKeyUi();
        const dl = st.download || {};
        const wasActive = lastDownloadState.active;
        if (dl.active) {
          applyDownloadProgress(dl);
          renderPacks(st.packs, dl);
        } else {
          if (wasActive) dl._justFinished = true;
          setDownloadBusy(false);
          renderPacks(st.packs, dl);
          scheduleRefresh(POLL_IDLE_MS);
        }
        updateDownloadStatus(dl);
        lastDownloadState = dl;
        if (st.agent?.has_key) {
          keyInput.placeholder = "输入新 Key 覆盖已保存的配置";
        } else {
          keyInput.placeholder = "Cursor API Key（cursor.com → Integrations）";
        }
      } catch (e) {
        setDownloadBusy(false);
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
      keyEditorMode = false;
      keyInput.value = "";
      await refresh();
      appendMsg("assistant", "✅ API Key 已保存到本机 ComfyUI 配置。");
    });

    updateKeyBtn.addEventListener("click", () => {
      keyEditorMode = true;
      keyInput.value = "";
      syncKeyUi();
      keyInput.focus();
    });
    document.getElementById("jinframe-key-icon").addEventListener("click", () => {
      updateKeyBtn.click();
    });

    const collapseBtn = document.getElementById("jinframe-model-collapse");
    if (localStorage.getItem(LS_MODEL_COLLAPSE) === "1") {
      modelSection.classList.add("jinframe-models-collapsed");
      collapseBtn.textContent = "▶";
    }
    collapseBtn.addEventListener("click", () => {
      const collapsed = modelSection.classList.toggle("jinframe-models-collapsed");
      collapseBtn.textContent = collapsed ? "▶" : "▼";
      localStorage.setItem(LS_MODEL_COLLAPSE, collapsed ? "1" : "0");
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
      return m;
    };

    const removePendingReply = () => {
      document.getElementById("jinframe-pending-reply")?.remove();
    };

    const showPendingReply = (label) => {
      removePendingReply();
      const m = el(
        "div",
        "jinframe-msg assistant jinframe-msg-pending",
        `<em>${label}</em>`
      );
      m.id = "jinframe-pending-reply";
      chatLog.appendChild(m);
      chatLog.scrollTop = chatLog.scrollHeight;
      return m;
    };

    const setChatBusy = (busy) => {
      chatBusy = busy;
      sendBtn.disabled = busy;
      chatInput.disabled = busy;
      sendBtn.textContent = busy ? "处理中…" : "发送";
    };

    /** Let the browser paint user message + pending state before await. */
    const yieldToPaint = () =>
      new Promise((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(resolve));
      });

    const sendChat = async () => {
      const text = chatInput.value.trim();
      if (!text || chatBusy) return;

      setChatBusy(true);
      chatInput.value = "";
      appendMsg("user", text);
      const pendingLabel = useAgent()
        ? "正在调用 Cursor Agent…（可能需要 1–5 分钟）"
        : "正在调用本地助手…";
      showPendingReply(pendingLabel);
      await yieldToPaint();

      try {
        if (useAgent() && !keyInput.value.trim()) {
          const st = await fetchStatus();
          lastAgent = st.agent || lastAgent;
          if (!st.agent?.has_key) {
            removePendingReply();
            appendMsg(
              "assistant",
              "启用 Agent 前请先填写并保存 Cursor API Key。"
            );
            keyEditorMode = true;
            syncKeyUi();
            keyInput.focus();
            return;
          }
        }

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
        removePendingReply();
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
        removePendingReply();
        appendMsg("assistant", "请求失败: " + e);
      } finally {
        setChatBusy(false);
        chatInput.focus();
      }
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
    scheduleRefresh(POLL_IDLE_MS);
    uiMounted = true;
    console.log(`[金帧AI助手] UI ${UI_BUILD} ready (click the blue chat button on the right)`);
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
