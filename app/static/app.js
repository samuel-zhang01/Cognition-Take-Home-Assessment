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
  message.textContent = "Saving…";
  try {
    const response = await fetch(form.dataset.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || result.error || "Request failed");
    window.location.reload();
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
});
