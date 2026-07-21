/* NeuroOps Phase 3 frontend - vanilla JS + Three.js.
   Connects to Flask backend via REST + Socket.IO for real-time
   multi-agent workflow visualization with dynamic agent selection. */

const API = window.location.origin + "/api";
let socket = null;
let eventCount = 0;
let threeScene = null;
let registryData = [];

/* =========================================================== Helpers */
function el(id) { return document.getElementById(id); }
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}
async function api(path, opts = {}) {
  const r = await fetch(API + path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.status === 204 ? null : r.json();
}

/* =========================================================== Three.js viz */
const AGENT_VIZ = {};  // agent_type -> { mesh, angle, baseColor, deptColor }
const DEPT_COLORS = {
  engineering: 0x3b82f6, design: 0x8b5cf6, testing: 0xf59e0b,
  research: 0x06b6d4, management: 0x10b981, communication: 0xec4899, memory: 0x6366f1,
};
const STATE_COLORS = {
  sleeping: 0x2a3a5a, available: 0x4a6a9a, assigned: 0x6366f1,
  thinking: 0x06b6d4, working: 0xf59e0b, waiting: 0x8b5cf6,
  waiting_approval: 0x8b5cf6, completed: 0x10b981, failed: 0xef4444,
};
const STATE_EMISSIVE = {
  sleeping: 0x0a1020, available: 0x10204a, assigned: 0x202050,
  thinking: 0x044a5a, working: 0x5a3a04, waiting: 0x3a2055,
  waiting_approval: 0x3a2055, completed: 0x055a3a, failed: 0x5a1010,
};

function initThree() {
  const container = el("three-canvas");
  const w = container.clientWidth, h = container.clientHeight;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x050810);
  const camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 1000);
  camera.position.set(0, 2, 32);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0x404060, 1.5));
  const dl = new THREE.DirectionalLight(0x3b82f6, 1);
  dl.position.set(10, 10, 10);
  scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0x06b6d4, 0.5);
  dl2.position.set(-10, -5, 8);
  scene.add(dl2);

  // Central CEO node
  const ceoGeo = new THREE.SphereGeometry(3, 32, 32);
  const ceoMat = new THREE.MeshPhongMaterial({ color: 0x3b82f6, emissive: 0x1a3a8a, shininess: 80 });
  const ceoNode = new THREE.Mesh(ceoGeo, ceoMat);
  scene.add(ceoNode);

  // Ring around CEO
  const ringGeo = new THREE.RingGeometry(14, 14.3, 64);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0x1a2540, side: THREE.DoubleSide, transparent: true, opacity: 0.3 });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = Math.PI / 2;
  scene.add(ring);

  // Agent nodes (created dynamically when registry loads)
  threeScene = { scene, camera, renderer, ceoNode, ring, container, connections: [] };
  animateThree();
  window.addEventListener("resize", resizeThree);
}

function resizeThree() {
  if (!threeScene) return;
  const { container, camera, renderer } = threeScene;
  const w = container.clientWidth, h = container.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}

function createAgentNode(agentType, index, total, department) {
  if (!threeScene) return;
  const angle = (index / total) * Math.PI * 2;
  const radius = 14;
  const deptColor = DEPT_COLORS[department] || 0x4a5578;

  const geo = new THREE.SphereGeometry(1.4, 20, 20);
  const mat = new THREE.MeshPhongMaterial({ color: 0x2a3a5a, emissive: 0x0a1020, shininess: 40 });
  const node = new THREE.Mesh(geo, mat);
  node.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius * 0.5, 0);
  threeScene.scene.add(node);

  // Connection line CEO -> agent
  const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), node.position.clone()]);
  const lineMat = new THREE.LineBasicMaterial({ color: deptColor, transparent: true, opacity: 0.25 });
  const line = new THREE.Line(lineGeo, lineMat);
  threeScene.scene.add(line);

  AGENT_VIZ[agentType] = { mesh: node, angle, baseColor: deptColor, line, lineMat };
}

let frame = 0;
function animateThree() {
  requestAnimationFrame(animateThree);
  if (!threeScene) return;
  frame += 0.005;
  threeScene.ceoNode.rotation.y += 0.008;
  threeScene.ceoNode.scale.setScalar(1 + Math.sin(frame * 2) * 0.05);
  threeScene.ring.rotation.z += 0.002;

  Object.values(AGENT_VIZ).forEach((a, i) => {
    a.angle += 0.002;
    const radius = 14;
    a.mesh.position.x = Math.cos(a.angle) * radius;
    a.mesh.position.y = Math.sin(a.angle) * radius * 0.5;
    a.mesh.rotation.y += 0.01;
    // Update connection line
    if (a.line) {
      const positions = a.line.geometry.attributes.position;
      positions.setXYZ(1, a.mesh.position.x, a.mesh.position.y, a.mesh.position.z);
      positions.needsUpdate = true;
    }
  });

  threeScene.renderer.render(threeScene.scene, threeScene.camera);
}

