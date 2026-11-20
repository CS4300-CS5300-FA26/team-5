// The search box in the top bar (base.html), on every page.
// - As you type, a menu offers both ways to search the same text: by title, or ask AI. The highlighted row is
//   what Enter does; it follows the AI mode switch, and picking a row also sets the switch.
// - With an empty box the menu shows example descriptions, so people find out AI mode exists.
// - "/" focuses the box from anywhere on the page.
// - A search shows a progress line under the top bar. A search by description waits on the AI for a few
//   seconds, so it also swaps the page for a loading panel until the results arrive.
(() => {
    const LOADING_STEPS = [
        "Reading your description…",
        "Thinking of games that fit…",
        "Checking them on IGDB…",
        "Almost there…",
    ];
    const EXAMPLES = ["zelda but darker", "a cozy co-op farming game on Switch", "stuck in a time loop"];
    const TITLE_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';
    const AI_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l1.9 5.6L19.5 9.5l-5.6 1.9L12 17l-1.9-5.6L4.5 9.5l5.6-1.9zM19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"/></svg>';

    document.addEventListener("DOMContentLoaded", () => {
        const form = document.querySelector("[data-search]");
        const progress = document.querySelector("[data-search-progress]");
        const loading = document.querySelector("[data-search-loading]");
        if (!form || !progress || !loading) {
            return;
        }
        const box = form.elements.q;
        const ai = form.elements.mode;
        const menu = form.querySelector('[role="listbox"]');
        const step = loading.querySelector("[data-search-loading-step]");
        const searchPath = new URL(form.action).pathname;
        let rows = [];
        let active = -1;
        let timer = null;

        box.setAttribute("role", "combobox");
        box.setAttribute("aria-controls", menu.id);
        box.setAttribute("aria-expanded", "false");
        box.setAttribute("aria-autocomplete", "none");

        function showMode() {
            box.placeholder = ai.checked ? box.dataset.describePlaceholder : box.dataset.titlePlaceholder;
        }

        // Menu rows: {mode, text, title, detail}. mode "describe" asks AI; "" searches titles. With text in
        // the box, the rows name the two ways to search it (the text itself is right above, in the box);
        // with an empty box, they are example descriptions.
        function render() {
            const text = box.value.trim();
            if (text) {
                rows = [
                    {mode: "", text, title: "Search titles", detail: "Find a game by its name"},
                    {mode: "describe", text, title: "Ask AI", detail: "Find games that fit what you describe"},
                ];
                active = ai.checked ? 1 : 0;
            } else {
                rows = EXAMPLES.map((example) => ({mode: "describe", text: example, title: example, detail: ""}));
                active = -1;
            }
            menu.replaceChildren();
            if (!text) {
                const lead = document.createElement("p");
                lead.className = "topbar-menu-lead";
                lead.textContent = "Not sure of the title? Describe it and ask AI";
                menu.append(lead);
            }
            rows.forEach((row, index) => {
                const option = document.createElement("div");
                option.id = `${menu.id}-${index}`;
                option.className = "topbar-option" + (row.mode ? " is-ai" : "");
                option.setAttribute("role", "option");
                option.innerHTML = row.mode ? AI_ICON : TITLE_ICON;
                const words = document.createElement("span");
                words.className = "topbar-option-text";
                const title = document.createElement("span");
                title.className = "topbar-option-title";
                title.textContent = row.title;
                words.append(title);
                if (row.detail) {
                    const detail = document.createElement("span");
                    detail.className = "topbar-option-detail";
                    detail.textContent = row.detail;
                    words.append(detail);
                }
                const enter = document.createElement("kbd");
                enter.className = "topbar-option-enter";
                enter.setAttribute("aria-hidden", "true");
                enter.textContent = "↵";
                option.append(words, enter);
                // mousedown, not click: the box keeps focus, so the menu does not close first
                option.addEventListener("mousedown", (event) => {
                    event.preventDefault();
                    run(row);
                });
                option.addEventListener("mousemove", () => highlight(index));
                menu.append(option);
            });
            highlight(active);
        }

        function highlight(index) {
            active = index;
            menu.querySelectorAll('[role="option"]').forEach((option, i) => {
                option.setAttribute("aria-selected", String(i === index));
            });
            if (index >= 0) {
                box.setAttribute("aria-activedescendant", `${menu.id}-${index}`);
            } else {
                box.removeAttribute("aria-activedescendant");
            }
        }

        function open() {
            render();
            menu.hidden = false;
            box.setAttribute("aria-expanded", "true");
        }

        function close() {
            menu.hidden = true;
            box.setAttribute("aria-expanded", "false");
            box.removeAttribute("aria-activedescendant");
        }

        function run(row) {
            box.value = row.text;
            ai.checked = Boolean(row.mode);
            showMode();
            close();
            form.requestSubmit();
        }

        function startLoading(describe, text) {
            progress.classList.toggle("is-ai", describe);
            progress.hidden = false;
            if (!describe) {
                return;
            }
            document.body.classList.add("is-searching");
            loading.querySelector("[data-search-loading-query]").textContent = `“${text}”`;
            step.textContent = LOADING_STEPS[0];
            loading.hidden = false;
            let next = 1;
            timer = setInterval(() => {
                step.textContent = LOADING_STEPS[next];
                next += 1;
                if (next === LOADING_STEPS.length) {
                    clearInterval(timer);   // stay on the last step until the page loads
                }
            }, 1800);
        }

        box.addEventListener("focus", open);
        box.addEventListener("input", open);
        box.addEventListener("blur", close);
        box.addEventListener("keydown", (event) => {
            if (menu.hidden && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
                open();
                return;
            }
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                const move = event.key === "ArrowDown" ? 1 : -1;
                highlight((active + move + rows.length) % rows.length);
            } else if (event.key === "Enter" && !menu.hidden && active >= 0) {
                event.preventDefault();
                run(rows[active]);
            } else if (event.key === "Escape" && !menu.hidden) {
                close();
            }
        });

        ai.addEventListener("change", () => {
            showMode();
            box.focus();
            open();
        });

        document.addEventListener("keydown", (event) => {
            const typing = event.target.closest("input, textarea, select, [contenteditable]");
            if (event.key === "/" && !typing && !event.ctrlKey && !event.metaKey && !event.altKey) {
                event.preventDefault();
                box.focus();
                box.select();
            }
        });

        form.addEventListener("submit", (event) => {
            if (form.getAttribute("aria-busy") === "true") {
                event.preventDefault();   // already searching; ignore a second Enter
                return;
            }
            form.setAttribute("aria-busy", "true");
            close();
            box.blur();
            startLoading(ai.checked, box.value.trim());
        });

        // Links to search results (the Titles and AI picks tabs, the examples) load the same way
        document.addEventListener("click", (event) => {
            const link = event.target.closest("a[href]");
            if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey
                || event.shiftKey || event.altKey || link.target) {
                return;
            }
            const url = new URL(link.href, location.href);
            if (url.origin === location.origin && url.pathname === searchPath && url.searchParams.get("q")) {
                startLoading(url.searchParams.get("mode") === "describe", url.searchParams.get("q"));
            }
        });

        // Back from the results page restores this page from the cache; undo the loading state.
        window.addEventListener("pageshow", (event) => {
            if (!event.persisted) {
                return;
            }
            clearInterval(timer);
            form.removeAttribute("aria-busy");
            progress.hidden = true;
            document.body.classList.remove("is-searching");
            loading.hidden = true;
            showMode();
        });
    });
})();
