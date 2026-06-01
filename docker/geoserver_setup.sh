#!/bin/bash
# GeoServer initial setup — workspace, PostGIS datastore, layers, WMTS
# Запуск: bash docker/geoserver_setup.sh
# Передумова: GeoServer запущений на localhost:8080

GS="http://localhost:8080/geoserver"
AUTH="admin:geoserver"
WS="geoportal"
DS="geodjango1"

wait_geoserver() {
  echo "Очікую GeoServer..."
  for i in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$GS/web/")
    [ "$code" = "200" ] || [ "$code" = "302" ] && echo "GeoServer готовий." && return
    sleep 5
  done
  echo "GeoServer не відповів за 150 сек." && exit 1
}

wait_geoserver

echo ""
echo "=== 1. Workspace ==="
curl -s -u $AUTH -X POST "$GS/rest/workspaces" \
  -H "Content-Type: application/json" \
  -d "{\"workspace\":{\"name\":\"$WS\"}}" \
  -o /dev/null -w "  workspace $WS: HTTP %{http_code}\n"

echo ""
echo "=== 2. PostGIS Datastore ==="
curl -s -u $AUTH -X POST "$GS/rest/workspaces/$WS/datastores" \
  -H "Content-Type: application/json" \
  -d "{\"dataStore\":{\"name\":\"$DS\",\"type\":\"PostGIS\",\"enabled\":true}}" \
  -o /dev/null -w "  datastore $DS: HTTP %{http_code}\n"

curl -s -u $AUTH -X PUT "$GS/rest/workspaces/$WS/datastores/$DS" \
  -H "Content-Type: application/xml" \
  -d "<dataStore>
        <name>$DS</name>
        <enabled>true</enabled>
        <connectionParameters>
          <entry key=\"host\">host.docker.internal</entry>
          <entry key=\"port\">5432</entry>
          <entry key=\"database\">geodjango1</entry>
          <entry key=\"user\">postgres</entry>
          <entry key=\"passwd\">postgres</entry>
          <entry key=\"dbtype\">postgis</entry>
          <entry key=\"schema\">public</entry>
          <entry key=\"Expose primary keys\">true</entry>
        </connectionParameters>
      </dataStore>" \
  -o /dev/null -w "  connection params: HTTP %{http_code}\n"

echo ""
echo "=== 3. Feature Types (шари) ==="
declare -A TITLES=(
  [maps_location]="Туристичні локації"
  [maps_route]="Туристичні маршрути"
  [maps_countrypolygon]="Полігони регіонів"
  [hystory_ob]="Пам'ятки культури"
  [ivfrankdist]="Райони Івано-Франківської обл."
)

for table in maps_location maps_route maps_countrypolygon hystory_ob ivfrankdist; do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -u $AUTH -X POST "$GS/rest/workspaces/$WS/datastores/$DS/featuretypes" \
    -H "Content-Type: application/xml" \
    -d "<featureType>
          <name>${table}</name>
          <nativeName>${table}</nativeName>
          <title>${TITLES[$table]}</title>
          <srs>EPSG:4326</srs>
          <projectionPolicy>FORCE_DECLARED</projectionPolicy>
          <enabled>true</enabled>
          <nativeBoundingBox>
            <minx>22.15</minx><maxx>26.16</maxx>
            <miny>47.73</miny><maxy>48.75</maxy>
            <crs>EPSG:4326</crs>
          </nativeBoundingBox>
          <latLonBoundingBox>
            <minx>22.15</minx><maxx>26.16</maxx>
            <miny>47.73</miny><maxy>48.75</maxy>
            <crs>EPSG:4326</crs>
          </latLonBoundingBox>
        </featureType>")
  [ "$code" = "201" ] && echo "  ✓ $table" || echo "  ✗ $table HTTP $code"
done

echo ""
echo "=== 4. WMTS (GeoWebCache) ==="
for layer in maps_location maps_route maps_countrypolygon hystory_ob ivfrankdist; do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -u $AUTH -X PUT "$GS/gwc/rest/layers/$WS:${layer}" \
    -H "Content-Type: application/xml" \
    -d "<GeoServerLayer>
          <enabled>true</enabled>
          <name>$WS:${layer}</name>
          <mimeFormats>
            <string>image/png</string>
            <string>image/jpeg</string>
            <string>image/png8</string>
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
        </GeoServerLayer>")
  [ "$code" = "200" ] && echo "  ✓ $layer WMTS" || echo "  ✗ $layer HTTP $code"
done

echo ""
echo "=== Готово ==="
echo "WMS:  $GS/$WS/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
echo "WFS:  $GS/$WS/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities"
echo "WMTS: $GS/gwc/service/wmts?REQUEST=GetCapabilities"
