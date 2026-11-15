{# PLATEAU の建物。pipelines/convert.py が都市ごとに書いた Parquet（1 棟 1 行）をそのまま読む #}

select *
from read_parquet('data/plateau/building/*.parquet')
