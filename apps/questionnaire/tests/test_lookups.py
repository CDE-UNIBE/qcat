from model_mommy import mommy

from qcat.tests import TestCase
from questionnaire.models import Questionnaire


class QuestionnaireLookupsTest(TestCase):

    def setUp(self):
        self.bread = mommy.make(
            Questionnaire,
            data={
                "qg_name": [
                    {
                        "name": {"en": "BREAD", "fr": "baguette"},
                        "local_name": {"en": "loaf", "fr": "mini"}
                    },
                    {
                        "name": {"en": "Something else"}
                    }
                ],
                "qg_country": [
                    {
                        "country": "country_FRA"
                    }
                ]
            }
        )
        self.peas = mommy.make(
            Questionnaire,
            data={
                "qg_name": [
                    {
                        "name": {"en": "peas", "it": "pisello"},
                        "local_name": {"en": "mini beans"}
                    }
                ],
            }
        )
        self.chickpeas = mommy.make(
            Questionnaire,
            data={
                "qg_name": [
                    {
                        "name": {"en": "grams", "fr": "Pois chiches"},
                        "local_name": {"en": "chickpeas"}
                    }
                ],
                "qg_country": [
                    {
                        "country": "country_IND"
                    }
                ]
            }
        )

    def test_qs_data_lookup_string_name_en(self):
        lookup_params = {
            'questiongroup': 'qg_name',
            'value': 'bread',
            'lookup_by': 'string',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.first(), self.bread)
        self.assertEquals(qs.count(), 1)

    def test_qs_data_lookup_string_name_fr(self):
        lookup_params = {
            'questiongroup': 'qg_name',
            'value': 'baguette',
            'lookup_by': 'string',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.first(), self.bread)
        self.assertEquals(qs.count(), 1)

    def test_qs_data_lookup_string_local_name_en(self):
        lookup_params = {
            'questiongroup': 'qg_name',
            'value': 'loaf',
            'lookup_by': 'string',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.first(), self.bread)
        self.assertEquals(qs.count(), 1)

    def test_qs_data_lookup_string_many(self):
        lookup_params = {
            'questiongroup': 'qg_name',
            'value': 'mini',
            'lookup_by': 'string',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.count(), 2)

    def test_qs_data_lookup_string_key(self):
        # Lookup by string WITHOUT a key
        lookup_params = {
            'questiongroup': 'qg_name',
            'value': 'peas',
            'lookup_by': 'string',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.count(), 2)
        # Lookup by string WITH a key
        lookup_params = {
            'questiongroup': 'qg_name',
            'key': 'local_name',
            'value': 'peas',
            'lookup_by': 'string',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.count(), 1)

    def test_qs_data_lookup_string_list(self):
        # Lookup only the first element (default)
        lookup_params = {
            'questiongroup': 'qg_name',
            'value': 'something',
            'lookup_by': 'string',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.count(), 0)
        # Lookup all elements
        lookup_params = {
            'questiongroup': 'qg_name',
            'value': 'something',
            'lookup_by': 'string',
            'lookup_in_list': True,
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.count(), 1)

    def test_qs_data_lookup_key_value(self):
        lookup_params = {
            'questiongroup': 'qg_country',
            'key': 'country',
            'value': 'country_IND',
            'lookup_by': 'key_value',
        }
        qs = Questionnaire.objects.filter(data__qs_data=lookup_params)
        self.assertEquals(qs.count(), 1)
