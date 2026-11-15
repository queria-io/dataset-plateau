{# 取り込んだ都市の CityGML。1 行が 1 都市。列名を変更し、地方公共団体コードを付ける #}

select
    city_code,
    {{ local_government_code('city_code') }} as lg_code,
    pref_code as prefecture_code,
    pref as prefecture_name,
    city as city_name,
    year,
    spec,
    file,
    page_url,
    zip_url,
    size
from {{ ref('raw_sources') }}
