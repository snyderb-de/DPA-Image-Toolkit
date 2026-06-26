'use strict';

// ── State ─────────────────────────────────────────────────────────────────

const TOOLS = ['auto_crop', 'straighten_images', 'merge_tiffs', 'split_tiffs', 'add_border', 'ocr_pdf', 'pdf_conversion'];

const state = {};
TOOLS.forEach(id => {
  state[id] = {
    jobState: 'idle',   // idle | running | done
    path: null,
    fileCount: 0,
    es: null,           // EventSource
    errorFolder: null,
    hasErrors: false,
  };
});

// Split TIFFs extra
state.split_tiffs.mode = 'folder';      // folder | files
state.split_tiffs.files = [];

// PDF Conversion extra
state.pdf_conversion.operation = 'reduce_size';
state.pdf_conversion.inputMode  = 'file';   // file | folder (reduce_size only)

// ── Boot ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNav();
  loadCompressionProfiles();
  loadPdfaProfiles();
  loadUpdateSettings();
  TOOLS.forEach(id => log(id, 'Ready — select an input to begin.', 'info'));

  setPdfInputMode(state.pdf_conversion.inputMode);
});

// ── Theme ─────────────────────────────────────────────────────────────────

const THEME_KEY = 'dpa-toolkit-theme';

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'dark';
  applyTheme(saved, false);
}

function setTheme(t) {
  applyTheme(t, true);
}

function applyTheme(t, save) {
  document.documentElement.setAttribute('data-theme', t);
  document.getElementById('theme-dark').classList.toggle('active', t === 'dark');
  document.getElementById('theme-light').classList.toggle('active', t === 'light');
  if (save) {
    localStorage.setItem(THEME_KEY, t);
    fetch('/api/settings', {
      method: 'POST',
      body: JSON.stringify({ appearance_mode: t }),
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// ── Navigation ────────────────────────────────────────────────────────────

function initNav() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => switchTool(item.dataset.tool));
  });
}

function switchTool(toolId) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tool-panel').forEach(el => el.classList.remove('active'));
  document.querySelector(`.nav-item[data-tool="${toolId}"]`).classList.add('active');
  document.getElementById(`panel-${toolId}`).classList.add('active');
}

function setNavState(toolId, st) {
  const dot = document.getElementById(`nav-state-${toolId}`);
  if (!dot) return;
  dot.className = 'nav-state';
  if (st === 'running') dot.classList.add('running');
  else if (st === 'done') dot.classList.add('done');
  else if (st === 'error') dot.classList.add('error');
}

// ── Folder / file pickers ─────────────────────────────────────────────────

async function pickFolder(toolId) {
  const s = state[toolId];
  const res = await api('/api/pick-folder', { title: 'Select Folder', initial_dir: s.path || null });
  if (!res.path) return;

  const prepRes = await api(`/api/${toolId}/prepare`, { folder: res.path });
  if (!prepRes.ok) { setBanner(toolId, prepRes.error || 'Invalid folder', 'error'); return; }

  s.path = res.path;
  setPathDisplay(toolId, res.path);

  if (toolId === 'merge_tiffs') {
    const groups = prepRes.group_count;
    s.fileCount = groups;
    setCount(toolId, `${groups} group${groups !== 1 ? 's' : ''}`);
    if (prepRes.warnings && prepRes.warnings.length) {
      setBanner(toolId, `Found ${groups} TIFF group(s). Warnings: ${prepRes.warnings.length}`, 'warn');
      prepRes.warnings.forEach(w => log(toolId, w, 'warning'));
    } else {
      setBanner(toolId, `Found ${groups} TIFF merge group(s) — click Start to merge.`, 'ok');
    }
  } else if (toolId === 'ocr_pdf') {
    s.fileCount = prepRes.document_count;
    setCount(toolId, `${prepRes.document_count} doc${prepRes.document_count !== 1 ? 's' : ''}, ${prepRes.page_count} pages`);
    setBanner(toolId, `Found ${prepRes.document_count} document group(s), ${prepRes.page_count} pages — click Start to run OCR.`, 'ok');
  } else {
    s.fileCount = prepRes.file_count;
    setCount(toolId, `${prepRes.file_count} file${prepRes.file_count !== 1 ? 's' : ''}`);
    setBanner(toolId, `Found ${prepRes.file_count} file(s) — click Start to begin.`, 'ok');
  }

  log(toolId, `Folder: ${res.path}`, 'info');
  log(toolId, toolId === 'merge_tiffs'
    ? `Found ${prepRes.group_count} merge group(s).`
    : toolId === 'ocr_pdf'
      ? `Found ${prepRes.document_count} document(s), ${prepRes.page_count} total pages.`
      : `Found ${prepRes.file_count} file(s).`, 'success');

  enableStart(toolId);
}

