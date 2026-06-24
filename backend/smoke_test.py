"""End-to-end API smoke test for EastBridge Ops Intelligence."""
import json
import os
import sys
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import Client

PASS = []
FAIL = []
WARN = []


def ok(name: str, detail: str = ""):
    PASS.append((name, detail))


def bad(name: str, detail: str):
    FAIL.append((name, detail))


def warn(name: str, detail: str):
    WARN.append((name, detail))


def login_client() -> tuple[Client, dict | None]:
    c = Client(HTTP_HOST="localhost")
    r = c.post(
        "/api/v1/auth/login/",
        data=json.dumps({"username": "demo", "password": "demo12345"}),
        content_type="application/json",
    )
    if r.status_code != 200:
        return c, None
    token = r.json().get("access")
    c.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    me = c.get("/api/v1/auth/me/")
    if me.status_code != 200:
        return c, None
    data = me.json()
    memberships = data.get("memberships", [])
    if memberships:
        c.defaults["HTTP_X_ORGANIZATION_ID"] = str(memberships[0]["organization"]["id"])
    return c, data


def main():
    anon = Client(HTTP_HOST="localhost")

    # --- Public / anonymous ---
    tests = [
        ("GET /health/", lambda: anon.get("/api/v1/health/")),
        ("GET /countries/", lambda: anon.get("/api/v1/countries/")),
        ("GET /ingestion/status/", lambda: anon.get("/api/v1/ingestion/status/")),
        ("GET /regulatory/changes/", lambda: anon.get("/api/v1/regulatory/changes/")),
        (
            "GET /regulatory/changes/?ordering=-detected_at",
            lambda: anon.get("/api/v1/regulatory/changes/?ordering=-detected_at"),
        ),
        ("GET /trade/procedures/", lambda: anon.get("/api/v1/trade/procedures/")),
        ("GET /intelligence/indicators/", lambda: anon.get("/api/v1/intelligence/indicators/")),
        ("GET /intelligence/risk/", lambda: anon.get("/api/v1/intelligence/risk/")),
        ("GET /playbooks/industries/", lambda: anon.get("/api/v1/playbooks/industries/")),
    ]
    for name, fn in tests:
        try:
            r = fn()
            if r.status_code == 200:
                ok(name, f"status={r.status_code}")
            else:
                bad(name, f"status={r.status_code} body={r.content[:200]!r}")
        except Exception as exc:
            bad(name, traceback.format_exc()[-500:])

    # Assistant ask (anonymous)
    try:
        r = anon.post(
            "/api/v1/assistant/queries/ask/",
            data=json.dumps(
                {
                    "question": "What are import requirements for solar panels in Uganda?",
                    "country_code": "UG",
                }
            ),
            content_type="application/json",
        )
        if r.status_code in (200, 201):
            d = r.json()
            if d.get("has_sufficient_evidence") or d.get("refusal_reason"):
                ok("POST /assistant/queries/ask/ (anon)", f"evidence={d.get('has_sufficient_evidence')}")
            else:
                bad("POST /assistant/queries/ask/ (anon)", "missing evidence/refusal in response")
        else:
            bad("POST /assistant/queries/ask/ (anon)", f"status={r.status_code} {r.content[:300]!r}")
    except Exception:
        bad("POST /assistant/queries/ask/ (anon)", traceback.format_exc()[-500:])

    # --- Auth ---
    auth, login_data = login_client()
    if not login_data:
        bad("POST /auth/login/", "demo/demo12345 login failed — run seed_demo_org")
    else:
        ok("POST /auth/login/", f"user={login_data['username']}")

    if login_data:
        auth_tests = [
            ("GET /vendors/", lambda: auth.get("/api/v1/vendors/")),
            ("GET /regulatory/alerts/", lambda: auth.get("/api/v1/regulatory/alerts/")),
            ("GET /assistant/queries/", lambda: auth.get("/api/v1/assistant/queries/")),
            ("GET /playbooks/", lambda: auth.get("/api/v1/playbooks/")),
        ]
        for name, fn in auth_tests:
            try:
                r = fn()
                if r.status_code == 200:
                    data = r.json()
                    count = data.get("count", len(data.get("results", [])))
                    ok(name, f"count={count}")
                else:
                    bad(name, f"status={r.status_code} {r.content[:200]!r}")
            except Exception:
                bad(name, traceback.format_exc()[-500:])

        # Playbook generate
        try:
            r = auth.post(
                "/api/v1/playbooks/generate/",
                data=json.dumps(
                    {
                        "origin_country": "DE",
                        "target_country_code": "UG",
                        "industry_slug": "solar-equipment",
                        "company_description": "Smoke test GmbH",
                    }
                ),
                content_type="application/json",
            )
            if r.status_code == 201:
                pb = r.json()
                ok("POST /playbooks/generate/", f"id={pb.get('id')} steps={len(pb.get('steps', []))}")
                step_id = pb["steps"][0]["id"] if pb.get("steps") else None
                if step_id:
                    r2 = auth.patch(
                        f"/api/v1/playbooks/steps/{step_id}/",
                        data=json.dumps({"is_completed": True}),
                        content_type="application/json",
                    )
                    if r2.status_code == 200:
                        ok("PATCH /playbooks/steps/{id}/", "toggle step")
                    else:
                        bad("PATCH /playbooks/steps/{id}/", f"status={r2.status_code}")
                # cleanup delete
                r3 = auth.delete(f"/api/v1/playbooks/{pb['id']}/")
                if r3.status_code == 204:
                    ok("DELETE /playbooks/{id}/", "cleanup")
                else:
                    warn("DELETE /playbooks/{id}/", f"status={r3.status_code}")
            else:
                bad("POST /playbooks/generate/", f"status={r.status_code} {r.content[:300]!r}")
        except Exception:
            bad("POST /playbooks/generate/", traceback.format_exc()[-500:])

        # Alert create + patch + delete
        try:
            r = auth.post(
                "/api/v1/regulatory/alerts/",
                data=json.dumps(
                    {"email": "smoke@test.example", "country_code": "UG", "category": "tax"}
                ),
                content_type="application/json",
            )
            if r.status_code == 201:
                alert = r.json()
                ok("POST /regulatory/alerts/", f"id={alert['id']}")
                r2 = auth.patch(
                    f"/api/v1/regulatory/alerts/{alert['id']}/",
                    data=json.dumps({"is_active": False}),
                    content_type="application/json",
                )
                if r2.status_code == 200:
                    ok("PATCH /regulatory/alerts/{id}/", "pause")
                else:
                    bad("PATCH /regulatory/alerts/{id}/", f"status={r2.status_code}")
                r3 = auth.delete(f"/api/v1/regulatory/alerts/{alert['id']}/")
                if r3.status_code == 204:
                    ok("DELETE /regulatory/alerts/{id}/", "cleanup")
                else:
                    bad("DELETE /regulatory/alerts/{id}/", f"status={r3.status_code}")
            else:
                bad("POST /regulatory/alerts/", f"status={r.status_code} {r.content[:300]!r}")
        except Exception:
            bad("POST /regulatory/alerts/", traceback.format_exc()[-500:])

        # Vendor create patch delete
        try:
            r = auth.post(
                "/api/v1/vendors/",
                data=json.dumps(
                    {
                        "name": "Smoke Test Vendor Ltd",
                        "registration_number": "SMOKE-001",
                        "country_code": "UG",
                        "business_profile": "Smoke test only",
                        "verification_status": "pending",
                        "risk_score": "50.0",
                        "red_flags": [],
                    }
                ),
                content_type="application/json",
            )
            if r.status_code == 201:
                vendor = r.json()
                ok("POST /vendors/", f"id={vendor['id']}")
                r2 = auth.patch(
                    f"/api/v1/vendors/{vendor['id']}/",
                    data=json.dumps({"risk_score": "55.0"}),
                    content_type="application/json",
                )
                if r2.status_code == 200:
                    ok("PATCH /vendors/{id}/", "update risk")
                else:
                    bad("PATCH /vendors/{id}/", f"status={r2.status_code}")
                r3 = auth.delete(f"/api/v1/vendors/{vendor['id']}/")
                if r3.status_code == 204:
                    ok("DELETE /vendors/{id}/", "cleanup")
                else:
                    bad("DELETE /vendors/{id}/", f"status={r3.status_code}")
            else:
                bad("POST /vendors/", f"status={r.status_code} {r.content[:300]!r}")
        except Exception:
            bad("POST /vendors/", traceback.format_exc()[-500:])

        # Org switcher — second org
        memberships = login_data.get("memberships", [])
        if len(memberships) >= 2:
            org2 = memberships[1]["organization"]["id"]
            auth2 = Client(HTTP_HOST="localhost")
            auth2.defaults["HTTP_AUTHORIZATION"] = auth.defaults["HTTP_AUTHORIZATION"]
            auth2.defaults["HTTP_X_ORGANIZATION_ID"] = str(org2)
            r = auth2.get("/api/v1/vendors/")
            if r.status_code == 200:
                ok("Org switch (2nd org vendors)", f"count={r.json().get('count')}")
            else:
                bad("Org switch (2nd org vendors)", f"status={r.status_code}")
        else:
            warn("Org switcher", "demo user has only one org — run seed_demo_org")

    # Data presence checks
    try:
        status = anon.get("/api/v1/ingestion/status/").json()
        if status.get("evidence_count", 0) == 0:
            warn("Data: evidence", "0 documents — run embed_evidence")
        else:
            ok("Data: evidence", str(status["evidence_count"]))
        if status.get("regulatory_changes_count", 0) == 0:
            warn("Data: regulatory", "0 changes — run ingest --target regulatory")
        else:
            ok("Data: regulatory", str(status["regulatory_changes_count"]))
        if status.get("trade_procedures_count", 0) == 0:
            warn("Data: trade", "0 procedures — run sync_trade_procedures --offline")
        else:
            ok("Data: trade", str(status["trade_procedures_count"]))
    except Exception:
        bad("Data checks", traceback.format_exc()[-300:])

    print("\n=== SMOKE TEST RESULTS ===\n")
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}  WARN: {len(WARN)}\n")
    if FAIL:
        print("-- FAILURES --")
        for name, detail in FAIL:
            print(f"  [FAIL] {name}")
            print(f"         {detail[:400]}")
    if WARN:
        print("\n-- WARNINGS --")
        for name, detail in WARN:
            print(f"  [WARN] {name}: {detail}")
    if PASS:
        print("\n-- PASSED --")
        for name, detail in PASS:
            print(f"  [OK]   {name}" + (f" — {detail}" if detail else ""))

    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
