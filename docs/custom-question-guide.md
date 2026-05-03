# Custom Question Guide

This guide shows you how to create and manage your own forecasting questions in XRTM using the existing infrastructure.

## Why Custom Questions?

The bundled `xrtm-real-binary-v1` corpus has only ~5-10 binary questions. It's a minimal seed corpus for CI smoke tests, not a comprehensive benchmark. **You'll need custom questions for:**
- Domain-specific forecasting (e.g., company-specific events)
- Local testing and experimentation
- Ablation studies or research
- Training/fine-tuning on your own data

For large-scale benchmarks, see [Benchmark Corpus Policy](./benchmark-corpus-policy.md).

---

## Quick Start: In-Memory Questions

The fastest way to test custom questions is to create them directly in Python without registering a corpus.

### Example: Single Question

```python
from datetime import datetime
from xrtm.data.core.schemas import ForecastQuestion, MetadataBase

# Create a minimal question
question = ForecastQuestion(
    id="my-q1",
    title="Will my project launch by end of Q1 2025?",
)

# With full metadata
question = ForecastQuestion(
    id="my-q1",
    title="Will my project launch by end of Q1 2025?",
    description="The project is considered 'launched' if the public website is live and accepts signups.",
    resolution_criteria="Resolves YES if the signup page is publicly accessible by 2025-03-31 23:59 UTC.",
    metadata=MetadataBase(
        snapshot_time=datetime(2025, 1, 15, 0, 0, 0),
        tags=["internal", "binary", "deadline"],
    ),
)
```

**Field requirements:**
- `id`: Unique string identifier (required)
- `title`: Main question text (required)
- `description`: Additional context (optional, aliased as `content`)
- `resolution_criteria`: How to determine ground truth (optional but recommended)
- `metadata`: Temporal and classification metadata (optional)

### Example: Question List

```python
from xrtm.data.core.schemas import ForecastQuestion

questions = [
    ForecastQuestion(
        id="team-q1",
        title="Will Team A ship Feature X by Feb 15?",
        description="Feature X is considered shipped if merged to main and deployed to staging.",
    ),
    ForecastQuestion(
        id="team-q2",
        title="Will quarterly revenue exceed $1M?",
        description="Based on Q1 2025 revenue from all sources.",
    ),
]
```

You can now pass this list directly to the validation harness or forecast pipeline.

---

## Method 1: Create a Custom DataSource

For reusable question sets, implement the `DataSource` interface. This gives you the same API as the bundled corpus.

### Minimal Implementation

```python
from datetime import datetime
from typing import List, Optional
from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion

class MyCustomSource(DataSource):
    """A simple in-memory data source."""
    
    def __init__(self):
        self.questions = [
            ForecastQuestion(
                id="custom-1",
                title="Will Product Launch succeed?",
                description="Launch is considered successful if DAU > 1000 by day 7.",
            ),
            ForecastQuestion(
                id="custom-2",
                title="Will the marketing campaign ROI exceed 2.0?",
                description="ROI = (Revenue - Cost) / Cost, measured over 30 days.",
            ),
        ]
    
    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[ForecastQuestion]:
        """Return all questions up to the limit."""
        return self.questions[:limit]
    
    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        """Find a question by ID."""
        for q in self.questions:
            if q.id == question_id:
                return q
        return None
```

### Using Your DataSource

```python
# In your script or notebook
source = MyCustomSource()

# Fetch questions
questions = await source.fetch_questions(limit=10)
for q in questions:
    print(f"{q.id}: {q.title}")

# Get specific question
q = await source.get_question_by_id("custom-1")
```

---

## Method 2: Load Questions from JSON

If you store questions in a file, load them into a DataSource.

### Example JSON Format

Create `my-questions.json`:

```json
[
  {
    "id": "q1",
    "title": "Will the product launch by March 2025?",
    "description": "Launch is defined as the public website going live.",
    "resolution_criteria": "Resolves YES if website is publicly accessible by 2025-03-31 23:59 UTC.",
    "metadata": {
      "snapshot_time": "2025-01-15T00:00:00Z",
      "tags": ["binary", "deadline", "internal"]
    }
  },
  {
    "id": "q2",
    "title": "Will Q1 revenue exceed $500k?",
    "description": "Based on total recognized revenue for January-March 2025.",
    "resolution_criteria": "Resolves YES if Q1 revenue > $500,000 per GAAP accounting.",
    "metadata": {
      "snapshot_time": "2025-01-15T00:00:00Z",
      "tags": ["binary", "revenue", "quarterly"]
    }
  }
]
```

