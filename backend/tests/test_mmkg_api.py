"""FastAPI smoke test for the mmkg admin endpoints."""
from __future__ import annotations


DOC = """# ZIP+4

ZIP+4 adds four digits to the 5-digit ZIP.

| digit | meaning        |
|-------|----------------|
| 1-2   | sectional      |
| 3-4   | delivery point |
"""


def test_mmkg_ingest_and_query(client):
    ingest = client.post(
        "/api/mmkg/ingest", json={"doc_id": "zip4", "content": DOC}
    )
    assert ingest.status_code == 200, ingest.text
    body = ingest.json()
    assert body["doc_id"] == "zip4"
    assert body["entities"]

    query = client.post(
        "/api/mmkg/query",
        json={"query": "delivery point", "doc_ids": ["zip4"], "top_k": 3},
    )
    assert query.status_code == 200, query.text
    hits = query.json()["hits"]
    assert hits
    # Expected: at least one hit has 'delivery' in label or summary.
    assert any(
        "deliv" in (h["entity"]["label"] + h["entity"]["summary"]).lower()
        for h in hits
    )


def test_mmkg_ingest_rejects_empty_request(client):
    r = client.post("/api/mmkg/ingest", json={"doc_id": "nothing"})
    assert r.status_code == 400
