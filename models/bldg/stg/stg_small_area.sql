{# 小地域の境界（Queria の e_stat データセット）。建物の代表点に小地域を付けるのに読む #}

select key_code, geometry
from e_stat.boundary.small_area
