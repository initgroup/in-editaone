"""Reproduce the fictional demo CSV. No customer data or external services."""
import csv
import random
from pathlib import Path


def generate(destination):
    rng = random.Random(20261026)
    with Path(destination).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["고객유형", "배송유형", "상품금액", "할인금액", "배송비", "공급가액", "부가세", "결제금액"])
        for index in range(2400):
            group = index % 3
            amount = rng.randrange(100, 3000) * 100
            discount = rng.randrange(0, 50) * 100
            shipping = [2500, 4000, 0][group]
            supply = amount - discount
            tax = supply // 10
            # Deliberate fictional entry errors let the demo discover rules and
            # inspect real disagreements; production rules are never fabricated.
            delivery = ["일반배송", "빠른배송", "무료배송"][(group + (index % 89 == 0)) % 3]
            payment = supply + tax + shipping + (1100 if index % 97 == 0 else 0)
            writer.writerow([["일반", "우수", "VIP"][group], delivery,
                             amount, discount, shipping, supply, tax, payment])


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[2] / "simple-edit" / "sample.csv")
