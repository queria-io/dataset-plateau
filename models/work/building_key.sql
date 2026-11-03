{# 残す建物と、その代表点が入る小地域・町字。building を作る途中の表で、公開しない。

   都市のデータは 3 次メッシュ単位で作られていて、境のメッシュには隣の市区町村の建物も入る。
   同じ建物は同じ gml_id で複数の都市のデータに出てくるので 1 つにする。また、隣の市区町村が
   自分のデータを持っているときは（年度が違うと gml_id も違う）、その市区町村のデータの建物だけを使う。 #}

with own as (
    select p.*
    from {{ ref('building_point') }} p
    where p.city_code is null
        or p.city_code = p.source_city_code
        or p.city_code not in (select city_code from {{ ref('source') }})
    qualify row_number() over (
        partition by p.gml_id
        order by (p.city_code = p.source_city_code) desc nulls last, p.source_year desc, p.source_city_code
    ) = 1
),

small_area as (
    select o.gml_id, min(s.key_code) as small_area_code
    from own o
    join e_stat.boundary.small_area s on st_contains(s.geometry, o.point)
    group by o.gml_id
),

town as (
    select source_city_code, gml_id, machiaza_id, lg_code as town_lg_code from {{ ref('building_town') }}
)

select
    o.source_city_code,
    o.gml_id,
    o.source_year,
    coalesce(o.city_code, left(t.town_lg_code, 5)) as city_code,
    sa.small_area_code,
    t.machiaza_id,
    st_x(o.point) as lng,
    st_y(o.point) as lat
from own o
left join small_area sa using (gml_id)
left join town t using (source_city_code, gml_id)
