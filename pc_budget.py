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
import re
import urllib.parse

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

# シリーズ別グループの表示順 (カスタム構成モードの見出し用)
GROUP_ORDER = {
    "CPU": ["AMD Ryzen (AM5)", "AMD Ryzen (AM4)", "Intel Core Ultra (LGA1851)", "Intel Core (LGA1700)"],
    "GPU": ["GeForce RTX 50番台", "GeForce RTX 40番台", "GeForce RTX 30番台", "Radeon RX 9000番台", "Radeon RX 7000番台", "Radeon RX 6000番台", "Intel Arc"],
    "マザーボード": ["AM5", "AM4", "LGA1851", "LGA1700"],
}


# ============================================================
# 性能見積もり用スコア (PassMark: 2026-11-23 時点で調査)
# CPUは parts.csv の「名前」と完全一致で引く。
# GPUは製品名に含まれるチップ名で引く (ボードメーカーで性能はほぼ同じ)。
# ============================================================
CPU_SCORES = {
    "AMD Ryzen 5 5500": (3062, 19246),
    "AMD Ryzen 5 5600": (3254, 21489),
    "AMD Ryzen 5 5600X": (3366, 21820),
    "AMD Ryzen 7 5700X": (3386, 26536),
    "AMD Ryzen 7 5800X": (3449, 27649),
    "AMD Ryzen 9 5900X": (3465, 38880),
    "AMD Ryzen 5 4500": (2583, 15915),
    "AMD Ryzen 5 7500F": (3822, 26487),
    "AMD Ryzen 5 7600": (3907, 26964),
    "AMD Ryzen 5 7600X": (4127, 28254),
    "AMD Ryzen 7 7700": (4050, 34307),
    "AMD Ryzen 7 7700X": (4175, 35472),
    "AMD Ryzen 7 7800X3D": (3759, 34280),
    "AMD Ryzen 5 8500G": (3874, 21343),
    "AMD Ryzen 5 8600G": (3875, 25165),
    "AMD Ryzen 7 8700G": (3919, 31462),
    "AMD Ryzen 5 9600X": (4568, 30004),
    "AMD Ryzen 7 9700X": (4642, 36911),
    "AMD Ryzen 7 9800X3D": (4420, 39911),
    "AMD Ryzen 9 9900X": (4670, 54274),
    "AMD Ryzen 9 9900X3D": (4628, 56038),
    "AMD Ryzen 9 9950X": (4726, 65677),
    "AMD Ryzen 9 9950X3D": (4736, 70108),
    "Intel Core i5-12400F": (3483, 19516),
    "Intel Core i5-12400": (3466, 18836),
    "Intel Core i5-13400F": (3628, 24870),
    "Intel Core i3-12100F": (3431, 13949),
    "Intel Core i3-14100": (3761, 15097),
    "Intel Core i5-14600K": (4264, 38338),
    "Intel Core i7-14700K": (4453, 51886),
    "Intel Core Ultra 5 225": (4416, 30372),
    "Intel Core Ultra 5 245K": (4710, 42974),
    "Intel Core Ultra 5 245KF": (4719, 43041),
    "Intel Core Ultra 7 265K": (4928, 58565),
    "Intel Core Ultra 7 265KF": (4923, 58429),
    "Intel Core Ultra 9 285K": (5087, 67227),
}

