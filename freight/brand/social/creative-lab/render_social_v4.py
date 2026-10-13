#!/usr/bin/env python3
"""RETALLY v4: phone-first visual revisions for the six approved-source draft concepts.

An additive local design experiment on v3. Never edits v3, Metricool, a live
website, social accounts, or approved logos. Preserves all human review holds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import render_social as engine
import render_social_v3 as v3

# Three full-width rows replace a dense 3-column form. At 390px phone width,
# primary headings exceed 14px and row values exceed 10px in the actual crop.
# Exact backgrounds, brand master, source rights holds and illustrations remain.
CSS_V4 = r"""
.v4 .hero-title{font-size:90px!important;line-height:1.035!important;letter-spacing:-3.7px!important;
                margin:23px 0 18px!important}
.v4 .hero-body{top:220px!important}
.v4 .hero-sub{font-size:31px!important;line-height:1.25!important}
.v4 .upper-pill{margin-top:18px!important;font-size:18px!important}
.v4 .section-top{top:42px!important}
.v4 .section-title{font-size:37px!important;line-height:1.1!important}
.v4 .sample{font-size:23px!important;line-height:1.35!important;letter-spacing:0!important}
.v4 .divider{top:169px!important}
.v4 .documents{top:203px!important;left:70px!important;width:940px!important;height:310px!important;
               display:grid!important;grid-template-columns:minmax(0,1fr)!important;
               grid-template-rows:repeat(3,92px)!important;gap:16px!important;counter-reset:step}
.v4 .document,.v4 .document.focus{position:relative;display:grid!important;
               grid-template-columns:minmax(0,1fr) 264px!important;
               gap:20px!important;align-items:center!important;
               margin:0!important;padding:14px 25px 14px 82px!important;
               height:92px!important;min-height:92px!important;
               border-radius:20px!important;transform:none!important;
               box-shadow:inset 0 2px 0 rgba(255,255,255,.87),0 5px 0 rgba(85,131,103,.14),
               0 12px 20px rgba(7,55,40,.13)!important;counter-increment:step}
