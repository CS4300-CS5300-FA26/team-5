// Light/dark theme for every page. Loaded in <head> so the theme is set before the page paints.
// Uses the visitor's saved choice, else their system setting, and sets Bootstrap's data-bs-theme.
(function () {
    const KEY = "theme";
    const root = document.documentElement;
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

    function saved() {
        try { return localStorage.getItem(KEY); } catch (e) { return null; }
    }

    function apply(theme) {
        root.setAttribute("data-bs-theme", theme);
        const toggle = document.getElementById("theme-toggle");
        if (toggle) toggle.setAttribute("aria-pressed", String(theme === "dark"));
    }

    apply(saved() || (systemDark.matches ? "dark" : "light"));

    systemDark.addEventListener("change", function (event) {
        if (!saved()) apply(event.matches ? "dark" : "light");
    });

    document.addEventListener("DOMContentLoaded", function () {
        const toggle = document.getElementById("theme-toggle");
        apply(root.getAttribute("data-bs-theme"));
        toggle.addEventListener("click", function () {
            const next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            try { localStorage.setItem(KEY, next); } catch (e) { /* private window: theme lasts for this page only */ }
            apply(next);
        });
    });
})();
