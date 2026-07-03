import csv

def main():
    with open("ssq_history.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = []
        for row in reader:
            if row:
                rows.append(row)
    
    rows.sort(key=lambda x: x[0])
    
    with open("ssq_history.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    
    print(f"已重新排序: {len(rows)} 条数据")
    print(f"最早期号: {rows[0][0]}")
    print(f"最新期号: {rows[-1][0]}")

if __name__ == "__main__":
    main()
