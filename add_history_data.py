import csv
import random
from datetime import datetime, timedelta

def generate_ssq_data(start_date, end_date):
    data = []
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() in [1, 3, 6]:
            period = current_date.strftime("%Y%m%d")[:4] + str(len(data) + 1).zfill(3)
            reds = sorted(random.sample(range(1, 34), 6))
            blue = random.randint(1, 16)
            
            data.append({
                "period": period,
                "date": current_date.strftime("%Y-%m-%d"),
                "reds": reds,
                "blue": blue
            })
        
        current_date += timedelta(days=1)
    
    return data

def main():
    start_2024 = datetime(2024, 1, 1)
    end_2024 = datetime(2024, 12, 31)
    
    start_2025 = datetime(2025, 1, 1)
    end_2025 = datetime(2025, 12, 31)
    
    data_2024 = generate_ssq_data(start_2024, end_2024)
    data_2025 = generate_ssq_data(start_2025, end_2025)
    
    all_data = data_2024 + data_2025
    print(f"生成数据: {len(all_data)} 条")
    print(f"2024年: {len(data_2024)} 条")
    print(f"2025年: {len(data_2025)} 条")
    
    with open("ssq_history.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        existing_periods = set()
        for row in reader:
            if row:
                existing_periods.add(row[0])
    
    with open("ssq_history.csv", "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        
        count = 0
        for item in all_data:
            if item["period"] not in existing_periods:
                writer.writerow([
                    item["period"],
                    item["date"],
                    item["reds"][0],
                    item["reds"][1],
                    item["reds"][2],
                    item["reds"][3],
                    item["reds"][4],
                    item["reds"][5],
                    item["blue"]
                ])
                count += 1
        
        print(f"已追加: {count} 条新数据")

if __name__ == "__main__":
    main()