# (チップ名, G3D Mark) 上から順に照合するので「Ti / XT」などの付くものを先に書く
GPU_CHIP_SCORES = [
    ("RTX 5090", 39035),
    ("RTX 5080", 35652),
    ("RTX 5070 Ti", 32330),
    ("RTX 5070", 28684),
    ("RTX 5060", 20580),
    ("RTX 5050", 16689),
    ("RTX 4060", 19477),
    ("RTX 3090 Ti", 29176),
    ("RTX 3090", 26456),
    ("RTX 3080 Ti", 26720),
    ("RTX 3080", 24966),
    ("RTX 3070 Ti", 23154),
    ("RTX 3070", 22059),
    ("RTX 3060 Ti", 20206),
    ("RTX 3060", 16872),
    ("RTX 3050", 12450),
    ("RX 9070 XT", 26929),
    ("RX 9070", 25374),
    ("RX 9060 XT", 20147),
    ("RX 7900 XTX", 31469),
    ("RX 7900 XT", 29127),
    ("RX 7900 GRE", 27455),
    ("RX 7800 XT", 24482),
    ("RX 7700 XT", 22797),
    ("RX 7600 XT", 17370),
    ("RX 7600", 16429),
    ("RX 6950 XT", 28079),
    ("RX 6900 XT", 26631),
    ("RX 6800 XT", 25118),
    ("RX 6800", 22045),
    ("RX 6750 XT", 20705),
    ("RX 6700 XT", 19712),
    ("RX 6650 XT", 17087),
    ("RX 6600 XT", 16447),
    ("RX 6600", 15030),
    ("RX 6500 XT", 9619),
    ("RX 6400", 7756),
    ("Arc B580", 16095),
    ("Arc B570", 14206),
    ("Arc A770", 13382),
    ("Arc A750", 12618),
    ("Arc A580", 12061),
    ("Arc A380", 6340),
    ("Arc A310", 5463),
]

LEVEL_LABELS = ["低め", "エントリー", "ミドル", "ミドルハイ", "ハイ", "最上位"]


def gpu_score_for(part_name):
    """GPU製品名からチップを判定して G3D Mark を返す。分からなければ None。"""
    # RTX 5060 Ti は VRAM容量で PassMark の値が分かれるので先に処理する
    if "RTX 5060 Ti" in part_name:
        return 22636 if "16GB" in part_name else 21755
    for chip, score in GPU_CHIP_SCORES:
        if chip in part_name:
            return score
    return None


def cpu_level(single):
    """シングルスレッドスコア → 0〜5 の性能レベル。"""
    if single >= 4400:
        return 5
    if single >= 3900:
        return 4
    if single >= 3400:
        return 3
    if single >= 3000:
        return 2
    if single >= 2600:
        return 1
    return 0


def gpu_level(g3d):
    """G3D Mark → 0〜5 の性能レベル。"""
    if g3d >= 30000:
        return 5
    if g3d >= 24000:
        return 4
    if g3d >= 19000:
        return 3
    if g3d >= 14000:
        return 2
    if g3d >= 9000:
        return 1
    return 0


def perf_estimate(selected):
    """選んだ構成の性能見積もり (スコア・バランス・VRChat目安) を行のリストで返す。"""
    lines = []
    cpu = selected.get("CPU")
    gpu = selected.get("GPU")
    cpu_sc = CPU_SCORES.get(cpu["名前"]) if cpu else None
    gpu_sc = gpu_score_for(gpu["名前"]) if gpu else None
    if not cpu_sc and not gpu_sc:
        return lines
    lines.append("🎮 性能見積もり (PassMark・2026-11-23時点の目安)")
    cl = gl = None
    if cpu_sc:
        cl = cpu_level(cpu_sc[0])
        lines.append(
            f"CPU性能: シングル {cpu_sc[0]:,} / マルチ {cpu_sc[1]:,} → {LEVEL_LABELS[cl]}クラス"
        )
        if "X3D" in cpu["名前"]:
            lines.append(
                "  ※X3Dは3D V-Cacheのおかげで、実際のゲーム/VRChatではシングルスコア以上の性能が出ることが多い"
            )
    if gpu_sc:
        gl = gpu_level(gpu_sc)
        lines.append(f"GPU性能: G3D Mark {gpu_sc:,} → {LEVEL_LABELS[gl]}クラス")
    elif gpu is None and cpu and cpu["内蔵GPU"] == "あり":
        lines.append("GPU性能: 内蔵GPU使用 (スコア目安なし・ゲーム性能は控えめ)")
    if cl is not None and gl is not None:
        diff = gl - cl
        if diff >= 2:
            lines.append(
                "バランス: ⚠ CPUボトルネック注意! GPUに対してCPUが弱めで、GPU使用率が上がりきらないタイプの組み合わせ"
            )
        elif diff == 1:
            lines.append("バランス: ややCPU寄り。高fpsを狙うとCPUが先に限界になりやすい")
        elif diff == 0:
            lines.append("バランス: 良好! CPUとGPUの釣り合いが取れている")
        elif diff == -1:
            lines.append("バランス: GPU寄りの構成。ゲームではGPUが先に上限になる普通のバランス")
        else:
            lines.append("バランス: GPUが弱めでCPUを持て余す組み合わせ。将来のGPU強化に余裕あり")
        weakest = min(cl, gl)
        if weakest >= 4:
            lines.append("VRChat目安: 重めのワールドでも戦えるクラス")
        elif weakest == 3:
            lines.append("VRChat目安: 概ね快適に遊べるクラス")
        elif weakest == 2:
            lines.append("VRChat目安: 軽〜中くらいのワールド向けクラス")
        elif weakest == 1:
            lines.append("VRChat目安: 軽いワールド向けクラス")
        else:
            lines.append("VRChat目安: 厳しめのクラス")
    elif cpu_sc or gpu_sc:
        lines.append("  (CPUとGPUの両方を選ぶとバランス判定も出るよ)")
    return lines


