"""Curated EAC trade procedures used when live TIP portals are unreachable."""

from trade.fetchers.base import ParsedProcedure

# Source URLs point to official portals for citation even when scraping fails.
FALLBACK_PROCEDURES: dict[str, list[dict]] = {
    "UG": [
        {
            "external_id": "UG-import-goods-commercial",
            "title": "Import goods for commercial purposes",
            "url": "https://www.ura.go.ug/en/e-services/efris/",
            "summary": "Standard commercial import procedure via Uganda Revenue Authority customs and URA e-services.",
            "activity_type": "import",
            "estimated_days": 5,
            "estimated_cost": "Variable duties and fees",
            "steps": [
                {
                    "sort_order": 0,
                    "title": "Obtain TIN and register importer",
                    "description": "Register with URA and obtain a Tax Identification Number before importing.",
                    "responsible_agency": "Uganda Revenue Authority (URA)",
                    "documents_required": ["TIN certificate", "Company registration"],
                },
                {
                    "sort_order": 1,
                    "title": "Prepare shipping documentation",
                    "description": "Commercial invoice, packing list, bill of lading/airway bill, and certificate of origin.",
                    "responsible_agency": "Exporter / Freight forwarder",
                    "documents_required": ["Commercial invoice", "Packing list", "Bill of lading"],
                },
                {
                    "sort_order": 2,
                    "title": "Customs declaration (ASYCUDA)",
                    "description": "Submit import declaration through ASYCUDA World via licensed clearing agent.",
                    "responsible_agency": "URA Customs",
                    "documents_required": ["Import declaration", "HS classification", "Import license if required"],
                },
                {
                    "sort_order": 3,
                    "title": "Pay duties and taxes",
                    "description": "Pay import duty, VAT, and any excise at customs before release.",
                    "responsible_agency": "URA",
                    "documents_required": ["Payment receipt"],
                },
                {
                    "sort_order": 4,
                    "title": "Release and delivery",
                    "description": "Goods released after inspection and payment confirmation.",
                    "responsible_agency": "URA Customs / Warehouse operator",
                    "documents_required": ["Release order"],
                },
            ],
        },
    ],
    "KE": [
        {
            "external_id": "KE-import-commercial-goods",
            "title": "Import commercial goods",
            "url": "https://kenyatradeportal.go.ke/",
            "summary": "Kenya import procedure via KRA customs and the Kenya Trade Information Portal.",
            "activity_type": "import",
            "estimated_days": 4,
            "estimated_cost": "Variable duties and IDF fees",
            "steps": [
                {
                    "sort_order": 0,
                    "title": "Obtain KRA PIN",
                    "description": "Register with Kenya Revenue Authority and obtain a PIN for import transactions.",
                    "responsible_agency": "Kenya Revenue Authority (KRA)",
                    "documents_required": ["KRA PIN certificate", "Company registration"],
                },
                {
                    "sort_order": 1,
                    "title": "Get Import Declaration Form (IDF)",
                    "description": "Apply for IDF through Kenya TradeNet before shipment arrival.",
                    "responsible_agency": "Kenya Revenue Authority",
                    "documents_required": ["Pro forma invoice", "IDF application"],
                },
                {
                    "sort_order": 2,
                    "title": "Customs clearance (iCMS)",
                    "description": "Clearing agent files entry in Integrated Customs Management System.",
                    "responsible_agency": "KRA Customs",
                    "documents_required": ["Bill of lading", "Commercial invoice", "Packing list", "IDF"],
                },
                {
                    "sort_order": 3,
                    "title": "Pay duties and release",
                    "description": "Pay import duty, VAT, and levies; obtain release after inspection if required.",
                    "responsible_agency": "KRA",
                    "documents_required": ["Payment confirmation"],
                },
            ],
        },
    ],
    "TZ": [
        {
            "external_id": "TZ-import-goods",
            "title": "Import goods into Tanzania",
            "url": "https://www.tra.go.tz/",
            "summary": "Tanzania import procedure via Tanzania Revenue Authority customs.",
            "activity_type": "import",
            "estimated_days": 6,
            "estimated_cost": "Variable duties",
            "steps": [
                {
                    "sort_order": 0,
                    "title": "Register with TRA",
                    "description": "Obtain TIN and importer registration with Tanzania Revenue Authority.",
                    "responsible_agency": "TRA",
                    "documents_required": ["TIN", "Business licence"],
                },
                {
                    "sort_order": 1,
                    "title": "Pre-arrival documentation",
                    "description": "Prepare invoice, packing list, transport document, and permits for regulated goods.",
                    "responsible_agency": "Importer",
                    "documents_required": ["Commercial invoice", "Packing list", "Bill of lading"],
                },
                {
                    "sort_order": 2,
                    "title": "Customs declaration (TANCIS)",
                    "description": "File import declaration in TANCIS through licensed clearing agent.",
                    "responsible_agency": "TRA Customs",
                    "documents_required": ["Customs declaration", "TIN", "Permits if applicable"],
                },
                {
                    "sort_order": 3,
                    "title": "Assessment and payment",
                    "description": "Pay import duty, VAT, and excise where applicable.",
                    "responsible_agency": "TRA",
                    "documents_required": ["Payment receipt"],
                },
            ],
        },
    ],
    "RW": [
        {
            "external_id": "RW-import-clearance",
            "title": "Import clearance in Rwanda",
            "url": "https://www.rra.gov.rw/",
            "summary": "Rwanda import procedure via Rwanda Revenue Authority and Rwanda Trade Portal.",
            "activity_type": "import",
            "estimated_days": 3,
            "estimated_cost": "Variable duties",
            "steps": [
                {
                    "sort_order": 0,
                    "title": "RRA registration",
                    "description": "Register business and obtain TIN from Rwanda Revenue Authority.",
                    "responsible_agency": "RRA",
                    "documents_required": ["TIN", "RDB registration"],
                },
                {
                    "sort_order": 1,
                    "title": "Submit import documentation",
                    "description": "Provide invoice, transport document, and certificates through clearing agent.",
                    "responsible_agency": "Licensed clearing agent",
                    "documents_required": ["Invoice", "Packing list", "Bill of lading"],
                },
                {
                    "sort_order": 2,
                    "title": "Customs processing (ReSW)",
                    "description": "Declaration filed in Rwanda Electronic Single Window (ReSW).",
                    "responsible_agency": "RRA Customs",
                    "documents_required": ["Customs declaration"],
                },
                {
                    "sort_order": 3,
                    "title": "Pay and release",
                    "description": "Pay duties and taxes; goods released upon compliance.",
                    "responsible_agency": "RRA",
                    "documents_required": ["Payment proof"],
                },
            ],
        },
    ],
}


def get_fallback_procedures(country_code: str) -> list[ParsedProcedure]:
    items = FALLBACK_PROCEDURES.get(country_code, [])
    return [
        ParsedProcedure(
            external_id=item["external_id"],
            title=item["title"],
            url=item["url"],
            summary=item["summary"],
            activity_type=item["activity_type"],
            steps=item["steps"],
            estimated_days=item.get("estimated_days"),
            estimated_cost=item.get("estimated_cost", ""),
        )
        for item in items
    ]
