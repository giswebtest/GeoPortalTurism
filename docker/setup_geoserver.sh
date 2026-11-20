#!/usr/bin/env bash
# ──────────────────────────────────────────────────────
#  GeoServer setup via REST API
#  Idempotent: safe to run multiple times
# ──────────────────────────────────────────────────────
set -euo pipefail

GS_URL="${GS_URL:-http://localhost:8080/geoserver}"
GS_USER="${GS_USER:-admin}"
GS_PASS="${GS_PASS:-geoserver}"
AUTH="${GS_USER}:${GS_PASS}"

WS="geoportal"
DS="postgis_store"

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-geodjango1}"
DB_USER="${DB_USER:-postgres}"
DB_PASS="${DB_PASS:-postgres}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GeoServer Configuration Script"
echo "  URL: ${GS_URL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Helper ──
gs_exists() {
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" -u "${AUTH}" "$1")
    [ "$code" = "200" ]
}

# ─────────────────────────
# 1. Workspace
# ─────────────────────────
echo ""
echo "▶ [1/3] Workspace: ${WS}"
if gs_exists "${GS_URL}/rest/workspaces/${WS}.json"; then
    echo "  ✔ Already exists"
else
    curl -sf -u "${AUTH}" \
        -X POST "${GS_URL}/rest/workspaces" \
        -H "Content-Type: application/json" \
        -d "{\"workspace\":{\"name\":\"${WS}\"}}"
    echo "  ✔ Created"
fi

# ─────────────────────────
# 2. PostGIS DataStore
# ─────────────────────────
echo ""
echo "▶ [2/3] DataStore: ${DS}"
if gs_exists "${GS_URL}/rest/workspaces/${WS}/datastores/${DS}.json"; then
    echo "  ✔ Already exists"
else
    curl -sf -u "${AUTH}" \
        -X POST "${GS_URL}/rest/workspaces/${WS}/datastores" \
        -H "Content-Type: application/json" \
        -d '{
  "dataStore": {
    "name": "'"${DS}"'",
    "type": "PostGIS",
    "connectionParameters": {
      "entry": [
        {"@key": "host",     "$": "'"${DB_HOST}"'"},
        {"@key": "port",     "$": "'"${DB_PORT}"'"},
        {"@key": "database", "$": "'"${DB_NAME}"'"},
        {"@key": "user",     "$": "'"${DB_USER}"'"},
        {"@key": "passwd",   "$": "'"${DB_PASS}"'"},
        {"@key": "dbtype",   "$": "postgis"},
        {"@key": "schema",   "$": "public"},
        {"@key": "Expose primary keys", "$": "true"},
        {"@key": "Loose bbox", "$": "true"},
        {"@key": "Estimated extends", "$": "true"},
        {"@key": "encode functions", "$": "true"}
      ]
    }
  }
}'
    echo "  ✔ Created"
fi

# ─────────────────────────
# 3. Publish Feature Types
# ─────────────────────────
publish_layer() {
    local TABLE=$1
    local TITLE=$2
    local SRS="${3:-EPSG:4326}"

    echo ""
    echo "  ▸ Layer: ${TABLE} (${TITLE})"
    if gs_exists "${GS_URL}/rest/workspaces/${WS}/datastores/${DS}/featuretypes/${TABLE}.json"; then
        echo "    ✔ Already published"
    else
        curl -sf -u "${AUTH}" \
            -X POST "${GS_URL}/rest/workspaces/${WS}/datastores/${DS}/featuretypes" \
            -H "Content-Type: application/json" \
            -d '{
  "featureType": {
    "name": "'"${TABLE}"'",
    "nativeName": "'"${TABLE}"'",
    "title": "'"${TITLE}"'",
    "srs": "'"${SRS}"'",
    "nativeCRS": "'"${SRS}"'",
    "enabled": true,
    "nativeBoundingBox": {
      "minx": -180, "maxx": 180,
      "miny": -90,  "maxy": 90,
      "crs": "'"${SRS}"'"
    },
    "latLonBoundingBox": {
      "minx": -180, "maxx": 180,
      "miny": -90,  "maxy": 90,
      "crs": "'"${SRS}"'"
    }
  }
}'
        echo "    ✔ Published"
    fi
}

