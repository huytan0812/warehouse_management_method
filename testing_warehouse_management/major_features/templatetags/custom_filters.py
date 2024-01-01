from django import template

register = template.Library()

@register.filter(is_safe=True)
def subtract(value, arg):
    if value and arg:
        return value - arg
    return 0

@register.filter(is_safe=True)
def multiply(value, arg):
    if value and arg:
        return value * arg
    return 0

@register.filter(is_safe=True)
def division(value, arg):
    if value and arg:
        return value / arg
    return 0
    
@register.filter(is_safe=True)
def round_float(value, n_digits):
    if value and n_digits:
        return round(value, n_digits)
    return 0

@register.filter(is_safe=True)
def to_percentage(value, arg):
    if value and arg:
        div = value / arg
        percentage = div * 100
        return percentage
    return 0