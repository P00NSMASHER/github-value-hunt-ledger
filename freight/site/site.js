"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const contact = document.querySelector('meta[name="freight-contact-email"]').content;
  const message = byId("formMessage");
  let subject = "Freight invoice review — fit discussion";
  let draft = "";

  byId("prepareDraft").addEventListener("click", () => {
    for (const field of document.querySelectorAll("#inquiryFields input, #inquiryFields textarea")) {
      if (!field.reportValidity()) return;
    }
    subject = `Freight invoice review — ${byId("company").value.trim()}`;
    draft = [
      "I would like to discuss fit and readiness for a freight invoice review.",
      "",
      `Name: ${byId("name").value.trim()}`,
      `Company: ${byId("company").value.trim()}`,
      `Work email: ${byId("email").value.trim()}`,
      `Carrier invoices per month: ${byId("volume").value}`,
      `Freight mix and review goal: ${byId("notes").value.trim()}`,
      "",
      "Please confirm the proposed scope, fees, and suitable data-handling arrangements before any freight documents are shared."
    ].join("\n");
    byId("draftText").value = draft;
    byId("draftPanel").hidden = false;
    if (contact) {
      byId("emailDraft").href = `mailto:${contact}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(draft)}`;
      byId("emailDraft").hidden = false;
      byId("deliveryNote").textContent = `Send the draft to ${contact} using your email application. No documents in the initial inquiry. This page cannot confirm delivery.`;
    }
    message.textContent = "Draft prepared. Nothing has been sent. Review the text, then copy, download, or open an email draft if available.";
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
    message.textContent = "Text download prepared. Nothing has been sent.";
  });

  byId("emailDraft").addEventListener("click", () => {
    message.textContent = "Email draft requested in your email application. Review it and send it yourself. This page cannot confirm sending or delivery.";
  });
})();
