from freight.contracts import PopulationRow, freeze_population
from freight.finding_factory import FIXED, ChargeRule, InvoiceCharge, derive_batch
from freight.review_queue import (
    REVIEW_EVIDENCE, REVIEW_MONEY, VALIDATED_MONEY, build_review_queue,
)


def population():
    return freeze_population(
        "b", "u", "four rows",
        [
            PopulationRow(f"i{n}", f"s{n}", "c", "k", "USD", f"src-{n}")
            for n in range(1, 5)
        ],
    )


def charge(n, code, billed):
    return InvoiceCharge(
        "b", "u", f"i{n}", f"s{n}", "c", "k", "USD",
        f"ch-{n}", code, "2026-09-10", 1, billed, f"line-{n}",
    )


def rule(code, fixed, verified=True):
    return ChargeRule(
        "b", "u", "c", "k", "USD", "doc", code, FIXED,
        "2026-09-01", "2026-09-30", "authority-" + code,
        verified, fixed, None,
    )


def batch():
    return derive_batch(
        population(),
        [
            charge(1, "A", 11000),  # validated +1000
            charge(2, "B", 15000),  # review +5000 (unverified)
            charge(3, "C", 20000),  # review, missing rule / unknown expected
            charge(4, "D", 9000),   # clear
        ],
        [
            rule("A", 10000, True),
            rule("B", 10000, False),
            rule("D", 10000, True),
        ],
    )


def test_queue_orders_supported_money_then_review_money_then_evidence_gap():
    q = build_review_queue(batch())
    assert [item.charge_id for item in q.items] == ["ch-1", "ch-2", "ch-3"]
    assert [item.priority_class for item in q.items] == [
        VALIDATED_MONEY, REVIEW_MONEY, REVIEW_EVIDENCE,
    ]
    assert all(item.queue_position == i for i, item in enumerate(q.items, 1))
    assert all(len(item.item_hash) == 64 for item in q.items)


def test_clear_items_are_not_sent_to_human_review_queue():
    q = build_review_queue(batch())
    assert "ch-4" not in {item.charge_id for item in q.items}


def test_queue_is_deterministic_and_bound_to_factory():
    a = build_review_queue(batch())
    b = build_review_queue(batch())
    assert a == b
    assert a.factory_hash == batch().factory_hash
    assert len(a.queue_hash) == 64


def test_same_priority_orders_larger_variance_first():
    b = derive_batch(
        freeze_population(
            "b", "u", "two",
            [
                PopulationRow("i1", "s1", "c", "k", "USD", "s1"),
                PopulationRow("i2", "s2", "c", "k", "USD", "s2"),
            ],
        ),
        [charge(1, "A", 12000), charge(2, "B", 15000)],
        [rule("A", 10000), rule("B", 10000)],
    )
    q = build_review_queue(b)
    assert [item.charge_id for item in q.items] == ["ch-2", "ch-1"]