### Load and Use

```python
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion

class JSONFileSource(DataSource):
    """Load questions from a JSON file."""
    
    def __init__(self, json_path: Path):
        self.questions = []
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                self.questions.append(ForecastQuestion(**item))
    
    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[ForecastQuestion]:
        return self.questions[:limit]
    
    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

# Usage
source = JSONFileSource(Path("my-questions.json"))
questions = await source.fetch_questions(limit=10)
```

---

## Method 3: Register a Custom Corpus

For integration with the XRTM CLI and validation harness, register your DataSource with the corpus registry.

### Registration Example

```python
from pathlib import Path
from xrtm.data.corpora import (
    CorpusRegistry,
    CorpusMetadata,
    CorpusManifest,
    CorpusTier,
    LicenseType,
    CorpusSplit,
)
from xrtm.data.core import DataSource

# Define your DataSource (see Method 1 or 2 above)
class MyCustomSource(DataSource):
    # ... implementation from above ...
    pass

# Create metadata
metadata = CorpusMetadata(
    corpus_id="my-internal-corpus",
    name="Internal Product Forecasts",
    tier=CorpusTier.TIER_3,  # Tier 3 = supplemental/internal use
    license_type=LicenseType.PROPRIETARY,  # or APACHE_2_0, MIT, etc.
    description="Custom questions for internal product forecasting",
    version="1.0",
    release_gate_approved=False,  # Not for release gates
    bundled=False,  # Not shipped with XRTM
    size_estimate=50,  # Approximate number of questions
    tags=["internal", "custom"],
)

# Create manifest
manifest = CorpusManifest(
    corpus_id="my-internal-corpus",
    metadata=metadata,
    loader_fn=lambda: MyCustomSource(),
    available_splits=[CorpusSplit.FULL],
)

# Register globally
registry = CorpusRegistry.get_instance()
registry.register(manifest)
```

### Using Registered Corpus

```python
from xrtm.data.corpora import get_corpus, list_available_corpora

# List all corpora
all_corpora = list_available_corpora()
for c in all_corpora:
    print(f"{c.corpus_id}: {c.name} (Tier {c.tier})")

# Load your custom corpus
source = get_corpus("my-internal-corpus")
questions = await source.fetch_questions(limit=10)
```

### CLI Integration

After registering, you can use your corpus with XRTM CLI commands:

```bash
# List available corpora
xrtm validate list-corpora

# Run validation with your corpus
xrtm validate run \
  --corpus-id my-internal-corpus \
  --provider mock \
  --limit 20

# Create a profile
xrtm profile create my-profile \
  --corpus-id my-internal-corpus \
  --provider mock \
  --limit 10

xrtm run profile my-profile
```

---

## Method 4: Load from CSV/Database

You can adapt the DataSource pattern to load questions from any source.

### CSV Example

Create `questions.csv`:

```csv
id,title,description,resolution_criteria
q1,"Will launch succeed?","Launch = website live","YES if website up by 2025-03-31 23:59 UTC"
q2,"Revenue > $500k?","Q1 2025 revenue","YES if revenue exceeds $500k"
```

Load it:

```python
import csv
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion

class CSVSource(DataSource):
    """Load questions from a CSV file."""
    
    def __init__(self, csv_path: Path):
        self.questions = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.questions.append(
                    ForecastQuestion(
                        id=row["id"],
                        title=row["title"],
                        description=row.get("description"),
                        resolution_criteria=row.get("resolution_criteria"),
                    )
                )
    
    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[ForecastQuestion]:
        return self.questions[:limit]
    
    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

# Usage
source = CSVSource(Path("questions.csv"))
questions = await source.fetch_questions(limit=10)
```

### Database Example

