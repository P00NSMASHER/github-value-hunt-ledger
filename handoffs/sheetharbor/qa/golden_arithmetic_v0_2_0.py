#!/usr/bin/env python3
"""SheetHarbor v0.2.0-alpha golden arithmetic regression gate.

Dependency-free by design: uses only the Python standard library so it can run
in a future private product repository/CI job without Excel-specific packages.

The gate verifies:
1. each canonical XLSX artifact has the frozen SHA-256 from the release handoff;
2. cached values in key decision-output cells match an independent Python
   implementation of the workbook arithmetic for the frozen golden scenario.

This is an arithmetic regression gate. It is NOT a substitute for Microsoft
Excel or Google Sheets round-trip/recalculation compatibility testing.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import posixpath
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, Mapping

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_DOC_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_DOC_NS}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        raw = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(raw)
    out: list[str] = []
    for si in root.findall(f"{{{MAIN_NS}}}si"):
        out.append("".join(t.text or "" for t in si.iter(f"{{{MAIN_NS}}}t")))
    return out


def _sheet_xml_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
    rid = None
    for sheet in wb_root.findall("m:sheets/m:sheet", NS):
        if sheet.attrib.get("name") == sheet_name:
            rid = sheet.attrib.get(f"{{{REL_DOC_NS}}}id")
            break
    if rid is None:
        raise KeyError(f"sheet not found: {sheet_name!r}")

    rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    target = None
    for rel in rel_root.findall(f"{{{REL_PKG_NS}}}Relationship"):
        if rel.attrib.get("Id") == rid:
            target = rel.attrib.get("Target")
            break
    if not target:
        raise KeyError(f"worksheet relationship not found for {sheet_name!r}")

    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join("xl", target))


def read_cached_cells(path: Path, sheet_name: str, addresses: Iterable[str]) -> Dict[str, object]:
    wanted = set(addresses)
    found: Dict[str, object] = {}
    with zipfile.ZipFile(path) as zf:
        shared = _shared_strings(zf)
        sheet_path = _sheet_xml_path(zf, sheet_name)
        root = ET.fromstring(zf.read(sheet_path))
        for cell in root.iter(f"{{{MAIN_NS}}}c"):
            addr = cell.attrib.get("r")
            if addr not in wanted:
                continue
            typ = cell.attrib.get("t")
            if typ == "inlineStr":
                is_el = cell.find(f"{{{MAIN_NS}}}is")
                value = "" if is_el is None else "".join(
                    t.text or "" for t in is_el.iter(f"{{{MAIN_NS}}}t")
                )
            else:
                v = cell.find(f"{{{MAIN_NS}}}v")
                raw = None if v is None else v.text
                if raw is None:
                    value = None
                elif typ == "s":
                    value = shared[int(raw)]
                elif typ in {"str", "e"}:
                    value = raw
                elif typ == "b":
                    value = raw == "1"
                else:
                    number = float(raw)
                    value = int(number) if number.is_integer() else number
            found[addr] = value
    missing = wanted - found.keys()
    if missing:
        raise KeyError(f"missing cached cell(s) in {path.name} / {sheet_name}: {sorted(missing)}")
    return found


def candle_golden() -> Mapping[str, float]:
    q, batch_units, fill_g, load = 48, 24, 200.0, 0.08
    wax_per_kg, fragrance_per_kg = 5.5, 28.0
    vessel, wick, label, packaging, other_unit = 1.6, 0.12, 0.18, 0.75, 0.15
    labor_rate, labor_min_batch, overhead_batch = 25.0, 35.0, 4.0
    spoilage, retail_fee, retail_fixed, target_margin = 0.03, 0.065, 0.2, 0.45
    wholesale_fee, discount = 0.0, 0.50
    avg_retail_order, wholesale_fixed, avg_wholesale_order = 1.0, 0.0, 24.0

    planned = math.ceil(q * (1 + spoilage))
    batches = math.ceil(planned / batch_units)
    wax_g = fill_g / (1 + load)
    fragrance_g = fill_g - wax_g
    total = (
        planned * wax_g / 1000 * wax_per_kg
        + planned * fragrance_g / 1000 * fragrance_per_kg
        + planned * vessel
        + planned * wick
        + planned * label
        + q * packaging
        + planned * other_unit
        + batches * labor_min_batch / 60 * labor_rate
        + batches * overhead_batch
    )
    unit = total / q
    target = (unit + retail_fixed / avg_retail_order) / (1 - retail_fee - target_margin)
    retail_profit = target - unit - target * retail_fee - retail_fixed / avg_retail_order
    discounted_wholesale = target * (1 - discount)
    wholesale_margin = (
        discounted_wholesale
        - unit
        - discounted_wholesale * wholesale_fee
        - wholesale_fixed / avg_wholesale_order
    ) / discounted_wholesale
    return {
        "B16": planned,
        "B32": total,
        "B33": unit,
        "B35": target,
        "B37": retail_profit / target,
        "B40": wholesale_margin,
    }


def fdm_golden() -> Mapping[str, float]:
    q, grams_per_unit, units_per_plate, hours_per_plate = 10, 85.0, 2.0, 6.0
    setup_min, post_min_per_unit = 10.0, 6.0
    labor_rate, electricity_rate = 25.0, 0.16
    printer_cost, useful_hours, maintenance = 599.0, 5000.0, 0.20
    fail_rate, material_per_kg, watts = 0.08, 22.0, 120.0
    packaging, other_per_unit = 0.60, 0.25
    fee_rate, fixed_fee, target_margin = 0.065, 0.20, 0.40

    plates = math.ceil(q / units_per_plate)
    failure_multiplier = 1 / (1 - fail_rate)
    machine_hours = plates * hours_per_plate * failure_multiplier
    expected_grams = grams_per_unit * q * failure_multiplier
    total = (
        expected_grams / 1000 * material_per_kg
        + machine_hours * watts / 1000 * electricity_rate
        + machine_hours * (printer_cost / useful_hours + maintenance)
        + (setup_min + post_min_per_unit * q) / 60 * labor_rate
        + q * packaging
        + q * other_per_unit
    )
    quote = (total + fixed_fee) / (1 - fee_rate - target_margin)
    profit = quote - total - fixed_fee - quote * fee_rate
    labor_hours = (setup_min + post_min_per_unit * q) / 60
    return {
        "B19": plates,
        "B30": total,
        "B32": quote,
        "B33": quote / q,
        "B35": profit / quote,
        "B37": profit / labor_hours,
    }


def embroidery_golden() -> Mapping[str, float]:
    q, stitches, colors, blank_cost = 24, 12000.0, 4, 8.5
    digitizing, other_item = 15.0, 0.25
    labor_rate, machine_rate = 25.0, 8.0
    speed, efficiency = 750.0, 0.75
    thread_per_1000, stabilizer, needle, packaging = 0.14, 0.20, 0.06, 0.40
    overhead_rate, spoilage = 0.10, 0.03
    fee_rate, fixed_fee, target_margin = 0.035, 0.30, 0.45
    setup_min, handling_min, trim_min, color_change_min = 10.0, 1.5, 1.0, 2.0

    planned = math.ceil(q * (1 + spoilage))
    machine_min = planned * stitches / (speed * efficiency)
    labor_min = setup_min + planned * (handling_min + trim_min) + max(0, colors - 1) * color_change_min
    direct = (
        planned * blank_cost
        + planned * stitches / 1000 * thread_per_1000
        + planned * stabilizer
        + planned * needle
        + q * packaging
        + planned * other_item
        + digitizing
        + machine_min / 60 * machine_rate
        + labor_min / 60 * labor_rate
    )
    cost = direct * (1 + overhead_rate)
    quote = (cost + fixed_fee) / (1 - fee_rate - target_margin)
    profit = quote - cost - fixed_fee - quote * fee_rate
    return {
        "B17": planned,
        "B32": cost,
        "B34": quote,
        "B35": quote / q,
        "B37": profit / quote,
        "B38": profit / (labor_min / 60),
    }


def screen_golden() -> Mapping[str, float]:
    q, garment_cost = 48, 3.25
    front_colors, back_colors, setup_per_screen = 2, 1, 18.0
    ink_per_oz, ink_oz_per_print_color = 1.20, 0.018
    spoilage, order_setup_hours, production_rate = 0.04, 0.75, 72.0
    labor_rate, order_overhead, packaging = 24.0, 15.0, 0.20
    target_margin, fee_rate, fixed_fee = 0.35, 0.08, 0.30

    colors = front_colors + back_colors
    production_units = math.ceil(q / (1 - spoilage))
    screens = colors
    labor_hours = order_setup_hours + production_units / production_rate
    total = (
        screens * setup_per_screen
        + production_units * garment_cost
        + production_units * colors * ink_oz_per_print_color * ink_per_oz
        + labor_hours * labor_rate
        + q * packaging
        + order_overhead
    )
    quote = (total + fixed_fee) / (1 - target_margin - fee_rate)
    profit = quote * (1 - fee_rate) - fixed_fee - total
    return {
        "G6": production_units,
        "G14": total,
        "G15": quote,
        "G16": quote / q,
        "G17": profit,
        "G18": profit / quote,
    }


PRODUCTS = {
    "SH-CANDLE": {
        "filename": "SheetHarbor_Candle_Economics_v0.2.0-alpha.xlsx",
        "sha256": "b289019dbf6c129d640a7b431ab52f3431f9f6d5bf0ead387b309341005631ba",
        "sheet": "Candle Calculator",
        "golden": candle_golden,
    },
    "SH-FDM": {
        "filename": "SheetHarbor_FDM_3D_Printing_Economics_v0.2.0-alpha.xlsx",
        "sha256": "94d69ceecf4f894ddacc8ae36f882dde25a918072aa7b802f2b9039a4631a94c",
        "sheet": "Job Calculator",
        "golden": fdm_golden,
    },
    "SH-EMB": {
        "filename": "SheetHarbor_Embroidery_Economics_v0.2.0-alpha.xlsx",
        "sha256": "384108221ab99173f91c54d7b5cacbf1c24212b76ea07d05cd56c168fe37bc8d",
        "sheet": "Job Calculator",
        "golden": embroidery_golden,
    },
    "SH-SCREEN": {
        "filename": "SheetHarbor_Screen_Printing_Economics_v0.2.0-alpha.xlsx",
        "sha256": "702b5fd6fdcdc69638d570699b323c021b18d3540241d63a24a2828169241b84",
        "sheet": "Worked Example",
        "golden": screen_golden,
    },
}


def close_enough(actual: object, expected: float) -> bool:
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    return math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-10)


def run(artifact_dir: Path) -> int:
    failures = 0
    print("SheetHarbor v0.2.0-alpha golden arithmetic gate")
    print(f"Artifact directory: {artifact_dir}")
    print()

    for product_id, spec in PRODUCTS.items():
        path = artifact_dir / spec["filename"]
        expected = spec["golden"]()
        product_failures: list[str] = []
        if not path.exists():
            product_failures.append(f"missing artifact: {path.name}")
        else:
            actual_hash = sha256_file(path)
            if actual_hash != spec["sha256"]:
                product_failures.append(
                    f"SHA-256 mismatch: expected {spec['sha256']}, got {actual_hash}"
                )
            try:
                actual_cells = read_cached_cells(path, spec["sheet"], expected.keys())
                for addr, exp in expected.items():
                    act = actual_cells[addr]
                    if not close_enough(act, exp):
                        product_failures.append(
                            f"{spec['sheet']}!{addr}: expected {exp!r}, got {act!r}"
                        )
            except Exception as exc:
                product_failures.append(f"workbook read failure: {exc}")

        if product_failures:
            failures += len(product_failures)
            print(f"FAIL {product_id} — {path.name}")
            for item in product_failures:
                print(f"  - {item}")
        else:
            print(f"PASS {product_id} — {path.name} — hash + {len(expected)} arithmetic checks")

    print()
    if failures:
        print(f"GATE: FAIL ({failures} failure(s))")
        return 1
    print("GATE: PASS (4/4 products; exact hashes; 24 independent arithmetic checks)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "artifact_dir",
        nargs="?",
        default=".",
        help="directory containing the four canonical v0.2.0-alpha XLSX artifacts",
    )
    args = parser.parse_args()
    return run(Path(args.artifact_dir))


if __name__ == "__main__":
    sys.exit(main())
