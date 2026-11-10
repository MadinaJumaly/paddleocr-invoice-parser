document.addEventListener("DOMContentLoaded", () => {
  // Sidebar toggle (remembers state between pages).
  const toggle = document.getElementById("header-toggle");
  const nav = document.getElementById("nav-bar");
  if (toggle && nav) {
    const setOpen = (open) => {
      nav.classList.toggle("show", open);
      document.body.classList.toggle("nav-open", open);
      toggle.querySelector("i").className = open ? "bx bx-x" : "bx bx-menu";
      try { localStorage.setItem("navOpen", open ? "1" : "0"); } catch (e) {}
    };
    let saved = null;
    try { saved = localStorage.getItem("navOpen"); } catch (e) {}
    setOpen(saved === null ? window.innerWidth >= 992 : saved === "1");
    toggle.addEventListener("click", () => setOpen(!nav.classList.contains("show")));
  }

  // Upload form: show a spinner and block double submits while OCR runs.
  const form = document.getElementById("upload-form");
  if (form) {
    form.addEventListener("submit", () => {
      const btn = document.getElementById("upload-btn");
      btn.disabled = true;
      btn.querySelector(".spinner-border").classList.remove("d-none");
      btn.querySelector(".btn-label").textContent = "Распознаём…";
    });
  }

  // Ask before deleting a history entry.
  document.querySelectorAll('form[action*="/delete/"]').forEach((f) => {
    f.addEventListener("submit", (e) => {
      if (!window.confirm("Удалить запись и файлы?")) e.preventDefault();
    });
  });
});
