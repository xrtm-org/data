# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

r"""Small deterministic real-world binary question corpus.

The records are market-style questions anchored to stable public historical
facts. They are intentionally embedded in Python so offline tests do not depend
on package-data configuration or live network access.

**Benchmark Corpus Policy:**
This is the xrtm-real-binary-v1 seed corpus (Tier 1, Apache 2.0 license).
It is a minimal fixture for CI smoke tests and provider-free validation.
For comprehensive release-gate benchmarks, use ForecastBench (Tier 1).

See data/docs/benchmark-corpus-policy.md for source classification and
licensing requirements.
"""

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion, MetadataBase

REAL_BINARY_CORPUS_ID = "xrtm-real-binary-v1"

_REAL_BINARY_QUESTION_CORPUS: tuple[dict[str, Any], ...] = (
    {
        "id": "real-binary-2023-fed-mar-hike",
        "title": "Will the Federal Reserve raise the federal funds target range on March 22, 2023?",
        "content": "The FOMC is scheduled to announce its policy decision on March 22, 2023.",
        "resolution_criteria": "Resolves YES if the target range is higher immediately after the meeting than before it.",
        "snapshot_time": "2023-03-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "central-bank", "rates", "us"],
        "source_metadata": {
            "event_date": "2023-03-22",
            "source_url": "https://www.federalreserve.gov/monetarypolicy/fomc.htm",
            "verification_method": "Federal Reserve FOMC statement archive",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-03-22T18:00:00Z",
        "resolution_notes": "The target range was increased by 25 basis points to 4.75%-5.00%.",
    },
    {
        "id": "real-binary-2023-boe-sep-hike",
        "title": "Will the Bank of England raise Bank Rate on September 21, 2023?",
        "content": "The Bank of England Monetary Policy Committee decision is due on September 21, 2023.",
        "resolution_criteria": "Resolves YES if Bank Rate is increased at the September 2023 MPC announcement.",
        "snapshot_time": "2023-09-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "central-bank", "rates", "uk"],
        "source_metadata": {
            "event_date": "2023-09-21",
            "source_url": "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2023/september-2023",
            "verification_method": "Bank of England MPC summary",
        },
        "resolved_outcome": False,
        "resolution_time": "2023-09-21T11:00:00Z",
        "resolution_notes": "The MPC voted to maintain Bank Rate at 5.25%.",
    },
    {
        "id": "real-binary-2023-ecb-sep-hike",
        "title": "Will the European Central Bank raise its key interest rates on September 14, 2023?",
        "content": "The ECB Governing Council is scheduled to announce its monetary policy decision.",
        "resolution_criteria": "Resolves YES if the ECB raises its main policy rates in the September 2023 decision.",
        "snapshot_time": "2023-09-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "central-bank", "rates", "eurozone"],
        "source_metadata": {
            "event_date": "2023-09-14",
            "source_url": "https://www.ecb.europa.eu/press/pr/date/2023/html/index.en.html",
            "verification_method": "ECB monetary policy decisions archive",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-09-14T12:15:00Z",
        "resolution_notes": "The ECB raised the three key ECB interest rates by 25 basis points.",
    },
    {
        "id": "real-binary-2023-boj-negative-rates-end",
        "title": "Will the Bank of Japan end negative interest rates by December 31, 2023?",
        "content": "The question tracks whether the BOJ's short-term policy rate exits negative territory in 2023.",
        "resolution_criteria": "Resolves YES if the BOJ ends negative interest-rate policy on or before December 31, 2023.",
        "snapshot_time": "2023-07-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "central-bank", "rates", "japan"],
        "source_metadata": {
            "event_date": "2023-12-31",
            "source_url": "https://www.boj.or.jp/en/mopo/mpmdeci/index.htm",
            "verification_method": "Bank of Japan monetary policy releases",
        },
        "resolved_outcome": False,
        "resolution_time": "2023-12-31T23:59:59Z",
        "resolution_notes": "The BOJ did not end negative rates during calendar year 2023.",
    },
    {
        "id": "real-binary-2024-sec-spot-bitcoin-etf-by-jan10",
        "title": "Will the SEC approve spot Bitcoin ETFs by January 10, 2024?",
        "content": "Several spot Bitcoin ETF applications have a January 2024 decision window.",
        "resolution_criteria": "Resolves YES if the SEC approves at least one spot Bitcoin ETF on or before January 10, 2024.",
        "snapshot_time": "2023-12-15T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "crypto", "regulation", "us", "etf"],
        "source_metadata": {
            "event_date": "2024-01-10",
            "source_url": "https://www.sec.gov/news/pressreleases",
            "verification_method": "SEC approval order and press releases",
        },
        "resolved_outcome": True,
        "resolution_time": "2024-01-10T21:30:00Z",
        "resolution_notes": "The SEC approved spot Bitcoin exchange-traded products on January 10, 2024.",
    },
    {
        "id": "real-binary-2023-bitcoin-above-40k-eoy",
        "title": "Will Bitcoin trade above $40,000 at the end of December 31, 2023 UTC?",
        "content": "The question uses widely reported BTC/USD spot pricing near the end of 2023.",
        "resolution_criteria": "Resolves YES if a major BTC/USD spot index is above $40,000 at 2023-12-31 23:59 UTC.",
        "snapshot_time": "2023-10-01T00:00:00Z",
        "source": "public_historical_market_data",
        "tags": ["binary", "crypto", "bitcoin", "market-price"],
        "source_metadata": {
            "event_date": "2023-12-31",
            "source_url": "https://www.coindesk.com/price/bitcoin/",
            "verification_method": "End-of-day BTC/USD spot market data",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-12-31T23:59:00Z",
        "resolution_notes": "BTC/USD was above $40,000 at the end of 2023.",
    },
    {
        "id": "real-binary-2023-sp500-above-4500-eoy",
        "title": "Will the S&P 500 close above 4,500 on the final trading day of 2023?",
        "content": "The final 2023 S&P 500 regular-session close is observed after the December 29, 2023 session.",
        "resolution_criteria": "Resolves YES if the official S&P 500 close on December 29, 2023 is greater than 4,500.",
        "snapshot_time": "2023-10-01T00:00:00Z",
        "source": "public_historical_market_data",
        "tags": ["binary", "equities", "market-price", "us"],
        "source_metadata": {
            "event_date": "2023-12-29",
            "source_url": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/",
            "verification_method": "Official index close",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-12-29T21:00:00Z",
        "resolution_notes": "The S&P 500 closed above 4,500 on the final trading day of 2023.",
    },
    {
        "id": "real-binary-2023-nasdaq-above-15000-eoy",
        "title": "Will the Nasdaq Composite close above 15,000 on the final trading day of 2023?",
        "content": "The final 2023 Nasdaq Composite regular-session close is observed after December 29, 2023.",
        "resolution_criteria": "Resolves YES if the official Nasdaq Composite close on December 29, 2023 is greater than 15,000.",
        "snapshot_time": "2023-10-01T00:00:00Z",
        "source": "public_historical_market_data",
        "tags": ["binary", "equities", "market-price", "us", "technology"],
        "source_metadata": {
            "event_date": "2023-12-29",
            "source_url": "https://www.nasdaq.com/market-activity/index/comp/historical",
            "verification_method": "Official index close",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-12-29T21:00:00Z",
        "resolution_notes": "The Nasdaq Composite closed above 15,000 on the final trading day of 2023.",
    },
    {
        "id": "real-binary-2023-us10y-above-450bp-eoy",
        "title": "Will the U.S. 10-year Treasury yield be above 4.50% at the end of 2023?",
        "content": "The question uses the final 2023 daily Treasury par-yield observation.",
        "resolution_criteria": "Resolves YES if the final 2023 10-year Treasury yield observation is greater than 4.50%.",
        "snapshot_time": "2023-10-01T00:00:00Z",
        "source": "public_historical_market_data",
        "tags": ["binary", "rates", "treasury", "market-price", "us"],
        "source_metadata": {
            "event_date": "2023-12-29",
            "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
            "verification_method": "U.S. Treasury daily par yield curve rates",
        },
        "resolved_outcome": False,
        "resolution_time": "2023-12-29T21:00:00Z",
        "resolution_notes": "The 10-year Treasury yield ended 2023 below 4.50%.",
    },
    {
        "id": "real-binary-2023-brent-above-90-eoy",
        "title": "Will Brent crude oil settle above $90 on the final trading day of 2023?",
        "content": "The question observes the front-month Brent crude settlement on the final trading day of 2023.",
        "resolution_criteria": "Resolves YES if the relevant Brent futures settlement is greater than $90 on December 29, 2023.",
        "snapshot_time": "2023-10-01T00:00:00Z",
        "source": "public_historical_market_data",
        "tags": ["binary", "commodities", "oil", "market-price"],
        "source_metadata": {
            "event_date": "2023-12-29",
            "source_url": "https://www.ice.com/products/219/Brent-Crude-Futures/data",
            "verification_method": "Exchange settlement data",
        },
        "resolved_outcome": False,
        "resolution_time": "2023-12-29T21:00:00Z",
        "resolution_notes": "Brent crude settled below $90 on the final trading day of 2023.",
    },
    {
        "id": "real-binary-2023-us-dec-cpi-below-4",
        "title": "Will U.S. CPI inflation for December 2023 be below 4.0% year over year?",
        "content": "The Bureau of Labor Statistics releases December 2023 CPI data in January 2024.",
        "resolution_criteria": "Resolves YES if headline CPI-U year-over-year inflation for December 2023 is less than 4.0%.",
        "snapshot_time": "2023-12-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "inflation", "cpi", "us"],
        "source_metadata": {
            "event_date": "2024-01-11",
            "source_url": "https://www.bls.gov/cpi/news.htm",
            "verification_method": "BLS CPI news release",
        },
        "resolved_outcome": True,
        "resolution_time": "2024-01-11T13:30:00Z",
        "resolution_notes": "Headline CPI-U was below 4.0% year over year for December 2023.",
    },
    {
        "id": "real-binary-2023-us-dec-unemployment-at-or-below-4",
        "title": "Will the U.S. unemployment rate for December 2023 be at or below 4.0%?",
        "content": "The Bureau of Labor Statistics releases the December 2023 employment report in January 2024.",
        "resolution_criteria": "Resolves YES if the unemployment rate for December 2023 is less than or equal to 4.0%.",
        "snapshot_time": "2023-12-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "labor", "us"],
        "source_metadata": {
            "event_date": "2024-01-05",
            "source_url": "https://www.bls.gov/news.release/empsit.nr0.htm",
            "verification_method": "BLS Employment Situation release",
        },
        "resolved_outcome": True,
        "resolution_time": "2024-01-05T13:30:00Z",
        "resolution_notes": "The unemployment rate was at or below 4.0% for December 2023.",
    },
    {
        "id": "real-binary-2023-uk-dec-cpi-below-4",
        "title": "Will UK CPI inflation for December 2023 be below 4.0% year over year?",
        "content": "The UK Office for National Statistics releases December 2023 CPI data in January 2024.",
        "resolution_criteria": "Resolves YES if UK headline CPI inflation for December 2023 is strictly below 4.0%. ",
        "snapshot_time": "2023-12-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "inflation", "cpi", "uk"],
        "source_metadata": {
            "event_date": "2024-01-17",
            "source_url": "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/previousReleases",
            "verification_method": "ONS consumer price inflation release",
        },
        "resolved_outcome": False,
        "resolution_time": "2024-01-17T07:00:00Z",
        "resolution_notes": "UK CPI inflation was 4.0% year over year, not strictly below 4.0%.",
    },
    {
        "id": "real-binary-2023-canada-dec-cpi-below-4",
        "title": "Will Canada CPI inflation for December 2023 be below 4.0% year over year?",
        "content": "Statistics Canada releases December 2023 CPI data in January 2024.",
        "resolution_criteria": "Resolves YES if Canadian headline CPI inflation for December 2023 is less than 4.0%.",
        "snapshot_time": "2023-12-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "inflation", "cpi", "canada"],
        "source_metadata": {
            "event_date": "2024-01-16",
            "source_url": "https://www150.statcan.gc.ca/n1/en/type/data?text=Consumer%20Price%20Index",
            "verification_method": "Statistics Canada CPI release",
        },
        "resolved_outcome": True,
        "resolution_time": "2024-01-16T13:30:00Z",
        "resolution_notes": "Canadian CPI inflation was below 4.0% year over year for December 2023.",
    },
    {
        "id": "real-binary-2023-tesla-deliveries-at-least-1-8m",
        "title": "Will Tesla report at least 1.8 million vehicle deliveries for calendar year 2023?",
        "content": "Tesla reports fourth-quarter and full-year 2023 delivery totals after year end.",
        "resolution_criteria": "Resolves YES if Tesla's reported 2023 vehicle deliveries are greater than or equal to 1,800,000.",
        "snapshot_time": "2023-10-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "equities", "earnings", "automotive", "tesla"],
        "source_metadata": {
            "event_date": "2024-01-02",
            "source_url": "https://ir.tesla.com/press",
            "verification_method": "Tesla production and deliveries press release",
        },
        "resolved_outcome": True,
        "resolution_time": "2024-01-02T13:00:00Z",
        "resolution_notes": "Tesla reported more than 1.8 million vehicle deliveries for 2023.",
    },
    {
        "id": "real-binary-2023-us-government-shutdown-before-nov18",
        "title": "Will the U.S. federal government shut down before November 18, 2023?",
        "content": "A continuing-resolution deadline in November 2023 creates shutdown risk.",
        "resolution_criteria": "Resolves YES if a lapse in appropriations causes a federal shutdown before November 18, 2023.",
        "snapshot_time": "2023-10-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "politics", "fiscal", "us"],
        "source_metadata": {
            "event_date": "2023-11-18",
            "source_url": "https://www.congress.gov/",
            "verification_method": "Enacted continuing-resolution and agency operating status",
        },
        "resolved_outcome": False,
        "resolution_time": "2023-11-18T05:00:00Z",
        "resolution_notes": "Congress passed funding legislation and a shutdown did not occur before the deadline.",
    },
    {
        "id": "real-binary-2023-us-debt-ceiling-deal-before-jun6",
        "title": "Will a U.S. debt-ceiling suspension be enacted before June 6, 2023?",
        "content": "The Treasury projected a June 2023 debt-limit deadline unless Congress acted.",
        "resolution_criteria": "Resolves YES if legislation suspending or raising the debt limit is signed into law before June 6, 2023.",
        "snapshot_time": "2023-05-20T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "politics", "fiscal", "us"],
        "source_metadata": {
            "event_date": "2023-06-06",
            "source_url": "https://www.congress.gov/bill/118th-congress/house-bill/3746",
            "verification_method": "Congress.gov bill status and enactment date",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-06-03T23:30:00Z",
        "resolution_notes": "The Fiscal Responsibility Act was signed before June 6, 2023.",
    },
    {
        "id": "real-binary-2023-argentina-milei-runoff",
        "title": "Will Javier Milei win Argentina's 2023 presidential runoff?",
        "content": "Argentina's presidential runoff election is scheduled for November 19, 2023.",
        "resolution_criteria": "Resolves YES if Javier Milei is the officially declared winner of the runoff.",
        "snapshot_time": "2023-10-23T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "politics", "election", "argentina"],
        "source_metadata": {
            "event_date": "2023-11-19",
            "source_url": "https://www.electoral.gob.ar/",
            "verification_method": "Official election result reporting",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-11-20T03:00:00Z",
        "resolution_notes": "Javier Milei won the 2023 Argentine presidential runoff.",
    },
    {
        "id": "real-binary-2023-turkey-policy-rate-at-least-40",
        "title": "Will Turkey's central bank policy rate be at least 40% after the November 23, 2023 meeting?",
        "content": "The Central Bank of the Republic of Turkey is scheduled to decide rates on November 23, 2023.",
        "resolution_criteria": "Resolves YES if the announced one-week repo rate is greater than or equal to 40% after the meeting.",
        "snapshot_time": "2023-11-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "macro", "central-bank", "rates", "turkey"],
        "source_metadata": {
            "event_date": "2023-11-23",
            "source_url": "https://www.tcmb.gov.tr/wps/wcm/connect/en/tcmb+en/main+menu/announcements/press+releases/",
            "verification_method": "Central Bank of Turkey policy announcement",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-11-23T11:00:00Z",
        "resolution_notes": "The one-week repo rate was raised to 40%.",
    },
    {
        "id": "real-binary-2023-opec-voluntary-cuts-nov30",
        "title": "Will OPEC+ announce additional voluntary oil supply cuts on November 30, 2023?",
        "content": "OPEC+ producers are scheduled to meet on November 30, 2023.",
        "resolution_criteria": "Resolves YES if OPEC or participating countries announce additional voluntary supply cuts after the meeting.",
        "snapshot_time": "2023-11-15T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "commodities", "oil", "policy"],
        "source_metadata": {
            "event_date": "2023-11-30",
            "source_url": "https://www.opec.org/opec_web/en/press_room/archive.htm",
            "verification_method": "OPEC press releases and participating-country statements",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-11-30T18:00:00Z",
        "resolution_notes": "OPEC+ participants announced additional voluntary cuts for early 2024.",
    },
    {
        "id": "real-binary-2023-spacex-starship-ift2-before-dec1",
        "title": "Will SpaceX launch the second integrated Starship flight test before December 1, 2023?",
        "content": "SpaceX is preparing a second integrated flight test of Starship from Starbase, Texas.",
        "resolution_criteria": "Resolves YES if Starship IFT-2 lifts off before 2023-12-01 00:00 UTC.",
        "snapshot_time": "2023-09-01T00:00:00Z",
        "source": "public_historical_event",
        "tags": ["binary", "space", "aerospace", "technology"],
        "source_metadata": {
            "event_date": "2023-12-01",
            "source_url": "https://www.spacex.com/launches/",
            "verification_method": "SpaceX launch record",
        },
        "resolved_outcome": True,
        "resolution_time": "2023-11-18T13:03:00Z",
        "resolution_notes": "The second integrated Starship flight test lifted off on November 18, 2023.",
    },
)


class RealBinaryQuestionRecord(BaseModel):
    r"""Validated source record for the deterministic real binary corpus."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable corpus-local question identifier")
    title: str = Field(..., description="Binary market-style forecast question")
    content: str = Field(..., description="Question background available at snapshot time")
    resolution_criteria: str = Field(..., description="Rules used to determine the binary outcome")
    snapshot_time: datetime = Field(..., description="Zero-leakage history cutoff for this question")
    source: str = Field(..., description="Stable source category for the fixture record")
    tags: list[str] = Field(default_factory=list, description="Question tags and source taxonomy")
    source_metadata: dict[str, Any] = Field(default_factory=dict, description="Source URL and verification metadata")
    resolved_outcome: Optional[bool] = Field(None, description="Resolved YES/NO outcome when known")
    resolution_time: Optional[datetime] = Field(None, description="Timestamp when the outcome was resolved")
    resolution_notes: Optional[str] = Field(None, description="Human-readable resolution evidence summary")

    @model_validator(mode="after")
    def _validate_resolution_pairing(self) -> "RealBinaryQuestionRecord":
        if self.resolved_outcome is not None and self.resolution_time is None:
            raise ValueError("resolved records must include resolution_time")
        if self.resolution_time is not None and self.resolution_time < self.snapshot_time:
            raise ValueError("resolution_time must not precede snapshot_time")
        return self

    def to_forecast_question(self) -> ForecastQuestion:
        r"""Convert the corpus record to the canonical XRTM ForecastQuestion schema."""
        raw_data = self.model_dump(mode="json")
        return ForecastQuestion(
            id=self.id,
            title=self.title,
            description=self.content,
            resolution_criteria=self.resolution_criteria,
            metadata=MetadataBase(
                id=f"{self.id}:metadata",
                created_at=self.snapshot_time,
                snapshot_time=self.snapshot_time,
                tags=list(self.tags),
                subject_type="binary",
                source_version=REAL_BINARY_CORPUS_ID,
                raw_data=raw_data,
                source=self.source,
                source_metadata=dict(self.source_metadata),
                resolved_outcome=self.resolved_outcome,
                resolution_time=self.resolution_time,
                resolution_notes=self.resolution_notes,
            ),
        )


def validate_real_binary_corpus(
    raw_records: Optional[Sequence[Mapping[str, Any]]] = None,
) -> list[RealBinaryQuestionRecord]:
    r"""Validate raw corpus records and return typed, deterministic records."""
    source_records = _REAL_BINARY_QUESTION_CORPUS if raw_records is None else raw_records
    records = [RealBinaryQuestionRecord.model_validate(item) for item in source_records]
    ids = [record.id for record in records]
    duplicate_ids = sorted({record_id for record_id in ids if ids.count(record_id) > 1})
    if duplicate_ids:
        raise ValueError(f"duplicate real binary corpus ids: {duplicate_ids}")
    if len(records) < 20:
        raise ValueError("real binary corpus must contain at least 20 records")
    return records


def load_real_binary_corpus() -> list[RealBinaryQuestionRecord]:
    r"""Load the deterministic real binary corpus without network access."""
    return [record.model_copy(deep=True) for record in validate_real_binary_corpus()]


def load_real_binary_questions(limit: Optional[int] = None) -> list[ForecastQuestion]:
    r"""Load the real binary corpus as canonical ForecastQuestion objects."""
    questions = [record.to_forecast_question() for record in load_real_binary_corpus()]
    if limit is None:
        return questions
    return questions[:limit]


def load_real_binary_resolved_outcomes() -> dict[str, bool]:
    r"""Return known binary outcomes keyed by question id for evaluation fixtures."""
    return {
        record.id: record.resolved_outcome
        for record in load_real_binary_corpus()
        if record.resolved_outcome is not None
    }


class RealBinaryCorpusSource(DataSource):
    r"""Offline DataSource backed by the deterministic real binary corpus."""

    def __init__(self, records: Optional[Sequence[Mapping[str, Any]]] = None) -> None:
        self._records = validate_real_binary_corpus(records)
        self._questions = [record.to_forecast_question() for record in self._records]
        self._questions_by_id = {question.id: question for question in self._questions}

    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> list[ForecastQuestion]:
        r"""Fetch deterministic corpus questions, optionally filtering title/content text."""
        query_lower = query.lower() if query else None
        matches: list[ForecastQuestion] = []
        for question in self._questions:
            searchable = f"{question.title} {question.description or ''}".lower()
            if query_lower is None or query_lower in searchable:
                matches.append(question.model_copy(deep=True))
            if len(matches) >= limit:
                break
        return matches

    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        r"""Retrieve a deterministic corpus question by id."""
        question = self._questions_by_id.get(question_id)
        if question is None:
            return None
        return question.model_copy(deep=True)
