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
import math
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
    "GPU": ["GeForce RTX 50番台", "GeForce RTX 40番台", "GeForce RTX 30番台", "Radeon RX 9000番台", "Radeon RX 7000番台", "Radeon RX 6000番台", "Radeon RX 500番台", "Intel Arc"],
    "マザーボード": ["AM5", "AM4", "LGA1851", "LGA1700"],
}


# ============================================================
# 性能見積もり用スコア (PassMark: 2026-11-23 時点で調査)
# CPUは parts.csv の「名前」と完全一致で引く。
# GPUは製品名に含まれるチップ名で引く (ボードメーカーで性能はほぼ同じ)。
# ============================================================
# 価格・中古相場データの調査日
DATA_DATE = "2026-11-23"

# GPUの消費電力 (TDP・メーカー公称の目安)
GPU_TDP = [
    ("RTX 5090", 575), ("RTX 5080", 360), ("RTX 5070 Ti", 300), ("RTX 5070", 250),
    ("RTX 5060 Ti", 180), ("RTX 5060", 145), ("RTX 5050", 130), ("RTX 4060", 115),
    ("RTX 3090 Ti", 450), ("RTX 3090", 350), ("RTX 3080 Ti", 350), ("RTX 3080", 320),
    ("RTX 3070 Ti", 290), ("RTX 3070", 220), ("RTX 3060 Ti", 200), ("RTX 3060", 170),
    ("RTX 3050", 130),
    ("RX 9070 XT", 304), ("RX 9070", 220), ("RX 9060 XT", 182),
    ("RX 7900 XTX", 355), ("RX 7900 XT", 315), ("RX 7900 GRE", 260), ("RX 7800 XT", 263),
    ("RX 7700 XT", 245), ("RX 7600 XT", 190), ("RX 7600", 165),
    ("RX 6950 XT", 335), ("RX 6900 XT", 300), ("RX 6800 XT", 300), ("RX 6800", 250),
    ("RX 6750 XT", 250), ("RX 6700 XT", 230), ("RX 6650 XT", 180), ("RX 6600 XT", 160),
    ("RX 6600", 132), ("RX 6500 XT", 107), ("RX 6400", 53), ("RX 580", 185),
    ("Arc B580", 190), ("Arc B570", 150), ("Arc A770", 225), ("Arc A750", 225),
    ("Arc A580", 175), ("Arc A380", 75), ("Arc A310", 75),
]

# CPUの最大消費電力の目安 (PPT / PL2 相当)
CPU_POWER = {
    "Ryzen 7 5800X": 142, "Ryzen 7 5800XT": 142, "Ryzen 7 5800X3D": 142,
    "Ryzen 9 5900X": 142, "Ryzen 9 5900XT": 142, "Ryzen 7 3800XT": 142,
    "Ryzen 9 3900XT": 171, "Ryzen 5 5600X": 88, "Ryzen 5 5600XT": 88,
    "Ryzen 5 5600": 88, "Ryzen 5 5500": 88, "Ryzen 7 5700X": 88, "Ryzen 5 4500": 88,
    "Ryzen 5 7600X": 142, "Ryzen 7 7700X": 142, "Ryzen 5 7500F": 88,
    "Ryzen 5 7600": 88, "Ryzen 7 7700": 88, "Ryzen 7 7800X3D": 162,
    "Ryzen 5 8500G": 88, "Ryzen 5 8600G": 88, "Ryzen 7 8700G": 88,
    "Ryzen 5 9600X": 88, "Ryzen 7 9700X": 88, "Ryzen 7 9800X3D": 162,
    "Ryzen 9 9900X": 162, "Ryzen 9 9900X3D": 162, "Ryzen 9 9950X": 230,
    "Ryzen 9 9950X3D": 230, "Ryzen 9 7900X3D": 162, "Ryzen 9 7950X3D": 162,
    "Core i5-12400F": 117, "Core i5-12400": 117, "Core i5-13400F": 148,
    "Core i3-12100F": 89, "Core i3-14100": 110, "Core i5-14600K": 181,
    "Core i7-14700K": 219, "Core Ultra 5 225": 121, "Core Ultra 5 245KF": 159,
    "Core Ultra 5 245K": 159, "Core Ultra 7 265KF": 250, "Core Ultra 7 265K": 250,
    "Core Ultra 9 285K": 250,
}

