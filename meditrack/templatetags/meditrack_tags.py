from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rupiah(value):
    try:
        return (
            format(Decimal(value), ",.2f")
            .replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )
    except (InvalidOperation, TypeError, ValueError):
        return value
