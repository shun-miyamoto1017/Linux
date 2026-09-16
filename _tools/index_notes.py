#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""既存ノートの索引を作る。

証跡を処理するとき「この論点はもう書いてあるか？」を調べるための索引。
ノート本体を1本ずつ開かなくても、この索引への検索だけで当たりが付く。

出力は 2 つ。

  _tools/notes_index.json   … 機械用。用語 → ノートの逆引きを含む完全な索引
  _tools/notes_outline.md   … 人間用。全ノートの見出しと扱うコマンドの一覧

使い方
    python3 _tools/index_notes.py          # 索引を作り直す
    grep -n "lvcreate" _tools/notes_index.json     # その語がどのノートにあるか
"""
import json
import pathlib
import re
import sys
from datetime import datetime, timezone, timedelta

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent

SKIP_DIRS = {"_tools", "_deploy", "_to_delete"}       # 検査しないフォルダ
SKIP_NAMES = {"00_このフォルダにあるもの.md", "README.md"}   # 自動生成の目次は対象外

FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)   # コードブロック（言語指定つき）
INLINE = re.compile(r"`([^`\n]+)`")               # インラインコード
HEADING = re.compile(r"^(#{1,4}) (.+)$", re.M)
# 太字で始まり、**その先頭がインラインコード**の行は、小見出しとして使われている。
#   拾う   **`blkid` … ブロックデバイスの情報を表示する**
#   拾わない **これらは `kill` してはいけません。**   ← 地の文の強調
BOLD_LEAD = re.compile(r"^\*\*`([^`\n]+)`", re.M)

# 索引に載せる用語の形。パス・コマンド・オプション・設定キーを拾い、
# 日本語の文や長すぎる文字列は落とす。
TERM_OK = re.compile(r"^[/~.\-]?[A-Za-z0-9][A-Za-z0-9_./+=\-\[\]*@:%]{0,39}$")
# 拾っても引く手がかりにならない語
TERM_NG = {
    "1", "2", "3", "0", "true", "false", "yes", "no", "on", "off",
    "a", "b", "c", "x", "y", "n", "l", "s", "k", "p", "r", "w",
}


def target_files():
    """索引の対象になるノートを返す。"""
    out = []
    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT)
        if SKIP_DIRS & set(rel.parts):
            continue
        if p.name in SKIP_NAMES:
            continue
        out.append(p)
    return out


def extract_commands(text):
    """```bash / ```sh ブロックの中の `$ ` 行から、実行しているコマンド名を拾う。"""
    cmds = []
    for lang, body in FENCE.findall(text):
        if lang not in ("bash", "sh"):
            continue
        for line in body.split("\n"):
            s = line.strip()
            if not s.startswith("$ "):
                continue
            s = s[2:].split("#")[0].strip()          # 行末のコメントを落とす
            for token in s.split():
                if token in ("sudo", "time", "env", "\\"):
                    continue                        # 前置きは読み飛ばして次の語を見る
                if token.startswith(("-", "$", "(", "<", ">", "|")):
                    break
                name = token.split("/")[-1]         # /usr/bin/ls → ls
                if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9._-]{0,30}", name):
                    cmds.append(name)
                break
    return sorted(set(cmds))


def extract_terms(text):
    """インラインコードから、引く手がかりになる用語を拾う。"""
    terms = set()
    for raw in INLINE.findall(text):
        t = raw.strip()
        if not TERM_OK.match(t):
            continue
        if t.lower() in TERM_NG or t.isdigit():
            continue
        terms.add(t)
    return sorted(terms)


def _terms_from(fragment):
    """見出しや太字の 1 行から、索引に載せられる語を拾う。

    インラインコード（`blkid`）を優先し、素の英数字トークン（blkid）も拾う。
    日本語はそのまま落ちる（TERM_OK に通らないため）。
    """
    out = set()
    for raw in INLINE.findall(fragment):
        t = raw.strip()
        if TERM_OK.match(t) and t.lower() not in TERM_NG and not t.isdigit():
            out.add(t)
    # インラインコードを外した残りから、素のトークンも拾う
    plain = INLINE.sub(" ", fragment)
    for token in re.split(r"[\s／/、。（）()「」:：,]+", plain):
        t = token.strip()
        if TERM_OK.match(t) and t.lower() not in TERM_NG and not t.isdigit():
            out.add(t)
    return out


def extract_headline_terms(text, stem):
    """**そのノートが解説の本体である**ことを示す語を拾う。

    「本文のどこかに出てくる」と「見出しになっている」を区別するための要。
    索引が『既出』と答えたのに実は一度も解説していない、という取りこぼしを防ぐ。

    拾う場所は 3 つ。

      1. 見出し（`#` 〜 `####`）
      2. 太字で始まる行（このリポジトリでは小見出しとして使っている）
      3. ファイル名（`systemctl_結果画面の見方.md` → `systemctl`）
    """
    terms = set()
    for _, title in HEADING.findall(text):
        terms |= _terms_from(title)
    for code in BOLD_LEAD.findall(text):
        t = code.strip()
        if TERM_OK.match(t) and t.lower() not in TERM_NG and not t.isdigit():
            terms.add(t)
    for token in re.split(r"[_\s-]+", stem):
        t = token.strip()
        if TERM_OK.match(t) and t.lower() not in TERM_NG and not t.isdigit():
            terms.add(t)
    return sorted(terms)


def extract_headings(text):
    """見出しを (レベル, 文字列) で返す。H1 はノートの題名。"""
    heads = []
    for hashes, title in HEADING.findall(text):
        heads.append((len(hashes), title.strip()))
    return heads


def lead_sentence(text):
    """冒頭の引用行（そのノートが何を扱うかの説明）を 1 行にまとめて返す。"""
    lines = []
    started = False
    for line in text.split("\n")[:40]:
        if line.startswith(">"):
            started = True
            lines.append(line.lstrip("> ").strip())
        elif started and not line.strip():
            break
    return " ".join(x for x in lines if x)[:300]


def build():
    notes = []
    by_command = {}
    by_term = {}
    by_headline = {}

    for path in target_files():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        heads = extract_headings(text)
        title = next((t for lv, t in heads if lv == 1), path.stem)
        sections = [t for lv, t in heads if lv in (2, 3)]
        commands = extract_commands(text)
        terms = extract_terms(text)
        headline = extract_headline_terms(text, path.stem)

        notes.append({
            "path": rel,
            "theme": rel.split("/")[0],
            "title": title,
            "lead": lead_sentence(text),
            "lines": len(text.split("\n")),
            "sections": sections,
            "commands": commands,
            "terms": terms,
            "headline": headline,
        })
        for c in commands:
            by_command.setdefault(c, []).append(rel)
        for t in terms:
            by_term.setdefault(t, []).append(rel)
        for h in headline:
            by_headline.setdefault(h, []).append(rel)

    jst = timezone(timedelta(hours=9))
    index = {
        "generated": datetime.now(jst).strftime("%Y-%m-%d %H:%M JST"),
        "note_count": len(notes),
        "notes": notes,
        "by_command": {k: sorted(set(v)) for k, v in sorted(by_command.items())},
        "by_term": {k: sorted(set(v)) for k, v in sorted(by_term.items())},
        # 見出し・太字の小見出し・ファイル名に出てくる語 → そのノートが「解説の本体」
        "by_headline": {k: sorted(set(v)) for k, v in sorted(by_headline.items())},
    }
    return index


def write_outline(index):
    """人間が読む用の一覧。テーマごとに、ノートの見出しと扱うコマンドを並べる。"""
    L = ["# ノートの索引",
         "",
         f"`_tools/index_notes.py` が生成。最終更新 {index['generated']}／全 {index['note_count']} ノート。",
         "",
         "> **証跡を処理する前に、ここで「もう書いてあるか」を確かめる。**",
         "> 語での検索は `grep -n \"<語>\" _tools/notes_index.json` が速い。",
         "",
         "---",
         ""]
    theme = None
    for n in index["notes"]:
        if n["theme"] != theme:
            theme = n["theme"]
            L += [f"## {theme}", ""]
        L.append(f"### {n['title']}")
        L.append("")
        L.append(f"`{n['path']}`（{n['lines']} 行）")
        L.append("")
        if n["lead"]:
            L += [f"> {n['lead']}", ""]
        if n["sections"]:
            L += ["**見出し**", "",
                  "　" + " ／ ".join(n["sections"]), ""]
        if n["commands"]:
            L += ["**扱うコマンド**", "",
                  "　" + " ".join(f"`{c}`" for c in n["commands"]), ""]
        L.append("---")
        L.append("")
    return "\n".join(L)


def find(words):
    """語を渡すと、それを扱っているノートを 3 段階で表示する（照合用）。

        python3 _tools/index_notes.py --find lvcreate quota xfs_growfs

    判定は 3 段階。**「◎ 本体」以外は、解説してあるとは限らない。**

        ◎ 本体      見出し・小見出し・ファイル名にその語がある → そこが解説の本体
        ○ 言及あり  本文や例文に出てくるだけ                   → 開いて確かめる
        ★ 未収録    どこにも無い                               → 新規ノートの候補
    """
    path = TOOLS / "notes_index.json"
    if not path.exists():
        print("索引がありません。先に python3 _tools/index_notes.py を実行してください。")
        return 1
    index = json.loads(path.read_text(encoding="utf-8"))
    by_c, by_t = index["by_command"], index["by_term"]
    by_h = index.get("by_headline", {})          # 古い索引でも落ちないようにする
    name = lambda p: p.split("/")[-1][:-3]

    for w in words:
        main = sorted(set(by_h.get(w, [])))
        if main:
            print(f"  {w:20s} ◎ 本体   → {' / '.join(name(h) for h in main)}")
            continue

        mention = sorted(set(by_c.get(w, []) + by_t.get(w, [])))
        if mention:
            print(f"  {w:20s} ○ 言及あり（解説とは限らない。開いて確かめる） → "
                  + " / ".join(name(h) for h in mention[:6]))
            continue

        # 部分一致でも当たりを見ておく（表記ゆれの取りこぼしを防ぐ）
        near = sorted({p for k, v in {**by_c, **by_t}.items()
                       if w.lower() in k.lower() for p in v})
        if near:
            print(f"  {w:20s} 完全一致なし。近い語を含むノート → "
                  + " / ".join(name(h) for h in near[:5]))
        else:
            print(f"  {w:20s} ★ 未収録（新規ノートの候補）")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--find":
        return find(sys.argv[2:])
    index = build()
    (TOOLS / "notes_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    (TOOLS / "notes_outline.md").write_text(write_outline(index), encoding="utf-8")

    print(f"ノート {index['note_count']} 本を索引しました（{index['generated']}）")
    print(f"  コマンド {len(index['by_command'])} 種 / 用語 {len(index['by_term'])} 種"
          f" / 見出しに出る語 {len(index['by_headline'])} 種")
    print("  _tools/notes_index.json")
    print("  _tools/notes_outline.md")

    # 例文の中でどこにでも出る道具は、散っていても問題にならないので除く
    UBIQUITOUS = {
        "ls", "cat", "echo", "cd", "mkdir", "rm", "cp", "mv", "touch", "vi", "vim",
        "grep", "find", "chmod", "chown", "head", "tail", "less", "wc", "sort",
        "awk", "sed", "cut", "tr", "sleep", "exit", "source", "export", "which",
        "aws", "docker", "kubectl", "dnf", "yum", "apt", "apt-get", "python3",
    }
    # 同じコマンドを 4 本以上のノートで扱っている場合は、説明が散っている可能性がある
    spread = {k: v for k, v in index["by_command"].items()
              if len(v) >= 4 and k not in UBIQUITOUS}
    if spread:
        print("\n複数のノートにまたがるコマンド（説明が散っていないか確認する）")
        for k, v in sorted(spread.items(), key=lambda x: -len(x[1]))[:15]:
            print(f"  {k:14s} {len(v)} 本  {', '.join(p.split('/')[-1] for p in v[:4])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
