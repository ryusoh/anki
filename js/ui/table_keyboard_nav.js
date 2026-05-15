export function initTableKeyboardNav() {
  const headers = document.querySelectorAll("th.sortable, th.filterable");
  headers.forEach((header) => {
    header.setAttribute("role", "button");
    if (!header.hasAttribute("tabindex")) {
      header.setAttribute("tabindex", "0");
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
