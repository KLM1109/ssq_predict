"""
双色球数据更新模块
==================
从互联网自动获取最新开奖数据并更新本地CSV文件。
支持多个数据源、数据去重、格式校验、增量更新。

使用方式:
    python ssq_updater.py              # 自动更新
    python ssq_updater.py --force      # 强制全量更新
    python ssq_updater.py --check      # 仅检查是否有新数据
"""
import argparse
import csv
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

DATA_FILE = "ssq_history.csv"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class SSQUpdater:
    """双色球数据自动更新器"""

    def __init__(self, data_file: str = DATA_FILE) -> None:
        self.data_file = data_file
        self.local_data: Dict[str, dict] = {}
        self._load_local()

    def _load_local(self) -> None:
        """加载本地CSV数据到字典(期号为键)"""
        if not self.data_file or not __import__("os").path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    period = row["期号"]
                    reds = [int(row[f"红球{i}"]) for i in range(1, 7)]
                    self.local_data[period] = {
                        "period": period,
                        "date": row["日期"],
                        "reds": reds,
                        "blue": int(row["蓝球"]),
                    }
        except Exception as e:
            print(f"[警告] 读取本地数据失败: {e}")

    def get_local_latest(self) -> Optional[str]:
        """获取本地最新期号"""
        if not self.local_data:
            return None
        return max(self.local_data.keys())

    def _parse_17500(self, html: str) -> List[dict]:
        """解析 17500.cn 移动端页面数据"""
        results = []
        pattern = re.compile(
            r'data-name="issue"\s+data-v="(\d{7})".*?'
            r'data-date="(\d{4}-\d{2}-\d{2})".*?'
            r'data-v="(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+\+\s+(\d{2})"',
            re.DOTALL,
        )
        for match in pattern.finditer(html):
            period = match.group(1)
            date_str = match.group(2)
            nums = [int(match.group(i)) for i in range(3, 10)]
            reds = sorted(nums[:6])
            blue = nums[6]
            results.append(
                {
                    "period": period,
                    "date": date_str,
                    "reds": reds,
                    "blue": blue,
                    "source": "17500.cn",
                }
            )
        return results

    def _parse_gsflcp(self, html: str) -> List[dict]:
        """解析 gsflcp.com 页面数据"""
        results = []
        # 匹配: 2026-06-14 | 2026067 | 273219043029 | 13
        pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2})\s*\|\s*(\d{7})\s*\|\s*(\d{12})\s*\|\s*(\d{1,2})"
        )
        for match in pattern.finditer(html):
            date_str = match.group(1)
            period = match.group(2)
            red_str = match.group(3)
            blue = int(match.group(4))
            reds = sorted([int(red_str[i : i + 2]) for i in range(0, 12, 2)])
            results.append(
                {
                    "period": period,
                    "date": date_str,
                    "reds": reds,
                    "blue": blue,
                    "source": "gsflcp.com",
                }
            )
        return results

    def _parse_ip138(self, html: str) -> List[dict]:
        """解析 ip138.com 页面数据"""
        results = []
        # 匹配: 2026068 | 06-16 | 3 5 16 18 29 32 4
        pattern = re.compile(
            r"(\d{7})\s*\|\s*(\d{2}-\d{2})\s*\|\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"
        )
        for match in pattern.finditer(html):
            period = match.group(1)
            month_day = match.group(2)
            nums = [int(match.group(i)) for i in range(3, 10)]
            reds = sorted(nums[:6])
            blue = nums[6]
            year = period[:4]
            date_str = f"{year}-{month_day}"
            results.append(
                {
                    "period": period,
                    "date": date_str,
                    "reds": reds,
                    "blue": blue,
                    "source": "ip138.com",
                }
            )
        return results

    def _guess_date(self, period: str) -> str:
        """根据期号估算日期(兜底方案)"""
        year = int(period[:4])
        seq = int(period[4:])
        base = datetime(year, 1, 1)
        days = (seq - 1) * 2.3
        guessed = base.replace(day=1)
        return guessed.strftime("%Y-%m-%d")

    def _fetch_url(self, url: str, timeout: int = 10) -> Optional[str]:
        """安全地获取网页内容"""
        try:
            headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            print(f"[警告] 请求 {url} 失败: {e}")
            return None

    def fetch_from_web(self) -> List[dict]:
        """从多个数据源获取数据并合并去重"""
        sources = [
            ("https://m.17500.cn/kj-m/list-ssq.html", self._parse_17500),
            ("https://www.gsflcp.com/cz/ssq/wqkj/", self._parse_gsflcp),
            ("https://cp.ip138.com/shuangseqiu/", self._parse_ip138),
        ]

        all_data: Dict[str, dict] = {}
        for url, parser in sources:
            html = self._fetch_url(url)
            if not html:
                continue
            try:
                items = parser(html)
                for item in items:
                    period = item["period"]
                    if period not in all_data:
                        all_data[period] = item
                    else:
                        existing = all_data[period]
                        if item["reds"] != existing["reds"] or item["blue"] != existing["blue"]:
                            print(f"[警告] 数据冲突: {period} {existing['source']} vs {item['source']}")
                            print(f"       {existing['reds']}+{existing['blue']} vs {item['reds']}+{item['blue']}")
            except Exception as e:
                print(f"[警告] 解析 {url} 失败: {e}")

        return sorted(all_data.values(), key=lambda x: x["period"])

    def _validate_record(self, record: dict) -> bool:
        """校验单条记录是否合法"""
        period = record["period"]
        reds = record["reds"]
        blue = record["blue"]
        if not re.match(r"^\d{7}$", period):
            return False
        if len(reds) != 6:
            return False
        if not all(1 <= r <= 33 for r in reds):
            return False
        if len(set(reds)) != 6:
            return False
        if reds != sorted(reds):
            return False
        if not 1 <= blue <= 16:
            return False
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", record.get("date", "")):
            return False
        return True

    def find_new_records(self, web_data: List[dict]) -> List[dict]:
        """找出本地没有的新记录"""
        local_periods = set(self.local_data.keys())
        new_records = []
        for record in web_data:
            if not self._validate_record(record):
                continue
            if record["period"] not in local_periods:
                new_records.append(record)
        return sorted(new_records, key=lambda x: x["period"])

    def merge_and_save(self, new_records: List[dict], force: bool = False) -> int:
        """合并新数据并保存到CSV"""
        if not new_records and not force:
            return 0

        all_records = list(self.local_data.values())
        all_records.extend(new_records)
        all_records.sort(key=lambda x: x["period"])

        with open(self.data_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["期号", "日期", "红球1", "红球2", "红球3", "红球4", "红球5", "红球6", "蓝球"])
            for rec in all_records:
                row = [rec["period"], rec["date"]]
                row.extend(f"{r:02d}" for r in rec["reds"])
                row.append(f"{rec['blue']:02d}")
                writer.writerow(row)

        return len(new_records)

    def update(self, force: bool = False) -> Tuple[int, str]:
        """执行完整更新流程"""
        print(f"[更新] 正在检查数据源...")
        web_data = self.fetch_from_web()

        if not web_data:
            return 0, "未获取到网络数据"

        print(f"[更新] 从网络获取到 {len(web_data)} 条记录")

        if force:
            print(f"[更新] 强制模式: 将覆盖本地数据")
            valid = [r for r in web_data if self._validate_record(r)]
            for rec in valid:
                self.local_data[rec["period"]] = rec
            count = self.merge_and_save([], force=True)
            return len(valid), f"强制更新 {len(valid)} 条"

        new_records = self.find_new_records(web_data)

        if not new_records:
            latest = self.get_local_latest()
            return 0, f"本地已是最新 (最新期号: {latest})"

        print(f"[更新] 发现 {len(new_records)} 条新数据:")
        for rec in new_records:
            print(f"  {rec['period']} ({rec['date']}): "
                  f"{', '.join(f'{r:02d}' for r in rec['reds'])} + {rec['blue']:02d}")

        count = self.merge_and_save(new_records)
        return count, f"成功更新 {count} 条新数据"

    def check_update(self) -> Tuple[int, List[dict]]:
        """检查是否有更新但不执行"""
        web_data = self.fetch_from_web()
        if not web_data:
            return 0, []
        new_records = self.find_new_records(web_data)
        return len(new_records), new_records


def main() -> None:
    parser = argparse.ArgumentParser(description="双色球数据更新工具")
    parser.add_argument("--force", action="store_true", help="强制全量更新")
    parser.add_argument("--check", action="store_true", help="仅检查更新")
    parser.add_argument("--file", default=DATA_FILE, help="数据文件路径")
    args = parser.parse_args()

    updater = SSQUpdater(args.file)
    local_latest = updater.get_local_latest()
    local_count = len(updater.local_data)
    print(f"[状态] 本地数据: {local_count} 条, 最新期号: {local_latest}")

    if args.check:
        count, records = updater.check_update()
        if count > 0:
            print(f"[检查] 发现 {count} 条新数据:")
            for rec in records:
                print(f"  {rec['period']} ({rec['date']}): "
                      f"{', '.join(f'{r:02d}' for r in rec['reds'])} + {rec['blue']:02d}")
        else:
            print(f"[检查] 本地已是最新")
        return

    count, msg = updater.update(args.force)
    print(f"[结果] {msg}")

    if count > 0:
        updater._load_local()
        new_latest = updater.get_local_latest()
        new_count = len(updater.local_data)
        print(f"[状态] 更新后: {new_count} 条, 最新期号: {new_latest}")


if __name__ == "__main__":
    main()
