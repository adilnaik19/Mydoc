/* ============================================================
   My Doc+ — single-page app (vanilla JS, zero dependencies)
   ============================================================ */

const API = "/api";
const store = {
  get token() { return localStorage.getItem("mdp_token"); },
  set token(v) { v ? localStorage.setItem("mdp_token", v) : localStorage.removeItem("mdp_token"); },
  get user() { try { return JSON.parse(localStorage.getItem("mdp_user")); } catch { return null; } },
  set user(v) { v ? localStorage.setItem("mdp_user", JSON.stringify(v)) : localStorage.removeItem("mdp_user"); },
};

/* ----------------------- helpers ----------------------- */
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const initials = (name) => (name || "?").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
const money = (n) => "₹" + Number(n || 0).toLocaleString("en-IN");
const stars = (r) => "★".repeat(Math.round(r)) + "☆".repeat(5 - Math.round(r));

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && store.token) headers.Authorization = "Bearer " + store.token;
  const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let data = null;
  try { data = await res.json(); } catch { /* no body */ }
  if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status})`);
  return data;
}

let toastTimer;
function toast(msg, kind = "") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast show " + kind;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.className = "toast " + kind), 2600);
}

function modal(html) {
  const root = $("#modalRoot");
  root.innerHTML = `<div class="modal-backdrop" id="mb"><div class="modal">${html}</div></div>`;
  $("#mb").addEventListener("click", (e) => { if (e.target.id === "mb") closeModal(); });
}
function closeModal() { $("#modalRoot").innerHTML = ""; }

/* pseudo-QR: deterministic decorative grid from the booking code */
function qr(code) {
  let h = 2166136261;
  for (const ch of code) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  let cells = "";
  for (let i = 0; i < 441; i++) {
    h ^= h << 13; h ^= h >>> 17; h ^= h << 5; h >>>= 0;
    const r = Math.floor(i / 21), c = i % 21;
    const finder = (r < 7 && c < 7) || (r < 7 && c > 13) || (r > 13 && c < 7);
    const on = finder ? ((r + c) % 2 === 0 || r === 0 || c === 0) : (h % 100 < 46);
    cells += `<span class="${on ? "on" : ""}"></span>`;
  }
  return `<div class="qr">${cells}</div>`;
}

const CATEGORIES = [
  ["Cardiology", "❤️", 1], ["Dermatology", "🧴", 2], ["Pediatrics", "🧒", 3],
  ["Orthopedics", "🦴", 4], ["Neurology", "🧠", 5], ["General", "🩺", 6],
  ["Gynecology", "🌸", 7], ["Dentistry", "🦷", 8],
];

/* ----------------------- theme ----------------------- */
function initTheme() {
  const saved = localStorage.getItem("mdp_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  $("#themeToggle").textContent = saved === "dark" ? "☀️" : "🌙";
}
$("#themeToggle").addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("mdp_theme", next);
  $("#themeToggle").textContent = next === "dark" ? "☀️" : "🌙";
});

/* ----------------------- auth/session ----------------------- */
function setSession(data) { store.token = data.token; store.user = data.user; renderChrome(); }
function logout() { store.token = null; store.user = null; renderChrome(); location.hash = "#/"; toast("Signed out"); }

function renderChrome() {
  const user = store.user;
  const nav = $("#nav");
  const links = [["#/", "Home"], ["#/search", "Find Doctors"]];
  if (user) {
    if (user.role === "patient") links.push(["#/appointments", "My Appointments"]);
    if (user.role === "doctor") links.push(["#/doctor-panel", "Doctor Panel"]);
    if (user.role === "admin") links.push(["#/admin", "Admin"]);
  }
  const hash = location.hash || "#/";
  nav.innerHTML = links.map(([h, l]) =>
    `<a href="${h}" data-link class="${h === hash ? "active" : ""}">${l}</a>`).join("");

  const authArea = $("#authArea");
  if (user) {
    authArea.innerHTML = `<div class="avatar" id="avatarBtn" title="${esc(user.name)}">${initials(user.name)}</div>`;
    $("#avatarBtn").onclick = () => {
      const items = [["Profile", "#/profile"]];
      if (user.role === "patient") items.push(["My Appointments", "#/appointments"]);
      modal(`<h3>${esc(user.name)}</h3>
        <p class="muted" style="margin-top:-6px">${esc(user.email)} · <span class="badge">${user.role}</span></p>
        <div class="grid mt">
          ${items.map(([l, h]) => `<button class="btn secondary" onclick="location.hash='${h}';closeModal()">${l}</button>`).join("")}
          <button class="btn danger" onclick="logout();closeModal()">Sign out</button>
        </div>`);
    };
  } else {
    authArea.innerHTML = `<a href="#/login" data-link class="btn sm">Sign in</a>`;
  }
}

/* ----------------------- router ----------------------- */
const routes = {};
function route(path, handler) { routes[path] = handler; }

function parseHash() {
  const raw = (location.hash || "#/").slice(1);
  const [path, queryStr] = raw.split("?");
  const query = Object.fromEntries(new URLSearchParams(queryStr || ""));
  return { path, query };
}

async function router() {
  renderChrome();
  const { path, query } = parseHash();
  const app = $("#app");
  window.scrollTo(0, 0);

  // dynamic segment matching: /doctor/:id
  for (const pattern in routes) {
    const names = [];
    const rx = new RegExp("^" + pattern.replace(/:(\w+)/g, (_, n) => { names.push(n); return "([^/]+)"; }) + "$");
    const m = path.match(rx);
    if (m) {
      const params = {}; names.forEach((n, i) => (params[n] = decodeURIComponent(m[i + 1])));
      try { await routes[pattern](app, params, query); }
      catch (e) { app.innerHTML = errorState(e.message); }
      return;
    }
  }
  app.innerHTML = errorState("Page not found");
}

function errorState(msg) {
  return `<div class="empty"><div class="emoji">😕</div><h3>${esc(msg)}</h3>
    <a class="btn mt" href="#/">Go home</a></div>`;
}
function requireAuth(role) {
  const u = store.user;
  if (!u || (role && u.role !== role)) { location.hash = "#/login"; return false; }
  return true;
}

/* ----------------------- views ----------------------- */
function skeletons(n = 4) {
  return `<div class="grid doc-grid">${Array(n).fill('<div class="card sk-card skeleton"></div>').join("")}</div>`;
}

function doctorCard(d) {
  const badges = [];
  if (d.video_consult) badges.push('<span class="badge">📹 Video</span>');
  if (d.home_visit) badges.push('<span class="badge">🏠 Home</span>');
  return `<div class="card hover doc-card" onclick="location.hash='#/doctor/${d.id}'" style="cursor:pointer">
    <div class="doc-photo">${initials(d.name)}</div>
    <div class="doc-main">
      <div class="doc-name">${esc(d.name)}</div>
      <div class="doc-spec">${esc(d.specialty || "General")}</div>
      <div class="doc-meta">${d.experience_years} yrs exp · ${esc(d.hospital || "")}, ${esc(d.city || "")}</div>
      <div class="doc-meta"><span class="stars">${stars(d.rating)}</span> ${d.rating} (${d.reviews_count}) · <strong>${money(d.consultation_fee)}</strong></div>
      <div class="row mt" style="gap:6px">${badges.join("")}</div>
    </div>
  </div>`;
}

/* Home */
route("/", async (app) => {
  app.innerHTML = `
    <section class="hero">
      <h1>Your health, one tap away 🩺</h1>
      <p>Search trusted doctors, book instantly, consult by video or in clinic.</p>
      <div class="searchbar">
        <span>🔍</span>
        <input id="heroSearch" placeholder="Search doctors, specialties, hospitals..." />
        <button class="btn" id="heroGo">Search</button>
      </div>
    </section>

    <div class="section-title"><span>Browse by specialty</span></div>
    <div class="cat-grid">
      ${CATEGORIES.map(([label, emoji, id]) =>
        `<div class="cat" onclick="location.hash='#/search?specialty=${id}'">
           <div class="emoji">${emoji}</div><div class="label">${label}</div></div>`).join("")}
    </div>

    <div class="section-title"><span>Top rated doctors</span><a href="#/search">See all →</a></div>
    <div id="topDoctors">${skeletons()}</div>

    <div class="section-title"><span>Health tips</span></div>
    <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(240px,1fr))">
      ${["Stay hydrated — 8 glasses a day keeps you sharp.",
         "30 min of daily walking cuts heart-disease risk.",
         "7–8 hours of sleep boosts immunity."].map(t =>
        `<div class="card">💡 ${t}</div>`).join("")}
    </div>`;

  const go = () => { const q = $("#heroSearch").value.trim(); location.hash = "#/search" + (q ? "?q=" + encodeURIComponent(q) : ""); };
  $("#heroGo").onclick = go;
  $("#heroSearch").addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });

  const docs = await api("/doctors?sort=rating", { auth: false });
  $("#topDoctors").innerHTML = `<div class="grid doc-grid">${docs.slice(0, 6).map(doctorCard).join("")}</div>`;
});

/* Search */
route("/search", async (app, _p, query) => {
  const state = { ...query };
  app.innerHTML = `
    <div class="searchbar">
      <span>🔍</span>
      <input id="q" placeholder="Search doctors, hospitals..." value="${esc(state.q || "")}" />
      <button class="btn" id="goBtn">Search</button>
    </div>
    <div class="chips mt">
      <span class="chip" data-f="video">📹 Video</span>
      <span class="chip" data-f="home">🏠 Home visit</span>
      <select class="chip" id="sort" style="cursor:pointer">
        <option value="rating">Top rated</option>
        <option value="fee">Lowest fee</option>
        <option value="experience">Most experienced</option>
      </select>
      <select class="chip" id="maxFee" style="cursor:pointer">
        <option value="">Any fee</option>
        <option value="400">≤ ₹400</option>
        <option value="600">≤ ₹600</option>
        <option value="800">≤ ₹800</option>
      </select>
    </div>
    <div class="section-title"><span id="resCount">Doctors</span></div>
    <div id="results">${skeletons(6)}</div>`;

  const chips = app.querySelectorAll(".chip[data-f]");
  chips.forEach(ch => {
    if (state[ch.dataset.f]) ch.classList.add("active");
    ch.onclick = () => { ch.classList.toggle("active"); load(); };
  });
  if (state.sort) $("#sort").value = state.sort;
  if (state.max_fee) $("#maxFee").value = state.max_fee;
  $("#sort").onchange = load;
  $("#maxFee").onchange = load;
  $("#goBtn").onclick = load;
  $("#q").addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });

  async function load() {
    const params = new URLSearchParams();
    const q = $("#q").value.trim(); if (q) params.set("q", q);
    if (state.specialty) params.set("specialty", state.specialty);
    app.querySelectorAll(".chip[data-f].active").forEach(ch => params.set(ch.dataset.f, "1"));
    const mf = $("#maxFee").value; if (mf) params.set("max_fee", mf);
    params.set("sort", $("#sort").value);
    $("#results").innerHTML = skeletons(6);
    const docs = await api("/doctors?" + params.toString(), { auth: false });
    $("#resCount").textContent = `${docs.length} doctor${docs.length === 1 ? "" : "s"} found`;
    $("#results").innerHTML = docs.length
      ? `<div class="grid doc-grid">${docs.map(doctorCard).join("")}</div>`
      : `<div class="empty"><div class="emoji">🔍</div><p>No doctors match your filters.</p></div>`;
  }
  load();
});

/* Doctor profile */
route("/doctor/:id", async (app, params) => {
  app.innerHTML = skeletons(1);
  const d = await api("/doctors/" + params.id, { auth: false });
  const badges = [];
  if (d.video_consult) badges.push('<span class="badge">📹 Video consult</span>');
  if (d.home_visit) badges.push('<span class="badge">🏠 Home visit</span>');
  app.innerHTML = `
    <a href="#/search" class="btn ghost sm">← Back</a>
    <div class="card mt doc-card" style="align-items:center">
      <div class="doc-photo" style="width:80px;height:80px;font-size:28px">${initials(d.name)}</div>
      <div class="doc-main">
        <div class="doc-name" style="font-size:22px">${esc(d.name)}</div>
        <div class="doc-spec">${esc(d.specialty || "General")} · ${esc(d.qualification || "")}</div>
        <div class="doc-meta">${d.experience_years} yrs exp · ${esc(d.hospital || "")}, ${esc(d.city || "")}</div>
        <div class="doc-meta"><span class="stars">${stars(d.rating)}</span> ${d.rating} (${d.reviews_count} reviews)</div>
        <div class="row mt" style="gap:6px">${badges.join("")}</div>
      </div>
      <div class="center">
        <div class="muted" style="font-size:13px">Consultation</div>
        <div style="font-size:24px;font-weight:800">${money(d.consultation_fee)}</div>
        <button class="btn mt" onclick="location.hash='#/book/${d.id}'">Book Appointment</button>
      </div>
    </div>
    <div class="grid mt" style="grid-template-columns:1.4fr 1fr">
      <div class="card">
        <h3>About</h3><p class="muted">${esc(d.about || "—")}</p>
        <h3 class="mt">Languages</h3>
        <div class="chips">${(d.languages || []).map(l => `<span class="chip">${esc(l)}</span>`).join("") || "—"}</div>
      </div>
      <div class="card">
        <h3>Reviews</h3>
        ${(d.reviews && d.reviews.length) ? d.reviews.map(r => `
          <div style="border-bottom:1px solid var(--border);padding:8px 0">
            <div class="between"><strong>${esc(r.patient)}</strong><span class="stars">${stars(r.rating)}</span></div>
            <div class="muted" style="font-size:13px">${esc(r.comment || "")}</div>
          </div>`).join("") : '<p class="muted">No reviews yet.</p>'}
      </div>
    </div>`;
});

/* Booking */
route("/book/:id", async (app, params) => {
  if (!requireAuth("patient")) { toast("Please sign in as a patient to book"); return; }
  app.innerHTML = skeletons(1);
  const d = await api("/doctors/" + params.id, { auth: false });
  const today = new Date();
  const dates = Array.from({ length: 7 }, (_, i) => {
    const dt = new Date(today); dt.setDate(today.getDate() + i);
    return dt.toISOString().slice(0, 10);
  });
  const types = [["video", "📹 Video", d.video_consult], ["clinic", "🏥 In-clinic", true], ["home", "🏠 Home", d.home_visit]]
    .filter(t => t[2]);
  const sel = { date: dates[0], slot: null, type: types[0][0] };

  app.innerHTML = `
    <a href="#/doctor/${d.id}" class="btn ghost sm">← Back</a>
    <h2>Book with ${esc(d.name)}</h2>
    <div class="grid" style="grid-template-columns:1.4fr 1fr">
      <div class="card">
        <div class="field"><label>Consultation type</label>
          <div class="chips" id="typeChips">
            ${types.map((t, i) => `<span class="chip ${i === 0 ? "active" : ""}" data-t="${t[0]}">${t[1]}</span>`).join("")}
          </div></div>
        <div class="field"><label>Select date</label>
          <div class="chips" id="dateChips">
            ${dates.map((dt, i) => `<span class="chip ${i === 0 ? "active" : ""}" data-d="${dt}">${new Date(dt).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}</span>`).join("")}
          </div></div>
        <div class="field"><label>Available slots</label><div id="slots" class="slot-grid">${skeletons(1)}</div></div>
        <div class="field"><label>Symptoms (optional)</label>
          <textarea id="symptoms" rows="3" placeholder="Describe your symptoms..."></textarea></div>
      </div>
      <div class="card" style="align-self:start">
        <h3>Summary</h3>
        <div class="between"><span class="muted">Doctor</span><strong>${esc(d.name)}</strong></div>
        <div class="between mt"><span class="muted">Fee</span><strong>${money(d.consultation_fee)}</strong></div>
        <div class="between mt"><span class="muted">When</span><strong id="sumWhen">—</strong></div>
        <div class="field mt"><label>Payment method</label>
          <select id="pay"><option>UPI</option><option>Credit / Debit Card</option><option>Net Banking</option><option>Wallet</option><option>Cash at clinic</option></select></div>
        <button class="btn block mt" id="confirmBtn" disabled>Confirm booking</button>
      </div>
    </div>`;

  const updWhen = () => $("#sumWhen").textContent = sel.slot ? `${sel.date} @ ${sel.slot}` : "—";
  $("#typeChips").querySelectorAll(".chip").forEach(c => c.onclick = () => {
    $("#typeChips").querySelectorAll(".chip").forEach(x => x.classList.remove("active"));
    c.classList.add("active"); sel.type = c.dataset.t;
  });
  $("#dateChips").querySelectorAll(".chip").forEach(c => c.onclick = () => {
    $("#dateChips").querySelectorAll(".chip").forEach(x => x.classList.remove("active"));
    c.classList.add("active"); sel.date = c.dataset.d; sel.slot = null; updWhen(); loadSlots();
  });

  async function loadSlots() {
    $("#slots").innerHTML = skeletons(1);
    const res = await api(`/doctors/${d.id}/slots?date=${sel.date}`, { auth: false });
    if (!res.slots.length) { $("#slots").innerHTML = '<p class="muted">No slots this day.</p>'; return; }
    $("#slots").innerHTML = res.slots.map(s => `<div class="slot" data-s="${s}">${s}</div>`).join("");
    $("#slots").querySelectorAll(".slot").forEach(sl => sl.onclick = () => {
      $("#slots").querySelectorAll(".slot").forEach(x => x.classList.remove("active"));
      sl.classList.add("active"); sel.slot = sl.dataset.s; updWhen();
      $("#confirmBtn").disabled = false;
    });
  }
  loadSlots();

  $("#confirmBtn").onclick = async () => {
    $("#confirmBtn").disabled = true;
    try {
      const appt = await api("/appointments", { method: "POST", body: {
        doctor_id: d.id, date: sel.date, slot: sel.slot, type: sel.type, symptoms: $("#symptoms").value.trim() } });
      showConfirmation(appt);
    } catch (e) { toast(e.message, "error"); $("#confirmBtn").disabled = false; }
  };
});

function showConfirmation(appt) {
  modal(`<div class="center">
    <div style="font-size:40px">✅</div>
    <h3>Appointment confirmed</h3>
    <p class="muted" style="margin-top:-8px">${esc(appt.doctor.name)} · ${appt.date} @ ${appt.slot}</p>
    ${qr(appt.code)}
    <div class="badge" style="font-size:14px">${appt.code}</div>
    <div class="grid mt">
      <button class="btn" onclick="location.hash='#/appointments';closeModal()">View my appointments</button>
      <button class="btn secondary" onclick="closeModal()">Close</button>
    </div></div>`);
}

/* Appointments (patient) */
route("/appointments", async (app) => {
  if (!requireAuth("patient")) return;
  app.innerHTML = `<h2>My Appointments</h2>
    <div class="chips" id="tabs">
      <span class="chip active" data-s="upcoming">Upcoming</span>
      <span class="chip" data-s="completed">Completed</span>
      <span class="chip" data-s="cancelled">Cancelled</span>
    </div>
    <div id="list" class="mt">${skeletons(3)}</div>`;
  let status = "upcoming";
  $("#tabs").querySelectorAll(".chip").forEach(c => c.onclick = () => {
    $("#tabs").querySelectorAll(".chip").forEach(x => x.classList.remove("active"));
    c.classList.add("active"); status = c.dataset.s; load();
  });
  async function load() {
    $("#list").innerHTML = skeletons(3);
    const items = await api("/appointments?status=" + status);
    if (!items.length) { $("#list").innerHTML = `<div class="empty"><div class="emoji">📭</div><p>No ${status} appointments.</p><a class="btn" href="#/search">Find a doctor</a></div>`; return; }
    $("#list").innerHTML = items.map(a => `
      <div class="card mt">
        <div class="between">
          <div>
            <strong>${esc(a.doctor.name)}</strong> <span class="pill ${a.status}">${a.status}</span>
            <div class="muted" style="font-size:13px">${esc(a.doctor.specialty || "")} · ${esc(a.doctor.hospital || "")}</div>
            <div class="muted" style="font-size:13px">📅 ${a.date} @ ${a.slot} · ${a.type} · ${money(a.fee)} · <code>${a.code}</code></div>
          </div>
          <div class="row" style="gap:6px">
            ${a.type === "video" && a.status === "confirmed" ? `<button class="btn sm" onclick="toast('Video room is a roadmap feature 🎥')">Join</button>` : ""}
            ${a.status === "confirmed" ? `<button class="btn sm danger" onclick="cancelAppt(${a.id})">Cancel</button>` : ""}
            ${a.status === "completed" && a.prescription ? `<button class="btn sm secondary" onclick='showPrescription(${JSON.stringify(a).replace(/'/g, "&#39;")})'>Prescription</button>` : ""}
          </div>
        </div>
        ${a.symptoms ? `<div class="muted mt" style="font-size:13px">📝 ${esc(a.symptoms)}</div>` : ""}
      </div>`).join("");
  }
  load();
  window._reloadAppts = load;
});

async function cancelAppt(id) {
  if (!confirm("Cancel this appointment?")) return;
  try { await api(`/appointments/${id}/cancel`, { method: "POST" }); toast("Appointment cancelled", "success"); window._reloadAppts && window._reloadAppts(); }
  catch (e) { toast(e.message, "error"); }
}

function showPrescription(a) {
  const p = a.prescription;
  modal(`<h3>Prescription</h3>
    <p class="muted" style="margin-top:-8px">${esc(a.doctor.name)} · ${a.date}</p>
    <table class="table"><tr><th>Medicine</th><th>Dosage</th><th>Freq</th><th>Duration</th></tr>
      ${(p.medicines || []).map(m => `<tr><td>${esc(m.name)}</td><td>${esc(m.dosage)}</td><td>${esc(m.frequency)}</td><td>${esc(m.duration)}</td></tr>`).join("")}
    </table>
    ${p.advice ? `<p class="mt"><strong>Advice:</strong> ${esc(p.advice)}</p>` : ""}
    ${p.tests ? `<p><strong>Tests:</strong> ${esc(p.tests)}</p>` : ""}
    ${p.follow_up_date ? `<p><strong>Follow-up:</strong> ${esc(p.follow_up_date)}</p>` : ""}
    <button class="btn block mt" onclick="closeModal()">Close</button>`);
}

/* Profile */
route("/profile", async (app) => {
  if (!requireAuth()) return;
  const u = await api("/auth/me");
  const f = (k, label, type = "text") => `<div class="field"><label>${label}</label><input id="p_${k}" type="${type}" value="${esc(u[k] ?? "")}" /></div>`;
  app.innerHTML = `<h2>My Profile</h2>
    <div class="auth-wrap"><div class="card">
      <div class="center"><div class="avatar" style="width:64px;height:64px;font-size:24px;margin:0 auto">${initials(u.name)}</div>
        <p class="muted">${esc(u.email)} · <span class="badge">${u.role}</span></p></div>
      ${f("name", "Full name")}
      ${f("phone", "Phone")}
      <div class="row">${f("age", "Age", "number")}<div style="flex:1">${f("gender", "Gender")}</div></div>
      ${f("blood_group", "Blood group")}
      ${f("address", "Address")}
      <button class="btn block mt" id="saveBtn">Save changes</button>
    </div></div>`;
  $("#saveBtn").onclick = async () => {
    const body = {}; ["name", "phone", "age", "gender", "blood_group", "address"].forEach(k => { const v = $("#p_" + k).value.trim(); if (v) body[k] = k === "age" ? Number(v) : v; });
    try { const upd = await api("/auth/me", { method: "PUT", body }); store.user = { ...store.user, name: upd.name }; renderChrome(); toast("Profile saved", "success"); }
    catch (e) { toast(e.message, "error"); }
  };
});

/* Login / signup */
route("/login", async (app) => {
  app.innerHTML = `<div class="auth-wrap"><div class="card">
    <div class="tabs"><button class="active" id="tabLogin">Sign in</button><button id="tabSignup">Create account</button></div>
    <div id="formHost"></div>
    <div class="mt center muted" style="font-size:13px">
      Demo logins:<br>patient: asha@mydocplus.dev / patient123<br>
      doctor: neha@mydocplus.dev / doctor123<br>admin: admin@mydocplus.dev / admin123</div>
  </div></div>`;
  const host = $("#formHost");
  const loginForm = () => {
    host.innerHTML = `<div class="field"><label>Email</label><input id="email" type="email" value="asha@mydocplus.dev"/></div>
      <div class="field"><label>Password</label><input id="password" type="password" value="patient123"/></div>
      <button class="btn block" id="submit">Sign in</button>`;
    $("#submit").onclick = async () => {
      try { const d = await api("/auth/login", { method: "POST", auth: false, body: { email: $("#email").value.trim(), password: $("#password").value } });
        setSession(d); toast("Welcome back, " + d.user.name.split(" ")[0], "success"); routeAfterLogin(d.user); }
      catch (e) { toast(e.message, "error"); }
    };
  };
  const signupForm = () => {
    host.innerHTML = `<div class="field"><label>Full name</label><input id="name"/></div>
      <div class="field"><label>Email</label><input id="email" type="email"/></div>
      <div class="field"><label>Phone</label><input id="phone"/></div>
      <div class="field"><label>Password</label><input id="password" type="password"/></div>
      <button class="btn block" id="submit">Create account</button>`;
    $("#submit").onclick = async () => {
      try { const d = await api("/auth/signup", { method: "POST", auth: false, body: {
        name: $("#name").value.trim(), email: $("#email").value.trim(), phone: $("#phone").value.trim(), password: $("#password").value } });
        setSession(d); toast("Account created 🎉", "success"); location.hash = "#/"; }
      catch (e) { toast(e.message, "error"); }
    };
  };
  $("#tabLogin").onclick = () => { $("#tabLogin").classList.add("active"); $("#tabSignup").classList.remove("active"); loginForm(); };
  $("#tabSignup").onclick = () => { $("#tabSignup").classList.add("active"); $("#tabLogin").classList.remove("active"); signupForm(); };
  loginForm();
});
function routeAfterLogin(u) {
  if (u.role === "admin") location.hash = "#/admin";
  else if (u.role === "doctor") location.hash = "#/doctor-panel";
  else location.hash = "#/";
}

/* Doctor panel */
route("/doctor-panel", async (app) => {
  if (!requireAuth("doctor")) return;
  app.innerHTML = `<h2>Doctor Panel</h2><div id="list">${skeletons(3)}</div>`;
  async function load() {
    const items = await api("/appointments");
    const upcoming = items.filter(a => a.status === "confirmed");
    const revenue = items.filter(a => a.status !== "cancelled").reduce((s, a) => s + a.fee, 0);
    app.innerHTML = `<h2>Doctor Panel</h2>
      <div class="grid stat-grid">
        <div class="card stat"><div class="val">${upcoming.length}</div><div class="lbl">Upcoming</div></div>
        <div class="card stat"><div class="val">${items.filter(a => a.status === "completed").length}</div><div class="lbl">Completed</div></div>
        <div class="card stat"><div class="val">${money(revenue)}</div><div class="lbl">Revenue</div></div>
        <div class="card stat"><div class="val">${new Set(items.map(a => a.patient && a.patient.name)).size}</div><div class="lbl">Patients</div></div>
      </div>
      <div class="section-title"><span>Appointments</span></div>
      <div>${items.length ? items.map(a => `
        <div class="card mt"><div class="between">
          <div><strong>${esc(a.patient ? a.patient.name : "Patient")}</strong> <span class="pill ${a.status}">${a.status}</span>
            <div class="muted" style="font-size:13px">📅 ${a.date} @ ${a.slot} · ${a.type} · ${money(a.fee)}</div>
            ${a.symptoms ? `<div class="muted" style="font-size:13px">📝 ${esc(a.symptoms)}</div>` : ""}</div>
          <div class="row" style="gap:6px">
            ${a.status === "confirmed" ? `<button class="btn sm" onclick="completeAppt(${a.id})">Complete + Rx</button>
              <button class="btn sm danger" onclick="cancelAppt(${a.id})">Cancel</button>` : ""}
          </div></div></div>`).join("") : '<div class="empty">No appointments yet.</div>'}</div>`;
  }
  await load();
  window._reloadAppts = load;
});

function completeAppt(id) {
  modal(`<h3>Complete & prescribe</h3>
    <div class="field"><label>Medicine</label><input id="rx_name" placeholder="e.g. Paracetamol"/></div>
    <div class="row"><div class="field" style="flex:1"><label>Dosage</label><input id="rx_dose" placeholder="500mg"/></div>
      <div class="field" style="flex:1"><label>Frequency</label><input id="rx_freq" placeholder="Twice daily"/></div></div>
    <div class="field"><label>Duration</label><input id="rx_dur" placeholder="5 days"/></div>
    <div class="field"><label>Advice</label><textarea id="rx_advice" rows="2"></textarea></div>
    <div class="field"><label>Follow-up date</label><input id="rx_follow" type="date"/></div>
    <button class="btn block" id="rxSave">Complete appointment</button>`);
  $("#rxSave").onclick = async () => {
    const meds = $("#rx_name").value.trim() ? [{ name: $("#rx_name").value.trim(), dosage: $("#rx_dose").value.trim(), frequency: $("#rx_freq").value.trim(), duration: $("#rx_dur").value.trim() }] : [];
    try {
      await api(`/appointments/${id}/complete`, { method: "POST", body: { prescription: { medicines: meds, advice: $("#rx_advice").value.trim(), follow_up_date: $("#rx_follow").value } } });
      closeModal(); toast("Appointment completed", "success"); window._reloadAppts && window._reloadAppts();
    } catch (e) { toast(e.message, "error"); }
  };
}

/* Admin */
route("/admin", async (app) => {
  if (!requireAuth("admin")) return;
  app.innerHTML = `<h2>Admin Dashboard</h2><div id="stats" class="grid stat-grid">${skeletons(4)}</div>
    <div class="section-title"><span>Recent appointments</span></div>
    <div class="card"><div id="apptTable">${skeletons(1)}</div></div>`;
  const s = await api("/admin/stats");
  $("#stats").innerHTML = `
    <div class="card stat"><div class="val">${s.total_doctors}</div><div class="lbl">Doctors</div></div>
    <div class="card stat"><div class="val">${s.total_patients}</div><div class="lbl">Patients</div></div>
    <div class="card stat"><div class="val">${s.total_appointments}</div><div class="lbl">Appointments</div></div>
    <div class="card stat"><div class="val">${money(s.revenue)}</div><div class="lbl">Revenue</div></div>
    <div class="card stat"><div class="val">${(s.cancellation_rate * 100).toFixed(0)}%</div><div class="lbl">Cancellation rate</div></div>
    <div class="card stat"><div class="val">${s.appointments_by_status.completed}</div><div class="lbl">Completed</div></div>`;
  const appts = await api("/admin/appointments");
  $("#apptTable").innerHTML = appts.length ? `<table class="table">
    <tr><th>Code</th><th>Patient</th><th>Doctor</th><th>Date</th><th>Type</th><th>Fee</th><th>Status</th></tr>
    ${appts.map(a => `<tr><td><code>${a.code}</code></td><td>${esc(a.patient)}</td><td>${esc(a.doctor)}</td><td>${a.date} ${a.slot}</td><td>${a.type}</td><td>${money(a.fee)}</td><td><span class="pill ${a.status}">${a.status}</span></td></tr>`).join("")}
    </table>` : '<div class="empty">No appointments.</div>';
});

/* ----------------------- AI Symptom Assistant ----------------------- */
const URGENCY = {
  emergency: { label: "Emergency", cls: "cancelled", emoji: "🚨" },
  soon: { label: "See a doctor soon", cls: "pending", emoji: "⚠️" },
  routine: { label: "Routine", cls: "confirmed", emoji: "🟢" },
};

function assistantDoctorCard(d) {
  return `<div class="card hover doc-card" style="cursor:pointer;padding:12px"
      onclick="closeModal();location.hash='#/doctor/${d.id}'">
    <div class="doc-photo" style="width:44px;height:44px;font-size:16px">${initials(d.name)}</div>
    <div class="doc-main">
      <div class="doc-name" style="font-size:14px">${esc(d.name)}</div>
      <div class="doc-meta"><span class="stars">${stars(d.rating)}</span> ${d.rating} · <strong>${money(d.consultation_fee)}</strong></div>
    </div>
    <button class="btn sm">Book</button>
  </div>`;
}

function openAssistant() {
  modal(`<div class="between"><h3 style="margin:0">🤖 AI Symptom Assistant</h3>
      <button class="icon-btn" onclick="closeModal()">✕</button></div>
    <p class="muted" style="font-size:13px;margin-top:6px">Tell me how you're feeling and I'll suggest the right specialist. This isn't a diagnosis.</p>
    <div id="aiChat" class="ai-chat"></div>
    <div class="ai-suggestions" id="aiSug">
      ${["I have a bad headache and feel dizzy", "Skin rash and itching", "Chest pain and short of breath", "My child has a fever", "Toothache since 2 days"]
        .map(s => `<span class="chip" onclick="aiAsk('${s.replace(/'/g, "\\'")}')">${s}</span>`).join("")}
    </div>
    <div class="searchbar mt">
      <span>💬</span>
      <input id="aiInput" placeholder="Describe your symptoms..." />
      <button class="btn" id="aiSend">Ask</button>
    </div>`);

  const send = () => { const v = $("#aiInput").value.trim(); if (v) aiAsk(v); };
  $("#aiSend").onclick = send;
  $("#aiInput").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  setTimeout(() => $("#aiInput") && $("#aiInput").focus(), 50);
}

async function aiAsk(text) {
  const chat = $("#aiChat");
  const sug = $("#aiSug");
  if (sug) sug.style.display = "none";
  if ($("#aiInput")) $("#aiInput").value = "";
  chat.innerHTML += `<div class="ai-bubble user">${esc(text)}</div>`;
  chat.innerHTML += `<div class="ai-bubble bot" id="aiThinking">Thinking…</div>`;
  chat.scrollTop = chat.scrollHeight;
  try {
    const r = await api("/ai/triage", { method: "POST", auth: false, body: { symptoms: text } });
    const u = URGENCY[r.urgency] || URGENCY.routine;
    const msgHtml = esc(r.message).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    let html = `<div><span class="pill ${u.cls}">${u.emoji} ${u.label}</span></div>
      <div class="mt">${msgHtml}</div>`;
    if (r.doctors && r.doctors.length) {
      html += `<div class="mt" style="font-weight:700;font-size:13px">Recommended doctors</div>
        <div class="grid mt" style="gap:8px">${r.doctors.map(assistantDoctorCard).join("")}</div>`;
    }
    html += `<div class="muted mt" style="font-size:11px">ℹ️ ${esc(r.disclaimer)}</div>`;
    $("#aiThinking").outerHTML = `<div class="ai-bubble bot">${html}</div>`;
  } catch (e) {
    $("#aiThinking").outerHTML = `<div class="ai-bubble bot">Sorry, something went wrong: ${esc(e.message)}</div>`;
  }
  chat.scrollTop = chat.scrollHeight;
}

/* ----------------------- boot ----------------------- */
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-link]");
  if (a) { /* hash links handled natively */ }
});
window.addEventListener("hashchange", router);

// Floating AI assistant button
const fab = document.createElement("button");
fab.className = "fab";
fab.id = "aiFab";
fab.title = "AI Symptom Assistant";
fab.innerHTML = "🤖";
fab.onclick = openAssistant;
document.body.appendChild(fab);

initTheme();
renderChrome();
router();

// expose handlers used in inline onclick
Object.assign(window, { logout, closeModal, cancelAppt, completeAppt, showPrescription, toast, openAssistant, aiAsk });
