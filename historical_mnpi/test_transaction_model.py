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
    HistoricalTransaction,
    InstrumentType,
    TimePrecision,
    TradeSide,
    TransactionRegistry,
)


def H(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture():
    raw = b"historical trade table"
    source = SourceRecord(
        source_id="SEC:TRADE:001",
        source_type=SourceType.SEC_COMPLAINT,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="SEC",
        title="Historical complaint table",
        url="https://www.sec.gov/example-trade.pdf",
        publication_date="2015-08-11",
        sha256=H(raw),
        retrieved_at="2026-09-24T10:30:00Z",
        public_release_confirmed=True,
        case_id="CASE-TRADE",
    )
    sources = SourceRegistry()
    sources.register(source)

    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        artifact = store.retain(
            sources,
            source,
            raw,
            media_type="application/pdf",
            acquired_at="2026-09-24T10:30:00Z",
            stored_at="2026-09-24T10:31:00Z",
        )
        manifest = freeze_raw_artifact_manifest(
            sources,
            (artifact,),
            created_at="2026-09-24T10:32:00Z",
            created_by="test",
        )

    ref = SourceArtifactRef(
        source_id=source.source_id,
        source_proof_hash=source.proof_hash,
        artifact_id=artifact.artifact_id,
        artifact_sha256=artifact.sha256,
        artifact_record_proof_hash=artifact.proof_hash,
        locator_kind=SourceLocatorKind.TABLE,
        locator="page=10;table=1;row=2",
    )

    case = HistoricalCase(
        case_id="CASE-TRADE",
        title="Historical matter",
        event_type=CaseEventType.MERGER_ACQUISITION,
        information_origin="confidential acquisition information",
        proceeding_status=CaseProceedingStatus.SETTLED,
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
        artifacts=(
            CaseArtifactLink(
                artifact_role=CaseArtifactRole.COMPLAINT,
                ref=ref,
            ),
        ),
    )
    cases = CaseRegistry()
    cases.register(
        case,
        source_registry=sources,
        artifact_manifest=manifest,
    )
    return sources, manifest, cases, case, ref


def sparse_transaction(case, ref):
    return HistoricalTransaction(
        trade_id="trade:001",
        case_id=case.case_id,
        case_proof_hash=case.proof_hash,
        trader_party_id="party:trader",
        issuer_id="issuer:target",
        source_ref=ref,
        trade_date="2015-08-10",
    )


class HistoricalTransactionTests(unittest.TestCase):
    def test_sparse_transaction_preserves_unknown_fields(self):
        sources, manifest, cases, case, ref = fixture()
        transaction = sparse_transaction(case, ref)
        registry = TransactionRegistry()
        registry.register(
            transaction,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )

        self.assertEqual(transaction.time_precision, TimePrecision.DATE_ONLY)
        self.assertEqual(transaction.instrument_type, InstrumentType.UNKNOWN)
        self.assertEqual(transaction.side, TradeSide.UNKNOWN)
        self.assertIsNone(transaction.quantity)
        self.assertIsNone(transaction.execution_price)
        self.assertIsNone(transaction.documented_profit)
        self.assertEqual(len(transaction.proof_hash), 64)

    def test_exact_transaction_fields_are_preserved_not_converted_to_float(self):
        _sources, _manifest, _cases, case, ref = fixture()
        transaction = HistoricalTransaction(
            trade_id="trade:002",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
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
        _sources, _manifest, _cases, case, ref = fixture()
        transaction = HistoricalTransaction(
            trade_id="trade:003",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
            trade_date_range_start="2015-08-01",
            trade_date_range_end="2015-08-10",
        )
        self.assertEqual(transaction.time_precision, TimePrecision.DATE_RANGE)
        self.assertIsNone(transaction.trade_date)

    def test_missing_all_trade_time_fields_fails(self):
        _sources, _manifest, _cases, case, ref = fixture()
        with self.assertRaisesRegex(ValueError, "trade-time"):
            HistoricalTransaction(
                trade_id="trade:004",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
            )

    def test_multiple_time_precisions_fail(self):
        _sources, _manifest, _cases, case, ref = fixture()
        with self.assertRaisesRegex(ValueError, "precision"):
            HistoricalTransaction(
                trade_id="trade:005",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                trade_date="2015-08-10",
                trade_timestamp="2015-08-10T14:00:00-04:00",
            )

    def test_option_fields_require_option_instrument(self):
        _sources, _manifest, _cases, case, ref = fixture()
        with self.assertRaisesRegex(ValueError, "option instrument"):
            HistoricalTransaction(
                trade_id="trade:006",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
                instrument_type=InstrumentType.STOCK,
                trade_date="2015-08-10",
                option_strike="15",
            )

    def test_negative_or_exponential_numeric_text_fails(self):
        _sources, _manifest, _cases, case, ref = fixture()
        with self.assertRaisesRegex(ValueError, "plain decimal"):
            HistoricalTransaction(
                trade_id="trade:007",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                trader_party_id="party:trader",
                issuer_id="issuer:target",
                source_ref=ref,
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
                trade_date="2015-08-10",
                execution_price="1e3",
            )

    def test_unknown_party_or_issuer_cannot_register(self):
        sources, manifest, cases, case, ref = fixture()
        registry = TransactionRegistry()
        bad_party = HistoricalTransaction(
            trade_id="trade:009",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            trader_party_id="party:unknown",
            issuer_id="issuer:target",
            source_ref=ref,
            trade_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "not a party"):
            registry.register(
                bad_party,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_case_proof_mismatch_cannot_register(self):
        sources, manifest, cases, case, ref = fixture()
        transaction = HistoricalTransaction(
            trade_id="trade:010",
            case_id=case.case_id,
            case_proof_hash=H(b"wrong case proof"),
            trader_party_id="party:trader",
            issuer_id="issuer:target",
            source_ref=ref,
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
        sources, manifest, cases, case, ref = fixture()
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
            trade_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "not linked"):
            TransactionRegistry().register(
                transaction,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_conflicting_trade_id_fails(self):
        sources, manifest, cases, case, ref = fixture()
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
