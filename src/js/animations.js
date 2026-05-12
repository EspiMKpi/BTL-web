/**
 * VozFlix — anime.js Animation Engine
 * Centralized animation utilities using anime.js v4
 *
 * All functions respect prefers-reduced-motion.
 */

import { animate, stagger, createTimeline, onScroll, createSpring } from 'animejs';

// ─── Reduced-motion guard ───────────────────────────────────────────
const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
export const prefersReducedMotion = () => motionQuery.matches;

// ─── Preloader ──────────────────────────────────────────────────────

/**
 * Animate the VozFlix preloader text and reveal the app.
 * @param {HTMLElement} preloaderEl - the #preloader overlay
 * @param {Function} [onBeforeReveal] - called just before the preloader slides up, so the page beneath can be made visible
 * @returns {Promise} resolves when preloader is hidden
 */
export function animatePreloader(preloaderEl, onBeforeReveal) {
    return new Promise((resolve) => {
        if (!preloaderEl || prefersReducedMotion()) {
            if (preloaderEl) preloaderEl.style.display = 'none';
            resolve();
            return;
        }

        const letters = preloaderEl.querySelectorAll('.preloader-letter');
        const bar = preloaderEl.querySelector('.preloader-bar');
        const glow = preloaderEl.querySelector('.preloader-glow');

        const tl = createTimeline({
            onComplete: () => {
                // Show the page beneath BEFORE sliding the preloader away
                if (onBeforeReveal) onBeforeReveal();

                // Slide preloader up and out
                animate(preloaderEl, {
                    translateY: '-100%',
                    duration: 600,
                    ease: 'inOutQuint',
                    onComplete: () => {
                        preloaderEl.style.display = 'none';
                        resolve();
                    }
                });
            }
        });

        // Letters stagger in
        tl.add(letters, {
            opacity: [0, 1],
            translateY: [30, 0],
            scale: [0.8, 1],
            delay: stagger(80),
            duration: 500,
            ease: 'outQuint',
        });

        // Gold glow pulse
        if (glow) {
            tl.add(glow, {
                opacity: [0, 0.6, 0.3],
                scale: [0.5, 1.2, 1],
                duration: 800,
                ease: 'outExpo',
            }, '-=300');
        }

        // Progress bar
        if (bar) {
            tl.add(bar, {
                scaleX: [0, 1],
                duration: 1000,
                ease: 'inOutQuad',
            }, '-=600');
        }

        // Hold for a beat
        tl.add({}, { duration: 300 });
    });
}

// ─── Scroll-Reveal System ───────────────────────────────────────────

let _scrollObservers = [];

/**
 * Initialize scroll-reveal animations for all [data-scroll-reveal] elements
 * within the given container. Called when a page becomes active.
 * @param {HTMLElement} container - the active page element
 */
export function initScrollReveals(container) {
    if (!container || prefersReducedMotion()) return;

    // Clean up previous observers
    cleanupScrollReveals();

    const targets = container.querySelectorAll('[data-scroll-reveal]');
    targets.forEach((el) => {
        const type = el.dataset.scrollReveal || 'fade-up';
        const delay = parseFloat(el.dataset.scrollDelay) || 0;

        // Set initial hidden state
        el.style.opacity = '0';

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        triggerReveal(el, type, delay);
                        observer.unobserve(el);
                    }
                });
            },
            { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
        );
        observer.observe(el);
        _scrollObservers.push(observer);
    });
}

function triggerReveal(el, type, delay) {
    const baseProps = {
        duration: 700,
        ease: 'outQuint',
        delay,
    };

    switch (type) {
        case 'fade-up':
            el.style.opacity = '0';
            animate(el, { opacity: [0, 1], translateY: [40, 0], ...baseProps });
            break;
        case 'fade-in':
            el.style.opacity = '0';
            animate(el, { opacity: [0, 1], ...baseProps });
            break;
        case 'slide-right':
            el.style.opacity = '0';
            animate(el, { opacity: [0, 1], translateX: [-50, 0], ...baseProps });
            break;
        case 'scale-in':
            el.style.opacity = '0';
            animate(el, { opacity: [0, 1], scale: [0.85, 1], ...baseProps });
            break;
        case 'slide-up':
            el.style.opacity = '0';
            animate(el, { opacity: [0, 1], translateY: [60, 0], ...baseProps });
            break;
        default:
            el.style.opacity = '0';
            animate(el, { opacity: [0, 1], translateY: [30, 0], ...baseProps });
    }
}

