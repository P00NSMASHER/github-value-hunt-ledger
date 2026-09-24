import hashlib
import tempfile
import unittest

from historical_mnpi.case_model import (
    CaseArtifactLink, CaseArtifactRole, CaseEventType, CaseIssuer, CaseParty,
    CasePartyRole, CaseProceedingStatus, CaseRegistry, HistoricalCase,
)
from historical_mnpi.economic_dedupe import (
    DedupeDecisionType, DedupeProposal, DedupeRelation, DedupeReviewChecks,
    build_economic_transaction_cluster, decide_dedupe,
    propose_transaction_dedupe,
)
from historical_mnpi.entity_resolution import (
    CanonicalEntity, CaseEntityResolution, EntityKind, EntityRegistry,
    ResolutionStatus,
)
from historical_mnpi.raw_artifacts import (
    LocalContentAddressedArtifactStore, SourceArtifactRef, SourceLocatorKind,
    freeze_raw_artifact_manifest,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility, SourceRecord, SourceRegistry, SourceType,
    canonical_hash,
)
from historical_mnpi.transaction_model import (
    FactStatus, HistoricalTransaction, InstrumentType, TradeSide,
)


def H(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()



def all_dedupe_checks() -> DedupeReviewChecks:
    return DedupeReviewChecks(
        identity_checked=True,
        temporal_overlap_checked=True,
        economic_fields_checked=True,
        source_evidence_checked=True,
        duplicate_risk_checked=True,
    )


def fixture(resolve_identities=True):
    specs = (
        ("complaint", SourceType.SEC_COMPLAINT, CaseArtifactRole.COMPLAINT, b"complaint"),
        ("judgment", SourceType.COURT_JUDGMENT, CaseArtifactRole.JUDGMENT, b"judgment"),
    )
    sources = SourceRegistry()
    records = []
    for name, stype, role, raw in specs:
        rec = SourceRecord(
            source_id=f"SRC:{name}",
            source_type=stype,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            publisher=name,
            title=name,
            url=f"https://example.org/{name}",
            publication_date="2015-01-01",
            sha256=H(raw),
            retrieved_at="2026-09-24T14:00:00Z",
            public_release_confirmed=True,
            case_id="CASE-DEDUPE",
        )
        sources.register(rec)
        records.append((rec, raw, role))
    refs = {}
    artifacts = []
    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        for rec, raw, role in records:
            art = store.retain(
                sources, rec, raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T14:00:00Z",
                stored_at="2026-09-24T14:01:00Z",
            )
            artifacts.append(art)
            refs[role] = SourceArtifactRef(
                source_id=rec.source_id,
                source_proof_hash=rec.proof_hash,
                artifact_id=art.artifact_id,
                artifact_sha256=art.sha256,
                artifact_record_proof_hash=art.proof_hash,
                locator_kind=SourceLocatorKind.TABLE,
                locator=f"role={role.value};row=1",
            )
        manifest = freeze_raw_artifact_manifest(
            sources, tuple(artifacts),
            created_at="2026-09-24T14:02:00Z",
            created_by="test",
        )
    case = HistoricalCase(
        case_id="CASE-DEDUPE",
        title="Economic dedupe case",
        event_type=CaseEventType.MERGER_ACQUISITION,
        information_origin="historical transaction",
        proceeding_status=CaseProceedingStatus.FINAL_CIVIL_JUDGMENT,
        parties=(CaseParty("party:trader", "Trader", (CasePartyRole.TRADER,)),),
        issuers=(CaseIssuer("issuer:target", "Target Corp."),),
        artifacts=tuple(CaseArtifactLink(role, refs[role]) for _r, _b, role in records),
    )
    cases = CaseRegistry()
    cases.register(case, source_registry=sources, artifact_manifest=manifest)

    entities = EntityRegistry()
    person = entities.register_entity(
        CanonicalEntity("person:trader", EntityKind.PERSON, "Trader")
    )
    issuer = entities.register_entity(
        CanonicalEntity("issuer:canonical", EntityKind.ISSUER, "Target Corp.")
    )
    if resolve_identities:
        entities.register_case_resolution(
            CaseEntityResolution(
                "resolution:trader", case.case_id, case.proof_hash,
                "party:trader", EntityKind.PERSON, ResolutionStatus.RESOLVED,
                (refs[CaseArtifactRole.COMPLAINT],),
                canonical_entity_id=person.entity_id,
            ),
            cases=cases, source_registry=sources, artifact_manifest=manifest,
        )
        entities.register_case_resolution(
            CaseEntityResolution(
                "resolution:issuer", case.case_id, case.proof_hash,
                "issuer:target", EntityKind.ISSUER, ResolutionStatus.RESOLVED,
                (refs[CaseArtifactRole.COMPLAINT],),
                canonical_entity_id=issuer.entity_id,
            ),
            cases=cases, source_registry=sources, artifact_manifest=manifest,
        )

    left = HistoricalTransaction(
        trade_id="trade:complaint",
        case_id=case.case_id,
        case_proof_hash=case.proof_hash,
        trader_party_id="party:trader",
        issuer_id="issuer:target",
        source_ref=refs[CaseArtifactRole.COMPLAINT],
        fact_status=FactStatus.ALLEGED,
        status_ref=refs[CaseArtifactRole.COMPLAINT],
        instrument_type=InstrumentType.STOCK,
        side=TradeSide.BUY,
        trade_date="2015-08-10",
        ticker_at_trade="TGT",
        quantity="2500",
        execution_price="30.375",
    )
    right = HistoricalTransaction(
        trade_id="trade:judgment",
        case_id=case.case_id,
        case_proof_hash=case.proof_hash,
        trader_party_id="party:trader",
        issuer_id="issuer:target",
        source_ref=refs[CaseArtifactRole.JUDGMENT],
        fact_status=FactStatus.COURT_ESTABLISHED,
        status_ref=refs[CaseArtifactRole.JUDGMENT],
        instrument_type=InstrumentType.STOCK,
        side=TradeSide.BUY,
        trade_date="2015-08-10",
        quantity="2500",
        execution_price="30.375",
    )
    return sources, manifest, cases, entities, left, right


class EconomicDedupeTests(unittest.TestCase):
    def test_date_only_matching_trade_stays_possible_same(self):
        sources, manifest, cases, entities, left, right = fixture()
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)
        self.assertIn("quantity", proposal.matching_fields)
        self.assertIn("execution_price", proposal.matching_fields)
        self.assertIn(
            "COMPATIBLE_TIME_AND_STRONG_ECONOMIC_MATCH",
            proposal.reason_codes,
        )
        proposal.verify_integrity()

    def test_exact_timestamp_matching_trade_can_propose_exact_same(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            **{
                **left.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
            }
        )
        right = HistoricalTransaction(
            **{
                **right.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": "TGT",
            }
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.EXACT_SAME)
        self.assertIn(
            "EXACT_TIMESTAMP_AND_STRONG_ECONOMIC_ANCHORS",
            proposal.reason_codes,
        )

    def test_exact_same_requires_trade_side_confirmation(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            **{
                **left.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "side": TradeSide.UNKNOWN,
            }
        )
        right = HistoricalTransaction(
            **{
                **right.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": "TGT",
            }
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)
        self.assertIn("TRADE_SIDE_NOT_CONFIRMED", proposal.reason_codes)

    def test_exact_same_requires_instrument_type_confirmation(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            **{
                **left.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "instrument_type": InstrumentType.UNKNOWN,
            }
        )
        right = HistoricalTransaction(
            **{
                **right.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": "TGT",
            }
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)
        self.assertIn("INSTRUMENT_TYPE_NOT_CONFIRMED", proposal.reason_codes)

    def test_exact_same_requires_currency_agreement_when_currency_is_present(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            **{
                **left.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "currency": "USD",
            }
        )
        right = HistoricalTransaction(
            **{
                **right.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": "TGT",
                "currency": None,
            }
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)
        self.assertIn("CURRENCY_NOT_CONFIRMED", proposal.reason_codes)

    def test_exact_same_requires_matching_security_identifier(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            **{
                **left.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": None,
            }
        )
        right = HistoricalTransaction(
            **{
                **right.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": None,
            }
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)
        self.assertIn(
            "SECURITY_IDENTIFIER_NOT_CONFIRMED",
            proposal.reason_codes,
        )

    def test_different_tickers_for_same_issuer_are_distinct(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            **{
                **left.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": "CLASSA",
            }
        )
        right = HistoricalTransaction(
            **{
                **right.__dict__,
                "trade_date": None,
                "trade_timestamp": "2015-08-10T10:15:30-04:00",
                "ticker_at_trade": "CLASSB",
            }
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.DISTINCT)
        self.assertIn("ticker_at_trade", proposal.conflicting_fields)

    def test_conflicting_currency_is_distinct(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(**{**left.__dict__, "currency": "USD"})
        right = HistoricalTransaction(**{**right.__dict__, "currency": "CAD"})
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.DISTINCT)
        self.assertIn("currency", proposal.conflicting_fields)

    def test_same_day_identical_economics_never_auto_exact(self):
        sources, manifest, cases, entities, left, right = fixture()
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertNotEqual(proposal.relation, DedupeRelation.EXACT_SAME)
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)

    def test_conflicting_quantity_is_distinct(self):
        sources, manifest, cases, entities, left, right = fixture()
        right = HistoricalTransaction(
            **{**right.__dict__, "quantity": "2600"}
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.DISTINCT)
        self.assertIn("quantity", proposal.conflicting_fields)

    def test_sparse_compatible_rows_are_possible_not_automatically_merged(self):
        sources, manifest, cases, entities, left, right = fixture()
        right = HistoricalTransaction(
            trade_id=right.trade_id,
            case_id=right.case_id,
            case_proof_hash=right.case_proof_hash,
            trader_party_id=right.trader_party_id,
            issuer_id=right.issuer_id,
            source_ref=right.source_ref,
            fact_status=right.fact_status,
            status_ref=right.status_ref,
            trade_date=right.trade_date,
            quantity="2500",
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)

    def test_generic_side_and_instrument_match_are_not_enough(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            trade_id=left.trade_id,
            case_id=left.case_id,
            case_proof_hash=left.case_proof_hash,
            trader_party_id=left.trader_party_id,
            issuer_id=left.issuer_id,
            source_ref=left.source_ref,
            fact_status=left.fact_status,
            status_ref=left.status_ref,
            instrument_type=InstrumentType.STOCK,
            side=TradeSide.BUY,
            trade_date=left.trade_date,
        )
        right = HistoricalTransaction(
            trade_id=right.trade_id,
            case_id=right.case_id,
            case_proof_hash=right.case_proof_hash,
            trader_party_id=right.trader_party_id,
            issuer_id=right.issuer_id,
            source_ref=right.source_ref,
            fact_status=right.fact_status,
            status_ref=right.status_ref,
            instrument_type=InstrumentType.STOCK,
            side=TradeSide.BUY,
            trade_date=right.trade_date,
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.INSUFFICIENT)
        self.assertIn(
            "ONLY_GENERIC_ECONOMIC_FIELDS_MATCH",
            proposal.reason_codes,
        )

    def test_exact_timestamp_requires_quantity_plus_price_or_amount(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            trade_id=left.trade_id,
            case_id=left.case_id,
            case_proof_hash=left.case_proof_hash,
            trader_party_id=left.trader_party_id,
            issuer_id=left.issuer_id,
            source_ref=left.source_ref,
            fact_status=left.fact_status,
            status_ref=left.status_ref,
            instrument_type=InstrumentType.STOCK,
            side=TradeSide.BUY,
            trade_timestamp="2015-08-10T10:15:30-04:00",
            quantity="2500",
        )
        right = HistoricalTransaction(
            trade_id=right.trade_id,
            case_id=right.case_id,
            case_proof_hash=right.case_proof_hash,
            trader_party_id=right.trader_party_id,
            issuer_id=right.issuer_id,
            source_ref=right.source_ref,
            fact_status=right.fact_status,
            status_ref=right.status_ref,
            instrument_type=InstrumentType.STOCK,
            side=TradeSide.BUY,
            trade_timestamp="2015-08-10T10:15:30-04:00",
            quantity="2500",
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)
        self.assertNotEqual(proposal.relation, DedupeRelation.EXACT_SAME)

    def test_option_exact_timestamp_without_contract_identity_is_not_exact(self):
        sources, manifest, cases, entities, left, right = fixture()
        left = HistoricalTransaction(
            trade_id=left.trade_id,
            case_id=left.case_id,
            case_proof_hash=left.case_proof_hash,
            trader_party_id=left.trader_party_id,
            issuer_id=left.issuer_id,
            source_ref=left.source_ref,
            fact_status=left.fact_status,
            status_ref=left.status_ref,
            instrument_type=InstrumentType.CALL_OPTION,
            side=TradeSide.BUY,
            trade_timestamp="2015-08-10T10:15:30-04:00",
            quantity="2500",
            execution_price="30.375",
        )
        right = HistoricalTransaction(
            trade_id=right.trade_id,
            case_id=right.case_id,
            case_proof_hash=right.case_proof_hash,
            trader_party_id=right.trader_party_id,
            issuer_id=right.issuer_id,
            source_ref=right.source_ref,
            fact_status=right.fact_status,
            status_ref=right.status_ref,
            instrument_type=InstrumentType.CALL_OPTION,
            side=TradeSide.BUY,
            trade_timestamp="2015-08-10T10:15:30-04:00",
            quantity="2500",
            execution_price="30.375",
        )
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.POSSIBLE_SAME)
        self.assertIn(
            "OPTION_CONTRACT_NOT_FULLY_IDENTIFIED",
            proposal.reason_codes,
        )

    def test_unresolved_identity_produces_insufficient_proposal(self):
        sources, manifest, cases, entities, left, right = fixture(resolve_identities=False)
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(proposal.relation, DedupeRelation.INSUFFICIENT)
        self.assertIn("IDENTITY_NOT_RESOLVED", proposal.reason_codes)

    def test_distinct_or_insufficient_proposal_cannot_be_confirmed_same(self):
        sources, manifest, cases, entities, left, right = fixture()
        different = HistoricalTransaction(
            **{**right.__dict__, "quantity": "9999"}
        )
        proposal = propose_transaction_dedupe(
            left, different, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        with self.assertRaisesRegex(ValueError, "requires exact/possible"):
            decide_dedupe(
                proposal,
                decision=DedupeDecisionType.SAME_TRANSACTION,
                checks=all_dedupe_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T15:00:00Z",
                rationale="Should fail.",
            )

    def test_same_transaction_requires_explicit_reviewer_checks(self):
        sources, manifest, cases, entities, left, right = fixture()
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        incomplete = DedupeReviewChecks(
            identity_checked=True,
            temporal_overlap_checked=True,
            economic_fields_checked=False,
            source_evidence_checked=True,
            duplicate_risk_checked=True,
        )
        with self.assertRaisesRegex(ValueError, "all dedupe reviewer checks"):
            decide_dedupe(
                proposal,
                decision=DedupeDecisionType.SAME_TRANSACTION,
                checks=incomplete,
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T15:00:00Z",
                rationale="Economic fields were not fully checked.",
            )

    def test_cluster_requires_explicit_same_decision_and_preserves_sources(self):
        sources, manifest, cases, entities, left, right = fixture()
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        decision = decide_dedupe(
            proposal,
            decision=DedupeDecisionType.SAME_TRANSACTION,
            checks=all_dedupe_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T15:00:00Z",
            rationale="Same date, parties, issuer, side, instrument, quantity and price.",
        )
        cluster = build_economic_transaction_cluster(
            (left, right),
            proposals=(proposal,),
            decisions=(decision,),
            trader_entity_id="person:trader",
            issuer_entity_id="issuer:canonical",
        )
        cluster.verify_integrity()
        self.assertEqual(len(cluster.members), 2)
        self.assertEqual(
            len({member.source_ref_hash for member in cluster.members}),
            2,
        )
        self.assertEqual(
            {member.fact_status for member in cluster.members},
            {"ALLEGED", "COURT_ESTABLISHED"},
        )

    def test_stale_dedupe_decision_cannot_apply_to_changed_row(self):
        sources, manifest, cases, entities, left, right = fixture()
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        decision = decide_dedupe(
            proposal,
            decision=DedupeDecisionType.SAME_TRANSACTION,
            checks=all_dedupe_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T15:00:00Z",
            rationale="Reviewed exact rows.",
        )
        changed_right = HistoricalTransaction(
            **{**right.__dict__, "execution_price": "31.000"}
        )
        with self.assertRaisesRegex(ValueError, "transaction hash"):
            build_economic_transaction_cluster(
                (left, changed_right),
                proposals=(proposal,),
                decisions=(decision,),
                trader_entity_id="person:trader",
                issuer_entity_id="issuer:canonical",
            )

    def test_cluster_entity_ids_must_match_reviewed_proposal(self):
        sources, manifest, cases, entities, left, right = fixture()
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        decision = decide_dedupe(
            proposal,
            decision=DedupeDecisionType.SAME_TRANSACTION,
            checks=all_dedupe_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T15:00:00Z",
            rationale="Reviewed canonical identities.",
        )
        with self.assertRaisesRegex(ValueError, "canonical entity identity mismatch"):
            build_economic_transaction_cluster(
                (left, right),
                proposals=(proposal,),
                decisions=(decision,),
                trader_entity_id="person:other",
                issuer_entity_id="issuer:canonical",
            )

    def test_three_member_cluster_requires_complete_pairwise_clique(self):
        sources, manifest, cases, entities, left, right = fixture()
        third = HistoricalTransaction(
            trade_id="trade:third",
            case_id=left.case_id,
            case_proof_hash=left.case_proof_hash,
            trader_party_id=left.trader_party_id,
            issuer_id=left.issuer_id,
            source_ref=left.source_ref,
            fact_status=left.fact_status,
            status_ref=left.status_ref,
            instrument_type=left.instrument_type,
            side=left.side,
            trade_date=left.trade_date,
            quantity=left.quantity,
            execution_price=left.execution_price,
        )
        p1 = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        p2 = propose_transaction_dedupe(
            left, third, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        decisions = tuple(
            decide_dedupe(
                proposal,
                decision=DedupeDecisionType.SAME_TRANSACTION,
                checks=all_dedupe_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T15:00:00Z",
                rationale="Confirmed pair.",
            )
            for proposal in (p1, p2)
        )
        with self.assertRaisesRegex(ValueError, "complete pairwise"):
            build_economic_transaction_cluster(
                (left, right, third),
                proposals=(p1, p2),
                decisions=decisions,
                trader_entity_id="person:trader",
                issuer_entity_id="issuer:canonical",
            )


    def test_cluster_rejects_decision_not_bound_to_reviewed_proposal(self):
        sources, manifest, cases, entities, left, right = fixture()
        proposal = propose_transaction_dedupe(
            left, right, entities=entities, cases=cases,
            source_registry=sources, artifact_manifest=manifest,
        )
        decision = decide_dedupe(
            proposal,
            decision=DedupeDecisionType.SAME_TRANSACTION,
            checks=all_dedupe_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T15:00:00Z",
            rationale="Reviewed pair.",
        )

        alternate_body = {
            "schema": 1,
            "left_trade_id": proposal.left_trade_id,
            "left_transaction_hash": proposal.left_transaction_hash,
            "right_trade_id": proposal.right_trade_id,
            "right_transaction_hash": proposal.right_transaction_hash,
            "trader_entity_id": proposal.trader_entity_id,
            "issuer_entity_id": proposal.issuer_entity_id,
            "relation": DedupeRelation.POSSIBLE_SAME.value,
            "matching_fields": ["quantity"],
            "conflicting_fields": [],
            "reason_codes": ["ALTERNATE_REVIEW_THEORY"],
        }
        alternate = DedupeProposal(
            left_trade_id=proposal.left_trade_id,
            left_transaction_hash=proposal.left_transaction_hash,
            right_trade_id=proposal.right_trade_id,
            right_transaction_hash=proposal.right_transaction_hash,
            trader_entity_id=proposal.trader_entity_id,
            issuer_entity_id=proposal.issuer_entity_id,
            relation=DedupeRelation.POSSIBLE_SAME,
            matching_fields=("quantity",),
            conflicting_fields=(),
            reason_codes=("ALTERNATE_REVIEW_THEORY",),
            proposal_hash=canonical_hash(alternate_body),
        )
        alternate.verify_integrity()
        self.assertNotEqual(alternate.proposal_hash, proposal.proposal_hash)

        with self.assertRaisesRegex(ValueError, "proposal hash"):
            build_economic_transaction_cluster(
                (left, right),
                proposals=(alternate,),
                decisions=(decision,),
                trader_entity_id="person:trader",
                issuer_entity_id="issuer:canonical",
            )

    def test_mismatched_artifact_manifest_and_source_registry_fail_closed(self):
        sources, manifest, cases, entities, left, right = fixture()
        mismatched = SourceRegistry()
        for item in sources.all():
            mismatched.register(item)
        mismatched.register(SourceRecord(
            source_id="SRC:extra",
            source_type=SourceType.SEC_COMPLAINT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            publisher="extra",
            title="extra",
            url="https://example.org/extra-dedupe",
            publication_date="2015-01-02",
            sha256=H(b"extra-dedupe"),
            retrieved_at="2026-09-24T14:03:00Z",
            public_release_confirmed=True,
            case_id="CASE-DEDUPE",
        ))
        with self.assertRaisesRegex(ValueError, "manifest/source registry mismatch"):
            propose_transaction_dedupe(
                left,
                right,
                entities=entities,
                cases=cases,
                source_registry=mismatched,
                artifact_manifest=manifest,
            )

if __name__ == "__main__":
    unittest.main()
