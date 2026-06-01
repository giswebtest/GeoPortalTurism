"""
Django management command — export ISO 19115:2003/19139 metadata XML.

Використання:
    python manage.py export_metadata
    python manage.py export_metadata --collection locations
    python manage.py export_metadata --out /app/metadata
    python manage.py export_metadata --base-url https://mysite.com
"""
import os
from django.core.management.base import BaseCommand
from maps.iso19115 import generate_xml, collection_ids


class Command(BaseCommand):
    help = 'Generates ISO 19115:2003/19139 XML metadata files for OGC/НІГД collections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--collection', '-c',
            default=None,
            help='Конкретна колекція (locations, routes, hystory-ob, districts). '
                 'За замовчуванням — всі.',
        )
        parser.add_argument(
            '--out', '-o',
            default='metadata',
            help='Директорія для збереження XML файлів (default: ./metadata)',
        )
        parser.add_argument(
            '--base-url', '-b',
            default='http://localhost:8000',
            help='Базова URL адреса порталу (default: http://localhost:8000)',
        )

    def handle(self, *args, **options):
        target    = options['collection']
        out_dir   = options['out']
        base_url  = options['base_url'].rstrip('/')
        ids       = [target] if target else collection_ids()

        os.makedirs(out_dir, exist_ok=True)
        self.stdout.write(f'Output directory: {os.path.abspath(out_dir)}\n')

        for cid in ids:
            try:
                xml = generate_xml(cid, base_url)
                filename = os.path.join(out_dir, f'metadata_{cid}.xml')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(xml)
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {cid:20s} → {filename}')
                )
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f'  ✗ {cid}: {e}')
                )

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово. {len(ids)} файл(ів) записано до "{out_dir}/"'
        ))
