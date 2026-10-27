from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()

def format_indian_number(val):
    if val is None or val == '':
        return '0.00'
    try:
        dec = Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return str(val)

    is_negative = dec < 0
    dec = abs(dec)
    s = f"{dec:.2f}"
    parts = s.split('.')
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted_int = ','.join(groups) + ',' + last3

    res = f"{formatted_int}.{decimal_part}"
    return f"-{res}" if is_negative else res

@register.filter(name='inr')
def inr(val):
    """
    Formats a number into Indian currency format with Rupee symbol.
    Example: 8877840.46 -> ₹88,77,840.46
    """
    if val is None or val == '':
        return '₹0.00'
    formatted = format_indian_number(val)
    if formatted.startswith('-'):
        return f"-₹{formatted[1:]}"
    return f"₹{formatted}"

@register.filter(name='inr_num')
def inr_num(val):
    """
    Formats a number into Indian number format without currency symbol.
    Example: 8877840.46 -> 88,77,840.46
    """
    return format_indian_number(val)

@register.filter(name='pct_val')
def pct_val(val):
    """
    Formats a percentage cleanly with 2 decimal places.
    """
    if val is None or val == '':
        return '0.00%'
    try:
        dec = Decimal(str(val))
        return f"{dec:.2f}%"
    except (InvalidOperation, ValueError, TypeError):
        return f"{val}%"