# 名前にWi-Fi表記が無いが実際は搭載しているボード
WIFI_BOARDS = {"GIGABYTE B850I AORUS PRO"}

# パターンの説明 (どんな人向けか)
PATTERN_INFO = {
    "AM4コスパゲーミング": "予算重視でゲームを遊びたい人向け。前世代AM4で安く組む構成",
    "VRChat向け AM4強化": "VRChatを快適に遊びたい人向け。AM4のままCPUとGPUを強化した構成",
    "AM5バランス": "今から長く使いたい人向け。現行AM5のバランス型構成",
    "AM5 VRChat本気": "VRChatを重いワールドでも快適に遊びたい人向け。AM5ハイエンド構成",
    "Intel入門": "Intelで安く始めたい人向けの入門構成",
}

# GPUのカード長 (mm・メーカー公式/価格.com仕様欄で確認。2026-11-23調査)
GPU_LENGTH = {
    "ASRock Radeon RX 7600 Steel Legend 8GB OC": 303,
    "Colorful GeForce RTX 5060 Battle AX DUO 8GB": 231,
    "Colorful GeForce RTX 5060 Gaming DUO 8GB": 200,
    "玄人志向 Radeon RX 7800 XT 16GB": 322,
    "ASRock Radeon RX 9060 XT Challenger 16GB OC": 249,
    "ASRock Radeon RX 9070 Challenger 16GB": 290,
    "PNY GeForce RTX 5060 Ti 16GB OC Dual Fan": 245,
    "Palit GeForce RTX 5070 Infinity 3 12GB": 292,
    "GIGABYTE AORUS GeForce RTX 5090 ICE 32GB": 360,
    "Palit GeForce RTX 5080 Infinity 3 16GB": 332,
    "Palit GeForce RTX 5070 Ti GamingPro-S 16GB": 332,
    "ASUS PRIME Radeon RX 9070 XT 16GB": 312,
    "Colorful GeForce RTX 5060 Ti Gaming DUO 8GB": 200,
    "玄人志向 Radeon RX 9060 XT 8GB": 200,
    "MSI GeForce RTX 4060 VENTUS 2X BLACK 8G OC": 199,
    "ASRock Intel Arc B570 Challenger 10GB OC": 249,
    "Colorful GeForce RTX 5050 Gaming DUO 8GB": 200,
    "MSI GeForce RTX 3090 Ti SUPRIM X 24G": 338,
    "MSI GeForce RTX 3090 GAMING X TRIO 24G": 323,
    "GAINWARD GeForce RTX 3080 Ti Phoenix 12GB": 294,
    "MSI GeForce RTX 3080 GAMING Z TRIO 12G": 323,
    "玄人志向 GALAKURO GeForce RTX 3070 Ti 8GB": 285,
    "玄人志向 GALAKURO GeForce RTX 3070 8GB OC": 285,
    "玄人志向 GALAKURO GeForce RTX 3060 Ti 8GB WHITE": 285,
    "Colorful GeForce RTX 3060 Battle AX DUO 12GB": 254,
    "MSI GeForce RTX 3060 VENTUS 2X 8G OC": 235,
    "MSI GeForce RTX 3050 VENTUS 2X XS 8G OC": 205,
    "GIGABYTE GeForce RTX 3050 WINDFORCE OC 6GB": 191,
    "XFX Radeon RX 7900 XT 20GB": 277,
    "GIGABYTE Radeon RX 7600 XT GAMING OC 16GB": 282,
    "MSI Radeon RX 6950 XT GAMING X TRIO 16G": 325,
    "MSI Radeon RX 6900 XT GAMING X TRIO 16G": 324,
    "MSI Radeon RX 6800 XT GAMING X TRIO 16G": 324,
    "ASUS ROG STRIX Radeon RX 6800 16GB": 320,
    "MSI Radeon RX 6750 XT MECH 2X 12G OC": 249,
    "MSI Radeon RX 6700 XT MECH 2X 12G OC": 247,
    "SAPPHIRE PULSE Radeon RX 6650 XT 8GB": 240,
    "MSI Radeon RX 6600 XT GAMING X 8G": 277,
    "XFX Radeon RX 6600 8GB": 241,
    "MSI Radeon RX 6500 XT MECH 2X 4G OC": 172,
    "玄人志向 Radeon RX 6400 LP 4GB": 152,
    "ASRock Intel Arc A770 Phantom Gaming D 8GB OC": 305,
    "SPARKLE Intel Arc A750 TITAN OC 8GB": 306,
    "SPARKLE Intel Arc A380 ELF 6GB": 153,
    "玄人志向 Intel Arc A310 4GB": 145,
    "SAPPHIRE NITRO+ Radeon RX 7700 XT 12G": 320,
    "Acer Predator BiFrost Intel Arc A770 16GB OC": 267,
    "XFX MERC 310 Radeon RX 7900 XTX 24GB": 344,
    "GIGABYTE Radeon RX 7900 GRE GAMING OC 16GB": 302,
    "玄人志向 Intel Arc B580 12GB": 242,
    "ASRock Intel Arc A580 Challenger 8GB OC": 271,
    "ASRock Phantom Gaming D Radeon RX 580 8GB": 237,
}

