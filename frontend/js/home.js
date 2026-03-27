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
        const ttW  = 240; // matches max-width in CSS

        let left = rect.left + rect.width / 2;

        // clamp so tooltip never overflows left or right
        const minLeft = ttW / 2 + 8;
        const maxLeft = window.innerWidth - ttW / 2 - 8;
        left = Math.max(minLeft, Math.min(maxLeft, left));

        tooltip.style.left      = left + 'px';
        tooltip.style.top       = (rect.top - 8) + 'px';
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

/* ── HERO MAP PREVIEW: INTERACTIVE ──────────────────────── */

(function () {
    const tabs    = document.querySelectorAll('.ptab');
    const dots    = document.querySelectorAll('.mdot, .mflood');
    const tooltip = document.getElementById('map-tooltip');
    const ttTitle = document.getElementById('tt-title');
    const ttSub   = document.getElementById('tt-sub');
    const counter = document.getElementById('map-counter');
    if (!tabs.length || !tooltip) return;

    const counts = { all: 12, eq: 5, fire: 4, gdacs: 3 };

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const filter = tab.dataset.filter;
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            dots.forEach(dot => {
                const show = filter === 'all' || dot.classList.contains(filter);
                dot.classList.toggle('hidden', !show);
            });
            counter.textContent = counts[filter] + ' events';
        });
    });

    dots.forEach(dot => {
        dot.addEventListener('mouseenter', () => {
            const rect = dot.closest('.map-preview-inner').getBoundingClientRect();
            const dr   = dot.getBoundingClientRect();
            tooltip.style.left = (dr.left - rect.left + dr.width / 2) + 'px';
            tooltip.style.top  = (dr.top  - rect.top) + 'px';
            ttTitle.textContent = dot.dataset.title;
            ttSub.textContent   = dot.dataset.sub;
            tooltip.classList.add('show');
        });
        dot.addEventListener('mouseleave', () => tooltip.classList.remove('show'));
    });
})();

/* ── HERO PARALLAX DEPTH ─────────────────────────────────── */

(function () {
    const hero = document.querySelector('.hero');
    const parallaxLayer = document.getElementById('heroParallax');
    if (!hero || !parallaxLayer) return;

    hero.addEventListener('mousemove', (e) => {
        const { innerWidth: w, innerHeight: h } = window;
        const x = (e.clientX / w - 0.5) * 24;   // max ±12px shift
        const y = (e.clientY / h - 0.5) * 16;   // max ±8px shift
        parallaxLayer.style.transform = `translate(${x}px, ${y}px)`;
    });

    hero.addEventListener('mouseleave', () => {
        parallaxLayer.style.transition = 'transform 0.8s cubic-bezier(0.4,0.0,0.2,1)';
        parallaxLayer.style.transform = 'translate(0px, 0px)';
    });

    hero.addEventListener('mouseenter', () => {
        parallaxLayer.style.transition = 'transform 0.1s linear';
    });
})();

/* ── HERO PING DOTS — LAT/LON PROJECTION ─────────────────── */

(function () {
    const pingsContainer = document.querySelector('.hero-pings');
    if (!pingsContainer) return;

    // Globe bounds in the NASA Blue Marble "globe_west" photo
    // The photo is centered roughly on 90°W longitude
    const GLOBE = {
        cx: 0.50,    // center X as fraction of container width
        cy: 0.485,   // center Y (slightly above center)
        r:  0.38,    // visible radius as fraction of container height
        viewLon: -90 // central meridian of the photo (degrees)
    };

    function latLonToXY(lat, lon) {
        const toRad = Math.PI / 180;
        const phi   = lat * toRad;
        // Longitude relative to the photo's center meridian
        const lambda = (lon - GLOBE.viewLon) * toRad;

        // Orthographic projection (view from infinity)
        const cosC = Math.sin(0) * Math.sin(phi) + Math.cos(0) * Math.cos(phi) * Math.cos(lambda);

        // Skip points on the far side of the globe
        if (cosC < 0.05) return null;

        const xNorm = Math.cos(phi) * Math.sin(lambda);
        const yNorm = -(Math.sin(phi));   // flip Y: screen Y goes down

        return {
            x: (GLOBE.cx + GLOBE.r * xNorm) * 100,
            y: (GLOBE.cy + GLOBE.r * yNorm) * 100
        };
    }

    // Real disaster locations across the Americas (visible hemisphere)
    const disasters = [
        // Earthquakes — Ring of Fire, Caribbean
        { lat: 19.4,  lon: -99.1,  type: 'eq'    },  // Mexico City
        { lat: -33.4, lon: -70.6,  type: 'eq'    },  // Santiago, Chile
        { lat: 61.2,  lon: -150.0, type: 'eq'    },  // Alaska
        { lat: 18.5,  lon: -72.3,  type: 'eq'    },  // Haiti
        { lat: -12.0, lon: -77.0,  type: 'eq'    },  // Lima, Peru

        // Fires — Americas wildfire zones
        { lat: 34.1,  lon: -118.2, type: 'fire'  },  // Los Angeles
        { lat: -3.4,  lon: -60.0,  type: 'fire'  },  // Amazon
        { lat: 49.3,  lon: -123.1, type: 'fire'  },  // British Columbia
        { lat: -15.8, lon: -56.1,  type: 'fire'  },  // Pantanal, Brazil

        // GDACS — floods, cyclones
        { lat: 25.8,  lon: -80.2,  type: 'gdacs' },  // Florida
        { lat: 23.6,  lon: -102.5, type: 'gdacs' },  // Central Mexico
        { lat: -22.9, lon: -43.2,  type: 'gdacs' },  // Rio de Janeiro
    ];

    disasters.forEach(({ lat, lon, type }, i) => {
        const pos = latLonToXY(lat, lon);
        if (!pos) return; // behind the globe

        const dot = document.createElement('div');
        dot.className = `hping hping--${type}`;
        dot.style.left = pos.x + '%';
        dot.style.top  = pos.y + '%';
        // Stagger ripple animation per dot
        dot.style.setProperty('--ripple-delay', (i * 0.3) + 's');
        pingsContainer.appendChild(dot);
    });
})();