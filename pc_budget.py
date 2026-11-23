# -*- coding: utf-8 -*-
"""
自作PC予算計算ツール (pc_budget.py)

parts.csv に入っているパーツデータ(価格.comの最安価格が基準)を使って、
構成パターンごとの合計金額を計算したり、
予算に収まるパターンを探したり、
自分でパーツを1つずつ選んで互換性チェック付きで構成を作ったりするツール。

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
    "AM5 VRChat本気": [
        "AMD Ryzen 7 7800X3D",
        "Thermalright Peerless Assassin 120 SE V3",
        "MSI MAG B650 TOMAHAWK WIFI",
        "ADATA XPG LANCER BLADE DDR5-6000 32GB (16GBx2)",
        "ASRock Radeon RX 9070 Challenger 16GB",
        "Samsung 990 PRO 2TB",
        "Corsair RM750e 2025 750W",
        "Fractal Design Pop Air Solid",
    ],
    "Intel入門": [
        "Intel Core i5-12400F",
        "ASRock B760M-HDV/M.2 D4",
        "Silicon Power DDR4-3200 16GB (8GBx2)",
        "ASRock Radeon RX 7600 Steel Legend 8GB OC",
        "WD_BLACK SN7100 1TB",
        "GIGABYTE P550B 550W",
        "MONTECH XR",
    ],
}

# カスタム構成モードで選ぶカテゴリの順番
CATEGORIES = ["CPU", "CPUクーラー", "マザーボード", "メモリ", "GPU", "SSD", "電源", "ケース", "OS"]


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


def pattern_selected(pattern_name, parts):
    """構成パターンのパーツを「カテゴリ → パーツ」の辞書にする。"""
    selected = {}
    for part_name in PATTERNS[pattern_name]:
        p = parts[part_name]
        selected[p["カテゴリ"]] = p
    return selected


def show_pattern(pattern_name, parts):
    """構成パターンの内訳と合計を表示する。"""
    print(f"\n=== {pattern_name} ===")
    for part_name in PATTERNS[pattern_name]:
        p = parts[part_name]
        print(f"  [{p['カテゴリ']}] {p['名前']}  ¥{p['価格']:,}")
    print(f"  合計: ¥{pattern_total(pattern_name, parts):,}")
    warnings = check_compatibility(pattern_selected(pattern_name, parts))
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")


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


# ============================================================
# カスタム構成モード + 互換性チェック
# ============================================================
def mem_matches(mem_spec, cpu_spec):
    """メモリ規格がCPUの対応規格に合っているか判定する。

    CPU側が "DDR4/DDR5" のように両対応の場合は、どちらでもOKとする。
    """
    return mem_spec in cpu_spec.split("/")


def check_compatibility(selected):
    """選んだパーツ同士の互換性をチェックして、警告のリストを返す。

    チェック内容:
    - CPUとマザーボードのソケット (AM4 / AM5 / LGA1700) が合っているか
    - メモリ規格 (DDR4 / DDR5) がマザーボード・CPUと合っているか
    - GPUなしで、CPUにも内蔵GPUがない場合は画面が出ない警告
    - クーラー別売りのCPUなのにクーラーが選ばれていない警告
    - ATXマザーボードがMicroATX専用ケースに入らない警告
    """
    warnings = []
    cpu = selected.get("CPU")
    cooler = selected.get("CPUクーラー")
    mb = selected.get("マザーボード")
    mem = selected.get("メモリ")
    gpu = selected.get("GPU")
    case = selected.get("ケース")

    if cpu and mb and cpu["ソケット"] != mb["ソケット"]:
        warnings.append(
            f"CPUのソケット({cpu['ソケット']})とマザーボードのソケット({mb['ソケット']})が違う! この組み合わせでは付きません"
        )
    if mem and mb and mem["メモリ規格"] != mb["メモリ規格"]:
        warnings.append(
            f"メモリ({mem['メモリ規格']})がマザーボードの対応規格({mb['メモリ規格']})と違う! 物理的に刺さりません"
        )
    if mem and cpu and not mem_matches(mem["メモリ規格"], cpu["メモリ規格"]):
        warnings.append(
            f"メモリ({mem['メモリ規格']})がCPUの対応規格({cpu['メモリ規格']})と違う!"
        )
    if cpu and not gpu and cpu["内蔵GPU"] == "なし":
        warnings.append(
            "GPUが選ばれていないのに、選んだCPUには内蔵GPUがない! このままだと画面が出ません"
        )
    if cpu and not cooler and cpu["クーラー付属"] == "なし":
        warnings.append(
            "選んだCPUはクーラー別売りなのに、CPUクーラーが選ばれていない! これでは冷やせません"
        )
    # フォームファクタ: マザーボードのサイズがケースに入る最大サイズを超えたら警告
    size_rank = {"ATX": 3, "MicroATX": 2, "Mini-ITX": 1}
    if mb and case:
        board_size = size_rank.get(mb["フォームファクタ"], 0)
        case_size = size_rank.get(case["フォームファクタ"], 0)
        if board_size and case_size and board_size > case_size:
            warnings.append(
                f"{mb['フォームファクタ']}マザーボードは{case['フォームファクタ']}まで対応のケースに入りません!"
            )
    return warnings


def custom_build(parts):
    """カテゴリごとにパーツを1つずつ選んで、合計と互換性を表示する。"""
    # カテゴリごとにパーツをグループ化する
    grouped = {c: [] for c in CATEGORIES}
    for p in parts.values():
        grouped[p["カテゴリ"]].append(p)

    selected = {}
    print("\n--- カスタム構成モード ---")
    print("カテゴリごとに番号で選んでね。0 は「選ばない」")
    for cat in CATEGORIES:
        options = grouped[cat]
        print(f"\n[{cat}]")
        for i, p in enumerate(options, start=1):
            print(f"  {i}: {p['名前']}  ¥{p['価格']:,}")
        print("  0: 選ばない")
        while True:
            text = input(f"{cat} の番号: ")
            if text.isdigit() and 0 <= int(text) <= len(options):
                break
            print("その番号はないよ。もう一度選んでね")
        num = int(text)
        if num > 0:
            selected[cat] = options[num - 1]

    # 結果表示
    print("\n=== あなたの構成 ===")
    total = 0
    for cat in CATEGORIES:
        if cat in selected:
            p = selected[cat]
            print(f"  [{cat}] {p['名前']}  ¥{p['価格']:,}")
            total += p["価格"]
        else:
            print(f"  [{cat}] (なし)")
    print(f"  合計: ¥{total:,}")

    # 互換性チェック
    print("\n--- 互換性チェック ---")
    warnings = check_compatibility(selected)
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        print("  問題なし! ソケットとメモリ規格は合っています")


def main():
    parts = load_parts()
    print("自作PC予算計算ツール")
    print("価格データ: 価格.com 最安価格 (2026-11-23 時点) が基準")
    while True:
        print("\n何をする?")
        print("  1: 構成パターンの合計を見る")
        print("  2: 予算に収まるパターンを探す")
        print("  3: パーツ一覧を見る")
        print("  4: カスタム構成を作る (互換性チェック付き)")
        print("  0: 終了")
        choice = input("番号を入力: ")
        if choice == "1":
            show_all_patterns(parts)
        elif choice == "2":
            find_within_budget(parts)
        elif choice == "3":
            show_all_parts(parts)
        elif choice == "4":
            custom_build(parts)
        elif choice == "0":
            print("またね!")
            break
        else:
            print("その番号はないよ。0〜4で選んでね")


if __name__ == "__main__":
    main()
