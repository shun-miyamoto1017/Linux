# patchによるソースの更新

| | |
|:--|:--|
| **学習の順番** | Phase3 専門 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / 能力値(主題206) — makeによるソースコードからのビルドとインストール |
| **業務での使いどころ** | **ベンダからパッチファイルだけ渡される場面**は今もある。Git を使わない配布物、カーネルへの独自パッチ、OSS への修正提案。`git apply` が裏でやっていることもこれなので、仕組みを知っておくと差分の読み方が変わる |

> **ビルドの流れ全体**は [ソースからのビルドとインストール](./ソースからのビルドとインストール.md)、
> **カーネル固有のパッチ運用**は [カーネルのビルドとインストール](../05_起動プロセスとカーネル/カーネルのビルドとインストール.md) にまとめています。

---

## 目次

- [パッチとは何か](#パッチとは何か)
- [diff でパッチを作る](#diff-でパッチを作る)
- [patch で当てる](#patch-で当てる)
  - [渡し方は3通り](#渡し方は3通り)
- [階層を剥がす p オプション](#階層を剥がす-p-オプション)
  - [数え方](#数え方)
  - [実測で確かめる](#実測で確かめる)
  - [p を指定しないとどうなるか](#p-を指定しないとどうなるか)
- [作業ディレクトリを指定する d オプション](#作業ディレクトリを指定する-d-オプション)
- [取り消す R オプション](#取り消す-r-オプション)
- [失敗すると rej と orig ができる](#失敗すると-rej-と-orig-ができる)
- [圧縮されたパッチを当てる](#圧縮されたパッチを当てる)
- [適用順序という落とし穴](#適用順序という落とし穴)
  - [fuzz が事故を隠す](#fuzz-が事故を隠す)
- [patch-kernel スクリプト](#patch-kernel-スクリプト)
- [オプション一覧](#オプション一覧)
- [実務での注意](#実務での注意)
- [参考リンク](#参考リンク)

---

## パッチとは何か

**パッチ（patch）は、2つのファイルの差分だけを取り出したテキスト**です。

```text
   修正前のソース  ──┐
                     ├─ diff ─▶  パッチファイル（差分だけ）
   修正後のソース  ──┘

   修正前のソース  ──┬─ patch ─▶  修正後のソース
   パッチファイル  ──┘
```

**なぜ差分で配るのか**

| 理由 | 実測 |
|:--|:--|
| **小さい** | 元ファイル 16 バイトに対し、パッチは 193 バイト（小さい例なので逆転しているが、大きなソースでは差が歴然） |
| **何が変わったか読める** | `+` と `-` で変更点だけが見える |
| **取り消せる** | `-R` で元に戻せる |

カーネルのように数百 MB のソースに対して数 KB の修正を配るなら、差分で配るのが圧倒的に合理的です。

---

## diff でパッチを作る

**パッチを作るのは `diff`、当てるのは `patch`** です。役割が分かれています。

```bash
$ diff -u old/src/a.txt new/src/a.txt       # unified 形式で差分を出す
```

```text
--- old/src/a.txt	2026-09-23 14:49:37.657631305 +0000
+++ new/src/a.txt	2026-09-23 14:49:37.657631305 +0000
@@ -1,3 +1,4 @@
 hello
-world
+WORLD
 foo
+bar
```

**読み方**

```text
   ---  修正前のファイル
   +++  修正後のファイル
   @@ -1,3 +1,4 @@   … 修正前は1行目から3行、修正後は1行目から4行
   （空白）hello      … 変更なし（文脈行 = context）
   -world            … 削除される行
   +WORLD            … 追加される行
```

**ディレクトリ全体の差分**を取るときは `-ruN` を使います。

```bash
$ diff -ruN old new > a.patch               # ディレクトリを再帰的に比較する
```

| オプション | 意味 |
|:--|:--|
| `-u` | unified 形式（前後3行の文脈付き）。**patch で当てる標準形式** |
| `-r` | ディレクトリを再帰的に比較する |
| `-N` | 片方にしか無いファイルを「新規追加」として扱う |
| `-c` | context 形式（古い形式） |

**`diff` の終了ステータス**にも意味があります。

```text
   0 … 差分なし
   1 … 差分あり
   2 … エラー
```

シェルスクリプトで `if diff a b; then` と書くと「同じなら真」になります。

---

## patch で当てる

```text
patch [オプション] [対象ファイル] [< パッチファイル]
```

```bash
$ cd old                                    # ソースのルートへ移動する
$ patch -p1 < ../a.patch                    # パッチを当てる
$ cat src/a.txt                             # 結果を確認する
```

```text
patching file src/a.txt
hello
WORLD
foo
bar
```

**`patching file ...` と出れば成功**です。終了ステータスは 0 になります。

### 渡し方は3通り

**どれも同じ結果になります。**

```bash
$ patch -p1 < a.patch                       # 入力リダイレクトで渡す（最も一般的）
$ cat a.patch | patch -p1                   # パイプで渡す
$ patch -p1 src/a.txt a.patch               # 引数で対象とパッチを両方指定する
```

| 渡し方 | 対象ファイルの決まり方 |
|:--|:--|
| リダイレクト `<` | **パッチの中の `---` / `+++` から自動判別** |
| パイプ `\|` | 同上 |
| 引数で指定 | **明示した対象ファイルに当てる** |

**`>`（出力リダイレクト）はパッチの適用にはなりません。**
`patch > a.patch` と書くと、patch の**標準出力をファイルに書く**だけです。よくある引っかけです。

---

## 階層を剥がす p オプション

**`-pN` は、パッチの中に書かれたパスから先頭 N 階層を取り除きます。**

### 数え方

```text
   パッチに書かれたパス:  old/src/a.txt

   -p0  →  old/src/a.txt    （何も取り除かない = そのまま）
   -p1  →  src/a.txt        （先頭1階層 old/ を取り除く）
   -p2  →  a.txt            （先頭2階層 old/src/ を取り除く）
```

**「スラッシュをいくつ飛ばすか」**と覚えると間違えません。

```text
   old / src / a.txt
      ↑     ↑
    -p1   -p2
```

### 実測で確かめる

同じパッチを、**いる場所とオプションを変えて**当ててみます。

```bash
$ cd old                                    # old ディレクトリの中に入る
$ patch -p1 < ../a.patch                    # old/ を剥がして src/a.txt に当てる
```

```text
patching file src/a.txt
```

**成功しました。** 今度は `old` の親（`patchlab`）から `-p0` で当てます。

```bash
$ cd ..                                     # 親ディレクトリへ戻る
$ patch -p0 < a.patch                       # パスをそのまま使って当てる
```

```text
patching file old/src/a.txt
```

**こちらも成功**です。**「どこにいるか」と「何階層剥がすか」はセットで決まります。**

```text
   カレントが old/        → src/a.txt を見つけたい  → -p1
   カレントが patchlab/   → old/src/a.txt を見つけたい → -p0
```

**カーネルのパッチは慣習的に `-p1`** です。
パッチが `linux-4.7/Makefile` のように書かれており、
展開したソースディレクトリの中から当てるため、先頭1階層を剥がす必要があるからです。

### p を指定しないとどうなるか

**`-p` を省略すると、patch はパスの先頭ディレクトリをすべて落とし、ファイル名だけで探します。**
実測で確かめます。パッチに書かれたパスは `old/src/a.txt` です。

`old/src/a.txt` が実在するディレクトリで `-p` を付けずに実行すると、**見つかりません。**

```bash
$ patch < a.patch                           # -p を付けずに実行する
```

```text
can't find file to patch at input line 3
Perhaps you should have used the -p or --strip option?
The text leading up to this was:
--------------------------
|--- old/src/a.txt
|+++ new/src/a.txt
--------------------------
File to patch: 
Skip this patch? [y] 
Skipping patch.
1 out of 1 hunk ignored
```

ところが、**`a.txt` がカレントディレクトリにあると当たってしまいます。**

```bash
$ cd t                                      # a.txt だけがあるディレクトリへ移動する
$ patch < ../a.patch                        # -p を付けずに実行する
$ cat a.txt                                 # 結果を確認する
```

```text
patching file a.txt
hello
WORLD
foo
bar
```

**まったく無関係の `a.txt` に当たる可能性がある**ということです。
**`-p` は必ず明示してください。**

なお、`-p` を明示していても**いる場所を間違えれば**当たりません。

```bash
$ cd old                                    # old の中にいる状態で
$ patch -p0 < ../a.patch                    # -p0（剥がさない）を指定してしまう
```

```text
can't find file to patch at input line 4
Perhaps you used the wrong -p or --strip option?
The text leading up to this was:
--------------------------
|diff -ruN old/src/a.txt new/src/a.txt
|--- old/src/a.txt	2026-09-23 14:49:37.657631305 +0000
|+++ new/src/a.txt	2026-09-23 14:49:37.657631305 +0000
--------------------------
File to patch: 
Skip this patch? [y] 
Skipping patch.
1 out of 1 hunk ignored
```

**`Perhaps you used the wrong -p or --strip option?` と親切に教えてくれます。**
`old/` の中から `old/src/a.txt` を探そうとして見つからなかった、ということです。

---

## 作業ディレクトリを指定する d オプション

**`-d` はパッチを当てる作業ディレクトリを指定**します。`cd` しなくて済みます。

```bash
$ patch -d old -p1 < a.patch                # old に移動してから当てるのと同じ
```

```text
patching file src/a.txt
```

**カレントディレクトリは変わりません。**
スクリプトから複数のディレクトリにパッチを当てる場合に便利です。

```text
   cd old && patch -p1 < ../a.patch   ≡   patch -d old -p1 < a.patch
```

---

## 取り消す R オプション

**`-R`（`--reverse`）はパッチを逆向きに適用**し、当てる前の状態に戻します。

```bash
$ patch -R -p1 < ../a.patch                 # 当てたパッチを取り消す
$ cat src/a.txt                             # 元に戻ったか確認する
```

```text
patching file src/a.txt
hello
world
foo
```

**`WORLD` が `world` に戻り、`bar` が消えました。**

```text
   通常:  -world  +WORLD   →  world を WORLD に置き換える
   -R  :  +WORLD  -world   →  WORLD を world に置き換える（逆に読む）
```

**バックアップを取り忘れていても、当てたパッチファイルさえあれば元に戻せます。**

**重要な前提が2つあります。**

```text
   1. 取り消せるのは「実際に当てたパッチ」だけ
        → 当てていないパッチに -R を使っても失敗する
   2. パッチファイルを消してしまうと取り消せない
        → 適用済みの変更はソース側に残ったまま
```

**パッチファイルは当てた後も必ず保管してください。**

---

## 失敗すると rej と orig ができる

**当たらないパッチを適用すると、2つのファイルが残ります。** 実測します。

**hunk（ハンク）** とは `@@ ... @@` で区切られた差分の 1 ブロックのことです。以下の出力はこの単位で成否が出ます。

```bash
$ printf 'totally\ndifferent\ncontent\n' > old/src/a.txt   # 内容を入れ替えておく
$ patch -d old -p1 < a.patch                               # 当たらないパッチを適用する
```

```text
patching file src/a.txt
Hunk #1 FAILED at 1.
1 out of 1 hunk FAILED -- saving rejects to file src/a.txt.rej
```

```bash
$ ls -l old/src/                             # 残ったファイルを確認する
```

```text
-rw-r--r-- 1 root root  26 Sep 23 14:49 a.txt
-rw-r--r-- 1 root root  26 Sep 23 14:49 a.txt.orig
-rw-r--r-- 1 root root 147 Sep 23 14:49 a.txt.rej
```

| ファイル | 中身 |
|:--|:--|
| **`a.txt.rej`** | **当てられなかった差分**（reject） |
| **`a.txt.orig`** | **適用前の元の内容**（original） |

```bash
$ cat old/src/a.txt.rej                     # 当てられなかった差分を見る
```

```text
--- src/a.txt	2026-09-23 14:49:37.657631305 +0000
+++ src/a.txt	2026-09-23 14:49:37.657631305 +0000
@@ -1,3 +1,4 @@
 hello
-world
+WORLD
 foo
+bar
```

```bash
$ cat old/src/a.txt.orig                    # 適用前の内容を見る
```

```text
totally
different
content
```

**`.rej` が出たら、手で当てるしかありません。**
`.rej` の内容を読んで、対象ファイルの該当箇所を直接編集します。
作業が終わったら `.rej` と `.orig` は削除してください。**残っているとビルドに紛れ込みます。**

`1 out of 1 hunk FAILED` は「1個あるハンクのうち1個が失敗した」という意味です。

---

## 圧縮されたパッチを当てる

**カーネルパッチは `.gz` `.bz2` `.xz` で配布されます。**
`-c` を付けて標準出力に解凍し、パイプで `patch` に渡すのが定石です。

```bash
$ xz -dc a.patch.xz | patch -d old -p1      # 解凍しながら当てる
$ cat old/src/a.txt                          # 結果を確認する
```

```text
patching file src/a.txt
hello
WORLD
foo
bar
```

**同じ「解凍して標準出力へ」でも、コマンドごとに書き方が違う**ので注意してください。

| 形式 | 解凍して標準出力へ | 同等の短縮形 |
|:--|:--|:--|
| gzip | `gzip -dc` / `gunzip -c` | `zcat` |
| bzip2 | `bzip2 -dc` / `bunzip2 -c` | `bzcat` |
| xz | `xz -dc` / `unxz -c` | `xzcat` |

```bash
$ gunzip -c a.patch.gz | head -1            # gunzip は既定で解凍する
$ gzip -dc a.patch.gz | head -1             # gzip は -d を付けないと解凍しない
$ zcat a.patch.gz | head -1                 # zcat は gunzip -c と同じ
```

```text
diff -ruN old/src/a.txt new/src/a.txt
diff -ruN old/src/a.txt new/src/a.txt
diff -ruN old/src/a.txt new/src/a.txt
```

**3つとも同じ結果です。**

**`-c` だけでは解凍になりません。** 実測すると、二重に圧縮されます。

```bash
$ gzip -c a.patch.gz | file -               # -c だけを付けて実行する
```

```text
/dev/stdin: gzip compressed data, was "a.patch.gz", last modified: Wed Sep 23 14:49:54 2026, from Unix
```

**さらに gzip 圧縮されたデータが出てきました。**

```text
   gzip   … 既定は「圧縮」  → 解凍するには -d が必要
   gunzip … 既定が「解凍」  → -d は不要
   -c     … 「結果を標準出力へ」という意味だけ。圧縮/解凍の向きは変えない
```

---

## 適用順序という落とし穴

**パッチは「適用前の状態」を前提に差分を持っています。**
したがって**複数のパッチは、作られた順番どおりに当てなければなりません。**

```text
   base ──p1──▶ v1 ──p2──▶ v2

   正しい順序:  base に p1 → p2       ✓
   誤った順序:  base に p2 → p1       ✗（p2 は v1 を前提にしている）
```

正しい順序で当てた結果です。

```bash
$ cp base.txt t.txt                         # 元の状態から始める
$ patch t.txt < p1.patch && patch t.txt < p2.patch   # 順番どおりに当てる
$ cat t.txt                                 # 結果を確認する
```

```text
patching file t.txt
patching file t.txt
v2
alpha-NEW
bravo
```

### fuzz が事故を隠す

**ここが最も重要な注意点です。**
順序を間違えても、**patch は「成功した」と言ってしまうことがあります。**

```bash
$ cp base.txt t.txt                         # 元の状態に戻す
$ patch t.txt < p2.patch                    # わざと p2 を先に当てる
$ cat t.txt                                 # 結果を確認する
```

```text
patching file t.txt
Hunk #1 succeeded at 1 with fuzz 1.
v1
alpha-NEW
bravo
```

**終了ステータスは 0（成功）です。** しかし結果は `v1` のまま `alpha-NEW` だけが適用された、
**どちらの版でもない中途半端な状態**になっています。

**`with fuzz 1` が警告のサイン**です。
patch は文脈行（前後の変更されていない行）が多少合わなくても、
**許容範囲内なら当ててしまいます。** これを **fuzz（ファジー）** と呼びます。

**既定の許容量を実測で求めました。**
文脈行を1行ずつ壊しながら、どこで失敗するかを調べます。

```bash
$ patch t.txt < p.patch                     # 文脈を壊しながら繰り返し実行する
```

```text
文脈を 0 行壊す → exit=0 : patching file t.txt 
文脈を 1 行壊す → exit=0 : patching file t.txt Hunk #1 succeeded at 1 with fuzz 1. 
文脈を 2 行壊す → exit=0 : patching file t.txt Hunk #1 succeeded at 1 with fuzz 2. 
文脈を 3 行壊す → exit=1 : patching file t.txt Hunk #1 FAILED at 1. 1 out of 1 hunk FAILED
```

**既定では fuzz 2 まで許容されます。**（GNU patch 2.7.6 で実測）

**厳密に当てたいときは `-F 0` を付けます。**

```bash
$ patch -F 0 t.txt < p2.patch               # fuzz を許さずに当てる
$ cat t.txt                                 # 変わっていないことを確認する
```

```text
patching file t.txt
Hunk #1 FAILED at 1.
1 out of 1 hunk FAILED -- saving rejects to file t.txt.rej
v1
alpha
bravo
```

**今度はきちんと失敗し、ファイルは変更されませんでした。**

```text
   検証やリリース作業では  -F 0 を付ける
        → 「成功したのに間違っている」という最悪の事態を防ぐ
   出力に fuzz の文字が出たら、必ず結果を目視する
```

---

## patch-kernel スクリプト

**`patch` コマンド自体には、複数のパッチをまとめて当てる機能はありません。**
カーネルソースには、それを行う `patch-kernel` というスクリプトが同梱されています。

```text
   /usr/src/linux/scripts/patch-kernel
```

**指定されたディレクトリにあるパッチを、バージョン順に自動で適用**します。
順番の判断を人がやらなくて済むのが利点です。

```bash
$ ./scripts/patch-kernel . /path/to/patches   # パッチを順に自動適用する
```

> **実測できていないこと** … この環境にはカーネルソースツリーが無いため、
> `patch-kernel` の実行は確認していません。

**パッチファイルの置き場所に決まりはありません。**
ソースを `/usr/src/linux` に展開するのは慣例ですが、パッチ自体はどこに置いても構いません。

> カーネルへのパッチ運用の詳細は
> [カーネルのビルドとインストール](../05_起動プロセスとカーネル/カーネルのビルドとインストール.md) を参照してください。

---

## オプション一覧

| オプション | 意味 |
|:--|:--|
| `-pN` / `--strip=N` | パスから先頭 N 階層を取り除く |
| `-d DIR` / `--directory=DIR` | 作業ディレクトリを指定する |
| `-R` / `--reverse` | **逆向きに適用する（取り消す）** |
| `-F N` / `--fuzz=N` | fuzz の許容量（既定 2）。**`-F 0` で厳密に** |
| `-b` / `--backup` | 元ファイルを `.orig` として保存する |
| `-i FILE` / `--input=FILE` | パッチファイルを指定する（`<` の代わり） |
| `-o FILE` / `--output=FILE` | 結果を別ファイルに出す（元を変更しない） |
| `-l` / `--ignore-whitespace` | 空白の違いを無視する |
| `-N` / `--forward` | すでに当たっている（または逆向きの）パッチを**対話プロンプトなしで**読み飛ばす。ただしメッセージは出て `.rej` も作られ、**終了ステータスは 1** |
| `--dry-run` | **実際には変更せず、結果だけ表示する** |
| `-s` / `--silent` | 成功時は何も表示しない |

**`--dry-run` は必ず使ってください。**

```bash
$ patch --dry-run -p1 < a.patch             # 当たるかどうかだけ確認する
```

---

## 実務での注意

**1. 当てる前に必ずバックアップを取る**

`-R` で戻せるとはいえ、`.rej` が出た後に手作業で直すと戻せなくなります。

```bash
$ cp -a src src.bak                         # ディレクトリごと退避する
```

**2. 当てる順番と当てたパッチを記録する**

```bash
$ for p in patches/*.patch; do              # 順番に当てて記録する
>   echo "applying $p" | tee -a applied.log # 適用したパッチをログに残す
>   patch -p1 -F 0 < "$p" || break          # 失敗したら止める
> done
```

**`|| break` が重要**です。1つ失敗した状態で次を当てると、傷口が広がります。

**ただし `-N` を併用するときは注意**してください。
`-N` は「すでに当たっているパッチ」を飛ばしますが、**終了ステータスは 1 のまま**です。

```text
$ patch -N -p1 < a.patch
patching file a.txt
Reversed (or previously applied) patch detected!  Skipping patch.
1 out of 1 hunk ignored -- saving rejects to file a.txt.rej
（終了ステータス 1）
```

`|| break` を付けたループでは、ここで止まります。
「当たっていたから飛ばした」のか「本当に失敗した」のかは、**メッセージを読んで判断する**しかありません。

**3. 当てた後は必ず再ビルドする**

**パッチはソースを書き換えるだけ**です。バイナリは古いままです。

```bash
$ make clean                                # 古い中間ファイルを消す
$ make                                      # 再ビルドする
```

**4. 非公式パッチは先に外す**

公式パッチを当てる前に、独自に当てた非公式パッチは `-R` で外しておきます。
当たったまま公式パッチを重ねると、衝突して `.rej` の山になります。

**5. `.rej` と `.orig` を消し忘れない**

```bash
$ find . -name '*.rej' -o -name '*.orig'    # 残骸を探す
```

ビルドディレクトリに残っていると、パッケージングのときに紛れ込みます。

---

## 参考リンク

- [man 1 patch](https://man7.org/linux/man-pages/man1/patch.1.html)
- [man 1 diff](https://man7.org/linux/man-pages/man1/diff.1.html)
- [GNU Diffutils マニュアル](https://www.gnu.org/software/diffutils/manual/)

---

[← 全体の目次にもどる](../README.md)