function updateAgentViz(agentType, state) {
  const a = AGENT_VIZ[agentType];
  if (!a) return;
  const color = STATE_COLORS[state] || 0x2a3a5a;
  const emissive = STATE_EMISSIVE[state] || 0x0a1020;
  a.mesh.material.color.setHex(color);
  a.mesh.material.emissive.setHex(emissive);
  if (state === "working" || state === "thinking") {
    a.mesh.scale.setScalar(1.4 + Math.sin(frame * 4 + a.angle * 3) * 0.15);
    a.lineMat.opacity = 0.7;
  } else if (state === "completed") {
    a.mesh.scale.setScalar(1.1);
    a.lineMat.opacity = 0.4;
  } else if (state === "sleeping") {
    a.mesh.scale.setScalar(0.9);
    a.lineMat.opacity = 0.15;
  } else {
    a.mesh.scale.setScalar(1.0);
    a.lineMat.opacity = 0.3;
  }
}

/* =========================================================== Event log */
function logEvent(event) {
  const log = el("event-log");
  const time = new Date(event.timestamp).toLocaleTimeString();
  const line = document.createElement("div");
  line.className = "event-line";
  const srcClass = "event-src-" + (event.source || "").replace(/[^A-Za-z]/g, "");
  line.innerHTML = `<span class="event-time">${time}</span>` +
                   `<span class="event-type">${escapeHtml(event.event_type || "")}</span>` +
                   `<span class="event-src ${srcClass}">${escapeHtml(event.source || "")}</span>` +
                   `<span class="event-msg"></span>`;
  line.querySelector(".event-msg").textContent = event.message || "";
  log.prepend(line);
  eventCount++;
  el("stat-events").textContent = eventCount;
  while (log.children.length > 150) log.removeChild(log.lastChild);
}

/* =========================================================== Agent Registry */
function renderRegistry(registry, states) {
  registryData = registry;
  el("registry-count").textContent = registry.length + " agents";
  // Create viz nodes if not yet
  if (Object.keys(AGENT_VIZ).length === 0 && threeScene) {
    registry.forEach((agent, i) => {
      createAgentNode(agent.agent_type, i, registry.length, agent.department);
    });
  }
  const grid = el("agent-grid");
  grid.innerHTML = "";
  registry.forEach(agent => {
    const state = (states && states[agent.agent_type]) || "sleeping";
    const card = document.createElement("div");
    card.className = "agent-card" + (state !== "sleeping" ? " active" : "");
    card.id = `agent-card-${agent.agent_type}`;
    const perf = agent.success_rate !== undefined ? `${(agent.success_rate * 100).toFixed(0)}% success` : "";
    card.innerHTML = `<div class="name"><span class="dot dot-${state}" style="margin-right:6px"></span>${escapeHtml(agent.name)}</div>` +
                     `<div class="dept">${escapeHtml(agent.department)}</div>` +
                     `<div class="caps">${(agent.capabilities || []).slice(0, 3).join(", ")}</div>` +
                     (perf ? `<div class="perf">${perf}</div>` : "");
    grid.appendChild(card);
  });
}

function updateAgentCard(agentType, state) {
  const card = el(`agent-card-${agentType}`);
  if (!card) return;
  const dot = card.querySelector(".dot");
  if (dot) dot.className = `dot dot-${state}`;
  card.classList.toggle("active", state !== "sleeping");
}

/* =========================================================== Tasks */
function renderTasks(tasks) {
  const pipe = el("task-pipeline");
  if (!tasks.length) { pipe.innerHTML = '<p class="empty">Submit a request to see the task DAG.</p>'; return; }
  pipe.innerHTML = "";
  tasks.forEach(t => {
    const card = document.createElement("div");
    card.className = "task-card";
    card.id = `task-${t.task_id}`;
    const badgeClass = `tbadge-${t.status}`;
    card.innerHTML = `<span class="tid">${escapeHtml(t.task_id)}</span>` +
                     `<span class="ttitle">${escapeHtml(t.title)}</span>` +
                     `<span class="tag">${escapeHtml((t.required_skills || []).join(", "))}</span>` +
                     `<span class="task-badge ${badgeClass}">${t.status}</span>`;
    pipe.appendChild(card);
  });
  el("stat-tasks").textContent = tasks.length;
}