```python
import asyncpg
from typing import List, Optional
from datetime import datetime
from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion

class PostgresSource(DataSource):
    """Load questions from PostgreSQL."""
    
    def __init__(self, connection_string: str):
        self.conn_string = connection_string
    
    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[ForecastQuestion]:
        conn = await asyncpg.connect(self.conn_string)
        try:
            rows = await conn.fetch(
                "SELECT id, title, description, resolution_criteria FROM questions LIMIT $1",
                limit,
            )
            return [
                ForecastQuestion(
                    id=row["id"],
                    title=row["title"],
                    description=row.get("description"),
                    resolution_criteria=row.get("resolution_criteria"),
                )
                for row in rows
            ]
        finally:
            await conn.close()
    
    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        conn = await asyncpg.connect(self.conn_string)
        try:
            row = await conn.fetchrow(
                "SELECT id, title, description, resolution_criteria FROM questions WHERE id = $1",
                question_id,
            )
            if row is None:
                return None
            return ForecastQuestion(
                id=row["id"],
                title=row["title"],
                description=row.get("description"),
                resolution_criteria=row.get("resolution_criteria"),
            )
        finally:
            await conn.close()
```

---

## Question Format Reference

### Required Fields

- **`id`**: Unique string identifier. Use kebab-case or underscores (e.g., `"my-q1"`, `"product_launch_2025"`)
- **`title`**: The main question. Should be clear and unambiguous.

### Optional Fields

- **`description`** (or `content`): Additional context, background, definitions. Both field names work due to aliasing.
- **`resolution_criteria`**: Explicit, non-ambiguous rules for determining ground truth. **Highly recommended** for reproducibility.
- **`metadata`**: Contains:
  - `snapshot_time`: The "Time T" at which the world state is frozen (zero-leakage principle)
  - `tags`: List of classification tags (e.g., `["binary", "internal", "deadline"]`)
  - `created_at`: When the question was created
  - Other fields (see [Forecast Object Standard](./concepts/forecast_object.md))

### Example: Full Question

```python
from datetime import datetime, timezone
from xrtm.data.core.schemas import ForecastQuestion, MetadataBase

question = ForecastQuestion(
    id="detailed-q1",
    title="Will the new feature achieve >10% adoption within 30 days of launch?",
    description="""
    Adoption is measured as the percentage of active users who use the feature at least once.
    Active users are defined as users who logged in during the 30-day window.
    The 30-day window starts the moment the feature is publicly available in production.
    """,
    resolution_criteria="""
    Resolves YES if (users_who_used_feature / active_users) > 0.10 within 30 days.
    Data source: internal analytics dashboard.
    """,
    metadata=MetadataBase(
        snapshot_time=datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
        tags=["binary", "product", "adoption", "internal"],
        source_version="1.0",
    ),
)
```

---

## Current Limitations

### What XRTM Does NOT Provide

1. **No built-in question editor UI**: You must create questions in Python, JSON, CSV, or a database.
2. **No automatic resolution**: You must track ground truth yourself and update question status manually.
3. **No collaborative question management**: The corpus infrastructure is single-user, file-based. For team collaboration, use version control (Git) or a shared database.
4. **No question marketplace**: Unlike Metaculus or Polymarket, XRTM does not host community-authored questions.

### Workarounds

- **Question authoring**: Use Python scripts, Jupyter notebooks, or simple JSON files.
- **Version control**: Store JSON/CSV files in Git for versioning and collaboration.
- **Resolution tracking**: Add a `resolved_outcome` field to your JSON and update it manually after events occur.
- **Team workflows**: Use a shared Postgres database and implement a web UI separately if needed.

---

## Best Practices

### 1. Use Explicit Resolution Criteria

```python
# ❌ BAD: Ambiguous
ForecastQuestion(
    id="q1",
    title="Will the project succeed?",
)

# ✅ GOOD: Clear criteria
ForecastQuestion(
    id="q1",
    title="Will the project succeed?",
    resolution_criteria="Resolves YES if the website is live and accepts signups by 2025-03-31 23:59 UTC.",
)
```

### 2. Use Unique, Stable IDs

```python
# ❌ BAD: Non-unique or sequential
ForecastQuestion(id="1", title="...")  # Conflicts if you merge question sets

# ✅ GOOD: Namespaced, unique IDs
ForecastQuestion(id="product-launch-q1-2025", title="...")
ForecastQuestion(id="team-alpha-metric-1", title="...")
```

