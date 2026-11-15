{# 建物ごとの災害リスク。1 行が 1 棟 × 1 想定（河川・想定規模ごと）。
   building_key が残すと決めた建物の分だけ、そのデータの行を使う。 #}

select
    r.gml_id,
    k.city_code,
    {{ local_government_code('k.city_code') }} as lg_code,
    r.hazard,
    r.description,
    r.admin_type,
    r.scale,
    r.rank,
    r.rank_code,
    r.rank_org,
    r.depth,
    r.duration,
    r.area_type
from {{ ref('stg_building_risk') }} r
join {{ ref('building_key') }} k on k.gml_id = r.gml_id and k.source_city_code = r.source_city_code
order by k.city_code, r.gml_id, r.hazard, r.description, r.scale
