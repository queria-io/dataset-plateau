{# 町字の形（Queria の japan_address_code データセット）。建物の代表点に町字を付けるのに読む。
   building_town の post_hook の SQL から読むので、ephemeral ではなくメモリの中のビューにする #}
{{ config(materialized='view', database='memory', schema='main') }}

select machiaza_id, lg_code, geometry
from japan_address_code.main.town_shape
