from backend.core.taxonomy import challenge_supported, normalize_skill


def test_taxonomy_normalizes_english_japanese_and_aliases():
    assert normalize_skill("fast api") == "FastAPI"
    assert normalize_skill("PostgreSQL") == "SQL"
    assert normalize_skill("日本語 B1") == "Japanese B1"
    assert normalize_skill("not-a-real-skill") is None


def test_live_proof_is_only_advertised_for_supported_skills():
    assert challenge_supported("Python")
    assert challenge_supported("FastAPI")
    assert challenge_supported("SQL")
    assert not challenge_supported("Docker")
    assert not challenge_supported("Japanese B1")
