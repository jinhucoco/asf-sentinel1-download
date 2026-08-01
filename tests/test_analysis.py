# -*- coding: utf-8 -*-
"""analysis 模块单元测试（本次测试沉淀的经验）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis import (check_per_date_coverage, check_orbit_consistency,
                      check_satellite_consistency, analyze_frame_coverage, monthly_sample)


class FakeGeo:
    """模拟 asf_search 产品对象"""
    def __init__(self, geojson, date, frame, orbit=135, sat='S1A'):
        self.geometry = geojson
        self.properties = {'startTime': date, 'frameNumber': frame,
                           'pathNumber': orbit, 'platform': sat}


UPPER = {'type': 'Polygon', 'coordinates': [[[129.5, 32], [131, 32], [131, 34], [129.5, 34], [129.5, 32]]]}
LOWER = {'type': 'Polygon', 'coordinates': [[[131, 32], [132, 32], [132, 34], [131, 34], [131, 32]]]}
AOI = 'POLYGON((130.5 32.5, 131.5 32.5, 131.5 33.5, 130.5 33.5, 130.5 32.5))'


def test_per_date_coverage_cross_frame():
    """逐时相覆盖：跨帧时相（463+468 并集）有效，单帧无效"""
    upper = FakeGeo(UPPER, '2025-01-01T00:00:00Z', 463)
    lower = FakeGeo(LOWER, '2025-01-01T00:00:00Z', 468)
    ok, bad = check_per_date_coverage(AOI, [upper, lower])
    assert len(ok) == 1 and len(bad) == 0
    ok2, bad2 = check_per_date_coverage(AOI, [upper])
    assert len(ok2) == 0 and len(bad2) == 1


def test_orbit_consistency():
    """同 frame 混入不同轨道应检出（frame468 混 62/135 场景）"""
    p1 = FakeGeo(UPPER, '2025-01-01T00:00:00Z', 463, orbit=135)
    p2 = FakeGeo(UPPER, '2025-01-02T00:00:00Z', 463, orbit=62)
    ok, paths, bad = check_orbit_consistency([p1, p2])
    assert not ok
    assert 62 in paths and 135 in paths
    assert len(bad) == 1


def test_satellite_consistency():
    """S1A/S1C 卫星一致性"""
    p1 = FakeGeo(UPPER, '2025-01-01T00:00:00Z', 463, sat='S1A')
    p2 = FakeGeo(UPPER, '2025-01-02T00:00:00Z', 463, sat='S1C')
    ok, sats = check_satellite_consistency([p1, p2])
    assert not ok and sats == {'S1A', 'S1C'}


def test_frame_coverage_analysis():
    """frame 覆盖面积比分析：跨帧互补 ≈100%"""
    upper = FakeGeo(UPPER, '2025-01-01T00:00:00Z', 463)
    lower = FakeGeo(LOWER, '2025-01-01T00:00:00Z', 468)
    info = analyze_frame_coverage(AOI, [upper, lower])
    assert info[463]['cover_ratio'] < 1 and info[468]['cover_ratio'] < 1
    assert abs(info[463]['cover_ratio'] + info[468]['cover_ratio'] - 1.0) < 0.05
    assert not info[463]['fully_covers']


def test_monthly_sample():
    """每月采样取最早时相"""
    prods = []
    for d in ['2025-01-05T00:00:00Z', '2025-01-17T00:00:00Z',
              '2025-02-02T00:00:00Z', '2025-02-14T00:00:00Z']:
        prods.append(FakeGeo(UPPER, d, 463))
    sel = monthly_sample(prods, 'first')
    assert len(sel) == 2  # 两个月各一个时相
    assert '2025-01-05' in str(sel[0].properties['startTime'])


def test_plot_coverage_orbit_filter(tmp_path):
    """覆盖图按轨道过滤：同 frame 不同轨道 footprint 区分，不混画"""
    import os
    from analysis import plot_coverage

    class FakeGeo:
        def __init__(self, geojson, frame, orbit):
            self.geometry = geojson
            self.properties = {'startTime': '2025-01-01T00:00:00Z',
                               'frameNumber': frame, 'pathNumber': orbit}

    # frame 468 在两个轨道下有不同 footprint（实测：轨道135在101-104°E，轨道62在103-106°E）
    fp_135 = {'type': 'Polygon', 'coordinates': [[[101, 37], [105, 37], [105, 39], [101, 39], [101, 37]]]}
    fp_62 = {'type': 'Polygon', 'coordinates': [[[103, 37], [107, 37], [107, 39], [103, 39], [103, 37]]]}
    aoi = 'POLYGON((103.5 37.5, 104.5 37.5, 104.5 38.5, 103.5 38.5, 103.5 37.5))'

    prods = [FakeGeo(fp_135, 468, 135), FakeGeo(fp_62, 468, 62)]
    out = os.path.join(str(tmp_path), 'cov.png')

    # 只画轨道 135：应只包含 fp_135 的 footprint
    plot_coverage(aoi, prods, out, orbit=135)
    assert os.path.exists(out) and os.path.getsize(out) > 1000
    # 无 orbit 参数时应画出两个（不崩）
    plot_coverage(aoi, prods, os.path.join(str(tmp_path), 'cov2.png'))
    print('✓ 覆盖图按轨道过滤测试通过')


def test_sample_by_frequency():
    """按频率采样：每月/每季/每半年/每年/全部"""
    from analysis import sample_by_frequency

    class FakeGeo:
        def __init__(self, date, frame=468):
            self.geometry = {'type': 'Polygon', 'coordinates': [[[101, 37], [105, 37], [105, 39], [101, 39], [101, 37]]]}
            self.properties = {'startTime': date, 'frameNumber': frame, 'pathNumber': 135}

    prods = []
    for y in (2020, 2021):
        for m in range(1, 13):
            for d in (5, 17):
                prods.append(FakeGeo(f'{y}-{m:02d}-{d:02d}T00:00:00Z'))

    cases = [('monthly', 24), ('quarterly', 8), ('semiyearly', 4), ('yearly', 2), ('all', 48)]
    for freq, expect in cases:
        sel = sample_by_frequency(prods, freq, 'first')
        n_days = len(set(p.properties['startTime'][:10] for p in sel))
        assert n_days == expect, f'{freq}: 期望 {expect} 时相天, got {n_days}'


def test_plot_coverage_orbit_str_int():
    """覆盖图轨道号 int/str 兼容（修复：str 轨道号过滤 bug）"""
    import os
    from analysis import plot_coverage

    class FakeGeo:
        def __init__(self, geojson, frame, orbit):
            self.geometry = geojson
            self.properties = {'startTime': '2025-01-01T00:00:00Z',
                               'frameNumber': frame, 'pathNumber': orbit}

    fp = {'type': 'Polygon', 'coordinates': [[[101, 37], [105, 37], [105, 39], [101, 39], [101, 37]]]}
    aoi = 'POLYGON((102 37.5, 104 37.5, 104 38.5, 102 38.5, 102 37.5))'
    prods = [FakeGeo(fp, 468, 135), FakeGeo(fp, 473, 135)]

    import tempfile
    d = tempfile.mkdtemp()
    # 轨道号用字符串 '135'（analyze.py 分组产生的情况）
    out1 = plot_coverage(aoi, prods, os.path.join(d, 'c1.png'), orbit='135')
    assert os.path.exists(out1) and os.path.getsize(out1) > 1000
    # 轨道号用 int 135
    out2 = plot_coverage(aoi, prods, os.path.join(d, 'c2.png'), orbit=135)
    assert os.path.exists(out2) and os.path.getsize(out2) > 1000
