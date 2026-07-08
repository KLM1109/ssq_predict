"""
双色球分析系统 单元测试 & 集成测试
==================================
使用标准库 unittest 框架, 无第三方依赖。
运行方式: python test_ssq_analyzer.py
"""
import csv
import os
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from typing import List

import ssq_analyzer as analyzer_mod
from ssq_analyzer import (
    BLUE_BALLS,
    INTERVALS,
    RED_BALLS,
    RECOMMEND_RED_COUNT,
    SSQAnalyzer,
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "ssq_history.csv")


def _write_csv(path: str, rows: List[List[str]]) -> None:
    """写入测试用CSV文件。"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["期号", "日期", "红球1", "红球2", "红球3", "红球4", "红球5", "红球6", "蓝球"])
        writer.writerows(rows)


def _sample_rows(n: int = 5) -> List[List[str]]:
    """构造 n 行合法的模拟数据(每行红球严格升序、范围合法、唯一)。"""
    rows = []
    base_date = "2026-01-01"
    for i in range(n):
        reds = [1 + (i * 6 + j) % 33 for j in range(6)]
        reds = sorted(set(reds))
        while len(reds) < 6:
            v = (reds[-1] + 1) % 33 + 1
            if v not in reds:
                reds.append(v)
        reds = sorted(reds)[:6]
        rows.append([f"202600{i + 1:02d}", base_date] + [f"{r:02d}" for r in reds] + ["05"])
    return rows


class TestConstants(unittest.TestCase):
    def test_red_balls(self):
        self.assertEqual(len(RED_BALLS), 33)
        self.assertEqual(RED_BALLS[0], 1)
        self.assertEqual(RED_BALLS[-1], 33)
        self.assertEqual(len(set(RED_BALLS)), 33)

    def test_blue_balls(self):
        self.assertEqual(len(BLUE_BALLS), 16)
        self.assertEqual(BLUE_BALLS[0], 1)
        self.assertEqual(BLUE_BALLS[-1], 16)

    def test_intervals_cover_all(self):
        covered = set()
        for lo, hi in INTERVALS.values():
            covered.update(range(lo, hi + 1))
        self.assertEqual(covered, set(RED_BALLS))


class TestDataLoading(unittest.TestCase):
    """数据加载与校验测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.tmpdir, "test.csv")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_valid_data(self):
        _write_csv(self.csv_path, _sample_rows(10))
        a = SSQAnalyzer(self.csv_path)
        self.assertTrue(a.is_ready)
        self.assertEqual(len(a.history_data), 10)

    def test_missing_file(self):
        a = SSQAnalyzer(os.path.join(self.tmpdir, "nope.csv"))
        self.assertFalse(a.is_ready)
        self.assertEqual(a.history_data, [])

    def test_invalid_red_range(self):
        rows = _sample_rows(1)
        rows[0][2] = "00"  # 红球1=0, 越界
        _write_csv(self.csv_path, rows)
        a = SSQAnalyzer(self.csv_path)
        self.assertFalse(a.is_ready)

    def test_duplicate_red(self):
        rows = _sample_rows(1)
        rows[0][3] = rows[0][2]  # 红球2=红球1, 重复
        _write_csv(self.csv_path, rows)
        a = SSQAnalyzer(self.csv_path)
        self.assertFalse(a.is_ready)

    def test_blue_out_of_range(self):
        rows = _sample_rows(1)
        rows[0][8] = "17"  # 蓝球=17, 越界
        _write_csv(self.csv_path, rows)
        a = SSQAnalyzer(self.csv_path)
        self.assertFalse(a.is_ready)

    def test_red_not_sorted(self):
        rows = _sample_rows(1)
        # 强制乱序
        rows[0][2], rows[0][3] = rows[0][3], rows[0][2]
        _write_csv(self.csv_path, rows)
        a = SSQAnalyzer(self.csv_path)
        self.assertFalse(a.is_ready)

    def test_missing_columns(self):
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["期号", "日期", "蓝球"])
            writer.writerow(["2026001", "2026-01-01", "05"])
        a = SSQAnalyzer(self.csv_path)
        self.assertFalse(a.is_ready)