/**
 * Clean up all IntersectionObserver instances
 */
export function cleanupScrollReveals() {
    _scrollObservers.forEach((obs) => obs.disconnect());
    _scrollObservers = [];
}

// ─── Hero Animations ────────────────────────────────────────────────

/**
 * Cinematic hero entrance: staggered reveal of kicker → title → description → buttons
 * @param {HTMLElement} heroContent - the hero content wrapper
 */
export function animateHeroContent(heroContent) {
    if (!heroContent || prefersReducedMotion()) return;

    const kicker = heroContent.querySelector('.hero-slide-kicker');
    const title = heroContent.querySelector('.hero-slide-title');
    const desc = heroContent.querySelector('.hero-slide-desc');
    const btns = heroContent.querySelector('.hero-slide-btns');

    const tl = createTimeline();

    if (kicker) {
        tl.add(kicker, {
            opacity: [0, 1],
            translateY: [20, 0],
            duration: 500,
            ease: 'outQuint',
        });
    }

    if (title) {
        tl.add(title, {
            opacity: [0, 1],
            translateY: [30, 0],
            duration: 600,
            ease: 'outQuint',
        }, '-=250');
    }

    if (desc) {
        tl.add(desc, {
            opacity: [0, 1],
            translateY: [25, 0],
            duration: 500,
            ease: 'outQuint',
        }, '-=300');
    }

    if (btns) {
        tl.add(btns, {
            opacity: [0, 1],
            translateY: [20, 0],
            duration: 400,
            ease: 'outQuint',
        }, '-=250');
    }
}

/**
 * Hero background parallax on scroll
 * @param {HTMLElement} bgElement - the hero background image
 */
export function initHeroParallax(bgElement) {
    if (!bgElement || prefersReducedMotion()) return;

    animate(bgElement, {
        translateY: ['0%', '15%'],
        ease: 'linear',
        autoplay: onScroll({
            container: window,
            enter: 'top top',
            leave: 'bottom top',
            sync: true,
        }),
    });
}

// ─── Staggered Cards ────────────────────────────────────────────────

/**
 * Stagger-reveal movie cards in a rail/grid
 * @param {string} selector - CSS selector for the cards
 * @param {Object} options - { from: 'first'|'center'|'last', staggerMs: number }
 */
export function staggerCards(selector, options = {}) {
    if (prefersReducedMotion()) return;

    const { from = 'first', staggerMs = 60 } = options;

    animate(selector, {
        opacity: [0, 1],
        translateY: [30, 0],
        scale: [0.95, 1],
        delay: stagger(staggerMs, { from }),
        duration: 600,
        ease: 'outQuint',
    });
}

/**
 * Animate Top 10 rank numbers with a spring bounce
 * @param {string} selector - CSS selector for rank elements
 */
export function animateRanks(selector) {
    if (prefersReducedMotion()) return;

    animate(selector, {
        scale: [0, 1],
        opacity: [0, 1],
        delay: stagger(80, { from: 'first' }),
        duration: 600,
        ease: createSpring({ stiffness: 150, damping: 12 }),
    });
}

// ─── Number Counters ────────────────────────────────────────────────

/**
 * Animate a number counting up from 0
 * @param {HTMLElement} el - element whose textContent will be updated
 * @param {number} target - target number
 * @param {Object} opts - { duration, decimals }
 */
export function animateCounter(el, target, opts = {}) {
    if (!el || prefersReducedMotion()) {
        if (el) el.textContent = target;
        return;
    }

    const { duration = 1500, decimals = 0 } = opts;

    animate(el, {
        textContent: [0, target],
        round: decimals > 0 ? Math.pow(10, decimals) : 1,
        duration,
        ease: 'outQuad',
    });
}

// ─── Page Transitions ───────────────────────────────────────────────

/**
 * Animate page exit (fade out + slide up)
 * @param {HTMLElement} el
 * @returns {Promise}
 */
export function pageTransitionOut(el) {
    return new Promise((resolve) => {
        if (!el || prefersReducedMotion()) {
            resolve();
            return;
        }

        animate(el, {
            opacity: [1, 0],
            translateY: [0, -15],
            duration: 280,
            ease: 'inQuad',
            onComplete: resolve,
        });
    });
}

/**
 * Animate page entrance (fade in + slide up)
 * @param {HTMLElement} el
 * @returns {Promise}
 */
