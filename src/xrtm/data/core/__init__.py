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
Core interfaces and protocols for xrtm-data.

This module defines the abstract base classes (protocols) that all data
providers must implement. The core module is domain-agnostic and MUST NOT
import from kit/ or providers/.
"""

from xrtm.data.core.interfaces import DataSource

__all__ = ["DataSource"]
