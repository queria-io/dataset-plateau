{# 建物ごとの代表点。building を作る途中の表で、公開しない（メモリの中のデータベースに置く）。
   外形を持ったまま全国 2,900 万行を並べ替えると手元のメモリに収まらないので、
   重なりの整理と小地域・町字の当てはめは、この点の表の上でやる。 #}

select
    b.source_city_code,
    b.gml_id,
    b.city_code,
    s.year as source_year,
    st_pointonsurface(st_makevalid(st_geomfromwkb(b.geometry))) as point
from read_parquet('data/plateau/building/*.parquet') b
join {{ ref('source') }} s on s.city_code = b.source_city_code
where b.geometry is not null
