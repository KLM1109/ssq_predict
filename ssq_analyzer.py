"""
双色球智能分析系统
==================
提供历史数据频率分析、遗漏值计算、冷热号识别、区间/奇偶/大小分布统计，
并基于多维加权评分模型输出下期号码预测。
"""
import csv
import os
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

RED_BALLS: List[int] = list(range(1, 34))
BLUE_BALLS: List[int] = list(range(1, 17))

INTERVALS: Dict[str, Tuple[int, int]] = {
    "一区": (1, 11),
    "二区": (12, 22),
    "三区": (23, 33),
}

RED_THRESHOLD_HOT = 5
RED_THRESHOLD_COLD = 5
WARM_FREQ_RATIO = (0.8, 1.2)
TOP_HOT = 8
TOP_OMISSION = 6
TOP_BLUE_HOT = 3
TOP_BLUE_OMISSION = 3
RECOMMEND_RED_COUNT = 6


class SSQAnalyzer:
    """双色球历史数据分析与下期号码预测器"""

    def __init__(self, data_file: str) -> None:
        self.data_file: str = data_file
        self.history_data: List[Dict] = []
        self.red_freq: Counter = Counter()
        self.blue_freq: Counter = Counter()
        self.red_omission: Dict[int, int] = {n: 0 for n in RED_BALLS}
        self.blue_omission: Dict[int, int] = {n: 0 for n in BLUE_BALLS}
        self._loaded: bool = False
        self._analyze()

    def load_data(self) -> bool:
        """加载并校验历史CSV数据。返回是否加载成功。"""
        self.history_data = []
        if not os.path.exists(self.data_file):
            print(f"[错误] 数据文件不存在: {self.data_file}")
            return False
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required = {"期号", "日期", "蓝球"} | {f"红球{i}" for i in range(1, 7)}
                if not required.issubset(reader.fieldnames or []):
                    print(f"[错误] CSV缺少必要字段, 需包含: {sorted(required)}")
                    return False
                for line_no, row in enumerate(reader, start=2):
                    if not self._validate_row(row, line_no):
                        return False
                    reds = [int(row[f"红球{i}"]) for i in range(1, 7)]
                    self.history_data.append({
                        "period": row["期号"],
                        "date": row["日期"],
                        "reds": reds,
                        "blue": int(row["蓝球"]),
                    })
            return True
        except (OSError, csv.Error, ValueError, KeyError) as e:
            print(f"[错误] 数据读取失败: {e}")
            return False

    def _validate_row(self, row: Dict[str, str], line_no: int) -> bool:
        """校验单行CSV数据是否符合双色球规则。"""
        try:
            reds = [int(row[f"红球{i}"]) for i in range(1, 7)]
            blue = int(row["蓝球"])
        except (ValueError, KeyError) as e:
            print(f"[错误] 第{line_no}行数据类型异常: {e}")
            return False
        if not all(1 <= r <= 33 for r in reds):
            print(f"[错误] 第{line_no}行({row.get('期号', '?')})红球超出1-33: {reds}")
            return False
        if len(set(reds)) != 6:
            print(f"[错误] 第{line_no}行({row.get('期号', '?')})红球存在重复: {reds}")
            return False
        if not 1 <= blue <= 16:
            print(f"[错误] 第{line_no}行({row.get('期号', '?')})蓝球超出1-16: {blue}")
            return False
        if reds != sorted(reds):
            print(f"[错误] 第{line_no}行({row.get('期号', '?')})红球未升序: {reds}")
            return False
        return True

    def calculate_frequency(self) -> None:
        self.red_freq = Counter()
        self.blue_freq = Counter()
        for record in self.history_data:
            self.red_freq.update(record["reds"])
            self.blue_freq.update([record["blue"]])

    def calculate_omission(self) -> None:
        self.red_omission = {n: 0 for n in RED_BALLS}
        self.blue_omission = {n: 0 for n in BLUE_BALLS}
        for record in self.history_data:
            current_reds = set(record["reds"])
            current_blue = record["blue"]
            for n in RED_BALLS:
                self.red_omission[n] = 0 if n in current_reds else self.red_omission[n] + 1
            for n in BLUE_BALLS:
                self.blue_omission[n] = 0 if n == current_blue else self.blue_omission[n] + 1

    def _analyze(self) -> None:
        if not self.load_data():
            return
        self._loaded = True
        self.calculate_frequency()
        self.calculate_omission()

    def _get_recent_data(self, limit: int = 0) -> List[Dict]:
        """获取最近N期数据，limit=0表示全部数据。"""
        if limit <= 0:
            return self.history_data
        return self.history_data[-limit:]

    def calculate_frequency(self, limit: int = 0) -> None:
        self.red_freq = Counter()
        self.blue_freq = Counter()
        data = self._get_recent_data(limit)
        for record in data:
            self.red_freq.update(record["reds"])
            self.blue_freq.update([record["blue"]])

    def calculate_omission(self, limit: int = 0) -> None:
        self.red_omission = {n: 0 for n in RED_BALLS}
        self.blue_omission = {n: 0 for n in BLUE_BALLS}
        data = self._get_recent_data(limit)
        for record in data:
            current_reds = set(record["reds"])
            current_blue = record["blue"]
            for n in RED_BALLS:
                self.red_omission[n] = 0 if n in current_reds else self.red_omission[n] + 1
            for n in BLUE_BALLS:
                self.blue_omission[n] = 0 if n == current_blue else self.blue_omission[n] + 1

    @property
    def is_ready(self) -> bool:
        """分析器是否已就绪（数据加载成功）。"""
        return self._loaded and bool(self.history_data)

    def get_hot_red_balls(self, top_n: int = 5) -> List[int]:
        return [ball for ball, _ in self.red_freq.most_common(top_n)]

    def get_cold_red_balls(self, top_n: int = 5) -> List[int]:
        return sorted(RED_BALLS, key=lambda x: (self.red_freq[x], -self.red_omission[x]))[:top_n]

    def get_warm_red_balls(self) -> List[int]:
        if not self.red_freq:
            return []
        avg_freq = sum(self.red_freq.values()) / 33
        lo, hi = avg_freq * WARM_FREQ_RATIO[0], avg_freq * WARM_FREQ_RATIO[1]
        return sorted(b for b in RED_BALLS if lo <= self.red_freq[b] <= hi)

    def get_hot_blue_balls(self, top_n: int = 3) -> List[int]:
        return [ball for ball, _ in self.blue_freq.most_common(top_n)]

    def get_cold_blue_balls(self, top_n: int = 3) -> List[int]:
        return sorted(BLUE_BALLS, key=lambda x: (self.blue_freq[x], -self.blue_omission[x]))[:top_n]

    def get_high_omission_red(self, top_n: int = 5) -> List[int]:
        return sorted(RED_BALLS, key=lambda x: -self.red_omission[x])[:top_n]

    def get_high_omission_blue(self, top_n: int = 3) -> List[int]:
        return sorted(BLUE_BALLS, key=lambda x: -self.blue_omission[x])[:top_n]

    def analyze_interval(self) -> Dict[str, Dict[str, float]]:
        """三区间出号数量统计。"""
        interval_stats: Dict[str, List[int]] = {k: [] for k in INTERVALS}
        for record in self.history_data:
            for key, (lo, hi) in INTERVALS.items():
                count = sum(1 for r in record["reds"] if lo <= r <= hi)
                interval_stats[key].append(count)
        result: Dict[str, Dict[str, float]] = {}
        for key, counts in interval_stats.items():
            avg = sum(counts) / len(counts) if counts else 0.0
            mode = Counter(counts).most_common(1)[0][0] if counts else 0
            result[key] = {
                "平均": round(avg, 2),
                "众数": mode,
                "最小": min(counts) if counts else 0,
                "最大": max(counts) if counts else 0,
            }
        return result

    def analyze_parity(self) -> Dict:
        parity_stats: List[int] = [
            sum(1 for r in record["reds"] if r % 2 == 1)
            for record in self.history_data
        ]
        if not parity_stats:
            return {"平均奇数": 0.0, "众数奇数": 0, "分布": Counter()}
        avg = sum(parity_stats) / len(parity_stats)
        mode = Counter(parity_stats).most_common(1)[0][0]
        return {"平均奇数": round(avg, 2), "众数奇数": mode, "分布": Counter(parity_stats)}

    def analyze_size(self) -> Dict:
        size_stats: List[int] = [
            sum(1 for r in record["reds"] if r > 16)
            for record in self.history_data
        ]
        if not size_stats:
            return {"平均大数": 0.0, "众数大数": 0, "分布": Counter()}
        avg = sum(size_stats) / len(size_stats)
        mode = Counter(size_stats).most_common(1)[0][0]
        return {"平均大数": round(avg, 2), "众数大数": mode, "分布": Counter(size_stats)}

    def analyze_repeat(self, recent_n: int = 5) -> List[Tuple[int, int]]:
        recent = self.history_data[-recent_n:] if self.history_data else []
        recent_reds: List[int] = [r for rec in recent for r in rec["reds"]]
        repeat_counts = Counter(recent_reds)
        return sorted(
            [(b, c) for b, c in repeat_counts.items() if c >= 2],
            key=lambda x: -x[1],
        )

    def _build_freq_rank_map(self, balls: List[int]) -> Dict[int, int]:
        """按出现频率降序构造 号码->排名 映射（O(n log n) 一次计算）。"""
        sorted_balls = sorted(balls, key=lambda x: -self.red_freq[x] if x in self.red_freq else 0)
        return {ball: rank for rank, ball in enumerate(sorted_balls)}

    def _get_ball_category(self, ball: int) -> str:
        """判断号码冷热温类别（基于近10期频率）。"""
        freq = self.red_freq.get(ball, 0)
        if freq >= 4:
            return 'hot'
        elif freq >= 2:
            return 'warm'
        else:
            return 'cold'
    
    def _get_mod3_category(self, ball: int) -> int:
        """获取号码除3余数（0、1、2）。"""
        return ball % 3
    
    def _get_interval(self, ball: int) -> int:
        """获取号码所在区间（1=1-11, 2=12-22, 3=23-33）。"""
        if ball <= 11:
            return 1
        elif ball <= 22:
            return 2
        else:
            return 3
    
    def _get_tail(self, ball: int) -> int:
        """获取号码尾数。"""
        return ball % 10
    
    def predict_red_balls(self, count: int = RECOMMEND_RED_COUNT, return_dict: bool = False) -> any:
        """基于频率统计均衡法的红球预测（算法A：标准均衡配比）。
        
        采用行业通用的3热+2温+1冷配比，结合区间、奇偶、大小均衡筛选。
        """
        if count <= 0:
            return [] if not return_dict else {"balls": [], "reasons": {}}
        
        hot_balls = self.get_hot_red_balls(TOP_HOT)
        warm_balls = self.get_warm_red_balls()
        cold_balls = self.get_cold_red_balls(TOP_HOT)
        parity_info = self.analyze_parity()
        size_info = self.analyze_size()
        
        target_odd = int(round(parity_info["平均奇数"]))
        target_big = int(round(size_info["平均大数"]))
        
        candidates = []
        reasons = {}
        
        for ball in hot_balls[:3]:
            candidates.append(ball)
            reasons[ball] = "热号(高频)"
        
        for ball in warm_balls[:2]:
            candidates.append(ball)
            reasons[ball] = "温号(均衡)"
        
        for ball in cold_balls[:1]:
            candidates.append(ball)
            reasons[ball] = "冷号(回补)"
        
        if len(candidates) < count:
            remaining = count - len(candidates)
            all_balls = hot_balls + warm_balls + cold_balls
            for ball in all_balls:
                if ball not in candidates:
                    candidates.append(ball)
                    reasons[ball] = reasons.get(ball, "补充")
                    remaining -= 1
                    if remaining <= 0:
                        break
        
        if len(candidates) < count:
            for ball in RED_BALLS:
                if ball not in candidates:
                    candidates.append(ball)
                    reasons[ball] = "补充"
                    if len(candidates) >= count:
                        break
        
        candidates = self._adjust_interval_balance(candidates[:count])
        candidates = self._adjust_parity_balance(candidates, target_odd)
        candidates = self._adjust_size_balance(candidates, target_big)
        
        final_balls = sorted(candidates[:count])
        final_reasons = {ball: reasons.get(ball, "综合") for ball in final_balls}
        
        if return_dict:
            return {"balls": final_balls, "reasons": final_reasons}
        return final_balls
    
    def predict_red_balls_advanced(self, count: int = RECOMMEND_RED_COUNT, exclude_balls: List[int] = None) -> Dict[str, any]:
        """基于多维指标共振模型的红球预测（算法B：冷号+高遗漏偏好）。
        
        采用区间均衡选择、余数分类法、尾数关联法等多维度交叉验证。
        与算法A形成互补，优先选择冷号和高遗漏号码，尽量避开算法A选中的号码。
        """
        if count <= 0:
            return {"balls": [], "reasons": {}}
        
        exclude_set = set(exclude_balls) if exclude_balls else set()
        
        parity_info = self.analyze_parity()
        size_info = self.analyze_size()
        target_odd = int(round(parity_info["平均奇数"]))
        target_big = int(round(size_info["平均大数"]))
        
        mod3_counts = self._analyze_mod3()
        tail_counts = self._analyze_tail()
        interval_counts = self._analyze_interval_recent()
        
        recent_reds = set()
        for rec in self.history_data[-5:]:
            recent_reds.update(rec.get("reds", []))
        
        candidates_by_interval = {1: [], 2: [], 3: []}
        ball_reasons = {}
        
        for ball in RED_BALLS:
            if ball in exclude_set:
                continue
            
            score = 0
            reason_list = []
            interval = self._get_interval(ball)
            
            if ball in recent_reds:
                score -= 15
            else:
                reason_list.append("非近期")
            
            mod = ball % 3
            if mod3_counts.get(mod, 0) < 2:
                score += 25
                reason_list.append("余{}回补".format(mod))
            
            tail = ball % 10
            if tail_counts.get(tail, 0) == 0:
                score += 20
                reason_list.append("尾{}冷".format(tail))
            
            if interval_counts.get(interval, 0) <= 1:
                score += 20
                reason_list.append("区间{}缺".format(interval))
            
            omission = self.red_omission.get(ball, 0)
            if omission >= 10:
                score += omission * 4
                reason_list.append("高遗漏({}期)".format(omission))
            elif omission >= 6:
                score += omission * 3
                reason_list.append("遗漏({}期)".format(omission))
            
            freq = self.red_freq.get(ball, 0)
            if freq <= 1:
                score += 20
                reason_list.append("冷号")
            elif freq <= 2:
                score += 10
                reason_list.append("温号")
            
            if reason_list:
                ball_reasons[ball] = ",".join(reason_list[:3])
            candidates_by_interval[interval].append((ball, score))
        
        for interval in [1, 2, 3]:
            candidates_by_interval[interval].sort(key=lambda x: -x[1])
        
        selected = []
        selected_set = set()
        selected_intervals = {1: 0, 2: 0, 3: 0}
        
        round_count = 0
        while len(selected) < count:
            for interval in [1, 2, 3]:
                if len(selected) >= count:
                    break
                
                if selected_intervals[interval] >= 3:
                    continue
                
                candidates = candidates_by_interval[interval]
                for ball, _ in candidates:
                    if ball not in selected_set:
                        has_adjacent = False
                        for s in selected:
                            if abs(ball - s) == 1:
                                has_adjacent = True
                                break
                        if not has_adjacent or len(selected) == 0:
                            selected.append(ball)
                            selected_set.add(ball)
                            selected_intervals[interval] += 1
                            break
            
            round_count += 1
            if round_count > 10:
                break
        
        if len(selected) < count:
            for ball in RED_BALLS:
                if ball not in selected_set and ball not in exclude_set:
                    selected.append(ball)
                    selected_set.add(ball)
                    if len(selected) >= count:
                        break
        
        selected = self._adjust_interval_balance(selected[:count])
        selected = self._adjust_parity_balance(selected, target_odd)
        selected = self._adjust_size_balance(selected, target_big)
        
        final_balls = sorted(selected[:count])
        final_reasons = {ball: ball_reasons.get(ball, "综合") for ball in final_balls}
        
        return {"balls": final_balls, "reasons": final_reasons}
    
    def _analyze_mod3(self) -> Dict[int, int]:
        """分析近10期红球除3余数分布。"""
        recent = self.history_data[-10:] if self.history_data else []
        counts = {0: 0, 1: 0, 2: 0}
        for rec in recent:
            for ball in rec["reds"]:
                counts[ball % 3] += 1
        return counts
    
    def _analyze_tail(self) -> Dict[int, int]:
        """分析近5期红球尾数分布。"""
        recent = self.history_data[-5:] if self.history_data else []
        counts = {t: 0 for t in range(10)}
        for rec in recent:
            for ball in rec["reds"]:
                counts[ball % 10] += 1
        return counts
    
    def _analyze_interval_recent(self) -> Dict[int, int]:
        """分析近3期区间分布。"""
        recent = self.history_data[-3:] if self.history_data else []
        counts = {1: 0, 2: 0, 3: 0}
        for rec in recent:
            for ball in rec["reds"]:
                interval = 1 if ball <= 11 else (2 if ball <= 22 else 3)
                counts[interval] += 1
        return counts
    
    def _adjust_interval_balance(self, balls: List[int]) -> List[int]:
        """调整区间分布，使其符合2:2:2或3:2:1的均衡形态。"""
        if len(balls) != 6:
            return balls
        
        counts = {1: 0, 2: 0, 3: 0}
        for ball in balls:
            interval = 1 if ball <= 11 else (2 if ball <= 22 else 3)
            counts[interval] += 1
        
        max_interval = max(counts.items(), key=lambda x: x[1])[0]
        min_interval = min(counts.items(), key=lambda x: x[1])[0]
        
        if counts[min_interval] == 0:
            for ball in range(1 + (min_interval - 1) * 11, min_interval * 11 + 1):
                if ball not in balls:
                    max_balls = [b for b in balls if (1 if b <= 11 else (2 if b <= 22 else 3)) == max_interval]
                    if max_balls:
                        balls = [ball] + [b for b in balls if b != max_balls[0]]
                        break
        
        elif counts[max_interval] >= 4:
            for ball in range(1 + (min_interval - 1) * 11, min_interval * 11 + 1):
                if ball not in balls:
                    max_balls = [b for b in balls if (1 if b <= 11 else (2 if b <= 22 else 3)) == max_interval]
                    if max_balls:
                        balls = [ball] + [b for b in balls if b != max_balls[0]]
                        break
        
        return balls
    
    def _adjust_parity_balance(self, balls: List[int], target_odd: int) -> List[int]:
        """调整奇偶分布。"""
        current_odd = sum(1 for b in balls if b % 2 == 1)
        if current_odd == target_odd:
            return balls
        
        if current_odd < target_odd:
            for ball in RED_BALLS:
                if ball % 2 == 1 and ball not in balls:
                    even_balls = [b for b in balls if b % 2 == 0]
                    if even_balls:
                        balls = [ball] + [b for b in balls if b != even_balls[0]]
                        break
        else:
            for ball in RED_BALLS:
                if ball % 2 == 0 and ball not in balls:
                    odd_balls = [b for b in balls if b % 2 == 1]
                    if odd_balls:
                        balls = [ball] + [b for b in balls if b != odd_balls[0]]
                        break
        
        return balls
    
    def _adjust_size_balance(self, balls: List[int], target_big: int) -> List[int]:
        """调整大小分布。"""
        current_big = sum(1 for b in balls if b > 16)
        if current_big == target_big:
            return balls
        
        if current_big < target_big:
            for ball in range(17, 34):
                if ball not in balls:
                    small_balls = [b for b in balls if b <= 16]
                    if small_balls:
                        balls = [ball] + [b for b in balls if b != small_balls[0]]
                        break
        else:
            for ball in range(1, 17):
                if ball not in balls:
                    big_balls = [b for b in balls if b > 16]
                    if big_balls:
                        balls = [ball] + [b for b in balls if b != big_balls[0]]
                        break
        
        return balls

    def _adjust_balance(
        self,
        selected: List[int],
        selected_set: set,
        count: int,
        target_odd: int,
        target_big: int,
    ) -> List[int]:
        """根据奇偶/大小众数做轻量调整（不保证完全满足, 仅作偏好引导）。"""
        if len(selected) < count:
            return selected
        odd_now = sum(1 for b in selected if b % 2 == 1)
        big_now = sum(1 for b in selected if b > 16)
        if odd_now == target_odd and big_now == target_big:
            return selected
        return selected

    def predict_blue_ball(self) -> int:
        """基于综合评分的蓝球预测（算法A：频率+遗漏+多维均衡）。
        
        综合考虑频率、遗漏、奇偶、大小、尾数、余数等多维因素。
        """
        hot_blues = self.get_hot_blue_balls(TOP_BLUE_HOT)
        cold_blues = self.get_cold_blue_balls(TOP_BLUE_HOT)
        high_omission = self.get_high_omission_blue(TOP_BLUE_OMISSION)
        freq_rank = self._build_freq_rank_map(BLUE_BALLS)
        recent_blues = [rec["blue"] for rec in self.history_data[-5:] if "blue" in rec]
        
        parity_info = self.analyze_parity()
        size_info = self.analyze_size()
        target_odd = int(round(parity_info["平均奇数"]))
        target_big = int(round(size_info["平均大数"]))
        
        tail_counts = {}
        mod3_counts = {0: 0, 1: 0, 2: 0}
        for ball in [rec["blue"] for rec in self.history_data[-10:] if "blue" in rec]:
            tail = ball % 10
            tail_counts[tail] = tail_counts.get(tail, 0) + 1
            mod3_counts[ball % 3] += 1
        
        candidates = []
        for ball in BLUE_BALLS:
            if ball in recent_blues:
                continue
            
            score = 0.0
            
            if ball in hot_blues:
                score += 25
            if ball in high_omission:
                score += 20
            if ball in cold_blues:
                score += 15
            
            omission = self.blue_omission.get(ball, 0)
            if omission >= 8:
                score += omission * 2.5
            elif omission >= 5:
                score += omission * 1.5
            elif omission >= 3:
                score += omission
            
            freq_rank_score = max(0, 15 - freq_rank.get(ball, 16) * 0.5)
            score += freq_rank_score
            
            tail = ball % 10
            if tail_counts.get(tail, 0) <= 1:
                score += 12
            
            mod3 = ball % 3
            if mod3_counts.get(mod3, 0) <= 2:
                score += 10
            
            candidates.append((ball, score))
        
        candidates.sort(key=lambda x: -x[1])
        
        if candidates:
            return candidates[0][0]
        
        for ball in BLUE_BALLS:
            if ball not in recent_blues:
                return ball
        
        return BLUE_BALLS[0]

    def predict_blue_ball_advanced(self, exclude_ball: int = None) -> int:
        """基于冷号+高遗漏偏好的蓝球预测（算法B：反向策略）。
        
        与算法A形成互补，优先选择冷号和高遗漏号码，结合区间回补和尾数分布。
        """
        recent_blues = [rec["blue"] for rec in self.history_data[-5:] if "blue" in rec]
        cold_blues = self.get_cold_blue_balls(TOP_BLUE_HOT)
        high_omission = self.get_high_omission_blue(TOP_BLUE_OMISSION)
        
        tail_counts = {}
        mod3_counts = {0: 0, 1: 0, 2: 0}
        mod4_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        size_counts = {0: 0, 1: 0}
        parity_counts = {0: 0, 1: 0}
        
        for ball in [rec["blue"] for rec in self.history_data[-15:] if "blue" in rec]:
            tail = ball % 10
            tail_counts[tail] = tail_counts.get(tail, 0) + 1
            mod3_counts[ball % 3] += 1
            mod4_counts[ball % 4] += 1
            size_counts[0 if ball <= 8 else 1] += 1
            parity_counts[ball % 2] += 1
        
        candidates = []
        for ball in BLUE_BALLS:
            if ball == exclude_ball:
                continue
            if ball in recent_blues:
                continue
            
            score = 0
            
            if ball in cold_blues:
                score += 35
            
            if ball in high_omission:
                score += 30
            
            omission = self.blue_omission.get(ball, 0)
            if omission >= 10:
                score += omission * 4
            elif omission >= 6:
                score += omission * 2.5
            elif omission >= 4:
                score += omission * 1.5
            
            freq = self.blue_freq.get(ball, 0)
            avg_freq = sum(self.blue_freq.values()) / len(BLUE_BALLS)
            if freq < avg_freq * 0.6:
                score += 20
            
            tail = ball % 10
            if tail_counts.get(tail, 0) == 0:
                score += 25
            elif tail_counts.get(tail, 0) == 1:
                score += 15
            
            mod3 = ball % 3
            if mod3_counts.get(mod3, 0) <= 2:
                score += 15
            
            mod4 = ball % 4
            if mod4_counts.get(mod4, 0) <= 2:
                score += 10
            
            size = 0 if ball <= 8 else 1
            if size_counts.get(size, 0) <= 4:
                score += 12
            
            parity = ball % 2
            if parity_counts.get(parity, 0) <= 4:
                score += 12
            
            candidates.append((ball, score))
        
        candidates.sort(key=lambda x: -x[1])
        
        if candidates:
            return candidates[0][0]
        
        for ball in BLUE_BALLS:
            if ball != exclude_ball and ball not in recent_blues:
                return ball
        
        return BLUE_BALLS[0]

    def predict_blue_options(self, top_n: int = 5) -> List[int]:
        """返回按综合评分排序的蓝球候选(已排序)。"""
        hot_blues = self.get_hot_blue_balls(TOP_BLUE_HOT)
        high_omission = self.get_high_omission_blue(TOP_BLUE_OMISSION)
        freq_rank = self._build_freq_rank_map(BLUE_BALLS)
        scores: List[Tuple[int, float]] = []
        for ball in BLUE_BALLS:
            score = 0.0
            if ball in hot_blues:
                score += 30
            if ball in high_omission:
                score += 25
            score += max(0.0, 20 - freq_rank.get(ball, 0))
            omission = self.blue_omission[ball]
            if omission >= 6:
                score += omission * 2
            elif omission >= 3:
                score += omission
            scores.append((ball, score))
        scores.sort(key=lambda x: -x[1])
        return sorted(b for b, _ in scores[:top_n])
    
    def predict_with_params(
        self,
        hot_weight: float = 1.0,
        cold_weight: float = 1.0,
        omission_weight: float = 1.0,
        interval_weight: float = 1.0,
        parity_weight: float = 1.0,
        size_weight: float = 1.0,
        recent_penalty: float = 1.0,
        count: int = RECOMMEND_RED_COUNT
    ) -> Dict[str, any]:
        """基于自定义参数的动态预测方法。
        
        参数:
            hot_weight: 热号权重 (0-3)
            cold_weight: 冷号权重 (0-3)
            omission_weight: 遗漏值权重 (0-3)
            interval_weight: 区间均衡权重 (0-2)
            parity_weight: 奇偶均衡权重 (0-2)
            size_weight: 大小均衡权重 (0-2)
            recent_penalty: 近期重复惩罚系数 (0-2)
            count: 预测红球数量
        
        返回:
            包含红球、蓝球预测结果的字典
        """
        if count <= 0:
            count = RECOMMEND_RED_COUNT
        
        parity_info = self.analyze_parity()
        size_info = self.analyze_size()
        target_odd = int(round(parity_info["平均奇数"]))
        target_big = int(round(size_info["平均大数"]))
        
        hot_balls = self.get_hot_red_balls(TOP_HOT)
        cold_balls = self.get_cold_red_balls(TOP_HOT)
        warm_balls = self.get_warm_red_balls()
        
        mod3_counts = self._analyze_mod3()
        tail_counts = self._analyze_tail()
        interval_counts = self._analyze_interval_recent()
        
        recent_reds = set()
        for rec in self.history_data[-5:]:
            recent_reds.update(rec.get("reds", []))
        
        scores = []
        for ball in RED_BALLS:
            score = 0.0
            
            if ball in recent_reds:
                score -= 10 * recent_penalty
            
            if ball in hot_balls[:3]:
                score += 30 * hot_weight
            elif ball in hot_balls:
                score += 15 * hot_weight
            
            if ball in cold_balls[:3]:
                score += 30 * cold_weight
            elif ball in cold_balls:
                score += 15 * cold_weight
            
            if ball in warm_balls:
                score += 10 * (hot_weight + cold_weight) / 2
            
            omission = self.red_omission.get(ball, 0)
            if omission >= 10:
                score += omission * 4 * omission_weight
            elif omission >= 6:
                score += omission * 3 * omission_weight
            elif omission >= 3:
                score += omission * 2 * omission_weight
            elif omission >= 1:
                score += omission * omission_weight
            
            mod = ball % 3
            if mod3_counts.get(mod, 0) < 2:
                score += 15 * interval_weight
            
            tail = ball % 10
            if tail_counts.get(tail, 0) == 0:
                score += 10 * interval_weight
            
            interval = self._get_interval(ball)
            if interval_counts.get(interval, 0) <= 1:
                score += 15 * interval_weight
            
            freq = self.red_freq.get(ball, 0)
            if freq <= 1:
                score += 10 * cold_weight
            elif freq >= 4:
                score += 10 * hot_weight
            
            scores.append((ball, score))
        
        scores.sort(key=lambda x: -x[1])
        
        selected = []
        selected_set = set()
        selected_intervals = {1: 0, 2: 0, 3: 0}
        
        round_count = 0
        while len(selected) < count:
            for interval in [1, 2, 3]:
                if len(selected) >= count:
                    break
                
                max_in_interval = 3
                if interval_weight > 1.5:
                    max_in_interval = 2
                
                if selected_intervals[interval] >= max_in_interval:
                    continue
                
                for ball, _ in scores:
                    if ball not in selected_set:
                        ball_interval = self._get_interval(ball)
                        if ball_interval == interval:
                            has_adjacent = False
                            for s in selected:
                                if abs(ball - s) == 1:
                                    has_adjacent = True
                                    break
                            if not has_adjacent or len(selected) == 0:
                                selected.append(ball)
                                selected_set.add(ball)
                                selected_intervals[interval] += 1
                                break
            
            round_count += 1
            if round_count > 20:
                break
        
        if len(selected) < count:
            for ball, _ in scores:
                if ball not in selected_set:
                    selected.append(ball)
                    selected_set.add(ball)
                    if len(selected) >= count:
                        break
        
        if interval_weight > 0:
            selected = self._adjust_interval_balance(selected[:count])
        if parity_weight > 0:
            selected = self._adjust_parity_balance(selected, target_odd)
        if size_weight > 0:
            selected = self._adjust_size_balance(selected, target_big)
        
        red_balls = sorted(selected[:count])
        
        recent_blues = [rec["blue"] for rec in self.history_data[-5:] if "blue" in rec]
        blue_scores = []
        
        for ball in BLUE_BALLS:
            score = 0.0
            
            if ball in recent_blues:
                score -= 15 * recent_penalty
            
            if ball in self.get_hot_blue_balls(TOP_BLUE_HOT):
                score += 25 * hot_weight
            
            if ball in self.get_cold_blue_balls(TOP_BLUE_HOT):
                score += 25 * cold_weight
            
            omission = self.blue_omission.get(ball, 0)
            if omission >= 8:
                score += omission * 3 * omission_weight
            elif omission >= 5:
                score += omission * 2 * omission_weight
            elif omission >= 3:
                score += omission * omission_weight
            
            tail = ball % 10
            tail_counts_b = {}
            for b in recent_blues:
                tail_counts_b[b % 10] = tail_counts_b.get(b % 10, 0) + 1
            if tail_counts_b.get(tail, 0) == 0:
                score += 20 * interval_weight
            
            blue_scores.append((ball, score))
        
        blue_scores.sort(key=lambda x: -x[1])
        blue_ball = blue_scores[0][0]
        
        blue_options = sorted([b for b, _ in blue_scores[:6]])
        
        features = self.analyze_prediction_features(red_balls, blue_ball)
        
        return {
            "red_balls": red_balls,
            "blue_ball": blue_ball,
            "blue_options": blue_options,
            "features": features
        }

    def _fmt_balls(self, balls) -> str:
        return ", ".join(f"{int(b):02d}" for b in balls)

    def _interval_of(self, ball: int) -> str:
        for name, (lo, hi) in INTERVALS.items():
            if lo <= ball <= hi:
                return name
        return "未知"

    def _interval_count(self, balls: List[int]) -> Dict[str, int]:
        counts = {k: 0 for k in INTERVALS}
        for b in balls:
            counts[self._interval_of(b)] += 1
        return counts

    def generate_report(self) -> str:
        if not self.is_ready:
            return "[错误] 无可用历史数据, 无法生成报告。"
        latest = self.history_data[-1]
        total_periods = len(self.history_data)

        lines: List[str] = []
        sep = "=" * 60
        lines.append(sep)
        lines.append("          双色球智能分析系统 v2.0")
        lines.append(sep)
        lines.append("")
        lines.append(f"数据文件: {os.path.basename(self.data_file)}")
        lines.append(f"数据范围: {self.history_data[0]['period']} ~ {latest['period']} (共 {total_periods} 期)")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"最新一期: {latest['period']} ({latest['date']})")
        lines.append(f"  红球: {self._fmt_balls(latest['reds'])}")
        lines.append(f"  蓝球: {latest['blue']:02d}")

        # 一、红球频率
        lines.append("")
        lines.append(sep)
        lines.append("          一、红球频率分析")
        lines.append(sep)
        sorted_red = sorted(RED_BALLS, key=lambda x: -self.red_freq[x])
        lines.append("\n红球频率排名 (前10):")
        for i, ball in enumerate(sorted_red[:10], 1):
            lines.append(f"  {i:2d}. 红球{ball:02d}: 出现 {self.red_freq[ball]} 次")

        # 二、蓝球频率
        lines.append("")
        lines.append(sep)
        lines.append("          二、蓝球频率分析")
        lines.append(sep)
        sorted_blue = sorted(BLUE_BALLS, key=lambda x: -self.blue_freq[x])
        lines.append("\n蓝球频率排名 (前5):")
        for i, ball in enumerate(sorted_blue[:5], 1):
            lines.append(f"  {i:2d}. 蓝球{ball:02d}: 出现 {self.blue_freq[ball]} 次")

        # 三、遗漏值
        lines.append("")
        lines.append(sep)
        lines.append("          三、遗漏值分析")
        lines.append(sep)
        sorted_red_om = sorted(RED_BALLS, key=lambda x: -self.red_omission[x])
        lines.append("\n红球遗漏值排名 (遗漏最久前5):")
        for i, ball in enumerate(sorted_red_om[:5], 1):
            lines.append(f"  {i:2d}. 红球{ball:02d}: 遗漏 {self.red_omission[ball]} 期")
        sorted_blue_om = sorted(BLUE_BALLS, key=lambda x: -self.blue_omission[x])
        lines.append("\n蓝球遗漏值排名 (遗漏最久前3):")
        for i, ball in enumerate(sorted_blue_om[:3], 1):
            lines.append(f"  {i:2d}. 蓝球{ball:02d}: 遗漏 {self.blue_omission[ball]} 期")

        # 四、冷热号
        lines.append("")
        lines.append(sep)
        lines.append("          四、冷热号分析")
        lines.append(sep)
        lines.append("\n【热号】(频率最高):")
        lines.append(f"  红球: {self._fmt_balls(self.get_hot_red_balls(5))}")
        lines.append(f"  蓝球: {self._fmt_balls(self.get_hot_blue_balls(3))}")
        lines.append("\n【冷号】(频率最低):")
        lines.append(f"  红球: {self._fmt_balls(self.get_cold_red_balls(5))}")
        lines.append(f"  蓝球: {self._fmt_balls(self.get_cold_blue_balls(3))}")
        lines.append("\n【温号】(频率中等):")
        lines.append(f"  红球: {self._fmt_balls(self.get_warm_red_balls())}")

        # 五、区间分布
        lines.append("")
        lines.append(sep)
        lines.append("          五、区间分布分析")
        lines.append(sep)
        interval_info = self.analyze_interval()
        for key, (lo, hi) in INTERVALS.items():
            stats = interval_info[key]
            lines.append(f"\n{key} (号码 {lo:02d}-{hi:02d}):")
            lines.append(f"  平均每期: {stats['平均']} 个")
            lines.append(f"  出现次数最多: {stats['众数']} 个")
            lines.append(f"  范围: {stats['最小']} ~ {stats['最大']} 个")

        # 六、奇偶
        lines.append("")
        lines.append(sep)
        lines.append("          六、奇偶分析")
        lines.append(sep)
        parity_info = self.analyze_parity()
        lines.append(f"\n奇数号码分析:")
        lines.append(f"  平均每期: {parity_info['平均奇数']} 个")
        lines.append(f"  出现次数最多: {parity_info['众数奇数']} 个")
        lines.append("  分布统计:")
        for odd_count, freq in sorted(parity_info["分布"].items()):
            ratio = freq / total_periods * 100
            lines.append(f"    {odd_count}奇{6 - odd_count}偶: {freq}次 ({ratio:.1f}%)")

        # 七、大小
        lines.append("")
        lines.append(sep)
        lines.append("          七、大小分析")
        lines.append(sep)
        size_info = self.analyze_size()
        lines.append("\n大数号码分析(>16):")
        lines.append(f"  平均每期: {size_info['平均大数']} 个")
        lines.append(f"  出现次数最多: {size_info['众数大数']} 个")
        lines.append("  分布统计:")
        for big_count, freq in sorted(size_info["分布"].items()):
            ratio = freq / total_periods * 100
            lines.append(f"    {big_count}大{6 - big_count}小: {freq}次 ({ratio:.1f}%)")

        # 八、近5期重复
        lines.append("")
        lines.append(sep)
        lines.append("          八、近期重复号分析")
        lines.append(sep)
        repeats = self.analyze_repeat(5)
        if repeats:
            lines.append("\n近5期重复出现的红球:")
            for ball, count in repeats:
                lines.append(f"  红球{ball:02d}: 出现 {count} 次")
        else:
            lines.append("\n近5期无重复红球")

        # 九、预测
        lines.append("")
        lines.append(sep)
        lines.append("          九、下期预测")
        lines.append(sep)
        pred_red_result = self.predict_red_balls(RECOMMEND_RED_COUNT)
        pred_red = pred_red_result["balls"] if isinstance(pred_red_result, dict) else pred_red_result
        pred_blue = self.predict_blue_ball()
        pred_blue_options = self.predict_blue_options(5)

        lines.append("\n【预测红球】(6个):")
        lines.append(f"  {self._fmt_balls(pred_red)}")
        lines.append("\n【预测蓝球】(1个首选 + 5个备选):")
        lines.append(f"  首选: {pred_blue:02d}")
        lines.append(f"  备选: {self._fmt_balls(pred_blue_options)}")

        pred_parity = sum(1 for r in pred_red if r % 2 == 1)
        pred_size = sum(1 for r in pred_red if r > 16)
        lines.append("\n【预测号码特征】:")
        lines.append(f"  奇偶分布: {pred_parity}奇{6 - pred_parity}偶")
        lines.append(f"  大小分布: {pred_size}大{6 - pred_size}小")
        interval_counts = self._interval_count(pred_red)
        lines.append("  区间分布:")
        for key, cnt in interval_counts.items():
            lo, hi = INTERVALS[key]
            lines.append(f"    {key} ({lo:02d}-{hi:02d}): {cnt}个")

        # 十、风险提示
        lines.append("")
        lines.append(sep)
        lines.append("          十、风险提示")
        lines.append(sep)
        lines.append("")
        lines.append("  * 彩票开奖号码完全随机, 本分析仅供参考!")
        lines.append("  * 预测结果基于历史数据统计, 不保证准确性!")
        lines.append("  * 请理性购彩, 量力而行!")
        lines.append("")
        lines.append(sep)
        return "\n".join(lines)

    def save_report(self, filename: Optional[str] = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ssq_report_{timestamp}.txt"
        report = self.generate_report()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已保存至: {os.path.abspath(filename)}")
        return filename

    def analyze_prediction_features(self, red_balls: List[int], blue_ball: int) -> Dict[str, str]:
        """分析预测号码的特征（奇偶、大小、区间分布）。"""
        pred_parity = sum(1 for r in red_balls if r % 2 == 1)
        pred_size = sum(1 for r in red_balls if r > 16)
        interval_counts = self._interval_count(red_balls)
        
        interval_str = ", ".join(
            f"{key} {cnt}个" for key, cnt in interval_counts.items() if cnt > 0
        )
        
        return {
            "parity": f"{pred_parity}奇{6 - pred_parity}偶",
            "size": f"{pred_size}大{6 - pred_size}小",
            "interval": interval_str
        }


def main(data_file: str = "ssq_history.csv") -> None:
    analyzer = SSQAnalyzer(data_file)
    if not analyzer.is_ready:
        print("[失败] 未加载到历史数据, 请检查数据文件。")
        return
    report = analyzer.generate_report()
    print(report)
    analyzer.save_report()


def cmd_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="双色球智能分析系统")
    parser.add_argument("--update", action="store_true", help="先更新数据再分析")
    parser.add_argument("--force", action="store_true", help="强制全量更新")
    parser.add_argument("--check", action="store_true", help="仅检查更新")
    parser.add_argument("--file", default="ssq_history.csv", help="数据文件路径")
    args = parser.parse_args()

    if args.check or args.update:
        from ssq_updater import SSQUpdater

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
        print(f"[更新] {msg}")

    main(args.file)


if __name__ == "__main__":
    cmd_main()
