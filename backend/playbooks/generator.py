"""Rule-based market entry playbook generation enriched with indexed evidence."""

from assistant.models import EvidenceDocument
from core.models import Country
from playbooks.models import Industry, MarketEntryPlaybook, PlaybookStep

# Base steps per industry slug — enriched with evidence at generation time
INDUSTRY_STEPS: dict[str, list[tuple[str, str, str]]] = {
    "solar-equipment": [
        (PlaybookStep.StepType.REGISTRATION, "Register with investment authority", "Register your foreign company or incorporate a local subsidiary with the national investment promotion agency."),
        (PlaybookStep.StepType.TAX, "Tax and VAT registration", "Obtain a Tax Identification Number (TIN) and register for VAT if turnover thresholds apply."),
        (PlaybookStep.StepType.IMPORT, "Solar equipment import compliance", "Verify HS codes, EAC duty rates, pre-shipment inspection requirements, and product standards for PV modules and inverters."),
        (PlaybookStep.StepType.PERMIT, "Energy sector permits", "Apply for generation/distribution permits if installing grid-connected systems; obtain UNBS or equivalent product certification."),
        (PlaybookStep.StepType.PAYMENT, "Cross-border payment setup", "Establish USD/EUR settlement via authorized dealer bank; review withholding tax on technical fees and royalties."),
        (PlaybookStep.StepType.PARTNER_RISK, "Local EPC partner vetting", "Conduct due diligence on local installers — verify URA compliance, contract history, and licensing."),
        (PlaybookStep.StepType.DOCUMENT, "Required documents", "Certificate of incorporation, board resolution, passport copies of directors, product datasheets, bill of lading, commercial invoice, packing list, certificate of origin."),
        (PlaybookStep.StepType.COMPLIANCE, "Ongoing compliance", "Monthly VAT returns, annual income tax filing, transfer pricing documentation if related-party transactions exist."),
        (PlaybookStep.StepType.LOGISTICS, "Customs clearance workflow", "Engage licensed clearing agent; submit ASYCUDA declaration; pay import duty and VAT at customs."),
    ],
    "agri-processing": [
        (PlaybookStep.StepType.REGISTRATION, "Business registration", "Register company and obtain trading license from local authority."),
        (PlaybookStep.StepType.TAX, "Tax registration", "Register for TIN, VAT, and PAYE if employing staff."),
        (PlaybookStep.StepType.IMPORT, "Equipment and input imports", "Review phytosanitary requirements for agricultural inputs and machinery HS classifications."),
        (PlaybookStep.StepType.PERMIT, "Food processing license", "Obtain UNBS/KEBS food handling and HACCP-related permits."),
        (PlaybookStep.StepType.COMPLIANCE, "Export compliance", "Register with export promotion council; meet EAC/SPS standards for EU market re-exports."),
    ],
    "fintech": [
        (PlaybookStep.StepType.REGISTRATION, "Company incorporation", "Incorporate locally or register foreign company branch."),
        (PlaybookStep.StepType.PERMIT, "Financial services licensing", "Apply for payment service provider or microfinance license from central bank/regulator."),
        (PlaybookStep.StepType.TAX, "Tax and data compliance", "Register for taxes; implement data protection compliance per national DPA."),
        (PlaybookStep.StepType.COMPLIANCE, "AML/CFT compliance", "Establish KYC/AML policies aligned with Financial Intelligence Authority requirements."),
    ],
    "logistics": [
        (PlaybookStep.StepType.REGISTRATION, "Company registration", "Register logistics entity and obtain trading license."),
        (PlaybookStep.StepType.PERMIT, "Customs agent license", "Apply for customs clearing agent license if providing brokerage services."),
        (PlaybookStep.StepType.IMPORT, "Fleet import", "Review vehicle and equipment import duties under EAC CET."),
        (PlaybookStep.StepType.LOGISTICS, "Bonded warehouse setup", "Apply for warehouse license if operating bonded storage."),
    ],
    "manufacturing": [
        (PlaybookStep.StepType.REGISTRATION, "Industrial registration", "Register with investment authority; apply for industrial park allocation if applicable."),
        (PlaybookStep.StepType.TAX, "Tax incentives review", "Evaluate investment code incentives (corporate income tax holidays, duty drawbacks)."),
        (PlaybookStep.StepType.IMPORT, "Raw material imports", "Classify inputs under EAC Common External Tariff; apply for duty remission if exporting."),
        (PlaybookStep.StepType.PERMIT, "Environmental permit", "Obtain NEMA/environmental impact assessment approval."),
        (PlaybookStep.StepType.COMPLIANCE, "Labor compliance", "Register with NSSF/pension; comply with occupational safety requirements."),
    ],
}

