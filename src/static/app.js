(() => {
  const POLICIES = {
    u1: "DOCENTE · Nível 2 · Máx 4h · Até 5 ativas · Antecedência 15 min · Auto-aprovação (salas comuns)",
    u2: "ALUNO · Nível 1 · Máx 2h · Até 2 ativas · Antecedência 30 min · Requer aprovação (PENDENTE)",
    u3: "GESTOR · Nível 3 · Máx 8h · Até 10 ativas · Antecedência 0 min · Aprovação, bloqueio e auditoria",
    custom: "ID customizado — útil para testar validações de vínculo (HTTP 403)",
  };

  const GRADE_HINTS = {
    s1: "Grade Acadêmica: 08:00–10:00",
    s2: "Grade Acadêmica: livre",
    s3: "Grade Acadêmica: 14:00–16:00 (Lab Restrito)",
  };

  const STORAGE_KEY = "ufpr_reservas_gui_session_v1";
  let sessionReservas = loadSessionReservas();
  let requestHistory = [];
  let lastCurl = "";
  let pendingSwapContext = null;

  // Helpers de data (sempre futura para respeitar antecedência mínima)
  function getFutureDateISO(daysAhead = 6) {
    const d = new Date();
    d.setDate(d.getDate() + daysAhead);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function makeDateTime(hour, minute = 0, daysAhead = 6) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${getFutureDateISO(daysAhead)}T${pad(hour)}:${pad(minute)}`;
  }

  function toApiIso(dtLocal) {
    if (!dtLocal) return "";
    return dtLocal.length === 16 ? `${dtLocal}:00` : dtLocal;
  }

  function formatShortDate(iso) {
    if (!iso) return "";
    return iso.replace("T", " ").slice(0, 16);
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function getActiveUserId() {
    const select = document.getElementById("global-user");
    if (select.value === "custom") {
      return document.getElementById("global-user-custom").value.trim() || "inexistente";
    }
    return select.value;
  }

  // Persistência local de reservas criadas na sessão
  function loadSessionReservas() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveSessionReservas() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessionReservas));
    } catch {
      // ignora restrições de storage
    }
  }

  function upsertSessionReserva(reserva) {
    if (!reserva || !reserva.id) return;
    const idx = sessionReservas.findIndex((r) => r.id === reserva.id);
    if (idx >= 0) {
      sessionReservas[idx] = reserva;
    } else {
      sessionReservas.unshift(reserva);
    }
    saveSessionReservas();
    renderSessionReservas();
  }

  function markSessionReservaStatus(id, status) {
    const item = sessionReservas.find((r) => r.id === id);
    if (item) {
      item.status = status;
      saveSessionReservas();
      renderSessionReservas();
    }
  }

  // Navegação por abas
  function switchTab(tabName) {
    document.querySelectorAll(".tab").forEach((btn) => {
      const isActive = btn.dataset.tab === tabName;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", String(isActive));
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("active", panel.id === `tab-${tabName}`);
    });
  }

  // Feedback visual por seção
  function showFeedback(elementId, type, message) {
    const el = document.getElementById(elementId);
    el.className = `feedback ${type}`;
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function hideFeedback(elementId) {
    const el = document.getElementById(elementId);
    el.classList.add("hidden");
  }

  function extractErrorMessage(data, fallbackStatus) {
    if (!data) return `Erro HTTP ${fallbackStatus}`;
    if (typeof data.detail === "string") return data.detail;
    if (data.detail && typeof data.detail === "object") {
      return data.detail.mensagem || JSON.stringify(data.detail);
    }
    return JSON.stringify(data);
  }

  // Cliente HTTP central + Inspetor
  function buildCurl(method, url, body) {
    const fullUrl = `${window.location.origin}${url}`;
    if (body) {
      return `curl -X ${method} "${fullUrl}" -H "Content-Type: application/json" -d '${JSON.stringify(body)}'`;
    }
    return `curl -X ${method} "${fullUrl}"`;
  }

  async function apiRequest(method, url, body = null) {
    const started = performance.now();
    const options = { method, headers: {} };
    if (body !== null) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    let status = 0;
    let statusText = "NETWORK ERROR";
    let data = null;

    try {
      const resp = await fetch(url, options);
      status = resp.status;
      statusText = resp.statusText;
      const text = await resp.text();
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = { raw: text };
      }
    } catch (err) {
      data = { error: err.message };
    }

    const elapsed = Math.round(performance.now() - started);
    const entry = {
      method,
      url,
      body,
      status,
      statusText,
      data,
      elapsed,
      curl: buildCurl(method, url, body),
    };

    requestHistory.unshift(entry);
    if (requestHistory.length > 15) requestHistory.pop();
    renderInspector(entry);
    renderHistory();

    return { ok: status >= 200 && status < 300, status, data };
  }

  function statusClass(status) {
    if (status >= 200 && status < 300) return "ok";
    if (status === 409) return "warn";
    if (status >= 400 || status === 0) return "err";
    return "neutral";
  }

  function renderInspector(entry) {
    const pill = document.getElementById("http-status");
    pill.textContent = entry.status ? `${entry.status} ${entry.statusText}` : "Erro";
    pill.className = `status-pill ${statusClass(entry.status)}`;

    document.getElementById("http-latency").textContent = `${entry.elapsed} ms`;
    document.getElementById("http-request").textContent = `${entry.method} ${entry.url}`;
    document.getElementById("http-response").textContent = JSON.stringify(entry.data, null, 2);

    lastCurl = entry.curl;
    document.getElementById("btn-copy-curl").disabled = false;
  }

  function renderHistory() {
    const ul = document.getElementById("http-history");
    if (!requestHistory.length) {
      ul.innerHTML = `<li class="empty-state small">As requisições feitas aparecerão aqui.</li>`;
      return;
    }
    ul.innerHTML = "";
    requestHistory.forEach((entry, idx) => {
      const li = document.createElement("li");
      li.className = "history-item";
      li.innerHTML = `
        <span class="status-pill ${statusClass(entry.status)}">${entry.status || "ERR"}</span>
        <span class="history-url" title="${escapeHtml(entry.method + " " + entry.url)}">
          <strong>${escapeHtml(entry.method)}</strong> ${escapeHtml(entry.url)}
        </span>
      `;
      li.addEventListener("click", () => renderInspector(requestHistory[idx]));
      ul.appendChild(li);
    });
  }

  // Renderização de Salas
  function renderSalas(salas) {
    const container = document.getElementById("salas-lista");
    if (!Array.isArray(salas) || salas.length === 0) {
      container.innerHTML = `<p class="empty-state">Nenhuma sala disponível para os critérios informados.</p>`;
      return;
    }

    container.innerHTML = "";
    salas.forEach((sala) => {
      const card = document.createElement("div");
      card.className = `sala-card ${sala.bloqueada_manutencao ? "bloqueada" : ""}`;

      const statusBadge = sala.bloqueada_manutencao
        ? `<span class="badge badge-rejeitada">BLOQUEADA</span>`
        : `<span class="badge badge-confirmada">OPERACIONAL</span>`;

      const gradeHint = GRADE_HINTS[sala.id] || "";

      card.innerHTML = `
        <div class="sala-top">
          <span class="sala-codigo">${escapeHtml(sala.codigo)} <code>${escapeHtml(sala.id)}</code></span>
          ${statusBadge}
        </div>
        <div class="sala-meta">
          <span>Tipo: <strong>${escapeHtml(sala.tipo)}</strong></span>
          <span>Lotação: <strong>${sala.lotacao}</strong> pessoas · Nível mín.: <strong>${sala.nivel_permissao_minimo}</strong></span>
          ${gradeHint ? `<span>${escapeHtml(gradeHint)}</span>` : ""}
        </div>
        <div class="sala-actions">
          <button type="button" class="btn btn-primary btn-xs btn-usar-sala">Reservar</button>
          <button type="button" class="btn btn-secondary btn-xs btn-toggle-bloqueio">
            ${sala.bloqueada_manutencao ? "Desbloquear (Gestor)" : "Bloquear Manutenção"}
          </button>
        </div>
      `;

      card.querySelector(".btn-usar-sala").addEventListener("click", () => {
        document.getElementById("res-usuario").value = document.getElementById("salas-usuario").value || getActiveUserId();
        document.getElementById("res-sala").value = sala.id;
        const sIni = document.getElementById("salas-inicio").value;
        const sFim = document.getElementById("salas-fim").value;
        if (sIni && sFim) {
          document.getElementById("res-inicio").value = sIni;
          document.getElementById("res-fim").value = sFim;
        }
        document.getElementById("res-qtd").value = Math.min(10, sala.lotacao);
        switchTab("reservas");
      });

      card.querySelector(".btn-toggle-bloqueio").addEventListener("click", async () => {
        const gestorId = getActiveUserId();
        const novoEstado = !sala.bloqueada_manutencao;
        const params = new URLSearchParams({
          gestor_id: gestorId,
          bloqueada: String(novoEstado),
        });
        const res = await apiRequest("PATCH", `/salas/${encodeURIComponent(sala.id)}/bloqueio?${params}`);
        if (res.ok) {
          showFeedback(
            "salas-feedback",
            "success",
            `Sala ${sala.codigo} ${novoEstado ? "bloqueada para manutenção" : "desbloqueada"} por ${gestorId}.`
          );
          consultarSalas();
        } else {
          showFeedback("salas-feedback", "error", extractErrorMessage(res.data, res.status));
        }
      });

      container.appendChild(card);
    });
  }

  async function consultarSalas() {
    hideFeedback("salas-feedback");
    const usuarioId = document.getElementById("salas-usuario").value.trim();
    const inicio = document.getElementById("salas-inicio").value;
    const fim = document.getElementById("salas-fim").value;

    const params = new URLSearchParams({ usuario_id: usuarioId });
    if (inicio) params.set("inicio", toApiIso(inicio));
    if (fim) params.set("fim", toApiIso(fim));

    const res = await apiRequest("GET", `/salas?${params.toString()}`);
    if (res.ok) {
      renderSalas(res.data);
      showFeedback(
        "salas-feedback",
        "info",
        `${res.data.length} sala(s) retornada(s) para o usuário "${usuarioId}".`
      );
    } else {
      document.getElementById("salas-lista").innerHTML = "";
      showFeedback("salas-feedback", "error", extractErrorMessage(res.data, res.status));
    }
  }

  // Renderização da lista de reservas da sessão
  function badgeClassForStatus(status) {
    const map = {
      CONFIRMADA: "badge-confirmada",
      PENDENTE: "badge-pendente",
      REJEITADA: "badge-rejeitada",
      CANCELADA: "badge-cancelada",
    };
    return map[status] || "badge-info";
  }

  function renderSessionReservas() {
    const container = document.getElementById("session-reservas");
    if (!sessionReservas.length) {
      container.innerHTML = `<p class="empty-state small">Nenhuma reserva criada ainda nesta sessão.</p>`;
      return;
    }

    container.innerHTML = "";
    sessionReservas.forEach((r) => {
      const item = document.createElement("div");
      item.className = "session-item";
      item.innerHTML = `
        <div class="session-item-top">
          <code>${escapeHtml(r.id)}</code>
          <span class="badge ${badgeClassForStatus(r.status)}">${escapeHtml(r.status)}</span>
        </div>
        <div class="session-item-meta">
          Usuário: <strong>${escapeHtml(r.usuario_id)}</strong> · Sala: <strong>${escapeHtml(r.sala_id)}</strong> · ${r.qtd_pessoas} pess.<br/>
          ${escapeHtml(formatShortDate(r.inicio))} → ${escapeHtml(formatShortDate(r.fim))}
        </div>
        <div class="session-item-actions">
          ${
            r.status === "PENDENTE"
              ? `<button type="button" class="btn btn-success btn-xs act-aprovar">Aprovar</button>
                 <button type="button" class="btn btn-danger btn-xs act-rejeitar">Rejeitar</button>`
              : ""
          }
          ${
            r.status === "CONFIRMADA" || r.status === "PENDENTE"
              ? `<button type="button" class="btn btn-secondary btn-xs act-trocar">Trocar</button>
                 <button type="button" class="btn btn-secondary btn-xs act-cancelar">Cancelar</button>`
              : ""
          }
          <button type="button" class="btn btn-ghost btn-xs act-auditar">Auditoria</button>
        </div>
      `;

      const btnAprovar = item.querySelector(".act-aprovar");
      if (btnAprovar) {
        btnAprovar.addEventListener("click", () => avaliarReserva(r.id, "u3", true));
      }

      const btnRejeitar = item.querySelector(".act-rejeitar");
      if (btnRejeitar) {
        btnRejeitar.addEventListener("click", () => avaliarReserva(r.id, "u3", false));
      }

      const btnTrocar = item.querySelector(".act-trocar");
      if (btnTrocar) {
        btnTrocar.addEventListener("click", () => {
          document.getElementById("troca-antiga-id").value = r.id;
          document.getElementById("troca-usuario").value = r.usuario_id;
          document.getElementById("troca-sala").value = r.sala_id === "s1" ? "s2" : "s1";
          document.getElementById("troca-inicio").value = r.inicio.slice(0, 16);
          document.getElementById("troca-fim").value = r.fim.slice(0, 16);
          document.getElementById("troca-qtd").value = r.qtd_pessoas;
          switchTab("reservas");
          document.getElementById("troca-antiga-id").focus();
        });
      }

      const btnCancelar = item.querySelector(".act-cancelar");
      if (btnCancelar) {
        btnCancelar.addEventListener("click", () => cancelarReserva(r.id, r.usuario_id));
      }

      item.querySelector(".act-auditar").addEventListener("click", () => {
        document.getElementById("audit-gestor").value = "u3";
        document.getElementById("audit-entidade").value = r.id;
        switchTab("auditoria");
        consultarAuditoria();
      });

      container.appendChild(item);
    });
  }

  // Solicitar Reserva
  async function solicitarReserva(e) {
    e.preventDefault();
    hideFeedback("reserva-feedback");
    document.getElementById("conflito-banner").classList.add("hidden");
    pendingSwapContext = null;

    const payload = {
      usuario_id: document.getElementById("res-usuario").value.trim(),
      sala_id: document.getElementById("res-sala").value,
      inicio: toApiIso(document.getElementById("res-inicio").value),
      fim: toApiIso(document.getElementById("res-fim").value),
      qtd_pessoas: Number(document.getElementById("res-qtd").value),
    };

    const res = await apiRequest("POST", "/reservas", payload);
    if (res.ok) {
      upsertSessionReserva(res.data);
      document.getElementById("aval-reserva-id").value = res.data.id;
      document.getElementById("canc-reserva-id").value = res.data.id;
      document.getElementById("canc-usuario").value = res.data.usuario_id;
      showFeedback(
        "reserva-feedback",
        "success",
        `Reserva ${res.data.id} criada com status ${res.data.status}.`
      );
      return;
    }

    if (
      res.status === 409 &&
      res.data &&
      typeof res.data.detail === "object" &&
      res.data.detail.codigo === "CONFLITO_AGENDA_USUARIO"
    ) {
      const antigaId = res.data.detail.reserva_atual_id;
      pendingSwapContext = { antigaId, payload };

      document.getElementById("conflito-msg").textContent =
        `${res.data.detail.mensagem} ${res.data.detail.acao_sugerida || ""}`;
      document.getElementById("conflito-banner").classList.remove("hidden");

      // Preenche também o formulário de troca manual
      document.getElementById("troca-antiga-id").value = antigaId;
      document.getElementById("troca-usuario").value = payload.usuario_id;
      document.getElementById("troca-sala").value = payload.sala_id;
      document.getElementById("troca-inicio").value = payload.inicio.slice(0, 16);
      document.getElementById("troca-fim").value = payload.fim.slice(0, 16);
      document.getElementById("troca-qtd").value = payload.qtd_pessoas;
      return;
    }

    showFeedback("reserva-feedback", "error", extractErrorMessage(res.data, res.status));
  }

  // Troca Atômica
  async function executarTroca(antigaId, payload, feedbackTarget = "troca-feedback") {
    hideFeedback(feedbackTarget);
    const res = await apiRequest(
      "POST",
      `/reservas/${encodeURIComponent(antigaId)}/troca`,
      payload
    );
    if (res.ok) {
      markSessionReservaStatus(antigaId, "CANCELADA");
      upsertSessionReserva(res.data);
      document.getElementById("conflito-banner").classList.add("hidden");
      pendingSwapContext = null;
      showFeedback(
        feedbackTarget,
        "success",
        `Troca atômica concluída! ${antigaId} cancelada e nova reserva ${res.data.id} (${res.data.status}) criada.`
      );
    } else {
      showFeedback(feedbackTarget, "error", extractErrorMessage(res.data, res.status));
    }
  }

  // Avaliar Reserva
  async function avaliarReserva(reservaId, aprovadorId, aprovada) {
    hideFeedback("avaliar-feedback");
    if (!reservaId) {
      showFeedback("avaliar-feedback", "error", "Informe o ID da reserva pendente.");
      return;
    }

    document.getElementById("aval-reserva-id").value = reservaId;
    document.getElementById("aval-aprovador").value = aprovadorId;

    const params = new URLSearchParams({
      aprovador_id: aprovadorId,
      aprovada: String(aprovada),
    });
    const res = await apiRequest(
      "POST",
      `/reservas/${encodeURIComponent(reservaId)}/avaliar?${params.toString()}`
    );
    if (res.ok) {
      upsertSessionReserva(res.data);
      showFeedback(
        "avaliar-feedback",
        "success",
        `Reserva ${res.data.id} atualizada para ${res.data.status} por ${aprovadorId}.`
      );
    } else {
      showFeedback("avaliar-feedback", "error", extractErrorMessage(res.data, res.status));
    }
  }

  // Cancelar Reserva
  async function cancelarReserva(reservaId, usuarioId) {
    hideFeedback("cancelar-feedback");
    if (!reservaId) {
      showFeedback("cancelar-feedback", "error", "Informe o ID da reserva.");
      return;
    }

    document.getElementById("canc-reserva-id").value = reservaId;
    document.getElementById("canc-usuario").value = usuarioId;

    const params = new URLSearchParams({ usuario_id: usuarioId });
    const res = await apiRequest(
      "POST",
      `/reservas/${encodeURIComponent(reservaId)}/cancelar?${params.toString()}`
    );
    if (res.ok) {
      upsertSessionReserva(res.data);
      showFeedback(
        "cancelar-feedback",
        "success",
        `Reserva ${res.data.id} cancelada com sucesso.`
      );
    } else {
      showFeedback("cancelar-feedback", "error", extractErrorMessage(res.data, res.status));
    }
  }

  // Auditoria
  async function consultarAuditoria() {
    hideFeedback("auditoria-feedback");
    const gestorId = document.getElementById("audit-gestor").value.trim();
    const entidadeId = document.getElementById("audit-entidade").value.trim();

    const params = new URLSearchParams({ gestor_id: gestorId });
    if (entidadeId) params.set("entidade_id", entidadeId);

    const res = await apiRequest("GET", `/auditoria?${params.toString()}`);
    const tbody = document.getElementById("auditoria-tbody");

    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">Acesso negado ou erro ao consultar logs.</td></tr>`;
      showFeedback("auditoria-feedback", "error", extractErrorMessage(res.data, res.status));
      return;
    }

    const logs = Array.isArray(res.data) ? [...res.data].reverse() : [];
    showFeedback("auditoria-feedback", "info", `${logs.length} evento(s) encontrado(s).`);

    if (!logs.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">Nenhum evento registrado para este filtro.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    logs.forEach((log) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${log.id ?? "-"}</td>
        <td>${escapeHtml(formatShortDate(log.timestamp))}</td>
        <td><code>${escapeHtml(log.acao)}</code></td>
        <td>${escapeHtml(log.usuario_id)}</td>
        <td><button type="button" class="link-btn">${escapeHtml(log.entidade_id)}</button></td>
        <td>${escapeHtml(log.ip)}</td>
      `;
      tr.querySelector(".link-btn").addEventListener("click", () => {
        document.getElementById("audit-entidade").value = log.entidade_id;
        consultarAuditoria();
      });
      tbody.appendChild(tr);
    });
  }

  // Sincronização do Usuário Ativo no cabeçalho
  function syncActiveUser() {
    const select = document.getElementById("global-user");
    const customInput = document.getElementById("global-user-custom");
    const isCustom = select.value === "custom";
    customInput.classList.toggle("hidden", !isCustom);

    const activeId = getActiveUserId();
    document.getElementById("persona-policy").textContent =
      POLICIES[select.value] || POLICIES.custom;

    document.getElementById("salas-usuario").value = activeId;
    document.getElementById("res-usuario").value = activeId;
    document.getElementById("troca-usuario").value = activeId;
    document.getElementById("canc-usuario").value = activeId;
  }

  // Inicialização
  function init() {
    // Valores iniciais de data (6 dias à frente -> ex: 2026-11-25)
    document.getElementById("res-inicio").value = makeDateTime(10, 0);
    document.getElementById("res-fim").value = makeDateTime(12, 0);
    document.getElementById("troca-inicio").value = makeDateTime(10, 0);
    document.getElementById("troca-fim").value = makeDateTime(12, 0);

    syncActiveUser();
    renderSessionReservas();

    // Eventos de abas
    document.querySelectorAll(".tab").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    // Persona switcher
    document.getElementById("global-user").addEventListener("change", syncActiveUser);
    document.getElementById("global-user-custom").addEventListener("input", syncActiveUser);

    // Tab 1: Salas
    document.getElementById("form-salas").addEventListener("submit", (e) => {
      e.preventDefault();
      consultarSalas();
    });
    document.getElementById("btn-limpar-horario-salas").addEventListener("click", () => {
      document.getElementById("salas-inicio").value = "";
      document.getElementById("salas-fim").value = "";
      consultarSalas();
    });
    document.getElementById("preset-salas-ana").addEventListener("click", () => {
      document.getElementById("salas-usuario").value = "u2";
      document.getElementById("salas-inicio").value = "";
      document.getElementById("salas-fim").value = "";
      consultarSalas();
    });
    document.getElementById("preset-salas-horario").addEventListener("click", () => {
      document.getElementById("salas-usuario").value = "u1";
      document.getElementById("salas-inicio").value = makeDateTime(14, 0);
      document.getElementById("salas-fim").value = makeDateTime(16, 0);
      consultarSalas();
    });
    document.getElementById("preset-salas-grade").addEventListener("click", () => {
      document.getElementById("salas-usuario").value = "u1";
      document.getElementById("salas-inicio").value = makeDateTime(8, 30);
      document.getElementById("salas-fim").value = makeDateTime(9, 30);
      consultarSalas();
    });

    // Tab 2: Reservas & Troca
    document.getElementById("form-reserva").addEventListener("submit", solicitarReserva);
    document.getElementById("preset-res-docente").addEventListener("click", () => {
      document.getElementById("res-usuario").value = "u1";
      document.getElementById("res-sala").value = "s1";
      document.getElementById("res-inicio").value = makeDateTime(10, 0);
      document.getElementById("res-fim").value = makeDateTime(12, 0);
      document.getElementById("res-qtd").value = 25;
    });
    document.getElementById("preset-res-aluno").addEventListener("click", () => {
      document.getElementById("res-usuario").value = "u2";
      document.getElementById("res-sala").value = "s2";
      document.getElementById("res-inicio").value = makeDateTime(14, 0);
      document.getElementById("res-fim").value = makeDateTime(16, 0);
      document.getElementById("res-qtd").value = 10;
    });
    document.getElementById("preset-res-conflito").addEventListener("click", () => {
      document.getElementById("res-usuario").value = "u1";
      document.getElementById("res-sala").value = "s2";
      document.getElementById("res-inicio").value = makeDateTime(10, 0);
      document.getElementById("res-fim").value = makeDateTime(12, 0);
      document.getElementById("res-qtd").value = 15;
    });
    document.getElementById("preset-res-restrito").addEventListener("click", () => {
      document.getElementById("res-usuario").value = "u2";
      document.getElementById("res-sala").value = "s3";
      document.getElementById("res-inicio").value = makeDateTime(10, 0);
      document.getElementById("res-fim").value = makeDateTime(12, 0);
      document.getElementById("res-qtd").value = 5;
    });

    document.getElementById("btn-executar-troca-rapida").addEventListener("click", () => {
      if (!pendingSwapContext) return;
      executarTroca(pendingSwapContext.antigaId, pendingSwapContext.payload, "reserva-feedback");
    });

    document.getElementById("form-troca").addEventListener("submit", (e) => {
      e.preventDefault();
      const antigaId = document.getElementById("troca-antiga-id").value.trim();
      const payload = {
        usuario_id: document.getElementById("troca-usuario").value.trim(),
        sala_id: document.getElementById("troca-sala").value,
        inicio: toApiIso(document.getElementById("troca-inicio").value),
        fim: toApiIso(document.getElementById("troca-fim").value),
        qtd_pessoas: Number(document.getElementById("troca-qtd").value),
      };
      executarTroca(antigaId, payload, "troca-feedback");
    });

    // Tab 3: Avaliar & Cancelar
    document.getElementById("btn-aprovar").addEventListener("click", () => {
      avaliarReserva(
        document.getElementById("aval-reserva-id").value.trim(),
        document.getElementById("aval-aprovador").value.trim(),
        true
      );
    });
    document.getElementById("btn-rejeitar").addEventListener("click", () => {
      avaliarReserva(
        document.getElementById("aval-reserva-id").value.trim(),
        document.getElementById("aval-aprovador").value.trim(),
        false
      );
    });
    document.getElementById("form-cancelar").addEventListener("submit", (e) => {
      e.preventDefault();
      cancelarReserva(
        document.getElementById("canc-reserva-id").value.trim(),
        document.getElementById("canc-usuario").value.trim()
      );
    });

    // Tab 4: Auditoria
    document.getElementById("form-auditoria").addEventListener("submit", (e) => {
      e.preventDefault();
      consultarAuditoria();
    });
    document.getElementById("btn-limpar-audit").addEventListener("click", () => {
      document.getElementById("audit-entidade").value = "";
      consultarAuditoria();
    });

    // Sidebar actions
    document.getElementById("btn-limpar-sessao").addEventListener("click", () => {
      sessionReservas = [];
      saveSessionReservas();
      renderSessionReservas();
    });

    document.getElementById("btn-copy-curl").addEventListener("click", async () => {
      if (!lastCurl) return;
      const btn = document.getElementById("btn-copy-curl");
      try {
        await navigator.clipboard.writeText(lastCurl);
        btn.textContent = "Copiado!";
        setTimeout(() => {
          btn.textContent = "Copiar curl";
        }, 1400);
      } catch {
        btn.textContent = "Erro";
      }
    });

    // Carrega salas iniciais automaticamente ao abrir a GUI
    consultarSalas();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
