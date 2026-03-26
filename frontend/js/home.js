/* ── NAV SCROLL BEHAVIOUR ────────────────────────────────── */
// The nav:
//   - starts transparent (no bg)
//   - gains a frosted background once user scrolls past 60px (nav--scrolled)
//   - hides (slides up) when scrolling DOWN past the hero
//   - reappears when scrolling UP, or when near the top

const nav = document.getElementById('nav');

let lastScrollY  = 0;
let ticking      = false;
const SCROLL_THRESHOLD = 60;   // px before gaining background
const HIDE_AFTER  = window.innerHeight * 0.4; // hide after scrolling 40vh down

function updateNav() {
    const currentY = window.scrollY;
    const heroH    = window.innerHeight;

    // Add/remove background
    nav.classList.toggle('nav--scrolled', currentY > SCROLL_THRESHOLD);

    // Only start hiding after user has scrolled past 40% of the viewport
    if (currentY > HIDE_AFTER) {
        if (currentY > lastScrollY) {
            // scrolling DOWN — hide
            nav.classList.add('nav--hidden');
        } else {
            // scrolling UP — show
            nav.classList.remove('nav--hidden');
        }
    } else {
        // near the top — always show
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

// ── MOBILE MENU ──────────────────────────────────────────
const mobileMenu = document.getElementById('nav-mobile');

function toggleMobileMenu() {
    mobileMenu.classList.toggle('open');
}

// Close mobile menu on link click
mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => mobileMenu.classList.remove('open'));
});