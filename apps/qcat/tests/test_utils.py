from qcat.tests import TestCase
from qcat.utils import (
    find_dict_in_list,
    is_empty_list_of_dicts,
)


class IsEmptyListOfDictsTest(TestCase):

    def test_returns_false_if_not_empty(self):
        is_empty = is_empty_list_of_dicts([{"foo": "bar"}])
        self.assertFalse(is_empty)

    def test_returns_true_if_empty(self):
        is_empty = is_empty_list_of_dicts([{"foo": ""}])
        self.assertTrue(is_empty)

    def test_returns_true_if_empty_with_None(self):
        is_empty = is_empty_list_of_dicts([{"foo": None}])
        self.assertTrue(is_empty)

    def test_returns_true_if_false_as_value(self):
        is_empty = is_empty_list_of_dicts([{"foo": False}])
        self.assertFalse(is_empty)

    def test_returns_true_if_empty_list(self):
        is_empty = is_empty_list_of_dicts([{"foo": []}])
        self.assertTrue(is_empty)

    def test_returns_False_if_not_empty_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": "bar"}}])
        self.assertFalse(is_empty)

    def test_returns_true_if_empty_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": ""}}])
        self.assertTrue(is_empty)

    def test_returns_true_if_None_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": None}}])
        self.assertTrue(is_empty)

    def test_returns_true_if_false_as_value_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": False}}])
        self.assertFalse(is_empty)


class FindDictInListTest(TestCase):

    def setUp(self):
        self.l = [
            {
                "foo": "bar",
                "bar": "faz"
            }, {
                "foo": "faz"
            }, {
                "faz": "foo"
            }, {
                "foo": "bar"
            }
        ]

    def test_finds_dict(self):
        retu = find_dict_in_list(self.l, 'foo', 'faz')
        self.assertEqual(retu, {"foo": "faz"})

    def test_returns_not_found(self):
        retu = find_dict_in_list(self.l, 'foo', 'foo')
        self.assertEqual(retu, {})

    def test_returns_custom_not_found(self):
        retu = find_dict_in_list(self.l, 'foo', 'foo', not_found="foo")
        self.assertEqual(retu, "foo")

    def test_returns_first_occurence(self):
        retu = find_dict_in_list(self.l, 'foo', 'bar')
        self.assertEqual(retu, {"foo": "bar", "bar": "faz"})

    def test_returns_not_found_if_value_None(self):
        retu = find_dict_in_list(self.l, 'foo', None)
        self.assertEqual(retu, {})