echo ""
echo "▶ [3/3] Publishing Feature Types"
publish_layer "maps_location"       "Туристичні локації"
publish_layer "maps_route"          "Туристичні маршрути"
publish_layer "maps_countrypolygon" "Полігони країн"

# ─────────────────────────
# 4. Raster Layers (GeoTIFF)
# ─────────────────────────
RASTER_FILE="/opt/geoserver_data/ОпорнийПлан.tif"
CS_NAME="oporniy_plan"
COV_TITLE="Опорний план"

echo ""
echo "▶ [4/5] Raster CoverageStore: ${CS_NAME}"
if gs_exists "${GS_URL}/rest/workspaces/${WS}/coveragestores/${CS_NAME}.json"; then
    echo "  ✔ CoverageStore already exists"
else
    curl -sf -u "${AUTH}" \
        -X POST "${GS_URL}/rest/workspaces/${WS}/coveragestores" \
        -H "Content-Type: application/json" \
        -d '{
  "coverageStore": {
    "name": "'"${CS_NAME}"'",
    "type": "GeoTIFF",
    "enabled": true,
    "workspace": { "name": "'"${WS}"'" },
    "url": "file://'"${RASTER_FILE}"'"
  }
}'
    echo "  ✔ Created"
fi

echo ""
echo "  ▸ Coverage: ${CS_NAME} (${COV_TITLE})"
if gs_exists "${GS_URL}/rest/workspaces/${WS}/coveragestores/${CS_NAME}/coverages/${CS_NAME}.json"; then
    echo "    ✔ Already published"
else
    curl -sf -u "${AUTH}" \
        -X POST "${GS_URL}/rest/workspaces/${WS}/coveragestores/${CS_NAME}/coverages" \
        -H "Content-Type: application/json" \
        -d '{
  "coverage": {
    "name": "'"${CS_NAME}"'",
    "nativeCoverageName": "ОпорнийПлан",
    "nativeName": "ОпорнийПлан",
    "title": "'"${COV_TITLE}"'",
    "enabled": true,
    "projectionPolicy": "REPROJECT_TO_DECLARED"
  }
}'
    echo "    ✔ Published"
fi

# WMTS caching for raster layer
echo ""
echo "  ▸ WMTS cache: ${WS}:${CS_NAME}"
curl -sf -u "${AUTH}" \
    -X PUT "${GS_URL}/gwc/rest/layers/${WS}:${CS_NAME}" \
    -H "Content-Type: application/xml" \
    -d '<GeoServerLayer>
  <enabled>true</enabled>
  <name>'"${WS}:${CS_NAME}"'</name>
  <mimeFormats>
    <string>image/png</string>
    <string>image/jpeg</string>
  </mimeFormats>
  <gridSubsets>
    <gridSubset>
      <gridSetName>EPSG:4326</gridSetName>
      <zoomStart>0</zoomStart><zoomStop>18</zoomStop>
    </gridSubset>
    <gridSubset>
      <gridSetName>EPSG:900913</gridSetName>
      <zoomStart>0</zoomStart><zoomStop>18</zoomStop>
    </gridSubset>
  </gridSubsets>
</GeoServerLayer>'
echo "    ✔ WMTS configured"

# ─────────────────────────
# 5. Verify Services
# ─────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_service() {
    local NAME=$1
    local URL=$2
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "${URL}")
    if [ "$code" = "200" ]; then
        echo "  ✔ ${NAME}: OK (HTTP ${code})"
    else
        echo "  ✘ ${NAME}: FAILED (HTTP ${code})"
    fi
}

check_service "WMS"  "${GS_URL}/${WS}/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
check_service "WFS"  "${GS_URL}/ows?service=WFS&request=GetCapabilities"
check_service "WMTS" "${GS_URL}/gwc/service/wmts?REQUEST=GetCapabilities"

echo ""
echo "🎉 Done! GeoServer is configured."
echo ""
echo "Service URLs (via nginx on port 80):"
echo "  WMS:  http://localhost/geoserver/${WS}/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
echo "  WFS:  http://localhost/geoserver/ows?service=WFS&request=GetCapabilities"
echo "  WMTS: http://localhost/geoserver/gwc/service/wmts?REQUEST=GetCapabilities"
echo ""
