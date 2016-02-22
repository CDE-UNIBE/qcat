from rest_framework import filters
from rest_framework import viewsets

from .serializers import QuestionnaireSerializer
from ..models import Questionnaire


class QuestionnaireViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and detail view for questionnaires.

    Filters can be passed in the url, e.g. /en/api/v1/questionnaire/?version=1

    Following fields can be filtered for:
    - version
    """
    serializer_class = QuestionnaireSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filter_fields = ('version', )

    def get_queryset(self):
        """
        Filter valid questionnaires; Status "3" is public.
        """
        return Questionnaire.with_status.public().filter(blocked=None)
