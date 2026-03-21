"""
scripts/generate_synthetic_data.py
------------------------------------
CLI tool to generate synthetic fraud / AML test data and optionally index it
into Azure AI Search to power the RAG pipeline.

Usage:
    python -m scripts.generate_synthetic_data [options]

Options:
    --records N          Number of records to generate (default: 200)
    --fraud-rate F       Fraction of fraud records 0.0–1.0 (default: 0.15)
    --seed S             Random seed for reproducibility
    --output FILE        Save JSON batch to this file (default: stdout summary)
    --no-index           Skip indexing to Azure AI Search
    --scenario NAME      Generate a targeted scenario instead of random batch
                         Choices: STRUCTURING CARD_FRAUD WIRE_FRAUD LAYERING
                                  SANCTIONS_EVASION ACCOUNT_TAKEOVER

Example:
    python -m scripts.generate_synthetic_data --records 500 --fraud-rate 0.2 --seed 42
    python -m scripts.generate_synthetic_data --scenario STRUCTURING --no-index --output batch.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def _run(
    n_records: int,
    fraud_rate: float,
    seed: int | None,
    output_file: str | None,
    index_to_search: bool,
    scenario: str | None,
) -> None:
    from backend.config import settings
    from backend.services.search_service import SearchService
    from backend.services.synthetic_data_service import SyntheticDataService

    search_svc = SearchService()
    await search_svc.ensure_indexes()

    synthetic_svc = SyntheticDataService(search_service=search_svc)

    start = time.perf_counter()

    if scenario:
        print(f"\nGenerating scenario: {scenario}  (15 transactions)\n")
        batch = await synthetic_svc.generate_scenario(typology=scenario, n_transactions=15)
    else:
        print(f"\nGenerating {n_records} records  (fraud_rate={fraud_rate:.0%}, seed={seed})\n")
        batch = await synthetic_svc.generate_batch(
            n_records=n_records,
            fraud_rate=fraud_rate,
            seed=seed,
        )

    elapsed = time.perf_counter() - start

    # Summary
    txn_count = len(batch.get("transactions", []))
    fraud_count = sum(1 for t in batch.get("transactions", []) if t.get("is_fraud"))
    cust_count = len(batch.get("customers", []))
    media_count = len(batch.get("adverse_media", []))
    sanctions_count = len(batch.get("sanctions_entries", []))
    kyc_count = len(batch.get("kyc_records", []))

    print(f"  Customers          : {cust_count}")
    print(f"  Transactions       : {txn_count}  ({fraud_count} fraud, {txn_count - fraud_count} legit)")
    print(f"  KYC Records        : {kyc_count}")
    print(f"  Adverse Media      : {media_count}")
    print(f"  Sanctions Entries  : {sanctions_count}")
    print(f"  Generation time    : {elapsed:.2f}s")

    # Save to file
    if output_file:
        with open(output_file, "w", encoding="utf-8") as fh:
            json.dump(batch, fh, indent=2, default=str)
        print(f"\n  Saved to: {output_file}")

    # Index to AI Search
    if index_to_search:
        print("\nIndexing into Azure AI Search…")
        idx_start = time.perf_counter()

        async def _safe_index(docs: list, index_name: str, label: str) -> None:
            if not docs:
                return
            try:
                await search_svc.index_documents(index_name, docs)
                print(f"  ✓ {label}: {len(docs)} docs → {index_name}")
            except Exception as exc:
                print(f"  ✗ {label}: {exc}")

        await asyncio.gather(
            _safe_index(
                batch.get("transactions", []) + batch.get("customers", []),
                settings.azure_search_transactions_index,
                "Transactions+Customers",
            ),
            _safe_index(
                batch.get("kyc_records", []),
                settings.azure_search_kyc_index,
                "KYC Records",
            ),
            _safe_index(
                batch.get("adverse_media", []),
                settings.azure_search_media_index,
                "Adverse Media",
            ),
            _safe_index(
                batch.get("sanctions_entries", []),
                settings.azure_search_sanctions_index,
                "Sanctions Entries",
            ),
        )

        idx_elapsed = time.perf_counter() - idx_start
        print(f"\n  Indexing time: {idx_elapsed:.2f}s")
    else:
        print("\n  Skipping AI Search indexing (--no-index flag set).")

    print("\nDone ✓")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic fraud/AML data for end-to-end testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--records", type=int, default=200, metavar="N",
                        help="Number of records (default: 200)")
    parser.add_argument("--fraud-rate", type=float, default=0.15, metavar="F",
                        help="Fraction of fraud records 0.0–1.0 (default: 0.15)")
    parser.add_argument("--seed", type=int, default=None, metavar="S",
                        help="Random seed for reproducibility")
    parser.add_argument("--output", metavar="FILE", default=None,
                        help="Save generated batch as JSON to this file")
    parser.add_argument("--no-index", action="store_true",
                        help="Skip indexing to Azure AI Search")
    parser.add_argument("--scenario", metavar="NAME", default=None,
                        choices=["STRUCTURING", "CARD_FRAUD", "WIRE_FRAUD", "LAYERING",
                                 "SANCTIONS_EVASION", "ACCOUNT_TAKEOVER", "PAYMENT_FRAUD"],
                        help="Generate a targeted scenario instead of a random batch")

    args = parser.parse_args()

    if args.fraud_rate < 0 or args.fraud_rate > 1:
        parser.error("--fraud-rate must be between 0.0 and 1.0")

    asyncio.run(_run(
        n_records=args.records,
        fraud_rate=args.fraud_rate,
        seed=args.seed,
        output_file=args.output,
        index_to_search=not args.no_index,
        scenario=args.scenario,
    ))


if __name__ == "__main__":
    main()