# ケースの上限 (GPU最大長mm, CPUクーラー最大高mm)。ファン搭載時の実用値で統一
CASE_LIMITS = {
    "ZALMAN Z3 Iceberg Black": (315, 163),
    "MONTECH XR": (420, 175),
    "NZXT H3 Flow": (352, 170),
    "NZXT H5 Flow": (410, 170),
    "Fractal Design Pop Air Solid": (405, 170),
    "Corsair 3500X Tempered Glass Black": (410, 170),
    "LIAN LI LANCOOL 216": (392, 180),
    "MONTECH KING 95 PRO": (420, 175),
    "Fractal Design North White": (355, 170),
    "Fractal Design Terra": (322, 77),
    "DEEPCOOL CH260": (388, 174),
}

# CPUクーラーの高さ (mm)。簡易水冷は None (高さチェック対象外)
COOLER_HEIGHT = {
    "サイズ 虎徹 MARK4 SCKTT-4000": 155,
    "DEEPCOOL AG400 G2": 152,
    "DEEPCOOL AK400": 155,
    "Thermalright Peerless Assassin 120 SE V3": 155,
    "DEEPCOOL LE240 V2": None,
    "玄人志向 KURO-AIOWC360/V2": None,
    "Noctua NH-U12A": 158,
    "Scythe FUMA 3": 154,
    "Fractal Design Lumen S28 v2": None,
    "DEEPCOOL AK620": 160,
    "Noctua NH-D15 G2": 168,
    "Thermalright Phantom Spirit 120 SE": 154,
}

# マザーボードのメモリスロット数
MB_SLOTS = {
    "ASRock B550M-HDV": 2, "ASRock B550 Phantom Gaming 4": 4,
    "MSI B550M PRO-VDH WIFI": 4, "ASRock B650M PG Riptide WiFi White": 4,
    "MSI MAG B650 TOMAHAWK WIFI": 4, "ASRock B760M-HDV/M.2 D4": 2,
    "MSI B760 GAMING PLUS WIFI": 4, "ASUS PRIME A520M-K ARGB-CSM": 2,
    "ASUS PRIME H610M-R D4": 2, "ASUS PRIME A620M-K-CSM": 2,
    "ASRock B850M-X WiFi R2.0": 2, "ASUS PRIME B840-PLUS WIFI-CSM": 4,
    "GIGABYTE B860 DS3H": 4, "ASUS PRIME Z890-P WIFI-CSM": 4,
    "MSI PRO Z790-P WIFI": 4, "ASRock X870 Pro-A WiFi": 4,
    "GIGABYTE B850I AORUS PRO": 2, "GIGABYTE X870E AORUS ELITE WIFI7": 4,
    "MSI MPG B650I EDGE WIFI": 2,
}

