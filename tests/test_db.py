"""Testy jednostkowe dla epc/db.py (EPCRepository)."""

import pytest
from epc.db import EPCRepository
from epc.models import BearerConfig, ThroughputStats


# ---------------------------------------------------------------------------
# attach_ue / detach_ue / get_ue / list_ues
# ---------------------------------------------------------------------------

class TestAttachDetach:
    def test_attach_ue_success(self, repo):
        repo.attach_ue(10)
        assert repo.ue_exists(10)

    def test_attach_ue_creates_default_bearer_9(self, repo):
        repo.attach_ue(10)
        state = repo.get_ue(10)
        assert 9 in state.bearers

    def test_attach_ue_duplicate_raises(self, repo):
        repo.attach_ue(10)
        with pytest.raises(ValueError, match="already attached"):
            repo.attach_ue(10)

    def test_detach_ue_success(self, repo):
        repo.attach_ue(10)
        repo.detach_ue(10)
        assert not repo.ue_exists(10)

    def test_detach_ue_not_found_raises(self, repo):
        with pytest.raises(ValueError, match="not found"):
            repo.detach_ue(99)

    def test_get_ue_success(self, repo):
        repo.attach_ue(42)
        state = repo.get_ue(42)
        assert state.ue_id == 42

    def test_get_ue_not_found_raises(self, repo):
        with pytest.raises(ValueError, match="not found"):
            repo.get_ue(99)

    def test_ue_exists_false(self, repo):
        assert not repo.ue_exists(55)

    def test_ue_exists_true(self, repo):
        repo.attach_ue(55)
        assert repo.ue_exists(55)


class TestListUes:
    def test_empty(self, repo):
        assert list(repo.list_ues()) == []

    def test_multiple_ues_sorted(self, repo):
        repo.attach_ue(5)
        repo.attach_ue(2)
        repo.attach_ue(9)
        assert list(repo.list_ues()) == [2, 5, 9]

    def test_after_detach(self, repo):
        repo.attach_ue(1)
        repo.attach_ue(2)
        repo.detach_ue(1)
        assert list(repo.list_ues()) == [2]


# ---------------------------------------------------------------------------
# add_bearer / delete_bearer
# ---------------------------------------------------------------------------

class TestBearers:
    def test_add_bearer_success(self, repo):
        repo.attach_ue(10)
        repo.add_bearer(10, 3)
        state = repo.get_ue(10)
        assert 3 in state.bearers

    def test_add_bearer_duplicate_raises(self, repo):
        repo.attach_ue(10)
        repo.add_bearer(10, 3)
        with pytest.raises(ValueError, match="already exists"):
            repo.add_bearer(10, 3)

    def test_add_bearer_ue_not_found_raises(self, repo):
        with pytest.raises(ValueError, match="not found"):
            repo.add_bearer(99, 3)

    def test_delete_bearer_success(self, repo):
        repo.attach_ue(10)
        repo.add_bearer(10, 3)
        repo.delete_bearer(10, 3)
        state = repo.get_ue(10)
        assert 3 not in state.bearers

    def test_delete_default_bearer_9_raises(self, repo):
        repo.attach_ue(10)
        with pytest.raises(ValueError, match="Cannot remove default bearer"):
            repo.delete_bearer(10, 9)

    def test_delete_bearer_not_found_raises(self, repo):
        repo.attach_ue(10)
        with pytest.raises(ValueError, match="not found"):
            repo.delete_bearer(10, 5)

    def test_delete_bearer_also_removes_stats(self, repo):
        repo.attach_ue(10)
        repo.add_bearer(10, 3)
        stats = ThroughputStats(bearer_id=3, ue_id=10)
        repo.update_stats(10, stats)
        repo.delete_bearer(10, 3)
        state = repo.get_ue(10)
        assert 3 not in state.stats


# ---------------------------------------------------------------------------
# update_bearer / update_stats / save_ue
# ---------------------------------------------------------------------------

class TestUpdateOperations:
    def test_update_bearer(self, repo):
        repo.attach_ue(10)
        bearer = BearerConfig(bearer_id=9, protocol="tcp", target_bps=1_000_000, active=True)
        repo.update_bearer(10, bearer)
        state = repo.get_ue(10)
        assert state.bearers[9].protocol == "tcp"
        assert state.bearers[9].target_bps == 1_000_000
        assert state.bearers[9].active is True

    def test_update_stats(self, repo):
        repo.attach_ue(10)
        stats = ThroughputStats(bearer_id=9, ue_id=10, bytes_tx=500, bytes_rx=250)
        repo.update_stats(10, stats)
        state = repo.get_ue(10)
        assert state.stats[9].bytes_tx == 500
        assert state.stats[9].bytes_rx == 250


# ---------------------------------------------------------------------------
# reset_all
# ---------------------------------------------------------------------------

class TestResetAll:
    def test_reset_removes_all_ues(self, repo):
        repo.attach_ue(1)
        repo.attach_ue(2)
        repo.attach_ue(3)
        repo.reset_all()
        assert list(repo.list_ues()) == []

    def test_reset_empty_repo_does_not_raise(self, repo):
        repo.reset_all()  # powinno przejść bez błędu
