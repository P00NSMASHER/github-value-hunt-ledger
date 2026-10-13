/* RETALLY social landing worksheet — local-only, no analytics or network.
 *
 * Anonymous amounts are processed in-browser for education. No storage,
 * request, beacon, tracking event, download payload or form submission.
 * Node exports the pure functions for offline correctness tests.
 */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (typeof document !== "undefined") api.mount(document, typeof window === "undefined" ? null : window);
})(typeof globalThis === "undefined" ? this : globalThis, function () {
  "use strict";

  const MAX_CENTS = 100000000000; // $1 billion, strictly bounded
  const CURRENCY = new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2
  });
  const PUBLIC_WORKSHEET_URL = "https://www.retallyrecovery.com/freight-invoice-audit-checklist#worksheet";
  const SAMPLE = Object.freeze({
    billed: "1167.60", expected: "1042.60", credits: "0.00"
  });

  function parseMoney(value) {
    if (typeof value !== "string") return { ok: false, error: "Enter a dollar amount." };
    const trimmed = value.trim();
    if (!trimmed) return { ok: false, error: "Enter an amount." };
    if (!/^(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,2})?$/.test(trimmed)) {
      return { ok: false, error: "Use a positive dollar amount with up to two decimals." };
    }
    const parts = trimmed.split(".");
    const dollars = Number(parts[0]);
    const fraction = Number((parts[1] || "").padEnd(2, "0"));
    const cents = dollars * 100 + fraction;
    if (!Number.isSafeInteger(cents) || cents > MAX_CENTS) {
      return { ok: false, error: "Use an amount no larger than $1 billion." };
    }
    return { ok: true, cents };
  }

  function calculate(values) {
    if (!values || typeof values !== "object") {
      return { ok: false, error: "Enter sample or anonymized amounts.", field: "billed" };
    }
    const parsed = {};
    for (const field of ["billed", "expected", "credits"]) {
      const item = parseMoney(values[field]);
      if (!item.ok) return { ok: false, error: item.error, field };
      parsed[field] = item.cents;
    }
    const originalDifference = parsed.billed - parsed.expected;
    const positiveDifference = Math.max(0, originalDifference);
    const eligiblePriorCredits = Math.min(positiveDifference, parsed.credits);
    const unresolved = positiveDifference - eligiblePriorCredits;
    const excessCredits = parsed.credits > positiveDifference;
    const result = {
      ok: true, billedCents: parsed.billed, expectedCents: parsed.expected,
      creditsCents: parsed.credits, positiveDifferenceCents: positiveDifference,
      reconciledCreditsCents: eligiblePriorCredits, unresolvedCents: unresolved,
      creditsExceedCandidate: excessCredits,
      state: originalDifference <= 0 ? "NO_POSITIVE_DIFFERENCE" :
             unresolved === 0 ? "NO_UNRESOLVED_POSITIVE_DIFFERENCE" :
             "CANDIDATE_ONLY",
      verifiedOvercharge: false, authorizedClaim: false, realizedRecoveryCents: null
    };
    return result;
  }

  function dollars(cents) {
    if (!Number.isSafeInteger(cents) || cents < 0 || cents > MAX_CENTS) {
      throw new RangeError("Only supported nonnegative integer cents can be formatted");
    }
    return CURRENCY.format(cents / 100);
  }

  function mount(doc, win) {
    if (!doc || typeof doc.getElementById !== "function") return false;
    const panel = doc.getElementById("invoiceWorksheet");
    if (!panel) return false;
    if (panel.dataset.initialized === "true") return true;
    const elements = {};
    for (const name of ["billed", "expected", "credits"]) {
      elements[name] = doc.getElementById("ws-" + name);
      if (!elements[name]) return false;
    }
    const difference = doc.getElementById("ws-difference");
    const remaining = doc.getElementById("ws-unresolved");
    const prior = doc.getElementById("ws-credit-applied");
    const status = doc.getElementById("ws-status");
    const error = doc.getElementById("ws-error");
    const sample = doc.getElementById("ws-sample");
    const clear = doc.getElementById("ws-clear");
    const print = doc.getElementById("ws-print");
    const copy = doc.getElementById("ws-copy");
    const copyStatus = doc.getElementById("ws-copy-status");
    const share = doc.getElementById("ws-share");
    const shareStatus = doc.getElementById("ws-share-status");
    if (![difference, remaining, prior, status, error, sample, clear, print, copy, copyStatus, share, shareStatus].every(Boolean)) return false;
    panel.dataset.initialized = "true";
    panel.dataset.dataPolicy = "local-only-no-storage-or-upload";

    function emptyResult(message) {
      difference.textContent = "—";
      remaining.textContent = "—";
      prior.textContent = "—";
      status.textContent = message;
    }
    function update() {
      error.textContent = "";
      const values = {
        billed: elements.billed.value,
        expected: elements.expected.value,
        credits: elements.credits.value
      };
      const anyData = Object.values(values).some(x => !!String(x).trim());
      if (!anyData) {
        emptyResult("Enter illustrative or anonymized amounts to explore a candidate difference.");
        return;
      }
      const output = calculate(values);
      if (!output.ok) {
        emptyResult("No result calculated. Complete the three dollar fields.");
        if (String(values[output.field] || "").trim()) {
          error.textContent = output.error;
        }
        return;
      }
      difference.textContent = dollars(output.positiveDifferenceCents);
      prior.textContent = dollars(output.reconciledCreditsCents);
      remaining.textContent = dollars(output.unresolvedCents);
      if (output.state === "NO_POSITIVE_DIFFERENCE") {
        status.textContent = "The sample arithmetic shows no positive billed-minus-expected difference. No conclusion about billing accuracy follows.";
      } else if (output.state === "NO_UNRESOLVED_POSITIVE_DIFFERENCE") {
        status.textContent = "The supplied credits offset the sample difference. Reconcile actual credits and corrections before calling anything resolved.";
      } else {
        status.textContent = "Illustrative unresolved difference only. This is not a validated overcharge, authorized claim, approved credit or recovered amount.";
      }
      if (output.creditsExceedCandidate) {
        status.textContent += " Entered credits exceed the calculated difference; check whether they relate to this specific charge.";
      }
    }
    for (const item of Object.values(elements)) {
      item.addEventListener("input", update);
      item.addEventListener("change", update);
    }
    sample.addEventListener("click", function () {
      for (const key of Object.keys(elements)) elements[key].value = SAMPLE[key];
      update();
    });
    clear.addEventListener("click", function () {
      for (const item of Object.values(elements)) item.value = "";
      update();
      elements.billed.focus();
    });
    const originalClass = "worksheet-print-mode";
    function cleanupPrint() { doc.body?.classList.remove(originalClass); }
    print.addEventListener("click", function () {
      doc.body?.classList.add(originalClass);
      if (win && typeof win.print === "function") win.print();
      else cleanupPrint();
    });
    if (win && typeof win.addEventListener === "function") {
      win.addEventListener("afterprint", cleanupPrint);
    }
    copy.addEventListener("click", async function () {
      const publicUrl = PUBLIC_WORKSHEET_URL;
      try {
        if (!win?.navigator?.clipboard?.writeText) throw new Error("Clipboard unavailable");
        await win.navigator.clipboard.writeText(publicUrl);
        copyStatus.textContent = "Public worksheet link copied. No amounts were copied.";
      } catch (_error) {
        copyStatus.textContent = "Copy unavailable. Share the RETALLY freight invoice audit checklist page instead.";
      }
    });
    share.addEventListener("click", async function () {
      // A user-initiated OS share operation sends ONLY this public URL and
      // static guide title. Never serialize fields, checkboxes or calculated
      // amounts, and do not treat a share sheet as a customer inquiry.
      const payload = Object.freeze({
        title: "RETALLY | Free Freight Invoice Audit Checklist",
        text: "15 evidence checks and a sample-only invoice review worksheet.",
        url: PUBLIC_WORKSHEET_URL
      });
      try {
        if (typeof win?.navigator?.share === "function") {
          await win.navigator.share(payload);
          shareStatus.textContent = "Share sheet completed. No worksheet amounts were shared.";
        } else if (win?.navigator?.clipboard?.writeText) {
          await win.navigator.clipboard.writeText(PUBLIC_WORKSHEET_URL);
          shareStatus.textContent = "Public guide link copied. No worksheet amounts were shared.";
        } else {
          shareStatus.textContent = "Native sharing is unavailable. Use the copy-link option.";
        }
      } catch (err) {
        shareStatus.textContent = err?.name === "AbortError"
          ? "Share canceled. No worksheet amounts were shared."
          : "Sharing is unavailable. Use the copy-link option.";
      }
    });
    update();
    return true;
  }

  return Object.freeze({ parseMoney, calculate, dollars, mount, SAMPLE });
});
