from dataclasses import dataclass


@dataclass
class ParsedProcedure:
    external_id: str
    title: str
    url: str
    summary: str
    activity_type: str
    steps: list[dict]
    estimated_days: int | None
    estimated_cost: str
