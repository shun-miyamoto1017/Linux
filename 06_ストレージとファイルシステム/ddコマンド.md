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
- [データを確実に消す](#データを確実に消す)
  - [rm では消えない](#rm-では消えない)
  - [mkfs で消えるかどうかは discard 次第](#mkfs-で消えるかどうかは-discard-次第)
  - [dd で全領域を上書きする](#dd-で全領域を上書きする)
  - [zero と urandom の使い分け](#zero-と-urandom-の使い分け)
  - [shred という専用コマンド](#shred-という専用コマンド)
  - [SSD では上書きが効かない](#ssd-では上書きが効かない)
- [dd は危険なコマンド](#dd-は危険なコマンド)
- [参考リンク](#参考リンク)

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
$ dd if=/dev/zero of=testfile bs=1M count=5    # 1MiB を 5 回 = 5MiB のファイルを作る
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
$ dd if=/dev/zero of=testfile bs=1M count=5    # 1MiB × 5回 = 5MiB
$ dd if=/dev/sda of=first1M.bin bs=1M count=1  # ディスクの先頭 1MiB だけ取り出す
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
$ dd if=/dev/zero of=testfile bs=1M count=100      # 100MiB の空ファイルを作る
$ dd if=/dev/urandom of=random.bin bs=1M count=10  # 10MiB のランダムデータを作る
$ dd if=/dev/sda of=/dev/null bs=1M count=1024     # 1GiB ぶん読んで速度だけを測る（書き込まない）
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
$ dd if=/dev/zero of=testfile bs=1M count=100    # 100MiB のファイルを作る
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

## データを確実に消す

**ディスクを廃棄・返却・譲渡するとき、「ファイルを消しただけ」では中身が残ります。**
ここは `dd` の代表的な用途であり、情報漏えい事故の定番の原因でもあります。

64MiB のループバックファイルシステムを作り、実際に何が残るか測りました。

```bash
$ dd if=/dev/zero of=disk.img bs=1M count=64 status=none   # 64MiB のイメージを作る
$ mkfs.ext4 -q -F disk.img                                 # ext4 を作る
$ mkdir mnt && mount -o loop disk.img mnt                  # マウントする
$ dd if=/dev/zero of=mnt/pad.bin bs=1M count=20 status=none   # データ領域を先へ押し出す
```

### rm では消えない

```bash
$ echo "極秘: この文字列は消えたか SECRET-STRING-12345" > mnt/secret.txt   # 機密ファイルを作る
$ umount mnt                                                               # アンマウントする
$ strings -t d disk.img | grep "SECRET-STRING"                             # イメージを直接検索する
```

```text
29429766  SECRET-STRING-12345
```

**先頭から 29,429,766 バイト目に、そのまま残っています。**
ここでファイルを削除して、もう一度検索します。

```bash
$ mount -o loop disk.img mnt                # マウントし直す
$ rm mnt/secret.txt                         # ファイルを削除する
$ umount mnt                                # アンマウントする
$ strings -t d disk.img | grep "SECRET-STRING"   # もう一度検索する
```

```text
29429766  SECRET-STRING-12345
```

**まったく同じ位置に、まったく同じ内容で残っています。**

```text
   rm がやっていること
     ・ディレクトリエントリからファイル名を外す
     ・inode を未使用としてマークする
        ↓
   データブロックの中身には一切触らない
        → 上書きされるまで、そのまま読める
```

**ファイル削除ツールや `rm -rf` では、ディスクの廃棄要件を満たせません。**

### mkfs で消えるかどうかは discard 次第

**「ファイルシステムを作り直せば消える」と言われますが、条件によります。** 実測します。

まず `-E nodiscard` を付けた場合。

```bash
$ mkfs.ext4 -q -F -E nodiscard disk.img     # discard を抑止してファイルシステムを作り直す
$ strings -t d disk.img | grep "SECRET-STRING"   # 検索する
```

```text
29429766  SECRET-STRING-12345
```

**残っています。** `mkfs` は管理情報（スーパーブロック・inode テーブルなど）を書き直すだけで、
データ領域には手を付けないからです。

ところが、**既定のまま実行すると消えました。**

```bash
$ mkfs.ext4 -F disk.img | grep -i discard   # 既定で実行して出力を見る
```

```text
Discarding device blocks:     0/16384           done                            
```

```bash
$ strings -t d disk.img | grep "SECRET-STRING"   # 検索する
$ echo "exit=$?"                                 # 見つからなければ 1
```

```text
exit=1
```

**`Discarding device blocks` が走っているのが原因**です。
ループバックファイルの場合、discard は穴あけ（punch hole）として実装されるため、
実際にデータが消えます。ファイルサイズの見え方でも確認できます。

```bash
$ du -h --apparent-size disk.img            # 見かけのサイズ
$ du -h disk.img                            # 実際に使っているサイズ
```

```text
64M	disk.img
4.2M	disk.img
```

**64MiB のはずが、実使用は 4.2MiB。**
中身が無い部分に実領域を割り当てない「**スパースファイル**」になっています。

```text
   discard が効く環境（SSD、シンプロビジョニング、ループバックファイル）
        → mkfs でもデータが消えることがある
   discard が効かない環境（従来型の HDD、-E nodiscard 指定時）
        → mkfs ではデータは残る
```

**「mkfs すれば安全」とは言えません。**
環境によって結果が変わるので、**確実に消したいなら次の上書きを行ってください。**

### dd で全領域を上書きする

**唯一確実なのは、全領域を別のデータで塗りつぶすこと**です。

```bash
$ dd if=/dev/zero of=/dev/sdc1 bs=1M        # ゼロで全領域を埋める
$ dd if=/dev/urandom of=/dev/sdc1 bs=1M     # 乱数で全領域を埋める
```

**`if=` / `of=` を使わず、リダイレクトでも書けます。**

```bash
$ dd bs=1M count=64 < /dev/urandom > disk.img    # リダイレクト形式で乱数を書き込む
$ od -A d -t x1 -N 32 disk.img                   # 先頭を覗いて確認する
```

```text
0000000 8a be bb c7 57 6b 28 8e a3 44 73 c8 ff eb 55 89
0000016 9d d6 da 04 42 ea 39 68 9b a5 e5 5a 5b 8b e2 2e
```

**乱数で埋まっています。** 機密文字列も、もちろん消えています。

```bash
$ strings -t d disk.img | grep "SECRET-STRING"   # 検索する
$ echo "exit=$?"                                 # 見つからなければ 1
```

```text
exit=1
```

**上書き後はファイルシステムの管理情報も潰れる**ので、マウントできなくなります。

```bash
$ mount -o loop disk.img mnt                # マウントしてみる
```

```text
mount: /tmp/w20/erase/mnt: wrong fs type, bad option, bad superblock on /dev/loop0,
       missing codepage or helper program, or other error.
       dmesg(1) may have more information after failed mount system call.
（終了ステータス 32）
```

**`bad superblock` は正常な反応**です。再利用するなら `mkfs` からやり直してください。

**デバイス全体を消すときは、パーティションではなくデバイスを指定します。**

```bash
$ dd if=/dev/zero of=/dev/sdc bs=1M status=progress   # パーティションテーブルごと消す
```

`/dev/sdc1` を消してもパーティションテーブルと MBR は残ります。
**丸ごと消すなら数字なしの `/dev/sdc`** です。

### zero と urandom の使い分け

**速度が大きく違います。** 512MiB を読み出して測りました。

```bash
$ dd if=/dev/zero of=/dev/null bs=1M count=512       # ゼロの生成速度を測る
$ dd if=/dev/urandom of=/dev/null bs=1M count=512    # 乱数の生成速度を測る
```

```text
/dev/zero      536870912 bytes (537 MB, 512 MiB) copied, 0.0173133 s, 31.0 GB/s
/dev/urandom   536870912 bytes (537 MB, 512 MiB) copied, 1.46211 s, 367 MB/s
```

**31.0 GB/s 対 367 MB/s。約 84 倍の差**があります。
`/dev/urandom` は乱数を生成する処理が入るぶん、どうしても遅くなります。

| 用途 | 使うもの |
|:--|:--|
| 社内で再利用するディスクの消去 | **`/dev/zero`**（速い。これで十分） |
| 外部へ返却・廃棄するディスク | `/dev/urandom`（パターンが残らない） |
| ダミーファイルを作りたいだけ | **`/dev/zero`** |

**1TB のディスクを乱数で埋めると、計算上 45 分以上かかります。**
時間の見積もりを誤ると、作業窓に収まりません。

### shred という専用コマンド

**消去専用のコマンドもあります。**

```bash
$ shred --help | grep -E '^ +-[nuvz],'      # 主要なオプションを確認する
```

```text
  -n, --iterations=N  overwrite N times instead of the default (3)
  -v, --verbose  show progress
  -z, --zero     add a final overwrite with zeros to hide shredding
```

| オプション | 意味 |
|:--|:--|
| `-n N` | **N 回上書きする**（既定 3 回） |
| `-z` | 最後にゼロで上書きし、消去の痕跡を隠す |
| `-u` | 上書き後にファイルを削除する |
| `-v` | 進捗を表示する |

```bash
$ shred -vzn 1 /dev/sdc1                    # 1回上書きしてゼロで仕上げる
```

**現代のディスクでは 1 回の上書きで十分**というのが一般的な見解です。
既定の 3 回は磁気ディスク時代の名残で、時間がかかるだけのことが多くなっています。

### SSD では上書きが効かない

**重要な注意です。**

```text
   SSD はウェアレベリングにより、書き込み先の物理ブロックを内部で入れ替える
        ↓
   論理アドレスを上書きしても、元のデータが入った物理ブロックは残る
        ↓
   dd や shred での上書きは、SSD では確実な消去にならない
```

**SSD の消去にはデバイス側の機能を使います。**

```bash
$ hdparm -I /dev/sda | grep -i "erase"      # Secure Erase に対応しているか確認する
$ nvme format /dev/nvme0n1 --ses=1          # NVMe の Secure Erase
```

**暗号化しておくのが最も確実**です。
LUKS で暗号化してあれば、**鍵を破棄するだけでデータは復元不能**になります。
クラウドの EBS / マネージドディスクが「削除すれば安全」と言えるのも、同じ理屈（暗号消去）です。

> 暗号化の詳細は [ディスクの暗号化 dm-cryptとLUKS](./ディスクの暗号化_dm-cryptとLUKS.md) を参照してください。

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

## 参考リンク

- [GNU Coreutils Manual — dd invocation](https://www.gnu.org/software/coreutils/manual/html_node/dd-invocation.html)
- [man 1 dd](https://man7.org/linux/man-pages/man1/dd.1.html)
- [man 4 null（/dev/null, /dev/zero）](https://man7.org/linux/man-pages/man4/null.4.html)
- [man 4 random（/dev/random, /dev/urandom）](https://man7.org/linux/man-pages/man4/random.4.html)
- [AWS — Amazon EBS スナップショット](https://docs.aws.amazon.com/ja_jp/ebs/latest/userguide/ebs-snapshots.html)

---

[← 全体の目次にもどる](../README.md)