async function pickSplit() {
  const s = state.split_tiffs;
  if (s.mode === 'folder') {
    const res = await api('/api/pick-folder', { title: 'Select TIFF Folder' });
    if (!res.path) return;
    const prepRes = await api('/api/split_tiffs/prepare', { mode: 'folder', folder: res.path });
    if (!prepRes.ok) { setBanner('split_tiffs', prepRes.error || 'Invalid folder', 'error'); return; }
    s.path = res.path;
    setPathDisplay('split_tiffs', res.path);
    setCount('split_tiffs', `${prepRes.file_count} TIFFs`);
    setBanner('split_tiffs', `Found ${prepRes.file_count} TIFF file(s) — click Start to split.`, 'ok');
    log('split_tiffs', `Folder: ${res.path} — ${prepRes.file_count} files`, 'success');
  } else {
    const res = await api('/api/pick-files', {
      title: 'Select TIFF Files',
      filetypes: [['TIFF Files', '*.tif *.tiff'], ['All Files', '*.*']],
    });
    if (!res.paths || !res.paths.length) return;
    s.files = res.paths;
    const prepRes = await api('/api/split_tiffs/prepare', { mode: 'files', files: res.paths });
    if (!prepRes.ok) { setBanner('split_tiffs', prepRes.error || 'Invalid files', 'error'); return; }
    setPathDisplay('split_tiffs', `${res.paths.length} file(s) selected`);
    setCount('split_tiffs', `${prepRes.file_count} TIFFs`);
    setBanner('split_tiffs', `${prepRes.file_count} TIFF file(s) ready — click Start to split.`, 'ok');
    log('split_tiffs', `${prepRes.file_count} files selected`, 'success');
  }
  enableStart('split_tiffs');
}

async function pickPdf() {
  const s = state.pdf_conversion;
  const op = s.operation;
  const useFolder = op === 'reduce_size' && s.inputMode === 'folder';

  if (useFolder) {
    const res = await api('/api/pick-folder', { title: 'Select PDF Folder' });
    if (!res.path) return;
    const prepRes = await api('/api/pdf_conversion/prepare', { path: res.path, mode: 'folder', operation: op });
    if (!prepRes.ok) { setBanner('pdf_conversion', prepRes.error || 'Invalid folder', 'error'); return; }
    s.path = res.path;
    setPathDisplay('pdf_conversion', res.path);
    setCount('pdf_conversion', `${prepRes.file_count} PDFs`);
    setBanner('pdf_conversion', `Found ${prepRes.file_count} PDF(s) — click Start.`, 'ok');
    log('pdf_conversion', `Folder: ${res.path} — ${prepRes.file_count} PDFs`, 'success');
  } else {
    const res = await api('/api/pick-files', {
      title: 'Select PDF File',
      filetypes: [['PDF Files', '*.pdf'], ['All Files', '*.*']],
    });
    if (!res.paths || !res.paths.length) return;
    const filePath = res.paths[0];
    const prepRes = await api('/api/pdf_conversion/prepare', { path: filePath, mode: 'file', operation: op });
    if (!prepRes.ok) { setBanner('pdf_conversion', prepRes.error || 'Invalid PDF', 'error'); return; }
    s.path = filePath;
    setPathDisplay('pdf_conversion', filePath);
    const fname = filePath.split(/[/\\]/).pop();
    setCount('pdf_conversion', fname);
    setBanner('pdf_conversion', `${fname} selected — click Start.`, 'ok');
    log('pdf_conversion', `File: ${filePath}`, 'success');
  }
  enableStart('pdf_conversion');
}

// ── Split mode ────────────────────────────────────────────────────────────

