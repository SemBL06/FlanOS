const status = document.getElementById("status");
const likeness = document.getElementById("likeness");
const likenessValue = document.getElementById("likeness-value");

if (window.location.search.includes("saved=1")) {
  status.textContent = "Saved to data.yml";
}

likeness.addEventListener("input", () => {
  likenessValue.textContent = likeness.value;
});

document.getElementById("pudding-form").addEventListener("submit", () => {
  status.textContent = "Saving...";
});
