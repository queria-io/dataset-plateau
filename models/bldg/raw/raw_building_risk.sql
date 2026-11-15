{# 建物ごとの災害リスク。pipelines/convert.py が都市ごとに書いた Parquet をそのまま読む #}

select *
from read_parquet('data/plateau/building_risk/*.parquet')
