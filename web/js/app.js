const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const state = {
  mode: "home",
  title: "",
  listData: [],
  skins: [],
  pendingSkin: null,
  stack: [],
};

const views = {
  home: $("#view-home"),
  list: $("#view-list"),
  skins: $("#view-skins"),
  status: $("#view-status"),
};

const els = {
  back: $("#btn-back"),
  statusBtn: $("#btn-status"),
  listItems: $("#list-items"),
  listSearch: $("#list-search"),
  listSearchWrap: $("#list-search-wrap"),
  skinGrid: $("#skin-grid"),
  skinSearch: $("#skin-search"),
  skinSearchWrap: $("#skin-search-wrap"),
  modal: $("#modal-overlay"),
  modalImg: $("#modal-img"),
  modalTitle: $("#modal-title"),
  modalSub: $("#modal-sub"),
  modalYes: $("#modal-yes"),
  modalNo: $("#modal-no"),
  loading: $("#loading"),
  loadingText: $("#loading-text"),
  toast: $("#toast"),
  statusCard: $("#status-card"),
};

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok && data.error) throw new Error(data.error);
  return data;
}

function showView(name) {
  Object.values(views).forEach((v) => v.classList.remove("active"));
  if (views[name]) views[name].classList.add("active");
  els.back.classList.toggle("hidden", name === "home");
}

function setLoading(on, text = "Memuat...") {
  els.loading.classList.toggle("hidden", !on);
  els.loadingText.textContent = text;
}

function toast(msg, type = "") {
  els.toast.textContent = msg;
  els.toast.className = `toast ${type}`;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => els.toast.classList.add("hidden"), 4000);
}

function goHome() {
  state.stack = [];
  state.mode = "home";
  showView("home");
}

function pushNav(mode, title, data = []) {
  state.stack.push({ mode: state.mode, title: state.title, listData: state.listData, skins: state.skins });
  state.mode = mode;
  state.title = title;
  state.listData = data;
}

function goBack() {
  if (state.stack.length === 0) return goHome();
  const prev = state.stack.pop();
  state.mode = prev.mode;
  state.title = prev.title;
  state.listData = prev.listData;
  state.skins = prev.skins;

  if (state.mode === "home") return goHome();
  if (state.skins?.length) {
    showView("skins");
    renderSkins(state.skins);
    return;
  }
  showView("list");
  renderList(state.listData);
}

function placeholderImg() {
  return "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="260"><rect fill="#1a1030" width="200" height="260"/><text x="50%" y="50%" fill="#666" font-size="14" text-anchor="middle" dy=".3em">No Image</text></svg>'
  );
}

function renderList(items, filter = "") {
  const q = filter.trim().toLowerCase();
  const filtered = q
    ? items.filter((it) => (it.label || it.name || it).toString().toLowerCase().includes(q))
    : items;

  if (!filtered.length) {
    els.listItems.innerHTML = '<p class="empty-state">Tidak ada data.</p>';
    return;
  }

  els.listItems.innerHTML = filtered
    .map((it) => {
      const label = it.label || it.name || it;
      const img = it.image_url ? `<img src="${esc(it.image_url)}" alt="" loading="lazy" onerror="this.style.display='none'" />` : "";
      const payload = esc(JSON.stringify(it));
      return `<button type="button" class="list-item" data-payload='${payload}'>
        ${img}<span>${esc(label)}</span><span class="arrow">›</span>
      </button>`;
    })
    .join("");

  els.listItems.querySelectorAll(".list-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = JSON.parse(btn.dataset.payload);
      onListPick(item);
    });
  });
}

function renderSkins(skins, filter = "") {
  const q = filter.trim().toLowerCase();
  const filtered = q
    ? skins.filter((s) => (s.label || "").toLowerCase().includes(q))
    : skins;

  if (!filtered.length) {
    els.skinGrid.innerHTML = '<p class="empty-state">Skin tidak ditemukan.</p>';
    return;
  }

  els.skinGrid.innerHTML = filtered
    .map(
      (s) => `
    <article class="skin-card" data-id="${esc(s.id)}" tabindex="0" role="button">
      <img class="skin-banner" src="${esc(s.image_url || placeholderImg())}" alt="${esc(s.label)}" loading="lazy"
        onerror="this.src='${placeholderImg()}'" />
      <p class="skin-name">${esc(s.label || s.skin_name || "Skin")}</p>
    </article>`
    )
    .join("");

  els.skinGrid.querySelectorAll(".skin-card").forEach((card, i) => {
    const skin = filtered[i];
    const open = () => openModal(skin);
    card.addEventListener("click", open);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });
  });
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function openModal(skin) {
  state.pendingSkin = skin;
  els.modalImg.src = skin.image_url || placeholderImg();
  els.modalImg.onerror = () => { els.modalImg.src = placeholderImg(); };
  els.modalTitle.textContent = "Inject skin ini?";
  els.modalSub.textContent = skin.label || `${skin.hero_name} — ${skin.skin_name}`;
  els.modalYes.disabled = false;
  els.modal.classList.remove("hidden");
}

