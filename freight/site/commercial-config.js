"use strict";

window.FreightRecoveryConfig = Object.freeze({
  contingencyRecoveryRate: "__CONTINGENCY_RECOVERY_RATE__",
  contingencyRecoveryRateLabel: "__CONTINGENCY_RECOVERY_RATE_LABEL__"
});

(() => {
  const href = "foundry.css?v=foundry-20261007";
  if (document.querySelector("link[data-foundry-typography]")) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  link.dataset.foundryTypography = "true";
  document.head.appendChild(link);
})();
