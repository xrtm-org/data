import json
from pathlib import Path

from click.testing import CliRunner

from xrtm.data.cli import main


def test_info_rejects_unsupported_suffix() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        path = Path("trades.txt")
        path.write_text("not a supported data file")

        result = runner.invoke(main, ["info", str(path)])

        assert result.exit_code != 0
        assert "Unsupported file type" in result.output


def test_collect_rejects_unsupported_output_suffix_before_fetching() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["collect", "-m", "0x1234", "-o", "trades.txt"])

    assert result.exit_code != 0
    assert "Output path must end with .parquet or .json" in result.output


def test_info_accepts_json_file() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        path = Path("prior.json")
        path.write_text(json.dumps({"family": "beta", "alpha": 1, "beta": 2}))

        result = runner.invoke(main, ["info", str(path)])

        assert result.exit_code == 0
        assert "Prior File" in result.output
