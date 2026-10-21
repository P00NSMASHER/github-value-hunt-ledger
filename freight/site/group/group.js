"use strict";
// Native details remains usable without JavaScript. Escape closes the directory.
const businessMenu = document.querySelector(".business-menu");
if (businessMenu) {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && businessMenu.open) {
      businessMenu.open = false;
      businessMenu.querySelector("summary").focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!businessMenu.contains(event.target)) businessMenu.open = false;
  });
}
// Preserve previously distributed freight homepage anchors after consolidation.
if (window.location.pathname === "/") {
  const freightAnchors = new Set(["#start-audit", "#pricing", "#audit-output", "#how"]);
  if (freightAnchors.has(window.location.hash)) {
    window.location.replace("/recovery/" + window.location.search + window.location.hash);
  }
}
