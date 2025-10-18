import csv, os, time
from contextlib import contextmanager

class CSVLogger:
    def __init__(self, csv_path, header):
        self.csv_path = csv_path
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(header)

    def log(self, row):
        with open(self.csv_path, "a", newline="") as f:
            w = csv.writer(f)
            w.writerow(row)

@contextmanager
def timer():
    t0 = time.time()
    yield
    t1 = time.time()
    print(f"[timer] {t1 - t0:.3f}s")
