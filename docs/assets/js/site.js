// Theme toggle — detection already handled by inline head script
var toggle = document.getElementById('theme-toggle');
var barColours = { light: '#ffffff', dark: '#08080a' };  // head.html's theme-color metas
// The button says whether dark mode is on (aria-pressed); the browser bar takes the theme in
// use. Both used to stay as the page loaded: a light choice on a dark system kept a dark bar.
function showTheme(theme) {
  if (toggle) toggle.setAttribute('aria-pressed', String(theme === 'dark'));
  document.querySelectorAll('meta[name="theme-color"]').forEach(function(m) {
    m.setAttribute('content', barColours[theme]);
  });
}
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  showTheme(theme);
}
showTheme(document.documentElement.getAttribute('data-theme'));
if (toggle) {
  toggle.addEventListener('click', function() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('ow-theme', next); } catch(e) {}
  });
}

// Follow system preference changes when user hasn't overridden manually
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
  var stored;
  try { stored = localStorage.getItem('ow-theme'); } catch(e2) {}
  if (!stored) {
    setTheme(e.matches ? 'dark' : 'light');
  }
});

// Mobile nav toggle
var navToggle = document.querySelector('.nav-toggle');
var navLinks = document.getElementById('nav-links');
if (navToggle && navLinks) {
  navToggle.addEventListener('click', function() {
    var isOpen = navToggle.getAttribute('aria-expanded') === 'true';
    navToggle.setAttribute('aria-expanded', String(!isOpen));
    navLinks.classList.toggle('open', !isOpen);
  });
}

// Docs: docs.html closes the menu on a phone. Above 768 px its summary is hidden, so a
// tablet turned to landscape re-opens it rather than keep an empty sidebar.
var docsMenu = document.querySelector('.docs-menu');
if (docsMenu) {
  window.matchMedia('(max-width: 768px)').addEventListener('change', function(e) {
    if (!e.matches) docsMenu.setAttribute('open', '');
  });
}

// A box that scrolls sideways (wide table, long code line) must take keyboard focus to be
// scrolled without a mouse, and a focusable region needs a name (axe
// scrollable-region-focusable). A box that fits is no tab stop. Re-checked on resize and once
// the fonts are in, since both change what overflows.
var scrollNames = document.documentElement.lang === 'de'
  ? { table: 'Scrollbare Tabelle', code: 'Scrollbarer Code' }
  : { table: 'Scrollable table', code: 'Scrollable code' };
function markScrollBoxes() {
  document.querySelectorAll('.table-scroll, pre').forEach(function(box) {
    if (box.scrollWidth > box.clientWidth) {
      var table = box.querySelector('table');
      var own = table && (table.getAttribute('aria-label') ||
        (table.caption && table.caption.textContent.trim()));
      box.tabIndex = 0;
      box.setAttribute('role', 'region');
      box.setAttribute('aria-label', own || (table ? scrollNames.table : scrollNames.code));
    } else {
      box.removeAttribute('tabindex');
      box.removeAttribute('role');
      box.removeAttribute('aria-label');
    }
  });
}
markScrollBoxes();
window.addEventListener('resize', markScrollBoxes);
if (document.fonts) document.fonts.ready.then(markScrollBoxes);
