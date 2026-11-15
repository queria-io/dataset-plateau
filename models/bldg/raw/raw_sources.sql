{# 取り込んだ都市の CityGML。1 行が 1 都市。pipelines/sources.py が data/plateau/sources.ndjson に書いたものをそのまま読む #}

select *
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