export function pageTransitionIn(el) {
    return new Promise((resolve) => {
        if (!el || prefersReducedMotion()) {
            if (el) el.style.opacity = '1';
            resolve();
            return;
        }

        el.style.opacity = '0';
        animate(el, {
            opacity: [0, 1],
            translateY: [20, 0],
            duration: 400,
            ease: 'outQuint',
            onComplete: resolve,
        });
    });
}

// ─── Detail Page ────────────────────────────────────────────────────

/**
 * Detail hero entrance: backdrop zoom + content stagger
 * @param {HTMLElement} container - detail page container
 */
export function animateDetailHero(container) {
    if (!container || prefersReducedMotion()) return;

    const backdrop = container.querySelector('.detail-hero-bg');
    const title = container.querySelector('.detail-title');
    const meta = container.querySelector('.detail-meta');
    const desc = container.querySelector('.detail-overview');
    const actions = container.querySelector('.detail-actions');

    // Backdrop zoom-in
    if (backdrop) {
        backdrop.style.transform = 'scale(1.08)';
        animate(backdrop, {
            scale: [1.08, 1],
            duration: 1400,
            ease: 'outQuart',
        });
    }

    // Content stagger
    const tl = createTimeline({ delay: 300 });

    if (title) {
        tl.add(title, { opacity: [0, 1], translateY: [30, 0], duration: 600, ease: 'outQuint' });
    }
    if (meta) {
        tl.add(meta, { opacity: [0, 1], translateY: [20, 0], duration: 400, ease: 'outQuint' }, '-=300');
    }
    if (desc) {
        tl.add(desc, { opacity: [0, 1], translateY: [20, 0], duration: 400, ease: 'outQuint' }, '-=250');
    }
    if (actions) {
        tl.add(actions, { opacity: [0, 1], translateY: [15, 0], duration: 350, ease: 'outQuint' }, '-=200');
    }
}

/**
 * Stagger cast avatars
 * @param {string} selector - CSS selector for cast items
 */
export function animateCast(selector) {
    if (prefersReducedMotion()) return;

    animate(selector, {
        opacity: [0, 1],
        scale: [0.7, 1],
        rotate: [-8, 0],
        delay: stagger(50, { from: 'first' }),
        duration: 500,
        ease: createSpring({ stiffness: 180, damping: 14 }),
    });
}

// ─── Watching Page ──────────────────────────────────────────────────

/**
 * Player container entrance animation
 * @param {HTMLElement} container - watching page container
 */
export function animatePlayerEntry(container) {
    if (!container || prefersReducedMotion()) return;

    const player = container.querySelector('.player-container');
    const episodes = container.querySelectorAll('.episode-card');
    const upNext = container.querySelector('.up-next-section');

    if (player) {
        animate(player, {
            opacity: [0, 1],
            scale: [0.95, 1],
            duration: 600,
            ease: 'outQuint',
        });
    }

    if (episodes.length > 0) {
        animate(episodes, {
            opacity: [0, 1],
            translateX: [-30, 0],
            delay: stagger(60, { from: 'first' }),
            duration: 500,
            ease: 'outQuint',
        });
    }

    if (upNext) {
        animate(upNext, {
            opacity: [0, 1],
            translateY: [30, 0],
            duration: 500,
            delay: 200,
            ease: 'outQuint',
        });
    }
}

// ─── Utility ────────────────────────────────────────────────────────

/**
 * Reveal section header with anime.js
 * @param {HTMLElement} header - section header element
 */
export function animateSectionHeader(header) {
    if (!header || prefersReducedMotion()) return;

    animate(header, {
        opacity: [0, 1],
        translateY: [25, 0],
        duration: 600,
        ease: 'outQuint',
    });
}

/**
 * Gold glow pulse effect on an element
 * @param {HTMLElement} el
 */
export function glowPulse(el) {
    if (!el || prefersReducedMotion()) return;

    animate(el, {
        boxShadow: [
            '0 0 0px rgba(244, 200, 74, 0)',
            '0 0 30px rgba(244, 200, 74, 0.4)',
            '0 0 0px rgba(244, 200, 74, 0)',
        ],
        duration: 2000,
        ease: 'inOutQuad',
        loop: true,
    });
}

// ─── Page-Level Preloader ───────────────────────────────────────────

