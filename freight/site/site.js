"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const contact = document.querySelector('meta[name="freight-contact-email"]').content;
  const message = byId("formMessage");
  let subject = "Freight invoice review — fit discussion";
  let draft = "";

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

  byId("prepareDraft").addEventListener("click", () => {
    for (const field of document.querySelectorAll("#inquiryFields input, #inquiryFields textarea")) {
      if (!field.reportValidity()) return;
    }
    subject = `Freight invoice review — ${byId("company").value.trim()}`;
    draft = [
      "I would like to discuss fit for a freight invoice review.",
      "",
      `Name: ${byId("name").value.trim()}`,
      `Company: ${byId("company").value.trim()}`,
      `Work email: ${byId("email").value.trim()}`,
      `Carrier invoices per month: ${byId("volume").value}`,
      `Freight mix and review goal: ${byId("notes").value.trim()}`,
      "",
      "Please confirm scope, fees, and a suitable data-handling route before any freight documents are shared."
    ].join("\n");
    byId("draftText").value = draft;
    byId("draftPanel").hidden = false;
    if (contact) {
      byId("emailDraft").href = `mailto:${contact}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(draft)}`;
      byId("emailDraft").hidden = false;
      byId("deliveryNote").textContent = `Send the draft to ${contact} using your email app. Do not attach documents. This page cannot confirm delivery.`;
    }
    message.textContent = "Draft ready. Nothing has been sent. Review it, then copy, download, or open it in your email app.";
    byId("draftText").focus();
  });

  byId("copyDraft").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(draft);
      message.textContent = "Draft copied. Nothing has been sent.";
    } catch (_) {
      byId("draftText").focus();
      byId("draftText").select();
      message.textContent = "The draft is selected. Use your device’s Copy command. Nothing has been sent.";
    }
  });

  byId("downloadDraft").addEventListener("click", () => {
    const blob = new Blob([`Subject: ${subject}\n\n${draft}\n`], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "freight-inquiry-draft.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    message.textContent = "Text download ready. Nothing has been sent.";
  });

  byId("emailDraft").addEventListener("click", () => {
    message.textContent = "Email draft opened. Review and send it yourself; this page cannot confirm delivery.";
  });
})();
