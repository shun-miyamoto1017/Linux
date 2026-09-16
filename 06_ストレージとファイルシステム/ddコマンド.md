# dd コマンド

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / GNUとUnixコマンド(主題103) — 基本的なファイル管理 |
| **業務での使いどころ** | ディスクの丸ごとバックアップ、ISO の書き込み、検証用ダミーファイルの作成、ディスクの先頭領域の調査 |

> Ping-t の分類上は「基本的なファイル管理（項目 2）」の問題ですが、
> `dd` が扱うのはファイルではなく**ディスクやデバイスのブロック**なので、
> このリポジトリではストレージのフォルダに置いています。
> ファイル単位の `cp` / `mv` / `rm` は
> [01_シェルとコマンドライン / ファイルとディレクトリの操作](../01_シェルとコマンドライン/ファイルとディレクトリの操作.md) にあります。

---

## 目次

- [まずこれだけ](#まずこれだけ)
- [dd とは何をするコマンドか](#dd-とは何をするコマンドか)
- [cp との違い](#cp-との違い)
- [書式とオペランド](#書式とオペランド)
  - [if と of](#if-と-of)
  - [bs ブロックサイズ](#bs-ブロックサイズ)
  - [count コピーする回数](#count-コピーする回数)
  - [skip と seek](#skip-と-seek)
  - [status 進捗の表示](#status-進捗の表示)
  - [conv と iflag oflag](#conv-と-iflag-oflag)
- [サイズの単位](#サイズの単位)
- [実行結果の読み方](#実行結果の読み方)
- [特殊なデバイスファイル](#特殊なデバイスファイル)
- [業務で使う場面](#業務で使う場面)
- [dd は危険なコマンド](#dd-は危険なコマンド)
- [手を動かして確かめる](#手を動かして確かめる)
- [つまずきポイント](#つまずきポイント)
- [クラウド実務メモ](#クラウド実務メモ)
- [参考リンク](#参考リンク)

---

## まずこれだけ

| やりたいこと | コマンド |
|:--|:--|
| ファイルをコピーする | `dd if=input.txt of=output.txt` |
| **5MB のダミーファイルを作る** | **`dd if=/dev/zero of=testfile bs=1M count=5`** |
| ディスクを丸ごとイメージ化する | `dd if=/dev/sda of=/backup/disk.img bs=4M status=progress` |
| イメージをディスクへ書き戻す | `dd if=/backup/disk.img of=/dev/sda bs=4M status=progress` |
| ISO を USB へ書き込む | `dd if=ubuntu.iso of=/dev/sdb bs=4M status=progress` |
| ディスクの先頭 1MB だけ取り出す | `dd if=/dev/sda of=first1M.bin bs=1M count=1` |

**覚え方**

| オペランド | 何の略か | 意味 |
|:--|:--|:--|
| `if=` | **I**nput **F**ile | 読み込み元 |
| `of=` | **O**utput **F**ile | 書き込み先 |
| `bs=` | **B**lock **S**ize | 一度に読み書きするバイト数 |
| `count=` | count | **入力ブロックを何回コピーするか** |

**作られるファイルのサイズ ＝ `bs` × `count`** です。
`bs=1M count=5` なら 1MB のかたまりを 5 回コピーするので 5MB になります。

---

## dd とは何をするコマンドか

`dd` は、

> ある場所からデータを読み取り、別の場所へそのまま書き込むコマンド

です。「そのまま」というのがポイントで、**中身を解釈せずバイト列として運びます**。

```bash
$ dd if=input.txt of=output.txt     # input.txt の中身をそのまま output.txt へ書く
```

データの流れはこうなります。

```text
input.txt
    │  読む（if）
    ▼
   dd
    │  書く（of）
    ▼
output.txt
```

**補足 … `if` / `of` は「オプション」ではなく「オペランド」です**

`dd` は Linux コマンドとしては珍しく、`-i` `-o` のような
**ハイフン付きのオプションを使いません**。`if=値` という形の
**オペランド（operand）** で指定します。これは `dd` が
IBM のメインフレームにあった JCL の `DD`（Data Definition）文を
真似した歴史的な経緯によるものです。

そのため、以下のような書き方は**すべて誤り**です。

```bash
$ dd -i input.txt -o output.txt     # -i / -o というオプションは無い
$ dd if = input.txt                 # = の前後にスペースを入れてはいけない
```

---

## cp との違い

普通のファイルコピーなら `cp` を使います。わざわざ `dd` を使う理由は、
**扱える対象と粒度が違う**からです。

| | `cp` | `dd` |
|:--|:--|:--|
| 何をコピーするか | **ファイル**（ファイルシステムを通す） | **バイト列・ブロック**（ファイルシステムを通さない） |
| 対象にできるもの | ファイル、ディレクトリ | ファイル、**ディスク、パーティション、ISO、デバイス** |
| 一部だけコピー | できない | **できる**（`skip` / `seek` / `count`） |
| ブロックサイズの指定 | できない | **できる**（`bs`） |
| 空きブロックも含めてコピー | しない | **する**（丸ごと同じものができる） |

イメージにするとこうです。

```text
cp
└─ ファイルをコピーする

dd
└─ データの塊をコピーする
   ├─ ファイル
   ├─ ディスク       ← cp では扱えない
   ├─ パーティション ← cp では扱えない
   ├─ ISO イメージ   ← cp では扱えない
   └─ デバイス       ← cp では扱えない
```

**なぜディスクは `cp` でコピーできないのか**

`cp` は「ファイルシステムの上にあるファイル」を扱うコマンドです。
ディスク全体には**パーティションテーブルやブートローダなど、
ファイルとして見えない領域**があり、`cp` ではそこに手が届きません。
`dd` はファイルシステムを無視して**先頭のバイトから順に読む**ので、
そうした領域ごと丸ごと複製できます。

---

## 書式とオペランド

```text
dd [オペランド]...
```

| オペランド | 意味 |
|:--|:--|
| `if=入力ファイル` | 入力側ファイル（デバイス）を指定。省略すると標準入力 |
| `of=出力ファイル` | 出力側ファイル（デバイス）を指定。省略すると標準出力 |
| `bs=バイト数` | 入出力のブロックサイズ（一度に読み書きするバイト数）を指定。**既定は 512 バイト** |
| `count=回数` | **入力ファイルから出力ファイルへブロックをコピーする回数**を指定 |
| `skip=回数` | **入力**側の先頭から、指定した数のブロックを読み飛ばす |
| `seek=回数` | **出力**側の先頭から、指定した数のブロック分を飛ばした位置に書く |
| `status=レベル` | 実行中・実行後に表示する情報の量（`none` / `noxfer` / `progress`） |
| `conv=変換` | 変換方法をカンマ区切りで指定（`notrunc` / `sync` / `noerror` など） |
| `ibs=` / `obs=` | 入力側だけ／出力側だけのブロックサイズ。`bs=` は両方をまとめて指定する |

### if と of

**意味** … 読み込み元（`if`）と書き込み先（`of`）を指定する

**例文**

```bash
$ echo "Hello dd!" > input.txt       # 練習用の入力ファイルを作る
$ dd if=input.txt of=output.txt      # input.txt を output.txt へコピーする
0+1 records in
0+1 records out
10 bytes copied, 2.5175e-05 s, 397 kB/s

$ cat output.txt                     # 中身が同じことを確認する
Hello dd!
```

**補足** … `if` を省略すると標準入力から、`of` を省略すると標準出力へ流れます。
そのためパイプの途中に置くこともできます。

```bash
$ cat input.txt | dd of=output.txt   # 標準入力から受け取って書き出す
$ dd if=input.txt | gzip > out.gz    # 読み出した結果をそのまま圧縮へ渡す
```

### bs ブロックサイズ

**意味** … 一度に読み書きするバイト数。**既定は 512 バイト**

**例文**

```bash
$ dd if=/dev/zero of=testfile bs=1M count=5    # 1MB を 5 回 = 5MB のファイルを作る
5+0 records in
5+0 records out
5242880 bytes (5.2 MB, 5.0 MiB) copied, 0.00302971 s, 1.7 GB/s

$ ls -l testfile                     # サイズを確認する（5242880 = 1024*1024*5）
-rw-r--r-- 1 root root 5242880 Aug 31 15:15 testfile
```

**補足 … `bs` は速度に効きます**

既定の 512 バイトのままディスクを丸ごとコピーすると、
512 バイトごとに読み書きが発生して**非常に遅くなります**。
実務では `bs=1M` や `bs=4M` を付けるのが定石です。

```bash
$ dd if=/dev/sda of=disk.img                   # bs 省略 = 512 バイトずつ。とても遅い
$ dd if=/dev/sda of=disk.img bs=4M             # 4MB ずつ読み書きする。実用的な速さ
```

大きくすれば必ず速いわけではなく、`1M` 〜 `4M` あたりが実用的な目安です。

### count コピーする回数

**意味** … **入力ブロックを何回コピーするか**。指定した回数だけコピーして終了する

**例文**

```bash
$ dd if=/dev/zero of=testfile bs=1M count=5    # 1MB × 5回 = 5MB
$ dd if=/dev/sda of=first1M.bin bs=1M count=1  # ディスクの先頭 1MB だけ取り出す
$ dd if=/dev/sda of=mbr.bin bs=512 count=1     # 先頭 512 バイト（MBR）だけ取り出す
```

**補足 … サイズは `bs` × `count` で決まります**

| `bs` | `count` | できるサイズ |
|:--|:--|:--|
| `1M` | `5` | 5 MiB |
| `1M` | `100` | 100 MiB |
| `4M` | `256` | 1 GiB |
| `512`（既定） | `1` | 512 バイト |

**`count` を付けないと、入力の終わりまで全部コピーします。**
ディスクを丸ごとコピーしたいときは `count` を付けません。

**補足 … `count` は「バイト数」ではありません**

`count=100` は「100 バイト」ではなく「**100 ブロック**」です。
1 ブロックの大きさは `bs` で決まります。
バイト数で指定したい場合は数値の末尾に `B` を付けます。

```bash
$ dd if=/dev/zero of=t bs=1M count=100         # 100 ブロック = 100MiB
$ dd if=/dev/zero of=t bs=1M count=100B        # 100 バイト（B を付けるとバイト指定）
```

### skip と seek

**意味** … 途中から読む（`skip`）／途中から書く（`seek`）

| | どちら側 | 意味 |
|:--|:--|:--|
| `skip=N` | **入力側** | 先頭から N ブロック読み飛ばしてから読み始める |
| `seek=N` | **出力側** | 先頭から N ブロック分の位置へ移動してから書き始める |

**例文**

```bash
$ printf 'ABCDEFGH' > src.bin        # 8 バイトのファイルを作る
$ dd if=src.bin bs=1 skip=4          # 先頭 4 バイトを飛ばして読む
EFGH4+0 records in
4+0 records out
4 bytes copied, 2.3345e-05 s, 171 kB/s
```

`EFGH` が表示され、`ABCD` は飛ばされています。
（`of` を省略したので、読んだ内容が画面＝標準出力に出ています）

**補足 … 覚え方**

```text
skip … 入力を「読み飛ばす」   → i の仲間（iseek とも書ける）
seek … 出力を「書く位置を探す」→ o の仲間（oseek とも書ける）
```

### status 進捗の表示

**意味** … 実行中・実行後に表示する情報の量を選ぶ

| 値 | 表示されるもの |
|:--|:--|
| `progress` | **コピー中の進捗を定期的に表示する** |
| `noxfer` | 最後の転送統計（バイト数・速度）を出さない |
| `none` | エラー以外は何も出さない |

**例文**

```bash
$ dd if=/dev/sda of=disk.img bs=4M status=progress   # 進捗を見ながらコピーする
1073741824 bytes (1.1 GB, 1.0 GiB) copied, 4 s, 268 MB/s
```

**補足 … `status=progress` が無い環境では**

`status=progress` は GNU coreutils 8.24 以降で使えます。
古い環境では、別の端末から `USR1` シグナルを送ると進捗が出ます。

```bash
$ kill -USR1 $(pgrep -x dd)          # 実行中の dd に進捗を出させる
```

`dd` は `USR1` を受け取ると統計を表示してコピーを続けます（`--help` に明記されています）。
**`kill` という名前ですが、この使い方ではプロセスは止まりません。**

### conv と iflag oflag

**意味** … 書き込み方や読み込み方の細かい挙動を変える

よく使うものだけ挙げます。

| 指定 | 意味 |
|:--|:--|
| `conv=notrunc` | **出力ファイルを切り詰めない**（既存ファイルの一部だけ書き換えたいとき） |
| `conv=noerror` | 読み取りエラーが出ても止まらずに続ける（壊れかけディスクの救出） |
| `conv=sync` | 読めなかった分を NUL で埋めて、サイズをずらさない |
| `conv=fsync` | 終了前に、実際にディスクへ書き込みきる |
| `oflag=direct` | OS のキャッシュを経由せず直接書く（速度測定などで使う） |
| `iflag=fullblock` | ブロックが埋まるまで読み続ける（パイプ入力のとき欠けを防ぐ） |

**例文 … `conv=notrunc` の有無で結果が変わる**

```bash
$ printf '0123456789' > n.bin                            # 10 バイトのファイルを用意する
$ printf 'XX' | dd of=n.bin bs=1 seek=3 conv=notrunc     # 4 バイト目から XX を上書きする
$ cat n.bin                                              # 前後が残っている
012XX56789
```

`conv=notrunc` を付けないと、**書いた位置より後ろが消えます**。

```bash
$ printf '0123456789' > n2.bin                           # もう一度 10 バイトを用意する
$ printf 'XX' | dd of=n2.bin bs=1 seek=3                 # notrunc なしで同じことをする
$ cat n2.bin                                             # 5 バイトに切り詰められた
012XX
```

**補足** … 壊れかけたディスクからデータを救出するときは、
`conv=noerror,sync` を組み合わせるのが定番です。
`noerror` で止まらずに読み進め、`sync` で読めなかった部分を NUL で埋めることで、
**後続データの位置がずれない**ようにします。

```bash
$ dd if=/dev/sdb of=rescue.img bs=4M conv=noerror,sync status=progress   # 読めない部分は NUL で埋め、止まらずに吸い出す
```

---

## サイズの単位

`bs` や `count` の数値には単位を付けられます。
**2 の累乗（K, M, G）と 10 の累乗（kB, MB, GB）が別物**なので注意します。

| 書き方 | 大きさ | 呼び方 |
|:--|--:|:--|
| `c` | 1 バイト | — |
| `b` | 512 バイト | ブロック |
| `K` / `KiB` | 1,024 バイト | キビバイト |
| `M` / `MiB` | 1,048,576 バイト | メビバイト |
| `G` / `GiB` | 1,073,741,824 バイト | ギビバイト |
| `kB` | 1,000 バイト | キロバイト |
| `MB` | 1,000,000 バイト | メガバイト |
| `GB` | 1,000,000,000 バイト | ギガバイト |

**確かめてみる**

```bash
$ dd if=/dev/zero of=t1 bs=1M count=5     # M は 1024*1024
$ ls -l t1                                # サイズを確認する
-rw-r--r-- 1 root root 5242880 Aug 31 15:15 t1     # 5,242,880 バイト

$ dd if=/dev/zero of=t2 bs=1MB count=5    # MB は 1000*1000
$ ls -l t2                                # サイズを確認する
-rw-r--r-- 1 root root 5000000 Aug 31 15:15 t2     # 5,000,000 バイト
```

**大文字の `M` は 1024 系、`MB` は 1000 系**。ここを取り違えると、
「1GB のはずが 1.07GB あった」といったズレが出ます。

---

## 実行結果の読み方

`dd` は終わると 3 行のサマリを**標準エラー出力**に出します。

```bash
$ dd if=input.txt of=output.txt      # 10 バイトのファイルをコピーする
0+1 records in                       # 読み込んだブロック数
0+1 records out                      # 書き出したブロック数
10 bytes copied, 2.5175e-05 s, 397 kB/s   # バイト数・所要時間・速度
```

**`0+1` の読み方**

```text
0 + 1
│   └─ 「途中で終わった（不完全な）ブロック」の数
└──── 「まるまる 1 ブロック分あった（完全な）ブロック」の数
```

上の例は 10 バイトのファイルです。ブロックサイズは既定の 512 バイトなので、
**512 バイトに満たない半端なブロックが 1 つ**だけありました。だから `0+1` です。

ちょうど割り切れる場合は右側が 0 になります。

```bash
$ dd if=/dev/zero of=testfile bs=1M count=5   # 割り切れる場合を試す
5+0 records in                       # 1MB のブロックがちょうど 5 個
5+0 records out
5242880 bytes (5.2 MB, 5.0 MiB) copied, 0.00302971 s, 1.7 GB/s
```

**補足 … サマリは標準エラー出力に出ます**

そのため `dd ... > file` でリダイレクトしても、サマリは画面に残ります。
消したいときは `status=none` を使うか、`2>/dev/null` を付けます。

```bash
$ dd if=input.txt of=output.txt status=none    # サマリを出さない
$ dd if=input.txt of=output.txt 2>/dev/null    # 標準エラー出力を捨てる
```

---

## 特殊なデバイスファイル

`dd` の `if=` に指定すると便利な、**中身が仮想的に作られるファイル**があります。

| デバイス | 読み出すと出てくるもの | 使いどころ |
|:--|:--|:--|
| `/dev/zero` | **NUL（0x00）が無限に出てくる** | 中身が空のダミーファイル作成、領域のゼロ埋め |
| `/dev/urandom` | 乱数が無限に出てくる | ランダムデータでの上書き、鍵素材の生成 |
| `/dev/null` | 何も出てこない（書き込むと捨てられる） | 出力の捨て先、読み出し速度の測定 |

**例文**

```bash
$ dd if=/dev/zero of=testfile bs=1M count=100      # 100MB の空ファイルを作る
$ dd if=/dev/urandom of=random.bin bs=1M count=10  # 10MB のランダムデータを作る
$ dd if=/dev/sda of=/dev/null bs=1M count=1024     # 読み出し速度だけを測る（書き込まない）
```

**補足 … `/dev/zero` と `/dev/null` の違い**

```text
/dev/zero … 読むと 0 が無限に出る   → データの「蛇口」
/dev/null … 書いたものが消える     → データの「排水口」
```

**注意** … `/dev/urandom` はデータを生成する処理が入るため、
`/dev/zero` より**かなり遅い**です。単にサイズが欲しいだけなら `/dev/zero` を使います。

---

## 業務で使う場面

### 1. OS イメージを USB へ書き込む

```bash
$ dd if=ubuntu.iso of=/dev/sdb bs=4M status=progress    # ISO を USB デバイスへ書く
$ sync                                                  # キャッシュを実ディスクへ確実に書き出す
```

```text
ubuntu.iso
    │
    ▼
   dd
    │
    ▼
USB メモリ（/dev/sdb）
```

**`of=` にはパーティション（`/dev/sdb1`）ではなくデバイス全体（`/dev/sdb`）を指定します。**
ISO にはブート情報が含まれており、ディスクの先頭から書かないと起動しません。

### 2. ディスクを丸ごとバックアップする

```bash
$ dd if=/dev/sda of=/backup/disk.img bs=4M status=progress    # ディスク全体をイメージ化する
```

**注意** … バックアップ元のディスクが**マウントされたままだと、
書き込み途中の状態を拾ってしまい、整合性が取れないイメージになる**ことがあります。
本来はレスキューモードや別 OS から起動して、アンマウントした状態で取ります。

### 3. イメージからディスクへ復元する

```bash
$ dd if=/backup/disk.img of=/dev/sda bs=4M status=progress    # イメージをディスクへ書き戻す
```

バックアップとは `if` と `of` の向きが逆になります。**ここを取り違えると、
バックアップイメージのほうがディスクの内容で上書きされて消えます。**

### 4. 検証用のダミーファイルを作る

```bash
$ dd if=/dev/zero of=testfile bs=1M count=100    # 約 100MB のファイルを作る
$ ls -lh testfile                                # サイズを確認する
-rw-r--r-- 1 root root 100M Aug 31 15:20 testfile
```

ディスク容量の逼迫試験、転送速度の測定、監視アラートの発報テストなどで使います。

### 5. ディスクの一部分だけ取り出す

```bash
$ dd if=/dev/sda of=mbr.bin bs=512 count=1       # 先頭 512 バイト（MBR）を取り出す
$ dd if=/dev/sda of=first1M.bin bs=1M count=1    # 先頭 1MB を取り出す
```

パーティションテーブルの破損調査や、ブートローダの退避で使います。

---

## dd は危険なコマンド

`dd` は**確認を一切しません**。`of=` に指定した先を、黙って上書きします。
`rm` のように「本当に消しますか？」とは聞いてくれません。

**取り違えの例**

```bash
$ dd if=/dev/sda of=/dev/sdb         # sda の内容を sdb へコピー（sdb が消える）
$ dd if=/dev/sdb of=/dev/sda         # 逆にすると sda が消える
```

`if` と `of` は 1 文字違いなので、**打ち間違いが致命傷になります**。

### 事故を防ぐ手順

**1. まず対象を確認する**

```bash
$ lsblk                              # デバイス名・サイズ・マウント先を一覧する
NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
sda      8:0    0  100G  0 disk
└─sda1   8:1    0  100G  0 part /
sdb      8:16   1   16G  0 disk               ← RM=1（リムーバブル）、16G = USB メモリ

$ sudo fdisk -l /dev/sdb             # 中身を確認して、消してよいデバイスか確かめる
```

**サイズとリムーバブル列（`RM`）で見分けるのが確実です。**

**2. 練習は普通のファイルで行う**

いきなり `/dev/sda` を触らず、まずファイル同士でコピーして挙動を掴みます。

**3. 上書きしたくないときは `conv=excl` を付ける**

```bash
$ dd if=input.txt of=output.txt conv=excl    # output.txt がすでにあれば失敗して止まる
dd: failed to open 'output.txt': File exists
```

**4. `of=` を打った直後に指を止めて読み返す**

現場では、この一拍が最も効きます。

---

## 手を動かして確かめる

危険のない範囲で、`dd` の基本を確かめる手順です。

**1. 練習用ディレクトリを作る**

```bash
$ mkdir -p ~/dd-practice             # 練習用のディレクトリを作る（-p で親ごと作る）
$ cd ~/dd-practice                   # そこへ移動する
```

**2. 入力ファイルを作る**

```bash
$ echo "Hello dd!" > input.txt       # 中身のあるファイルを作る
$ cat input.txt                      # 中身を確認する
Hello dd!
```

**3. `dd` でコピーする**

```bash
$ dd if=input.txt of=output.txt      # dd でコピーする
0+1 records in
0+1 records out
10 bytes copied, 2.5175e-05 s, 397 kB/s

$ cat output.txt                     # 同じ中身になっていることを確認する
Hello dd!
```

**4. `bs` と `count` でサイズを作り分ける**

```bash
$ dd if=/dev/zero of=t5m bs=1M count=5     # 1MB × 5回
$ dd if=/dev/zero of=t10m bs=1M count=10   # 1MB × 10回
$ ls -lh t5m t10m                          # サイズの違いを確認する
-rw-r--r-- 1 root root 5.0M Aug 31 15:15 t5m
-rw-r--r-- 1 root root  10M Aug 31 15:15 t10m
```

`bs` と `count` を掛けた値がサイズになる、という感覚をここで掴んでおきます。

**5. 後片付け**

```bash
$ cd ~                               # 練習ディレクトリの外へ出る
$ rm -r ~/dd-practice                # 練習用ディレクトリごと削除する
```

---

## つまずきポイント

| 症状 | 原因 | 対処 |
|:--|:--|:--|
| `dd: unrecognized operand '-i'` | `-i` `-o` のようなオプション形式で書いた | `if=` `of=` の形で書く |
| `dd: unrecognized operand` が出る | `if = input.txt` のように `=` の前後にスペースを入れた | スペースを入れない |
| 作ったファイルが思ったサイズでない | `M`（1024 系）と `MB`（1000 系）を混同した | 1024 系なら `M`、1000 系なら `MB` |
| `count=100` にしたのに 100 バイトにならない | `count` は**ブロック数**であってバイト数ではない | バイト指定なら `count=100B` |
| ディスクのコピーが極端に遅い | `bs` を省略して既定の 512 バイトで動いていた | `bs=4M` などを付ける |
| 既存ファイルの一部を書き換えたら後ろが消えた | `conv=notrunc` を付けていない | `conv=notrunc` を付ける |
| 進捗が全く見えない | `status=progress` を付けていない | 付ける。古い環境なら `kill -USR1` |
| リダイレクトしたのにサマリが画面に出る | サマリは標準エラー出力へ出るため | `status=none` または `2>/dev/null` |
| **別のディスクを消してしまった** | `if` と `of` を取り違えた | **復旧手段はない。** 実行前に `lsblk` で確認する習慣をつける |

---

## クラウド実務メモ

**クラウドでは `dd` の出番は多くありません**

AWS や Google Cloud では、ディスクのバックアップはマネージドの機能を使います。

| 用途 | オンプレでの手段 | クラウドでの手段 |
|:--|:--|:--|
| ディスクのバックアップ | `dd` でイメージ化 | AWS: **EBS スナップショット** / Google Cloud: **Persistent Disk スナップショット** / Azure: **マネージドディスクのスナップショット** |
| ディスクの複製 | `dd` でコピー | スナップショットから新しいボリュームを作成 |
| OS イメージの配布 | ISO を `dd` で書き込み | AMI / カスタムイメージ |

スナップショットは**増分バックアップで、稼働中のボリュームに対して取得できる**ため、
`dd` のようにアンマウントを気にする必要がありません。

**それでも `dd` を使う場面**

| 場面 | 内容 |
|:--|:--|
| ディスク性能の測定 | `dd if=/dev/zero of=test bs=1M count=1024 oflag=direct` で書き込み速度を測る |
| 容量逼迫のテスト | ダミーファイルでディスクを埋め、監視アラートの発報を確認する |
| オンプレからの移行 | 物理サーバのディスクをイメージ化し、`VM Import/Export` などへ渡す |
| 障害調査 | パーティションテーブルやブートセクタを取り出して中身を確認する |
| ボリューム暗号化前の準備 | 領域を `/dev/zero` や `/dev/urandom` で埋める |

**性能測定の注意**

`oflag=direct` を付けないと OS のページキャッシュに書いただけで終わり、
**実際のディスク性能ではなくメモリの速度を測ってしまいます**。

```bash
$ dd if=/dev/zero of=testfile bs=1M count=1024 oflag=direct    # キャッシュを通さず測る
```

読み出し側を測るときは、事前にキャッシュを落とします。

```bash
$ sync                                          # 未書き込みのデータを書き出す
$ echo 3 | sudo tee /proc/sys/vm/drop_caches    # ページキャッシュを破棄する
$ dd if=testfile of=/dev/null bs=1M             # 読み出し速度を測る
```

**EC2 での注意**

gp3 / gp2 ボリュームには **IOPS とスループットの上限**があります。
`dd` で測った値がカタログスペックに届かない場合、ディスクの問題ではなく
**インスタンスタイプ側の EBS 帯域上限**に当たっていることがあります。

---

## 参考リンク

- [GNU Coreutils Manual — dd invocation](https://www.gnu.org/software/coreutils/manual/html_node/dd-invocation.html)
- [man 1 dd](https://man7.org/linux/man-pages/man1/dd.1.html)
- [man 4 null（/dev/null, /dev/zero）](https://man7.org/linux/man-pages/man4/null.4.html)
- [man 4 random（/dev/random, /dev/urandom）](https://man7.org/linux/man-pages/man4/random.4.html)
- [AWS — Amazon EBS スナップショット](https://docs.aws.amazon.com/ja_jp/ebs/latest/userguide/ebs-snapshots.html)

---

[← このフォルダの目次にもどる](./00_このフォルダにあるもの.md) ｜ [全体の目次にもどる](../README.md)