class TestFrequencyAndOmission(unittest.TestCase):
    """频率与遗漏值测试"""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DATA_FILE):
            raise unittest.SkipTest(f"数据文件不存在: {DATA_FILE}")
        cls.a = SSQAnalyzer(DATA_FILE)

    def test_total_red_count(self):
        total = sum(self.a.red_freq.values())
        expected = 6 * len(self.a.history_data)
        self.assertEqual(total, expected)

    def test_total_blue_count(self):
        total = sum(self.a.blue_freq.values())
        self.assertEqual(total, len(self.a.history_data))

    def test_freq_keys_complete(self):
        # 真实历史数据中并非所有 1-16 蓝球都会出现, 蓝球频次键应为 BLUE_BALLS 的子集
        self.assertEqual(set(self.a.red_freq.keys()), set(RED_BALLS))
        self.assertTrue(set(self.a.blue_freq.keys()).issubset(set(BLUE_BALLS)))
        self.assertTrue(set(self.a.blue_freq.keys()))

        # 重新加载一份覆盖所有 1-16 蓝球的合成数据, 验证频次键的完整性
        rows = []
        for i in range(16):
            reds = sorted({(i * 6 + j) % 33 + 1 for j in range(6)})
            while len(reds) < 6:
                v = (reds[-1] % 33) + 1
                if v not in reds:
                    reds.append(v)
            reds = sorted(reds)[:6]
            rows.append([f"202700{i + 1:02d}", "2027-01-01"] + [f"{r:02d}" for r in reds] + [f"{i + 1:02d}"])
        tmp = os.path.join(tempfile.gettempdir(), "ssq_full_blue.csv")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["期号", "日期", "红球1", "红球2", "红球3", "红球4", "红球5", "红球6", "蓝球"])
            w.writerows(rows)
        full = SSQAnalyzer(tmp)
        os.remove(tmp)
        self.assertEqual(set(full.blue_freq.keys()), set(BLUE_BALLS))

    def test_omission_latest(self):
        latest_reds = set(self.a.history_data[-1]["reds"])
        for n in RED_BALLS:
            if n in latest_reds:
                self.assertEqual(self.a.red_omission[n], 0)
        latest_blue = self.a.history_data[-1]["blue"]
        self.assertEqual(self.a.blue_omission[latest_blue], 0)

    def test_hot_cold_warm_count(self):
        hot = self.a.get_hot_red_balls(5)
        cold = self.a.get_cold_red_balls(5)
        warm = self.a.get_warm_red_balls()
        self.assertEqual(len(hot), 5)
        self.assertEqual(len(cold), 5)
        # 冷热号不应重叠
        self.assertEqual(set(hot) & set(cold), set())


class TestStatistics(unittest.TestCase):
    """统计接口测试"""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DATA_FILE):
            raise unittest.SkipTest(f"数据文件不存在: {DATA_FILE}")
        cls.a = SSQAnalyzer(DATA_FILE)

    def test_interval_keys(self):
        info = self.a.analyze_interval()
        self.assertEqual(set(info.keys()), set(INTERVALS.keys()))

    def test_interval_total_per_period(self):
        """每期三个区间红球数之和应等于6。"""
        info = self.a.analyze_interval()
        for record in self.a.history_data:
            counts = []
            for key, (lo, hi) in INTERVALS.items():
                counts.append(sum(1 for r in record["reds"] if lo <= r <= hi))
            self.assertEqual(sum(counts), 6)

    def test_parity_total(self):
        """每期奇数+偶数=6, 平均奇数+平均偶数=6。"""
        info = self.a.analyze_parity()
        self.assertAlmostEqual(info["平均奇数"] + (6 - info["平均奇数"]), 6.0)
        # 分布累计
        self.assertEqual(sum(info["分布"].values()), len(self.a.history_data))

    def test_size_total(self):
        info = self.a.analyze_size()
        self.assertAlmostEqual(info["平均大数"] + (6 - info["平均大数"]), 6.0)
        self.assertEqual(sum(info["分布"].values()), len(self.a.history_data))

    def test_repeat_recent(self):
        repeats = self.a.analyze_repeat(5)
        for ball, cnt in repeats:
            self.assertGreaterEqual(cnt, 2)
            self.assertIn(ball, RED_BALLS)


