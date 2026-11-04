{# 残す建物と、その代表点が入る小地域・町字。building を作る途中の表で、公開しない。

   都市のデータは 3 次メッシュ単位で作られていて、境のメッシュには隣の市区町村の建物も入る。
   同じ建物は同じ gml_id で複数の都市のデータに出てくるので 1 つにする。また、隣の市区町村が
   自分のデータを持っているときは（年度が違うと gml_id も違う）、その市区町村のデータの建物だけを使う。 #}

with city_owner as (
    {# 建物の city_code を自分のデータとして持つ source の city_code。政令市の建物は区のコード
       （札幌市中央区は 01101）を持つが、source は市のコード（01100）なので、区は市のものとして見る。
       政令市のコードは 3 桁目が 1 で 5 桁目が 0（01100、14130 など）、区はそのあとの 29 個のうちにある #}
    select c.city_code, max(s.city_code) as owner_code
    from (select distinct city_code from {{ ref('building_point') }}) c
    join {{ ref('source') }} s
        on s.city_code = c.city_code
        or (s.city_code like '__1_0'
            and left(c.city_code, 2) = left(s.city_code, 2)
            and try_cast(c.city_code as integer) between s.city_code::integer + 1 and s.city_code::integer + 29)
    group by c.city_code
),

own as (
    select p.*
    from {{ ref('building_point') }} p
    left join city_owner o using (city_code)
    where o.owner_code is null or o.owner_code = p.source_city_code
    qualify row_number() over (
        partition by p.gml_id
        order by (o.owner_code = p.source_city_code) desc nulls last, p.source_year desc, p.source_city_code
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
