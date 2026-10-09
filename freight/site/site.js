"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const all = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const campaignParams = new URLSearchParams(window.location.search);
  const cleanCampaignValue = (name) => {
    const value = campaignParams.get(name);
    return value ? value.trim().slice(0, 120) : "";
  };
  const campaignContext = Object.freeze({
    utm_source: cleanCampaignValue("utm_source"),
    utm_medium: cleanCampaignValue("utm_medium"),
    utm_campaign: cleanCampaignValue("utm_campaign"),
    utm_term: cleanCampaignValue("utm_term"),
    utm_content: cleanCampaignValue("utm_content")
  });
  const nonEmptyCampaignContext = Object.freeze(
    Object.fromEntries(Object.entries(campaignContext).filter(([, value]) => value))
  );

  // Preserve acquisition attribution when a visitor follows a first-party
  // educational-page link to the free-audit form. Never tag offsite links or
  // downloads, and never overwrite a destination's existing campaign value.
  if (Object.keys(nonEmptyCampaignContext).length) {
    for (const anchor of all("a[href]")) {
      if (anchor.hasAttribute("download")) continue;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#")) continue;
      let target;
      try { target = new URL(href, window.location.href); }
      catch (_error) { continue; }
      if (target.origin !== window.location.origin ||
          !["http:", "https:"].includes(target.protocol) ||
          /\.(?:pdf|zip|csv|xlsx?|png|jpe?g|gif|webp|svg|js|css)$/i.test(target.pathname)) continue;
      let updated = false;
      for (const [key, value] of Object.entries(nonEmptyCampaignContext)) {
        if (!target.searchParams.has(key)) {
          target.searchParams.set(key, value);
          updated = true;
        }
      }
      if (updated) anchor.setAttribute("href", target.href);
    }
  }

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
      properties: { ...nonEmptyCampaignContext, ...properties },
      occurredAt: new Date().toISOString()
    });
    window.dispatchEvent(new CustomEvent("freight:analytics", { detail }));
    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({ event: eventName, ...nonEmptyCampaignContext, ...properties });
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

    let serverReady = false;
    let pendingRequestKey = null;
    let sending = false;
    const fallbackLink = byId("auditEmailFallback");
    const submitButton = auditForm.querySelector("button[type='submit']");
    const submitHint = auditForm.querySelector(".form-actions small");

    // Default remains the established email fallback. Only the verified backend
    // can opt a client into direct submission, and disabling it rolls clients back.
    if (["www.retallyrecovery.com", "retallyrecovery.com"].includes(window.location.hostname)) {
      fetch("/api/inquiry", { cache: "no-store", credentials: "same-origin" })
        .then(async (response) => response.ok ? response.json() : null)
        .then((status) => {
          if (!status?.online || !/^[a-zA-Z0-9_-]{10,}$/.test(status.siteKey)) return;
          serverReady = true;
          if (fallbackLink) fallbackLink.hidden = false;
          if (submitButton) submitButton.textContent = "Submit My Free Audit Request";
          if (submitHint) submitHint.textContent = "Submitted securely to RETALLY. No freight files or credentials, please.";
          const widget = document.createElement("div");
          widget.id = "auditTurnstile";
          widget.className = "cf-turnstile";
          widget.dataset.sitekey = status.siteKey;
          widget.dataset.action = "retally_audit";
          widget.dataset.theme = "light";
          formError?.before(widget);
          const script = document.createElement("script");
          script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
          script.async = true;
          script.defer = true;
          script.addEventListener("error", () => {
            serverReady = false;
            if (submitButton) submitButton.textContent = "Open My Free Audit Request";
            if (submitHint) submitHint.textContent = "Opens an email draft. Review it and press Send.";
          });
          document.head.appendChild(script);
        })
        .catch(() => { /* Offline/unconfigured: preserve working mailto method. */ });
    }

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
        pendingRequestKey = null;
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
      Object.keys(nonEmptyCampaignContext).length
        ? `Acquisition source: ${Object.entries(nonEmptyCampaignContext).map(([key, value]) => `${key}=${value}`).join(", ")}`
        : "Acquisition source: Direct / untagged",
      "",
      "No freight records or credentials are attached. Please review fit and, if appropriate, confirm scope and an approved secure intake route."
    ].join("\n");

    const prepareEmailDraft = () => {
      const contactEmail = document.querySelector('meta[name="freight-contact-email"]')?.content.trim() || "";
      const sendLink = byId("sendAuditRequest");
      if (!contactEmail || !sendLink) {
        setError("The business inbox is temporarily unavailable. Please try again later.");
        return;
      }
      const reference = makeReference();
      preparedSummary = buildSummary(reference);
      const subject = encodeURIComponent("Free Recovery Audit Request — " + fieldValue("companyName") + " — " + reference);
      const body = encodeURIComponent(preparedSummary);
      sendLink.href = `mailto:${contactEmail}?subject=${subject}&body=${body}`;
      sendLink.removeAttribute("aria-disabled");
      auditForm.hidden = true;
      const ready = byId("auditReady");
      ready.hidden = false;
      ready.focus({ preventScroll: true });
      ready.scrollIntoView({ block: "center", behavior: "smooth" });
      track(EVENTS.auditFormCompleted, { completedSteps: 1, method: "email_draft" });
      track(EVENTS.auditRequestPrepared, { reference });
      // Keep the mail app handoff inside the visitor's click/submit gesture.
      // Mobile browsers may suppress deferred mailto navigation.
      window.location.href = sendLink.href;
    };

    fallbackLink?.addEventListener("click", (event) => {
      event.preventDefault();
      if (validate()) prepareEmailDraft();
    });

    auditForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (sending || !validate()) return;
      if (!serverReady) {
        prepareEmailDraft();
        return;
      }
      const turnstileToken = auditForm.querySelector('[name="cf-turnstile-response"]')?.value || "";
      if (!turnstileToken) {
        setError("Complete the security verification, or use the email option instead.");
        if (fallbackLink) fallbackLink.hidden = false;
        return;
      }
      pendingRequestKey ||= window.crypto?.randomUUID?.();
      if (!pendingRequestKey) {
        setError("Secure submission is unavailable on this device. Use the email option.");
        if (fallbackLink) fallbackLink.hidden = false;
        return;
      }
      const payload = {
        fullName: fieldValue("fullName"), workEmail: fieldValue("workEmail"),
        companyName: fieldValue("companyName"), annualSpend: fieldValue("annualSpend"),
        modes: valuesFor("modes"), monthlyShipments: fieldValue("monthlyShipments"),
        invoiceHistory: fieldValue("invoiceHistory"), suspectedIssues: fieldValue("suspectedIssues"),
        majorCarriers: fieldValue("majorCarriers"), records: valuesFor("records"),
        issueNotes: fieldValue("issueNotes"), campaign: nonEmptyCampaignContext,
        idempotencyKey: pendingRequestKey, turnstileToken
      };
      sending = true;
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Submitting securely…";
      }
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 12000);
      setError("");
      try {
        const response = await fetch("/api/inquiry", {
          method: "POST", cache: "no-store", credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload), signal: controller.signal
        });
        const result = await response.json();
        if (!response.ok || !result.received || !/^RA-[0-9]{8}-[A-F0-9]{8}$/.test(result.reference || "")) {
          throw new Error(result.error || "We could not confirm receipt.");
        }
        // This screen is shown ONLY after Cloudflare confirms durable D1 acceptance.
        auditForm.hidden = true;
        const ready = byId("auditReady");
        ready.querySelector(".eyebrow").textContent = "Request received";
        ready.querySelector("h3").textContent = "RETALLY has received your request.";
        ready.querySelector("p:not(.eyebrow)").textContent = "Reference " + result.reference +
          ". No freight files were submitted. We will review the business details you provided.";
        byId("sendAuditRequest").hidden = true;
        byId("copyAuditSummary").hidden = true;
        ready.hidden = false;
        ready.focus({ preventScroll: true });
        ready.scrollIntoView({ block: "center", behavior: "smooth" });
        track(EVENTS.auditFormCompleted, { completedSteps: 1, method: "durable_intake" });
      } catch (error) {
        setError((error.message || "Unable to confirm receipt.") +
          " Your form has not shown a confirmation. You can use the email method instead.");
        if (fallbackLink) fallbackLink.hidden = false;
        window.turnstile?.reset?.();
      } finally {
        window.clearTimeout(timeout);
        sending = false;
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = "Submit My Free Audit Request";
        }
      }
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


  // RETALLY's glossy launcher uses BubblaV's public widget.open() API.
  // Fail open to BubblaV's native launcher if the vendor API does not respond.
  const retallyChat = byId("retallyChatLauncher");
  if (retallyChat) {
    const body = document.body;
    let pendingOpenAt = 0;
    let openedThisAttempt = false;
    const fallbackToVendor = () => {
      pendingOpenAt = 0;
      body.classList.remove("retally-chat-open");
      body.classList.add("retally-chat-fallback");
      retallyChat.hidden = true;
    };
    const syncRetallyChat = () => {
      if (body.classList.contains("retally-chat-fallback")) return;
      const isOpen = window.BubblaV?.isOpen?.() === true;
      if (isOpen) {
        openedThisAttempt = true;
        pendingOpenAt = 0;
        body.classList.add("retally-chat-open");
        retallyChat.hidden = true;
        return;
      }
      if (pendingOpenAt && Date.now() - pendingOpenAt < 3200) return;
      if (pendingOpenAt && !openedThisAttempt) {
        fallbackToVendor();
        return;
      }
      pendingOpenAt = 0;
      body.classList.remove("retally-chat-open");
      retallyChat.hidden = false;
    };
    body.classList.add("retally-chat-enhanced");
    retallyChat.addEventListener("click", () => {
      const api = window.BubblaV;
      const frame = byId("bv-chat-frame");
      if (!frame || typeof api?.open !== "function") {
        fallbackToVendor();
        return;
      }
      pendingOpenAt = Date.now();
      openedThisAttempt = false;
      body.classList.add("retally-chat-open");
      retallyChat.hidden = true;
      try {
        api.open();
      } catch (_error) {
        fallbackToVendor();
      }
    });
    window.setInterval(syncRetallyChat, 500);
    syncRetallyChat();
  }

})();
