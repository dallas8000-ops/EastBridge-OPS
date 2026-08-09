# App data in the GitHub zip

These JSON files are the **committed image of the app** — countries, demo orgs, vendors, regulatory samples, trade procedures, and evidence for the assistant.

Anyone who downloads the repo zip can **open these files in an editor** and see what the platform contains before running anything.

## Files

| File | Contents |
|------|----------|
| `initial_01_core.json` | EAC countries, data sources, industries |
| `initial_02_accounts.json` | Demo user, organizations, memberships |
| `initial_03_vendors.json` | Vendor due diligence records |
| `initial_04_regulatory.json` | Regulatory changes and alert subscriptions |
| `initial_05_intelligence.json` | Economic indicators and country risk snapshots |
| `initial_06_trade.json` | Trade procedures and steps |
| `initial_07_evidence.json` | Source documents for the AI assistant |
| `MANIFEST.json` | Export checksums (CI uses this to detect drift) |

## Load after migrate

```powershell
python backend\manage.py load_initial_data
python backend\manage.py verify_data
```

## Before you push (keep zip downloads current)

```powershell
npm run export:fixtures
git add backend/fixtures/
git commit -m "Update app data fixtures for zip download"
git push
```

Or enable the git hook once — it refreshes fixtures automatically before each push:

```powershell
npm run hooks:install
```

CI fails if fixtures are out of date (`export_app_data --check`).
