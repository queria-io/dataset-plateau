{# 取り込んだ都市の CityGML。1 行が 1 都市。 #}

select *
from {{ ref('stg_sources') }}
order by city_code
