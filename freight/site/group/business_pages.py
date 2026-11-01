"""Shared editorial product pages; commercial facts stay in the public catalog."""
from html import escape
import re


# These photographs illustrate the subject of the work, never customer outcomes.
PRESENTATION = {
    "capturebrief": ("research", "Research notebooks and a laptop in a sunlit workspace", "decision rests on.", "A clearer picture of one pursuit.", ("Check the fit", "Place your order", "Review the evidence")),
    "permitplate": ("restaurant", "Illustrative New York corner restaurant with green window frames", "worth a closer look.", "Look past the filing.", ("Set your focus", "Review the research", "Put the brief to work")),
    "rehabsignal": ("research", "A quiet workspace for reviewing public-source research", "your next territory.", "Put territory context in focus.", ("Define a territory", "Agree the research scope", "Confirm availability")),
    "sheetharbor": ("tools", "Ceramics, a candle and measuring tools on an oak maker’s workbench", "what you make.", "Make the inputs visible.", ("Choose a workbook", "Review the preview", "Confirm release terms")),
    "app-factory": ("digital", "An illustrative workspace for practical digital tools", "a better home.", "Designed around everyday work.", ("Name the workflow", "Explore an edition", "Agree on production use")),
    "data-services": ("digital", "An illustrative workspace for public-data research and digital tools", "closer to the work.", "Connect the source to the task.", ("Choose the source", "Confirm access", "Validate the integration")),
    "scopesignal": ("tools", "Measuring tools and materials arranged on a workbench", "to its evidence.", "Follow the change.", ("Describe the problem", "Discuss the workflow", "Evaluate a future prototype")),
    "contractor-quote-recovery": ("tools", "A workbench with measuring tools and materials", "after the quote.", "Bring follow-up into focus.", ("Describe the gap", "Examine the current process", "Agree on a defined service")),
    "resonance": ("restaurant", "An illustrative neighborhood restaurant and shared cultural setting", "connection.", "Start with what people enjoy.", ("Choose cultural anchors", "Shape the session", "Review the ideas")),
    "market-surveillance": ("digital", "An illustrative digital research workspace", "easier to examine.", "Make historical context easier to inspect.", ("Frame the research question", "Confirm the sources", "Agree on evaluation")),
}