COUNTRY_TIMELINE_WEEKS: dict[str, int] = {
    "UG": 10,
    "KE": 8,
    "TZ": 12,
    "RW": 6,
    "BI": 14,
    "SS": 16,
}

EVIDENCE_KEYWORDS: dict[str, list[str]] = {
    "solar-equipment": ["solar", "import", "energy", "equipment", "vat", "customs"],
    "agri-processing": ["agriculture", "food", "export", "phytosanitary", "processing"],
    "fintech": ["payment", "financial", "license", "data protection", "bank"],
    "logistics": ["customs", "clearance", "warehouse", "freight", "import"],
    "manufacturing": ["investment", "industrial", "tariff", "environment", "labor"],
}


def _find_evidence(country_code: str, industry_slug: str) -> EvidenceDocument | None:
    keywords = EVIDENCE_KEYWORDS.get(industry_slug, [])
    docs = EvidenceDocument.objects.filter(country_code__in=[country_code, ""]).order_by(
        "-published_at", "-indexed_at"
    )
    for doc in docs[:100]:
        text = f"{doc.title} {doc.content}".lower()
        if any(kw in text for kw in keywords):
            return doc
    return docs.first() if docs.exists() else None


def _find_trade_procedure(country_code: str, industry_slug: str):
    from trade.models import TradeProcedure

    keywords = EVIDENCE_KEYWORDS.get(industry_slug, [])
    procedures = TradeProcedure.objects.filter(country__code=country_code).prefetch_related("steps")
    for proc in procedures:
        text = f"{proc.title} {proc.summary}".lower()
        if any(kw in text for kw in keywords):
            return proc
    return procedures.first()


def generate_playbook(
    origin_country: str,
    industry: Industry,
    target_country: Country,
    company_description: str = "",
    organization=None,
) -> MarketEntryPlaybook:
    steps_template = INDUSTRY_STEPS.get(industry.slug, INDUSTRY_STEPS["manufacturing"])
    evidence = _find_evidence(target_country.code, industry.slug)
    trade_proc = _find_trade_procedure(target_country.code, industry.slug)

    playbook = MarketEntryPlaybook.objects.create(
        organization=organization,
        origin_country=origin_country.upper(),
        industry=industry,
        target_country=target_country,
        company_description=company_description,
        estimated_timeline_weeks=COUNTRY_TIMELINE_WEEKS.get(target_country.code, 12),
    )

    for order, (step_type, title, description) in enumerate(steps_template):
        source_url = ""
        enriched = description

        if trade_proc and step_type in (
            PlaybookStep.StepType.IMPORT,
            PlaybookStep.StepType.LOGISTICS,
            PlaybookStep.StepType.PERMIT,
        ):
            source_url = trade_proc.source_url
            tip_step = trade_proc.steps.filter(title__icontains=title.split()[0]).first()
            if tip_step:
                enriched = f"{description} Per {trade_proc.source_portal}: {tip_step.description[:400]}"
            else:
                enriched = f"{description} See {trade_proc.title} ({trade_proc.source_url})."
        elif evidence and order == 0:
            source_url = evidence.source_url
            enriched = f"{description} Refer to indexed source: {evidence.title}."

        if company_description and step_type == PlaybookStep.StepType.REGISTRATION:
            enriched = f"{enriched} Company context: {company_description[:200]}"

        PlaybookStep.objects.create(
            playbook=playbook,
            step_type=step_type,
            title=title,
            description=enriched,
            source_url=source_url,
            sort_order=order,
        )

    return playbook
