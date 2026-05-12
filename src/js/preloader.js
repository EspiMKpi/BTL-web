/**
 * VozFlix Preloader
 * Shows a cinematic branded loading screen while pages load.
 */

import { animatePreloader, prefersReducedMotion } from './animations.js';

/**
 * Initialize the preloader. Returns a Promise that resolves
 * when the preloader animation completes and it's safe to show content.
 *
 * @param {Promise} pagesReady - the pages_ready promise from pages.js
 * @param {Function} [onBeforeReveal] - called just before the preloader slides up
 * @returns {Promise}
 */
export async function initPreloader(pagesReady, onBeforeReveal) {
    const el = document.getElementById('preloader');
    if (!el) return;

    // If reduced motion, skip animation entirely
    if (prefersReducedMotion()) {
        el.style.display = 'none';
        return;
    }

    // Wait for pages to load (with a minimum display time for the animation)
    const MIN_DISPLAY = 1800; // ms — enough time for the full animation
    const start = Date.now();

    await pagesReady;

    const elapsed = Date.now() - start;
    if (elapsed < MIN_DISPLAY) {
        await new Promise(r => setTimeout(r, MIN_DISPLAY - elapsed));
    }

    // Run the anime.js preloader animation, passing the reveal callback
    await animatePreloader(el, onBeforeReveal);
}
