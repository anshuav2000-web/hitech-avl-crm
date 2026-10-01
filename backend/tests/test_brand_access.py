"""Unit tests for the per-user brand allow-list.

The bug these lock down: an empty allow-list was treated as "this user may not
use any brand", so every non-admin account rendered every brand dropdown empty.
An absent or empty list now means unrestricted, and restriction is expressed
only by a non-empty list.
"""
import os

import pytest

pytest.importorskip("server", reason="backend module not importable in this environment")

from server import _allowed_brands  # noqa: E402


class TestAllowedBrands:
    def test_admin_is_unrestricted(self):
        assert _allowed_brands({"role": "admin"}) is None
        assert _allowed_brands({"role": "admin", "allowed_brands": []}) is None

    def test_empty_list_is_unrestricted(self):
        """The regression: [] used to lock every brand in the UI."""
        assert _allowed_brands({"role": "sales", "allowed_brands": []}) is None

    def test_missing_key_is_unrestricted(self):
        assert _allowed_brands({"role": "sales"}) is None

    def test_explicit_list_restricts(self):
        got = _allowed_brands({"role": "sales", "allowed_brands": ["RCF", "DiGiCo"]})
        assert got == ["RCF", "DiGiCo"]

    def test_every_brand_is_locked_only_when_a_list_is_given(self):
        allowed = _allowed_brands({"role": "service", "allowed_brands": ["RCF"]})
        flags = [b["name"] not in allowed for b in ({"name": "RCF"}, {"name": "QSC"})]
        assert flags == [False, True]