function updateTaskCard(taskId, status) {
  const card = el(`task-${taskId}`);
  if (!card) return;
  const badge = card.querySelector(".task-badge");
  if (badge) { badge.className = `task-badge tbadge-${status}`; badge.textContent = status; }
}

/* =========================================================== Memory */
function renderMemory(entries) {
  const tl = el("memory-timeline");
  el("memory-count").textContent = entries.length + " entries";
  el("stat-memory").textContent = entries.length;
  if (!entries.length) { tl.innerHTML = '<p class="empty">No memory stored yet.</p>'; return; }
  tl.innerHTML = "";
  entries.slice(-20).reverse().forEach(m => {
    const row = document.createElement("div");
    row.className = "memory-entry";
    row.innerHTML = `<span class="mtype mtype-${m.memory_type}">${m.memory_type}</span>` +
                    `<span class="mcontent">${escapeHtml(m.content.slice(0, 100))}</span>` +
                    `<span class="mtime">${new Date(m.timestamp).toLocaleTimeString()}</span>`;
    tl.appendChild(row);
  });
}

/* =========================================================== Performance */
function renderPerformance(data) {
  const dash = el("performance-dashboard");
  const sys = data.system || {};
  el("stat-success").textContent = sys.system_success_rate !== undefined ? (sys.system_success_rate * 100).toFixed(0) + "%" : "-";
  el("stat-confidence").textContent = sys.system_avg_confidence !== undefined ? sys.system_avg_confidence.toFixed(2) : "-";

  const agents = data.agents || {};
  const entries = Object.entries(agents);
  if (!entries.length) { dash.innerHTML = '<p class="empty">No performance data yet.</p>'; return; }
  dash.innerHTML = "";
  entries.forEach(([aid, p]) => {
    const row = document.createElement("div");
    row.className = "perf-row";
    const pct = (p.success_rate || 0) * 100;
    const color = pct >= 80 ? "var(--success)" : pct >= 50 ? "var(--warning)" : "var(--error)";
    row.innerHTML = `<span class="pagent">${escapeHtml(aid.split("-")[0])}</span>` +
                    `<div class="pbar"><div class="pfill" style="width:${pct}%;background:${color}"></div></div>` +
                    `<span class="pstats">${p.tasks_completed} done, ${(p.avg_confidence || 0).toFixed(2)} conf</span>`;
    dash.appendChild(row);
  });
}

/* =========================================================== Approvals */
function renderApprovals(approvals) {
  const section = el("approval-section");
  const queue = el("approval-queue");
  if (!approvals.length) { section.style.display = "none"; return; }
  section.style.display = "";
  queue.innerHTML = "";
  approvals.forEach(a => {
    const card = document.createElement("div");
    card.className = "approval-card";
    card.innerHTML = `<div class="arow"><span class="atitle">Task: ${escapeHtml(a.task_id)}</span></div>` +
                     `<div class="arow"><span class="areason">${escapeHtml(a.reason)}</span></div>` +
                     `<div class="arow"><span>Confidence: ${a.confidence.toFixed(2)}</span></div>` +
                     `<div class="abtns">` +
                     `<button class="btn btn-success btn-sm" onclick="resolveApproval('${a.approval_id}','approved')">Approve</button>` +
                     `<button class="btn btn-danger btn-sm" onclick="resolveApproval('${a.approval_id}','rejected')">Reject</button>` +
                     `<button class="btn btn-sm" onclick="resolveApproval('${a.approval_id}','modification')">Modify</button>` +
                     `</div>`;
    queue.appendChild(card);
  });
}

window.resolveApproval = async function(id, decision) {
  try {
    await api(`/approvals/${id}/resolve`, { method: "POST", body: JSON.stringify({ decision }) });
    refreshApprovals();
  } catch (e) { console.error(e); }
};

/* =========================================================== Report */
function renderReport(markdown) {
  el("report-status").textContent = "Complete";
  el("report-status").style.color = "var(--success)";
  el("final-report").innerHTML = renderMarkdown(markdown);
}