def render_business(b, photograph, link, mail):
    """Return a body fragment for one of the ten non-Recovery business pages."""
    photo, alt, emphasis, focus_heading, step_titles = PRESENTATION[b["slug"]]
    name = escape(b["name"])
    status = escape(b["status"])
    headline = b["headline"]
    if headline.endswith(emphasis):
        headline_html = escape(headline[:-len(emphasis)]) + "<em>" + escape(emphasis) + "</em>"
    else:
        headline_html = escape(headline)
    hero_photo = re.sub(r'\bsizes="[^"]*"', 'sizes="100vw"', photograph(photo, "", eager=True))
    contact = "/contact/?business=" + b["slug"]
    target = b.get("href", contact)
    price = (f'<p class="group-price"><strong>{escape(b["price"])}</strong><span>{escape(b["unit"])}</span></p>'
             if "price" in b else '<p class="offer-stage-note">Start with the right fit.</p>')
    offer_points = "".join(f'<li>{escape(title)}</li>' for title, _ in b["features"])
    sample = ""
    if b["slug"] in {"capturebrief", "permitplate"}:
        label, href = b["links"][0]
        sample = '<div class="offer-sample"><span>See the work before you decide</span>' + link(label + " ↗", href, "group-text-link sample-link") + '</div>'
    action_note = ("Continue to the product site for its full scope and next step."
                   if "href" in b else "Tell RETALLY what you need using the shared enquiry form.")
    if "purchase_note" in b:
        legal_links = " · ".join(link(label, href) for label, href in b["purchase_links"])
        action_note = "Secure checkout opens on Stripe. " + escape(b["purchase_note"]) + "<br>By purchasing, you agree to the published terms. " + legal_links
    features = "".join(
        f'<article class="premium-feature"><span class="feature-index" aria-hidden="true">0{i}</span><h3>{escape(title)}</h3><p>{escape(detail)}</p></article>'
        for i, (title, detail) in enumerate(b["features"], 1))
    steps = "".join(
        f'<li><span class="step-number" aria-hidden="true">0{i}</span><div><h3>{escape(title)}</h3><p>{escape(detail)}</p></div></li>'
        for i, (title, detail) in enumerate(zip(step_titles, b["steps"]), 1))
    resources = "".join(link(label + " ↗", href, "business-resource-link") for label, href in b["links"])
    if not resources:
        resources = link("Ask about " + b["name"] + " ↗", contact, "business-resource-link")
    resource_heading = "Explore the details." if b["links"] else "Talk through the fit."
    audience = b["audience"][0].lower() + b["audience"][1:]
    return f'''<section class="premium-business-hero">
<div class="business-hero-media" aria-hidden="true">{hero_photo}</div>
<div class="group-wrap"><nav class="group-breadcrumb" aria-label="Breadcrumb"><a href="/">RETALLY Group</a><span aria-hidden="true">/</span><span>{name}</span></nav>
<div class="business-hero-grid"><div class="business-hero-copy"><p class="group-kicker">{escape(b['division'])} / {name}</p><h1>{headline_html}</h1><p class="group-lead">{escape(b['summary'])}</p><div class="business-audience"><span>BUILT AROUND YOUR WORK</span><p>For {escape(audience)}.</p></div><a class="business-hero-explore" href="#focus">Explore the focus <span aria-hidden="true">↓</span></a></div>
<aside class="business-offer" aria-labelledby="business-offer-title"><div class="offer-content"><span class="group-status">{status}</span><h2 id="business-offer-title">{name}</h2>{price}<p class="offer-focus-label">Areas of focus</p><ul class="offer-points">{offer_points}</ul>{link(b['cta'] + ' ↗', target, 'group-button')}{sample}<p class="group-small offer-action-note">{action_note}</p></div></aside></div></div></section>
<nav class="business-section-nav" aria-label="On this page"><div class="group-wrap"><a href="#focus">What it covers <span aria-hidden="true">↘</span></a><a href="#next-steps">How to begin <span aria-hidden="true">↘</span></a><a href="#scope">Scope &amp; resources <span aria-hidden="true">↘</span></a></div></nav>
<section class="group-section group-wrap premium-business-focus" id="focus"><div class="business-section-heading"><div><p class="group-kicker">THE FOCUS</p><h2>{escape(focus_heading)}</h2></div><p>{escape(b['detail'])}</p></div><div class="group-features premium-features">{features}</div></section>
<section class="business-process-section" id="next-steps"><div class="group-wrap business-process-grid"><div class="business-process-intro"><p class="group-kicker">YOUR NEXT STEP</p><h2>A clear way<br><em>to begin.</em></h2><p class="process-stage">Current stage: <strong>{status}</strong></p><figure class="business-context-photo">{photograph(photo, alt)}<figcaption>Illustrative setting for the work.</figcaption></figure></div><ol class="group-steps premium-steps">{steps}</ol></div></section>
<section class="group-section group-wrap premium-business-scope" id="scope"><div class="business-scope-copy"><p class="group-kicker">SCOPE &amp; AVAILABILITY</p><h2>Clarity comes first.</h2><p class="group-boundary">{escape(b['boundary'])}</p><p class="business-scope-question">Questions about {name}? {link('Contact RETALLY', contact)}. A brief, non-sensitive description of what you need is enough to begin.</p></div><aside class="business-resource-panel" aria-labelledby="business-resource-title"><p class="group-kicker">KEEP EXPLORING</p><h3 id="business-resource-title">{resource_heading}</h3><div class="group-resource-links">{resources}</div>{link('Explore all RETALLY businesses →', '/#businesses', 'business-directory-link')}</aside></section>'''

