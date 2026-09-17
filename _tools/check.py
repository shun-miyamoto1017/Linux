#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成物の検証：リンク切れ / 目次アンカー / コマンドのコメント率 / 行数 / 証跡の記録漏れ。"""
import ast, re, pathlib, urllib.parse, sys

# このスクリプトは _tools/ の中に置かれている前提。検査対象はリポジトリのルート。

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]+`")

def slug(h):
    """GitHub（github-slugger）と同じ順序で見出しをアンカーに変換する。

    github-slugger は「trim → 記号を除去 → 残った空白を - に置換」の順で処理する。
    先に trim するため、記号を消した結果できた先頭の空白は - として残る。
    """
    s = h.strip().lower()                                   # ① 先に前後の空白を落とす
    s = re.sub(r"[`*_\[\]()（）「」。、:：/\\.,!?'\"]", "", s)  # ② 記号を落とす
    return s.replace(" ", "-")                              # ③ 残った空白を - にする

root = pathlib.Path(__file__).resolve().parent.parent   # _tools の 1 つ上
bad, anchor_bad, miss_lines = [], [], []

SKIP = {"_tools", "_deploy", "_to_delete"}   # 検査しないフォルダ

LINE_LIMIT = 1000            # ノート 1 本の行数の目安（README のルール）
LINE_WARN = 900              # ここを超えたら「次の追記で超える」ので早めに知らせる
INDEX_LIKE = "00_このフォルダにあるもの.md"   # 2026-09-17 廃止。あったら警告する（作らないルール）
long_notes = []              # 目安を超えたノート
near_notes = []              # 目安に近づいたノート（LINE_WARN 超〜LINE_LIMIT 以下）

# --- 証跡の記録漏れを調べるための設定 -------------------------------------
# gen_index.py の SHOUSEKI に載っている番号の「飛び」を探す。
# ただし、処理しなくてよいと分かっている番号は除外する（毎回出ると警告が形骸化するため）。
SHOUSEKI_BLOCK = re.compile(r"^SHOUSEKI = \[\n(.*?)^\]\n", re.S | re.M)
SHOUSEKI_SKIP = {
    # 取得元: 飛んでいても問題ない番号
    "PC": (set(range(11, 17)) | set(range(18, 23))    # 別セッションが処理。元フォルダも削除済み
           | {94, 385}                                 # フォルダそのものが存在しない（385 は本人が削除済み）
           | set(range(124, 140))                      # 空フォルダ（スクリーンショットが無い）
           | {487, 488}),                               # 空フォルダ（スクリーンショットが無い）
}


def shouseki_gaps():
    """SHOUSEKI に記録されていない番号を、取得元ごとに返す。

    記録の最小〜最大の範囲だけを見る（まだ着手していない先の番号は対象外）。
    戻り値 … {取得元: [抜けている番号, ...]}
    """
    gen = pathlib.Path(__file__).resolve().parent / "gen_index.py"
    if not gen.exists():
        return {}
    m = SHOUSEKI_BLOCK.search(gen.read_text(encoding="utf-8"))
    if not m:
        return {}
    try:
        rows = ast.literal_eval("[\n" + m.group(1) + "\n]")
    except (SyntaxError, ValueError):
        return {}
    by_src = {}
    for r in rows:
        by_src.setdefault(r[0], set()).add(r[1])
    out = {}
    for src, nums in by_src.items():
        skip = SHOUSEKI_SKIP.get(src, set())
        missing = [n for n in range(min(nums), max(nums) + 1)
                   if n not in nums and n not in skip]
        if missing:
            out[src] = missing
    return out


def ranges(nums):
    """連続する番号を 95〜112 の形にまとめる（一覧を短くするため）。"""
    out, start, prev = [], None, None
    for n in nums + [None]:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(str(start) if start == prev else f"{start}〜{prev}")
            start = prev = n
    return " / ".join(out)


def target_files():
    """検査対象の md を返す（作業用フォルダは除く）。"""
    return [p for p in sorted(root.rglob("*.md"))
            if not (SKIP & set(p.relative_to(root).parts))]