def buy_links(selected):
    """選んだ構成の購入先リンク (価格.com / Amazon の検索リンク) を行のリストで返す。

    最安の店は日々変わるので、商品ページ直リンクではなく検索リンクにしている。
    """
    lines = []
    for cat in CATEGORIES:
        if cat in selected:
            p = selected[cat]
            q = urllib.parse.quote(p["名前"], safe="")
            lines.append(f"[{cat}] {p['名前']}  ¥{p['価格']:,}")
            lines.append(f"  価格.comで探す: https://kakaku.com/search_results/{q}/")
            lines.append(f"  Amazonで探す: https://www.amazon.co.jp/s?k={q}")
    return lines


def series_of(p):
    """パーツが属するシリーズ名を返す (グループ表示用)。"""
    if p["カテゴリ"] == "CPU":
        if p["名前"].startswith("AMD"):
            return f"AMD Ryzen ({p['ソケット']})"
        if "Core Ultra" in p["名前"]:
            return f"Intel Core Ultra ({p['ソケット']})"
        return f"Intel Core ({p['ソケット']})"
    if p["カテゴリ"] == "GPU":
        m = re.search(r"RTX (\d)\d{3}", p["名前"])
        if m:
            return f"GeForce RTX {m.group(1)}0番台"
        r = re.search(r"RX (\d)\d{3}", p["名前"])
        if r:
            return f"Radeon RX {r.group(1)}000番台"
        if "Arc" in p["名前"]:
            return "Intel Arc"
    if p["カテゴリ"] == "マザーボード":
        return p["ソケット"]
    return ""


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
    for line in perf_estimate(pattern_selected(pattern_name, parts)):
        print(f"  {line}")
    links = buy_links(pattern_selected(pattern_name, parts))
    if links:
        print("  --- 購入リンクまとめ (検索リンク) ---")
        for line in links:
            print(f"  {line}")


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
        # シリーズ別に並べ替える (CPU / GPU / マザーボード)
        if cat in GROUP_ORDER:
            order = GROUP_ORDER[cat]
            options = sorted(
                options,
                key=lambda p: order.index(series_of(p)) if series_of(p) in order else 99,
            )
        print(f"\n[{cat}]")
        current_group = None
        for i, p in enumerate(options, start=1):
            g = series_of(p)
            if cat in GROUP_ORDER and g and g != current_group:
                print(f"  ― {g} ―")
                current_group = g
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

    # 性能見積もり
    lines = perf_estimate(selected)
    if lines:
        print()
        for line in lines:
            print(f"  {line}")

    # 購入リンクまとめ
    links = buy_links(selected)
    if links:
        print("\n--- 購入リンクまとめ (検索リンク) ---")
        for line in links:
            print(f"  {line}")


def main():
    parts = load_parts()
    print("自作PC予算計算ツール")
    print("価格データ: 価格.com / Amazon等 最安価格 (2026-11-23 時点) が基準")
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
