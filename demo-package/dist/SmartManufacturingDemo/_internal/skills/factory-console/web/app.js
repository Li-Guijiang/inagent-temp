/* 工厂操作工控制台 - 前端逻辑（四大 Agent + 能耗看板，纯业务视图） */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function clock() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  $("#clock").textContent =
    `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
setInterval(clock, 1000); clock();

$$(".entry").forEach((btn) => {
  btn.addEventListener("click", () => showView(btn.dataset.view));
});
$$(".back").forEach((btn) => {
  btn.addEventListener("click", () => showView("home"));
});

function showView(name) {
  $$(".view").forEach((v) => v.classList.remove("active"));
  $("#view-" + name).classList.add("active");
  window.scrollTo(0, 0);
  if (name === "alerts") loadAlerts();
  if (name === "quality") loadQuality();
  if (name === "energy") loadEnergy();
}

/* 主页待办 */
async function loadHomeTodo() {
  try {
    const a = await fetch("/api/alerts").then((r) => r.json());
    const todo = [];
    if (a.ok && (a.summary["严重"] + a.summary["紧急"] > 0))
      todo.push(`${a.summary["严重"]+a.summary["紧急"]} 条设备严重/紧急告警`);
    $("#home-todo").textContent = todo.length ? "请优先处理：" + todo.join("、") : "暂无紧急事项 ✅";
  } catch (e) {
    $("#home-todo").textContent = "服务未连接";
  }
}

/* ===== A4 设备告警 ===== */
async function loadAlerts() {
  const box = $("#alerts-list");
  $("#alerts-list").innerHTML = '<div class="ok-strip">加载中…</div>';
  const r = await fetch("/api/alerts").then((r) => r.json());
  if (!r.ok) { box.innerHTML = `<div class="ok-strip">${r.msg}</div>`; return; }
  $("#alerts-updated").textContent = "更新于 " + (r.updated_at || "-");
  const s = r.summary || {};
  $("#alerts-summary").innerHTML = `
    <div class="sum-card ok"><div class="num">${r.normal_count}</div><div class="label">运行正常（共${r.total}台）</div></div>
    <div class="sum-card warn"><div class="num">${s["预警"]||0}</div><div class="label">预警</div></div>
    <div class="sum-card warn"><div class="num">${s["严重"]||0}</div><div class="label">严重</div></div>
    <div class="sum-card bad"><div class="num">${s["紧急"]||0}</div><div class="label">紧急</div></div>`;
  if (!r.alerts.length) {
    box.innerHTML = '<div class="ok-strip">🎉 全部设备运行正常，无需处理</div>';
    return;
  }
  box.innerHTML = r.alerts.map((a) => `
    <div class="alert-item ${a.status}">
      <span class="lvl">${a.status}</span>
      <div class="body">
        <div class="dev">${a.device_name}（${a.device_id}）</div>
        <div class="param">${a.param} = ${a.value}${a.unit}　正常范围：${a.normal_range}</div>
        <div class="hint">${a.action_hint || ""}</div>
      </div>
    </div>`).join("");
}

/* ===== A1 质检上报 ===== */
async function loadQuality() {
  const r = await fetch("/api/quality").then((r) => r.json());
  if (!r.ok) { $("#quality-updated").textContent = r.msg; return; }
  $("#quality-updated").textContent = "更新于 " + (r.updated_at || "-");
  const s = r.summary || {};
  $("#quality-summary").innerHTML = `
    <div class="sum-card ok"><div class="num">${s["正常"]||0}</div><div class="label">正常巡检项</div></div>
    <div class="sum-card warn"><div class="num">${s["预警"]||0}</div><div class="label">预警</div></div>
    <div class="sum-card warn"><div class="num">${s["严重"]||0}</div><div class="label">严重</div></div>
    <div class="sum-card bad"><div class="num">${s["紧急"]||0}</div><div class="label">紧急</div></div>`;
  $("#report-count").textContent = r.submitted_today || 0;
  renderReports(r.recent_reports || []);
}

function renderReports(list) {
  const box = $("#recent-reports");
  if (!list.length) { box.innerHTML = '<div class="ok-strip">今日暂未有上报记录</div>'; return; }
  box.innerHTML = list.map((r) => `
    <div class="report-row">
      <span>${r.time}｜${r.line}｜批次 ${r.batch}</span>
      <span class="res ${r.result}">${r.result}</span>
    </div>`).join("");
}

$("#quality-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const msg = $("#form-msg");
  const body = Object.fromEntries(new FormData(form).entries());
  const r = await fetch("/api/quality/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => r.json());
  if (r.ok) {
    msg.className = "form-msg ok";
    msg.textContent = "✅ 上报成功";
    form.reset();
    loadQuality();
  } else {
    msg.className = "form-msg err";
    msg.textContent = r.msg || "上报失败，请重试";
  }
});

/* ===== A2 工艺解析 ===== */
const SAMPLE_DOC = `# 电池箱体弧焊工艺参数卡（示例）
焊接电流：180 A
焊接电压：24 V
焊接速度：12 mm/s
保护气流量：15 L/min
送丝速度：8 m/min
焊枪倾角：75 度
预热温度：80 ℃
电流范围 170~190，电压范围 22~26`;

$("#process-example").addEventListener("click", () => {
  $("#process-doc").value = SAMPLE_DOC;
  $("#process-msg").textContent = "示例文档已载入，点击开始解析";
  $("#process-msg").className = "form-msg";
});

$("#process-parse").addEventListener("click", async () => {
  const msg = $("#process-msg");
  const doc = $("#process-doc").value.trim();
  if (!doc) { msg.className = "form-msg err"; msg.textContent = "请先粘贴或上传工艺文档"; return; }
  msg.className = "form-msg"; msg.textContent = "解析中…";
  const r = await fetch("/api/agent/parse-process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_text: doc }),
  }).then((r) => r.json());
  if (!r.ok) {
    msg.className = "form-msg err"; msg.textContent = r.msg; return;
  }
  msg.className = "form-msg ok";
  msg.textContent = `✅ 已识别 ${r.param_count} 项工艺参数（来源：${r.source}，行数 ${r.lines}）`;
  $("#process-updated").textContent = "分析时间 " + r.analyzed_at;
  const box = $("#process-result");
  box.innerHTML = r.params.map((p) => `
    <div class="param-card">
      <div class="p-name">${p.name}</div>
      <div class="p-val">${p.value} <span>${p.unit}</span></div>
      ${p.range ? `<div class="p-range">建议区间 ${p.range}</div>` : ""}
    </div>`).join("");
});

/* ===== A3 生产报表 ===== */
$("#report-gen").addEventListener("click", async () => {
  const msg = $("#report-msg");
  msg.className = "form-msg"; msg.textContent = "生成中…";
  const r = await fetch("/api/agent/report").then((r) => r.json());
  if (!r.ok) {
    msg.className = "form-msg err"; msg.textContent = r.msg; return;
  }
  msg.className = "form-msg ok";
  msg.textContent = `✅ 报表已生成（${r.generated_at}）`;
  $("#report-updated").textContent = r.generated_at;
  const s = r.summary || {};
  const detail = $("#report-detail");
  let rowsHtml = r.rows.map((row) => `
    <tr class="${row.severe + row.critical > 0 ? "row-bad" : row.warning > 0 ? "row-warn" : ""}">
      <td>${row.pack}</td>
      <td>${row.normal}</td>
      <td>${row.warning}</td>
      <td>${row.severe}</td>
      <td>${row.critical}</td>
      <td>${row.alerts}</td>
      <td>${row.updated}</td>
    </tr>`).join("");
  detail.innerHTML = `
    <div class="sumline" style="margin-bottom:12px">
      <div class="sum-card ok"><div class="num">${s.total_normal}</div><div class="label">全部正常项</div></div>
      <div class="sum-card warn"><div class="num">${s.total_alerts}</div><div class="label">累计告警</div></div>
      <div class="sum-card bad"><div class="num">${s.severe_or_critical}</div><div class="label">含严重/紧急模块</div></div>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>模块</th><th>正常</th><th>预警</th><th>严重</th><th>紧急</th><th>告警数</th><th>更新时间</th></tr></thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    </div>
    ${r.excel_url ? `<div class="dl-link"><a href="${r.excel_url}" target="_blank">⬇ 下载 Excel 报表</a></div>` : ""}`;
});

/* ===== 能耗看板 ===== */
async function loadEnergy() {
  const box = $("#energy-list");
  $("#energy-list").innerHTML = '<div class="ok-strip">加载中…</div>';
  const r = await fetch("/api/energy").then((r) => r.json());
  if (!r.ok) { box.innerHTML = `<div class="ok-strip">${r.msg}</div>`; return; }
  $("#energy-updated").textContent = "更新于 " + (r.updated_at || "-");
  const s = r.summary || {};
  $("#energy-summary").innerHTML = `
    <div class="sum-card ok"><div class="num">${s["正常"]||0}</div><div class="label">正常能耗单元</div></div>
    <div class="sum-card warn"><div class="num">${s["预警"]||0}</div><div class="label">预警</div></div>
    <div class="sum-card warn"><div class="num">${s["严重"]||0}</div><div class="label">严重</div></div>
    <div class="sum-card bad"><div class="num">${s["紧急"]||0}</div><div class="label">紧急</div></div>`;
  box.innerHTML = r.devices.map((d) => {
    const worst = d.status === "正常" ? "" : d.status;
    return `
    <div class="energy-item ${worst}">
      <div class="dev">${d.device_name}</div>
      <div class="val">${worst || "正常 ✅"}</div>
      <div class="meta">${d.worst_param || "全部指标正常"}　|　${d.device_id}</div>
    </div>`;
  }).join("");
}

/* 初始化 */
loadHomeTodo();