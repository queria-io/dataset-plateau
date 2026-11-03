"""都市の CityGML の zip から建物を読み、1 棟 1 行の Parquet にする。

zip は HTTP の Range で読み、建物（udx/bldg/*.gml）と符号表（codelists/*.xml）だけを取る。
写真の貼り付けや地形は読まない。メンバーを 1 つずつ取ると要求の数が数千になって遅いので、
zip の中で近くに並ぶメンバーをまとめて 1 回の要求で取る。

- 外形は LOD0（lod0FootPrint か lod0RoofEdge）の面。無ければ LOD1 の立体のいちばん低い水平な面
- 座標は緯度・経度・高さの順（EPSG:6697）なので、経度・緯度の 2 次元に直す
- 用途などの符号は、同じ zip の符号表で名前に直す。名前と符号を両方持つ
- 汎用属性（gen:*Attribute）は名前 → 値の対応で持つ。都市によって項目が違う
- 災害リスク（浸水深・土砂災害など）は 1 棟 × 1 想定 1 行の別の表にする

出力:
- data/plateau/building/<市区町村コード>.parquet
- data/plateau/building_risk/<市区町村コード>.parquet
"""

import io
import re
import struct
import zipfile
import zlib
from collections.abc import Iterator
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree
from shapely.geometry import MultiPolygon, Polygon

from shared.fetch import RangeFile, replacing

GML_ID = "{http://www.opengis.net/gml}id"
BLDG_FILE = re.compile(r"(?:^|/)udx/bldg/[^/]+\.gml$")
CODELIST_FILE = re.compile(r"(?:^|/)codelists/([^/]+)\.xml$")
GENERIC = ("stringAttribute", "intAttribute", "doubleAttribute", "measureAttribute", "dateAttribute", "uriAttribute")

# 製品仕様書 3.x までは Building が頭に付く（BuildingRiverFloodingRiskAttribute）
HAZARDS = {
    "RiverFloodingRiskAttribute": "洪水",
    "TsunamiRiskAttribute": "津波",
    "HighTideRiskAttribute": "高潮",
    "InlandFloodingRiskAttribute": "内水",
    "ReservoirFloodingRiskAttribute": "ため池",
    "LandSlideRiskAttribute": "土砂災害",
}
RISKS = HAZARDS | {f"Building{name}": hazard for name, hazard in HAZARDS.items()}

BUILDING = pa.schema(
    [
        ("source_city_code", pa.string()),
        ("gml_id", pa.string()),
        ("building_id", pa.string()),
        ("city_code", pa.string()),
        ("class", pa.string()),
        ("usage", pa.string()),
        ("usage_code", pa.string()),
        ("detailed_usage", pa.string()),
        ("measured_height", pa.float64()),
        ("storeys_above_ground", pa.int32()),
        ("storeys_below_ground", pa.int32()),
        ("year_of_construction", pa.int32()),
        ("total_floor_area", pa.float64()),
        ("footprint_area", pa.float64()),
        ("structure", pa.string()),
        ("fireproof_structure", pa.string()),
        ("survey_year", pa.int32()),
        ("address", pa.string()),
        ("real_estate_id", pa.string()),
        ("land_real_estate_ids", pa.list_(pa.string())),
        ("lod", pa.int8()),
        ("attributes", pa.map_(pa.string(), pa.string())),
        ("geometry", pa.binary()),
        ("file", pa.string()),
    ]
)

RISK = pa.schema(
    [
        ("source_city_code", pa.string()),
        ("gml_id", pa.string()),
        ("hazard", pa.string()),
        ("description", pa.string()),
        ("admin_type", pa.string()),
        ("scale", pa.string()),
        ("rank", pa.string()),
        ("rank_code", pa.string()),
        ("rank_org", pa.string()),
        ("depth", pa.float64()),
        ("duration", pa.float64()),
        ("area_type", pa.string()),
    ]
)


def localname(element) -> str:
    return etree.QName(element).localname


# 閉じタグの抜けた符号表を配る都市がある（鎌倉市）ので、読めるところまで読む
CODELIST_PARSER = etree.XMLParser(recover=True)


def parse_codelist(data: bytes) -> dict[str, str]:
    root = etree.fromstring(data, CODELIST_PARSER)
    return {
        d.findtext("{*}name"): d.findtext("{*}description")
        for d in root.iter("{*}Definition")
    }


def text(element) -> str | None:
    value = element.text.strip() if element is not None and element.text else None
    return value or None


def number(element, kind=float):
    value = text(element)
    try:
        return kind(float(value)) if value is not None else None
    except ValueError:
        return None


