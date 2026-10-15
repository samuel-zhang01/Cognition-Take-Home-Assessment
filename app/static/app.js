const errorCopy = {
  stale_version: "Someone else changed this record. Reload to see the latest version.",
  invalid_transition: "This record has already been decided.",
  forbidden: "You don't have permission for this action.",
  validation_failed: "Add a reason of at least 3 characters.",
};

function showToast(text) {
  let toast = document.querySelector("#app-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "app-toast";
    toast.className = "toast";
    toast.setAttribute("role", "status");
    document.body.append(toast);
  }
  toast.textContent = text;
  toast.hidden = false;
}

function setMessage(target, text, isError = false) {
  target.textContent = text;
  target.classList.toggle("error", isError);
}

async function readResponse(response) {
  const result = await response.json();
  if (!response.ok) {
    const code = result.error || (response.status === 403 ? "forbidden" : "");
    throw new Error(errorCopy[code] || result.detail || "The request could not be completed.");
  }
  return result;
}

document.addEventListener("submit", async (event) => {
  const form = event.target.closest(".command-form");
  if (!form) return;
  event.preventDefault();
  const message = form.querySelector(".form-message");
  const payload = {};
  for (const [key, value] of new FormData(form).entries()) {
    if (key === "expected_version") payload[key] = Number(value);
    else if (key === "enabled") payload[key] = value === "true";
    else payload[key] = value;
  }
  if (event.submitter?.name) payload[event.submitter.name] = event.submitter.value;
  setMessage(message, "Saving");
  try {
    const response = await fetch(form.dataset.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await readResponse(response);
    showToast("Saved");
    window.setTimeout(() => window.location.reload(), 650);
  } catch (error) {
    setMessage(message, error.message, true);
  }
});

document.querySelectorAll("[data-table-search]").forEach((search) => {
  search.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    const page = search.closest("main, body");
    const table = page.querySelector("table");
    const rows = table
      ? table.querySelectorAll("tbody tr")
      : page.querySelectorAll(".flag-list > .flag-row");
    rows.forEach((row) => {
      row.hidden = Boolean(query) && !row.textContent.toLowerCase().includes(query);
    });
  });
});

document.querySelectorAll("tr[data-href]").forEach((row) => {
  row.setAttribute("tabindex", "0");
  row.setAttribute("role", "link");
  row.addEventListener("click", (event) => {
    if (event.target.closest("a, button, input, select, textarea")) return;
    window.location.href = row.dataset.href;
  });
  row.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      window.location.href = row.dataset.href;
    }
  });
});

document.querySelectorAll(".demo-account").forEach((button) => {
  button.addEventListener("click", () => {
    const username = document.querySelector('input[name="username"]');
    username.value = button.dataset.username;
    username.focus();
  });
});

document.querySelectorAll(".import-form").forEach((form) => {
  const module = form.dataset.module;
  const result = form.querySelector(".validation-result");
  const errors = form.querySelector(".validation-errors");
  const errorBody = errors.querySelector("tbody");
  const validateButton = form.querySelector(".validate-import");
  const commitButton = form.querySelector(".commit-import");

  const resetValidation = () => {
    form.dataset.validated = "false";
    commitButton.disabled = true;
    commitButton.textContent = "Import 0 rows";
    errors.hidden = true;
    errorBody.replaceChildren();
    result.textContent = "";
  };
  form.addEventListener("input", resetValidation);
  form.addEventListener("change", resetValidation);

  const submitImport = async (dryRun) => {
    const data = new FormData(form);
    data.set("dry_run", String(dryRun));
    const response = await fetch(`/api/import/${module}`, { method: "POST", body: data });
    return readResponse(response);
  };

  validateButton.addEventListener("click", async () => {
    if (!form.reportValidity()) return;
    resetValidation();
    setMessage(result, "Validating");
    try {
      const response = await submitImport(true);
      if (response.errors.length) {
        errors.hidden = false;
        response.errors.forEach((error) => {
          const row = document.createElement("tr");
          [error.row, error.column, error.message].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.append(cell);
          });
          errorBody.append(row);
        });
        setMessage(result, `${response.errors.length} validation errors found.`, true);
        return;
      }
      form.dataset.validated = "true";
      form.dataset.rowCount = response.rows;
      commitButton.textContent = `Import ${response.rows} rows`;
      commitButton.disabled = response.rows === 0;
      setMessage(result, `${response.rows} rows ready`);
    } catch (error) {
      setMessage(result, error.message, true);
    }
  });

  commitButton.addEventListener("click", async () => {
    if (form.dataset.validated !== "true" || !form.reportValidity()) return;
    commitButton.disabled = true;
    try {
      const response = await submitImport(false);
      if (response.errors.length) {
        errors.hidden = false;
        response.errors.forEach((error) => {
          const row = document.createElement("tr");
          [error.row, error.column, error.message].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.append(cell);
          });
          errorBody.append(row);
        });
        setMessage(result, `${response.errors.length} validation errors found.`, true);
        return;
      }
      showToast("Saved");
      window.setTimeout(() => window.location.reload(), 650);
    } catch (error) {
      setMessage(result, error.message, true);
      commitButton.disabled = false;
    }
  });
});
