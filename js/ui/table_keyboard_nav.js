export function initTableKeyboardNav() {
  const headers = document.querySelectorAll("th.sortable, th.filterable");
  headers.forEach((header) => {
    if (!header.hasAttribute("tabindex")) {
      header.setAttribute("tabindex", "0");
    }

    if (header.classList.contains("sortable") && !header.hasAttribute("aria-sort")) {
      header.setAttribute("aria-sort", "none");
    }

    header.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        header.click();
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", initTableKeyboardNav);
