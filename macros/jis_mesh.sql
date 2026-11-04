{# 経度・緯度から JIS X 0410 の地域メッシュコードを出す。
   1 次メッシュは緯度 40 分 × 経度 1 度（約 80km 四方）、2 次メッシュはそれを縦横 8 等分（約 10km 四方）。 #}

{% macro jis_mesh1(lon, lat) -%}
    (floor(({{ lat }}) * 1.5)::integer * 100 + floor(({{ lon }}) - 100)::integer)
{%- endmacro %}

{% macro jis_mesh2(lon, lat) -%}
    ({{ jis_mesh1(lon, lat) }} * 100
        + floor((({{ lat }}) * 1.5 - floor(({{ lat }}) * 1.5)) * 8)::integer * 10
        + floor((({{ lon }}) - floor({{ lon }})) * 8)::integer)
{%- endmacro %}

{# 3 次メッシュ（基準地域メッシュ、約 1km 四方）は 2 次メッシュを縦横 10 等分したもの。
   緯度 × 12 が 2 次メッシュの行の通し番号になる（1.5 × 8）。 #}

{% macro jis_mesh3(lon, lat) -%}
    ({{ jis_mesh2(lon, lat) }} * 100
        + floor((({{ lat }}) * 12 - floor(({{ lat }}) * 12)) * 10)::integer * 10
        + floor((({{ lon }}) * 8 - floor(({{ lon }}) * 8)) * 10)::integer)
{%- endmacro %}