def label(element, lists: dict[str, dict[str, str]]) -> str | None:
    """符号を符号表の名前に直す。符号表に無ければ符号のまま。"""
    code = text(element)
    if code is None:
        return None
    space = Path(element.get("codeSpace") or "").stem
    return lists.get(space, {}).get(code, code)


def first_elements(building) -> dict:
    """建物の中の要素を名前ごとに最初の 1 つだけ引けるようにする。"""
    index: dict = {}
    for element in building.iter(tag=etree.Element):
        index.setdefault(localname(element), element)
    return index


def ring(pos_list) -> list[tuple[float, float]]:
    values = [float(v) for v in pos_list.text.split()]
    dim = int(pos_list.get("srsDimension") or pos_list.getparent().get("srsDimension") or 3)
    return [(values[i + 1], values[i]) for i in range(0, len(values) - dim + 1, dim)]


def heights(pos_list) -> list[float]:
    values = [float(v) for v in pos_list.text.split()]
    return values[2::3]


def polygon(element) -> Polygon | None:
    exterior = element.find("{*}exterior//{*}posList")
    if exterior is None or not exterior.text:
        return None
    interiors = [ring(p) for p in element.iterfind("{*}interior//{*}posList") if p.text]
    shell = ring(exterior)
    return Polygon(shell, interiors) if len(shell) >= 4 else None


def lowest_faces(solid) -> list:
    """LOD1 の立体の面のうち、いちばん低い水平な面（底面）。"""
    faces = [
        (p, z)
        for p in solid.iter("{*}Polygon")
        if (pos := p.find("{*}exterior//{*}posList")) is not None and pos.text
        and len(set(z := heights(pos))) == 1
    ]
    if not faces:
        return []
    bottom = min(z[0] for _, z in faces)
    return [p for p, z in faces if z[0] == bottom]


def present(index: dict, *names: str):
    """names のうち最初にある要素。要素は子が無いと偽になるので is not None で見る。"""
    return next((index[n] for n in names if index.get(n) is not None), None)


def footprint(index: dict) -> bytes | None:
    surface = present(index, "lod0FootPrint", "lod0RoofEdge")
    faces = list(surface.iter("{*}Polygon")) if surface is not None else []
    if not faces and index.get("lod1Solid") is not None:
        faces = lowest_faces(index["lod1Solid"])
    polygons = [p for p in map(polygon, faces) if p is not None]
    if not polygons:
        return None
    return (polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)).wkb


def lod(index: dict) -> int | None:
    levels = [int(name[3]) for name in index if re.fullmatch(r"lod[0-4](Solid|MultiSurface)", name)]
    return max(levels) if levels else None


def generic_attributes(building) -> list[tuple[str, str]]:
    return [
        (e.get("name"), text(e.find("{*}value")))
        for e in building.iter(*(f"{{*}}{name}" for name in GENERIC))
        if e.get("name")
    ]


def building_row(building, lists: dict, city_code: str, file: str) -> dict:
    index = first_elements(building)
    get = index.get
    return {
        "source_city_code": city_code,
        "gml_id": building.get(GML_ID),
        "building_id": text(get("buildingID")),
        "city_code": text(get("city")),
        "class": label(get("class"), lists),
        "usage": label(get("usage"), lists),
        "usage_code": text(get("usage")),
        "detailed_usage": label(get("detailedUsage"), lists),
        "measured_height": number(get("measuredHeight")),
        "storeys_above_ground": number(get("storeysAboveGround"), int),
        "storeys_below_ground": number(get("storeysBelowGround"), int),
        "year_of_construction": number(get("yearOfConstruction"), int),
        "total_floor_area": number(get("totalFloorArea")),
        "footprint_area": number(present(index, "buildingFootprintArea", "buildingRoofEdgeArea")),
        "structure": label(get("buildingStructureType"), lists),
        "fireproof_structure": label(get("fireproofStructureType"), lists),
        "survey_year": number(get("surveyYear"), int),
        "address": text(get("LocalityName")),
        "real_estate_id": text(get("realEstateIDOfBuilding")),
        "land_real_estate_ids": [v for e in building.iter("{*}realEstateIDOfLand") if (v := text(e))] or None,
        "lod": lod(index),
        "attributes": generic_attributes(building) or None,
        "geometry": footprint(index),
        "file": file,
    }


