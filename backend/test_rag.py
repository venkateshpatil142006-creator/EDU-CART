from backend.rag import retrieve_relevant_context


def test_retrieval_prefers_topic_specific_coursework():
    materials = [
        "Birds migrate seasonally in response to food and climate.",
        "ABAP internal tables store rows in memory. A sorted table keeps rows ordered by its key.",
        "In ABAP, a hashed table uses a unique key and supports efficient key-based access.",
    ]

    context = retrieve_relevant_context("ABAP internal table key", materials)

    assert "ABAP internal tables" in context
    assert "hashed table" in context
    assert "Birds migrate" not in context


def test_retrieval_does_not_inject_unrelated_material_when_no_match():
    context = retrieve_relevant_context(
        "Quantum chromodynamics", ["A lecture about marine biology and coral reefs."]
    )

    assert context == ""
