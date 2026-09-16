#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""処理した証跡を、gen_index.py の対応表へまとめて書き足す。

証跡を10件20件とまとめて処理すると、gen_index.py の SHOUSEKI を手で編集するのは
取りこぼしのもとになる。TSV を用意して、このスクリプトに流し込む。

TSV の形（タブ区切り・5列・見出し行なし）

    取得元	番号	問われた内容	扱い	取り込み先のパス
    PC	269	`mount` の主なオプション	既存ノートへ追記	06_ストレージとファイルシステム/マウントとアンマウント.md

  取得元 … PC / PC-L2 / Drive
  扱い   … 新規作成 / 既存ノートへ追記 / 既出
           「既出」と書けば **既出**（追加なし） に置き換わる

使い方

    python3 _tools/add_shouseki.py 追加分.tsv            # 追記して保存する
    python3 _tools/add_shouseki.py 追加分.tsv --dry-run  # 何が起きるか見るだけ

書き足したあとは gen_index.py を実行して README を作り直すこと。
"""
import ast
import json
import pathlib
import re
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
GEN = TOOLS / "gen_index.py"

SOURCES = ("PC", "PC-L2", "Drive")
SOURCE_ORDER = {s: i for i, s in enumerate(SOURCES)}
ATSUKAI = {
    "新規作成": "新規作成",
    "既存ノートへ追記": "既存ノートへ追記",
    "追記": "既存ノートへ追記",
    "既出": "**既出**（追加なし）",
    "**既出**（追加なし）": "**既出**（追加なし）",
}

BLOCK = re.compile(r"^SHOUSEKI = \[\n(.*?)^\]\n", re.S | re.M)


def load_existing(src):
    """gen_index.py の SHOUSEKI を読み出す。"""
    m = BLOCK.search(src)
    if not m:
        sys.exit("gen_index.py の中に SHOUSEKI = [ ... ] が見つかりません。")
    rows = ast.literal_eval("[\n" + m.group(1) + "\n]")
    return m, [tuple(r) for r in rows]


def read_tsv(path):
    """TSV を読んで、行のタプルにして返す。"""
    rows = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 5:
            sys.exit(f"{path}:{lineno} 列が {len(parts)} 個です（5 個必要）\n  {line}")
        src, no, naiyou, atsukai, dest = (p.strip() for p in parts)
        if src not in SOURCES:
            sys.exit(f"{path}:{lineno} 取得元 '{src}' は {'/'.join(SOURCES)} のいずれかにしてください")
        if not no.isdigit():
            sys.exit(f"{path}:{lineno} 番号 '{no}' が数字ではありません")
        if atsukai not in ATSUKAI:
            sys.exit(f"{path}:{lineno} 扱い '{atsukai}' は "
                     f"{' / '.join(k for k in ATSUKAI if not k.startswith('**'))} のいずれかにしてください")
        if not (ROOT / dest).exists():
            sys.exit(f"{path}:{lineno} 取り込み先が見つかりません → {dest}")
        rows.append((src, int(no), naiyou, ATSUKAI[atsukai], dest))
    return rows


def fmt(row):
    """既存の書き方に合わせて 2 行で出力する。"""
    src, no, naiyou, atsukai, dest = row
    j = lambda s: json.dumps(s, ensure_ascii=False)
    return f' ({j(src)}, {no}, {j(naiyou)}, {j(atsukai)},\n  {j(dest)}),'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)

    tsv = pathlib.Path(args[0])
    if not tsv.exists():
        sys.exit(f"{tsv} がありません")

    src_text = GEN.read_text(encoding="utf-8")
    m, existing = load_existing(src_text)
    have = {(r[0], r[1]) for r in existing}

    new = read_tsv(tsv)

    # 同じ TSV の中での番号の重複を先に弾く
    seen = set()
    for r in new:
        key = (r[0], r[1])
        if key in seen:
            sys.exit(f"TSV の中で {r[0]} {r[1]} が重複しています")
        seen.add(key)

    add = [r for r in new if (r[0], r[1]) not in have]
    skip = [r for r in new if (r[0], r[1]) in have]

    for r in skip:
        print(f"  すでに登録済みなので飛ばします … {r[0]} {r[1]}")

    if not add:
        print("書き足すものはありませんでした。")
        return 0

    merged = sorted(existing + add, key=lambda r: (SOURCE_ORDER[r[0]], r[1]))
    body = "\n".join(fmt(r) for r in merged)
    out = src_text[:m.start()] + "SHOUSEKI = [\n" + body + "\n]\n" + src_text[m.end():]

    # 書き換えた結果が Python として読めるか、件数が合っているかを確かめる
    try:
        ast.parse(out)
    except SyntaxError as e:
        sys.exit(f"書き換えた gen_index.py が壊れています（{e}）。中止しました。")
    _, check = load_existing(out)
    if len(check) != len(merged):
        sys.exit("件数が合いません。中止しました。")

    print(f"  {len(add)} 件を書き足します（{len(existing)} → {len(merged)} 件）")
    for r in add:
        print(f"    {r[0]} {r[1]:4d}  {r[3]:20s} {r[4]}")

    if dry:
        print("\n--dry-run なので保存していません。")
        return 0

    GEN.write_text(out, encoding="utf-8")
    print(f"\n{GEN} を更新しました。")
    print("続けて python3 _tools/gen_index.py を実行して、目次と README を作り直してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
