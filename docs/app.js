'use strict';

// ============================================================================
// Pure-JS SHA-256 (works identically on file://, localhost, and GitHub Pages)
// Matches Python's miku_bot/ship_logic.py byte-for-byte!
// ============================================================================

const SHIP_SALT = 'miku-discord-ship-v1';

function sha256Bytes(message) {
  const utf8 = new TextEncoder().encode(message);
  const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);
  let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
  let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;

  const bitLen = utf8.length * 8;
  const paddedLen = Math.ceil((utf8.length + 9) / 64) * 64;
  const buf = new Uint8Array(paddedLen);
  buf.set(utf8);
  buf[utf8.length] = 0x80;
  const view = new DataView(buf.buffer);
  view.setUint32(paddedLen - 8, Math.floor(bitLen / 0x100000000), false);
  view.setUint32(paddedLen - 4, bitLen >>> 0, false);

  const w = new Uint32Array(64);
  for (let offset = 0; offset < paddedLen; offset += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4, false);
    for (let i = 16; i < 64; i++) {
      const s0 = ((w[i - 15] >>> 7) | (w[i - 15] << 25)) ^ ((w[i - 15] >>> 18) | (w[i - 15] << 14)) ^ (w[i - 15] >>> 3);
      const s1 = ((w[i - 2] >>> 17) | (w[i - 2] << 15)) ^ ((w[i - 2] >>> 19) | (w[i - 2] << 13)) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;
    for (let i = 0; i < 64; i++) {
      const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
      const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      h = g; g = f; f = e; e = (d + temp1) >>> 0;
      d = c; c = b; b = a; a = (temp1 + temp2) >>> 0;
    }
    h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0; h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0;
  }
  return h0 >>> 0;
}

function normalizeShipKey(raw) {
  return raw.trim().replace(/\s+/g, ' ').toLowerCase().replace(/^@+/, '');
}

function formatDisplayName(raw) {
  const cleaned = raw.trim().replace(/\s+/g, ' ');
  if (!cleaned) return 'Nieznajomy';
  if (cleaned === cleaned.toLowerCase()) {
    return cleaned.split(' ').map((p) => (p ? p[0].toUpperCase() + p.slice(1) : '')).join(' ');
  }
  return cleaned;
}

function buildShipName(nameA, nameB) {
  const a = nameA.trim().replace(/\s+/g, '') || 'Mi';
  const b = nameB.trim().replace(/\s+/g, '') || 'Ku';
  const left = a.slice(0, Math.max(2, Math.floor((a.length + 1) / 2)));
  const right = b.slice(Math.floor(b.length / 2));
  const combined = (left + right).trim();
  if (!combined) return 'MikuShip';
  return combined[0].toUpperCase() + combined.slice(1).toLowerCase();
}

function shipComment(percent, isSelf) {
  if (isSelf) return 'Miłość do samego siebie też jest ważna… chyba.';
  if (percent >= 90) return 'To już niemal przeznaczenie… aż zrobiło mi się trochę ciepło.';
  if (percent >= 75) return 'Naprawdę świetnie do siebie pasujecie. Kibicuję Wam po cichu.';
  if (percent >= 55) return 'Jest tu wyraźna iskra — przy wspólnej playliście wyjdzie jeszcze lepiej.';
  if (percent >= 35) return 'Całkiem spokojna relacja. Dobre słuchawki i matcha potrafią zbliżyć.';
  if (percent >= 15) return 'Hmm… na razie raczej znajomi z jednego kanału, ale nigdy nie wiadomo.';
  return 'Oj… może lepiej zostać przy wspólnym słuchaniu muzyki.';
}

function calculateShip(rawA, rawB) {
  const nameA = formatDisplayName(rawA);
  const nameB = formatDisplayName(rawB);
  const keyA = normalizeShipKey(rawA);
  const keyB = normalizeShipKey(rawB);
  const isSelf = Boolean(keyA) && keyA === keyB;
  let percent = 100;
  if (!isSelf) {
    const ordered = [keyA, keyB].sort();
    const firstWord = sha256Bytes(`${SHIP_SALT}:${ordered[0]}\0${ordered[1]}`);
    percent = firstWord % 101;
  }
  return {
    nameA,
    nameB,
    percent,
    shipName: buildShipName(nameA, nameB),
    comment: shipComment(percent, isSelf),
  };
}

// ============================================================================
// UI Interactions: Overlay Menu, Command Filter, Copy Toast, Live Ship Lab
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  const menuOverlay = document.getElementById('menuOverlay');
  const menuOpenBtn = document.getElementById('menuOpenBtn');
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const menuCloseBtn = document.getElementById('menuCloseBtn');
  const toastEl = document.getElementById('toast');
  let toastTimer = null;

  function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2200);
  }

  function setMenu(open) {
    menuOverlay.classList.toggle('open', open);
    menuOverlay.setAttribute('aria-hidden', String(!open));
    menuOpenBtn.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  }

  menuOpenBtn.addEventListener('click', () => setMenu(!menuOverlay.classList.contains('open')));
  mobileMenuBtn.addEventListener('click', () => setMenu(true));
  menuCloseBtn.addEventListener('click', () => setMenu(false));
  menuOverlay.querySelectorAll('.menu-link').forEach((link) => {
    link.addEventListener('click', () => setMenu(false));
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && menuOverlay.classList.contains('open')) setMenu(false);
  });

  // Command category tabs
  const filterBtns = document.querySelectorAll('.filter-pill');
  const cmdCards = document.querySelectorAll('.cmd-card');
  filterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.filter;
      filterBtns.forEach((b) => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-selected', String(b === btn));
      });
      cmdCards.forEach((card) => {
        card.classList.toggle('hidden', target !== 'all' && card.dataset.cat !== target);
      });
    });
  });

  // Copy command helper
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast(`Skopiowano: ${text}`);
    } catch {
      showToast(`Komenda: ${text}`);
    }
  }

  document.querySelectorAll('.copy-btn').forEach((btn) => {
    btn.addEventListener('click', () => copyText(btn.dataset.copy || ''));
  });

  // Interactive Ship Lab
  const shipForm = document.getElementById('shipForm');
  const shipA = document.getElementById('shipA');
  const shipB = document.getElementById('shipB');
  const resNames = document.getElementById('resNames');
  const resBlend = document.getElementById('resBlend');
  const resBar = document.getElementById('resBar');
  const resPercent = document.getElementById('resPercent');
  const resComment = document.getElementById('resComment');
  const resCommand = document.getElementById('resCommand');
  const copyShipCmd = document.getElementById('copyShipCmd');

  function updateShipPreview() {
    const a = shipA.value.trim() || 'matizane';
    const b = shipB.value.trim() || 'Miku';
    const res = calculateShip(a, b);
    resNames.textContent = `${res.nameA} ♥ ${res.nameB}`;
    resBlend.textContent = `« ${res.shipName} »`;
    resPercent.textContent = `${res.percent}%`;
    resBar.style.width = `${Math.max(4, res.percent)}%`;
    resComment.textContent = res.comment;
    resCommand.textContent = `!s ${a} ${b}`;
  }

  shipForm.addEventListener('submit', (e) => {
    e.preventDefault();
    updateShipPreview();
  });
  copyShipCmd.addEventListener('click', () => copyText(resCommand.textContent));
  updateShipPreview();
});