### 3. Include Snapshot Time

```python
from datetime import datetime, timezone
from xrtm.data.core.schemas import MetadataBase

# ✅ GOOD: Explicit snapshot time
question = ForecastQuestion(
    id="q1",
    title="Will revenue exceed $1M?",
    metadata=MetadataBase(
        snapshot_time=datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
    ),
)
```

This ensures zero temporal leakage: the model cannot access information after this timestamp.

### 4. Tag Questions for Filtering

```python
# ✅ GOOD: Use tags
question = ForecastQuestion(
    id="q1",
    title="Will the product launch succeed?",
    metadata=MetadataBase(
        tags=["binary", "product", "launch", "q1-2025", "internal"],
    ),
)
```

Tags help with filtering, organization, and retrospective analysis.

### 5. Version Your Question Sets

Store questions in files and use Git:

```bash
# questions/v1/product-forecasts.json
git add questions/v1/product-forecasts.json
git commit -m "Add Q1 2025 product forecast questions"
git tag questions-v1.0
```

This gives you reproducibility and auditability.

---

## Testing Your Custom Questions

### Quick Test with Mock Provider

```python
# test_custom_questions.py
import asyncio
from xrtm.data.core.schemas import ForecastQuestion

async def test_custom_questions():
    questions = [
        ForecastQuestion(id="q1", title="Will A happen?"),
        ForecastQuestion(id="q2", title="Will B happen?"),
    ]
    
    # Verify question structure
    for q in questions:
        assert q.id
        assert q.title
        print(f"✓ {q.id}: {q.title}")

if __name__ == "__main__":
    asyncio.run(test_custom_questions())
```

### Integration with Validation Harness

```python
from xrtm.data.corpora import CorpusRegistry, CorpusMetadata, CorpusManifest, CorpusTier, LicenseType, CorpusSplit
from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion

class MyTestSource(DataSource):
    def __init__(self):
        self.questions = [
            ForecastQuestion(id="test-1", title="Test question 1"),
            ForecastQuestion(id="test-2", title="Test question 2"),
        ]
    
    async def fetch_questions(self, query=None, limit=5, *, snapshot_time=None):
        return self.questions[:limit]
    
    async def get_question_by_id(self, question_id, *, snapshot_time=None):
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

# Register
metadata = CorpusMetadata(
    corpus_id="test-corpus",
    name="Test Corpus",
    tier=CorpusTier.TIER_3,
    license_type=LicenseType.APACHE_2_0,
    description="Test questions",
    version="1.0",
    release_gate_approved=False,
    bundled=False,
    size_estimate=2,
    tags=["test"],
)
manifest = CorpusManifest(
    corpus_id="test-corpus",
    metadata=metadata,
    loader_fn=lambda: MyTestSource(),
    available_splits=[CorpusSplit.FULL],
)
CorpusRegistry.get_instance().register(manifest)

# Now use with CLI
# xrtm validate run --corpus-id test-corpus --provider mock --limit 2
```

---

## Complete Working Example

Here's a full end-to-end example:

