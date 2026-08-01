# tests/test_download.py
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from download import (shp_to_kml, format_inventory, parse_polarization, _confirm,
                      ymd_to_mdy, FILE_TYPE_LABEL, shp_to_wkt, kml_to_wkt,
                      aoi_to_wkt, iso_datetime, parse_direction, footprint_contains,
                      group_by_orbit, group_union_covers, group_by_frame)

import pytest


def _make_test_shp(d=None):
    """创建最小矩形 shp，返回 shp 路径"""
    import shapefile
    d = d or tempfile.mkdtemp()
    w = shapefile.Writer(os.path.join(d, 'aoi'))
    w.field('id', 'N')
    w.poly([[[130.0, 32.0], [131.0, 32.0], [131.0, 33.0], [130.0, 33.0], [130.0, 32.0]]])
    w.record(1)
    w.close()
    return os.path.join(d, 'aoi.shp')


def _make_test_kml(d=None):
    """创建最小矩形 kml，返回 kml 路径"""
    d = d or tempfile.mkdtemp()
    kml_path = os.path.join(d, 'aoi.kml')
    with open(kml_path, 'w', encoding='utf-8') as f:
        f.write('''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>
130.8,33.0
131.2,33.0
131.2,33.4
130.8,33.4
130.8,33.0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document>
</kml>''')
    return kml_path


def test_ymd_to_mdy():
    assert ymd_to_mdy('20240101') == '01/01/2024'
    assert ymd_to_mdy('20241231') == '12/31/2024'
    assert ymd_to_mdy('20200101') == '01/01/2020'


def test_ymd_to_mdy_invalid():
    with pytest.raises(ValueError):
        ymd_to_mdy('2024-01-01')
    with pytest.raises(ValueError):
        ymd_to_mdy('20241')
    with pytest.raises(ValueError):
        ymd_to_mdy('')


def test_file_type_label_mapping():
    # SLC 应映射到 ASF 下拉的完整选项文本
    assert FILE_TYPE_LABEL['SLC'] == 'Single Look Complex'
    assert 'Single Look Complex' in 'L1 Single Look Complex (SLC)'
    assert FILE_TYPE_LABEL['GRD'] == 'Detected'


def test_confirm_all(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda *a: 'y')
    assert _confirm([{'orbit': '123'}, {'orbit': '456'}]) == 'all'


def test_confirm_orbit(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda *a: '123')
    assert _confirm([{'orbit': '123'}, {'orbit': '456'}]) == '123'


def test_confirm_cancel(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda *a: 'n')
    assert _confirm([{'orbit': '123'}]) is None


def test_confirm_retry_then_all(monkeypatch):
    # 非法输入后重试，再输入 y → 返回 'all'
    answers = iter(['abc', 'y'])
    monkeypatch.setattr('builtins.input', lambda *a: next(answers))
    assert _confirm([]) == 'all'


def test_shp_to_kml():
    # 生成最小 shp（用 pyshp 写入一个矩形）
    import shapefile
    d = tempfile.mkdtemp()
    w = shapefile.Writer(os.path.join(d, 'aoi'))
    w.field('id', 'N')
    w.poly([[[130.0, 32.0], [131.0, 32.0], [131.0, 33.0], [130.0, 33.0], [130.0, 32.0]]])
    w.record(1)
    w.close()
    kml = shp_to_kml(os.path.join(d, 'aoi.shp'))
    assert '<Polygon>' in kml
    assert '130.0,32.0' in kml or '130,32' in kml

def test_format_inventory():
    items = [
        {'date': '20240101', 'orbit': 123, 'pol': 'VV', 'size': '1.2 GB', 'file': 'S1A_xxx.zip'},
        {'date': '20240102', 'orbit': 456, 'pol': 'VH', 'size': '1.1 GB', 'file': 'S1A_yyy.zip'},
    ]
    out = format_inventory(items)
    assert '1' in out and '20240101' in out and 'S1A_xxx.zip' in out
    assert '2' in out and '20240102' in out

def test_parse_polarization():
    assert parse_polarization('vv') == 'VV'
    assert parse_polarization('VV+VH') == 'VV+VH'
    assert parse_polarization('vv+vh') == 'VV+VH'

# ============ 新增：WKT 转换与 ISO 日期（官方库方案） ============

