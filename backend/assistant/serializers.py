from rest_framework import serializers

from .models import AssistantQuery, Citation, EvidenceDocument


class EvidenceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceDocument
        fields = (
            "id",
            "title",
            "source_url",
            "country_code",
            "category",
            "published_at",
        )


class CitationSerializer(serializers.ModelSerializer):
    evidence = EvidenceDocumentSerializer(read_only=True)

    class Meta:
        model = Citation
        fields = ("id", "evidence", "excerpt", "relevance_score")


class AssistantQuerySerializer(serializers.ModelSerializer):
    citations = CitationSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantQuery
        fields = (
            "id",
            "question",
            "answer",
            "has_sufficient_evidence",
            "refusal_reason",
            "retrieval_method",
            "citations",
            "created_at",
        )


class AskSerializer(serializers.Serializer):
    question = serializers.CharField()
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True)
