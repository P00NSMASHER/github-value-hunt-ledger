"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const all = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const EVENTS = Object.freeze({
    landingPageViewed: "freight_landing_page_viewed",
    freeAuditCtaClicked: "freight_free_audit_cta_clicked",
    howItWorksClicked: "freight_how_it_works_clicked",
    auditFormStarted: "freight_audit_form_started",
    auditFormStepCompleted: "freight_audit_form_step_completed",
    auditFormCompleted: "freight_audit_form_completed",
    auditRequestPrepared: "freight_audit_request_prepared",
    auditRequestEmailOpened: "freight_audit_request_email_opened",
    secureDataRouteIssued: "freight_secure_data_route_issued",
    dataSubmitted: "freight_data_submitted",
    qualifiedLead: "freight_qualified_lead",
    auditCompleted: "freight_audit_completed",
    recoveryOpportunityIdentified: "freight_recovery_opportunity_identified",
    recoveryEngagementStarted: "freight_recovery_engagement_started",
    recoveryEngagementAccepted: "freight_recovery_engagement_accepted",
    actualRecoveryRecorded: "freight_actual_recovery_recorded",
    controlledDemoDownloaded: "freight_controlled_demo_downloaded"
  });

  const track = (eventName, properties = {}) => {
    const detail = Object.freeze({
      event: eventName,
      properties: { ...properties },
      occurredAt: new Date().toISOString()
    });
    window.dispatchEvent(new CustomEvent("freight:analytics", { detail }));
    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({ event: eventName, ...properties });
    }
  };

  window.FreightRecoveryAnalytics = Object.freeze({ events: EVENTS, track });
  track(EVENTS.landingPageViewed, { page: document.body.classList.contains("document-page") ? "document" : "home" });

  const eventForTrackName = Object.freeze({
    free_audit_cta_clicked: EVENTS.freeAuditCtaClicked,
    how_it_works_clicked: EVENTS.howItWorksClicked,
    controlled_demo_downloaded: EVENTS.controlledDemoDownloaded
  });
  for (const item of all("[data-track]")) {
    item.addEventListener("click", () => {
      const eventName = eventForTrackName[item.dataset.track];
      if (eventName) track(eventName, { placement: item.closest("section")?.id || "header" });
    });
  }

  const menuToggle = byId("menuToggle");
  const mainNav = byId("mainNav");
  if (menuToggle && mainNav) {
    const closeMenu = () => {
      menuToggle.setAttribute("aria-expanded", "false");
      mainNav.classList.remove("is-open");
      document.body.classList.remove("menu-open");
    };
    menuToggle.addEventListener("click", () => {
      const open = menuToggle.getAttribute("aria-expanded") !== "true";
      menuToggle.setAttribute("aria-expanded", String(open));
      mainNav.classList.toggle("is-open", open);
      document.body.classList.toggle("menu-open", open);
    });
    for (const link of all("a", mainNav)) link.addEventListener("click", closeMenu);
    window.addEventListener("resize", () => {
      if (window.innerWidth > 860) closeMenu();
    });
  }

  const config = window.FreightRecoveryConfig || {};
  const contingencyRate = Number(config.contingencyRecoveryRate);
  const hasValidRate = Number.isFinite(contingencyRate) && contingencyRate > 0 && contingencyRate < 1;
  const configuredRateLabel = hasValidRate
    ? String(config.contingencyRecoveryRateLabel || `${contingencyRate * 100}%`)
    : "Rate confirmed before engagement";
  for (const label of all("[data-rate-label]")) label.textContent = configuredRateLabel;

  const currency = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });
  const recoveryInput = byId("actualRecovery");
  const updateCalculator = () => {
    if (!recoveryInput) return;
    const entered = Number(recoveryInput.value);
    const actual = Number.isFinite(entered) ? Math.max(0, Math.min(1_000_000_000, entered)) : 0;
    const fee = hasValidRate ? actual * contingencyRate : 0;
    const customerNet = actual - fee;
    byId("actualRecoveredDisplay").textContent = currency.format(actual);
    byId("recoveryFeeDisplay").textContent = hasValidRate ? currency.format(fee) : "Confirmed in engagement";
    byId("customerNetDisplay").textContent = hasValidRate ? currency.format(customerNet) : "Confirmed in engagement";
  };
  if (recoveryInput) {
    recoveryInput.addEventListener("input", updateCalculator);
    updateCalculator();
  }

  const auditForm = byId("auditForm");
  if (auditForm) {
    let formStarted = false;
    let preparedSummary = "";
    const formError = byId("formError");

    const markStarted = () => {
      if (formStarted) return;
      formStarted = true;
      track(EVENTS.auditFormStarted);
    };
    auditForm.addEventListener("input", markStarted, { once: true });

    const valuesFor = (name) => all(`input[name='${name}']:checked`, auditForm).map((field) => field.value);
    const fieldValue = (id) => byId(id)?.value.trim() || "";
    const makeReference = () => {
      const date = new Date().toISOString().slice(0, 10).replaceAll("-", "");
      const random = new Uint32Array(1);
      if (window.crypto?.getRandomValues) window.crypto.getRandomValues(random);
      else random[0] = Date.now() % 0xffffffff;
      return `FR-${date}-${random[0].toString(16).toUpperCase().padStart(8, "0").slice(0, 6)}`;
    };

    const setError = (message) => {
      if (formError) formError.textContent = message;
    };

    const validate = () => {
      setError("");
      for (const field of all("input[required],select[required],textarea[required]", auditForm)) {
        field.removeAttribute("aria-invalid");
        if (!field.checkValidity()) {
          field.setAttribute("aria-invalid", "true");
          setError("Complete the required fields before continuing.");
          field.focus();
          return false;
        }
      }
      if (!auditForm.querySelector("input[name='modes']:checked")) {
        setError("Choose at least one freight type.");
        byId("modesGroup")?.scrollIntoView({ block: "center", behavior: "smooth" });
        return false;
      }
      return true;
    };

    for (const field of all("input,select,textarea", auditForm)) {
      field.addEventListener("input", () => {
        if (field.checkValidity()) field.removeAttribute("aria-invalid");
        setError("");
      });
    }

    const issueNotes = byId("issueNotes");
    if (issueNotes) {
      issueNotes.addEventListener("input", () => {
        const count = byId("noteCount");
        if (count) count.textContent = String(issueNotes.value.length);
      });
    }

    const buildSummary = (reference) => [
      "FREE RECOVERY AUDIT REQUEST",
      `Reference: ${reference}`,
      "",
      `Contact: ${fieldValue("fullName")}`,
      `Work email: ${fieldValue("workEmail")}`,
      `Company: ${fieldValue("companyName")}`,
      "",
      `Annual freight spend: ${fieldValue("annualSpend")}`,
      `Freight types: ${valuesFor("modes").join(", ")}`,
      `Monthly shipments: ${fieldValue("monthlyShipments") || "Not provided"}`,
      `Invoice history: ${fieldValue("invoiceHistory") || "Not provided"}`,
      `Major carriers/context: ${fieldValue("majorCarriers") || "Not provided"}`,
      `Available records: ${valuesFor("records").join(", ") || "Not provided"}`,
      `Known or suspected issue: ${fieldValue("suspectedIssues") || "Not provided"}`,
      `General reason for review: ${fieldValue("issueNotes") || "Not provided"}`,
      "",
      "No freight records or credentials are attached. Please review fit and, if appropriate, confirm scope and an approved secure intake route."
    ].join("\n");

    auditForm.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!validate()) return;

      const contactEmail = document.querySelector('meta[name="freight-contact-email"]')?.content.trim() || "";
      const sendLink = byId("sendAuditRequest");
      if (!contactEmail || !sendLink) {
        setError("The business inbox is temporarily unavailable. Please try again later.");
        return;
      }

      const reference = makeReference();
      preparedSummary = buildSummary(reference);
      const subject = encodeURIComponent(`Free Recovery Audit Request — ${fieldValue("companyName")} — ${reference}`);
      const body = encodeURIComponent(preparedSummary);
      sendLink.href = `mailto:${contactEmail}?subject=${subject}&body=${body}`;
      sendLink.removeAttribute("aria-disabled");

      auditForm.hidden = true;
      const ready = byId("auditReady");
      ready.hidden = false;
      ready.focus({ preventScroll: true });
      ready.scrollIntoView({ block: "center", behavior: "smooth" });

      track(EVENTS.auditFormCompleted, { completedSteps: 1 });
      track(EVENTS.auditRequestPrepared, { reference });
      window.setTimeout(() => {
        window.location.href = sendLink.href;
      }, 80);
    });

    byId("sendAuditRequest")?.addEventListener("click", (event) => {
      if (event.currentTarget.getAttribute("aria-disabled") === "true") event.preventDefault();
      else track(EVENTS.auditRequestEmailOpened);
    });

    byId("copyAuditSummary")?.addEventListener("click", async () => {
      const output = byId("copyStatus");
      try {
        await navigator.clipboard.writeText(preparedSummary);
        output.textContent = "Request details copied.";
      } catch (_error) {
        output.textContent = "Copy was unavailable. Use the prepared email instead.";
      }
    });
  }

})();
