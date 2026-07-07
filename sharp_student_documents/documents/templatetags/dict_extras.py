# documents/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Get dictionary value in template"""
    if isinstance(d, dict):
        return d.get(key, "")
    return ""

@register.simple_tag(takes_context=True)
def param_replace(context, page):
    """Replace page parameter in URL while preserving other parameters"""
    request = context['request']
    params = request.GET.copy()
    params['page'] = page
    return params.urlencode()

