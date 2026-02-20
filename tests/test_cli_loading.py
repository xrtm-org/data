
import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path
from xrtm.data.cli import _load_trades
from xrtm.data.core.schemas import TradeEvent

def test_load_trades_parquet(tmp_path):
    # Create dummy data
    data = {
        "price": [0.5, 0.6],
        "amount": [100.0, 200.0],
        "timestamp": [
            datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat(),
            datetime(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc).isoformat(),
        ],
        "maker": ["0xMaker1", "0xMaker2"],
        "taker": ["0xTaker1", "0xTaker2"],
    }
    df = pd.DataFrame(data)
    table = pa.Table.from_pandas(df)

    file_path = tmp_path / "trades.parquet"
    pq.write_table(table, file_path)

    # Load data
    trades = _load_trades(file_path)

    # Verify
    assert len(trades) == 2
    assert isinstance(trades[0], TradeEvent)
    assert trades[0].price == 0.5
    assert trades[0].amount == 100.0
    assert trades[0].timestamp == datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert trades[0].maker == "0xMaker1"
    assert trades[0].taker == "0xTaker1"

    assert trades[1].price == 0.6
    assert trades[1].amount == 200.0
    assert trades[1].timestamp == datetime(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    assert trades[1].maker == "0xMaker2"
    assert trades[1].taker == "0xTaker2"

def test_load_trades_json(tmp_path):
    import json
    # Create dummy data
    data = {
        "trades": [
            {
                "price": 0.5,
                "amount": 100.0,
                "timestamp": datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat(),
                "maker": "0xMaker1",
                "taker": "0xTaker1",
            }
        ]
    }

    file_path = tmp_path / "trades.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    # Load data
    trades = _load_trades(file_path)

    # Verify
    assert len(trades) == 1
    assert isinstance(trades[0], TradeEvent)
    assert trades[0].price == 0.5