const _pageLoaderHTML = `
    <div class="page-preloader">
        <div class="page-preloader-glow"></div>
        <div class="page-preloader-text">
            <span class="page-preloader-letter">V</span>
            <span class="page-preloader-letter">O</span>
            <span class="page-preloader-letter">Z</span>
            <span class="page-preloader-letter gold">F</span>
            <span class="page-preloader-letter gold">L</span>
            <span class="page-preloader-letter gold">I</span>
            <span class="page-preloader-letter gold">X</span>
        </div>
        <div class="page-preloader-bar-track">
            <div class="page-preloader-bar"></div>
        </div>
        <p class="page-preloader-label">Loading…</p>
    </div>`;

/**
 * Show a branded VozFlix preloader inside a container element.
 * Returns an async hide() function that animates the loader out.
 *
 * @param {HTMLElement} container - element to inject the loader into
 * @param {string} [label] - optional label (default "Loading…")
 * @returns {{ hide: () => Promise<void> }}
 */
export function showPageLoader(container, label) {
    if (!container) return { hide: Promise.resolve };

    // Inject the loader HTML
    const wrapper = document.createElement('div');
    wrapper.innerHTML = _pageLoaderHTML.trim();
    const loaderEl = wrapper.firstElementChild;
    container.appendChild(loaderEl);

    // Update label if provided
    if (label) {
        const labelEl = loaderEl.querySelector('.page-preloader-label');
        if (labelEl) labelEl.textContent = label;
    }

    if (prefersReducedMotion()) {
        // Show letters immediately, no animation
        loaderEl.querySelectorAll('.page-preloader-letter').forEach(l => l.style.opacity = '1');
        return {
            hide: async () => {
                loaderEl.style.display = 'none';
                loaderEl.remove();
            }
        };
    }

    const letters = loaderEl.querySelectorAll('.page-preloader-letter');
    const bar = loaderEl.querySelector('.page-preloader-bar');
    const glow = loaderEl.querySelector('.page-preloader-glow');

    // Entrance animation
    const tl = createTimeline();

    tl.add(letters, {
        opacity: [0, 1],
        translateY: [20, 0],
        scale: [0.85, 1],
        delay: stagger(60),
        duration: 400,
        ease: 'outQuint',
    });

    if (glow) {
        tl.add(glow, {
            opacity: [0, 0.5, 0.3],
            scale: [0.5, 1.1, 1],
            duration: 600,
            ease: 'outExpo',
        }, '-=200');
    }

    if (bar) {
        tl.add(bar, {
            scaleX: [0, 1],
            duration: 1200,
            ease: 'inOutQuad',
        }, '-=400');
    }

    return {
        /**
         * Animate the page preloader out and remove it from the DOM.
         */
        hide: () => new Promise((resolve) => {
            animate(loaderEl, {
                opacity: [1, 0],
                scale: [1, 0.95],
                duration: 350,
                ease: 'inQuad',
                onComplete: () => {
                    loaderEl.remove();
                    resolve();
                },
            });
        }),
    };
}

// ─── Landing Page Hero ─────────────────────────────────────────────

/**
 * Cinematic landing hero entrance: staggered reveal of nav → kicker → title → subtitle → CTAs → scroll indicator.
 * @param {HTMLElement} container - the #page-landing element
 */
export function animateLandingHero(container) {
    if (!container || prefersReducedMotion()) return;

    const nav = container.querySelector('#landing-nav');
    const heroContent = container.querySelector('#landing-hero-content');
    const scrollInd = container.querySelector('#landing-scroll-indicator');

    if (!heroContent) return;

    const animEls = heroContent.querySelectorAll('[data-anim="hero"]');

    const tl = createTimeline();

    // Nav fades in
    if (nav) {
        nav.style.opacity = '0';
        tl.add(nav, {
            opacity: [0, 1],
            translateY: [-20, 0],
            duration: 500,
            ease: 'outQuint',
        });
    }

    // Hero content elements stagger in
    animEls.forEach((el, i) => {
        el.style.opacity = '0';
        tl.add(el, {
            opacity: [0, 1],
            translateY: [35, 0],
            duration: 600,
            ease: 'outQuint',
        }, i === 0 ? '+=150' : '-=350');
    });

    // Scroll indicator bounces in
    if (scrollInd) {
        scrollInd.style.opacity = '0';
        tl.add(scrollInd, {
            opacity: [0, 1],
            translateY: [20, 0],
            duration: 500,
            ease: 'outQuint',
        }, '-=200');

        // Continuous bounce
        animate(scrollInd.querySelector('svg'), {
            translateY: [0, 8, 0],
            duration: 1500,
            ease: 'inOutQuad',
            loop: true,
        });
    }
}
