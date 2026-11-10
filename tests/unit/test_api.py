from fastapi.testclient import TestClient

from app.api.main import create_app
from tests.fakes import CSV_LOG, memory_container


def client():
    c, *_ = memory_container()
    return TestClient(create_app(container_factory=lambda: c))


def test_full_crud_flow_over_http():
    http = client()
    created = http.post("/processes", json={"name": "Torno"})
    assert created.status_code == 201 and created.json()["status"] == "vazio"
    loaded = http.post(f"/processes/{created.json()['id']}/log", files={"file": ("t.csv", CSV_LOG, "text/csv")})
    assert loaded.status_code == 200
    body = loaded.json()
    assert body["status"] == "mapeando" and body["operations"][0]["suggestedActivity"]
    pid = body["id"]

    mapping = {"operations": [{"rawLabel": op["rawLabel"], "activity": op["suggestedActivity"], "description": "d"} for op in body["operations"]]}
    mapped = http.put(f"/processes/{pid}/operations", json=mapping)
    assert mapped.status_code == 200 and mapped.json()["status"] == "pronto"
    assert mapped.json()["graph"]["nodes"][0]["frequency"] > 0

    assert http.get("/processes").json()[0]["variantCount"] == 2
    assert len(http.get(f"/processes/{pid}/traces", params={"variantId": "v1"}).json()) == 2
    series = http.get(f"/processes/{pid}/series", params={"activity": "Usinagem"}).json()
    assert [p["value"] for p in series["points"]] == [40.0, 50.0, 70.0]

    assert http.patch(f"/processes/{pid}", json={"name": "Torno 2"}).json()["name"] == "Torno 2"
    assert http.delete(f"/processes/{pid}").status_code == 204
    assert http.get(f"/processes/{pid}").status_code == 404


def test_errors_are_4xx():
    http = client()
    pid = http.post("/processes", json={"name": "X"}).json()["id"]
    bad = http.post(f"/processes/{pid}/log", files={"file": ("x.txt", b"a", "text/plain")})
    assert bad.status_code == 422
    assert http.post("/processes/nope/log", files={"file": ("t.csv", CSV_LOG, "text/csv")}).status_code == 404
    assert http.post("/processes", json={"name": ""}).status_code == 422
    assert http.put("/processes/nope/operations", json={"operations": []}).status_code == 404


def test_activities_and_swagger():
    http = client()
    assert http.post("/activities", json={"name": "Usinagem", "description": "Corte"}).status_code == 201
    assert http.post("/activities", json={"name": "usinagem"}).json()["name"] == "Usinagem"
    assert http.get("/activities").json() == [{"id": "a0", "name": "Usinagem", "description": "Corte"}]
    assert http.get("/openapi.json").json()["info"]["title"].startswith("Driftor")
