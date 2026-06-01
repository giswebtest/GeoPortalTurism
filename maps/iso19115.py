"""
ISO 19115:2003 / 19139 metadata XML generator
Відповідає вимогам INSPIRE та НІГД України.

Використання:
    from maps.iso19115 import generate_xml
    xml = generate_xml('locations', 'https://mysite.com')
"""
from datetime import date
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace
from xml.dom.minidom import parseString

# ── Namespace URIs ────────────────────────────────────────────────────────────
GMD   = 'http://www.isotc211.org/2005/gmd'
GCO   = 'http://www.isotc211.org/2005/gco'
XSI   = 'http://www.w3.org/2001/XMLSchema-instance'

register_namespace('gmd',  GMD)
register_namespace('gco',  GCO)
register_namespace('xsi',  XSI)

_CL = ('http://standards.iso.org/ittf/PubliclyAvailableStandards/'
       'ISO_19139_Schemas/resources/codelist/ML_gmxCodelists.xml')

# ── Shorthand builders ────────────────────────────────────────────────────────
def _g(tag):  return f'{{{GMD}}}{tag}'
def _c(tag):  return f'{{{GCO}}}{tag}'

def _cs(parent, text):
    el = SubElement(parent, _c('CharacterString'))
    el.text = str(text)

def _dec(parent, val):
    el = SubElement(parent, _c('Decimal'))
    el.text = str(val)

def _dt(parent, val):
    el = SubElement(parent, _c('DateTime'))
    el.text = val if isinstance(val, str) else val.isoformat()

def _cl(parent, tag, value, base=None):
    el = SubElement(parent, _g(tag))
    el.set('codeList', f'{base or _CL}#{tag}')
    el.set('codeListValue', value)
    el.text = value
    return el


# ── Stable dataset UUIDs — не змінювати після першої публікації! ──────────────
_DATASETS = {
    'locations': {
        'file_id':  '7a4e2c1b-3f8d-4a9e-b5c6-1d2e3f4a5b6c',
        'title':    'Туристичні локації Івано-Франківської та суміжних областей',
        'abstract': (
            "Набір геопросторових точкових об'єктів — туристичні локації "
            "Івано-Франківської та суміжних областей України. "
            "Атрибути: назва, опис, категорія, регіон, фотоматеріали. "
            "Геометрія PointField у системі координат WGS-84 (EPSG:4326)."
        ),
        'topics':   ['society', 'location'],
        'lineage':  (
            "Дані введені адміністраторами порталу та імпортовані з OpenStreetMap. "
            "Координати отримані засобами геокодування та польового збору. "
            "Масовий імпорт через GeoJSON (LocationAdmin)."
        ),
    },
    'routes': {
        'file_id':  '8b5f3d2a-4e9f-5b0a-c6d7-2e3f4a5b6c7d',
        'title':    'Туристичні маршрути Івано-Франківської та суміжних областей',
        'abstract': (
            "Набір лінійних геопросторових об'єктів — затверджені туристичні маршрути. "
            "Атрибути: назва, опис, складність (easy/medium/hard), "
            "відстань (км), тривалість (хв). "
            "Геометрія LineStringField у WGS-84 (EPSG:4326). "
            "Відстань розраховується автоматично через PostGIS ST_Length."
        ),
        'topics':   ['society', 'transportation'],
        'lineage':  (
            "Маршрути побудовані через OSRM (Open Source Routing Machine) "
            "та імпортовані з GPX-файлів польового збору."
        ),
    },
    'hystory-ob': {
        'file_id':  '9c6a4e3b-5f0a-6c1b-d7e8-3f4a5b6c7d8e',
        'title':    "Пам'ятки культурної спадщини Івано-Франківської області",
        'abstract': (
            "Набір геопросторових точкових об'єктів — об'єкти культурної "
            "та архітектурної спадщини. Таблиця hystory_ob — 62 об'єкти. "
            "Атрибути: назва, опис. Геометрія 3D PointField у WGS-84 (EPSG:4326)."
        ),
        'topics':   ['society', 'structure'],
        'lineage':  (
            "Дані отримані з реєстру об'єктів культурної спадщини. "
            "Існуюча PostGIS-таблиця (managed=False). "
            "Потребує синхронізації з реєстром МКІП (перспектива)."
        ),
    },
    'districts': {
        'file_id':  'ad7b5f4c-6a1b-7d2c-e8f9-4a5b6c7d8e9f',
        'title':    'Адміністративні райони Івано-Франківської області',
        'abstract': (
            "Набір полігональних геопросторових об'єктів — адміністративно-"
            "територіальний поділ Івано-Франківської області на райони. "
            "Таблиця IvFrankDist. Геометрія MultiPolygon у WGS-84 (EPSG:4326)."
        ),
        'topics':   ['boundaries', 'location'],
        'lineage':  (
            "Межі адміністративних районів отримані з офіційних геодезичних даних "
            "та уточнені за OpenStreetMap."
        ),
    },
}

