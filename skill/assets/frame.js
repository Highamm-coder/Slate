/* ==================================================================
   Slate — frame v1 (injected by the slate-frame skill)
   Configurable: change SLIDE_SELECTOR below if your deck uses a
   different class than ".slide".
   ================================================================== */
(function(){
  const SLIDE_SELECTOR = '.slide';

  const slides = [...document.querySelectorAll(SLIDE_SELECTOR)];
  if (!slides.length) {
    console.warn('[deck-frame] No slides found for selector:', SLIDE_SELECTOR);
    return;
  }
  const total = slides.length;
  let current = 0;

  // Assign stable IDs (slide-1, slide-2, …) for URL deep-linking.
  // Skip any slide that already has an id to avoid overwriting.
  slides.forEach((s, i) => { if (!s.id) s.id = `slide-${i+1}`; });

  // Reveal-on-scroll fade-in if slides have starting opacity:0 (optional;
  // safe even when the host deck doesn't use it).
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.12 });
  slides.forEach(s => revealObserver.observe(s));

  // Nav UI refs
  const nav      = document.getElementById('dfnav');
  const help     = document.getElementById('dfnav-help');
  const helpPane = document.getElementById('dfnav-help-panel');
  const elCur    = document.getElementById('dfnav-current');
  const elTotal  = document.getElementById('dfnav-total');
  const elPrev   = document.getElementById('dfnav-prev');
  const elNext   = document.getElementById('dfnav-next');
  if (!nav || !help || !helpPane) {
    console.warn('[deck-frame] Nav markup missing; skipping init.');
    return;
  }
  elTotal.textContent = total;

  // Auto-hide nav
  let hideTimer;
  const HIDE_DELAY = 2400;
  const showNav = () => {
    nav.classList.add('dfnav-visible');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => nav.classList.remove('dfnav-visible'), HIDE_DELAY);
  };
  document.addEventListener('mousemove', showNav, { passive: true });
  document.addEventListener('touchstart', showNav, { passive: true });
  nav.addEventListener('mouseenter', () => {
    clearTimeout(hideTimer);
    nav.classList.add('dfnav-visible');
  });
  nav.addEventListener('mouseleave', showNav);

  // Help toggle
  help.addEventListener('click', (e) => {
    e.stopPropagation();
    helpPane.classList.toggle('dfnav-open');
  });
  document.addEventListener('click', (e) => {
    if (!helpPane.contains(e.target) && e.target !== help) {
      helpPane.classList.remove('dfnav-open');
    }
  });

  // Peek shortcuts on counter hover/focus
  const elCount = document.getElementById('dfnav-counter');
  if (elCount) {
    let peekTimer;
    const peekOpen = () => {
      clearTimeout(peekTimer);
      helpPane.classList.add('dfnav-open');
    };
    const peekClose = () => {
      clearTimeout(peekTimer);
      peekTimer = setTimeout(() => {
        if (!elCount.matches(':hover') && !helpPane.matches(':hover') && document.activeElement !== elCount) {
          helpPane.classList.remove('dfnav-open');
        }
      }, 180);
    };
    elCount.addEventListener('mouseenter', peekOpen);
    elCount.addEventListener('focus', peekOpen);
    elCount.addEventListener('mouseleave', peekClose);
    elCount.addEventListener('blur', peekClose);
    helpPane.addEventListener('mouseenter', () => clearTimeout(peekTimer));
    helpPane.addEventListener('mouseleave', peekClose);
  }

  const updateCounter = () => {
    elCur.textContent = current + 1;
    elPrev.disabled = current === 0;
    elNext.disabled = current === total - 1;
  };

  const goTo = (i, { push = true } = {}) => {
    current = Math.max(0, Math.min(total - 1, i));
    slides[current].scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (push) history.replaceState(null, '', `#slide-${current + 1}`);
    updateCounter();
    showNav();
  };

  // Track centered slide from scrolling/keyboard
  const centerObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting && e.intersectionRatio > 0.5) {
        const idx = slides.indexOf(e.target);
        if (idx !== -1 && idx !== current) {
          current = idx;
          updateCounter();
          history.replaceState(null, '', `#slide-${current + 1}`);
        }
      }
    });
  }, { threshold: [0.5, 0.75] });
  slides.forEach(s => centerObserver.observe(s));

  // Keyboard
  document.addEventListener('keydown', (e) => {
    const tag = document.activeElement && document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    if (['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)) {
      e.preventDefault(); goTo(current + 1);
    } else if (['ArrowLeft','ArrowUp','PageUp'].includes(e.key)) {
      e.preventDefault(); goTo(current - 1);
    } else if (e.key === 'Home') {
      e.preventDefault(); goTo(0);
    } else if (e.key === 'End') {
      e.preventDefault(); goTo(total - 1);
    } else if (e.key === 'p' || e.key === 'P') {
      if (!e.metaKey && !e.ctrlKey) { e.preventDefault(); window.print(); }
    } else if (e.key === '?' || e.key === '/') {
      e.preventDefault(); helpPane.classList.toggle('dfnav-open'); showNav();
    } else if (e.key === 'Escape') {
      helpPane.classList.remove('dfnav-open');
    }
  });

  elPrev.addEventListener('click', () => goTo(current - 1));
  elNext.addEventListener('click', () => goTo(current + 1));

  // URL hash routing
  const jumpFromHash = () => {
    const m = (location.hash || '').match(/^#slide-(\d+)$/);
    if (m) {
      const i = Math.max(0, Math.min(total - 1, parseInt(m[1], 10) - 1));
      goTo(i, { push: false });
    } else {
      updateCounter();
    }
  };
  window.addEventListener('hashchange', jumpFromHash);
  requestAnimationFrame(jumpFromHash);

  // Briefly show the nav on load so users know it exists
  setTimeout(showNav, 600);
})();
