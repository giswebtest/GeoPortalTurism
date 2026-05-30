import re
from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def extract_url(description):
    if not description:
        return ''
    match = re.search(r'https?://[^\s"<>\]]+', description)
    return match.group(0) if match else ''


@register.simple_tag
def description_link(description):
    """Повертає 'Див. ↗' як посилання якщо опис містить URL, інакше — скорочений текст."""
    if not description:
        return ''
    url_match = re.search(r'https?://[^\s"<>\]]+', description)
    if url_match:
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" '
            'style="color:#1a6fa8;font-size:0.82rem;text-decoration:none;'
            'border-bottom:1px dotted #1a6fa8;">Див. ↗</a>',
            url_match.group(0)
        )
    plain = re.sub(r'<[^>]+>', '', description).strip()
    if not plain:
        return ''
    words = plain.split()
    truncated = ' '.join(words[:12])
    if len(words) > 12:
        truncated += '…'
    return format_html('<span style="font-size:0.82rem;color:#555;">{}</span>', truncated)
