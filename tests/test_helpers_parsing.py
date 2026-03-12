"""Tests for helpers.py parsing functions and adapter validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from gui.routes.helpers import parse_wg_output
from gui.integrations.wireguard.adapter import (
    _validate_interface,
    _validate_key,
    _validate_allowed_ips,
)


class TestParseWgOutput:
    WG_SHOW_OUTPUT = """\
interface: wg0
  public key: xTIBA5rboUvnH4htodjb6e697QjLERt1NAB4mZqp8Dg=
  private key: (hidden)
  listening port: 51820

peer: ba8AwcolBVDuhR/MKFU8O6CZrAjh7c20h6EOnQx0VRE=
  endpoint: 10.0.0.2:51820
  allowed ips: 10.0.0.2/32
  latest handshake: 1 minute, 30 seconds ago
  transfer: 92.65 KiB received, 31.24 KiB sent
  persistent keepalive: every 25 seconds

peer: TrMvSoP4jYQlY6RIzBgbssQqY3vxI2Pi+y71lOWWXX0=
  endpoint: 10.0.0.3:51820
  allowed ips: 10.0.0.3/32, 10.1.0.0/24
  transfer: 0 B received, 0 B sent
"""

    def test_parses_peers(self):
        result = parse_wg_output(self.WG_SHOW_OUTPUT)
        assert len(result) == 2
        assert "ba8AwcolBVDuhR/MKFU8O6CZrAjh7c20h6EOnQx0VRE=" in result
        assert "TrMvSoP4jYQlY6RIzBgbssQqY3vxI2Pi+y71lOWWXX0=" in result

    def test_parses_endpoint(self):
        result = parse_wg_output(self.WG_SHOW_OUTPUT)
        peer = result["ba8AwcolBVDuhR/MKFU8O6CZrAjh7c20h6EOnQx0VRE="]
        assert peer["endpoint"] == "10.0.0.2"
        assert peer["endpoint_port"] == "51820"

    def test_parses_transfer(self):
        result = parse_wg_output(self.WG_SHOW_OUTPUT)
        peer = result["ba8AwcolBVDuhR/MKFU8O6CZrAjh7c20h6EOnQx0VRE="]
        assert peer["transfer_rx"] == "92.65 KiB"
        assert peer["transfer_tx"] == "31.24 KiB"

    def test_parses_zero_transfer(self):
        result = parse_wg_output(self.WG_SHOW_OUTPUT)
        peer = result["TrMvSoP4jYQlY6RIzBgbssQqY3vxI2Pi+y71lOWWXX0="]
        assert peer["transfer_rx"] == "0 B"
        assert peer["transfer_tx"] == "0 B"

    def test_parses_handshake(self):
        result = parse_wg_output(self.WG_SHOW_OUTPUT)
        peer = result["ba8AwcolBVDuhR/MKFU8O6CZrAjh7c20h6EOnQx0VRE="]
        assert peer["latest_handshake"] == 90

    def test_parses_allowed_ips(self):
        result = parse_wg_output(self.WG_SHOW_OUTPUT)
        peer = result["TrMvSoP4jYQlY6RIzBgbssQqY3vxI2Pi+y71lOWWXX0="]
        assert "10.0.0.3/32, 10.1.0.0/24" in peer["allowed_ips"]

    def test_empty_output(self):
        assert parse_wg_output("") == {}

    def test_no_peers(self):
        output = "interface: wg0\n  public key: abc\n"
        assert parse_wg_output(output) == {}

    def test_handshake_days_hours_minutes_seconds(self):
        output = (
            "peer: abc=\n"
            "  latest handshake: 2 days, 3 hours, 4 minutes, 5 seconds ago\n"
        )
        result = parse_wg_output(output)
        expected = 2 * 86400 + 3 * 3600 + 4 * 60 + 5
        assert result["abc="]["latest_handshake"] == expected


class TestAdapterValidation:
    def test_valid_interface(self):
        assert _validate_interface("wg0") == "wg0"
        assert _validate_interface("wg-test_01") == "wg-test_01"

    def test_invalid_interface_rejects_spaces(self):
        with pytest.raises(ValueError):
            _validate_interface("wg 0")

    def test_invalid_interface_rejects_special_chars(self):
        with pytest.raises(ValueError):
            _validate_interface("wg0; rm -rf /")

    def test_invalid_interface_too_long(self):
        with pytest.raises(ValueError):
            _validate_interface("a" * 16)

    def test_valid_key(self):
        from wireguard_tools.wireguard_key import WireguardKey
        key = str(WireguardKey.generate())
        assert _validate_key(key) == key

    def test_invalid_key(self):
        with pytest.raises(ValueError):
            _validate_key("not-a-valid-key")

    def test_valid_allowed_ips(self):
        assert _validate_allowed_ips("10.0.0.0/24") == "10.0.0.0/24"
        assert _validate_allowed_ips("10.0.0.0/24,10.1.0.0/16") == "10.0.0.0/24,10.1.0.0/16"

    def test_invalid_allowed_ips(self):
        with pytest.raises(ValueError):
            _validate_allowed_ips("not-an-ip; rm -rf /")

    def test_allowed_ips_strips_spaces(self):
        result = _validate_allowed_ips("10.0.0.0/24, 10.1.0.0/16")
        assert result == "10.0.0.0/24,10.1.0.0/16"