function setSplitMode(mode) {
  state.split_tiffs.mode = mode;
  state.split_tiffs.files = [];
  state.split_tiffs.path = null;
  document.getElementById('mode-btn-folder').classList.toggle('active', mode === 'folder');
  document.getElementById('mode-btn-files').classList.toggle('active', mode === 'files');
  const btn = document.getElementById('pick-btn-split');
  btn.textContent = mode === 'folder' ? '📁 Select Folder' : '📄 Select Files';
  setPathDisplay('split_tiffs', 'No selection');
  setCount('split_tiffs', null);
  disableStart('split_tiffs');
  setBanner('split_tiffs', 'Select a ' + (mode === 'folder' ? 'folder' : 'file(s)') + ' to begin.');
}

// ── PDF operation ─────────────────────────────────────────────────────────

function setPdfInputMode(mode) {
  const s = state.pdf_conversion;
  s.inputMode = mode === 'folder' ? 'folder' : 'file';
  s.path = null;
  document.getElementById('pdf-mode-file').classList.toggle('active', s.inputMode === 'file');
  document.getElementById('pdf-mode-folder').classList.toggle('active', s.inputMode === 'folder');
  const btn = document.getElementById('pick-btn-pdf');
  btn.textContent = s.inputMode === 'folder' ? '📁 Select Folder' : '📄 Select PDF';
  setPathDisplay('pdf_conversion', s.inputMode === 'folder' ? 'No folder selected' : 'No file selected');
  setCount('pdf_conversion', null);
  disableStart('pdf_conversion');
  setBanner('pdf_conversion', s.inputMode === 'folder' ? 'Select a PDF folder to begin.' : 'Select a PDF to begin.');
}

function setPdfOp(op) {
  state.pdf_conversion.operation = op;
  state.pdf_conversion.path = null;
  document.querySelectorAll('.op-btn').forEach(b => b.classList.toggle('active', b.dataset.op === op));

  const labels = { reduce_size: 'Input', split_pdf: 'PDF File', extract_pages: 'PDF File', pdfa: 'PDF File' };
  document.getElementById('pdf-pick-label').textContent = labels[op] || 'Input';

  const modeToggle = document.getElementById('pdf-input-mode-toggle');
  modeToggle.style.display = op === 'reduce_size' ? '' : 'none';
  if (op !== 'reduce_size') {
    state.pdf_conversion.inputMode = 'file';
  }

  ['reduce', 'split', 'extract', 'pdfa'].forEach(k => {
    const el = document.getElementById(`pdf-opts-${k}`);
    if (el) el.classList.add('hidden');
  });
  const opMap = { reduce_size: 'reduce', split_pdf: 'split', extract_pages: 'extract', pdfa: 'pdfa' };
  const el = document.getElementById(`pdf-opts-${opMap[op]}`);
  if (el) el.classList.remove('hidden');

  setPdfInputMode(state.pdf_conversion.inputMode);
}

// ── Start / Cancel / Reset ────────────────────────────────────────────────

async function startTool(toolId) {
  const s = state[toolId];
  if (s.jobState === 'running') return;

  let body = {};

  if (toolId === 'auto_crop') {
    body = {
      straighten: document.getElementById('opt-auto-straighten').checked,
    };
  } else if (toolId === 'ocr_pdf') {
    body = {
      skip_existing: document.getElementById('opt-skip-existing').checked,
      skip_messy:    document.getElementById('opt-quality-check').checked,
      reduce_size:   document.getElementById('opt-reduce-pdf').checked,
      compression_profile: document.getElementById('sel-ocr-compression').value,
    };
  } else if (toolId === 'pdf_conversion') {
    const op = s.operation;
    body = {
      reduce_size:          document.getElementById('opt-pdf-reduce').checked,
      compression_profile:  document.getElementById('sel-pdf-compression').value,
      split_output_type:    document.getElementById('sel-split-format').value,
      extract_page_spec:    document.getElementById('inp-page-spec').value,
      write_remaining_pages: document.getElementById('opt-write-remaining-pages').checked,
      pdfa_profile:         document.getElementById('sel-pdfa-profile').value,
    };
  }

  const res = await api(`/api/${toolId}/start`, body);
  if (!res.ok) { setBanner(toolId, res.error || 'Failed to start', 'error'); return; }

  s.jobState = 'running';
  s.hasErrors = false;
  setNavState(toolId, 'running');
  setBanner(toolId, 'Running…', 'info');
  setProgress(toolId, 0, 'Starting…');
  showProgress(toolId, true);
  setBtn(toolId, 'start', true, '⏳ Running…');
  setBtn(toolId, 'cancel', false);
  setBtn(toolId, 'err', true);
  log(toolId, 'Job started.', 'success');

  openStream(toolId);
}

