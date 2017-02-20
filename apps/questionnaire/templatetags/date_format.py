import datetime
from django.template.defaultfilters import date as _date, capfirst

from django import template

register = template.Library()


@register.filter
def month_name(month_number, date_format='b'):
    """
    Return the name of a month based on its number (1 = January, 12 = December).

    Args:
        month_number: The number of the month.
        date_format: Optional format, defaults to 'b' (3 letters). Other option:
          'B' (full month name)

        (see https://docs.djangoproject.com/en/1.8/ref/templates/builtins/#date)

    Returns:
        String.
    """
    try:
        month_number = month_number.strip()
    except AttributeError:
        pass
    try:
        month_number = int(month_number)
    except ValueError:
        return month_number
    date = datetime.date(year=2016, month=month_number, day=1)
    return capfirst(_date(date, date_format))


@register.filter
def check_month(month_number, month_list):
    """
    Check if a month (as integer) is in a list of selected months (as strings).

    Args:
        month_number: The number of the month.
        month_list: A list of months as defined by the configuration.

    Returns:
        Bool.
    """
    month_map = {
        1: 'january',
        2: 'february',
        3: 'march',
        4: 'april',
        5: 'may',
        6: 'june',
        7: 'july',
        8: 'august',
        9: 'september',
        10: 'october',
        11: 'november',
        12: 'december',
    }
    return month_map.get(month_number, '') in month_list
