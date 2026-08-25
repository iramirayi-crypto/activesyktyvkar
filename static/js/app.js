document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toast").forEach((element) => {
        bootstrap.Toast.getOrCreateInstance(element).show();
    });

    document.querySelectorAll("form.needs-validation").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                form.querySelector(":invalid")?.focus();
            }
            form.classList.add("was-validated");
        });
    });

    document.querySelectorAll("textarea[data-submit-shortcut]").forEach((textarea) => {
        textarea.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                textarea.form?.requestSubmit();
            }
        });
    });

    const backToTop = document.getElementById("backToTop");
    if (backToTop) {
        const updateVisibility = () => backToTop.classList.toggle("is-visible", window.scrollY > 560);
        window.addEventListener("scroll", updateVisibility, { passive: true });
        updateVisibility();
        backToTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    }
});