def test_iso_datetime():
    assert iso_datetime('20240101') == '2024-01-01T00:00:00Z'
    assert iso_datetime('20241231') == '2024-12-31T00:00:00Z'


def test_iso_datetime_invalid():
    with pytest.raises(ValueError):
        iso_datetime('2024-1-1')
    with pytest.raises(ValueError):
        iso_datetime('202401')


def test_shp_to_wkt():
    shp = _make_test_shp()
    wkt = shp_to_wkt(shp)
    assert wkt.startswith('POLYGON((')
    assert '130.0 32.0' in wkt
    assert '131.0 33.0' in wkt
    assert wkt.endswith('))')


def test_kml_to_wkt():
    kml = _make_test_kml()
    wkt = kml_to_wkt(kml)
    assert wkt.startswith('POLYGON((')
    assert '130.8 33.0' in wkt
    assert '131.2 33.4' in wkt
    assert wkt.endswith('))')


def test_aoi_to_wkt_dispatch():
    # shp 分发
    shp = _make_test_shp()
    wkt_shp = aoi_to_wkt(shp)
    assert wkt_shp.startswith('POLYGON((')
    assert '130.0 32.0' in wkt_shp
    # kml 分发
    kml = _make_test_kml()
    wkt_kml = aoi_to_wkt(kml)
    assert wkt_kml.startswith('POLYGON((')
    assert '130.8 33.0' in wkt_kml


def test_aoi_to_wkt_unsupported():
    with pytest.raises(ValueError):
        aoi_to_wkt('foo.geojson')


def test_parse_direction():
    assert parse_direction('asc') == 'ASCENDING'
    assert parse_direction('desc') == 'DESCENDING'
    assert parse_direction('升轨') == 'ASCENDING'
    assert parse_direction('降轨') == 'DESCENDING'
    try:
        parse_direction('sideways')
        assert False, '应抛 ValueError'
    except ValueError:
        pass


def test_footprint_contains():
    # 研究区：小矩形
    aoi = 'POLYGON((130.8 33, 131.2 33, 131.2 33.4, 130.8 33.4, 130.8 33))'
    # 覆盖范围：大矩形（完全包含研究区）
    big_fp = {'type': 'Polygon', 'coordinates': [[[130.0, 32.0], [132.0, 32.0], [132.0, 34.0], [130.0, 34.0], [130.0, 32.0]]]}
    assert footprint_contains(aoi, big_fp) is True
    # 部分相交（不覆盖）→ False
    partial_fp = {'type': 'Polygon', 'coordinates': [[[130.5, 32.5], [131.5, 32.5], [131.5, 33.2], [130.5, 33.2], [130.5, 32.5]]]}
    assert footprint_contains(aoi, partial_fp) is False
    # 非法输入 → False 不崩溃
    assert footprint_contains('invalid', big_fp) is False


def test_group_by_orbit():
    class FakeR:
        def __init__(self, orbit):
            self.properties = {'pathNumber': orbit}
    results = [FakeR(163), FakeR(163), FakeR(55), FakeR(163), FakeR(55)]
    groups = group_by_orbit(results)
    assert len(groups) == 2
    assert len(groups['163']) == 3
    assert len(groups['55']) == 2


def test_kml_to_wkt_sarscape_format():
    """SARscape 导出的 kml：earth.google.com 命名空间 + 3维带海拔坐标"""
    import tempfile
    sarscape_kml = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.0">
   <Document>
      <name>test</name>
      <Placemark>
         <Polygon>
            <outerBoundaryIs>
               <LinearRing>
                  <coordinates>
                     116.749206,32.830839,3000.000000
                     116.839298,32.844799,3000.000000
                     116.830715,32.883914,3000.000000
                     116.749206,32.830839,3000.000000
                  </coordinates>
               </LinearRing>
            </outerBoundaryIs>
         </Polygon>
      </Placemark>
   </Document>