async function cancelTool(toolId) {
  const res = await api(`/api/${toolId}/cancel`, { force: false });
  if (res.ok) {
    log(toolId, 'Cancellation requested — finishing current file.', 'warning');
    setBanner(toolId, 'Cancelling — waiting for current file to finish.', 'warn');
  }
}

async function resetTool(toolId) {
  const s = state[toolId];
  if (s.jobState === 'running') return;
  closeStream(toolId);
  await api(`/api/${toolId}/reset`, {});
  s.jobState = 'idle';
  s.path = null;
  s.fileCount = 0;
  s.errorFolder = null;
  s.hasErrors = false;
  setPathDisplay(toolId, toolId === 'pdf_conversion' ? 'No file selected' : 'No folder selected');
  setCount(toolId, null);
  showProgress(toolId, false);
  setProgress(toolId, 0, '');
  clearLog(toolId);
  setBanner(toolId, 'Select an input to begin.');
  disableStart(toolId);
  setBtn(toolId, 'start', false, '▶ Start');
  setBtn(toolId, 'cancel', true);
  setBtn(toolId, 'err', true);
  setNavState(toolId, 'idle');
  log(toolId, 'Ready — select an input to begin.', 'info');
  if (toolId === 'split_tiffs') {
    state.split_tiffs.files = [];
  }
  if (toolId === 'pdf_conversion') {
    setPdfInputMode(state.pdf_conversion.inputMode);
  }
}

// ── SSE stream ────────────────────────────────────────────────────────────

function openStream(toolId) {
  closeStream(toolId);
  const es = new EventSource(`/api/${toolId}/stream`);
  state[toolId].es = es;

  es.onmessage = e => {
    let evt;
    try { evt = JSON.parse(e.data); } catch { return; }
    handleEvent(toolId, evt);
  };

  es.onerror = () => {
    log(toolId, 'Stream connection lost.', 'warning');
    closeStream(toolId);
  };
}

function closeStream(toolId) {
  if (state[toolId].es) {
    state[toolId].es.close();
    state[toolId].es = null;
  }
}

function handleEvent(toolId, evt) {
  switch (evt.type) {
    case 'progress': {
      const pct = evt.percentage != null ? evt.percentage : (evt.pdf_percent ?? 0);
      const label = evt.filename || evt.message || '';
      setProgress(toolId, pct, label);
      if (toolId === 'ocr_pdf') {
        setProgressFill(`prog-fill-ocr_pdf`, pct);
        setProgressMeta(`prog-label-ocr_pdf`, `prog-pct-ocr_pdf`, label, pct);
        if (evt.job_percent != null) {
          const jobLabel = `PDF ${evt.current_pdf ?? ''}/${evt.total_pdfs ?? ''}`;
          setProgressFill(`prog-job-fill-ocr_pdf`, evt.job_percent);
          setProgressMeta(`prog-job-label-ocr_pdf`, `prog-job-pct-ocr_pdf`, jobLabel, evt.job_percent);
        }
      }
      break;
    }
    case 'status':
      log(toolId, evt.message, 'info');
      setBanner(toolId, evt.message, 'info');
      break;
    case 'error':
      state[toolId].hasErrors = true;
      log(toolId, `${evt.file}: ${evt.message}`, 'error');
      setBtn(toolId, 'err', false);
      setNavState(toolId, 'error');
      break;
    case 'done':
      onJobDone(toolId, evt.results);
      break;
    case 'end':
    case 'ping':
      break;
  }
}

function onJobDone(toolId, results) {
  closeStream(toolId);
  state[toolId].jobState = 'done';

  const r = results || {};
  const cancelled = r.cancelled;
  const success = r.success ?? 0;
  const failed  = r.failed ?? 0;
  const skipped = r.skipped ?? 0;

  const level = (failed > 0 || state[toolId].hasErrors) ? 'warn' : 'ok';
  const msg = cancelled
    ? `Cancelled — ${success} completed, ${skipped} skipped, ${failed} failed`
    : `Done — ${success} completed, ${skipped} skipped, ${failed} failed`;

  setBanner(toolId, msg, level);
  setProgress(toolId, 100, msg);
  setProgressActive(toolId, false);
  log(toolId, msg, level === 'ok' ? 'success' : 'warning');
  setNavState(toolId, failed > 0 ? 'error' : 'done');

  setBtn(toolId, 'start', false, '▶ Start');
  setBtn(toolId, 'cancel', true);
}

