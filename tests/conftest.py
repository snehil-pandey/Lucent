"""Pytest configuration and test isolation fixtures."""
import pytest
from PySide6.QtCore import QSettings


@pytest.fixture(autouse=True)
def isolate_test_settings(monkeypatch, tmp_path):
    """Isolate QSettings to a temporary INI file for every test.
    This guarantees that running tests never pollutes or touches the user's registry.
    """
    settings_file = str(tmp_path / "test_settings.ini")

    def _mock_settings():
        return QSettings(settings_file, QSettings.Format.IniFormat)

    import lucent.config
    monkeypatch.setattr(lucent.config, "_settings", _mock_settings)
    yield
