// Animated CRT cursor controller
(function () {
  // Respect touch devices: keep native cursor
  const isTouch = matchMedia("(pointer: coarse)").matches || 'ontouchstart' in window;
  if (isTouch) return;

  const body = document.body;
  body.classList.add('crt-cursor-on');

  const cur = document.createElement('div');
  cur.className = 'crt-cursor arrow';
  document.body.appendChild(cur);

  // Hotspot offsets so the visible shape lines up with click point
  const OFFSETS = {
    arrow:  { x: -2,  y: -2  },   // tip near top-left
    pointer:{ x: -12, y: -12 },   // circle centered on point
    ibeam:  { x: -2,  y: -24 }    // I-beam baseline
  };
  let current = 'arrow';

  function setCursor(kind){
    if (current === kind) return;
    current = kind;
    cur.className = 'crt-cursor ' + kind;
  }

  function updatePosition(x, y){
    const o = OFFSETS[current];
    cur.style.setProperty('--cx', (x + o.x) + 'px');
    cur.style.setProperty('--cy', (y + o.y) + 'px');
  }

  window.addEventListener('mousemove', (e) => {
    // Determine target intent
    const t = e.target;
    if (t.closest('input, textarea, [contenteditable=""], [contenteditable="true"]')) {
      setCursor('ibeam');
    } else if (t.closest('a, button, .btn, .titlelink')) {
      setCursor('pointer');
    } else {
      setCursor('arrow');
    }
    updatePosition(e.clientX, e.clientY);
  }, { passive: true });

  // Keep position on scroll (for fixed header nesting)
  window.addEventListener('scroll', () => {
    // noop: position is fixed to viewport; nothing to recalc
  }, { passive: true });

  // Hide our cursor during print
  window.addEventListener('beforeprint', () => cur.style.display = 'none');
  window.addEventListener('afterprint',  () => cur.style.display = '');
})();
