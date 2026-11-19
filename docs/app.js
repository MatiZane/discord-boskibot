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

  // ============================================================================
  // Living Anime Sky Canvas:
  // - 3 parallax layers of fluffy sunlit cumulus clouds gliding across the sky
  // - Soft blurred cloud-mist ribbon trailing the cursor + gentle ripples
  // - Floating 5-color petals & musical notes swept by the cursor cloud wake
  // ============================================================================
  const hero = document.getElementById('top');
  const canvas = document.getElementById('heroCanvas');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (hero && canvas && !reducedMotion) {
    const ctx = canvas.getContext('2d');
    const palette = ['#F5C52B', '#B465DA', '#38B6F0', '#7ED046', '#FF6EA8'];
    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    const clouds = [];
    const cloudTrail = [];
    const ripples = [];
    const bursts = [];
    const petals = [];
    const mouse = {
      x: -999,
      y: -999,
      smoothX: -999,
      smoothY: -999,
      prevX: -999,
      prevY: -999,
      nx: 0,
      ny: 0,
      active: false,
      lastRippleAt: 0,
      lastPuffAt: 0,
    };

    // Pre-render a soft glowing cloud-puff sprite once (ultra-fast 60fps stamping!)
    function makePuffSprite(size, innerAlpha, tintRgb) {
      const c = document.createElement('canvas');
      c.width = size;
      c.height = size;
      const g = c.getContext('2d');
      const r = size / 2;
      const grad = g.createRadialGradient(r, r * 0.92, r * 0.08, r, r, r);
      grad.addColorStop(0, `rgba(${tintRgb}, ${innerAlpha})`);
      grad.addColorStop(0.42, `rgba(${tintRgb}, ${innerAlpha * 0.62})`);
      grad.addColorStop(0.75, `rgba(${tintRgb}, ${innerAlpha * 0.2})`);
      grad.addColorStop(1, `rgba(${tintRgb}, 0)`);
      g.fillStyle = grad;
      g.fillRect(0, 0, size, size);
      return c;
    }

    // Pre-render fluffy multi-lobe anime cumulus cloud sprite
    function makeCloudSprite(variant) {
      const cw = 460;
      const ch = 220;
      const c = document.createElement('canvas');
      c.width = cw;
      c.height = ch;
      const g = c.getContext('2d');

      const puffWhite = makePuffSprite(180, 0.86, '255, 255, 255');
      const puffUnder = makePuffSprite(180, 0.42, '182, 224, 252');

      const layouts = [
        [
          { x: 0.25, y: 0.62, s: 0.72 },
          { x: 0.42, y: 0.46, s: 0.95 },
          { x: 0.58, y: 0.52, s: 0.88 },
          { x: 0.73, y: 0.64, s: 0.68 },
          { x: 0.49, y: 0.66, s: 0.82 },
        ],
        [
          { x: 0.22, y: 0.65, s: 0.65 },
          { x: 0.36, y: 0.54, s: 0.85 },
          { x: 0.54, y: 0.44, s: 1.0 },
          { x: 0.70, y: 0.56, s: 0.82 },
          { x: 0.80, y: 0.68, s: 0.58 },
        ],
        [
          { x: 0.28, y: 0.58, s: 0.80 },
          { x: 0.48, y: 0.48, s: 0.94 },
          { x: 0.66, y: 0.58, s: 0.78 },
          { x: 0.47, y: 0.68, s: 0.84 },
        ],
      ];
      const lobes = layouts[variant % layouts.length];

      // Soft sky-blue underside shadow first
      for (const l of lobes) {
        const d = 150 * l.s;
        g.drawImage(puffUnder, cw * l.x - d / 2, ch * (l.y + 0.08) - d / 2, d, d * 0.78);
      }
      // Bright sunlit white cloud puffs on top
      for (const l of lobes) {
        const d = 150 * l.s;
        g.drawImage(puffWhite, cw * l.x - d / 2, ch * l.y - d / 2, d, d * 0.82);
      }
      return c;
    }

    const cloudSprites = [makeCloudSprite(0), makeCloudSprite(1), makeCloudSprite(2)];
    const trailSpriteWhite = makePuffSprite(160, 0.52, '255, 255, 255');
    const trailSpriteMist = makePuffSprite(160, 0.38, '214, 242, 255');

    function resize() {
      const rect = hero.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function seedSky() {
      clouds.length = 0;
      const cloudCount = width < 700 ? 6 : 10;
      for (let i = 0; i < cloudCount; i++) {
        const layer = i % 3; // 0 = far/slow, 1 = mid, 2 = near/faster
        const scale = (layer === 0 ? 0.58 : layer === 1 ? 0.86 : 1.18) * (0.85 + Math.random() * 0.3);
        clouds.push({
          sprite: cloudSprites[i % cloudSprites.length],
          x: Math.random() * (width + 420) - 210,
          y: height * (layer === 0 ? 0.06 + Math.random() * 0.35 : layer === 1 ? 0.16 + Math.random() * 0.45 : 0.44 + Math.random() * 0.42),
          scale,
          speed: (layer === 0 ? 0.14 : layer === 1 ? 0.28 : 0.46) * (0.8 + Math.random() * 0.45),
          alpha: layer === 0 ? 0.46 : layer === 1 ? 0.68 : 0.82,
          parallax: layer === 0 ? 10 : layer === 1 ? 22 : 36,
          bobPhase: Math.random() * Math.PI * 2,
        });
      }

      petals.length = 0;
      const count = width < 700 ? 14 : 24;
      for (let i = 0; i < count; i++) {
        petals.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: 0.12 + Math.random() * 0.35,
          vy: 0.18 + Math.random() * 0.36,
          size: 5 + Math.random() * 5.5,
          angle: Math.random() * Math.PI * 2,
          spin: (Math.random() - 0.5) * 0.025,
          color: palette[i % palette.length],
          note: i % 5 === 0,
        });
      }
    }

    function spawnCloudPuff(x, y, vx, vy, big = false) {
      const jitterX = (Math.random() - 0.5) * (big ? 28 : 14);
      const jitterY = (Math.random() - 0.5) * (big ? 24 : 14);
      cloudTrail.push({
        x: x + jitterX,
        y: y + jitterY,
        vx: vx * 0.16 + (Math.random() - 0.5) * 0.45,
        vy: vy * 0.16 - 0.18 - Math.random() * 0.25,
        size: big ? 84 + Math.random() * 44 : 58 + Math.random() * 34,
        grow: big ? 1.35 : 0.85,
        alpha: big ? 0.72 : 0.48,
        fade: big ? 0.011 : 0.013,
        sprite: Math.random() > 0.38 ? trailSpriteWhite : trailSpriteMist,
      });
      if (cloudTrail.length > 52) cloudTrail.splice(0, cloudTrail.length - 52);
    }

    function spawnRipple(x, y, strong = false) {
      ripples.push({
        x,
        y,
        r: strong ? 10 : 6,
        maxR: strong ? 148 : 84,
        alpha: strong ? 0.5 : 0.28,
        speed: strong ? 2.3 : 1.65,
        tint: strong ? '#ffffff' : '#d8f4ff',
      });
      if (strong) {
        ripples.push({
          x,
          y,
          r: 2,
          maxR: 102,
          alpha: 0.4,
          speed: 1.45,
          tint: '#ffcee2',
        });
        for (let i = 0; i < 6; i++) {
          const ang = (Math.PI * 2 * i) / 6 + Math.random() * 0.4;
          spawnCloudPuff(x, y, Math.cos(ang) * 5, Math.sin(ang) * 5, true);
        }
        for (let i = 0; i < 8; i++) {
          const ang = (Math.PI * 2 * i) / 8 + Math.random() * 0.3;
          const spd = 1.2 + Math.random() * 2.1;
          bursts.push({
            x,
            y,
            vx: Math.cos(ang) * spd,
            vy: Math.sin(ang) * spd - 0.5,
            alpha: 0.95,
            size: 4 + Math.random() * 4,
            color: palette[i % palette.length],
            symbol: i % 2 === 0 ? '♪' : '✿',
          });
        }
      }
      if (ripples.length > 26) ripples.splice(0, ripples.length - 26);
    }

    hero.addEventListener('pointermove', (e) => {
      const rect = hero.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const dx = mouse.active ? x - mouse.prevX : 0;
      const dy = mouse.active ? y - mouse.prevY : 0;
      mouse.prevX = x;
      mouse.prevY = y;
      mouse.x = x;
      mouse.y = y;
      if (!mouse.active) {
        mouse.smoothX = x;
        mouse.smoothY = y;
      }
      mouse.nx = (x / Math.max(1, width) - 0.5) * 2;
      mouse.ny = (y / Math.max(1, height) - 0.5) * 2;
      mouse.active = true;

      const now = performance.now();
      const speed = Math.hypot(dx, dy);
      if (now - mouse.lastPuffAt > 24 && speed > 1.5) {
        spawnCloudPuff(x, y, dx, dy, false);
        mouse.lastPuffAt = now;
      }
      if (now - mouse.lastRippleAt > 110 && speed > 4) {
        spawnRipple(x, y, false);
        mouse.lastRippleAt = now;
      }
    });

    hero.addEventListener('pointerleave', () => {
      mouse.active = false;
    });

    hero.addEventListener('pointerdown', (e) => {
      const rect = hero.getBoundingClientRect();
      spawnRipple(e.clientX - rect.left, e.clientY - rect.top, true);
    });

    resize();
    seedSky();
    window.addEventListener('resize', () => {
      resize();
      seedSky();
    });

    let rafId = 0;
    let tick = 0;
    function frame() {
      tick += 0.012;
      ctx.clearRect(0, 0, width, height);

      // Smooth cursor easing for subtle sky parallax + soft mist halo
      if (mouse.active) {
        mouse.smoothX += (mouse.x - mouse.smoothX) * 0.14;
        mouse.smoothY += (mouse.y - mouse.smoothY) * 0.14;
      } else {
        mouse.nx *= 0.96;
        mouse.ny *= 0.96;
      }

      // 1. Drifting multi-layer anime cumulus clouds
      for (const cl of clouds) {
        cl.x += cl.speed;
        const drawW = cl.sprite.width * cl.scale;
        const drawH = cl.sprite.height * cl.scale;
        if (cl.x - drawW / 2 > width + 80) {
          cl.x = -drawW / 2 - 40;
        }
        const px = cl.x - mouse.nx * cl.parallax;
        const py = cl.y - mouse.ny * (cl.parallax * 0.45) + Math.sin(tick + cl.bobPhase) * 5;
        ctx.save();
        ctx.globalAlpha = cl.alpha;
        ctx.drawImage(cl.sprite, px - drawW / 2, py - drawH / 2, drawW, drawH);
        ctx.restore();
      }

      // 2. Silky blurred cloud-mist ribbon trailing the cursor
      for (let i = cloudTrail.length - 1; i >= 0; i--) {
        const pf = cloudTrail[i];
        pf.x += pf.vx;
        pf.y += pf.vy;
        pf.vx *= 0.95;
        pf.vy *= 0.96;
        pf.size += pf.grow;
        pf.alpha -= pf.fade;
        if (pf.alpha <= 0.01) {
          cloudTrail.splice(i, 1);
          continue;
        }
        ctx.save();
        ctx.globalAlpha = pf.alpha;
        ctx.drawImage(pf.sprite, pf.x - pf.size / 2, pf.y - pf.size / 2, pf.size, pf.size * 0.84);
        ctx.restore();
      }

      // Soft warm cloud halo directly beneath smoothed cursor
      if (mouse.active) {
        ctx.save();
        ctx.globalAlpha = 0.48;
        ctx.drawImage(trailSpriteWhite, mouse.smoothX - 78, mouse.smoothY - 68, 156, 136);
        ctx.restore();
      }

      // 3. Expanding water/air ripples
      for (let i = ripples.length - 1; i >= 0; i--) {
        const rp = ripples[i];
        rp.r += rp.speed;
        const progress = rp.r / rp.maxR;
        const a = rp.alpha * (1 - progress);
        if (progress >= 1 || a <= 0.01) {
          ripples.splice(i, 1);
          continue;
        }
        ctx.save();
        ctx.globalAlpha = a;
        ctx.strokeStyle = rp.tint;
        ctx.lineWidth = Math.max(1, 2.4 * (1 - progress));
        ctx.beginPath();
        ctx.arc(rp.x, rp.y, rp.r, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      // 4. Drifting 5-color petals & musical notes gently swept by cursor cloud wake
      for (const p of petals) {
        if (mouse.active) {
          const dx = p.x - mouse.smoothX;
          const dy = p.y - mouse.smoothY;
          const dist = Math.hypot(dx, dy);
          if (dist > 1 && dist < 130) {
            const push = (1 - dist / 130) * 0.48;
            p.vx += (dx / dist) * push;
            p.vy += (dy / dist) * push;
          }
        }
        p.vx = p.vx * 0.985 + 0.004;
        p.vy = p.vy * 0.985 + 0.007;
        p.x += p.vx + Math.sin(p.angle) * 0.25;
        p.y += p.vy;
        p.angle += p.spin;

        if (p.y > height + 20) { p.y = -16; p.x = Math.random() * width; p.vy = 0.22 + Math.random() * 0.34; }
        if (p.x > width + 20) p.x = -16;
        if (p.x < -20) p.x = width + 16;

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.angle);
        ctx.globalAlpha = 0.78;
        ctx.fillStyle = p.color;
        if (p.note) {
          ctx.font = `700 ${Math.round(p.size * 2.1)}px "Plus Jakarta Sans", sans-serif`;
          ctx.fillText('♪', -p.size / 2, p.size / 2);
        } else {
          ctx.beginPath();
          ctx.ellipse(0, 0, p.size, p.size * 0.58, 0, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }

      // 5. Click burst notes/petals
      for (let i = bursts.length - 1; i >= 0; i--) {
        const b = bursts[i];
        b.x += b.vx;
        b.y += b.vy;
        b.vy += 0.03;
        b.alpha -= 0.02;
        if (b.alpha <= 0) {
          bursts.splice(i, 1);
          continue;
        }
        ctx.save();
        ctx.globalAlpha = b.alpha;
        ctx.fillStyle = b.color;
        ctx.font = `700 ${Math.round(b.size * 2.4)}px "Plus Jakarta Sans", sans-serif`;
        ctx.fillText(b.symbol, b.x, b.y);
        ctx.restore();
      }

      rafId = requestAnimationFrame(frame);
    }

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        cancelAnimationFrame(rafId);
      } else {
        rafId = requestAnimationFrame(frame);
      }
    });
    rafId = requestAnimationFrame(frame);
  }

  // Interactive Miku Quote Bubble on Hero Avatar click
  const mikuQuoteBtn = document.getElementById('mikuQuoteBtn');
  const mikuBubble = document.getElementById('mikuBubble');
  const mikuQuotes = [
    'Załóż słuchawki… puszczamy coś na kanale?',
    'Wpisz !s na serwerze, zobaczymy co wyjdzie…',
    'Chwila przerwy przy matchy zawsze pomaga.',
    'Tak między nami — Takeda Shingen był genialnym strategiem.',
    'Pamiętaj, że działają zarówno !p jak i /play.',
  ];
  let quoteIdx = 0;
  let bubbleTimer = null;

  if (mikuQuoteBtn && mikuBubble) {
    mikuQuoteBtn.addEventListener('click', () => {
      mikuBubble.textContent = mikuQuotes[quoteIdx % mikuQuotes.length];
      quoteIdx += 1;
      mikuBubble.classList.add('show');
      clearTimeout(bubbleTimer);
      bubbleTimer = setTimeout(() => mikuBubble.classList.remove('show'), 3600);
    });
  }

  // Smooth scroll-reveal for feature cards
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 }
    );
    revealEls.forEach((el) => observer.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('visible'));
  }
});