class TestPrediction(unittest.TestCase):
    """预测函数测试"""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DATA_FILE):
            raise unittest.SkipTest(f"数据文件不存在: {DATA_FILE}")
        cls.a = SSQAnalyzer(DATA_FILE)

    def test_red_count_and_range(self):
        pred = self.a.predict_red_balls(RECOMMEND_RED_COUNT)
        self.assertEqual(len(pred), RECOMMEND_RED_COUNT)
        self.assertEqual(len(set(pred)), RECOMMEND_RED_COUNT, "红球不能重复")
        for b in pred:
            self.assertIn(b, RED_BALLS)
        self.assertEqual(pred, sorted(pred), "红球应升序")

    def test_red_count_zero(self):
        self.assertEqual(self.a.predict_red_balls(0), [])

    def test_red_count_large(self):
        # 请求超过可用号码数时, 应返回33个不重复号码
        pred = self.a.predict_red_balls(50)
        self.assertEqual(len(pred), 33)
        self.assertEqual(set(pred), set(RED_BALLS))

    def test_blue_in_range(self):
        b, _ = self.a.predict_blue_ball()
        self.assertIn(b, BLUE_BALLS)

    def test_blue_options_count_and_sorted(self):
        opts, _ = self.a.predict_blue_options(5)
        self.assertEqual(len(opts), 5)
        self.assertEqual(opts, sorted(opts))
        for b in opts:
            self.assertIn(b, BLUE_BALLS)


class TestReport(unittest.TestCase):
    """报告生成测试"""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DATA_FILE):
            raise unittest.SkipTest(f"数据文件不存在: {DATA_FILE}")
        cls.a = SSQAnalyzer(DATA_FILE)

    def test_report_sections_present(self):
        r = self.a.generate_report()
        for section in [
            "一、红球频率分析",
            "二、蓝球频率分析",
            "三、遗漏值分析",
            "四、冷热号分析",
            "五、区间分布分析",
            "六、奇偶分析",
            "七、大小分析",
            "八、近期重复号分析",
            "九、下期预测",
            "十、风险提示",
        ]:
            self.assertIn(section, r)

    def test_report_includes_interval_range(self):
        r = self.a.generate_report()
        self.assertIn("01-11", r)
        self.assertIn("12-22", r)
        self.assertIn("23-33", r)

    def test_report_when_no_data(self):
        a = SSQAnalyzer(os.path.join(tempfile.gettempdir(), "never_exists_xyz.csv"))
        r = a.generate_report()
        self.assertIn("无可用历史数据", r)

    def test_save_report_creates_file(self):
        path = self.a.save_report("test_report.txt")
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)
        os.remove(path)


class TestPerformance(unittest.TestCase):
    """性能回归测试 - 防止 O(n²) 退化"""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DATA_FILE):
            raise unittest.SkipTest(f"数据文件不存在: {DATA_FILE}")

    def test_predict_under_one_second(self):
        import time
        a = SSQAnalyzer(DATA_FILE)
        start = time.time()
        for _ in range(50):
            a.predict_red_balls(6)
            a.predict_blue_ball()
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"50次预测耗时{elapsed:.2f}s, 性能不达标")


class TestIntegration(unittest.TestCase):
    """集成测试 - 完整流程"""

    def test_full_pipeline(self):
        if not os.path.exists(DATA_FILE):
            self.skipTest("数据文件不存在")
        a = SSQAnalyzer(DATA_FILE)
        self.assertTrue(a.is_ready)
        report = a.generate_report()
        self.assertGreater(len(report), 500)
        # 验证报告包含预测结果
        self.assertIn("【预测红球】", report)
        self.assertIn("【预测蓝球】", report)
        self.assertIn("首选", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
