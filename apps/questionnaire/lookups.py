from django.db.models import Lookup, Field


@Field.register_lookup
class DataLookup(Lookup):
    """
    Lookup for values inside the data JSON of questionnaires. This is based on a
    text search inside the JSON of the questiongroup. It is therefore not
    extremely fast and also quite fuzzy!

    A dictionary with the following lookup parameters is required:

        "lookup_by": string, required. Either "string" or "key_value". Either
        look for a string (case insensitive) or look for a specific key/value
        pair (case sensitive).

        "questiongroup": string, required. The keyword of the questiongroup
          which is looked up.

        "value": string, required. The value which is looked for.

         "key": string, required when using "lookup_by": "key_value". Can
           optionally be used for "lookup_by": "string" to narrow the search.

        "lookup_in_list": boolean, defaults to False. By default, only the first
          element of a data list is searched. If set to True, the entire data
          list of the questiongroup is searched.

    Use as:
        Questionnaire.objects.filter(data__qs_data=lookup_params)

        where lookup_params is a dict containing the lookup parameters.
    """
    lookup_name = 'qs_data'

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)

        # Check general format of params
        if len(rhs_params) != 1 or not isinstance(rhs_params[0], dict):
            raise NotImplementedError('RHS params must be exactly 1 dict.')
        lookup_params = rhs_params[0]

        # Check required params
        value = lookup_params.get('value')
        if value is None:
            raise Exception('Value must be provided.')
        questiongroup = lookup_params.get('questiongroup')
        if questiongroup is None:
            raise Exception('Questiongroup must be provided.')

        # Additional params
        key = lookup_params.get('key')
        lookup_in_list = lookup_params.get('lookup_in_list', False)

        lookup_by = lookup_params.get('lookup_by')
        if lookup_by == 'string':
            # Lookup for simple string search.
            if key is not None:
                params = '%"{}":%{}%'.format(key, value)
            else:
                params = '%{}%'.format(value)
            query_operator = 'ILIKE'

        elif lookup_by == 'key_value':
            # Lookup for exact key/value matches.
            if key is None:
                raise Exception(
                    'Key must be provided when using lookup_by "key_value".')
            params = '%"{}": "{}"%'.format(key, value)
            query_operator = 'LIKE'

        else:
            raise NotImplementedError(
                'Unknown lookup_by "{}".'.format(lookup_by))

        if lookup_in_list is True:
            element_accessor = " ->> '{}'".format(questiongroup)
        else:
            element_accessor = " -> '{}' ->> 0".format(questiongroup)

        return " ".join([lhs, element_accessor, query_operator, rhs]), [params]
