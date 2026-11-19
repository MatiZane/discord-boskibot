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
  // Interactive Hero Sky Canvas: Mouse Water/Air Ripples + Floating 5-Color Petals
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

    const ripples = [];
    const bursts = [];
    const petals = [];
    const mouse = { x: -999, y: -999, active: false, lastRippleAt: 0 };

    function resize() {
      const rect = hero.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function seedPetals() {
      petals.length = 0;
      const count = width < 700 ? 14 : 24;
      for (let i = 0; i < count; i++) {
        petals.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.35) * 0.45,
          vy: 0.22 + Math.random() * 0.42,
          size: 5 + Math.random() * 6,
          angle: Math.random() * Math.PI * 2,
          spin: (Math.random() - 0.5) * 0.025,
          color: palette[i % palette.length],
          note: i % 5 === 0,
        });
      }
    }

    function spawnRipple(x, y, strong = false) {
      ripples.push({
        x,
        y,
        r: strong ? 10 : 6,
        maxR: strong ? 140 : 88,
        alpha: strong ? 0.52 : 0.34,
        speed: strong ? 2.4 : 1.75,
        tint: strong ? '#ffffff' : '#d8f4ff',
      });
      if (strong) {
        ripples.push({
          x,
          y,
          r: 2,
          maxR: 96,
          alpha: 0.42,
          speed: 1.5,
          tint: '#ffcee2',
        });
        for (let i = 0; i < 8; i++) {
          const ang = (Math.PI * 2 * i) / 8 + Math.random() * 0.3;
          const spd = 1.2 + Math.random() * 2.2;
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
      if (ripples.length > 28) ripples.splice(0, ripples.length - 28);
    }

    hero.addEventListener('pointermove', (e) => {
      const rect = hero.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      mouse.x = x;
      mouse.y = y;
      mouse.active = true;
      const now = performance.now();
      if (now - mouse.lastRippleAt > 85) {
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
    seedPetals();
    window.addEventListener('resize', () => {
      resize();
      seedPetals();
    });

    let rafId = 0;
    function frame() {
      ctx.clearRect(0, 0, width, height);

      // Soft ambient glow following pointer
      if (mouse.active) {
        const glow = ctx.createRadialGradient(mouse.x, mouse.y, 4, mouse.x, mouse.y, 130);
        glow.addColorStop(0, 'rgba(255, 255, 255, 0.22)');
        glow.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(mouse.x, mouse.y, 130, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw expanding water/air ripples
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
        ctx.lineWidth = Math.max(1, 2.6 * (1 - progress));
        ctx.beginPath();
        ctx.arc(rp.x, rp.y, rp.r, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      // Draw drifting 5-color petals & musical notes (gently pushed by mouse!)
      for (const p of petals) {
        if (mouse.active) {
          const dx = p.x - mouse.x;
          const dy = p.y - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist > 1 && dist < 110) {
            const push = (1 - dist / 110) * 0.42;
            p.vx += (dx / dist) * push;
            p.vy += (dy / dist) * push;
          }
        }
        p.vx *= 0.985;
        p.vy = p.vy * 0.985 + 0.008;
        p.x += p.vx + Math.sin(p.angle) * 0.25;
        p.y += p.vy;
        p.angle += p.spin;

        if (p.y > height + 20) { p.y = -16; p.x = Math.random() * width; p.vy = 0.25 + Math.random() * 0.35; }
        if (p.x > width + 20) p.x = -16;
        if (p.x < -20) p.x = width + 16;

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.angle);
        ctx.globalAlpha = 0.72;
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

      // Draw click burst notes/petals
      for (let i = bursts.length - 1; i >= 0; i--) {
        const b = bursts[i];
        b.x += b.vx;
        b.y += b.vy;
        b.vy += 0.03;
        b.alpha -= 0.022;
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