function renderMarkdown(md) {
  let html = escapeHtml(md);
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/^\- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, m => '<ul>' + m + '</ul>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\n\n/g, '<br><br>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

/* =========================================================== Socket.IO */
function connectSocket() {
  socket = io({ transports: ["websocket", "polling"] });
  socket.on("connect", () => {
    el("ws-status").className = "pill pill-online";
    el("ws-status").textContent = "Socket: Connected";
  });
  socket.on("disconnect", () => {
    el("ws-status").className = "pill pill-offline";
    el("ws-status").textContent = "Socket: Disconnected";
  });
  socket.on("neuroops:event", (event) => {
    logEvent(event);
    handleEvent(event);
  });
}

function handleEvent(event) {
  const d = event.data || {};
  if (event.event_type && event.event_type.startsWith("agent:")) {
    if (d.agent_type && d.new_state) {
      updateAgentCard(d.agent_type, d.new_state);
      updateAgentViz(d.agent_type, d.new_state);
    }
  }
  if (event.event_type === "agent:selected" && d.agent_type) {
    updateAgentCard(d.agent_type, "assigned");
    updateAgentViz(d.agent_type, "assigned");
  }
  if (event.event_type === "agent:registered" && registryData.length) {
    api("/workflow/agents").then(data => renderRegistry(data.registry, data.states)).catch(() => {});
  }
  if (event.event_type === "task:created") { api("/workflow/tasks").then(renderTasks).catch(() => {}); }
  if (event.event_type === "task:finished" && d.task_id) { updateTaskCard(d.task_id, "completed"); }
  if (event.event_type === "task:failed" && d.task_id) { updateTaskCard(d.task_id, "failed"); }
  if (event.event_type === "human:approval_required") { refreshApprovals(); }
  if (event.event_type === "memory:accessed") { refreshMemory(); }
  if (event.event_type === "workflow:completed" || event.event_type === "workflow:failed") {
    refreshAll();
  }
}

/* =========================================================== Refresh */
async function refreshAll() {
  await Promise.all([refreshStats(), refreshTasks(), refreshAgents(), refreshMemory(), refreshAnalytics(), refreshApprovals()]);
}

async function refreshStats() {
  try {
    const session = await api("/workflow/session");
    el("stat-tasks").textContent = session.session.task_count;
    el("stat-events").textContent = session.session.event_count || eventCount;
    const ws = session.session.workflow_status;
    const pill = el("workflow-status");
    pill.className = "pill pill-" + ws;
    pill.textContent = "Workflow: " + ws.charAt(0).toUpperCase() + ws.slice(1);
    if (session.session.final_response) renderReport(session.session.final_response);
  } catch (e) { /* ignore */ }
}

async function refreshTasks() {
  try { renderTasks(await api("/workflow/tasks")); } catch (e) {}
}

async function refreshAgents() {
  try {
    const data = await api("/workflow/agents");
    renderRegistry(data.registry, data.states);
    el("stat-agents").textContent = Object.values(data.states).filter(s => s !== "sleeping").length;
  } catch (e) {}
}

async function refreshMemory() {
  try { renderMemory(await api("/memory")); } catch (e) {}
}

async function refreshAnalytics() {
  try { renderPerformance(await api("/analytics")); } catch (e) {}
}

async function refreshApprovals() {
  try { renderApprovals(await api("/approvals")); } catch (e) {}
}

/* =========================================================== Actions */
el("request-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = el("request-input");
  const req = input.value.trim();
  if (!req) return;
  el("submit-btn").disabled = true;
  el("submit-btn").textContent = "Running...";
  el("report-status").textContent = "Running";
  el("report-status").style.color = "var(--warning)";
  el("final-report").innerHTML = '<p class="empty">Workflow in progress... watch the event stream.</p>';
  try {
    await api("/workflow/submit", { method: "POST", body: JSON.stringify({ request: req }) });
    input.value = "";
  } catch (err) {
    logEvent({ timestamp: new Date().toISOString(), event_type: "error", source: "API", message: "Submit failed: " + err.message });
  } finally {
    setTimeout(() => {
      el("submit-btn").disabled = false;
      el("submit-btn").textContent = "Deploy Workforce";
    }, 2000);
  }
});

el("reset-btn").addEventListener("click", async () => {
  try {
    await api("/workflow/reset", { method: "POST" });
    el("event-log").innerHTML = "";
    el("final-report").innerHTML = '<p class="empty">Session reset. Submit a new request.</p>';
    el("report-status").textContent = "Awaiting workflow";
    el("report-status").style.color = "var(--text-dim)";
    eventCount = 0;
    el("stat-events").textContent = "0";
    refreshAll();
  } catch (e) {}
});

el("btn-clear-log").addEventListener("click", () => {
  el("event-log").innerHTML = "";
  eventCount = 0;
  el("stat-events").textContent = "0";
});

/* =========================================================== Clock */
function tickClock() { el("clock").textContent = new Date().toISOString().slice(11, 19) + " UTC"; }

/* =========================================================== Boot */
window.addEventListener("DOMContentLoaded", () => {
  initThree();
  connectSocket();
  refreshAll();
  setInterval(refreshAll, 5000);
  setInterval(tickClock, 1000);
  tickClock();
});