CPU_SCORES = {
    "AMD Ryzen 5 5500": (3062, 19246),
    "AMD Ryzen 5 5600": (3254, 21489),
    "AMD Ryzen 5 5600X": (3366, 21820),
    "AMD Ryzen 7 5700X": (3386, 26536),
    "AMD Ryzen 7 5800X": (3449, 27649),
    "AMD Ryzen 9 5900X": (3465, 38880),
    "AMD Ryzen 7 3800XT": (2797, 23392),
    "AMD Ryzen 9 3900XT": (2743, 32446),
    "AMD Ryzen 5 5600XT": (3468, 22258),
    "AMD Ryzen 7 5800XT": (3532, 28018),
    "AMD Ryzen 9 5900XT": (3479, 43858),
    "AMD Ryzen 7 5800X3D": (3234, 28291),
    "AMD Ryzen 9 7900X3D": (4118, 50197),
    "AMD Ryzen 9 7950X3D": (4144, 62306),
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
    ("RX 580", 8781),
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


def gpu_tdp_for(part_name):
    """GPU製品名からチップを判定して TDP (W) を返す。分からなければ None。"""
    if "RTX 3050" in part_name and "6GB" in part_name:
        return 70  # RTX 3050 6GB版は低消費電力モデル
    for chip, tdp in GPU_TDP:
        if chip in part_name:
            return tdp
    return None


def cpu_power_for(part_name):
    """CPU製品名から最大消費電力の目安 (W) を返す。分からなければ None。"""
    for model, watts in CPU_POWER.items():
        if model in part_name:
            return watts
    return None


def psu_wattage(p):
    """電源パーツの名前から容量 (W) を読み取る。"""
    m = re.search(r"(\d{3,4})\s*W", p["名前"])
    return int(m.group(1)) if m else None


def power_check(selected):
    """電源容量チェック。結果の行リストを返す (必要なパーツが揃っていない場合は空)。"""
    gpu = selected.get("GPU")
    cpu = selected.get("CPU")
    psu = selected.get("電源")
    if not (gpu and cpu and psu):
        return []
    gt = gpu_tdp_for(gpu["名前"])
    cw = cpu_power_for(cpu["名前"])
    w = psu_wattage(psu)
    if gt is None or cw is None or w is None:
        return []
    est = gt + cw + 100  # +100W はマザーボード・SSD・ファン等の分
    rec = math.ceil(est * 1.25 / 50) * 50  # 推奨容量 = 推定最大×1.25 を50W単位で切り上げ
    lines = [f"🔌 電源チェック: 推定最大消費電力 約{est}W (GPU {gt}W + CPU {cw}W + その他 100W) / 推奨電源 {rec}W / 選択中の電源 {w}W"]
    if w < est:
        lines.append("  ⚠ 電源容量が推定最大消費電力を下回っています。容量の大きい電源を推奨します")
    elif w < rec:
        lines.append("  △ 最低ラインは満たしますが、電源容量の余裕が少なめです")
    else:
        lines.append("  ✓ 電源容量に余裕があります")
    if "RTX 50" in gpu["名前"]:
        lines.append("  ℹ RTX 50系は12V-2x6コネクタを使います (変換アダプタはGPUに付属)。ATX 3.x対応電源だとケーブル1本で接続できます")
    return lines


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
        r3 = re.search(r"RX (\d)\d{2}\b", p["名前"])
        if r3:
            return f"Radeon RX {r3.group(1)}00番台"
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
            used = row.get("中古価格") or ""
            row["中古価格"] = int(used) if used else None
            parts[row["名前"]] = row
    return parts


def price_of(p, mode):
    """価格モード (new / used) に応じた価格を返す。対象外なら None。

    - 区分が「中古」のパーツ (RX 580など) は中古モードでのみ使える (価格=中古相場)
    - 通常パーツは新品モードでは価格、中古モードでは中古価格 (未調査なら None)
    """
    if mode == "used":
        if p.get("区分") == "中古":
            return p["価格"]
        return p["中古価格"]
    if p.get("区分") == "中古":
        return None
    return p["価格"]


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
    if pattern_name in PATTERN_INFO:
        print(f"  {PATTERN_INFO[pattern_name]}")
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
    for line in power_check(pattern_selected(pattern_name, parts)):
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
        extra = ""
        if p.get("区分") == "中古":
            extra = " [中古]"
        elif p["中古価格"]:
            extra = f" / 中古相場 ¥{p['中古価格']:,}"
        print(f"  [{p['カテゴリ']}] {p['名前']}  ¥{p['価格']:,}{extra}  ({p['備考']})")


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
    # Wi-Fi非搭載ボードの案内
    if mb and mb["名前"] not in WIFI_BOARDS and not re.search(r"wifi", mb["名前"], re.I):
        warnings.append(
            "ℹ このマザーボードはWi-Fi非搭載です。無線LANで使う場合は、有線接続かWi-Fi子機 (USB/PCIe) が別途必要です"
        )
    # GPUの長さとケースの干渉
    if gpu and case:
        gl = GPU_LENGTH.get(gpu["名前"])
        lim = CASE_LIMITS.get(case["名前"])
        if gl and lim and gl > lim[0]:
            warnings.append(
                f"GPUの長さ ({gl}mm) がケースの搭載可能最大長 ({lim[0]}mm) を超えています! 入りません"
            )
    # CPUクーラーの高さとケースの干渉 (簡易水冷は対象外)
    if cooler and case:
        ch = COOLER_HEIGHT.get(cooler["名前"])
        lim = CASE_LIMITS.get(case["名前"])
        if ch and lim and ch > lim[1]:
            warnings.append(
                f"CPUクーラーの高さ ({ch}mm) がケースの対応最大高 ({lim[1]}mm) を超えています! サイドパネルが閉まりません"
            )
    # メモリの枚数とマザーボードのスロット数
    if mem and mb:
        m = re.search(r"x(\d+)", mem["名前"])
        slots = MB_SLOTS.get(mb["名前"])
        if m and slots and int(m.group(1)) > slots:
            warnings.append(
                f"メモリが{int(m.group(1))}枚組なのに、マザーボードのメモリスロットは{slots}つだけです! 全部は刺さりません"
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
    print("価格の種類は?  1: 新品価格  2: 中古相場")
    mode = "used" if input("番号: ") == "2" else "new"
    if mode == "used":
        print("中古相場モード: 相場データのあるパーツだけが選べるよ")
    print("カテゴリごとに番号で選んでね。0 は「選ばない」")
    for cat in CATEGORIES:
        options = [p for p in grouped[cat] if price_of(p, mode) is not None]
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
            print(f"  {i}: {p['名前']}  ¥{price_of(p, mode):,}")
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
            print(f"  [{cat}] {p['名前']}  ¥{price_of(p, mode):,}")
            total += price_of(p, mode)
        else:
            print(f"  [{cat}] (なし)")
    print(f"  合計{' (中古相場)' if mode == 'used' else ''}: ¥{total:,}")

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

    # 電源チェック
    for line in power_check(selected):
        print(f"  {line}")

    # 購入リンクまとめ
    links = buy_links(selected)
    if links:
        print("\n--- 購入リンクまとめ (検索リンク) ---")
        for line in links:
            print(f"  {line}")

    # 共有用テキスト
    print("\n--- 共有用テキスト (コピーして友達への相談に使えるよ) ---")
    print("【自作PC構成】")
    for cat in CATEGORIES:
        if cat in selected:
            p = selected[cat]
            print(f"[{cat}] {p['名前']} ¥{price_of(p, mode):,}")
    print(f"合計{' (中古相場)' if mode == 'used' else ''}: ¥{total:,}")
    for line in perf_estimate(selected):
        print(line)


def main():
    parts = load_parts()
    print("自作PC予算計算ツール")
    print(f"価格データ: 価格.com / Amazon等 最安価格 ({DATA_DATE} 時点) が基準。中古相場も {DATA_DATE} 調査")
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
