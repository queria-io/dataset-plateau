{# 建物ごとの災害リスク。1 行が 1 都市のデータの 1 棟 × 1 想定 #}

select
    source_city_code,
    gml_id,
    hazard,
    description,
    admin_type,
    scale,
    rank,
    rank_code,
    rank_org,
    depth,
    duration,
    area_type
from {{ ref('raw_building_risk') }}
