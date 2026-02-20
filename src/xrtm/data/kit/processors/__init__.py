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
Beta distribution fitting from trade history.

This module implements volume-weighted Beta distribution fitting (Decision 1)
for converting market trade data into belief state representations.

The core insight is that each trade at price p with amount a can be decomposed:
- α contribution: p × a (weight toward Yes)
- β contribution: (1-p) × a (weight toward No)

Example:
    >>> from xrtm.data.kit.processors import fit_beta_from_trades
    >>> from xrtm.data.core.schemas import TradeEvent, BetaPrior
    >>> trades = [
    ...     TradeEvent(price=0.7, amount=100, ...),
    ...     TradeEvent(price=0.8, amount=50, ...),
    ... ]
    >>> prior = fit_beta_from_trades(trades)
    >>> print(f"Fitted: α={prior.alpha:.2f}, β={prior.beta:.2f}")
"""

from typing import Optional

from xrtm.data.core.schemas.prior import BetaPrior
from xrtm.data.core.schemas.trade import TradeEvent, TradeWindow


def fit_beta_from_trades(
    trades: list[TradeEvent],
    scale: float = 100.0,
    min_concentration: float = 2.0,
) -> BetaPrior:
    r"""
    Fit Beta(α, β) from volume-weighted trade history.

    Decision 1 Implementation: Each trade contributes to α and β proportionally
    to its price and amount. The resulting distribution represents the
    aggregate market belief.

    The fitting formula:
        α = Σ(price_i × amount_i) / normalization
        β = Σ((1 - price_i) × amount_i) / normalization

    Args:
        trades: List of trade events to fit.
        scale: Normalization factor for concentration. Higher values yield
            lower concentration (more uncertainty). Defaults to 100.0.
        min_concentration: Minimum α + β to avoid degenerate distributions.
            Defaults to 2.0 (uniform prior).

    Returns:
        BetaPrior with fitted α and β parameters.

    Example:
        >>> trades = [
        ...     TradeEvent(price=0.7, amount=100, ...),
        ...     TradeEvent(price=0.8, amount=50, ...),
        ... ]
        >>> prior = fit_beta_from_trades(trades)
        >>> # total_yes = 0.7*100 + 0.8*50 = 110
        >>> # total_no = 0.3*100 + 0.2*50 = 40
        >>> # With scale=100: α = 110/normalization, β = 40/normalization
    """
    if not trades:
        return BetaPrior.uniform()

    total_yes = 0.0
    total_no = 0.0

    for t in trades:
        total_yes += t.yes_weight
        total_no += t.no_weight

    total_volume = total_yes + total_no

    if total_volume == 0:
        return BetaPrior.uniform()

    # Normalize to target scale
    norm = total_volume / scale
    alpha = total_yes / norm
    beta = total_no / norm

    # Ensure minimum concentration
    concentration = alpha + beta
    if concentration < min_concentration:
        # Scale up to minimum while preserving mean
        scale_factor = min_concentration / concentration
        alpha *= scale_factor
        beta *= scale_factor

    # Ensure minimum values to avoid numerical issues
    return BetaPrior(
        alpha=max(0.1, alpha),
        beta=max(0.1, beta),
    )


def fit_beta_from_window(
    window: TradeWindow,
    scale: float = 100.0,
    min_concentration: float = 2.0,
) -> BetaPrior:
    r"""
    Fit Beta distribution from a TradeWindow.

    Convenience wrapper around fit_beta_from_trades for TradeWindow objects.

    Args:
        window: TradeWindow containing trades to fit.
        scale: Normalization factor for concentration.
        min_concentration: Minimum α + β to ensure valid distribution.

    Returns:
        BetaPrior with fitted α and β parameters.
    """
    return fit_beta_from_trades(window.trades, scale, min_concentration)


def fit_beta_exponential_decay(
    trades: list[TradeEvent],
    reference_time: Optional[float] = None,
    half_life_hours: float = 24.0,
    scale: float = 100.0,
    min_concentration: float = 2.0,
) -> BetaPrior:
    r"""
    Fit Beta distribution with exponential time decay.

    More recent trades are weighted more heavily than older trades,
    with weights decaying exponentially based on time distance.

    Args:
        trades: List of trade events to fit.
        reference_time: Unix timestamp for decay reference. Defaults to
            the most recent trade timestamp.
        half_life_hours: Time (in hours) for weight to decay by half.
        scale: Normalization factor for concentration.
        min_concentration: Minimum α + β to ensure valid distribution.

    Returns:
        BetaPrior with time-decay-weighted α and β parameters.

    Example:
        >>> # Recent trades weighted more than old trades
        >>> prior = fit_beta_exponential_decay(
        ...     trades, half_life_hours=12.0
        ... )
    """
    import math

    if not trades:
        return BetaPrior.uniform()

    # Use most recent trade as reference if not provided
    if reference_time is None:
        reference_time = max(t.timestamp.timestamp() for t in trades)

    half_life_seconds = half_life_hours * 3600
    decay_rate = math.log(2) / half_life_seconds

    total_yes = 0.0
    total_no = 0.0

    for trade in trades:
        age_seconds = reference_time - trade.timestamp.timestamp()
        weight = math.exp(-decay_rate * max(0, age_seconds))

        total_yes += trade.yes_weight * weight
        total_no += trade.no_weight * weight

    total_volume = total_yes + total_no
    if total_volume == 0:
        return BetaPrior.uniform()

    norm = total_volume / scale
    alpha = total_yes / norm
    beta = total_no / norm

    concentration = alpha + beta
    if concentration < min_concentration:
        scale_factor = min_concentration / concentration
        alpha *= scale_factor
        beta *= scale_factor

    return BetaPrior(
        alpha=max(0.1, alpha),
        beta=max(0.1, beta),
    )


__all__ = [
    "fit_beta_from_trades",
    "fit_beta_from_window",
    "fit_beta_exponential_decay",
]
