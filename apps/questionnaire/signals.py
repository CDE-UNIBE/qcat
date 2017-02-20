"""
A notification requires a single sender (person responsible for the action). This information is not on the
Questionnaire model. A more concise (although more hacky way) would be to handle this in the Questionnaires save
method. Sending a signal each time results in more code, but should be more explicit. Please note that the
'providing_args' are not validated, but are just documentation.
"""
import django.dispatch

create_questionnaire = django.dispatch.Signal(providing_args=["questionnaire", "user"])
delete_questionnaire = django.dispatch.Signal(providing_args=["questionnaire", "user"])
change_status = django.dispatch.Signal(providing_args=["questionnaire", "user"])
change_member = django.dispatch.Signal(providing_args=["questionnaire", "user", "affected", "role"])
change_questionnaire_data = django.dispatch.Signal(providing_args=["questionnaire", "user"])
