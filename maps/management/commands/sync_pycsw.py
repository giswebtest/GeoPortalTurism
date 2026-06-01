"""
Django management command — синхронізація ISO 19115 метаданих з PyCSW.

Використання:
    python manage.py sync_pycsw
    python manage.py sync_pycsw --url http://localhost:8001/csw
    python manage.py sync_pycsw --base-url https://mysite.com
"""
import re
import requests
from django.core.management.base import BaseCommand
from maps.iso19115 import generate_xml, collection_ids

CSW_NS  = 'http://www.opengis.net/cat/csw/2.0.2'
GMD_NS  = 'http://www.isotc211.org/2005/gmd'


def _transaction(csw_url: str, action: str, body: str) -> requests.Response:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<csw:Transaction
    xmlns:csw="{CSW_NS}"
    xmlns:gmd="{GMD_NS}"
    service="CSW" version="2.0.2">
  <csw:{action}>
    {body}
  </csw:{action}>
</csw:Transaction>"""
    return requests.post(
        csw_url,
        data=xml.encode('utf-8'),
        headers={'Content-Type': 'application/xml'},
        timeout=30,
    )


def _delete_by_id(csw_url: str, file_id: str) -> requests.Response:
    """Видаляє запис за fileIdentifier через CSW Transaction Delete."""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<csw:Transaction
    xmlns:csw="{CSW_NS}"
    xmlns:ogc="http://www.opengis.net/ogc"
    service="CSW" version="2.0.2">
  <csw:Delete typeName="gmd:MD_Metadata">
    <csw:Constraint version="1.1.0">
      <ogc:Filter>
        <ogc:PropertyIsEqualTo>
          <ogc:PropertyName>dc:identifier</ogc:PropertyName>
          <ogc:Literal>{file_id}</ogc:Literal>
        </ogc:PropertyIsEqualTo>
      </ogc:Filter>
    </csw:Constraint>
  </csw:Delete>
</csw:Transaction>"""
    return requests.post(
        csw_url,
        data=xml.encode('utf-8'),
        headers={'Content-Type': 'application/xml'},
        timeout=30,
    )


def _strip_xml_decl(xml: str) -> str:
    """Прибирає <?xml ...?> декларацію — вона не потрібна всередині Transaction."""
    return re.sub(r'<\?xml[^?]*\?>\s*', '', xml, count=1)


class Command(BaseCommand):
    help = 'Синхронізує ISO 19115 метадані з PyCSW (CSW 2.0.2 Transaction)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url', '-u',
            default='http://localhost:8001/csw',
            help='CSW endpoint (default: http://localhost:8001/csw)',
        )
        parser.add_argument(
            '--base-url', '-b',
            default='http://localhost:8000',
            help='Базова URL порталу для посилань у метаданих',
        )
        parser.add_argument(
            '--collection', '-c',
            default=None,
            help='Конкретна колекція. За замовчуванням — всі.',
        )

    def handle(self, *args, **options):
        csw_url  = options['url']
        base_url = options['base_url'].rstrip('/')
        target   = options['collection']
        ids      = [target] if target else collection_ids()

        # Перевірка доступності PyCSW
        self.stdout.write(f'CSW endpoint: {csw_url}')
        try:
            r = requests.get(
                f'{csw_url}?SERVICE=CSW&VERSION=2.0.2&REQUEST=GetCapabilities',
                timeout=10,
            )
            if r.status_code != 200:
                self.stderr.write(self.style.ERROR(
                    f'PyCSW недоступний: HTTP {r.status_code}. '
                    f'Запусти: docker compose up -d pycsw'
                ))
                return
        except requests.ConnectionError:
            self.stderr.write(self.style.ERROR(
                f'Не вдалося підключитися до {csw_url}. '
                f'Запусти: docker compose up -d pycsw'
            ))
            return

        self.stdout.write(self.style.SUCCESS('PyCSW доступний ✓'))
        self.stdout.write('')

        ok = 0
        for cid in ids:
            self.stdout.write(f'  {cid}')

            # 1. Генерація ISO 19115 XML
            xml = generate_xml(cid, base_url)
            xml_body = _strip_xml_decl(xml)

            # 2. Видалення старого запису (якщо є)
            from maps.iso19115 import _DATASETS
            file_id = _DATASETS[cid]['file_id']
            _delete_by_id(csw_url, file_id)

            # 3. Вставка нового запису
            resp = _transaction(csw_url, 'Insert', xml_body)

            if resp.status_code == 200 and 'ExceptionReport' not in resp.text:
                self.stdout.write(self.style.SUCCESS(f'    ✓ вставлено'))
                ok += 1
            else:
                err = resp.text[:300] if resp.text else f'HTTP {resp.status_code}'
                self.stderr.write(self.style.ERROR(f'    ✗ {err}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Готово: {ok}/{len(ids)} записів синхронізовано.'
        ))
        self.stdout.write(
            f'\nПеревір: {csw_url}'
            f'?SERVICE=CSW&VERSION=2.0.2&REQUEST=GetRecords'
            f'&TYPENAMES=gmd:MD_Metadata&outputSchema={GMD_NS}&resultType=results'
        )
