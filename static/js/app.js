document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toast").forEach((element) => {
        bootstrap.Toast.getOrCreateInstance(element).show();
    });

    document.querySelectorAll("form.needs-validation").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const skipValidation = event.submitter?.formNoValidate;
            if (!skipValidation && !form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                form.querySelector(":invalid")?.focus();
            }
            if (!skipValidation) {
                form.classList.add("was-validated");
            }
        });
    });

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-password-toggle]");
        if (!button) {
            return;
        }

        const field = button.closest("[data-password-field]");
        const input = field?.querySelector("[data-password-input]");
        const icon = button.querySelector("[data-password-toggle-icon]");
        if (!input || !icon) {
            return;
        }

        const showPassword = input.type === "password";
        input.type = showPassword ? "text" : "password";

        const label = showPassword ? "Скрыть пароль" : "Показать пароль";
        button.setAttribute("aria-label", label);
        button.setAttribute("title", label);
        button.setAttribute("aria-pressed", String(showPassword));
        icon.classList.toggle("bi-eye", !showPassword);
        icon.classList.toggle("bi-eye-slash", showPassword);
    });

    document.querySelectorAll("textarea[data-submit-shortcut]").forEach((textarea) => {
        textarea.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                textarea.form?.requestSubmit();
            }
        });
    });

    const formatDateDigits = (digits) => {
        const cleanDigits = digits.replace(/\D/g, "").slice(0, 8);
        return [
            cleanDigits.slice(0, 2),
            cleanDigits.slice(2, 4),
            cleanDigits.slice(4, 8),
        ].filter(Boolean).join(".");
    };

    const setDateCaret = (input, digitCount) => {
        let position = 0;
        let seenDigits = 0;
        while (position < input.value.length && seenDigits < digitCount) {
            if (/\d/.test(input.value[position])) {
                seenDigits += 1;
            }
            position += 1;
        }
        input.setSelectionRange(position, position);
    };

    document.querySelectorAll("input[data-date-mask]").forEach((input) => {
        input.addEventListener("keydown", (event) => {
            const position = input.selectionStart;
            if (position !== input.selectionEnd || position === null) {
                return;
            }

            const digits = input.value.replace(/\D/g, "").slice(0, 8);
            const digitsBefore = input.value.slice(0, position).replace(/\D/g, "").length;
            if (event.key === "Backspace" && input.value[position - 1] === ".") {
                event.preventDefault();
                input.value = formatDateDigits(
                    digits.slice(0, digitsBefore - 1) + digits.slice(digitsBefore)
                );
                setDateCaret(input, Math.max(0, digitsBefore - 1));
            } else if (event.key === "Delete" && input.value[position] === ".") {
                event.preventDefault();
                input.value = formatDateDigits(
                    digits.slice(0, digitsBefore) + digits.slice(digitsBefore + 1)
                );
                setDateCaret(input, digitsBefore);
            }
        });

        input.addEventListener("input", () => {
            const caret = input.selectionStart ?? input.value.length;
            const digitsBefore = input.value.slice(0, caret).replace(/\D/g, "").length;
            input.value = formatDateDigits(input.value);
            setDateCaret(input, digitsBefore);
        });
    });

    document.querySelectorAll("select[data-category-select]").forEach((select) => {
        const box = select.parentElement.querySelector("[data-category-description-box]");
        const name = box?.querySelector("[data-category-name]");
        const description = box?.querySelector("[data-category-description]");

        const updateCategoryDescription = () => {
            const option = select.selectedOptions[0];
            const text = option?.dataset.description?.trim() || "";
            if (!box || !name || !description) {
                return;
            }
            box.hidden = !text;
            name.textContent = text ? option.textContent.trim() : "";
            description.textContent = text;
        };

        select.addEventListener("change", updateCategoryDescription);
        updateCategoryDescription();
    });

    const backToTop = document.getElementById("backToTop");
    if (backToTop) {
        const updateVisibility = () => backToTop.classList.toggle("is-visible", window.scrollY > 560);
        window.addEventListener("scroll", updateVisibility, { passive: true });
        updateVisibility();
        backToTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    }
});
