"""Tests for WireguardKey: generation, conversion, edge cases."""

import pytest

from wireguard_tools.wireguard_key import WireguardKey, convert_wireguard_key


class TestConvertWireguardKey:
    def test_from_base64(self):
        b64 = "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg="
        raw = convert_wireguard_key(b64)
        assert len(raw) == 32

    def test_from_base64_no_padding(self):
        b64_no_pad = "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg"
        raw = convert_wireguard_key(b64_no_pad)
        assert len(raw) == 32

    def test_from_hex(self):
        key = WireguardKey.generate()
        raw = convert_wireguard_key(key.hex)
        assert raw == key.keydata

    def test_from_bytes(self):
        key = WireguardKey.generate()
        raw = convert_wireguard_key(key.keydata)
        assert raw == key.keydata

    def test_from_wireguard_key(self):
        key = WireguardKey.generate()
        raw = convert_wireguard_key(key)
        assert raw == key.keydata

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="Invalid WireGuard key length"):
            convert_wireguard_key(b"\x00" * 16)

    def test_empty_bytes_raises(self):
        with pytest.raises(ValueError):
            convert_wireguard_key(b"")


class TestWireguardKey:
    def test_generate_produces_valid_key(self):
        key = WireguardKey.generate()
        assert len(key.keydata) == 32
        assert (key.keydata[0] & (~248)) == 0
        assert (key.keydata[31] & (~127)) == 0
        assert (key.keydata[31] & 64) != 0

    def test_public_key_derivation(self):
        key = WireguardKey.generate()
        pub = key.public_key()
        assert len(pub.keydata) == 32
        assert pub != key

    def test_public_key_deterministic(self):
        key = WireguardKey.generate()
        assert key.public_key() == key.public_key()

    def test_str_is_base64(self):
        key = WireguardKey.generate()
        s = str(key)
        assert s.endswith("=")
        assert len(s) == 44

    def test_urlsafe_property(self):
        key = WireguardKey.generate()
        urlsafe = key.urlsafe
        assert "+" not in urlsafe
        assert "/" not in urlsafe

    def test_hex_property(self):
        key = WireguardKey.generate()
        assert len(key.hex) == 64

    def test_bool_nonzero(self):
        key = WireguardKey.generate()
        assert bool(key)

    def test_bool_zero(self):
        zero_key = WireguardKey(b"\x00" * 32)
        assert not bool(zero_key)

    def test_frozen_key(self):
        key = WireguardKey.generate()
        with pytest.raises(AttributeError):
            key.keydata = b"\x00" * 32

    def test_equality(self):
        b64 = "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg="
        k1 = WireguardKey(b64)
        k2 = WireguardKey(b64)
        assert k1 == k2

    def test_hash_usable_as_dict_key(self):
        key = WireguardKey.generate()
        d = {key: "value"}
        assert d[key] == "value"

    def test_roundtrip_base64(self):
        key = WireguardKey.generate()
        restored = WireguardKey(str(key))
        assert restored == key

    def test_roundtrip_hex(self):
        key = WireguardKey.generate()
        restored = WireguardKey(key.hex)
        assert restored == key
