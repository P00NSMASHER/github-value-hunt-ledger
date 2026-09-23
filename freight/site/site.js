"use strict";

(() => {
  const byId = (id) => document.getElementById(id);

  const revealItems = document.querySelectorAll(".reveal-image");
  if ("IntersectionObserver" in window && revealItems.length) {
    document.documentElement.classList.add("js");
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      }
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    for (const item of revealItems) observer.observe(item);
  }

  const checkoutReturn = byId("checkout-return");
  const returnedFromCheckout =
    new URLSearchParams(window.location.search).get("checkout") === "complete";
  if (checkoutReturn && returnedFromCheckout) {
    checkoutReturn.hidden = false;
    checkoutReturn.focus({ preventScroll: true });
    checkoutReturn.scrollIntoView({ block: "center" });
  }

  const service = byId("servicePrice");
  const recovery = byId("recoveryAmount");
  const currency = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });

  const updateCalculator = () => {
    const fixed = Number(service.value);
    const enteredRecovery = Number(recovery.value);
    const realized = Number.isFinite(enteredRecovery)
      ? Math.max(0, Math.min(1_000_000_000, enteredRecovery))
      : 0;
    const recoveryFee = realized * 0.2;
    const customerShare = realized - recoveryFee;
    const totalCharges = fixed + recoveryFee;

    byId("customerShare").textContent = currency.format(customerShare);
    byId("recoveryFee").textContent = currency.format(recoveryFee);
    byId("fixedFee").textContent = currency.format(fixed);
    byId("totalCharges").textContent = currency.format(totalCharges);
    byId("calculatorNote").textContent =
      `The fixed service fee is separate from the 80/20 split. In this example, ` +
      `the customer's gross realized recovery is ${currency.format(realized)}, ` +
      `the customer keeps ${currency.format(customerShare)} of that recovery, and ` +
      `total Freight Recovery charges are ${currency.format(totalCharges)}: ` +
      `${currency.format(fixed)} fixed plus ${currency.format(recoveryFee)} recovery fee.`;
  };

  service.addEventListener("change", updateCalculator);
  recovery.addEventListener("input", updateCalculator);
  updateCalculator();
})();
