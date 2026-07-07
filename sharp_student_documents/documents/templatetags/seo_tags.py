from urllib.parse import urlencode

from django import template
from django.templatetags.static import static


register = template.Library()


@register.simple_tag(takes_context=True)
def canonical_url(context, keep_params=""):
    request = context.get("request")
    if request is None:
        return ""

    allowed = {param.strip() for param in keep_params.split(",") if param.strip()}
    query_params = request.GET.copy()

    if allowed:
        filtered = [(key, value) for key, values in query_params.lists() if key in allowed for value in values]
        query_string = urlencode(filtered, doseq=True)
    else:
        query_string = ""

    url = request.build_absolute_uri(request.path)
    return f"{url}?{query_string}" if query_string else url


@register.simple_tag(takes_context=True)
def absolute_static(context, asset_path):
    request = context.get("request")
    static_path = static(asset_path)
    if request is None:
        return static_path
    return request.build_absolute_uri(static_path)


@register.simple_tag(takes_context=True)
def absolute_url(context, url):
    request = context.get("request")
    if not url:
        return ""
    if str(url).startswith(("http://", "https://")) or request is None:
        return url
    return request.build_absolute_uri(url)
