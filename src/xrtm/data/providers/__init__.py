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

r"""
Data providers for xrtm-data.

This module exports concrete DataSource implementations that fetch data
from various external sources. Providers implement the core interfaces
and CAN import from core/ but MUST NOT import from kit/.
"""

from xrtm.data.providers.local import LocalDataSource
from xrtm.data.providers.online import PolymarketSource
from xrtm.data.providers.subgraph import PolymarketTradeSource

__all__ = ["LocalDataSource", "PolymarketSource", "PolymarketTradeSource"]