for md in target_files():
    raw = md.read_text(encoding="utf-8")
    nofence = FENCE.sub("", raw)                      # コードブロックは検査対象外
    txt = INLINE.sub("", nofence)                     # リンク検査ではインラインコードも外す
    for m in re.finditer(r"\]\((?!https?://|mailto:|#)([^)]+)\)", txt):
        p = urllib.parse.unquote(m.group(1).split("#")[0])
        if p and not (md.parent / p).exists():
            bad.append((md.name, p))
    # 見出しはインラインコードを残したまま slug 化する（GitHub と同じ入力にするため）
    heads = {slug(h) for h in re.findall(r"^#{2,4} (.+)$", nofence, re.M)}
    miss = {a for a in re.findall(r"\]\(#([^)]+)\)", txt)} - heads
    if miss:
        anchor_bad.append((md.name, miss))

print("リンク切れ:", bad or "なし")
print("目次アンカー不整合:", anchor_bad or "なし")
print()
for f in target_files():
    if f.name == "README.md":
        continue
    lines = f.read_text(encoding="utf-8").split("\n")
    tot = nc = 0
    in_bash = False                                   # ```bash の中だけを検査対象にする
    for l in lines:
        s = l.strip()
        if s.startswith("```"):
            in_bash = s in ("```bash", "```sh") if not in_bash else False
            continue
        if in_bash and s.startswith("$ ") and not s.startswith("$ ..."):
            tot += 1
            if "#" not in l and not l.rstrip().endswith("\\"):
                nc += 1
                miss_lines.append((f.name, lines.index(l) + 1, s[:70]))
    n_lines = len(lines)
    mark = ""
    if f.name != INDEX_LIKE:
        if n_lines > LINE_LIMIT:
            long_notes.append((f.name, n_lines))
            mark = "  ← 分割を検討"
        elif n_lines > LINE_WARN:
            near_notes.append((f.name, n_lines))
            mark = "  ← そろそろ"
    print(f"{f.name:36s} {n_lines:5d}行  コマンド{tot:4d}  コメント無し{nc:3d}{mark}")

# --- 廃止したフォルダ目次が残っていないか ---------------------------------
# 2026-09-17 … 各フォルダの「00_このフォルダにあるもの.md」は作らないルールにした。
stale_index = sorted(
    str(f.relative_to(root))
    for f in root.rglob(INDEX_LIKE)
    if not (set(f.parts) & SKIP)
)
if stale_index:
    print("\n=== 廃止したフォルダ目次が残っています（作らないルール） ===")
    for f in stale_index:
        print(f"  {f}")
    print("  → 削除してください。生成は gen_index.py から外してあります。")

if miss_lines:
    print("\n=== コメントの無いコマンド行 ===")
    for name, ln, s in miss_lines:
        print(f"  {name}:{ln}  {s}")

if long_notes:
    print(f"\n=== {LINE_LIMIT} 行を超えたノート（ルールの目安。トピック単位で分割する） ===")
    for name, n in sorted(long_notes, key=lambda x: -x[1]):
        print(f"  {name}  {n}行  （目安 +{n - LINE_LIMIT} 行）")

if near_notes:
    print(f"\n=== {LINE_WARN} 行を超えたノート（次の追記で目安に届く。切れ目を決めておく） ===")
    for name, n in sorted(near_notes, key=lambda x: -x[1]):
        print(f"  {name}  {n}行  （目安まであと {LINE_LIMIT - n} 行）")

gaps = shouseki_gaps()
if gaps:
    print("\n=== 証跡の対応表に記録が無い番号（処理漏れか、書き戻し漏れの疑い） ===")
    for src, nums in sorted(gaps.items()):
        print(f"  {src}  {len(nums)} 件  {ranges(nums)}")
    print("  ※ 空フォルダなど、処理しなくてよい番号は check.py の SHOUSEKI_SKIP に足す")
else:
    print("\n証跡の記録漏れ: なし")

sys.exit(1 if bad or anchor_bad else 0)