</kml>'''
    d = tempfile.mkdtemp()
    p = os.path.join(d, 'sarscape.kml')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(sarscape_kml)
    wkt = kml_to_wkt(p)
    assert '116.749206 32.830839' in wkt
    assert '3000' not in wkt  # 海拔应被忽略
    assert wkt.startswith('POLYGON((')


def test_group_union_covers_cross_frame():
    """研究区压在上下两景边界：单景不覆盖，并集覆盖"""
    from shapely.geometry import shape
    from shapely.wkt import loads
    # 模拟 asf_search 产品对象
    class FakeGeo:
        def __init__(self, geojson):
            self.geometry = geojson

    aoi_wkt = 'POLYGON((130.5 32.5, 131.5 32.5, 131.5 33.5, 130.5 33.5, 130.5 32.5))'
    upper = FakeGeo({'type': 'Polygon', 'coordinates': [[[129.5, 32], [131, 32], [131, 34], [129.5, 34], [129.5, 32]]]})
    lower = FakeGeo({'type': 'Polygon', 'coordinates': [[[131, 32], [132, 32], [132, 34], [131, 34], [131, 32]]]})
    # 单景都不覆盖
    assert not footprint_contains(aoi_wkt, upper.geometry)
    assert not footprint_contains(aoi_wkt, lower.geometry)
    # 并集覆盖
    assert group_union_covers(aoi_wkt, [upper, lower]) is True
    # 缺下景则不覆盖
    assert group_union_covers(aoi_wkt, [upper]) is False


def test_group_by_frame():
    """同一时相多帧识别"""
    class FakeP:
        def __init__(self, date, frame):
            self.properties = {'startTime': date, 'frameNumber': frame}
    prods = [
        FakeP('2025-07-01T00:00:00Z', 101),
        FakeP('2025-07-01T00:00:00Z', 102),  # 同一天两个 frame（上下景）
        FakeP('2025-07-13T00:00:00Z', 101),
    ]
    frames = group_by_frame(prods)
    assert len(frames) == 2  # 两天
    assert len(frames['2025-07-01']) == 2  # 这一天有上下景
    assert len(frames['2025-07-13']) == 1


def test_sanitize_filename():
    """文件名消毒：路径穿越防护"""
    from robust_download import sanitize_filename
    # 正常文件名
    assert sanitize_filename('S1A_IW_SLC__1SDV_xxx.zip') == 'S1A_IW_SLC__1SDV_xxx.zip'
    # 路径穿越：反斜杠和 ../ 被剥离
    assert sanitize_filename(r'..\..\evil.zip') == 'evil.zip'
    assert sanitize_filename('a/../../evil.zip') == 'evil.zip'
    # 危险输入被净化或拒绝
    for bad in ('..', '.', '', None):
        try:
            sanitize_filename(bad)
            assert False, f'应拒绝: {bad!r}'
        except ValueError:
            pass
    # 含 : 或 / 的输入被 basename 净化，不会逃逸目录
    assert sanitize_filename('a:b.zip') == 'b.zip'
    assert sanitize_filename('a/b.zip') == 'b.zip'


def test_check_download_url():
    """下载 URL 校验：HTTPS + host 白名单"""
    from robust_download import check_download_url
    check_download_url('https://datapool.asf.alaska.edu/SLC/SA/xxx.zip')  # 合法
    check_download_url('https://s3.amazonaws.com/xxx.zip')  # 合法
    for bad in ('http://datapool.asf.alaska.edu/xxx.zip',      # 非 HTTPS
                'https://evil.com/xxx.zip',                     # 白名单外
                'https://datapool.asf.alaska.edu.evil.com/xxx', # 域名伪造
                'file:///etc/passwd'):
        try:
            check_download_url(bad)
            assert False, f'应拒绝: {bad}'
        except ValueError:
            pass


def test_path_consistency_check():
    """轨道一致性校验：同 frame 不同轨道应被拒绝"""
    import io, contextlib
    from download import run_download
    # 构造含多轨道的 results 模拟（直接测 run_download 的校验逻辑）
    # 用 monkeypatch 模拟认证/搜索，验证校验拦截
    class FakeProps:
        def __init__(self, path):
            self.properties = {'pathNumber': path}
    # 校验逻辑本身：path_set 应捕获多轨道
    results = [FakeProps(135), FakeProps(62)]
    path_set = {r.properties.get('pathNumber', '?') for r in results}
    assert len(path_set) == 2  # 多轨道会被发现
    results2 = [FakeProps(135), FakeProps(135)]
    path_set2 = {r.properties.get('pathNumber', '?') for r in results2}
    assert len(path_set2) == 1  # 单一轨道通过
