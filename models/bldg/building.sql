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
    b.measured_height,
    b.storeys_above_ground,
    b.storeys_below_ground,
    b.year_of_construction,
    b.total_floor_area,
    b.footprint_area,
    b.structure,
    b.fireproof_structure,
    b.survey_year,
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