function closeModal() {
  els.modal.classList.add("hidden");
  state.pendingSkin = null;
}

async function doInject() {
  const skin = state.pendingSkin;
  if (!skin) return;
  els.modalYes.disabled = true;
  setLoading(true, "Menginject skin...");
  try {
    const res = await api("/api/inject", {
      method: "POST",
      body: JSON.stringify(skin),
    });
    closeModal();
    if (res.ok) toast(res.message || "Inject berhasil!", "ok");
    else toast(res.message || "Inject gagal", "err");
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
    els.modalYes.disabled = false;
  }
}

async function loadHeroes() {
  pushNav("heroes", "Browse Hero");
  setLoading(true);
  try {
    const { heroes } = await api("/api/heroes");
    state.listData = heroes.map((h) => ({ name: h, label: h }));
    showView("list");
    els.listSearchWrap.classList.remove("hidden");
    els.listSearch.value = "";
    els.listSearch.placeholder = "Cari hero...";
    renderList(state.listData);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadRoles() {
  pushNav("roles", "Browse Role");
  setLoading(true);
  try {
    const { roles } = await api("/api/roles");
    state.listData = roles.map((r) => ({ name: r, label: r }));
    showView("list");
    els.listSearchWrap.classList.remove("hidden");
    els.listSearch.value = "";
    els.listSearch.placeholder = "Cari role...";
    renderList(state.listData);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadRoleHeroes(role) {
  pushNav("role-heroes", role);
  setLoading(true);
  try {
    const { heroes } = await api(`/api/roles/${encodeURIComponent(role)}/heroes`);
    state.listData = heroes.map((h) => ({ name: h, label: h, role }));
    showView("list");
    els.listSearch.value = "";
    renderList(state.listData);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadHeroSkins(hero) {
  pushNav("hero-skins", hero);
  setLoading(true);
  try {
    const { skins } = await api(`/api/heroes/${encodeURIComponent(hero)}/skins`);
    state.skins = skins;
    showView("skins");
    els.skinSearchWrap.classList.remove("hidden");
    els.skinSearch.value = "";
    renderSkins(skins);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadUpgrade() {
  pushNav("upgrade", "Upgrade Skin");
  setLoading(true);
  try {
    const { items } = await api("/api/upgrade");
    state.listData = items;
    showView("list");
    els.listSearchWrap.classList.remove("hidden");
    els.listSearch.value = "";
    els.listSearch.placeholder = "Cari upgrade...";
    renderList(state.listData);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadUpgradeSkins(item) {
  pushNav("upgrade-skins", item.label);
  setLoading(true);
  try {
    const { skins } = await api(`/api/upgrade/${item.index}/skins`);
    state.skins = skins;
    showView("skins");
    els.skinSearch.value = "";
    renderSkins(skins);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadCustom() {
  pushNav("custom", "Custom Bundle");
  setLoading(true);
  try {
    const { bundles } = await api("/api/custom/bundles");
    state.listData = bundles;
    showView("list");
    els.listSearchWrap.classList.remove("hidden");
    els.listSearch.value = "";
    renderList(state.listData);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadBundleSkins(bundle) {
  pushNav("bundle-skins", bundle.name);
  setLoading(true);
  try {
    const { skins } = await api(`/api/custom/${encodeURIComponent(bundle.id)}/skins`);
    state.skins = skins;
    showView("skins");
    els.skinSearch.value = "";
    renderSkins(skins);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadEffects() {
  pushNav("effects", "Effects");
  setLoading(true);
  try {
    const { categories } = await api("/api/effects/categories");
    state.listData = categories.map((c) => ({ ...c, label: c.label }));
    showView("list");
    els.listSearchWrap.classList.remove("hidden");
    els.listSearch.value = "";
    renderList(state.listData);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadEffectSkins(cat) {
  pushNav("effect-skins", cat.label);
  setLoading(true);
  try {
    const { skins } = await api(`/api/effects/${encodeURIComponent(cat.id)}/skins`);
    state.skins = skins;
    showView("skins");
    els.skinSearch.value = "";
    renderSkins(skins);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadSearch() {
  pushNav("search", "Search");
  state.skins = [];
  showView("skins");
  els.skinSearchWrap.classList.remove("hidden");
  els.skinSearch.value = "";
  els.skinSearch.placeholder = "Ketik nama hero / skin...";
  els.skinGrid.innerHTML = '<p class="empty-state">Ketik di atas lalu Enter untuk mencari.</p>';

  let debounce;
  els.skinSearch.oninput = () => {
    clearTimeout(debounce);
    const q = els.skinSearch.value.trim();
    if (q.length < 2) {
      els.skinGrid.innerHTML = '<p class="empty-state">Minimal 2 karakter.</p>';
      return;
    }
    debounce = setTimeout(() => runSearch(q), 400);
  };
}

async function runSearch(q) {
  setLoading(true);
  try {
    const { skins } = await api(`/api/search?q=${encodeURIComponent(q)}`);
    state.skins = skins;
    renderSkins(skins);
  } catch (e) {
    toast(String(e.message || e), "err");
  } finally {
    setLoading(false);
  }
}

async function loadStatus() {
  pushNav("status", "Status");
  showView("status");
  els.statusCard.innerHTML = '<div class="loader"></div><p>Memuat status...</p>';
  try {
    const st = await api("/api/status");
    const ok = st.ok ? "status-ok" : "status-bad";
    els.statusCard.innerHTML = `
      <h3 style="margin-bottom:16px;font-size:1.1rem">Status Sistem</h3>
      <div class="status-row"><span>Backend</span><span>${esc(st.backend || "-")}</span></div>
      <div class="status-row"><span>Package MLBB</span><span>${esc(st.package || "-")}</span></div>
      <div class="status-row"><span>Assets path</span><span style="font-size:0.75rem;word-break:break-all">${esc(st.assets_path || "-")}</span></div>
      <div class="status-row"><span>Katalog</span><span>${esc(st.catalog || "-")}</span></div>
      <div class="status-row"><span>Heroes</span><span>${st.heroes ?? "-"}</span></div>
      <div class="status-row"><span>Siap inject</span><span class="${ok}">${st.ok ? "Ya" : "Tidak"}</span></div>
    `;
    els.statusBtn.classList.toggle("online", !!st.ok);
  } catch (e) {
    els.statusCard.innerHTML = `<p class="status-bad">${esc(String(e.message || e))}</p>`;
  }
}

function onListPick(item) {
  if (state.mode === "heroes" || (state.mode === "role-heroes")) {
    loadHeroSkins(item.name || item.label);
    return;
  }
  if (state.mode === "roles") {
    loadRoleHeroes(item.name || item.label);
    return;
  }
  if (state.mode === "upgrade") {
    loadUpgradeSkins(item);
    return;
  }
  if (state.mode === "custom") {
    loadBundleSkins(item);
    return;
  }
  if (state.mode === "effects") {
    loadEffectSkins(item);
    return;
  }
}

function onMenu(mode) {
  switch (mode) {
    case "heroes": return loadHeroes();
    case "roles": return loadRoles();
    case "search": return loadSearch();
    case "upgrade": return loadUpgrade();
    case "custom": return loadCustom();
    case "effects": return loadEffects();
    default: return goHome();
  }
}

$$(".menu-btn").forEach((btn) => {
  btn.addEventListener("click", () => onMenu(btn.dataset.mode));
});

els.back.addEventListener("click", goBack);
els.statusBtn.addEventListener("click", loadStatus);
els.modalNo.addEventListener("click", closeModal);
els.modalYes.addEventListener("click", doInject);
els.modal.addEventListener("click", (e) => {
  if (e.target === els.modal) closeModal();
});

els.listSearch.addEventListener("input", () => {
  renderList(state.listData, els.listSearch.value);
});

els.skinSearch.addEventListener("input", () => {
  if (state.mode === "search") return;
  renderSkins(state.skins, els.skinSearch.value);
});

els.skinSearch.addEventListener("keydown", (e) => {
  if (state.mode === "search" && e.key === "Enter") {
    const q = els.skinSearch.value.trim();
    if (q.length >= 2) runSearch(q);
  }
});

api("/api/status")
  .then((st) => els.statusBtn.classList.toggle("online", !!st.ok))
  .catch(() => {});
