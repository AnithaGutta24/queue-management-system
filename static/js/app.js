// Shared frontend JavaScript. The public queue display polls the Flask API
// every five seconds (its page-specific script is in display.html).
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form").forEach((form) => {
    if (form.dataset.confirmSubmit === "true") {
      form.addEventListener("submit", (event) => {
        if (!confirm("Are you sure you want to continue?")) {
          event.preventDefault();
        }
      });
    }
  });
});
