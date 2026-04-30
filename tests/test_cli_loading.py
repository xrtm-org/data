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

from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from xrtm.data.cli import _load_trades


def test_load_trades_from_parquet_with_itertuples(tmp_path):
    path = tmp_path / "trades.parquet"
    table = pa.table(
        {
            "price": [0.7],
            "amount": [42.0],
            "timestamp": [datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()],
            "maker": ["maker"],
            "taker": ["taker"],
        }
    )
    pq.write_table(table, path)

    trades = _load_trades(path)

    assert len(trades) == 1
    assert trades[0].price == 0.7
    assert trades[0].amount == 42.0
    assert trades[0].maker == "maker"
