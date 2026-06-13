"""Testy jednostkowe dla epc/models.py."""

import pytest
from pydantic import ValidationError

from epc.models import (
    AttachUERequest,
    AddBearerRequest,
    BearerConfig,
    StartTrafficRequest,
    ThroughputStats,
    UEState,
)


# ---------------------------------------------------------------------------
# BearerConfig
# ---------------------------------------------------------------------------

class TestBearerConfig:
    def test_valid_bearer_id_min(self):
        b = BearerConfig(bearer_id=1)
        assert b.bearer_id == 1

    def test_valid_bearer_id_max(self):
        b = BearerConfig(bearer_id=9)
        assert b.bearer_id == 9

    def test_invalid_bearer_id_zero(self):
        with pytest.raises(ValidationError):
            BearerConfig(bearer_id=0)

    def test_invalid_bearer_id_ten(self):
        with pytest.raises(ValidationError):
            BearerConfig(bearer_id=10)

    def test_valid_protocol_tcp(self):
        b = BearerConfig(bearer_id=1, protocol="tcp")
        assert b.protocol == "tcp"

    def test_valid_protocol_udp(self):
        b = BearerConfig(bearer_id=1, protocol="udp")
        assert b.protocol == "udp"

    def test_invalid_protocol(self):
        with pytest.raises(ValidationError):
            BearerConfig(bearer_id=1, protocol="http")

    def test_defaults(self):
        b = BearerConfig(bearer_id=5)
        assert b.protocol is None
        assert b.target_bps is None
        assert b.active is False


# ---------------------------------------------------------------------------
# AttachUERequest
# ---------------------------------------------------------------------------

class TestAttachUERequest:
    def test_valid_ue_id_min(self):
        r = AttachUERequest(ue_id=1)
        assert r.ue_id == 1

    def test_valid_ue_id_max(self):
        r = AttachUERequest(ue_id=100)
        assert r.ue_id == 100

    def test_invalid_ue_id_zero(self):
        with pytest.raises(ValidationError):
            AttachUERequest(ue_id=0)

    def test_invalid_ue_id_101(self):
        with pytest.raises(ValidationError):
            AttachUERequest(ue_id=101)


# ---------------------------------------------------------------------------
# AddBearerRequest
# ---------------------------------------------------------------------------

class TestAddBearerRequest:
    def test_valid(self):
        r = AddBearerRequest(bearer_id=3)
        assert r.bearer_id == 3

    def test_invalid_too_high(self):
        with pytest.raises(ValidationError):
            AddBearerRequest(bearer_id=10)


# ---------------------------------------------------------------------------
# StartTrafficRequest — walidator "dokładnie jedno pole throughput"
# ---------------------------------------------------------------------------

class TestStartTrafficRequest:
    def test_valid_mbps(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=10.0)
        assert r.Mbps == 10.0

    def test_valid_kbps(self):
        r = StartTrafficRequest(protocol="udp", kbps=500.0)
        assert r.kbps == 500.0

    def test_valid_bps(self):
        r = StartTrafficRequest(protocol="tcp", bps=1_000_000)
        assert r.bps == 1_000_000

    def test_no_throughput_field_raises(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp")

    def test_two_throughput_fields_raises(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp", Mbps=10.0, kbps=500.0)

    def test_invalid_protocol(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="ftp", Mbps=10.0)

    def test_negative_mbps_raises(self):
        """Ujemna wartość transferu powinna być odrzucona (DEF-RUL-003)."""
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp", Mbps=-1.0)

    def test_zero_mbps_raises(self):
        """Transfer 0 Mbps nie ma sensu i powinien być odrzucony."""
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp", Mbps=0.0)

    def test_valid_direction_dl(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=10.0, direction="DL")
        assert r.direction == "DL"

    def test_valid_direction_ul(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=10.0, direction="UL")
        assert r.direction == "UL"

    def test_invalid_direction_raises(self):
        """Nieprawidłowa wartość direction powinna być odrzucona (TC-008)."""
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp", Mbps=10.0, direction="BOTH")

    def test_direction_optional(self):
        """Pole direction jest opcjonalne."""
        r = StartTrafficRequest(protocol="tcp", Mbps=10.0)
        assert r.direction is None

    # --- target_bps() ---

    def test_target_bps_from_mbps(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=10.0)
        assert r.target_bps() == 10_000_000

    def test_target_bps_from_kbps(self):
        r = StartTrafficRequest(protocol="tcp", kbps=500.0)
        assert r.target_bps() == 500_000

    def test_target_bps_from_bps(self):
        r = StartTrafficRequest(protocol="tcp", bps=123_456)
        assert r.target_bps() == 123_456

    def test_target_bps_boundary_100mbps(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=100.0)
        assert r.target_bps() == 100_000_000


# ---------------------------------------------------------------------------
# UEState — init_defaults
# ---------------------------------------------------------------------------

class TestUEState:
    def test_defaults_created(self):
        s = UEState(ue_id=5)
        assert s.bearers == {}
        assert s.stats == {}

    def test_valid_ue_id(self):
        s = UEState(ue_id=100)
        assert s.ue_id == 100

    def test_invalid_ue_id(self):
        with pytest.raises(ValidationError):
            UEState(ue_id=0)

    def test_bearers_none_converted_to_empty_dict(self):
        s = UEState(ue_id=1, bearers=None)
        assert s.bearers == {}

    def test_stats_none_converted_to_empty_dict(self):
        s = UEState(ue_id=1, stats=None)
        assert s.stats == {}
