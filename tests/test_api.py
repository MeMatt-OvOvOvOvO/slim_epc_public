"""Testy integracyjne dla epc/api.py (endpoint po endpoincie)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from epc.api import router, get_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(repo) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


@pytest.fixture
def client(repo):
    return make_client(repo)


# ---------------------------------------------------------------------------
# POST /ues — attach UE
# ---------------------------------------------------------------------------

class TestAttachUE:
    def test_attach_success(self, client):
        r = client.post("/ues", json={"ue_id": 10})
        assert r.status_code == 200
        assert r.json() == {"status": "attached", "ue_id": 10}

    def test_attach_duplicate_returns_400(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues", json={"ue_id": 10})
        assert r.status_code == 400

    def test_attach_ue_id_zero_returns_200(self, client):
        r = client.post("/ues", json={"ue_id": 0})
        assert r.status_code == 200
        assert r.json() == {"status": "attached", "ue_id": 0}

    def test_attach_ue_id_negative_returns_422(self, client):
        r = client.post("/ues", json={"ue_id": -1})
        assert r.status_code == 422

    def test_attach_ue_id_101_returns_422(self, client):
        r = client.post("/ues", json={"ue_id": 101})
        assert r.status_code == 422

    def test_attach_ue_id_boundary_0(self, client):
        r = client.post("/ues", json={"ue_id": 0})
        assert r.status_code == 200

    def test_attach_ue_id_boundary_1(self, client):
        r = client.post("/ues", json={"ue_id": 1})
        assert r.status_code == 200

    def test_attach_ue_id_boundary_100(self, client):
        r = client.post("/ues", json={"ue_id": 100})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /ues — list UEs
# ---------------------------------------------------------------------------

class TestListUEs:
    def test_empty_list(self, client):
        r = client.get("/ues")
        assert r.status_code == 200
        assert r.json() == {"ues": []}

    def test_lists_attached_ues(self, client):
        client.post("/ues", json={"ue_id": 5})
        client.post("/ues", json={"ue_id": 3})
        r = client.get("/ues")
        assert r.status_code == 200
        assert sorted(r.json()["ues"]) == [3, 5]


# ---------------------------------------------------------------------------
# GET /ues/{ue_id}
# ---------------------------------------------------------------------------

class TestGetUE:
    def test_get_existing_ue(self, client):
        client.post("/ues", json={"ue_id": 42})
        r = client.get("/ues/42")
        assert r.status_code == 200
        assert r.json()["ue_id"] == 42

    def test_get_nonexistent_ue(self, client):
        r = client.get("/ues/99")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /ues/{ue_id} — detach UE
# ---------------------------------------------------------------------------

class TestDetachUE:
    def test_detach_success(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.delete("/ues/10")
        assert r.status_code == 200
        assert r.json() == {"status": "detached", "ue_id": 10}

    def test_detach_nonexistent_returns_400(self, client):
        r = client.delete("/ues/99")
        assert r.status_code == 400

    def test_detach_removes_ue_from_list(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.delete("/ues/10")
        r = client.get("/ues")
        assert 10 not in r.json()["ues"]


# ---------------------------------------------------------------------------
# POST /ues/{ue_id}/bearers — add bearer
# ---------------------------------------------------------------------------

class TestAddBearer:
    def test_add_bearer_success(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers", json={"bearer_id": 3})
        assert r.status_code == 200
        assert r.json() == {"status": "bearer_added", "ue_id": 10, "bearer_id": 3}

    def test_add_bearer_duplicate_returns_400(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers", json={"bearer_id": 3})
        r = client.post("/ues/10/bearers", json={"bearer_id": 3})
        assert r.status_code == 400

    def test_add_bearer_ue_not_found(self, client):
        r = client.post("/ues/99/bearers", json={"bearer_id": 3})
        assert r.status_code == 400

    def test_add_bearer_invalid_id_returns_422(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers", json={"bearer_id": 10})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /ues/{ue_id}/bearers/{bearer_id} — delete bearer
# ---------------------------------------------------------------------------

class TestDeleteBearer:
    def test_delete_bearer_success(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers", json={"bearer_id": 3})
        r = client.delete("/ues/10/bearers/3")
        assert r.status_code == 200
        assert r.json()["status"] == "bearer_deleted"

    def test_delete_default_bearer_9_returns_400(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.delete("/ues/10/bearers/9")
        assert r.status_code == 400

    def test_delete_nonexistent_bearer_returns_400(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.delete("/ues/10/bearers/5")
        assert r.status_code == 400

    def test_delete_bearer_ue_not_found(self, client):
        r = client.delete("/ues/99/bearers/3")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /ues/{ue_id}/bearers/{bearer_id}/traffic — start traffic
# ---------------------------------------------------------------------------

class TestStartTraffic:
    def test_start_traffic_success(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "traffic_started"
        assert body["ue_id"] == 10
        assert body["bearer_id"] == 9
        assert body["target_bps"] == 10_000_000

    def test_start_traffic_ue_not_found(self, client):
        r = client.post("/ues/99/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        assert r.status_code == 400

    def test_start_traffic_bearer_not_found(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/5/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        assert r.status_code == 400

    def test_start_traffic_duplicate_returns_400(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        assert r.status_code == 400

    def test_start_traffic_invalid_protocol_returns_422(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "ftp", "Mbps": 10.0})
        assert r.status_code == 422

    def test_start_traffic_no_throughput_field_returns_422(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp"})
        assert r.status_code == 422

    def test_start_traffic_negative_mbps_returns_422(self, client):
        """Ujemna wartość Mbps powinna być odrzucona (DEF-RUL-003)."""
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": -1.0})
        assert r.status_code == 422

    def test_start_traffic_boundary_100mbps(self, client):
        """Dokładnie 100 Mbps mieści się w dozwolonym zakresie."""
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 100.0})
        assert r.status_code == 200

    def test_start_traffic_above_100mbps_returns_422(self, client):
        """100.1 Mbps przekracza limit — powinno być odrzucone (DEF-RUL-003)."""
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 100.1})
        assert r.status_code == 422

    def test_start_traffic_using_kbps(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.post("/ues/10/bearers/9/traffic", json={"protocol": "udp", "kbps": 500.0})
        assert r.status_code == 200
        assert r.json()["target_bps"] == 500_000


# ---------------------------------------------------------------------------
# DELETE /ues/{ue_id}/bearers/{bearer_id}/traffic — stop traffic
# ---------------------------------------------------------------------------

class TestStopTraffic:
    def test_stop_traffic_success(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        r = client.delete("/ues/10/bearers/9/traffic")
        assert r.status_code == 200
        assert r.json()["status"] == "traffic_stopped"

    def test_stop_traffic_not_running_returns_400(self, client):
        """Zatrzymanie ruchu, który nie jest aktywny, powinno zwrócić 400 (DEF-TRF-001)."""
        client.post("/ues", json={"ue_id": 10})
        r = client.delete("/ues/10/bearers/9/traffic")
        assert r.status_code == 400

    def test_stop_traffic_after_stop_returns_400(self, client):
        """Ponowne zatrzymanie już zatrzymanego ruchu powinno zwrócić 400 (DEF-TRF-001)."""
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        client.delete("/ues/10/bearers/9/traffic")
        r = client.delete("/ues/10/bearers/9/traffic")
        assert r.status_code == 400

    def test_stop_traffic_ue_not_found(self, client):
        r = client.delete("/ues/99/bearers/9/traffic")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /ues/{ue_id}/traffic — stop all traffic for UE (TC-006)
# ---------------------------------------------------------------------------

class TestStopAllTrafficForUE:
    def test_stop_all_success(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        r = client.delete("/ues/10/traffic")
        assert r.status_code == 200
        assert r.json()["status"] == "traffic_stopped"

    def test_stop_all_ue_not_found(self, client):
        r = client.delete("/ues/99/traffic")
        assert r.status_code == 400

    def test_stop_all_no_active_traffic_still_returns_200(self, client):
        """Stop-all na UE bez aktywnego ruchu zwraca 200 (w odróżnieniu od stop-single)."""
        client.post("/ues", json={"ue_id": 10})
        r = client.delete("/ues/10/traffic")
        assert r.status_code == 200

    def test_stop_all_multiple_bearers(self, client):
        """Stop-all zatrzymuje ruch na wszystkich bearerach (scenariusz z DEF-TRF-002)."""
        client.post("/ues", json={"ue_id": 56})
        client.post("/ues/56/bearers", json={"bearer_id": 4})
        client.post("/ues/56/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 2.0})
        client.post("/ues/56/bearers/4/traffic", json={"protocol": "udp", "Mbps": 3.0})
        r = client.delete("/ues/56/traffic")
        assert r.status_code == 200
        assert r.json()["status"] == "traffic_stopped"

    def test_stop_all_traffic_actually_stopped(self, client):
        """Po stop-all ponowne stop-single na każdym bearerze zwraca 400."""
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers", json={"bearer_id": 4})
        client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 2.0})
        client.post("/ues/10/bearers/4/traffic", json={"protocol": "udp", "Mbps": 3.0})
        client.delete("/ues/10/traffic")
        assert client.delete("/ues/10/bearers/9/traffic").status_code == 400
        assert client.delete("/ues/10/bearers/4/traffic").status_code == 400


# ---------------------------------------------------------------------------
# GET /ues/{ue_id}/bearers/{bearer_id}/traffic — stats
# ---------------------------------------------------------------------------

class TestGetTrafficStats:
    def test_stats_no_traffic_returns_zeros(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.get("/ues/10/bearers/9/traffic")
        assert r.status_code == 200
        body = r.json()
        assert body["tx_bps"] == 0
        assert body["rx_bps"] == 0
        assert body["duration"] == 0

    def test_stats_default_unit_is_bps(self, client):
        """Domyślna jednostka w odpowiedzi to bps (DEF-RUL-001)."""
        client.post("/ues", json={"ue_id": 10})
        r = client.get("/ues/10/bearers/9/traffic")
        assert r.status_code == 200
        assert r.json()["unit"] == "bps"

    def test_stats_unit_kbps(self, client):
        """Parametr unit=kbps zwraca pole unit=kbps (DEF-RUL-001)."""
        client.post("/ues", json={"ue_id": 10})
        r = client.get("/ues/10/bearers/9/traffic?unit=kbps")
        assert r.status_code == 200
        assert r.json()["unit"] == "kbps"

    def test_stats_unit_mbps(self, client):
        """Parametr unit=Mbps zwraca pole unit=Mbps (DEF-RUL-001)."""
        client.post("/ues", json={"ue_id": 10})
        r = client.get("/ues/10/bearers/9/traffic?unit=Mbps")
        assert r.status_code == 200
        assert r.json()["unit"] == "Mbps"

    def test_stats_invalid_unit_returns_422(self, client):
        client.post("/ues", json={"ue_id": 10})
        r = client.get("/ues/10/bearers/9/traffic?unit=invalid")
        assert r.status_code == 422

    def test_stats_after_start_returns_data(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 10.0})
        r = client.get("/ues/10/bearers/9/traffic")
        assert r.status_code == 200
        body = r.json()
        assert body["ue_id"] == 10
        assert body["bearer_id"] == 9

    def test_stats_ue_not_found(self, client):
        r = client.get("/ues/99/bearers/9/traffic")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /ues/stats — aggregated stats
# ---------------------------------------------------------------------------

class TestAggregatedStats:
    def test_empty_returns_zeros(self, client):
        r = client.get("/ues/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["scope"] == "all"
        assert body["ue_count"] == 0
        assert body["bearer_count"] == 0
        assert body["total_tx_bps"] == 0
        assert body["total_rx_bps"] == 0

    def test_scope_all_with_ues(self, client):
        client.post("/ues", json={"ue_id": 1})
        client.post("/ues", json={"ue_id": 2})
        r = client.get("/ues/stats")
        assert r.status_code == 200
        assert r.json()["ue_count"] == 2

    def test_scope_single_ue(self, client):
        client.post("/ues", json={"ue_id": 5})
        r = client.get("/ues/stats?ue_id=5")
        assert r.status_code == 200
        assert r.json()["scope"] == "ue:5"

    def test_invalid_ue_id_returns_400(self, client):
        r = client.get("/ues/stats?ue_id=99")
        assert r.status_code == 400

    def test_details_flag(self, client):
        client.post("/ues", json={"ue_id": 10})
        client.post("/ues/10/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 5.0})
        r = client.get("/ues/stats?include_details=true")
        assert r.status_code == 200
        assert r.json()["details"] is not None


# ---------------------------------------------------------------------------
# POST /reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_all(self, client):
        client.post("/ues", json={"ue_id": 1})
        client.post("/ues", json={"ue_id": 2})
        r = client.post("/reset")
        assert r.status_code == 200
        assert r.json() == {"status": "reset"}
        ues = client.get("/ues").json()["ues"]
        assert ues == []

    def test_reset_empty_state(self, client):
        r = client.post("/reset")
        assert r.status_code == 200