def risk_rows(building, lists: dict, city_code: str) -> list[dict]:
    def field(risk, name, convert=label):
        element = risk.find(f"{{*}}{name}")
        return convert(element, lists) if convert is label else convert(element)

    return [
        {
            "source_city_code": city_code,
            "gml_id": building.get(GML_ID),
            "hazard": RISKS[localname(risk)],
            "description": field(risk, "description"),
            "admin_type": field(risk, "adminType"),
            "scale": field(risk, "scale"),
            "rank": field(risk, "rank"),
            "rank_code": field(risk, "rank", text),
            "rank_org": field(risk, "rankOrg"),
            "depth": field(risk, "depth", number),
            "duration": field(risk, "duration", number),
            "area_type": field(risk, "areaType"),
        }
        for risk in building.iter(*(f"{{*}}{name}" for name in RISKS))
    ]


def buildings(data: bytes) -> Iterator:
    """GML の中の建物（bldg:Building）を 1 つずつ返し、返したものは捨てる。"""
    for _, element in etree.iterparse(io.BytesIO(data), events=("end",), tag="{*}Building", huge_tree=True):
        yield element
        element.clear()
        parent = element.getparent()
        while parent is not None and element.getprevious() is not None:
            del parent[0]


def parse_gml(data: bytes, lists: dict, city_code: str, file: str) -> tuple[list[dict], list[dict]]:
    rows, risks = [], []
    for building in buildings(data):
        rows.append(building_row(building, lists, city_code, file))
        risks.extend(risk_rows(building, lists, city_code))
    return rows, risks


# まとめて取るときに、間に挟まる要らないメンバーをどこまで読み捨てるか、1 回で取る上限
GAP = 1 << 20
BLOCK = 1 << 26
LOCAL_HEADER = struct.Struct("<4s5H3L2H")


def blocks(infos: list[zipfile.ZipInfo]) -> list[list[zipfile.ZipInfo]]:
    """zip の中の位置の順に、近くに並ぶメンバーを 1 つの塊にする。"""
    groups: list[list[zipfile.ZipInfo]] = []
    for info in sorted(infos, key=lambda i: i.header_offset):
        last = groups[-1] if groups else None
        if last and info.header_offset - end(last[-1]) <= GAP and end(info) - last[0].header_offset <= BLOCK:
            last.append(info)
        else:
            groups.append([info])
    return groups


def end(info: zipfile.ZipInfo) -> int:
    # ローカルヘッダーの拡張フィールドは中央ディレクトリと長さが違うことがあるので余裕を見る
    return info.header_offset + LOCAL_HEADER.size + len(info.orig_filename.encode()) + 1024 + info.compress_size


def unpack(block: bytes, start: int, info: zipfile.ZipInfo) -> bytes | None:
    """塊の中のメンバーを取り出す。塊に収まっていなければ None。"""
    offset = info.header_offset - start
    header = LOCAL_HEADER.unpack_from(block, offset)
    begin = offset + LOCAL_HEADER.size + header[9] + header[10]
    data = block[begin : begin + info.compress_size]
    if len(data) < info.compress_size:
        return None
    if info.compress_type == zipfile.ZIP_DEFLATED:
        return zlib.decompress(data, -15)
    return data if info.compress_type == zipfile.ZIP_STORED else None


def members(url: str, wanted) -> Iterator[tuple[str, bytes]]:
    """zip の中で wanted(名前) が真のメンバーを (名前, 中身) で返す。"""
    raw = RangeFile(url)
    with zipfile.ZipFile(io.BufferedReader(raw, 1 << 16)) as z:
        infos = [i for i in z.infolist() if wanted(i.filename)]
        for group in blocks(infos):
            start = group[0].header_offset
            raw.seek(start)
            block = raw.read(min(raw.size, end(group[-1])) - start)
            for info in group:
                data = unpack(block, start, info)
                yield info.filename, data if data is not None else z.read(info)


def convert(source: dict, building_path: Path, risk_path: Path) -> tuple[int, int]:
    """都市の zip を読み、建物と災害リスクの Parquet を書いて行数を返す。"""
    city_code = source["city_code"]
    counts = [0, 0]
    lists = {
        m.group(1): parse_codelist(data)
        for name, data in members(source["zip_url"], CODELIST_FILE.search)
        if (m := CODELIST_FILE.search(name))
    }
    building_path.parent.mkdir(parents=True, exist_ok=True)
    risk_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        replacing(building_path) as bp,
        replacing(risk_path) as rp,
        pq.ParquetWriter(bp, BUILDING, compression="zstd") as bw,
        pq.ParquetWriter(rp, RISK, compression="zstd") as rw,
    ):
        for name, data in members(source["zip_url"], BLDG_FILE.search):
            rows, risks = parse_gml(data, lists, city_code, Path(name).name)
            if rows:
                bw.write_table(pa.Table.from_pylist(rows, schema=BUILDING))
            if risks:
                rw.write_table(pa.Table.from_pylist(risks, schema=RISK))
            counts[0] += len(rows)
            counts[1] += len(risks)
    return counts[0], counts[1]
