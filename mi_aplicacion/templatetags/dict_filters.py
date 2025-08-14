# mi_aplicacion/templatetags/dict_filters.py
from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    return d.get(key)

@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})
