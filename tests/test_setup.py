"""Tests for the setup command."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sutras.cli.main import setup


def test_setup_check_mode(tmp_path):
    target = tmp_path / ".claude" / "skills" / "sutras" / "SKILL.md"
    with patch.object(Path, "home", return_value=tmp_path):
        runner = CliRunner()
        result = runner.invoke(setup, ["--check"])
    assert result.exit_code == 0
    assert "Would install" in result.output
    assert not target.exists()


def test_setup_install(tmp_path):
    target = tmp_path / ".claude" / "skills" / "sutras" / "SKILL.md"
    with patch.object(Path, "home", return_value=tmp_path):
        runner = CliRunner()
        result = runner.invoke(setup, [])
    assert result.exit_code == 0
    assert "installed" in result.output.lower()
    assert target.exists()
    content = target.read_text()
    assert "name: sutras" in content


def test_setup_overwrites_existing(tmp_path):
    target_dir = tmp_path / ".claude" / "skills" / "sutras"
    target_dir.mkdir(parents=True)
    target = target_dir / "SKILL.md"
    target.write_text("old content")

    with patch.object(Path, "home", return_value=tmp_path):
        runner = CliRunner()
        result = runner.invoke(setup, [])
    assert result.exit_code == 0
    assert target.read_text() != "old content"


def test_setup_uninstall(tmp_path):
    target_dir = tmp_path / ".claude" / "skills" / "sutras"
    target_dir.mkdir(parents=True)
    target = target_dir / "SKILL.md"
    target.write_text("skill content")

    with patch.object(Path, "home", return_value=tmp_path):
        runner = CliRunner()
        result = runner.invoke(setup, ["--uninstall"])
    assert result.exit_code == 0
    assert "removed" in result.output.lower()
    assert not target.exists()


def test_setup_uninstall_not_installed(tmp_path):
    with patch.object(Path, "home", return_value=tmp_path):
        runner = CliRunner()
        result = runner.invoke(setup, ["--uninstall"])
    assert result.exit_code == 0
    assert "not installed" in result.output.lower()
