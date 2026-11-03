{# 取り込んだ都市の CityGML。1 行が 1 都市。pipelines/sources.py が data/plateau/sources.ndjson に書く。 #}

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
from read_json(
    'data/plateau/sources.ndjson',
    format = 'newline_delimited',
    columns = {
        city_code: 'VARCHAR',
        pref_code: 'VARCHAR',
        pref: 'VARCHAR',
        city: 'VARCHAR',
        year: 'INTEGER',
        spec: 'VARCHAR',
        file: 'VARCHAR',
        zip_url: 'VARCHAR',
        size: 'BIGINT',
        page_url: 'VARCHAR'
    }
)
order by city_code
