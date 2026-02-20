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
CLI entry point for xrtm-data.

Provides commands for:
- Collecting trade data from Polymarket
- Fitting Beta priors from trade history
- Caching data to Parquet files

Example:
    $ xrtm-data collect --market-id 0x... --days 30 -o trades.parquet
    $ xrtm-data fit-prior --input trades.parquet -o prior.json
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from xrtm.data.version import __version__

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    r"""xrtm-data: Data collection and preprocessing for xRTM training."""
    pass


@main.command()
@click.option("--market-id", "-m", required=True, help="Polymarket market ID (hex address)")
@click.option("--days", "-d", default=30, help="Number of days of history to fetch")
@click.option("--start", type=click.DateTime(), help="Start date (overrides --days)")
@click.option("--end", type=click.DateTime(), help="End date (default: now)")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path (.parquet or .json)")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing file")
def collect(
    market_id: str,
    days: int,
    start: Optional[datetime],
    end: Optional[datetime],
    output: str,
    force: bool,
):
    r"""
    Collect trade data from Polymarket.

    Fetches historical trades for a given market and saves to Parquet or JSON.
    Supports caching — will skip if output file exists unless --force is used.

    Example:
        xrtm-data collect -m 0x1234... -d 30 -o data/trades.parquet
    """
    output_path = Path(output)

    # Check cache
    if output_path.exists() and not force:
        console.print(f"[yellow]⚠ File exists:[/yellow] {output_path}")
        console.print("  Use --force to overwrite, or specify different output.")
        return

    # Calculate time range
    end_time = end or datetime.now(timezone.utc)
    if start:
        start_time = start.replace(tzinfo=timezone.utc)
    else:
        start_time = end_time - timedelta(days=days)

    console.print(Panel(
        f"[bold blue]Collecting Polymarket Trades[/bold blue]\n"
        f"Market: {market_id[:16]}...\n"
        f"Range: {start_time.date()} → {end_time.date()}",
        title="xrtm-data",
    ))

    # Run async collection
    async def _collect():
        from xrtm.data.providers.subgraph import PolymarketTradeSource

        source = PolymarketTradeSource()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching trades...", total=None)

            window = await source.fetch_trade_window(
                market_id=market_id,
                start_time=start_time,
                end_time=end_time,
            )

            progress.update(task, description=f"Fetched {len(window.trades)} trades")

        return window

    window = asyncio.run(_collect())

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix == ".parquet":
        _save_parquet(window, output_path)
    else:
        _save_json(window, output_path)

    console.print(f"[green]✓ Saved {len(window.trades)} trades to:[/green] {output_path}")

    # Summary table
    table = Table(title="Trade Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Trades", str(window.trade_count))
    table.add_row("Total Volume", f"${window.total_volume:,.2f}")
    table.add_row("VWAP", f"{window.volume_weighted_price:.4f}")
    console.print(table)


@main.command("fit-prior")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True), help="Input trades file")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output prior file (.json)")
@click.option("--half-life", "-h", default=24.0, help="Half-life in hours for decay weighting")
@click.option("--min-concentration", default=2.0, help="Minimum concentration (α+β)")
def fit_prior(input_path: str, output: str, half_life: float, min_concentration: float):
    r"""
    Fit a Beta prior from trade data.

    Reads trade history and fits a Beta distribution using exponential
    decay weighting (recent trades weighted more heavily).

    Example:
        xrtm-data fit-prior -i trades.parquet -o prior.json -h 24.0
    """
    from xrtm.data.kit.processors import fit_beta_exponential_decay

    console.print(Panel(
        f"[bold blue]Fitting Beta Prior[/bold blue]\n"
        f"Input: {input_path}\n"
        f"Half-life: {half_life} hours",
        title="xrtm-data",
    ))

    # Load trades
    trades = _load_trades(Path(input_path))
    console.print(f"Loaded {len(trades)} trades")

    # Fit prior
    prior = fit_beta_exponential_decay(
        trades,
        half_life_hours=half_life,
        min_concentration=min_concentration,
    )

    # Save
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prior_dict = prior.to_distribution_dict()
    prior_dict["metadata"] = {
        "source": str(input_path),
        "trade_count": len(trades),
        "half_life_hours": half_life,
        "fitted_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(output_path, "w") as f:
        json.dump(prior_dict, f, indent=2)

    console.print(f"[green]✓ Saved prior to:[/green] {output_path}")

    # Summary
    low, high = prior.credible_interval(0.9)
    table = Table(title="Fitted Prior")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("α (alpha)", f"{prior.alpha:.4f}")
    table.add_row("β (beta)", f"{prior.beta:.4f}")
    table.add_row("Mean", f"{prior.mean:.4f}")
    table.add_row("90% CI", f"[{low:.4f}, {high:.4f}]")
    console.print(table)


@main.command("info")
@click.argument("file_path", type=click.Path(exists=True))
def info(file_path: str):
    r"""
    Show information about a data file.

    Displays summary statistics for trade files or prior files.
    """
    path = Path(file_path)

    if path.suffix == ".json":
        with open(path) as f:
            data = json.load(f)

        if "family" in data:
            # It's a prior
            console.print(Panel(
                f"[bold]Prior File[/bold]\n"
                f"Family: {data['family']}\n"
                f"α: {data.get('alpha', 'N/A')}\n"
                f"β: {data.get('beta', 'N/A')}",
                title=path.name,
            ))
        else:
            console.print(f"JSON file with {len(data)} keys")
    elif path.suffix == ".parquet":
        import pyarrow.parquet as pq

        table = pq.read_table(path)
        console.print(Panel(
            f"[bold]Parquet File[/bold]\n"
            f"Rows: {table.num_rows}\n"
            f"Columns: {table.column_names}",
            title=path.name,
        ))


def _save_parquet(window, path: Path) -> None:
    r"""Save TradeWindow to Parquet format."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    data = {
        "price": [t.price for t in window.trades],
        "amount": [t.amount for t in window.trades],
        "timestamp": [t.timestamp.isoformat() for t in window.trades],
        "maker": [t.maker for t in window.trades],
        "taker": [t.taker for t in window.trades],
    }

    table = pa.table(data)
    pq.write_table(table, path)


def _save_json(window, path: Path) -> None:
    r"""Save TradeWindow to JSON format."""
    data = {
        "market_id": window.market_id,
        "start_time": window.start_time.isoformat(),
        "end_time": window.end_time.isoformat(),
        "trades": [
            {
                "price": t.price,
                "amount": t.amount,
                "timestamp": t.timestamp.isoformat(),
                "maker": t.maker,
                "taker": t.taker,
            }
            for t in window.trades
        ],
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_trades(path: Path) -> list:
    r"""Load trades from Parquet or JSON."""
    from xrtm.data.core.schemas import TradeEvent

    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        table = pq.read_table(path)
        df = table.to_pandas()
        return [
            TradeEvent(
                price=row.price,
                amount=row.amount,
                timestamp=datetime.fromisoformat(row.timestamp),
                maker=row.maker,
                taker=row.taker,
            )
            for row in df.itertuples(index=False)
        ]
    else:
        with open(path) as f:
            data = json.load(f)

        return [
            TradeEvent(
                price=t["price"],
                amount=t["amount"],
                timestamp=datetime.fromisoformat(t["timestamp"]),
                maker=t["maker"],
                taker=t["taker"],
            )
            for t in data.get("trades", data)
        ]


if __name__ == "__main__":
    main()


__all__ = ["main"]
