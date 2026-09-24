import hashlib
import tempfile
import unittest

from historical_mnpi.case_model import (
    CaseArtifactLink,
    CaseArtifactRole,
    CaseEventType,
    CaseIssuer,
    CaseParty,
    CasePartyRole,
    CaseProceedingStatus,
    CaseRegistry,
    HistoricalCase,
)
from historical_mnpi.raw_artifacts import (
    LocalContentAddressedArtifactStore,
    SourceArtifactRef,
    SourceLocatorKind,
    freeze_raw_artifact_manifest,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility,
    SourceRecord,
    SourceRegistry,
    SourceType,
)
from historical_mnpi.transaction_model import (
    FactStatus,
    HistoricalTransaction,
    InstrumentType,
    TimePrecision,
    TradeSide,
    TransactionRegistry,
)


def H(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source(
    *,
    source_id: str,
    raw: bytes,
    source_type: SourceType,
    admissibility: SourceAdmissibility,
    url: str,
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=source_type,
        admissibility=admissibility,
        publisher="Public source",
        title=source_id,
        url=url,
        publication_date="2015-08-11",
        sha256=H(raw),
        retrieved_at="2026-09-24T10:30:00Z",
        public_release_confirmed=True,
        case_id="CASE-TRADE",
    )


def fixture(*, include_judgment: bool = False, academic_only: bool = False):
    sources = SourceRegistry()
    raw_objects = []
    specs = []

    if academic_only:
        specs.append((
            _source(
                source_id="ACADEMIC:TRADE:001",
                raw=b"published academic reconstruction",
                source_type=SourceType.ACADEMIC_REPLICATION,
                admissibility=SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
                url="https://example.edu/replication.zip",
            ),
            b"published academic reconstruction",
            CaseArtifactRole.ACADEMIC_RECONSTRUCTION,
        ))
    else:
        specs.append((
            _source(
                source_id="SEC:TRADE:001",
                raw=b"historical complaint trade table",
                source_type=SourceType.SEC_COMPLAINT,
                admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
                url="https://www.sec.gov/example-trade.pdf",
            ),
            b"historical complaint trade table",
            CaseArtifactRole.COMPLAINT,
        ))
        if include_judgment:
            specs.append((
                _source(
                    source_id="COURT:JUDGMENT:001",
                    raw=b"historical final judgment",
                    source_type=SourceType.COURT_JUDGMENT,
                    admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
                    url="https://www.courtlistener.com/example-judgment.pdf",
                ),
                b"historical final judgment",
                CaseArtifactRole.JUDGMENT,
            ))

    for source, _raw, _role in specs:
        sources.register(source)

    refs = {}
    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        for source, raw, role in specs:
            artifact = store.retain(
                sources,
                source,
                raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T10:30:00Z",
                stored_at="2026-09-24T10:31:00Z",
            )
            raw_objects.append(artifact)
            refs[role] = SourceArtifactRef(
                source_id=source.source_id,
                source_proof_hash=source.proof_hash,
                artifact_id=artifact.artifact_id,
                artifact_sha256=artifact.sha256,
                artifact_record_proof_hash=artifact.proof_hash,
                locator_kind=SourceLocatorKind.TABLE,
                locator=f"role={role.value};page=1",
            )

        manifest = freeze_raw_artifact_manifest(
            sources,
            tuple(raw_objects),
            created_at="2026-09-24T10:32:00Z",
            created_by="test",
        )

    case = HistoricalCase(
        case_id="CASE-TRADE",
        title="Historical matter",
        event_type=CaseEventType.MERGER_ACQUISITION,
        information_origin="confidential acquisition information",
        proceeding_status=(
            CaseProceedingStatus.FINAL_CIVIL_JUDGMENT
            if include_judgment
            else CaseProceedingStatus.SETTLED
        ),
        parties=(
            CaseParty(
                party_id="party:trader",
                display_name="Historical Trader",
                roles=(CasePartyRole.TRADER, CasePartyRole.DEFENDANT),
            ),
        ),
        issuers=(
            CaseIssuer(
                issuer_id="issuer:target",
                legal_name="Target Corp.",
                cik="123456",
                ticker_at_case="TGT",
            ),
        ),
        artifacts=tuple(
            CaseArtifactLink(artifact_role=role, ref=refs[role])
            for _source_record, _raw, role in specs
        ),
    )
    cases = CaseRegistry()
    cases.register(
        case,
        source_registry=sources,
        artifact_manifest=manifest,
    )
    return sources, manifest, cases, case, refs


def sparse_transaction(case, complaint_ref):
    return HistoricalTransaction(
        trade_id="trade:001",
        case_id=case.case_id,
        case_proof_hash=case.proof_hash,
        trader_party_id="party:trader",
        issuer_id="issuer:target",
        source_ref=complaint_ref,
        fact_status=FactStatus.ALLEGED,
        status_ref=complaint_ref,
        trade_date="2015-08-10",
    )


class HistoricalTransactionTests(unittest.TestCase):
    def test_sparse_transaction_preserves_unknown_fields(self):
        sources, manifest, cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        transaction = sparse_transaction(case, ref)
        registry = TransactionRegistry()
        registry.register(
            transaction,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )

        self.assertEqual(transaction.fact_status, FactStatus.ALLEGED)
        self.assertEqual(transaction.time_precision, TimePrecision.DATE_ONLY)
        self.assertEqual(transaction.instrument_type, InstrumentType.UNKNOWN)
        self.assertEqual(transaction.side, TradeSide.UNKNOWN)
        self.assertIsNone(transaction.quantity)
        self.assertIsNone(transaction.execution_price)
        self.assertIsNone(transaction.documented_profit)
        self.assertEqual(len(transaction.proof_hash), 64)

    def test_fact_status_is_constructor_mandatory(self):
        _sources, _manifest, _cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        with self.assertRaises(TypeError):
            HistoricalTransaction(
                trade_id="trade:missing-status",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                trade_date="2015-08-10",
            )

    def test_exact_transaction_fields_preserve_decimal_text(self):
        _sources, _manifest, _cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        transaction = HistoricalTransaction(
            trade_id="trade:002",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
            fact_status=FactStatus.ALLEGED,
            status_ref=ref,
            instrument_type=InstrumentType.CALL_OPTION,
            side=TradeSide.BUY,
            trade_timestamp="2015-08-10T14:31:22-04:00",
            ticker_at_trade="TGT",
            currency="usd",
            quantity="164",
            execution_price="0.35",
            trade_amount="5740.00",
            option_strike="15",
            option_expiry="2015-09-18",
            documented_profit="120000.50",
        )
        self.assertEqual(transaction.currency, "USD")
        self.assertEqual(transaction.execution_price, "0.35")
        self.assertEqual(transaction.trade_amount, "5740.00")
        self.assertEqual(transaction.time_precision, TimePrecision.EXACT_TIMESTAMP)

    def test_date_range_is_supported_without_guessing_a_date(self):
        _sources, _manifest, _cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        transaction = HistoricalTransaction(
            trade_id="trade:003",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
            fact_status=FactStatus.ALLEGED,
            status_ref=ref,
            trade_date_range_start="2015-08-01",
            trade_date_range_end="2015-08-10",
        )
        self.assertEqual(transaction.time_precision, TimePrecision.DATE_RANGE)
        self.assertIsNone(transaction.trade_date)

    def test_missing_all_trade_time_fields_fails(self):
        _sources, _manifest, _cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        with self.assertRaisesRegex(ValueError, "trade-time"):
            HistoricalTransaction(
                trade_id="trade:004",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                fact_status=FactStatus.ALLEGED,
                status_ref=ref,
            )

    def test_multiple_time_precisions_fail(self):
        _sources, _manifest, _cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        with self.assertRaisesRegex(ValueError, "precision"):
            HistoricalTransaction(
                trade_id="trade:005",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                fact_status=FactStatus.ALLEGED,
                status_ref=ref,
                trade_date="2015-08-10",
                trade_timestamp="2015-08-10T14:00:00-04:00",
            )

    def test_option_fields_require_option_instrument(self):
        _sources, _manifest, _cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        with self.assertRaisesRegex(ValueError, "option instrument"):
            HistoricalTransaction(
                trade_id="trade:006",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                fact_status=FactStatus.ALLEGED,
                status_ref=ref,
                instrument_type=InstrumentType.STOCK,
                trade_date="2015-08-10",
                option_strike="15",
            )

    def test_negative_or_exponential_numeric_text_fails(self):
        _sources, _manifest, _cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        with self.assertRaisesRegex(ValueError, "plain decimal"):
            HistoricalTransaction(
                trade_id="trade:007",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                fact_status=FactStatus.ALLEGED,
                status_ref=ref,
                trade_date="2015-08-10",
                quantity="-100",
            )
        with self.assertRaisesRegex(ValueError, "plain decimal"):
            HistoricalTransaction(
                trade_id="trade:008",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                fact_status=FactStatus.ALLEGED,
                status_ref=ref,
                trade_date="2015-08-10",
                execution_price="1e3",
            )

    def test_unknown_party_cannot_register(self):
        sources, manifest, cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        transaction = HistoricalTransaction(
            trade_id="trade:009",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:unknown",
            issuer_id="issuer:target",
            source_ref=ref,
            fact_status=FactStatus.ALLEGED,
            status_ref=ref,
            trade_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "not a party"):
            TransactionRegistry().register(
                transaction,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_case_proof_mismatch_cannot_register(self):
        sources, manifest, cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        transaction = HistoricalTransaction(
            trade_id="trade:010",
            case_id=case.case_id,
            case_proof_hash=H(b"wrong case proof"),
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
            fact_status=FactStatus.ALLEGED,
            status_ref=ref,
            trade_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "case proof"):
            TransactionRegistry().register(
                transaction,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_transaction_source_must_be_linked_to_case(self):
        sources, manifest, cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        altered_ref = SourceArtifactRef(
            source_id=ref.source_id,
            source_proof_hash=ref.source_proof_hash,
            artifact_id=ref.artifact_id,
            artifact_sha256=ref.artifact_sha256,
            artifact_record_proof_hash=ref.artifact_record_proof_hash,
            locator_kind=SourceLocatorKind.PAGE,
            locator="page=99",
        )
        transaction = HistoricalTransaction(
            trade_id="trade:011",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=altered_ref,
            fact_status=FactStatus.ALLEGED,
            status_ref=ref,
            trade_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "not linked"):
            TransactionRegistry().register(
                transaction,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_complaint_cannot_support_found_liable(self):
        sources, manifest, cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        transaction = HistoricalTransaction(
            trade_id="trade:012",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
            fact_status=FactStatus.FOUND_LIABLE,
            status_ref=ref,
            trade_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "not supported"):
            TransactionRegistry().register(
                transaction,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_judgment_can_support_found_liable(self):
        sources, manifest, cases, case, refs = fixture(include_judgment=True)
        complaint = refs[CaseArtifactRole.COMPLAINT]
        judgment = refs[CaseArtifactRole.JUDGMENT]
        transaction = HistoricalTransaction(
            trade_id="trade:013",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=complaint,
            fact_status=FactStatus.FOUND_LIABLE,
            status_ref=judgment,
            trade_date="2015-08-10",
        )
        TransactionRegistry().register(
            transaction,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(transaction.fact_status, FactStatus.FOUND_LIABLE)

    def test_academic_reconstruction_must_stay_academic(self):
        sources, manifest, cases, case, refs = fixture(academic_only=True)
        ref = refs[CaseArtifactRole.ACADEMIC_RECONSTRUCTION]
        academic = HistoricalTransaction(
            trade_id="trade:014",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
            fact_status=FactStatus.ACADEMIC_RECONSTRUCTION,
            status_ref=ref,
            trade_date="2015-08-10",
        )
        TransactionRegistry().register(
            academic,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )

        relabeled = HistoricalTransaction(
            trade_id="trade:015",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
            fact_status=FactStatus.FOUND_LIABLE,
            status_ref=ref,
            trade_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "primary public record"):
            TransactionRegistry().register(
                relabeled,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_conflicting_trade_id_fails(self):
        sources, manifest, cases, case, refs = fixture()
        ref = refs[CaseArtifactRole.COMPLAINT]
        registry = TransactionRegistry()
        first = sparse_transaction(case, ref)
        registry.register(
            first,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        altered = HistoricalTransaction(
            trade_id=first.trade_id,
            case_id=first.case_id,
            case_proof_hash=first.case_proof_hash,
            trader_party_id=first.trader_party_id,
            issuer_id=first.issuer_id,
            source_ref=first.source_ref,
            fact_status=first.fact_status,
            status_ref=first.status_ref,
            trade_date="2015-08-09",
        )
        with self.assertRaisesRegex(ValueError, "different content"):
            registry.register(
                altered,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )


if __name__ == "__main__":
    unittest.main()
