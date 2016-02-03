from collections import namedtuple

from django.db.models import Lookup, Field


@Field.register_lookup
class JsonDataContains(Lookup):
    """
    Custom lookup for json in the form of:

    data->key->language ILIKE '%my-search-term%'

    Will be made more generic if required. Use the namedtuple below to pass
    the arguments.

    This can't be used right now to replace the raw sql query on
    questionnaire.utils.query_questionnaires_for_link as Lateral joins are not
    yet nicely handled in django: https://code.djangoproject.com/ticket/25590

    Lookup as of now:

    qs = Questionnaire.objects.filter(
        # force left outer join
        Q(questionnairemembership__questionnaire_id__isnull=True) |
        Q(questionnairemembership__questionnaire_id__isnull=False)
    ).filter(
        questionnaireconfiguration__configuration__code='sample'
    ).filter(
        status=4
    ).filter(
        reduce(operator.or_, json_filters)
    ).annotate(max_id=Max('id'))

    Don't use this for user input, as data isn't escaped properly!
    """
    lookup_name = 'json_contains'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        qs = "{lhs}{json_lookup} ILIKE '%%{term}%%'".format(
            lhs=lhs,
            json_lookup=self.get_key_structure(rhs_params[0].json_keys),
            term=rhs_params[0].term,
        )
        return qs, []

    def key_structure(self, keys):
        """
        Return a string that can be used for the lookup in form
        ->{key}-->{last_key}

        Args:
            keys: list of keys

        Returns:
            string
        """
        key_structure = ''
        for key in keys[:1]:
            key_structure += '->{key}'.format(key)
        else:
            key_structure += '-->{key}'.format(keys[-1])
        return key_structure


JsonLookup = namedtuple('JsonLookup', 'questiongroup json_keys value')
