{# 建物ごとの災害リスク。1 行が 1 棟 × 1 想定（河川・想定規模ごと）。
   building に残った建物の分だけ、そのデータの行を使う。 #}

select
    r.gml_id,
    b.city_code,
    b.lg_code,
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
from read_parquet('data/plateau/building_risk/*.parquet') r
join {{ ref('building') }} b on b.gml_id = r.gml_id and b.source_city_code = r.source_city_code
order by b.city_code, r.gml_id, r.hazard, r.description, r.scale