// ── Progress helpers ──────────────────────────────────────────────────────

function showProgress(toolId, show) {
  const el = document.getElementById(`prog-${toolId}`);
  if (el) el.classList.toggle('hidden', !show);
}

function setProgress(toolId, pct, label) {
  setProgressFill(`prog-fill-${toolId}`, pct);
  setProgressMeta(`prog-label-${toolId}`, `prog-pct-${toolId}`, label, pct);
}

function setProgressFill(fillId, pct) {
  const el = document.getElementById(fillId);
  if (!el) return;
  const clamped = Math.min(100, Math.max(0, pct));
  el.style.width = clamped + '%';
  el.classList.toggle('active', clamped > 0 && clamped < 100);
}

function setProgressMeta(labelId, pctId, label, pct) {
  const lEl = document.getElementById(labelId);
  const pEl = document.getElementById(pctId);
  if (lEl) lEl.textContent = label || '';
  if (pEl) pEl.textContent = Math.round(pct) + '%';
}

function setProgressActive(toolId, active) {
  const fill = document.getElementById(`prog-fill-${toolId}`);
  if (fill) fill.classList.toggle('active', active);
}

// ── UI helpers ────────────────────────────────────────────────────────────

function setPathDisplay(toolId, text) {
  const el = document.getElementById(`path-${toolId}`);
  if (!el) return;
  el.textContent = text || '';
  el.classList.toggle('has-path', !!(text && text !== 'No folder selected' && text !== 'No file selected' && text !== 'No selection'));
}

function setCount(toolId, text) {
  const el = document.getElementById(`count-${toolId}`);
  if (!el) return;
  if (text) {
    el.textContent = text;
    el.style.display = '';
  } else {
    el.style.display = 'none';
  }
}

function setBanner(toolId, text, level) {
  const el = document.getElementById(`banner-${toolId}`);
  if (!el) return;
  el.textContent = text;
  el.className = 'status-banner';
  if (level === 'ok')    el.classList.add('ok');
  if (level === 'warn')  el.classList.add('warn');
  if (level === 'error') el.classList.add('error');
}

function enableStart(toolId) {
  setBtn(toolId, 'start', false, '▶ Start');
}

function disableStart(toolId) {
  setBtn(toolId, 'start', true, '▶ Start');
}

function setBtn(toolId, which, disabled, text) {
  const el = document.getElementById(`btn-${which}-${toolId}`);
  if (!el) return;
  el.disabled = disabled;
  if (text !== undefined) el.textContent = text;
}

// ── Log ───────────────────────────────────────────────────────────────────

const prefixes = { info: '·', success: '✓', warning: '⚠', error: '✕' };

