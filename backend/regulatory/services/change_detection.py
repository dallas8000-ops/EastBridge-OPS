"""Advanced change detection and analysis for regulatory updates."""

import logging
from datetime import timedelta
from difflib import SequenceMatcher
from django.db.models import Q
from django.utils import timezone

from regulatory.models import RegulatoryChange
from core.models import DataSource

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detect and analyze changes in regulatory content."""
    
    def __init__(self):
        self.similarity_threshold = 0.7  # 70% similarity threshold
        
    def detect_content_changes(self, old_content: str, new_content: str) -> dict:
        """Detect changes between two versions of content."""
        if not old_content or not new_content:
            return {"has_changes": True, "change_type": "new_content"}
        
        similarity = SequenceMatcher(None, old_content, new_content).ratio()
        
        if similarity >= self.similarity_threshold:
            return {
                "has_changes": False,
                "similarity": similarity,
                "change_type": "minor"
            }
        
        # Analyze the type of changes
        change_analysis = {
            "has_changes": True,
            "similarity": similarity,
            "change_type": self._classify_change_type(old_content, new_content),
            "added_text": self._get_added_text(old_content, new_content),
            "removed_text": self._get_removed_text(old_content, new_content),
        }
        
        return change_analysis
    
    def _classify_change_type(self, old_content: str, new_content: str) -> str:
        """Classify the type of change based on content analysis."""
        old_lower = old_content.lower()
        new_lower = new_content.lower()
        
        # Check for specific legal change indicators
        legal_keywords = [
            "amendment", "amended", "repealed", "repeal", "revised", "revision",
            "new section", "added section", "deleted section", "removed section",
            "substituted", "replacement", "inserted", "enacted", "assented"
        ]
        
        for keyword in legal_keywords:
            if keyword in new_lower and keyword not in old_lower:
                return "legislative_amendment"
        
        # Check for numeric changes (rates, fees, deadlines)
        if self._has_numeric_changes(old_content, new_content):
            return "numeric_change"
        
        # Check for date changes
        if self._has_date_changes(old_content, new_content):
            return "date_change"
        
        # Check for structural changes
        if len(new_content) > len(old_content) * 1.5:
            return "significant_expansion"
        elif len(new_content) < len(old_content) * 0.5:
            return "significant_reduction"
        
        return "content_modification"
    
    def _has_numeric_changes(self, old: str, new: str) -> bool:
        """Check if there are significant numeric changes."""
        import re
        old_numbers = set(re.findall(r'\d+\.?\d*', old))
        new_numbers = set(re.findall(r'\d+\.?\d*', new))
        
        # If more than 50% of numbers changed, consider it numeric change
        if not old_numbers:
            return len(new_numbers) > 0
        
        changed_ratio = len(old_numbers.symmetric_difference(new_numbers)) / len(old_numbers)
        return changed_ratio > 0.5
    
    def _has_date_changes(self, old: str, new: str) -> bool:
        """Check if there are date-related changes."""
        import re
        date_pattern = r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}'
        
        old_dates = set(re.findall(date_pattern, old, re.IGNORECASE))
        new_dates = set(re.findall(date_pattern, new, re.IGNORECASE))
        
        return old_dates != new_dates
    
    def _get_added_text(self, old: str, new: str) -> str:
        """Extract text that was added."""
        # Simple approach: find sentences in new but not in old
        old_sentences = set(old.split('.'))
        new_sentences = new.split('.')
        
        added = [s.strip() for s in new_sentences if s.strip() and s.strip() not in old_sentences]
        return '. '.join(added[:3]) if added else ""  # Return first 3 added sentences
    
    def _get_removed_text(self, old: str, new: str) -> str:
        """Extract text that was removed."""
        new_sentences = set(new.split('.'))
        old_sentences = old.split('.')
        
        removed = [s.strip() for s in old_sentences if s.strip() and s.strip() not in new_sentences]
        return '. '.join(removed[:3]) if removed else ""  # Return first 3 removed sentences


def detect_urgent_changes(hours: int = 24) -> list[RegulatoryChange]:
    """Detect urgent regulatory changes from the last N hours."""
    cutoff = timezone.now() - timedelta(hours=hours)
    
    urgent_changes = RegulatoryChange.objects.filter(
        detected_at__gte=cutoff,
        risk_level__in=[
            RegulatoryChange.RiskLevel.HIGH,
            RegulatoryChange.RiskLevel.CRITICAL
        ]
    ).select_related('country', 'source').order_by('-detected_at')
    
    return urgent_changes


def analyze_regulatory_trends(days: int = 30) -> dict:
    """Analyze regulatory trends over time."""
    cutoff = timezone.now() - timedelta(days=days)
    
    changes = RegulatoryChange.objects.filter(detected_at__gte=cutoff)
    
    # Category breakdown
    category_breakdown = {}
    for change in changes:
        category = change.category
        if category not in category_breakdown:
            category_breakdown[category] = 0
        category_breakdown[category] += 1
    
    # Risk level breakdown
    risk_breakdown = {}
    for change in changes:
        risk = change.risk_level
        if risk not in risk_breakdown:
            risk_breakdown[risk] = 0
        risk_breakdown[risk] += 1
    
    # Country breakdown
    country_breakdown = {}
    for change in changes:
        country = change.country.code
        if country not in country_breakdown:
            country_breakdown[country] = 0
        country_breakdown[country] += 1
    
    # Source activity
    source_activity = {}
    for change in changes:
        source = change.source.name
        if source not in source_activity:
            source_activity[source] = 0
        source_activity[source] += 1
    
    return {
        "total_changes": changes.count(),
        "category_breakdown": category_breakdown,
        "risk_breakdown": risk_breakdown,
        "country_breakdown": country_breakdown,
        "source_activity": source_activity,
        "period_days": days,
    }


def detect_related_changes(change: RegulatoryChange) -> list[RegulatoryChange]:
    """Detect related regulatory changes based on content similarity."""
    detector = ChangeDetector()
    
    # Get changes from the same country and category in the last 7 days
    cutoff = timezone.now() - timedelta(days=7)
    potential_related = RegulatoryChange.objects.filter(
        country=change.country,
        category=change.category,
        detected_at__gte=cutoff
    ).exclude(id=change.id)
    
    related_changes = []
    for potential in potential_related:
        similarity = SequenceMatcher(
            None, 
            change.summary + " " + change.business_impact,
            potential.summary + " " + potential.business_impact
        ).ratio()
        
        if similarity >= 0.5:  # 50% similarity threshold for related changes
            related_changes.append({
                "change": potential,
                "similarity": similarity,
            })
    
    # Sort by similarity
    related_changes.sort(key=lambda x: x["similarity"], reverse=True)
    
    return [item["change"] for item in related_changes[:5]]


def generate_change_summary(change: RegulatoryChange) -> dict:
    """Generate a comprehensive summary of a regulatory change."""
    detector = ChangeDetector()
    
    # Detect related changes
    related = detect_related_changes(change)
    
    # Analyze urgency
    urgency_factors = []
    if change.risk_level in [RegulatoryChange.RiskLevel.HIGH, RegulatoryChange.RiskLevel.CRITICAL]:
        urgency_factors.append("high_risk_level")
    
    if "urgent" in change.title.lower() or "immediate" in change.title.lower():
        urgency_factors.append("urgent_keywords")
    
    if change.detected_at >= timezone.now() - timedelta(hours=48):
        urgency_factors.append("recent_detection")
    
    summary = {
        "change": change,
        "urgency_factors": urgency_factors,
        "related_changes": related,
        "recommended_actions": _generate_recommendations(change),
        "stakeholder_impact": _assess_stakeholder_impact(change),
    }
    
    return summary


def _generate_recommendations(change: RegulatoryChange) -> list[str]:
    """Generate recommended actions based on change characteristics."""
    recommendations = []
    
    if change.category == RegulatoryChange.Category.TAX:
        recommendations.extend([
            "Review tax registration requirements",
            "Update VAT/import duty calculations",
            "Consult with local tax advisor",
            "Update internal tax compliance procedures"
        ])
    elif change.category == RegulatoryChange.Category.CUSTOMS:
        recommendations.extend([
            "Review import/export documentation requirements",
            "Update customs clearance procedures",
            "Verify tariff classifications",
            "Train logistics team on new requirements"
        ])
    elif change.category == RegulatoryChange.Category.INVESTMENT:
        recommendations.extend([
            "Review investment license requirements",
            "Update foreign investment procedures",
            "Consult with investment authority",
            "Review shareholder structure compliance"
        ])
    
    if change.risk_level == RegulatoryChange.RiskLevel.CRITICAL:
        recommendations.insert(0, "IMMEDIATE ACTION REQUIRED: Assign senior compliance lead")
    elif change.risk_level == RegulatoryChange.RiskLevel.HIGH:
        recommendations.insert(0, "HIGH PRIORITY: Review within 48 hours")
    
    return recommendations


def _assess_stakeholder_impact(change: RegulatoryChange) -> dict:
    """Assess impact on different stakeholders."""
    impact = {
        "operations": "low",
        "finance": "low", 
        "legal": "low",
        "hr": "low",
        "it": "low"
    }
    
    content = (change.title + " " + change.summary + " " + change.business_impact).lower()
    
    if any(term in content for term in ["tax", "vat", "duty", "revenue", "financial"]):
        impact["finance"] = "high"
    
    if any(term in content for term in ["compliance", "legal", "regulation", "law"]):
        impact["legal"] = "high"
    
    if any(term in content for term in ["operations", "process", "procedure", "workflow"]):
        impact["operations"] = "medium"
    
    if any(term in content for term in ["employment", "labor", "worker", "staff"]):
        impact["hr"] = "medium"
    
    if any(term in content for term in ["data", "digital", "system", "technology"]):
        impact["it"] = "medium"
    
    return impact