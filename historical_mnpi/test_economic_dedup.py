import unittest

from historical_mnpi.economic_dedup import (
    DedupMatchState,
    EconomicTransactionSignature,
    build_economic_signature,
    compare_economic_signatures,
)
from historical_mnpi.review_queue import (
    ReviewDecision,
    decide_review_item,
)
from historical_mnpi.test_review_queue import all_checks, clean_item
from historical_mnpi.transaction_model import (
    InstrumentType,
    TimePrecision,
    TradeSide,
)


def sig(
    row,
    *,
    trader="trader-entity:one",
    issuer="issuer-entity:one",
    event="event:one",
    instrument=InstrumentType.STOCK,
    side=TradeSide.BUY,
    timestamp="2015-08-10T14:31:22-04:00",
    trade_date=None,
    range_start=None,
    range_end=None,
    currency="USD",
    quantity="2500",
    price="30.375",
    strike=None,
    expiry=None,
):
    precision = (
        TimePrecision.EXACT_TIMESTAMP
        if timestamp is not None
        else TimePrecision.DATE_ONLY
        if trade_date is not None
        else TimePrecision.DATE_RANGE
    )
    return EconomicTransactionSignature(
        normalized_row_hash=(f"{row:064x}")[-64:],
        review_item_hash=(f"{row + 1000:064x}")[-64:],
        trader_entity_id=trader,
        issuer_entity_id=issuer,
        event_id=event,
        instrument_type=instrument,
        side=side,
        time_precision=precision,
        trade_timestamp=timestamp,
        trade_date=trade_date,
        trade_date_range_start=range_start,
        trade_date_range_end=range_end,
        currency=currency,
        quantity=quantity,
        execution_price=price,
        option_strike=strike,
        option_expiry=expiry,
    )


