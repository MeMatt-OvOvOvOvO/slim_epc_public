"""Warstwa 3: testy logiki endpointów — bezpośrednie wywołania handlerów z mockami.

Cel: sprawdzić gałęzie kodu (branch coverage) wewnątrz każdego handlera
bez uruchamiania serwera HTTP. Mockujemy repo i traffic managera.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from epc.api import (
    attach_ue,
    list_ues,
    get_ue,
    detach_ue,
    add_bearer,
    delete_bearer,
    start_traffic,
    stop_traffic,
    stop_all_traffic_for_ue,
    get_traffic_stats,
    get_ues_stats,
    reset_all,
)
from epc.models import (
    AttachUERequest,
    AddBearerRequest,
    StartTrafficRequest,
    UEState,
    BearerConfig,
    ThroughputStats,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_repo(**kwargs):
    return MagicMock(**kwargs)


def make_tm(**kwargs):
    return MagicMock(**kwargs)


def ue_with_bearer(ue_id=10, bearer_id=9):
    state = UEState(ue_id=ue_id)
    state.bearers[bearer_id] = BearerConfig(bearer_id=bearer_id)
    return state


# ---------------------------------------------------------------------------
# attach_ue
# ---------------------------------------------------------------------------

class TestAttachUeLogic:
    def test_success_returns_attach_response(self):
        repo = make_repo()
        result = attach_ue(AttachUERequest(ue_id=10), repo)
        assert result.status == "attached"
        assert result.ue_id == 10
        repo.attach_ue.assert_called_once_with(10)

    def test_value_error_raises_http_400(self):
        repo = make_repo()
        repo.attach_ue.side_effect = ValueError("UE already attached")
        with pytest.raises(HTTPException) as exc:
            attach_ue(AttachUERequest(ue_id=10), repo)
        assert exc.value.status_code == 400
        assert "already attached" in exc.value.detail


# ---------------------------------------------------------------------------
# list_ues
# ---------------------------------------------------------------------------

class TestListUesLogic:
    def test_returns_all_ue_ids(self):
        repo = make_repo()
        repo.list_ues.return_value = iter([1, 2, 3])
        result = list_ues(repo)
        assert sorted(result.ues) == [1, 2, 3]

    def test_empty_list(self):
        repo = make_repo()
        repo.list_ues.return_value = iter([])
        result = list_ues(repo)
        assert result.ues == []


# ---------------------------------------------------------------------------
# get_ue
# ---------------------------------------------------------------------------

class TestGetUeLogic:
    def test_success_returns_ue_state(self):
        repo = make_repo()
        repo.get_ue.return_value = UEState(ue_id=42)
        result = get_ue(42, repo)
        assert result.ue_id == 42

    def test_value_error_raises_http_400(self):
        repo = make_repo()
        repo.get_ue.side_effect = ValueError("UE not found")
        with pytest.raises(HTTPException) as exc:
            get_ue(99, repo)
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# detach_ue
# ---------------------------------------------------------------------------

class TestDetachUeLogic:
    def test_success_returns_detach_response(self):
        repo = make_repo()
        result = detach_ue(10, repo)
        assert result.status == "detached"
        assert result.ue_id == 10
        repo.detach_ue.assert_called_once_with(10)

    def test_value_error_raises_http_400(self):
        repo = make_repo()
        repo.detach_ue.side_effect = ValueError("UE not found")
        with pytest.raises(HTTPException) as exc:
            detach_ue(99, repo)
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# add_bearer
# ---------------------------------------------------------------------------

class TestAddBearerLogic:
    def test_success_returns_bearer_add_response(self):
        repo = make_repo()
        result = add_bearer(10, AddBearerRequest(bearer_id=3), repo)
        assert result.status == "bearer_added"
        assert result.bearer_id == 3
        repo.add_bearer.assert_called_once_with(10, 3)

    def test_value_error_raises_http_400(self):
        repo = make_repo()
        repo.add_bearer.side_effect = ValueError("Bearer already exists")
        with pytest.raises(HTTPException) as exc:
            add_bearer(10, AddBearerRequest(bearer_id=3), repo)
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# delete_bearer
# ---------------------------------------------------------------------------

class TestDeleteBearerLogic:
    def test_ue_not_found_raises_400(self):
        repo = make_repo()
        repo.get_ue.side_effect = ValueError("UE not found")
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                delete_bearer(99, 3, repo)
        assert exc.value.status_code == 400

    def test_bearer_not_in_state_raises_400(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                delete_bearer(10, 5, repo)  # bearer 5 nie istnieje
        assert exc.value.status_code == 400

    def test_stops_traffic_if_running(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=3)
        tm = make_tm()
        tm.is_running.return_value = True
        with patch("epc.api.get_traffic_manager", return_value=tm):
            delete_bearer(10, 3, repo)
        tm.stop.assert_called_once_with(10, 3)

    def test_does_not_stop_traffic_if_not_running(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=3)
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            delete_bearer(10, 3, repo)
        tm.stop.assert_not_called()

    def test_delete_bearer_repo_error_raises_400(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=3)
        repo.delete_bearer.side_effect = ValueError("Cannot remove default bearer")
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            with pytest.raises(HTTPException) as exc:
                delete_bearer(10, 3, repo)
        assert exc.value.status_code == 400

    def test_success_returns_bearer_delete_response(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=3)
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = delete_bearer(10, 3, repo)
        assert result.status == "bearer_deleted"
        assert result.bearer_id == 3


# ---------------------------------------------------------------------------
# start_traffic
# ---------------------------------------------------------------------------

class TestStartTrafficLogic:
    def _body(self, mbps=10.0, protocol="tcp"):
        return StartTrafficRequest(protocol=protocol, Mbps=mbps)

    def test_ue_not_found_raises_400(self):
        repo = make_repo()
        repo.get_ue.side_effect = ValueError("UE not found")
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                start_traffic(99, 9, self._body(), repo)
        assert exc.value.status_code == 400

    def test_bearer_not_found_raises_400(self):
        repo = make_repo()
        repo.get_ue.return_value = UEState(ue_id=10)  # brak bearerów
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                start_traffic(10, 9, self._body(), repo)
        assert exc.value.status_code == 400

    def test_traffic_already_running_raises_400(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)
        tm = make_tm()
        tm.start.side_effect = ValueError("Traffic already running")
        with patch("epc.api.get_traffic_manager", return_value=tm):
            with pytest.raises(HTTPException) as exc:
                start_traffic(10, 9, self._body(), repo)
        assert exc.value.status_code == 400

    def test_success_returns_correct_target_bps(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = start_traffic(10, 9, self._body(mbps=20.0), repo)
        assert result.status == "traffic_started"
        assert result.target_bps == 20_000_000

    def test_bearer_protocol_stored_on_bearer(self):
        """Protokół z requestu jest zapisywany na bearerze przed startem ruchu."""
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            start_traffic(10, 9, self._body(protocol="udp"), repo)
        saved_bearer = repo.update_bearer.call_args[0][1]
        assert saved_bearer.protocol == "udp"

    def test_initial_stats_created_when_not_existing(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)  # stats puste
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            start_traffic(10, 9, self._body(), repo)
        repo.update_stats.assert_called_once()


# ---------------------------------------------------------------------------
# stop_traffic
# ---------------------------------------------------------------------------

class TestStopTrafficLogic:
    def test_ue_not_found_raises_400(self):
        repo = make_repo()
        repo.get_ue.side_effect = ValueError("UE not found")
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                stop_traffic(99, 9, repo)
        assert exc.value.status_code == 400

    def test_bearer_not_found_raises_400(self):
        repo = make_repo()
        repo.get_ue.return_value = UEState(ue_id=10)  # brak bearerów
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                stop_traffic(10, 9, repo)
        assert exc.value.status_code == 400

    def test_success_calls_tm_stop(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = stop_traffic(10, 9, repo)
        tm.stop.assert_called_once_with(10, 9)
        assert result.status == "traffic_stopped"

    def test_success_sets_bearer_inactive(self):
        repo = make_repo()
        state = ue_with_bearer(bearer_id=9)
        state.bearers[9].active = True
        repo.get_ue.return_value = state
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            stop_traffic(10, 9, repo)
        saved_bearer = repo.update_bearer.call_args[0][1]
        assert saved_bearer.active is False


# ---------------------------------------------------------------------------
# get_traffic_stats
# ---------------------------------------------------------------------------

class TestGetTrafficStatsLogic:
    def test_ue_not_found_raises_400(self):
        repo = make_repo()
        repo.get_ue.side_effect = ValueError("UE not found")
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                get_traffic_stats(99, 9, repo)
        assert exc.value.status_code == 400

    def test_no_stats_returns_zeros(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)  # stats puste
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_traffic_stats(10, 9, repo)
        assert result.tx_bps == 0
        assert result.rx_bps == 0
        assert result.duration == 0

    def test_stats_calculated_when_traffic_stopped(self):
        """Gdy ruch zatrzymany, bps liczone na podstawie last_update_ts."""
        repo = make_repo()
        state = ue_with_bearer(bearer_id=9)
        state.stats[9] = ThroughputStats(
            bearer_id=9, ue_id=10,
            bytes_tx=8000, bytes_rx=4000,
            start_ts=100.0, last_update_ts=101.0,  # 1 sekunda
            protocol="tcp", target_bps=64000,
        )
        repo.get_ue.return_value = state
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_traffic_stats(10, 9, repo)
        # 8000 bajtów * 8 bitów / 1 sekunda = 64000 bps
        assert result.tx_bps == 64000
        assert result.rx_bps == 32000
        assert result.duration == pytest.approx(1.0)

    def test_stats_use_current_time_when_running(self):
        """Gdy ruch aktywny, end_ts = time.time()."""
        repo = make_repo()
        state = ue_with_bearer(bearer_id=9)
        state.stats[9] = ThroughputStats(
            bearer_id=9, ue_id=10,
            bytes_tx=16000, bytes_rx=8000,
            start_ts=100.0, last_update_ts=101.0,
            protocol="tcp", target_bps=128000,
        )
        repo.get_ue.return_value = state
        tm = make_tm()
        tm.is_running.return_value = True
        with patch("epc.api.get_traffic_manager", return_value=tm), \
             patch("epc.api.time") as mock_time:
            mock_time.time.return_value = 102.0  # 2 sekundy od start_ts
            result = get_traffic_stats(10, 9, repo)
        # 16000 * 8 / 2 = 64000
        assert result.tx_bps == 64000
        assert result.duration == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# get_ues_stats (aggregation logic)
# ---------------------------------------------------------------------------

class TestGetUesStatsLogic:
    def _make_state_with_stats(self, ue_id, bearer_id, bytes_tx, bytes_rx, start_ts, last_ts):
        state = ue_with_bearer(ue_id=ue_id, bearer_id=bearer_id)
        state.stats[bearer_id] = ThroughputStats(
            bearer_id=bearer_id, ue_id=ue_id,
            bytes_tx=bytes_tx, bytes_rx=bytes_rx,
            start_ts=start_ts, last_update_ts=last_ts,
        )
        return state

    def test_ue_id_not_found_raises_400(self):
        repo = make_repo()
        repo.ue_exists.return_value = False
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                get_ues_stats(repo, ue_id=99)
        assert exc.value.status_code == 400

    def test_scope_all_when_no_ue_id(self):
        repo = make_repo()
        repo.list_ues.return_value = []
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_ues_stats(repo, ue_id=None)
        assert result.scope == "all"

    def test_scope_ue_when_ue_id_given(self):
        repo = make_repo()
        repo.ue_exists.return_value = True
        repo.get_ue.return_value = ue_with_bearer(ue_id=5)
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_ues_stats(repo, ue_id=5)
        assert result.scope == "ue:5"

    def test_aggregates_tx_rx_across_bearers(self):
        """Suma tx/rx bps z dwóch bearerow jednego UE."""
        state = ue_with_bearer(ue_id=10, bearer_id=9)
        state.bearers[3] = BearerConfig(bearer_id=3)
        # bearer 9: 8000 bytes_tx w ciągu 1 sekundy → 64000 bps
        state.stats[9] = ThroughputStats(
            bearer_id=9, ue_id=10,
            bytes_tx=8000, bytes_rx=4000,
            start_ts=100.0, last_update_ts=101.0,
        )
        # bearer 3: 16000 bytes_tx w ciągu 1 sekundy → 128000 bps
        state.stats[3] = ThroughputStats(
            bearer_id=3, ue_id=10,
            bytes_tx=16000, bytes_rx=8000,
            start_ts=100.0, last_update_ts=101.0,
        )
        repo = make_repo()
        repo.list_ues.return_value = [10]
        repo.get_ue.return_value = state
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_ues_stats(repo, ue_id=None)
        assert result.total_tx_bps == 192000
        assert result.total_rx_bps == 96000
        assert result.bearer_count == 2

    def test_no_details_by_default(self):
        repo = make_repo()
        repo.list_ues.return_value = []
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_ues_stats(repo, ue_id=None, include_details=False)
        assert result.details is None

    def test_details_included_when_flag_true(self):
        state = ue_with_bearer(ue_id=10, bearer_id=9)
        state.stats[9] = ThroughputStats(
            bearer_id=9, ue_id=10,
            bytes_tx=8000, bytes_rx=4000,
            start_ts=100.0, last_update_ts=101.0,
        )
        repo = make_repo()
        repo.list_ues.return_value = [10]
        repo.get_ue.return_value = state
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_ues_stats(repo, ue_id=None, include_details=True)
        assert result.details is not None
        assert "10" in result.details

    def test_zero_duration_returns_zero_bps(self):
        """Gdy duration == 0 (brak start_ts), bps = 0."""
        state = ue_with_bearer(ue_id=10, bearer_id=9)
        state.stats[9] = ThroughputStats(
            bearer_id=9, ue_id=10,
            bytes_tx=9999, bytes_rx=9999,
            start_ts=None, last_update_ts=None,
        )
        repo = make_repo()
        repo.list_ues.return_value = [10]
        repo.get_ue.return_value = state
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_ues_stats(repo, ue_id=None)
        assert result.total_tx_bps == 0
        assert result.total_rx_bps == 0


# ---------------------------------------------------------------------------
# stop_all_traffic_for_ue (TC-006)
# ---------------------------------------------------------------------------

class TestStopAllTrafficForUeLogic:
    def test_ue_not_found_raises_400(self):
        repo = make_repo()
        repo.get_ue.side_effect = ValueError("UE not found")
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                stop_all_traffic_for_ue(99, repo)
        assert exc.value.status_code == 400

    def test_stops_all_bearers(self):
        repo = make_repo()
        state = UEState(ue_id=10)
        state.bearers[9] = BearerConfig(bearer_id=9)
        state.bearers[3] = BearerConfig(bearer_id=3)
        repo.get_ue.return_value = state
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = stop_all_traffic_for_ue(10, repo)
        assert tm.stop.call_count == 2
        assert result.status == "traffic_stopped"

    def test_no_bearers_does_not_raise(self):
        repo = make_repo()
        repo.get_ue.return_value = UEState(ue_id=10)
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = stop_all_traffic_for_ue(10, repo)
        tm.stop.assert_not_called()
        assert result.status == "traffic_stopped"


# ---------------------------------------------------------------------------
# get_traffic_stats — unit conversion (DEF-RUL-001)
# ---------------------------------------------------------------------------

class TestGetTrafficStatsUnitConversion:
    def _state_with_stats(self):
        state = ue_with_bearer(bearer_id=9)
        state.stats[9] = ThroughputStats(
            bearer_id=9, ue_id=10,
            bytes_tx=8_000_000, bytes_rx=4_000_000,  # 8 MB tx, 4 MB rx
            start_ts=100.0, last_update_ts=101.0,     # 1 sekunda
            protocol="tcp", target_bps=64_000_000,
        )
        return state

    def test_default_unit_bps(self):
        repo = make_repo()
        repo.get_ue.return_value = self._state_with_stats()
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_traffic_stats(10, 9, repo, unit=None)
        assert result.unit == "bps"
        assert result.tx_bps == 64_000_000  # 8_000_000 bytes * 8 / 1s

    def test_unit_kbps_converts_values(self):
        repo = make_repo()
        repo.get_ue.return_value = self._state_with_stats()
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_traffic_stats(10, 9, repo, unit="kbps")
        assert result.unit == "kbps"
        assert result.tx_bps == 64_000  # 64_000_000 / 1000

    def test_unit_mbps_converts_values(self):
        repo = make_repo()
        repo.get_ue.return_value = self._state_with_stats()
        tm = make_tm()
        tm.is_running.return_value = False
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = get_traffic_stats(10, 9, repo, unit="Mbps")
        assert result.unit == "Mbps"
        assert result.tx_bps == 64  # 64_000_000 / 1_000_000

    def test_invalid_unit_raises_422(self):
        repo = make_repo()
        repo.get_ue.return_value = ue_with_bearer(bearer_id=9)
        with patch("epc.api.get_traffic_manager"):
            with pytest.raises(HTTPException) as exc:
                get_traffic_stats(10, 9, repo, unit="invalid")
        assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# reset_all
# ---------------------------------------------------------------------------

class TestResetAllLogic:
    def test_stops_all_traffic_and_resets_repo(self):
        repo = make_repo()
        tm = make_tm()
        with patch("epc.api.get_traffic_manager", return_value=tm):
            result = reset_all(repo)
        tm.stop_all.assert_called_once()
        repo.reset_all.assert_called_once()
        assert result.status == "reset"