```python
# custom_questions_demo.py
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion, MetadataBase
from xrtm.data.corpora import (
    CorpusRegistry,
    CorpusMetadata,
    CorpusManifest,
    CorpusTier,
    LicenseType,
    CorpusSplit,
)

class MyCompanySource(DataSource):
    """Custom corpus for company-specific forecasts."""
    
    def __init__(self):
        self.questions = [
            ForecastQuestion(
                id="company-product-launch-q1",
                title="Will Product X launch by end of Q1 2025?",
                description="Launch is defined as public availability on the main website.",
                resolution_criteria="Resolves YES if the product page is live and accepts orders by 2025-03-31 23:59 UTC.",
                metadata=MetadataBase(
                    snapshot_time=datetime(2025, 1, 15, tzinfo=timezone.utc),
                    tags=["binary", "product", "launch", "q1-2025"],
                ),
            ),
            ForecastQuestion(
                id="company-revenue-q1",
                title="Will Q1 2025 revenue exceed $500k?",
                description="Based on total recognized revenue for January-March 2025.",
                resolution_criteria="Resolves YES if Q1 revenue > $500,000 per GAAP accounting.",
                metadata=MetadataBase(
                    snapshot_time=datetime(2025, 1, 15, tzinfo=timezone.utc),
                    tags=["binary", "revenue", "quarterly"],
                ),
            ),
            ForecastQuestion(
                id="company-feature-adoption",
                title="Will Feature Y achieve >15% adoption in 30 days?",
                description="Adoption = (users who used feature / active users) measured over 30 days post-launch.",
                resolution_criteria="Resolves YES if adoption rate exceeds 15% within 30 days of feature launch.",
                metadata=MetadataBase(
                    snapshot_time=datetime(2025, 1, 15, tzinfo=timezone.utc),
                    tags=["binary", "adoption", "feature"],
                ),
            ),
        ]
    
    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[ForecastQuestion]:
        return self.questions[:limit]
    
    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

def register_custom_corpus():
    """Register the custom corpus with XRTM."""
    metadata = CorpusMetadata(
        corpus_id="my-company-corpus",
        name="My Company Internal Forecasts",
        tier=CorpusTier.TIER_3,
        license_type=LicenseType.PROPRIETARY,
        description="Internal forecasting questions for company metrics",
        version="1.0",
        release_gate_approved=False,
        bundled=False,
        size_estimate=3,
        tags=["internal", "company", "custom"],
    )
    
    manifest = CorpusManifest(
        corpus_id="my-company-corpus",
        metadata=metadata,
        loader_fn=lambda: MyCompanySource(),
        available_splits=[CorpusSplit.FULL],
    )
    
    CorpusRegistry.get_instance().register(manifest)
    print("✓ Registered custom corpus: my-company-corpus")

async def main():
    # Register the corpus
    register_custom_corpus()
    
    # Use it directly
    source = MyCompanySource()
    questions = await source.fetch_questions(limit=10)
    
    print(f"\nLoaded {len(questions)} custom questions:")
    for q in questions:
        print(f"  - {q.id}: {q.title}")
    
    # Fetch specific question
    q = await source.get_question_by_id("company-revenue-q1")
    if q:
        print(f"\nDetailed question:")
        print(f"  ID: {q.id}")
        print(f"  Title: {q.title}")
        print(f"  Description: {q.description}")
        print(f"  Resolution Criteria: {q.resolution_criteria}")
        print(f"  Tags: {q.metadata.tags}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**

```bash
python custom_questions_demo.py
```

**Expected output:**

```
✓ Registered custom corpus: my-company-corpus

Loaded 3 custom questions:
  - company-product-launch-q1: Will Product X launch by end of Q1 2025?
  - company-revenue-q1: Will Q1 2025 revenue exceed $500k?
  - company-feature-adoption: Will Feature Y achieve >15% adoption in 30 days?

Detailed question:
  ID: company-revenue-q1
  Title: Will Q1 2025 revenue exceed $500k?
  Description: Based on total recognized revenue for January-March 2025.
  Resolution Criteria: Resolves YES if Q1 revenue > $500,000 per GAAP accounting.
  Tags: ['binary', 'revenue', 'quarterly']
```

---

## Related Documentation

- [Corpus Infrastructure Guide](./corpus-infrastructure-guide.md) - Advanced corpus management, splits, and importers
- [Benchmark Corpus Policy](./benchmark-corpus-policy.md) - Tier classification and licensing
- [Forecast Object Standard](./concepts/forecast_object.md) - Question and forecast schema details
- [Getting Started](../../xrtm/docs/getting-started.md) - XRTM CLI quick start
- [Operator Runbook](../../xrtm/docs/operator-runbook.md) - Validation harness and CLI usage
- `data/src/xrtm/data/core/interfaces.py` - DataSource interface definition
- `data/src/xrtm/data/core/schemas/forecast.py` - ForecastQuestion schema
- `data/src/xrtm/data/corpora/real_binary.py` - Example bundled corpus implementation
- `governance/schemas/forecast_object_v1.1.json` - JSON Schema for forecast objects

---

**Last Updated**: 2025-01-01  
**Version**: 1.0
