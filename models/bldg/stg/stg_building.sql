{# PLATEAU の建物。1 行が 1 都市のデータの 1 棟。外形を形として読み、不明を表す値を NULL にする #}

select
    source_city_code,
    gml_id,
    building_id,
    city_code,
    class,
    usage,
    usage_code,
    detailed_usage,
    -- 原典は不明を -9999・9999 などの値で書く（製品仕様書の「不明」）。数として集計されないように NULL にする
    if(measured_height in (-9999, 9999), null, measured_height) as measured_height,
    nullif(storeys_above_ground, 9999) as storeys_above_ground,
    nullif(storeys_below_ground, 9999) as storeys_below_ground,
    if(year_of_construction in (1, 9999, 99999), null, year_of_construction) as year_of_construction,
    nullif(total_floor_area, -9999) as total_floor_area,
    nullif(footprint_area, -9999) as footprint_area,
    structure,
    fireproof_structure,
    nullif(survey_year, 1) as survey_year,
    address,
    real_estate_id,
    land_real_estate_ids,
    lod,
    attributes,
    st_makevalid(st_geomfromwkb(geometry)) as geometry,
    file
from {{ ref('raw_building') }}
