import json
import pytest
from r0env import diagnostics, windows_cli


def test_inventory_cannot_claim_leak_protection(monkeypatch):
    monkeypatch.setattr(diagnostics.windows, 'powershell', lambda script: json.dumps({
        'adapters': [{'Name': 'mihomo TUN', 'Status': 'Up'}],
        'registered_browsers': [{'exe': 'chrome.exe'}],
    }))
    report = diagnostics.collect()
    assert report['read_only']
    assert report['overall'] == 'unverified'
    assert all(item['status'] == 'unverified' for item in report['verification'].values())


def test_failed_inventory_propagates_error(monkeypatch):
    def fail(_):
        raise RuntimeError('PowerShell unavailable')
    monkeypatch.setattr(diagnostics.windows, 'powershell', fail)
    with pytest.raises(RuntimeError):
        diagnostics.collect()


def test_doctor_cli_is_read_only(monkeypatch, capsys):
    monkeypatch.setattr(diagnostics, 'collect', lambda: {'overall': 'unverified', 'read_only': True})
    assert windows_cli.main(['doctor']) == 0
    assert json.loads(capsys.readouterr().out)['overall'] == 'unverified'
    assert windows_cli.main(['doctor', '--execute']) == 2
