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
def param_replace(context, page=None, **kwargs):
    """Rebuild the current query string while updating one or more parameters.

    - ``{% param_replace page_obj.next_page_number %}`` keeps every existing
      filter and just swaps ``page`` for pagination links.
    - ``{% param_replace document_type='exam' %}`` keeps the current search/filters
      and adds/replaces ``document_type`` (resetting to page 1).
    """
    request = context['request']
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == '':
            params.pop(key, None)
        else:
            params[key] = value
    params['page'] = page if page is not None else 1
    return params.urlencode()

