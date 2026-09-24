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
    let currentStep = 1;
    let formStarted = false;
    let preparedSummary = "";
    const steps = all("[data-form-step]", auditForm);
    const progressItems = all("[data-progress]");
    const formError = byId("formError");

    const markStarted = () => {
      if (formStarted) return;
      formStarted = true;
      track(EVENTS.auditFormStarted);
    };
    auditForm.addEventListener("input", markStarted, { once: true });

    const showStep = (stepNumber) => {
      currentStep = stepNumber;
      for (const step of steps) step.hidden = Number(step.dataset.formStep) !== stepNumber;
      for (const item of progressItems) {
        const number = Number(item.dataset.progress);
        item.classList.toggle("is-current", number === stepNumber);
        item.classList.toggle("is-complete", number < stepNumber);
      }
      const active = steps.find((step) => Number(step.dataset.formStep) === stepNumber);
      const focusTarget = active?.querySelector("input,select,textarea");
      if (focusTarget) focusTarget.focus({ preventScroll: true });
      active?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    };

    const stepError = (step) => step.querySelector(".step-error") || formError;
    const setError = (step, message) => {
      const output = stepError(step);
      if (output) output.textContent = message;
    };
    const clearInvalid = (step) => {
      setError(step, "");
      for (const field of all("[aria-invalid='true']", step)) field.removeAttribute("aria-invalid");
    };

    const validateStep = (number) => {
      const step = steps.find((item) => Number(item.dataset.formStep) === number);
      if (!step) return false;
      clearInvalid(step);
      const requiredFields = all("input[required],select[required],textarea[required]", step);
      for (const field of requiredFields) {
        if (!field.checkValidity()) {
          field.setAttribute("aria-invalid", "true");
          setError(step, "Complete the required fields before continuing.");
          field.focus();
          return false;
        }
      }
      if (number === 2 && !step.querySelector("input[name='modes']:checked")) {
        setError(step, "Choose at least one freight type.");
        step.querySelector("#modesGroup")?.scrollIntoView({ block: "center" });
        return false;
      }
      if (number === 3 && !step.querySelector("input[name='records']:checked")) {
        setError(step, "Choose at least one available record type.");
        step.querySelector("#recordsGroup")?.scrollIntoView({ block: "center" });
        return false;
      }
      return true;
    };

    for (const button of all("[data-next-step]", auditForm)) {
      button.addEventListener("click", () => {
        if (!validateStep(currentStep)) return;
        track(EVENTS.auditFormStepCompleted, { step: currentStep });
        showStep(Number(button.dataset.nextStep));
      });
    }
    for (const button of all("[data-prev-step]", auditForm)) {
      button.addEventListener("click", () => showStep(Number(button.dataset.prevStep)));
    }

    for (const field of all("input,select,textarea", auditForm)) {
      field.addEventListener("input", () => {
        if (field.checkValidity()) field.removeAttribute("aria-invalid");
        const containingStep = field.closest("[data-form-step]");
        if (containingStep) setError(containingStep, "");
      });
    }

    const issueNotes = byId("issueNotes");
    if (issueNotes) {
      issueNotes.addEventListener("input", () => {
        byId("noteCount").textContent = String(issueNotes.value.length);
      });
    }

    const valuesFor = (name) => all(`input[name='${name}']:checked`, auditForm).map((field) => field.value);
    const fieldValue = (id) => byId(id)?.value.trim() || "";
    const makeReference = () => {
      const date = new Date().toISOString().slice(0, 10).replaceAll("-", "");
      const random = new Uint32Array(1);
      if (window.crypto?.getRandomValues) window.crypto.getRandomValues(random);
      else random[0] = Date.now() % 0xffffffff;
      return `FR-${date}-${random[0].toString(16).toUpperCase().padStart(8, "0").slice(0, 8)}`;
    };

    const buildSummary = (reference) => [
      "FREE RECOVERY AUDIT QUALIFICATION",
      `Reference: ${reference}`,
      "",
      `Contact: ${fieldValue("fullName")}`,
      `Work email: ${fieldValue("workEmail")}`,
      `Company: ${fieldValue("companyName")}`,
      `Role: ${fieldValue("role")}`,
      "",
      `Annual freight spend: ${fieldValue("annualSpend")}`,
      `Monthly shipments: ${fieldValue("monthlyShipments")}`,
      `Freight types: ${valuesFor("modes").join(", ")}`,
      `Active carriers: ${fieldValue("carrierCount")}`,
      `Major carriers/context: ${fieldValue("majorCarriers") || "Not provided"}`,
      "",
      `Invoice history: ${fieldValue("invoiceHistory")}`,
      `Approximate invoice count: ${fieldValue("invoiceCount")}`,
      `Available records: ${valuesFor("records").join(", ")}`,
      `Prior audit: ${fieldValue("priorAudit")}`,
      `Known or suspected issue: ${fieldValue("suspectedIssues")}`,
      `General reason for review: ${fieldValue("issueNotes") || "Not provided"}`,
      "",
      "I have not attached freight records or credentials. Please review fit and, if appropriate, confirm scope and an approved secure intake route."
    ].join("\n");

    auditForm.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!validateStep(3)) return;
      const reference = makeReference();
      preparedSummary = buildSummary(reference);
      const contactEmail = document.querySelector('meta[name="freight-contact-email"]')?.content.trim() || "";
      const sendLink = byId("sendAuditRequest");
      if (contactEmail && sendLink) {
        const subject = encodeURIComponent(`Free Recovery Audit Request — ${fieldValue("companyName")} — ${reference}`);
        const body = encodeURIComponent(preparedSummary);
        sendLink.href = `mailto:${contactEmail}?subject=${subject}&body=${body}`;
        sendLink.removeAttribute("aria-disabled");
      } else if (sendLink) {
        sendLink.href = "#contact-pending";
        sendLink.setAttribute("aria-disabled", "true");
        sendLink.textContent = "Business inbox configuration pending";
      }
      byId("requestReference").textContent = reference;
      auditForm.hidden = true;
      document.querySelector(".form-progress").hidden = true;
      const ready = byId("auditReady");
      ready.hidden = false;
      ready.focus({ preventScroll: true });
      ready.scrollIntoView({ block: "center", behavior: "smooth" });
      track(EVENTS.auditFormCompleted, { completedSteps: 3 });
      track(EVENTS.auditRequestPrepared, { reference });
    });

    byId("sendAuditRequest")?.addEventListener("click", (event) => {
      if (event.currentTarget.getAttribute("aria-disabled") === "true") event.preventDefault();
      else track(EVENTS.auditRequestEmailOpened, { reference: byId("requestReference")?.textContent || "" });
    });

    byId("copyAuditSummary")?.addEventListener("click", async () => {
      const output = byId("copyStatus");
      try {
        await navigator.clipboard.writeText(preparedSummary);
        output.textContent = "Request summary copied.";
      } catch (_error) {
        output.textContent = "Copy was unavailable. Use the prepared email instead.";
      }
    });
  }
})();
