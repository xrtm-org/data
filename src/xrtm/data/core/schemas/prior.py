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
Prior state schemas for LLM training injection.

This module defines the Beta distribution parameters and prior state
representation used for injecting market belief state into LLM training.
Implements Decision 1 from the training architecture.

Example:
    >>> from xrtm.data.core.schemas import BetaPrior, PriorState
    >>> prior = BetaPrior(alpha=7.0, beta=3.0)
    >>> print(f"Mean: {prior.mean:.2f}, Concentration: {prior.concentration}")
    Mean: 0.70, Concentration: 10.0
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class BetaPrior(BaseModel):
    r"""
    Beta distribution parameters fitted from trade history.

    The Beta distribution is the conjugate prior for Bernoulli outcomes,
    making it ideal for representing belief state about binary events.
    Parameters α and β can be interpreted as "pseudo-counts" of Yes and No
    observations respectively.

    Attributes:
        alpha: Shape parameter α (Yes-weighted). Higher values indicate
            stronger belief in the positive outcome.
        beta: Shape parameter β (No-weighted). Higher values indicate
            stronger belief in the negative outcome.

    Example:
        >>> prior = BetaPrior(alpha=7.0, beta=3.0)
        >>> prior.mean
        0.7
        >>> prior.concentration
        10.0
        >>> prior.variance
        0.019090909090909092
    """

    alpha: float = Field(
        ...,
        gt=0,
        description="Shape parameter α (Yes-weighted pseudo-count)",
    )
    beta: float = Field(
        ...,
        gt=0,
        description="Shape parameter β (No-weighted pseudo-count)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mean(self) -> float:
        r"""Expected value of the Beta distribution: α / (α + β)."""
        return self.alpha / (self.alpha + self.beta)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def concentration(self) -> float:
        r"""
        Total concentration α + β.

        Higher concentration indicates more confident prior (less uncertainty).
        A concentration of 2 represents maximum uncertainty (uniform prior).
        """
        return self.alpha + self.beta

    @property
    def variance(self) -> float:
        r"""Variance of the Beta distribution: αβ / ((α+β)²(α+β+1))."""
        total = self.alpha + self.beta
        return (self.alpha * self.beta) / (total * total * (total + 1))

    @classmethod
    def uniform(cls) -> "BetaPrior":
        r"""Create a uniform (uninformative) prior with α=β=1."""
        return cls(alpha=1.0, beta=1.0)

    @classmethod
    def from_mean_concentration(cls, mean: float, concentration: float) -> "BetaPrior":
        r"""
        Create a BetaPrior from mean and concentration.

        Args:
            mean: Target mean value in (0, 1).
            concentration: Target α + β, must be > 0.

        Returns:
            BetaPrior with specified mean and concentration.

        Example:
            >>> prior = BetaPrior.from_mean_concentration(0.7, 10.0)
            >>> prior.alpha, prior.beta
            (7.0, 3.0)
        """
        alpha = mean * concentration
        beta = (1 - mean) * concentration
        return cls(alpha=alpha, beta=beta)

    def credible_interval(self, level: float = 0.9) -> tuple[float, float]:
        r"""
        Compute the credible interval (Bayesian confidence interval).

        Uses scipy.stats.beta to compute the equal-tailed credible interval.

        Args:
            level: Confidence level (default 0.9 for 90% interval).

        Returns:
            Tuple of (low, high) bounds.

        Example:
            >>> prior = BetaPrior(alpha=7.0, beta=3.0)
            >>> low, high = prior.credible_interval(0.9)
            >>> print(f"90% CI: [{low:.3f}, {high:.3f}]")
            90% CI: [0.435, 0.895]
        """
        from scipy.stats import beta as beta_dist

        dist = beta_dist(self.alpha, self.beta)
        tail = (1 - level) / 2
        return (float(dist.ppf(tail)), float(dist.ppf(1 - tail)))

    def sample(self, n: int = 1) -> list[float]:
        r"""
        Draw random samples from the Beta distribution.

        Args:
            n: Number of samples to draw.

        Returns:
            List of n samples from Beta(α, β).

        Example:
            >>> prior = BetaPrior(alpha=7.0, beta=3.0)
            >>> samples = prior.sample(1000)
            >>> abs(sum(samples)/len(samples) - prior.mean) < 0.05
            True
        """
        from scipy.stats import beta as beta_dist

        dist = beta_dist(self.alpha, self.beta)
        return [float(x) for x in dist.rvs(size=n)]

    def to_distribution_dict(self) -> dict:
        r"""
        Convert to governance schema v1.1 distribution format.

        Returns:
            Dictionary matching the forecast_object_v1.1 distribution schema.

        Example:
            >>> prior = BetaPrior(alpha=7.0, beta=3.0)
            >>> d = prior.to_distribution_dict()
            >>> d["family"]
            'beta'
        """
        low, high = self.credible_interval(0.9)
        return {
            "family": "beta",
            "alpha": self.alpha,
            "beta": self.beta,
            "credible_interval": {
                "low": low,
                "high": high,
                "level": 0.9,
            },
        }


class PriorState(BaseModel):
    r"""
    Full prior state for training injection (Decision 1).

    This domain-agnostic schema captures the complete belief state at a
    point in time, including temporal context for the model to reason
    about information staleness and deadline proximity.

    Attributes:
        prior: The Beta distribution parameters representing current belief.
        silence_delta: Normalized time since last information update.
            0 = just updated, 1 = long silence (model should consider decay).
        deadline_delta: Normalized time remaining until resolution.
            0 = at resolution, 1 = maximum time remaining.
        snapshot_time: UTC timestamp when this state was captured.
        metadata: Optional additional context.

    Example:
        >>> from datetime import datetime, timezone
        >>> state = PriorState(
        ...     prior=BetaPrior(alpha=7.0, beta=3.0),
        ...     silence_delta=0.1,
        ...     deadline_delta=0.5,
        ...     snapshot_time=datetime.now(timezone.utc),
        ... )
    """

    prior: BetaPrior = Field(
        ...,
        description="Beta distribution parameters representing current belief",
    )
    silence_delta: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Normalized time since last information update [0=just updated, 1=long silence]",
    )
    deadline_delta: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Normalized time remaining until resolution [0=at resolution, 1=max time]",
    )
    snapshot_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this state was captured",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Optional additional context",
    )

    @classmethod
    def uninformative(cls) -> "PriorState":
        r"""Create an uninformative prior state with uniform Beta(1,1)."""
        return cls(
            prior=BetaPrior.uniform(),
            silence_delta=0.0,
            deadline_delta=1.0,
        )


__all__ = ["BetaPrior", "PriorState"]
