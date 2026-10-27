
import csv
from pathlib import Path

# File CSV gốc
input_file = Path("Raw Data/TMDB_movie_dataset_v11.csv")

# Thư mục chứa 9 file kết quả
output_dir = Path("tmdb_parts")
output_dir.mkdir(exist_ok=True)

NUM_PARTS = 9

# Đếm số dòng dữ liệu, không tính header
print("Counting rows...")
with input_file.open("r", encoding="utf-8-sig", newline="") as f:
    total_rows = sum(1 for _ in f) - 1

if total_rows <= 0:
    raise ValueError("CSV không có dữ liệu.")

rows_per_part = (total_rows + NUM_PARTS - 1) // NUM_PARTS

print(f"Total rows: {total_rows:,}")
print(f"Rows per part: approximately {rows_per_part:,}")

# Chia file
with input_file.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)

    part_number = 1
    rows_in_part = 0
    writer = None
    output_file = None

    try:
        for row in reader:
            if writer is None or rows_in_part >= rows_per_part:
                if output_file is not None:
                    output_file.close()

                output_path = (
                    output_dir / f"tmdb_part_{part_number}.csv"
                )

                output_file = output_path.open(
                    "w", encoding="utf-8", newline=""
                )
                writer = csv.writer(output_file)
                writer.writerow(header)

                print(f"Creating {output_path}")

                part_number += 1
                rows_in_part = 0

            writer.writerow(row)
            rows_in_part += 1

    finally:
        if output_file is not None:
            output_file.close()

print("\nDone!")
print(f"Output folder: {output_dir.resolve()}")