function log(toolId, message, level) {
  const body = document.getElementById(`log-${toolId}`);
  if (!body) return;
  const line = document.createElement('div');
  line.className = `log-line ${level || 'info'}`;
  const pre = document.createElement('span');
  pre.className = 'log-prefix';
  pre.textContent = prefixes[level] || '·';
  const txt = document.createElement('span');
  txt.className = 'log-text';
  txt.textContent = message;
  line.appendChild(pre);
  line.appendChild(txt);
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

function clearLog(toolId) {
  const el = document.getElementById(`log-${toolId}`);
  if (el) el.textContent = '';
}

// ── Error folder opener ───────────────────────────────────────────────────

async function openErrorFolder(toolId) {
  const res = await api(`/api/${toolId}/open-errors`, {});
  if (res.ok) {
    log(toolId, `Opened error folder: ${res.path}`, 'success');
  } else {
    log(toolId, res.error || 'Could not open error folder.', 'warning');
  }
}

// ── Updates ───────────────────────────────────────────────────────────────

async function loadUpdateSettings() {
  try {
    const res = await fetch('/api/updates/settings');
    const data = await res.json();
    const pathEl = document.getElementById('update-source-path');
    const checkEl = document.getElementById('opt-check-updates-on-start');
    const versionEl = document.getElementById('update-current-version');
    const exeEl = document.getElementById('update-exe-name');

    if (pathEl) pathEl.value = data.update_source_path || '';
    if (checkEl) checkEl.checked = !!data.check_updates_on_start;
    if (versionEl) versionEl.textContent = data.current_version || 'Unknown';
    if (exeEl) exeEl.textContent = data.exe_filename || 'DPA-Image-Toolkit.exe';

    if (data.check_updates_on_start && data.update_source_path) {
      setTimeout(() => checkForUpdates(true), 500);
    }
  } catch (e) {
    setUpdateStatus('Could not load update settings.', 'error');
  }
}

async function saveUpdateSettings() {
  const pathEl = document.getElementById('update-source-path');
  const checkEl = document.getElementById('opt-check-updates-on-start');
  const res = await api('/api/updates/settings', {
    update_source_path: pathEl ? pathEl.value : '',
    check_updates_on_start: checkEl ? checkEl.checked : false,
  });

  if (res.ok) {
    setUpdateStatus('Update settings saved.', 'ok');
  } else {
    setUpdateStatus(res.error || 'Could not save update settings.', 'error');
  }
}

async function browseUpdateExe() {
  const pathEl = document.getElementById('update-source-path');
  const res = await api('/api/updates/pick-exe', {
    initial_dir: pathEl ? pathEl.value : null,
  });
  if (res.path && pathEl) {
    pathEl.value = res.path;
    setUpdateStatus('Update source selected.', 'ok');
  }
}

async function checkForUpdates(auto) {
  const btn = document.getElementById('btn-check-updates');
  const pathEl = document.getElementById('update-source-path');
  const sourcePath = pathEl ? pathEl.value : '';

  if (!auto && btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Checking…';
  }

  const res = await api('/api/updates/check', { update_source_path: sourcePath });
  renderUpdateResult(res, auto);

  if (!auto && btn) {
    btn.disabled = false;
    btn.textContent = '⇧ Check for Updates';
  }
}

function renderUpdateResult(res, auto) {
  if (res.ok && res.state === 'available') {
    setUpdateStatus(`Update available: ${res.candidate_version} (current ${res.current_version})`, 'warn');
    return;
  }
  if (res.ok && res.state === 'current') {
    setUpdateStatus(`Current: ${res.current_version}`, 'ok');
    return;
  }
  if (auto && res.state === 'not_configured') return;
  setUpdateStatus(res.message || 'Update check failed.', 'error');
}

async function openUpdateLocation() {
  const pathEl = document.getElementById('update-source-path');
  const res = await api('/api/updates/open-location', {
    update_source_path: pathEl ? pathEl.value : '',
  });
  if (res.ok) {
    setUpdateStatus(`Opened: ${res.path}`, 'ok');
  } else {
    setUpdateStatus(res.error || 'Could not open update location.', 'error');
  }
}

function setUpdateStatus(text, level) {
  const el = document.getElementById('update-status');
  if (!el) return;
  el.textContent = text;
  el.className = 'status-banner';
  if (level === 'ok')    el.classList.add('ok');
  if (level === 'warn')  el.classList.add('warn');
  if (level === 'error') el.classList.add('error');
}

// ── API ───────────────────────────────────────────────────────────────────

async function api(url, body) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  } catch (e) {
    console.error('API error:', url, e);
    return { ok: false, error: 'Network error' };
  }
}

// ── Compression profiles ──────────────────────────────────────────────────

async function loadCompressionProfiles() {
  try {
    const res = await fetch('/api/compression-profiles');
    const data = await res.json();
    ['sel-ocr-compression', 'sel-pdf-compression'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      data.keys.forEach(key => {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = data.labels[key] || key;
        if (key === data.default) opt.selected = true;
        el.appendChild(opt);
      });
    });
  } catch (e) {
    console.warn('Could not load compression profiles:', e);
  }
}

async function loadPdfaProfiles() {
  try {
    const res = await fetch('/api/pdfa-profiles');
    const data = await res.json();
    const el = document.getElementById('sel-pdfa-profile');
    if (!el) return;
    data.labels.forEach(label => {
      const opt = document.createElement('option');
      opt.value = label;
      opt.textContent = label;
      if (label === data.default) opt.selected = true;
      el.appendChild(opt);
    });
  } catch (e) {
    console.warn('Could not load PDF/A profiles:', e);
  }
}
