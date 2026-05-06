/**
 * CineDrop Page Loader
 * Fetches page HTML fragments from /pages/*.html and injects them into #page-host
 * Exposes window.pages_ready promise so other scripts can wait for pages to load
 */

const PAGE_FILES = [
    "login",
    "register",
    "discover",
    "movies",
    "series",
    "detail",
    "watching",
    "watchlists"
];

window.pages_ready = (async function load_pages() {
    const page_host = document.getElementById("page-host");
    if (!page_host) return;

    const fetch_promises = PAGE_FILES.map(async (page_name) => {
        try {
            const response = await fetch(`pages/${page_name}.html`);
            if (!response.ok) {
                console.warn(`Failed to load page: ${page_name}.html (${response.status})`);
                return null;
            }
            const html = await response.text();
            return { name: page_name, html: html };
        } catch (err) {
            console.warn(`Error loading page ${page_name}:`, err);
            return null;
        }
    });

    const results = await Promise.all(fetch_promises);

    results.forEach((result) => {
        if (result && result.html) {
            const wrapper = document.createElement("div");
            wrapper.innerHTML = result.html;
            const page_element = wrapper.firstElementChild;
            if (page_element) {
                page_host.appendChild(page_element);
            }
        }
    });

    console.log("Pages loaded");
})();