_BBOX     = {'west': 22.15, 'east': 26.16, 'south': 47.73, 'north': 48.75}
_ORG      = 'Геопортал туристичних ресурсів Івано-Франківської області'
_EMAIL    = 'admin@geoportal.if.ua'


# ── Main generator ────────────────────────────────────────────────────────────

def generate_xml(collection_id: str, base_url: str = 'http://localhost:8000') -> str:
    """
    Генерує ISO 19115:2003/19139 XML для вказаної колекції.
    Повертає UTF-8 рядок з pretty-printed XML.
    """
    if collection_id not in _DATASETS:
        raise KeyError(f'Unknown collection: {collection_id}')

    cfg      = _DATASETS[collection_id]
    today    = date.today().isoformat() + 'T00:00:00'
    items_url = f'{base_url}/ogc/collections/{collection_id}/items/'

    # ── Root element ──────────────────────────────────────────
    root = Element(_g('MD_Metadata'))
    root.set(
        f'{{{XSI}}}schemaLocation',
        f'{GMD} http://schemas.opengis.net/iso/19139/20060504/gmd/gmd.xsd',
    )

    # fileIdentifier
    fi = SubElement(root, _g('fileIdentifier'));  _cs(fi, cfg['file_id'])

    # language
    _cl(SubElement(root, _g('language')), 'LanguageCode', 'ukr',
        'http://www.loc.gov/standards/iso639-2/')

    # characterSet
    _cl(SubElement(root, _g('characterSet')), 'MD_CharacterSetCode', 'utf8')

    # hierarchyLevel
    _cl(SubElement(root, _g('hierarchyLevel')), 'MD_ScopeCode', 'dataset')

    # ── Contact ───────────────────────────────────────────────
    contact  = SubElement(root, _g('contact'))
    rp       = SubElement(contact, _g('CI_ResponsibleParty'))
    org      = SubElement(rp, _g('organisationName'));  _cs(org, _ORG)
    ci       = SubElement(SubElement(rp, _g('contactInfo')), _g('CI_Contact'))
    addr     = SubElement(SubElement(ci, _g('address')), _g('CI_Address'))
    mail     = SubElement(addr, _g('electronicMailAddress'));  _cs(mail, _EMAIL)
    _cl(SubElement(rp, _g('role')), 'CI_RoleCode', 'pointOfContact')

    # dateStamp
    _dt(SubElement(root, _g('dateStamp')), today)

    # metadataStandardName / Version
    msn = SubElement(root, _g('metadataStandardName'));  _cs(msn, 'ISO 19115:2003/19139')
    msv = SubElement(root, _g('metadataStandardVersion'));  _cs(msv, '1.0')

    # referenceSystemInfo → EPSG:4326
    rs_id  = SubElement(SubElement(SubElement(SubElement(
        root, _g('referenceSystemInfo')),
        _g('MD_ReferenceSystem')),
        _g('referenceSystemIdentifier')),
        _g('RS_Identifier'))
    code   = SubElement(rs_id, _g('code'));       _cs(code, 'EPSG:4326')
    space  = SubElement(rs_id, _g('codeSpace'));  _cs(space, 'http://www.epsg-registry.org/')

    # ── identificationInfo ────────────────────────────────────
    di = SubElement(SubElement(root, _g('identificationInfo')), _g('MD_DataIdentification'))

    # citation
    ci_cit  = SubElement(SubElement(di, _g('citation')), _g('CI_Citation'))
    title   = SubElement(ci_cit, _g('title'));  _cs(title, cfg['title'])
    ci_date = SubElement(SubElement(ci_cit, _g('date')), _g('CI_Date'))
    _dt(SubElement(ci_date, _g('date')), today)
    _cl(SubElement(ci_date, _g('dateType')), 'CI_DateTypeCode', 'publication')

    # abstract
    _cs(SubElement(di, _g('abstract')), cfg['abstract'])

    # status
    _cl(SubElement(di, _g('status')), 'MD_ProgressCode', 'onGoing')

    # pointOfContact
    poc_rp = SubElement(SubElement(di, _g('pointOfContact')), _g('CI_ResponsibleParty'))
    _cs(SubElement(poc_rp, _g('organisationName')), _ORG)
    _cl(SubElement(poc_rp, _g('role')), 'CI_RoleCode', 'owner')

    # resourceMaintenance
    maint = SubElement(SubElement(
        SubElement(di, _g('resourceMaintenance')),
        _g('MD_MaintenanceInformation')),
        _g('maintenanceAndUpdateFrequency'))
    _cl(maint, 'MD_MaintenanceFrequencyCode', 'asNeeded')

    # constraints — CC BY 4.0
    lc = SubElement(SubElement(di, _g('resourceConstraints')), _g('MD_LegalConstraints'))
    _cs(SubElement(lc, _g('useLimitation')),
        'CC BY 4.0 — Creative Commons Attribution 4.0 International. '
        'https://creativecommons.org/licenses/by/4.0/')
    _cl(SubElement(lc, _g('accessConstraints')), 'MD_RestrictionCode', 'license')
    _cl(SubElement(lc, _g('useConstraints')),    'MD_RestrictionCode', 'license')

    # spatialRepresentationType
    _cl(SubElement(di, _g('spatialRepresentationType')),
        'MD_SpatialRepresentationTypeCode', 'vector')

    # topicCategory (one element per topic)
    for topic in cfg['topics']:
        tc = SubElement(di, _g('topicCategory'))
        SubElement(tc, _g('MD_TopicCategoryCode')).text = topic

    # language / characterSet
    _cl(SubElement(di, _g('language')), 'LanguageCode', 'ukr',
        'http://www.loc.gov/standards/iso639-2/')
    _cl(SubElement(di, _g('characterSet')), 'MD_CharacterSetCode', 'utf8')

    # extent → bounding box
    geo_bb = SubElement(SubElement(SubElement(
        SubElement(di, _g('extent')),
        _g('EX_Extent')),
        _g('geographicElement')),
        _g('EX_GeographicBoundingBox'))
    _dec(SubElement(geo_bb, _g('westBoundLongitude')), _BBOX['west'])
    _dec(SubElement(geo_bb, _g('eastBoundLongitude')), _BBOX['east'])
    _dec(SubElement(geo_bb, _g('southBoundLatitude')), _BBOX['south'])
    _dec(SubElement(geo_bb, _g('northBoundLatitude')), _BBOX['north'])

    # ── distributionInfo ──────────────────────────────────────
    md_dist = SubElement(SubElement(root, _g('distributionInfo')), _g('MD_Distribution'))

    for fmt_name, fmt_ver in (('GeoJSON', 'RFC 7946'), ('OGC API Features', '1.0')):
        mdf = SubElement(SubElement(md_dist, _g('distributionFormat')), _g('MD_Format'))
        _cs(SubElement(mdf, _g('name')),    fmt_name)
        _cs(SubElement(mdf, _g('version')), fmt_ver)

    mdto   = SubElement(SubElement(md_dist, _g('transferOptions')), _g('MD_DigitalTransferOptions'))
    ci_or  = SubElement(SubElement(mdto, _g('onLine')), _g('CI_OnlineResource'))
    SubElement(SubElement(ci_or, _g('linkage')), _g('URL')).text = items_url
    _cs(SubElement(ci_or, _g('protocol')), 'OGC:OGC API - Features - 1.0')
    _cs(SubElement(ci_or, _g('name')),     cfg['title'])
    _cl(SubElement(ci_or, _g('function')), 'CI_OnLineFunctionCode', 'download')

    # ── dataQualityInfo ───────────────────────────────────────
    dq = SubElement(SubElement(root, _g('dataQualityInfo')), _g('DQ_DataQuality'))
    _cl(SubElement(SubElement(dq, _g('scope')), _g('DQ_Scope')), 'MD_ScopeCode', 'dataset')

    # Lineage statement  ← звідки дані
    lin_stmt = SubElement(
        SubElement(SubElement(dq, _g('lineage')), _g('LI_Lineage')),
        _g('statement'),
    )
    _cs(lin_stmt, cfg['lineage'])

    # ── Serialize → pretty XML ────────────────────────────────
    raw = tostring(root, encoding='unicode')
    dom = parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}')
    return dom.toprettyxml(indent='  ', encoding='UTF-8').decode('utf-8')


def collection_ids():
    return list(_DATASETS.keys())
