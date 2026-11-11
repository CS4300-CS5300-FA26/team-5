// Game page: a live character count for the review box, and a confirmation before
// removing a game (which also deletes its rating and review).
document.addEventListener("DOMContentLoaded", () => {
    const review = document.querySelector(".details-review-form textarea");
    const count = document.querySelector("[data-review-count]");
    if (review && count) {
        const max = Number(review.maxLength).toLocaleString("en-US");
        review.addEventListener("input", () => {
            count.textContent = `${review.value.length.toLocaleString("en-US")} / ${max}`;
        });
    }

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) event.preventDefault();
        });
    });
});