.v4 .document.focus{border-width:3px!important;border-color:#18a978!important}
.v4 .document:before{display:none!important}
.v4 .document:after{content:counter(step,decimal-leading-zero);position:absolute;left:27px;top:50%;
                    transform:translateY(-50%);font-size:30px;letter-spacing:-.6px;
                    font-weight:900;color:#0b8b61;opacity:.88}
.v4 .document .doc-top,.v4 .document .doc-label,.v4 .document .doc-rule,.v4 .document .doc-status{
                display:none!important}
.v4 .document .doc-type{font-size:42px!important;line-height:1.04!important;letter-spacing:-1.0px!important;
                       margin:0!important;padding:0!important;color:#12352e;white-space:nowrap}
.v4 .document .doc-value{font-size:29px!important;line-height:1.12!important;
                        padding:13px 12px!important;border-radius:13px!important;
                        white-space:nowrap!important;text-align:center!important;
                        overflow:visible!important;margin:0!important}
.v4 .document.focus .doc-value{background:#e9fff2;border-color:#9bd6b4}
.v4.detention .document .doc-type{font-size:53px!important;letter-spacing:-1px!important}
.v4 .keypoint{top:528px!important;padding-top:17px!important}
.v4 .keypoint strong{font-size:24px!important;line-height:1.13!important}
.v4 .keypoint em{font-size:20px!important}
.v4 .footer-note{font-size:21px!important;letter-spacing:0!important}
.v4 .eyebrow{font-size:20px!important}
/* Color treatment remains topic-specific. Avoid any invented carrier identity. */
.v4.fuel .document.focus .doc-value{background:#f4fffa}
.v4.security .document:nth-child(3) .doc-type{color:#92503a}
.v4.settlement .document:nth-child(3) .doc-type{color:#795b2d}
"""

CURRENT_TEMPLATE = v3.template_html
CURRENT_QA = engine._dom_qa


def template_html(logo: str, photo: str, concept: str, preview: bool = False) -> str:
    page = CURRENT_TEMPLATE(logo, photo, concept, preview)
    key = '<main class="artboard v3 '
    if page.count(key) != 1 or page.count("</style>") != 1:
        raise ValueError("Unexpected editorial template structure")
    return page.replace(key, '<main class="artboard v3 v4 ', 1).replace(
        "</style>", "\n" + CSS_V4 + "\n</style>", 1)


def _dom_qa(page) -> dict:
    result = CURRENT_QA(page)
    stats = page.evaluate("""() => {
      const get = selector => [...document.querySelectorAll(selector)];
      const primary=get('.document .doc-type'), secondary=get('.document .doc-value');
      const num = node => parseFloat(getComputedStyle(node).fontSize);
      const rect = node => node.getBoundingClientRect();
      const cards=get('.documents .document');
      const cardX=cards.map(node=>rect(node).left);
      const sortedRows=cards.every((node,i) => !i || rect(node).top>rect(cards[i-1]).bottom);
      const allVisible=primary.concat(secondary).every(node=>{
        const style=getComputedStyle(node),r=rect(node);
        return style.display!=='none' && style.visibility!=='hidden'
          && r.width>5 && r.height>5
          && node.scrollWidth<=node.clientWidth+2
          && node.scrollHeight<=node.clientHeight+2;
      });
      const disclaimer=get('.sample')[0];
      const title=get('.hero-title')[0];
      const valueSizes=secondary.map(num), titleSizes=primary.map(num);
      return {columns: cards.length, stacked:sortedRows, all_card_text_visible:allVisible,
        card_title_sizes_px:titleSizes, card_value_sizes_px:valueSizes,
        card_titles_unique:(new Set(primary.map(n=>n.textContent))).size===primary.length,
        disclaimer_px:num(disclaimer), disclaimer_visible:rect(disclaimer).width>100,
        headline_px:num(title), headline_not_clipped:title.scrollWidth<=title.clientWidth+3,
        card_row_lefts_px:cardX};
    }""")
    failure=[]
    if stats["columns"] != 3 or not stats["stacked"]:
        failure.append("v4:expected-three-stacked-cards")
    if not stats["all_card_text_visible"] or not stats["card_titles_unique"]:
        failure.append("v4:card-text-clipped-or-repeated")
    if min(stats["card_title_sizes_px"],default=0) < 40:
        failure.append("v4:card-heading-below-phone-legibility-minimum")
    if min(stats["card_value_sizes_px"],default=0) < 28:
        failure.append("v4:card-action-below-phone-legibility-minimum")
    if not stats["headline_not_clipped"] or stats["headline_px"] < 85:
        failure.append("v4:hero-headline-clipped")
    if stats["disclaimer_px"] < 22 or not stats["disclaimer_visible"]:
        failure.append("v4:illustrative-disclaimer-too-small")
    result["v4_phone_readability"] = stats
    result["escaped_elements"].extend(failure)
    return result


def render(output: Path, mode: str, logo: Path, photo: Path,
           *, concept: str = "all", executable: str | None = None) -> dict:
    old_template = v3.template_html
    old_qa = engine._dom_qa
    try:
        v3.template_html = template_html
        engine._dom_qa = _dom_qa
        manifest = v3.render(output,mode,logo,photo,concept=concept,
                             executable=executable)
    finally:
        v3.template_html=old_template
        engine._dom_qa=old_qa
    manifest["creative_series"] = "RETALLY Field Notes v4, phone-first stacked evidence, review only"
    manifest["mobile_type_legibility_gate"] = True
    manifest["three_visible_full_width_cards"] = True
    manifest["existing_published_and_scheduled_posts_untouched"] = True
    for item in manifest["content_proposals"]:
        item["approved_for_publication"] = False
    Path(output,"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("preview","production"),default="production")
    parser.add_argument("--concept",choices=(*v3.CONCEPTS,"all"),default="all")
    parser.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[4])
    parser.add_argument("--photo",type=Path)
    parser.add_argument("--logo",type=Path)
    parser.add_argument("--chromium",type=str)
    parser.add_argument("--output-dir",type=Path,default=Path("/tmp/retally-v4-review"))
    a=parser.parse_args()
    if a.mode=="production" and (a.photo or a.logo):
        parser.error("Production source override forbidden")
    if a.mode=="preview" and not a.photo:
        parser.error("Preview requires sample photo")
    wordmark=a.logo or a.repo_root/v3.base.CANONICAL_WORDMARK
    photo=a.photo or a.repo_root/v3.base.CANONICAL_PHOTOS["rate_versions"]
    print(json.dumps(render(a.output_dir,a.mode,wordmark,photo,concept=a.concept,
                            executable=a.chromium),indent=2))


if __name__=="__main__":
    main()
