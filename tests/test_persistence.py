from __future__ import annotations

import copy

from backend.services.persistence import JsonStore


def test_json_store_survives_reinstantiation(tmp_path, fixture_path):
    store_path = tmp_path / "runtime.json"
    first = JsonStore(store_path, fixture_path)

    def add_event(data: dict) -> None:
        data.setdefault("verification_events", []).append(
            {"id": "VER-PERSISTED", "student_id": "STU-DEMO-IND-001"}
        )

    first.update(add_event)
    second = JsonStore(store_path, fixture_path)

    assert any(
        event["id"] == "VER-PERSISTED"
        for event in second.read()["verification_events"]
    )


def test_demo_reset_is_idempotent_and_returns_independent_data(tmp_path, fixture_path):
    store = JsonStore(tmp_path / "runtime.json", fixture_path)
    expected = copy.deepcopy(store.reset())

    store.update(lambda data: data["claims"].append({"id": "CLM-TRANSIENT"}))
    first_reset = store.reset()
    first_reset["students"][0]["display_name"] = "mutated return value"
    second_reset = store.reset()

    assert second_reset == expected
    assert not any(claim.get("id") == "CLM-TRANSIENT" for claim in second_reset["claims"])
    assert second_reset["students"][0]["display_name"] != "mutated return value"


def test_fixture_does_not_store_plaintext_password(demo_data: dict):
    assert demo_data["users"]
    for user in demo_data["users"]:
        assert "password" not in user
        assert user["password_hash"].startswith("scrypt$")
        assert user["password_hash"] != user.get("email")
