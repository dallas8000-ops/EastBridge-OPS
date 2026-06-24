from decimal import Decimal, InvalidOperation

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from accounts.permissions import get_user_organization
from ingestion.services.retrieval import best_excerpt, search_evidence, synthesize_answer, tokenize

from .llm import generate_grounded_answer

from .models import AssistantQuery, Citation
from .serializers import AskSerializer, AssistantQuerySerializer


def _clamp_relevance_score(score: Decimal) -> Decimal:
    """Keep scores within DecimalField bounds and avoid SQLite read errors."""
    try:
        value = Decimal(str(score)).quantize(Decimal("0.0001"))
    except InvalidOperation:
        return Decimal("0")
    max_score = Decimal("999999.9999")
    if value > max_score:
        return max_score
    if value < Decimal("0"):
        return Decimal("0")
    return value


class AssistantQueryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AssistantQuerySerializer

    def get_queryset(self):
        qs = AssistantQuery.objects.prefetch_related("citations__evidence")
        org = get_user_organization(self.request)
        if org and self.request.user.is_authenticated:
            return qs.filter(organization=org)
        return qs.none() if self.request.user.is_authenticated else qs[:0]

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def ask(self, request):
        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]
        country_code = serializer.validated_data.get("country_code", "").upper()

        matches, method = search_evidence(question, country_code=country_code, limit=5)
        org = get_user_organization(request)

        query = AssistantQuery.objects.create(
            question=question,
            organization=org,
            retrieval_method=method,
        )

        if not matches:
            query.has_sufficient_evidence = False
            query.refusal_reason = (
                "Insufficient source evidence to answer. "
                "No matching official notices or trade procedures were found. "
                "Run `python manage.py ingest --target all` and `python manage.py embed_evidence`."
            )
            query.save()
            return Response(AssistantQuerySerializer(query).data, status=status.HTTP_200_OK)

        tokens = tokenize(question)
        for doc, score in matches:
            Citation.objects.create(
                query=query,
                evidence=doc,
                excerpt=best_excerpt(doc.content, tokens),
                relevance_score=_clamp_relevance_score(score),
            )

        llm_answer = generate_grounded_answer(question, matches)
        query.answer = llm_answer or synthesize_answer(question, matches)
        if llm_answer:
            method = f"{method}+llm"
            query.retrieval_method = method
        query.has_sufficient_evidence = True
        query.save()

        return Response(AssistantQuerySerializer(query).data, status=status.HTTP_201_CREATED)
