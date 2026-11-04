{# PLATEAU の建物。1 行が 1 棟。pipelines/convert.py が都市ごとに書いた Parquet から、
   work.building_key が残すと決めた建物だけを取る。小地域と町字は外形の上の代表点が入るもの。 #}

{{ config(pre_hook=[
    "SET preserve_insertion_order = false",
]) }}

select
    b.gml_id,
    b.building_id,
    k.city_code,
    {{ local_government_code('k.city_code') }} as lg_code,
    left(k.city_code, 2) as prefecture_code,
    b.class,
    b.usage,
    b.usage_code,
    b.detailed_usage,
    -- 原典は不明を -9999・9999 などの値で書く（製品仕様書の「不明」）。数として集計されないように NULL にする
    if(b.measured_height in (-9999, 9999), null, b.measured_height) as measured_height,
    nullif(b.storeys_above_ground, 9999) as storeys_above_ground,
    nullif(b.storeys_below_ground, 9999) as storeys_below_ground,
    if(b.year_of_construction in (1, 9999, 99999), null, b.year_of_construction) as year_of_construction,
    nullif(b.total_floor_area, -9999) as total_floor_area,
    nullif(b.footprint_area, -9999) as footprint_area,
    b.structure,
    b.fireproof_structure,
    nullif(b.survey_year, 1) as survey_year,
    b.address,
    b.real_estate_id,
    b.land_real_estate_ids,
    b.lod,
    b.attributes,
    k.small_area_code,
    k.machiaza_id,
    k.lng,
    k.lat,
    {{ jis_mesh3('k.lng', 'k.lat') }} as mesh3,
    st_makevalid(st_geomfromwkb(b.geometry)) as geometry,
    b.source_city_code,
    k.source_year,
    b.file
from read_parquet('data/plateau/building/*.parquet') b
join {{ ref('building_key') }} k using (source_city_code, gml_id)
order by k.city_code, mesh3, b.gml_id
