(function () {
  'use strict';

  const ADMIN_PATH = (window.__ADMIN_PATH__ || '').trim();
  const API_BASE = `/admin/${ADMIN_PATH}/api`;

  const ICONS = {
    upload: `<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`,
    'trash-2': `<svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>`,
    'refresh-cw': `<svg viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`,
    'file-spreadsheet': `<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><rect x="8" y="13" width="3" height="3" rx=".5"/><rect x="13" y="13" width="3" height="3" rx=".5"/><rect x="8" y="17" width="3" height="3" rx=".5"/><rect x="13" y="17" width="3" height="3" rx=".5"/></svg>`,
    'external-link': `<svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
    'alert-circle': `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    'check-circle': `<svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    'x-circle': `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    loader: `<svg viewBox="0 0 24 24"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>`,
    'chevron-right': `<svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>`,
    loop: `<svg viewBox="0 0 24 24"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
    'check-circle-2': `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>`,
    'x-mark': `<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    clipboard: `<svg viewBox="0 0 24 24"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>`
  };

  const el = {};
  let selectedFile = null;

  function $(id) {
    return document.getElementById(id);
  }

  function initIconPlaceholders() {
    const map = {
      'icon-upload': ICONS.upload,
      'icon-btn-upload': ICONS.upload,
      'icon-file-spreadsheet': ICONS['file-spreadsheet'],
      'icon-file-preview': ICONS['file-spreadsheet'],
      'icon-refresh-cw': ICONS['refresh-cw'],
      'icon-history': ICONS.clipboard,
      'icon-alert-circle': ICONS['alert-circle'],
      'icon-empty-state': ICONS['file-spreadsheet'],
      'icon-dashboard-link': ICONS['external-link'],
      'icon-x-circle': ICONS['x-circle']
    };
    Object.keys(map).forEach(id => {
      const node = $(id);
      if (node) node.innerHTML = map[id];
    });
  }

  function formatBytes(bytes) {
    if (!bytes && bytes !== 0) return '-';
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const size = Math.min(i, sizes.length - 1);
    const val = bytes / Math.pow(k, size);
    return `${parseFloat(val.toFixed(2))} ${sizes[size]}`;
  }

  function formatDate(iso) {
    if (!iso) return '-';
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return '-';
      const bulan = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
      const tgl = d.getDate();
      const bln = bulan[d.getMonth()];
      const thn = d.getFullYear();
      const jam = String(d.getHours()).padStart(2, '0');
      const mnt = String(d.getMinutes()).padStart(2, '0');
      return `${tgl} ${bln} ${thn}, ${jam}:${mnt}`;
    } catch (e) {
      return '-';
    }
  }

  function estimateRows(file) {
    try {
      const sizeKb = file.size / 1024;
      const est = Math.max(1, Math.round(sizeKb * 1.8));
      return est;
    } catch (e) {
      return 0;
    }
  }

  function showToast(type, title, message) {
    const container = $('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = ICONS['alert-circle'];
    if (type === 'success') iconSvg = ICONS['check-circle'];
    if (type === 'error') iconSvg = ICONS['x-circle'];
    if (type === 'info') iconSvg = ICONS['alert-circle'];

    toast.innerHTML = `
      <span class="toast-icon">${iconSvg}</span>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message || ''}</div>
      </div>
      <button type="button" class="toast-close" aria-label="Tutup">${ICONS['x-mark']}</button>
    `;

    container.appendChild(toast);

    const closeBtn = toast.querySelector('.toast-close');
    const dismiss = () => {
      if (toast.classList.contains('leaving')) return;
      toast.classList.add('leaving');
      setTimeout(() => toast.remove(), 200);
    };

    if (closeBtn) closeBtn.addEventListener('click', dismiss);
    setTimeout(dismiss, 4200);
  }

  function renderTable(uploads) {
    const tbody = $('uploadTableBody');
    if (!tbody) return;

    if (!uploads || !uploads.length) {
      tbody.innerHTML = `
        <tr class="table-empty">
          <td colspan="7">
            <div class="empty-state">
              <span class="icon-empty">${ICONS['file-spreadsheet']}</span>
              <p>Belum ada data upload.</p>
              <p class="empty-subtext">Klik Refresh atau upload file pertama.</p>
            </div>
          </td>
        </tr>`;
      return;
    }

    const rows = uploads.map(u => {
      const isActive = Number(u.is_active) === 1 || u.is_active === true;
      const statusClass = isActive ? 'status-active' : '';
      const statusText = isActive ? 'AKTIF' : (u.status || 'Ready');
      const statusBadgeClass = isActive ? 'badge-success' : (u.status === 'PROCESSING' ? 'badge-warning' : 'badge-secondary');

      const rangeText = u.date_range_min && u.date_range_max
        ? `${formatDate(u.date_range_min).split(',')[0]} — ${formatDate(u.date_range_max).split(',')[0]}`
        : (u.date_range || '-');

      const actions = [];
      if (!isActive) {
        actions.push(`<button type="button" class="btn btn-primary btn-sm act-set-active" data-id="${u.id}">
          <span class="icon-inline">${ICONS['check-circle-2']}</span> Jadikan Aktif
        </button>`);
      }
      actions.push(`<button type="button" class="btn btn-secondary btn-sm act-reparse" data-id="${u.id}" title="Reparse">
        <span class="icon-inline">${ICONS.loop}</span>
      </button>`);
      actions.push(`<button type="button" class="btn btn-danger btn-sm act-delete" data-id="${u.id}" title="Hapus">
        <span class="icon-inline">${ICONS['trash-2']}</span>
      </button>`);

      return `
        <tr data-id="${u.id}">
          <td>#${u.id || '-'}</td>
          <td>
            <div style="font-weight:500;">${u.filename || '-'}</div>
            <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">${formatBytes(u.file_size)}</div>
          </td>
          <td>${formatDate(u.uploaded_at || u.created_at)}</td>
          <td>${u.rows_count != null ? u.rows_count.toLocaleString('id-ID') : '-'}</td>
          <td>${rangeText}</td>
          <td>
            <span class="badge ${statusBadgeClass} ${statusClass}" style="${isActive ? 'font-weight:700;' : ''}">${statusText}</span>
          </td>
          <td class="col-actions">
            <div class="row-actions">
              ${actions.join('')}
            </div>
          </td>
        </tr>
      `;
    }).join('');

    tbody.innerHTML = rows;

    tbody.querySelectorAll('.act-set-active').forEach(btn => {
      btn.addEventListener('click', () => setActive(btn.dataset.id));
    });
    tbody.querySelectorAll('.act-reparse').forEach(btn => {
      btn.addEventListener('click', () => reparseUpload(btn.dataset.id));
    });
    tbody.querySelectorAll('.act-delete').forEach(btn => {
      btn.addEventListener('click', () => deleteUpload(btn.dataset.id));
    });
  }

  async function loadUploadHistory() {
    const btn = $('btnRefreshList');
    if (btn) {
      btn.disabled = true;
      const orig = btn.innerHTML;
      btn.innerHTML = `<span class="icon-inline spinner">${ICONS.loader}</span> Loading...`;
      try {
        const res = await fetch(`${API_BASE}/uploads`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        });
        let data = {};
        try { data = await res.json(); } catch (_e) { data = {}; }
        if (!res.ok) {
          const msg = data.detail || data.message || `HTTP ${res.status}`;
          showToast('error', 'Gagal Memuat Riwayat', msg);
          renderTable([]);
          return;
        }
        const list = Array.isArray(data) ? data : (data.uploads || data.data || []);
        renderTable(list);
        showToast('info', 'Riwayat Dimuat', `${list.length} item ditampilkan.`);
      } catch (err) {
        console.error(err);
        showToast('error', 'Koneksi Gagal', err && err.message ? err.message : 'Tidak dapat terhubung ke server.');
        renderTable([]);
      } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
      }
    }
  }

  function handleFileSelect(file) {
    if (!file) return;
    const name = (file.name || '').toLowerCase();
    const allowed = /\.(xlsx|xls)$/i.test(name);
    if (!allowed) {
      showToast('error', 'Format Tidak Didukung', 'Pilih file dengan format .xlsx atau .xls.');
      return;
    }
    if (file.size > 200 * 1024 * 1024) {
      showToast('error', 'File Terlalu Besar', `Max 200 MB. File Anda ${formatBytes(file.size)}.`);
      return;
    }
    selectedFile = file;
    updatePreview();
  }

  function updatePreview() {
    const preview = $('filePreview');
    const btnUpload = $('btnUpload');
    if (!preview || !btnUpload) return;

    if (!selectedFile) {
      preview.style.display = 'none';
      btnUpload.disabled = true;
      return;
    }

    preview.style.display = 'block';
    btnUpload.disabled = false;

    const nameEl = $('fileName');
    const sizeEl = $('fileSize');
    const rowsEl = $('fileRows');
    if (nameEl) nameEl.textContent = selectedFile.name || '-';
    if (sizeEl) sizeEl.textContent = formatBytes(selectedFile.size);
    if (rowsEl) rowsEl.textContent = `~${estimateRows(selectedFile).toLocaleString('id-ID')} rows (est.)`;
  }

  function clearSelection() {
    selectedFile = null;
    const input = $('fileInput');
    if (input) input.value = '';
    updatePreview();
    hideProgress();
  }

  function showProgress() {
    const wrap = $('progressWrapper');
    const bar = $('progressBar');
    const label = $('progressLabel');
    if (wrap) wrap.style.display = 'block';
    if (bar) bar.style.width = '0%';
    if (label) label.textContent = '0%';
  }

  function hideProgress() {
    const wrap = $('progressWrapper');
    if (wrap) wrap.style.display = 'none';
  }

  function setProgress(pct, labelText) {
    const bar = $('progressBar');
    const label = $('progressLabel');
    const p = Math.max(0, Math.min(100, pct));
    if (bar) bar.style.width = `${p}%`;
    if (label) label.textContent = labelText || `${Math.round(p)}%`;
  }

  function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  async function uploadFile() {
    if (!selectedFile) {
      showToast('error', 'Pilih File', 'Silakan pilih file .xlsx terlebih dahulu.');
      return;
    }
    const btn = $('btnUpload');
    const fileInput = $('fileInput');
    const dropArea = $('drop-area');
    const btnRemove = $('btnRemoveFile');

    const busy = true;
    if (btn) {
      btn.disabled = true;
      btn.dataset.origHtml = btn.innerHTML;
      btn.innerHTML = `<span class="icon-inline spinner">${ICONS.loader}</span> Uploading...`;
    }
    if (fileInput) fileInput.disabled = true;
    if (dropArea) dropArea.style.pointerEvents = 'none';
    if (btnRemove) btnRemove.disabled = true;

    showProgress();

    const steps = [10, 30, 50, 70, 90];
    let responsePromise = null;

    try {
      const form = new FormData();
      form.append('file', selectedFile);

      responsePromise = fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: form,
        headers: { 'Accept': 'application/json' }
      });

      for (const pct of steps) {
        await sleep(280);
        if (pct < 90) {
          setProgress(pct);
        } else {
          setProgress(pct, 'Memproses file...');
        }
      }

      const res = await responsePromise;
      let data = {};
      try { data = await res.json(); } catch (_e) { data = {}; }

      if (!res.ok) {
        setProgress(0);
        const msg = data.detail || data.message || data.error || `HTTP ${res.status}`;
        showToast('error', 'Upload Gagal', msg);
        return;
      }

      setProgress(100, 'Selesai!');
      await sleep(260);

      const detailMsg = data.detail
        || (data.upload && data.upload.rows_count ? `${Number(data.upload.rows_count).toLocaleString('id-ID')} baris berhasil diproses dan report diaktifkan.` : 'File berhasil diunggah.');
      showToast('success', 'Upload Berhasil', detailMsg);

      clearSelection();
      loadUploadHistory();

    } catch (err) {
      console.error(err);
      setProgress(0);
      const msg = err && err.message ? err.message : 'Tidak dapat terhubung ke server.';
      showToast('error', 'Upload Gagal', msg);
    } finally {
      if (btn) {
        btn.disabled = false;
        if (btn.dataset.origHtml) btn.innerHTML = btn.dataset.origHtml;
      }
      if (fileInput) fileInput.disabled = false;
      if (dropArea) dropArea.style.pointerEvents = '';
      if (btnRemove) btnRemove.disabled = false;
      hideProgress();
    }
  }

  async function setActive(id) {
    if (!id) return;
    const ok = window.confirm('Jadikan file ini sebagai data AKTIF di dashboard?');
    if (!ok) return;

    try {
      const res = await fetch(`${API_BASE}/uploads/${encodeURIComponent(id)}/set-active`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });
      let data = {};
      try { data = await res.json(); } catch (_e) { data = {}; }
      if (!res.ok) {
        const msg = data.detail || data.message || `HTTP ${res.status}`;
        showToast('error', 'Gagal Aktifkan', msg);
        return;
      }
      const msg = 'File berhasil dijadikan aktif di dashboard.';
      showToast('success', 'Diaktifkan', msg);
      loadUploadHistory();
    } catch (err) {
      console.error(err);
      showToast('error', 'Koneksi Gagal', err && err.message ? err.message : 'Tidak dapat terhubung.');
    }
  }

  async function reparseUpload(id) {
    if (!id) return;
    const ok = window.confirm('Jalankan parser ulang untuk file ini?');
    if (!ok) return;

    try {
      const res = await fetch(`${API_BASE}/uploads/${encodeURIComponent(id)}/reparse`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });
      let data = {};
      try { data = await res.json(); } catch (_e) { data = {}; }
      if (!res.ok) {
        const msg = data.detail || data.message || `HTTP ${res.status}`;
        showToast('error', 'Reparse Gagal', msg);
        return;
      }
      const msg = data.detail || 'Parser berjalan di background.';
      showToast('info', 'Reparse Dijalankan', msg);
      loadUploadHistory();
    } catch (err) {
      console.error(err);
      showToast('error', 'Koneksi Gagal', err && err.message ? err.message : 'Tidak dapat terhubung.');
    }
  }

  async function deleteUpload(id) {
    if (!id) return;
    const ok = window.confirm('Hapus file upload ini? Data terkait akan ikut dihapus. Tindakan ini tidak bisa dibatalkan.');
    if (!ok) return;

    try {
      const res = await fetch(`${API_BASE}/uploads/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: { 'Accept': 'application/json' }
      });
      let data = {};
      try { data = await res.json(); } catch (_e) { data = {}; }
      if (!res.ok) {
        const msg = data.detail || data.message || `HTTP ${res.status}`;
        showToast('error', 'Hapus Gagal', msg);
        return;
      }
      const msg = data.detail || 'Upload berhasil dihapus.';
      showToast('success', 'Dihapus', msg);
      loadUploadHistory();
    } catch (err) {
      console.error(err);
      showToast('error', 'Koneksi Gagal', err && err.message ? err.message : 'Tidak dapat terhubung.');
    }
  }

  function bindEvents() {
    const dropArea = $('drop-area');
    const fileInput = $('fileInput');
    const btnUpload = $('btnUpload');
    const btnRefresh = $('btnRefreshList');
    const btnRemoveFile = $('btnRemoveFile');

    if (dropArea) {
      ['dragenter', 'dragover'].forEach(evt => {
        dropArea.addEventListener(evt, e => {
          e.preventDefault();
          e.stopPropagation();
          dropArea.classList.add('drag-over');
        });
      });
      ['dragleave', 'drop', 'dragend'].forEach(evt => {
        dropArea.addEventListener(evt, e => {
          e.preventDefault();
          e.stopPropagation();
          if (evt === 'dragleave' && e.target !== dropArea) return;
          dropArea.classList.remove('drag-over');
        });
      });
      dropArea.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt && dt.files;
        if (files && files[0]) handleFileSelect(files[0]);
      });
      dropArea.addEventListener('click', () => {
        if (fileInput) fileInput.click();
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files[0]) {
          handleFileSelect(fileInput.files[0]);
        }
      });
    }

    if (btnUpload) {
      btnUpload.addEventListener('click', uploadFile);
    }

    if (btnRefresh) {
      btnRefresh.addEventListener('click', loadUploadHistory);
    }

    if (btnRemoveFile) {
      btnRemoveFile.addEventListener('click', clearSelection);
    }
  }

  function init() {
    const rawPath = (window.__ADMIN_PATH__ || '').trim();
    if (!rawPath) {
      try {
        const fromStorage = localStorage.getItem('ADMIN_SECRET_LAST');
        if (fromStorage && fromStorage.trim()) {
          console.warn('[admin] __ADMIN_PATH__ empty, fallback localStorage ADMIN_SECRET_LAST, redirect ke /admin/' + fromStorage);
          window.location.assign('/admin/' + encodeURIComponent(fromStorage.trim()));
          return;
        }
      } catch (_e) {}
      try {
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:99999;background:#7f1d1d;color:#fff;padding:14px 20px;border-radius:12px;font-weight:700;min-width:340px;max-width:92vw;box-shadow:0 20px 40px rgba(0,0,0,.25);border:1px solid #b91c1c;font-size:14px;line-height:1.5;';
        toast.innerHTML = '<div style="margin-bottom:6px;">⚠️ URL ADMIN TIDAK VALID (secret kosong)</div><div style="font-weight:500;font-size:13px;opacity:.98;">JANGAN buka /admin/ langsung tanpa secret.<br>Solusi mudah: <b style="color:#fde68a;">BUKA /admin</b> (login form baru) atau <b style="color:#fde68a;">/admin/&lt;ADMIN_SECRET&gt;</b> dengan nilai benar.<br>(<a href="/admin" style="color:#93c5fd;font-weight:700;text-decoration:underline;">Klik disini pindah ke halaman login Admin →</a>)</div>';
        document.body && document.body.appendChild(toast);
      } catch (_e) {}
      console.error('[admin] FATAL: window.__ADMIN_PATH__ TIDAK ADA / kosong. URL yang dibuka user BUKAN /admin/<secret>.');
      return;
    }
    if (!ADMIN_PATH) {
      // This block kept for safety; the rawPath check above is primary guard.
      console.warn('[admin] __ADMIN_PATH__ tidak terdeteksi.');
    }
    initIconPlaceholders();
    bindEvents();
    loadUploadHistory();
    const isPermanent = typeof window.__IS_PERMANENT_MODE__ !== 'undefined' && !!window.__IS_PERMANENT_MODE__;
    const bannerTemp = document.getElementById('vercelBannerNotice');
    const bannerPerm = document.getElementById('permanentBannerNotice');
    if (isPermanent) {
      if (bannerTemp) bannerTemp.style.display = 'none';
      if (bannerPerm) bannerPerm.style.display = 'block';
    } else {
      if (bannerPerm) bannerPerm.style.display = 'none';
      if (bannerTemp && typeof window.__IS_VERCEL__ !== 'undefined' && !!window.__IS_VERCEL__) {
        bannerTemp.style.display = 'block';
      } else if (bannerTemp) {
        bannerTemp.style.display = 'none';
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
