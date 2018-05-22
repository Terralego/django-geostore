import datetime
import re

from django.core import exceptions
from django.db.models import DateField
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _


class DateFieldYearLess(DateField):
    base_year = 1970
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid date format. It must be"
                     " in MM-DD format."),
        'invalid_date': _("'%(value)s' value has the correct format (MM-DD) "
                          "but it is an invalid date."),
    }

    def from_db_value(self, value, expression, connection, context):
        return f"{value:%m-%d}"

    def to_python(self, value):
        if isinstance(value, datetime.date):
            value = f'{value:%m-%d}'
        if not re.search(r'^\d{2}-\d{2}$', value):
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

        normalized_date = parse_date(f'1970-{value}')
        return super().to_python(normalized_date)
