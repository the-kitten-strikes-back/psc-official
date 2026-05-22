/**
 * PSC Easter Egg: Pen Thief Alert System
 * Triggers a site-wide red alert banner when "pen thief" is typed
 */

(function() {
  // Buffer to track typed characters
  let typeBuffer = '';
  const triggerPhrase = 'pen thief';
  const glowPhrase = 'psc day';
  let alertActive = false;
  let glowActive = false;
  const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight'];
  let konamiBuffer = [];

  // Create the alert banner HTML
  function createAlertBanner() {
    const banner = document.createElement('div');
    banner.id = 'psc-pen-thief-alert';
    banner.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      width: 100%;
      background: linear-gradient(90deg, #8b0000 0%, #ff0000 50%, #8b0000 100%);
      color: #fff;
      padding: 20px;
      text-align: center;
      font-size: 18px;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 2px;
      z-index: 10000;
      box-shadow: 0 4px 20px rgba(139, 0, 0, 0.8);
      animation: pen-thief-pulse 0.5s ease-out;
    `;
    
    banner.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; gap: 15px;">
        <span style="font-size: 28px;">🚨</span>
        <span>ALERT: PEN THIEF DETECTED IN VICINITY</span>
        <span style="font-size: 28px;">🚨</span>
      </div>
      <div style="margin-top: 10px; font-size: 12px; letter-spacing: 1px; opacity: 0.9;">
        ALL SECTORS ACTIVATED — SECURITY PROTOCOL OMEGA ENGAGED
      </div>
    `;

    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pen-thief-pulse {
        0% {
          transform: translateY(-100%);
          opacity: 0;
        }
        50% {
          box-shadow: 0 4px 20px rgba(139, 0, 0, 0.8), 0 0 30px rgba(255, 0, 0, 0.6);
        }
        100% {
          transform: translateY(0);
          opacity: 1;
        }
      }

      @keyframes red-flicker {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
      }

      #psc-pen-thief-alert {
        animation: red-flicker 0.3s infinite;
      }
    `;

    if (!document.querySelector('style[data-easter-egg]')) {
      style.setAttribute('data-easter-egg', 'pen-thief');
      document.head.appendChild(style);
    }

    return banner;
  }

  // Trigger the alert
  function triggerAlert() {
    if (alertActive) return;
    alertActive = true;

    // Remove existing alert if any
    const existing = document.getElementById('psc-pen-thief-alert');
    if (existing) {
      existing.remove();
    }

    // Create and insert new alert
    const banner = createAlertBanner();
    document.body.insertBefore(banner, document.body.firstChild);

    // Add red tint to the entire page
    const overlay = document.createElement('div');
    overlay.id = 'psc-red-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(255, 0, 0, 0.05);
      pointer-events: none;
      z-index: 9999;
      animation: red-overlay-pulse 2s infinite;
    `;

    const overlayStyle = document.createElement('style');
    overlayStyle.textContent = `
      @keyframes red-overlay-pulse {
        0%, 100% { opacity: 0.05; }
        50% { opacity: 0.15; }
      }
    `;
    document.head.appendChild(overlayStyle);
    document.body.appendChild(overlay);

    // Auto-dismiss after 10 seconds, but keep it dramatic
    setTimeout(() => {
      // Fade out
      banner.style.animation = 'fadeOut 1s ease-out forwards';
      overlay.style.animation = 'fadeOut 1s ease-out forwards';

      const fadeStyle = document.createElement('style');
      fadeStyle.textContent = `
        @keyframes fadeOut {
          0% { opacity: 1; }
          100% { opacity: 0; }
        }
      `;
      document.head.appendChild(fadeStyle);

      setTimeout(() => {
        banner.remove();
        overlay.remove();
        alertActive = false;
        typeBuffer = ''; // Reset buffer
      }, 1000);
    }, 10000);
  }

  function triggerVaultGlow() {
    if (glowActive) return;
    glowActive = true;
    const badge = document.createElement('div');
    badge.style.cssText = `
      position: fixed;
      right: 18px;
      bottom: 18px;
      padding: 14px 18px;
      border-radius: 14px;
      background: linear-gradient(135deg, #10b981, #3b82f6);
      color: white;
      font-weight: 800;
      z-index: 10001;
      box-shadow: 0 18px 32px rgba(59, 130, 246, 0.35);
    `;
    badge.textContent = 'PSC DAY MODE ACTIVATED';
    document.body.appendChild(badge);
    document.body.style.transition = 'filter 0.35s ease';
    document.body.style.filter = 'saturate(1.15) hue-rotate(-8deg)';
    setTimeout(() => {
      badge.remove();
      document.body.style.filter = '';
      glowActive = false;
    }, 5000);
  }

  function triggerKonamiEgg() {
    const stamp = document.createElement('div');
    stamp.style.cssText = `
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 10002;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 3rem;
      font-weight: 900;
      color: rgba(15, 23, 42, 0.9);
      text-shadow: 0 0 30px rgba(255,255,255,0.8);
    `;
    stamp.textContent = 'LEGENDARY PEN MODE';
    document.body.appendChild(stamp);
    setTimeout(() => stamp.remove(), 2800);
  }

  // Listen for keyboard input
  document.addEventListener('keypress', (e) => {
    // Only track alphabetic and space characters
    if (e.key && /[a-z\s]/i.test(e.key)) {
      typeBuffer += e.key.toLowerCase();

      // Keep buffer size manageable
      if (typeBuffer.length > triggerPhrase.length + 10) {
        typeBuffer = typeBuffer.slice(-triggerPhrase.length - 10);
      }

      // Check if trigger phrase is in the buffer
      if (typeBuffer.includes(triggerPhrase)) {
        triggerAlert();
        typeBuffer = ''; // Reset after trigger
      } else if (typeBuffer.includes(glowPhrase)) {
        triggerVaultGlow();
        typeBuffer = '';
      }
    }
  });

  document.addEventListener('keydown', (e) => {
    konamiBuffer.push(e.key);
    if (konamiBuffer.length > konamiCode.length) {
      konamiBuffer = konamiBuffer.slice(-konamiCode.length);
    }
    if (konamiCode.every((key, index) => konamiBuffer[index] === key)) {
      triggerKonamiEgg();
      konamiBuffer = [];
    }
  });

  // Also listen for paste events in case someone pastes "pen thief"
  document.addEventListener('paste', (e) => {
    const pastedText = e.clipboardData.getData('text').toLowerCase();
    if (pastedText.includes(triggerPhrase)) {
      triggerAlert();
    }
  });

  // Log easter egg activation to console for fun
  console.log('%c🔍 PSC Security: Pen Thief Detection System Active', 'color: #8b0000; font-size: 14px; font-weight: bold;');
})();
