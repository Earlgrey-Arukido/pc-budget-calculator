# -*- coding: utf-8 -*-
"""
自作PC予算計算ツール (pc_budget.py)

parts.csv に入っているパーツデータ(価格.comの最安価格が基準)を使って、
構成パターンごとの合計金額を計算したり、
予算に収まるパターンを探したりするツール。

使い方: python pc_budget.py
"""

import csv

# ============================================================
# 構成パターン
# parts.csv の「名前」と同じ文字列でパーツを指定する。
# パターンを増やしたいときは、ここに書き足すだけでOK。
# ============================================================
PATTERNS = {
    "AM4コスパゲーミング": [
        "AMD Ryzen 5 5600",
        "ASRock B550M-HDV",
        "Corsair DDR4-3200 32GB (16GBx2)",
        "ASRock Radeon RX 7600 Steel Legend 8GB OC",
        "KIOXIA EXCERIA PLUS G3 1TB",
        "Fractal Design ION Gold 750W",
        "NZXT H5 Flow",
    ],
    "VRChat向け AM4強化": [
        "AMD Ryzen 5 5600",
        "ASRock B550 Phantom Gaming 4",
        "Corsair DDR4-3200 32GB (16GBx2)",
        "Colorful GeForce RTX 5060 Gaming DUO 8GB",
        "KIOXIA EXCERIA PLUS G3 1TB",
        "Fractal Design ION Gold 750W",
        "NZXT H5 Flow",
    ],
    "AM5バランス": [
        "AMD Ryzen 5 7500F",
        "ASRock B650M PG Riptide WiFi White",
        "DDR5-5600 32GB (16GBx2) 最安クラス",
        "Colorful GeForce RTX 5060 Gaming DUO 8GB",
        "Samsung 990 PRO 1TB",
        "Fractal Design ION Gold 750W",
        "NZXT H5 Flow",
    ],
}


def load_parts(path="parts.csv"):
    """parts.csv を読み込んで、名前をキーにした辞書で返す。"""
    parts = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["価格"] = int(row["価格"])  # 文字列 → 数値に変換
            parts[row["名前"]] = row
    return parts


def pattern_total(pattern_name, parts):
    """1つの構成パターンの合計金額を計算する。"""
    total = 0
    for part_name in PATTERNS[pattern_name]:
        total += parts[part_name]["価格"]
    return total


def show_pattern(pattern_name, parts):
    """構成パターンの内訳と合計を表示する。"""
    print(f"\n=== {pattern_name} ===")
    for part_name in PATTERNS[pattern_name]:
        p = parts[part_name]
        print(f"  [{p['カテゴリ']}] {p['名前']}  ¥{p['価格']:,}")
    print(f"  合計: ¥{pattern_total(pattern_name, parts):,}")


def show_all_patterns(parts):
    """すべての構成パターンを表示する。"""
    for name in PATTERNS:
        show_pattern(name, parts)


def find_within_budget(parts):
    """予算を入力してもらい、収まるパターンを表示する。"""
    text = input("\n予算はいくら? (円, 数字だけ入力): ")
    budget = int(text)
    print(f"\n--- 予算 ¥{budget:,} に収まるパターン ---")
    found = False
    for name in PATTERNS:
        total = pattern_total(name, parts)
        if total <= budget:
            print(f"  ○ {name}: ¥{total:,} (残り ¥{budget - total:,})")
            found = True
        else:
            print(f"  × {name}: ¥{total:,} (¥{total - budget:,} オーバー)")
    if not found:
        print("  収まるパターンはなかった… パーツ価格の更新か予算アップが必要かも")


def show_all_parts(parts):
    """parts.csv の全パーツをカテゴリ順に表示する。"""
    print("\n--- パーツ一覧 (parts.csv) ---")
    for p in parts.values():
        print(f"  [{p['カテゴリ']}] {p['名前']}  ¥{p['価格']:,}  ({p['備考']})")


def main():
    parts = load_parts()
    print("自作PC予算計算ツール")
    print("価格データ: 価格.com 最安価格 (2026-11-23 時点) が基準")
    while True:
        print("\n何をする?")
        print("  1: 構成パターンの合計を見る")
        print("  2: 予算に収まるパターンを探す")
        print("  3: パーツ一覧を見る")
        print("  0: 終了")
        choice = input("番号を入力: ")
        if choice == "1":
            show_all_patterns(parts)
        elif choice == "2":
            find_within_budget(parts)
        elif choice == "3":
            show_all_parts(parts)
        elif choice == "0":
            print("またね!")
            break
        else:
            print("その番号はないよ。0〜3で選んでね")


if __name__ == "__main__":
    main()
