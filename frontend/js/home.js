/* ── THEME ───────────────────────────────────────────────── */

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('theme-icon');
    if (icon) icon.textContent = theme === 'dark' ? '☀' : '☾';
    localStorage.setItem('dvs-theme', theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    applyTheme(current === 'dark' ? 'light' : 'dark');
}

// On load: restore saved theme
(function () {
    const saved = localStorage.getItem('dvs-theme') || 'dark';
    applyTheme(saved);
})();

/* ── NAV SCROLL BEHAVIOUR ────────────────────────────────── */

const nav = document.getElementById('nav');

let lastScrollY = 0;
let ticking     = false;
const SCROLL_THRESHOLD = 60;
const HIDE_AFTER       = window.innerHeight * 0.4;

function updateNav() {
    const currentY = window.scrollY;

    nav.classList.toggle('nav--scrolled', currentY > SCROLL_THRESHOLD);

    if (currentY > HIDE_AFTER) {
        if (currentY > lastScrollY) {
            nav.classList.add('nav--hidden');
            closeExplorerDropdown();
        } else {
            nav.classList.remove('nav--hidden');
        }
    } else {
        nav.classList.remove('nav--hidden');
    }

    lastScrollY = currentY;
    ticking = false;
}

window.addEventListener('scroll', () => {
    if (!ticking) {
        requestAnimationFrame(updateNav);
        ticking = true;
    }
}, { passive: true });

/* ── MOBILE MENU ─────────────────────────────────────────── */

const mobileMenu = document.getElementById('nav-mobile');

function toggleMobileMenu() {
    mobileMenu.classList.toggle('open');
}

mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => mobileMenu.classList.remove('open'));
});

/* ── FLOATING UI: EXPLORER DROPDOWN ─────────────────────── */

const explorerBtn      = document.getElementById('nav-explorer-btn');
const explorerDropdown = document.getElementById('nav-explorer-dropdown');
let dropdownOpen = false;

function openExplorerDropdown() {
    if (!explorerBtn || !explorerDropdown) return;
    dropdownOpen = true;
    explorerBtn.setAttribute('aria-expanded', 'true');

    const rect = explorerBtn.getBoundingClientRect();
    explorerDropdown.style.left = rect.left + 'px';
    explorerDropdown.style.top  = (rect.bottom + 8) + 'px';

    explorerDropdown.classList.add('open');
}

function closeExplorerDropdown() {
    if (!explorerBtn || !explorerDropdown) return;
    dropdownOpen = false;
    explorerDropdown.classList.remove('open');
    explorerBtn.setAttribute('aria-expanded', 'false');
}

if (explorerBtn) {
    explorerBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownOpen ? closeExplorerDropdown() : openExplorerDropdown();
    });
    explorerBtn.addEventListener('mouseenter', openExplorerDropdown);
}

if (explorerDropdown) {
    explorerDropdown.addEventListener('mouseleave', (e) => {
        if (!explorerBtn.contains(e.relatedTarget)) closeExplorerDropdown();
    });
}

document.addEventListener('click', (e) => {
    if (!explorerBtn?.contains(e.target) && !explorerDropdown?.contains(e.target)) {
        closeExplorerDropdown();
    }
});

/* ── FLOATING UI: SOURCE CHIP TOOLTIPS ───────────────────── */

const chipPairs = [
    { chip: 'chip-usgs',  tooltip: 'tooltip-usgs'  },
    { chip: 'chip-nasa',  tooltip: 'tooltip-nasa'  },
    { chip: 'chip-gdacs', tooltip: 'tooltip-gdacs' },
];

chipPairs.forEach(({ chip: chipId, tooltip: tooltipId }) => {
    const chip    = document.getElementById(chipId);
    const tooltip = document.getElementById(tooltipId);
    if (!chip || !tooltip) return;

    function showTooltip() {
        const rect = chip.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) + 'px';
        tooltip.style.top  = (rect.top - 8) + 'px';
        tooltip.style.transform = 'translateX(-50%) translateY(-100%)';
        tooltip.classList.add('visible');
    }

    function hideTooltip() {
        tooltip.classList.remove('visible');
    }

    chip.addEventListener('mouseenter', showTooltip);
    chip.addEventListener('mouseleave', hideTooltip);
    chip.addEventListener('focus',      showTooltip);
    chip.addEventListener('blur',       hideTooltip);
});