class EconomicDedupTests(unittest.TestCase):
    def test_approved_review_builds_source_independent_signature(self):
        (
            sources,
            manifest,
            cases,
            _events,
            _case,
            _event,
            _record,
            _candidate,
            _refs,
            entities,
            crosswalks,
            source_conflicts,
            item,
        ) = clean_item()
        decision = decide_review_item(
            item,
            decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
            checks=all_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T14:00:00Z",
            rationale="Approved for dedup test.",
            cases=cases,
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=source_conflicts,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        signature = build_economic_signature(item, decision)
        self.assertEqual(
            signature.trader_entity_id,
            item.durable_identity.trader_entity_id,
        )
        self.assertEqual(
            signature.issuer_entity_id,
            item.durable_identity.issuer_entity_id,
        )
        self.assertEqual(signature.event_id, item.event_id)
        self.assertEqual(len(signature.economic_key_hash), 64)
        self.assertEqual(len(signature.proof_hash), 64)

    def test_nonapproved_decision_cannot_create_signature(self):
        *_, item = clean_item()
        decision = decide_review_item(
            item,
            decision=ReviewDecision.REJECTED,
            checks=all_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T14:00:00Z",
            rationale="Rejected.",
        )
        with self.assertRaisesRegex(ValueError, "approved historical row"):
            build_economic_signature(item, decision)

    def test_exact_match_accepts_equivalent_timezone_offsets(self):
        left = sig(1, timestamp="2015-08-10T14:31:22-04:00")
        right = sig(2, timestamp="2015-08-10T18:31:22Z")
        result = compare_economic_signatures(left, right)
        self.assertEqual(result.state, DedupMatchState.EXACT_MATCH)
        self.assertIn("trade_time", result.agreeing_fields)

    def test_decimal_representation_does_not_create_false_difference(self):
        left = sig(1, quantity="2500.0", price="30.3750")
        right = sig(2, quantity="2500", price="30.375")
        self.assertEqual(left.economic_key_hash, right.economic_key_hash)
        self.assertEqual(
            compare_economic_signatures(left, right).state,
            DedupMatchState.EXACT_MATCH,
        )

    def test_source_row_hashes_do_not_affect_economic_key(self):
        left = sig(1)
        right = sig(999)
        self.assertNotEqual(left.proof_hash, right.proof_hash)
        self.assertEqual(left.economic_key_hash, right.economic_key_hash)

    def test_date_only_agreement_is_possible_not_exact(self):
        left = sig(
            1,
            timestamp=None,
            trade_date="2015-08-10",
        )
        right = sig(
            2,
            timestamp=None,
            trade_date="2015-08-10",
        )
        result = compare_economic_signatures(left, right)
        self.assertEqual(result.state, DedupMatchState.POSSIBLE_MATCH)
        self.assertIn("TRADE_TIME_NOT_EXACT", result.reasons)

    def test_exact_timestamp_inside_date_only_is_possible(self):
        left = sig(1, timestamp="2015-08-10T14:31:22-04:00")
        right = sig(
            2,
            timestamp=None,
            trade_date="2015-08-10",
        )
        self.assertEqual(
            compare_economic_signatures(left, right).state,
            DedupMatchState.POSSIBLE_MATCH,
        )

    def test_overlapping_date_ranges_are_possible(self):
        left = sig(
            1,
            timestamp=None,
            range_start="2015-08-01",
            range_end="2015-08-10",
        )
        right = sig(
            2,
            timestamp=None,
            range_start="2015-08-08",
            range_end="2015-08-12",
        )
        self.assertEqual(
            compare_economic_signatures(left, right).state,
            DedupMatchState.POSSIBLE_MATCH,
        )

    def test_disjoint_time_is_distinct(self):
        left = sig(1, timestamp="2015-08-10T14:31:22-04:00")
        right = sig(2, timestamp="2015-08-10T14:32:22-04:00")
        result = compare_economic_signatures(left, right)
        self.assertEqual(result.state, DedupMatchState.DISTINCT)
        self.assertIn("TRADE_TIME_DISJOINT", result.reasons)

    def test_different_durable_trader_is_distinct(self):
        left = sig(1, trader="trader-entity:one")
        right = sig(2, trader="trader-entity:two")
        result = compare_economic_signatures(left, right)
        self.assertEqual(result.state, DedupMatchState.DISTINCT)
        self.assertIn("trader_entity_id", result.differing_fields)

    def test_different_quantity_is_distinct(self):
        left = sig(1, quantity="2500")
        right = sig(2, quantity="2600")
        result = compare_economic_signatures(left, right)
        self.assertEqual(result.state, DedupMatchState.DISTINCT)
        self.assertIn("quantity", result.differing_fields)

    def test_missing_quantity_downgrades_to_possible(self):
        left = sig(1, quantity=None)
        right = sig(2, quantity="2500")
        result = compare_economic_signatures(left, right)
        self.assertEqual(result.state, DedupMatchState.POSSIBLE_MATCH)
        self.assertIn("quantity", result.missing_fields)

    def test_sparse_unknown_economics_are_insufficient_not_duplicate(self):
        left = sig(
            1,
            instrument=InstrumentType.UNKNOWN,
            side=TradeSide.UNKNOWN,
            quantity=None,
            price=None,
            currency=None,
        )
        right = sig(
            2,
            instrument=InstrumentType.UNKNOWN,
            side=TradeSide.UNKNOWN,
            quantity=None,
            price=None,
            currency=None,
        )
        result = compare_economic_signatures(left, right)
        self.assertEqual(
            result.state,
            DedupMatchState.INSUFFICIENT_INFORMATION,
        )

    def test_option_strike_difference_is_distinct(self):
        left = sig(
            1,
            instrument=InstrumentType.CALL_OPTION,
            strike="15",
            expiry="2015-09-18",
        )
        right = sig(
            2,
            instrument=InstrumentType.CALL_OPTION,
            strike="20",
            expiry="2015-09-18",
        )
        result = compare_economic_signatures(left, right)
        self.assertEqual(result.state, DedupMatchState.DISTINCT)
        self.assertIn("option_strike", result.differing_fields)


if __name__ == "__main__":
    unittest.main()
