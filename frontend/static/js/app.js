document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) toggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  document.querySelectorAll("[data-demo-form]").forEach(form => {
    form.addEventListener("submit", event => {
      event.preventDefault();
      const message = form.querySelector(".form-message");
      if (message) message.textContent = "Demo interface only. Connect this form to a FastAPI endpoint to enable it.";
    });
  });

  const fileInput = document.getElementById("fileInput");
  const selectedFile = document.getElementById("selectedFile");
  if (fileInput && selectedFile) fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    selectedFile.textContent = file ? `${file.name} (${(file.size / 1048576).toFixed(2)} MB)` : "No file selected";
  });

  const uploadForm = document.getElementById("uploadForm");
  if (uploadForm) uploadForm.addEventListener("submit", event => {
    event.preventDefault();
    const file = fileInput.files[0];
    const message = document.getElementById("uploadMessage");
    const allowed = [".pdf", ".docx", ".txt", ".csv"];
    const extension = file ? "." + file.name.split(".").pop().toLowerCase() : "";
    if (!file) message.textContent = "Choose a file first.";
    else if (!allowed.includes(extension)) message.textContent = "This file type is not allowed.";
    else if (file.size > 10 * 1024 * 1024) message.textContent = "The file exceeds the 10 MB limit.";
    else message.textContent = "Frontend checks passed. The backend upload endpoint is not connected yet.";
  });

  document.querySelectorAll("[data-revoke]").forEach(button => button.addEventListener("click", () => {
    alert("Demo only: no real permission was revoked. Backend authorization is required.");
  }));

  function searchTable(inputId, tableId, emptyId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    input.addEventListener("input", () => {
      const query = input.value.toLowerCase();
      let count = 0;
      table.querySelectorAll("tbody tr").forEach(row => {
        const match = row.innerText.toLowerCase().includes(query);
        row.hidden = !match;
        if (match) count++;
      });
      const empty = emptyId && document.getElementById(emptyId);
      if (empty) empty.hidden = count > 0;
    });
  }
  searchTable("documentSearch", "documentsTable", "noResults");
  searchTable("auditSearch", "auditTable");
});
