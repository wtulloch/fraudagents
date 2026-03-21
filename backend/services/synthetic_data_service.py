"""
Synthetic data generator — creates realistic fraud/AML test scenarios.

Generates:
  • Customer profiles (individuals + businesses)
  • Transaction histories with embedded fraud patterns
  • KYC/KYB records
  • Adverse media articles
  • Sanctions watchlist entries

Patterns injected (controllable via profile):
  • Normal baseline transactions
  • Structuring (multiple sub-$10k transactions)
  • Layering (rapid fund movement across accounts)
  • Account takeover (geo/device anomalies)
  • Sanctions name matches (fuzzy)
  • PEP-linked accounts
  • Card fraud (high-frequency small transactions)
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from faker import Faker

from backend.config import settings

fake = Faker()
Faker.seed(settings.synthetic_seed)
random.seed(settings.synthetic_seed)

HIGH_RISK_JURISDICTIONS = [
    "IR", "KP", "SY", "CU", "SD", "MM", "AF", "LY", "YE", "VE",
]

CHANNELS = ["ACH", "WIRE", "SWIFT", "CARD", "FEDNOW", "RTP", "ZELLE", "CHECK"]
FRAUD_TYPOLOGIES = [
    "STRUCTURING", "LAYERING", "ACCOUNT_TAKEOVER", "CARD_FRAUD",
    "SANCTIONS_EVASION", "PEP_ACTIVITY", "SYNTHETIC_IDENTITY",
    "WIRE_FRAUD", "TRADE_BASED_ML", "FIRST_PARTY_FRAUD",
]

SANCTIONS_NAMES = [
    "Vladimir Petrov", "Ali Hassan Al-Rashid", "Kim Jong-chul",
    "Dmitri Volkov", "Fatima Al-Zahrawi", "Nikolai Sokolov",
    "Hamid Reza Tehrani", "Carlos Eduardo Mendez",
]


class SyntheticDataService:
    def __init__(self) -> None:
        self.fake = Faker()
        Faker.seed(settings.synthetic_seed)

    def generate_customer(self, customer_type: str = "individual") -> Dict[str, Any]:
        if customer_type == "business":
            return {
                "id": str(uuid.uuid4()),
                "customer_type": "business",
                "name": fake.company(),
                "tax_id": fake.bothify(text="##-#######"),
                "incorporation_country": random.choice(["US", "UK", "DE", "CA", "AU"] + HIGH_RISK_JURISDICTIONS[:2]),
                "industry": fake.job(),
                "address": fake.address(),
                "created_at": fake.date_time_between(start_date="-5y", end_date="-1y").isoformat(),
                "is_pep": random.random() < 0.03,
                "ubo_disclosed": random.random() > 0.15,
            }
        return {
            "id": str(uuid.uuid4()),
            "customer_type": "individual",
            "name": fake.name(),
            "dob": fake.date_of_birth(minimum_age=18, maximum_age=85).isoformat(),
            "nationality": fake.country_code(),
            "address": fake.address(),
            "ssn_masked": "***-**-" + fake.numerify(text="####"),
            "occupation": fake.job(),
            "created_at": fake.date_time_between(start_date="-5y", end_date="-1y").isoformat(),
            "is_pep": random.random() < 0.02,
            "is_sanctions_match": random.random() < 0.005,
        }

    def generate_account(self, customer_id: str) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "account_number": fake.bban(),
            "account_type": random.choice(["CHECKING", "SAVINGS", "BUSINESS", "MONEY_MARKET"]),
            "opened_date": fake.date_time_between(start_date="-4y", end_date="-6m").isoformat(),
            "balance": round(random.uniform(500, 500_000), 2),
            "currency": "USD",
            "status": random.choices(["ACTIVE", "DORMANT", "CLOSED"], weights=[0.85, 0.10, 0.05])[0],
            "risk_rating": random.choices(["LOW", "MEDIUM", "HIGH"], weights=[0.70, 0.20, 0.10])[0],
        }

    def generate_transaction(
        self,
        account_id: str,
        pattern: Optional[str] = None,
        base_amount: float = 5000.0,
    ) -> Dict[str, Any]:
        channel = random.choice(CHANNELS)
        amount = base_amount

        if pattern == "STRUCTURING":
            amount = round(random.uniform(8_500, 9_950), 2)  # just under $10k CTR
            channel = random.choice(["CASH", "ACH"])
        elif pattern == "CARD_FRAUD":
            amount = round(random.uniform(1, 500), 2)
            channel = "CARD"
        elif pattern == "WIRE_FRAUD":
            amount = round(random.uniform(5_000, 200_000), 2)
            channel = random.choice(["WIRE", "SWIFT"])
        elif pattern == "LAYERING":
            amount = round(random.uniform(1_000, 50_000), 2)
            channel = random.choice(["ACH", "WIRE", "FEDNOW"])

        is_international = channel in ["SWIFT", "WIRE"] and random.random() < 0.4
        counterparty_country = (
            random.choice(HIGH_RISK_JURISDICTIONS)
            if is_international and random.random() < 0.3
            else fake.country_code()
        )

        return {
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "counterparty_account_id": str(uuid.uuid4()),
            "counterparty_name": fake.name() if random.random() > 0.3 else fake.company(),
            "counterparty_bank": fake.company() + " Bank",
            "counterparty_country": counterparty_country,
            "amount": amount,
            "currency": "USD",
            "channel": channel,
            "direction": random.choice(["CREDIT", "DEBIT"]),
            "timestamp": fake.date_time_between(start_date="-90d", end_date="now").isoformat(),
            "description": fake.sentence(nb_words=6),
            "reference_number": fake.bothify(text="REF-??####??"),
            "ip_address": fake.ipv4() if channel in ["CARD", "FEDNOW", "RTP"] else None,
            "device_fingerprint": fake.md5() if channel == "CARD" else None,
            "geo_location": fake.city() + ", " + fake.country_code(),
            "is_international": is_international,
            "is_structured": pattern == "STRUCTURING",
            "swift_message_type": "MT103" if channel == "SWIFT" else None,
            "pattern": pattern or "NORMAL",
        }

    def generate_adverse_media_article(
        self, subject_name: str, is_high_risk: bool = False
    ) -> Dict[str, Any]:
        categories = (
            ["money_laundering", "fraud", "sanctions"] if is_high_risk
            else ["general_news"]
        )
        category = random.choice(categories)
        return {
            "id": str(uuid.uuid4()),
            "title": f"{'Investigation into' if is_high_risk else 'Profile of'} {subject_name}",
            "content": (
                f"{subject_name} was {'investigated for alleged ' + category.replace('_', ' ') if is_high_risk else 'featured in an article about business activities'}. "
                + fake.paragraph(nb_sentences=5)
            ),
            "source": random.choice(["Reuters", "Bloomberg", "FT", "WSJ", "BBC", "AP"]),
            "publication_date": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
            "risk_category": category,
            "entity_id": subject_name.lower().replace(" ", "_"),
            "metadata": {"keywords": [subject_name, category], "sentiment": "negative" if is_high_risk else "neutral"},
        }

    def generate_sanctions_entry(self, use_real_name: bool = False) -> Dict[str, Any]:
        name = (
            random.choice(SANCTIONS_NAMES) if use_real_name
            else fake.name()
        )
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "aliases": [fake.name() for _ in range(random.randint(0, 3))],
            "list_name": random.choice(["OFAC_SDN", "EU_CONSOLIDATED", "UN_1267", "HMT_CONSOLIDATED"]),
            "nationality": random.choice(HIGH_RISK_JURISDICTIONS),
            "date_of_birth": fake.date_of_birth(minimum_age=30, maximum_age=80).isoformat(),
            "entity_type": random.choice(["INDIVIDUAL", "ENTITY"]),
            "program": random.choice(["IRAN", "RUSSIA", "NORTH_KOREA", "TERRORISM", "NARCOTICS"]),
            "listed_date": fake.date_time_between(start_date="-10y", end_date="-1m").isoformat(),
            "content": f"Sanctioned individual/entity: {name}. Listed under {random.choice(['OFAC', 'EU', 'UN', 'HMT'])} for suspected involvement in financial crimes.",
            "title": f"Sanctions entry: {name}",
            "source": "Official sanctions list",
            "match_score": round(random.uniform(0.7, 1.0), 3),
            "entity_id": name.lower().replace(" ", "_"),
        }

    def generate_kyc_record(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "customer_id": customer["id"],
            "customer_type": customer.get("customer_type", "individual"),
            "name": customer.get("name", ""),
            "verified": random.random() > 0.1,
            "risk_rating": random.choices(["LOW", "MEDIUM", "HIGH", "VERY_HIGH"], weights=[0.60, 0.25, 0.12, 0.03])[0],
            "pep_status": customer.get("is_pep", False),
            "sanctions_match": customer.get("is_sanctions_match", False),
            "ubo_chain": [fake.name() for _ in range(random.randint(0, 3))],
            "jurisdiction": customer.get("incorporation_country", fake.country_code()),
            "last_review_date": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
            "content": (
                f"KYC record for {customer.get('name', 'Unknown')}. "
                f"Risk rating: {random.choice(['LOW', 'MEDIUM', 'HIGH'])}. "
                + fake.paragraph(nb_sentences=3)
            ),
            "title": f"KYC: {customer.get('name', 'Unknown')}",
            "source": "Internal CIF",
            "entity_id": customer["id"],
        }

    # ── Scenario generators ───────────────────────────────────────────────────

    def generate_alert_scenario(
        self, typology: str = "STRUCTURING", n_transactions: int = 10
    ) -> Dict[str, Any]:
        """Generate a complete alert scenario with customer, account, and transactions."""
        customer = self.generate_customer()
        account = self.generate_account(customer["id"])
        transactions = [
            self.generate_transaction(account["id"], pattern=typology)
            for _ in range(n_transactions)
        ]
        return {
            "customer": customer,
            "account": account,
            "transactions": transactions,
            "alert": {
                "id": str(uuid.uuid4()),
                "account_id": account["id"],
                "customer_name": customer["name"],
                "typology": typology,
                "amount": sum(t["amount"] for t in transactions),
                "transaction_ids": [t["id"] for t in transactions],
                "created_at": datetime.utcnow().isoformat(),
                "status": "NEW",
                "priority": random.choice(["HIGH", "MEDIUM", "LOW"]),
                "source": "TMS",
            },
        }

    def generate_batch(
        self,
        n_records: int = 500,
        fraud_rate: float = 0.15,
    ) -> Dict[str, Any]:
        """
        Generate a full synthetic dataset.
        Returns indexable documents for each AI Search index.
        """
        customers = [self.generate_customer(random.choice(["individual", "business"])) for _ in range(n_records)]
        accounts = [self.generate_account(c["id"]) for c in customers]

        transactions = []
        alerts = []
        kyc_records = []
        media_articles = []
        sanctions_entries = [self.generate_sanctions_entry(use_real_name=True) for _ in range(50)]

        n_fraud = int(n_records * fraud_rate)
        for i, (cust, acct) in enumerate(zip(customers, accounts)):
            typ = random.choice(FRAUD_TYPOLOGIES) if i < n_fraud else "NORMAL"
            n_txn = random.randint(5, 20)
            txns = [self.generate_transaction(acct["id"], pattern=typ if typ != "NORMAL" else None) for _ in range(n_txn)]
            transactions.extend(txns)
            kyc_records.append(self.generate_kyc_record(cust))

            if i < n_fraud:
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "account_id": acct["id"],
                    "customer_name": cust["name"],
                    "typology": typ,
                    "amount": sum(t["amount"] for t in txns[:3]),
                    "transaction_ids": [t["id"] for t in txns[:3]],
                    "created_at": datetime.utcnow().isoformat(),
                    "status": "NEW",
                    "priority": "HIGH" if typ in ["SANCTIONS_EVASION", "PEP_ACTIVITY"] else "MEDIUM",
                    "source": "TMS",
                })

                if random.random() < 0.4:
                    media_articles.append(
                        self.generate_adverse_media_article(cust["name"], is_high_risk=True)
                    )

        return {
            "batch_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "counts": {
                "customers": len(customers),
                "accounts": len(accounts),
                "transactions": len(transactions),
                "alerts": len(alerts),
                "kyc_records": len(kyc_records),
                "media_articles": len(media_articles),
                "sanctions_entries": len(sanctions_entries),
            },
            "customers": customers,
            "accounts": accounts,
            "transactions": transactions,
            "alerts": alerts,
            "kyc_records": kyc_records,
            "media_articles": media_articles,
            "sanctions_entries": sanctions_entries,
        }
