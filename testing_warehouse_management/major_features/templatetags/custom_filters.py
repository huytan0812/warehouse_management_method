from django import template

register = template.Library()

@register.filter(is_safe=True)
def multiply(value, arg):
    if value and arg:
        return value * arg
        