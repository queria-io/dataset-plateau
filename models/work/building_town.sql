{# 建物の代表点が入る町字。building を作る途中の表で、公開しない。
   町字の形（japan_address_code の town_shape）は全国で頂点が 3 億あり、1 回で当てると
   手元のメモリに収まらないので、都道府県ごとに分けて足す（post_hook）。 #}

{%- set hooks = [] -%}
{%- for pref in range(1, 48) -%}
{%- set code = "%02d" % pref -%}
{%- do hooks.append(
    "insert into {{ this }} select p.source_city_code, p.gml_id, min(t.machiaza_id), arg_min(t.lg_code, t.machiaza_id)
     from {{ ref('building_point') }} p
     join japan_address_code.main.town_shape t on st_contains(t.geometry, p.point)
     where left(coalesce(p.city_code, p.source_city_code), 2) = '" ~ code ~ "' and left(t.lg_code, 2) = '" ~ code ~ "'
     group by p.source_city_code, p.gml_id"
) -%}
{%- endfor -%}
{{ config(post_hook=hooks) }}

-- depends_on: {{ ref('building_point') }}
select
    cast(null as varchar) as source_city_code,
    cast(null as varchar) as gml_id,
    cast(null as varchar) as machiaza_id,
    cast(null as varchar) as lg_code
limit 0
