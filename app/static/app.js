const $ = (s) => document.querySelector(s);
const watchlist = $('#watchlist');
const eventsBox = $('#events');

function fmtDate(v) {
  if (!v) return 'Never checked';
  try { return new Date(v).toLocaleString(); } catch { return v; }
}
function statusClass(s) {
  return s === 'IN_STOCK' ? 'in' : s === 'OUT_OF_STOCK' ? 'out' : 'unknown';
}
function statusText(s) {
  return s === 'IN_STOCK' ? 'IN STOCK' : s === 'OUT_OF_STOCK' ? 'OUT OF STOCK' : 'UNKNOWN';
}
async function api(path, opts={}) {
  const r = await fetch(path, {headers:{'Content-Type':'application/json', ...(opts.headers||{})}, ...opts});
  if (!r.ok) {
    let msg = 'Request failed';
    try { msg = (await r.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return r.json();
}
async function load() {
  const items = await api('/api/watchlist');
  $('#watchCount').textContent = `${items.length} item${items.length === 1 ? '' : 's'}`;
  watchlist.innerHTML = '';
  if (!items.length) watchlist.innerHTML = '<div class="card empty">Add your first card product above.</div>';
  for (const item of items) renderItem(item);
  await loadEvents();
}
function renderItem(item) {
  const el = $('#itemTpl').content.firstElementChild.cloneNode(true);
  el.querySelector('.retailer').textContent = item.retailer;
  el.querySelector('.item-name').textContent = item.name;
  const st = el.querySelector('.status');
  st.textContent = statusText(item.last_status);
  st.classList.add(statusClass(item.last_status));
  const price = item.last_price != null ? `$${Number(item.last_price).toFixed(2)}` : 'Price unknown';
  const cap = item.max_price != null ? ` · Alert cap $${Number(item.max_price).toFixed(2)}` : '';
  const err = item.last_error ? `<br>Last result: ${escapeHtml(item.last_error)}` : '';
  el.querySelector('.meta').innerHTML = `${price}${cap} · Every ${item.interval_seconds}s<br>Checked: ${fmtDate(item.last_checked)}${err}`;
  const open = el.querySelector('.open'); open.href = item.url;
  el.querySelector('.check').onclick = async () => {
    const b = el.querySelector('.check'); b.disabled = true; b.textContent = 'Checking…';
    try { await api(`/api/check/${item.id}`, {method:'POST'}); await load(); }
    catch(e) { alert(e.message); }
  };
  const toggle = el.querySelector('.toggle');
  toggle.textContent = item.enabled ? 'Pause' : 'Resume';
  toggle.onclick = async () => { await api(`/api/watchlist/${item.id}`, {method:'PATCH', body:JSON.stringify({enabled:!item.enabled})}); await load(); };
  el.querySelector('.delete').onclick = async () => {
    if (!confirm(`Delete ${item.name}?`)) return;
    await api(`/api/watchlist/${item.id}`, {method:'DELETE'}); await load();
  };
  watchlist.appendChild(el);
}
async function loadEvents() {
  const events = await api('/api/events');
  eventsBox.innerHTML = '';
  if (!events.length) { eventsBox.innerHTML = '<div class="card empty">No stock changes recorded yet.</div>'; return; }
  for (const e of events.slice(0, 20)) {
    const div = document.createElement('div'); div.className = 'card event';
    div.innerHTML = `<strong>${escapeHtml(e.name)} → ${statusText(e.new_status)}</strong><small>${escapeHtml(e.retailer)} · ${fmtDate(e.created_at)}${e.price != null ? ` · $${Number(e.price).toFixed(2)}` : ''}</small>`;
    eventsBox.appendChild(div);
  }
}
function escapeHtml(v='') { return String(v).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

$('#addForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const payload = {
    name: $('#name').value.trim(),
    retailer: $('#retailer').value,
    url: $('#url').value.trim(),
    interval_seconds: Number($('#interval').value),
    max_price: $('#maxPrice').value ? Number($('#maxPrice').value) : null,
  };
  try {
    await api('/api/watchlist', {method:'POST', body:JSON.stringify(payload)});
    ev.target.reset(); $('#interval').value='90'; $('#formMsg').textContent='Added.'; await load();
  } catch(e) { $('#formMsg').textContent=e.message; }
});

$('#checkAllBtn').onclick = async () => {
  const b = $('#checkAllBtn'); b.disabled=true; b.textContent='Checking…';
  try { await api('/api/check-all', {method:'POST'}); await load(); }
  catch(e) { alert(e.message); }
  finally { b.disabled=false; b.textContent='Check all now'; }
};

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
}

$('#notifyBtn').onclick = async () => {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    alert('Push notifications are not supported in this browser.'); return;
  }
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') { alert('Notification permission was not granted.'); return; }
  const reg = await navigator.serviceWorker.register('/sw.js');
  const {publicKey} = await api('/api/push/public-key');
  let sub = await reg.pushManager.getSubscription();
  if (!sub) sub = await reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:urlBase64ToUint8Array(publicKey)});
  await api('/api/push/subscribe', {method:'POST', body:JSON.stringify(sub.toJSON())});
  $('#notifyBtn').textContent='Alerts enabled';
};

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(console.error);
load().catch(e => { watchlist.innerHTML = `<div class="card empty">${escapeHtml(e.message)}</div>`; });
setInterval(load, 30000);
