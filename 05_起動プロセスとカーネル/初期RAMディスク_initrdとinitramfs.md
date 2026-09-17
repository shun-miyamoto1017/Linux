# 初期RAMディスク initrdとinitramfs

| | |
|:--|:--|
| **学習の順番** | Phase2 ★★★★☆（Linuxカーネルの構成要素 ／ ブートプロセスとGRUB） |
| **Ping-t の範囲** | Linux2 / システムの起動とLinuxカーネル(主題2.01〜2.02) — Linuxカーネルの構成要素、Linuxカーネルのコンパイル |
| **業務での使いどころ** | **起動しないサーバの切り分け**。`Cannot open root device` や `kernel panic` の原因の多くがここ |

> カーネル本体のビルドとインストール（`make install` / `/boot` の中身）は
> [カーネルのビルドとインストール](./カーネルのビルドとインストール.md) にまとめています。
> このノートは**初期RAMディスクだけ**を扱います。

---

## 目次

- [何のためにあるのか](#何のためにあるのか)
- [initrdとinitramfsの違い](#initrdとinitramfsの違い)
- [作成するコマンド](#作成するコマンド)
- [中身を取り出す](#中身を取り出す)
- [cpio のよく使うオプション](#cpio-のよく使うオプション)
- [gunzip と zcat の使い分け](#gunzip-と-zcat-の使い分け)
- [結果画面の見方](#結果画面の見方)
- [よく使う確認コマンドまとめ](#よく使う確認コマンドまとめ)
- [参考リンク](#参考リンク)

---

## 何のためにあるのか

### 鶏と卵の問題

Linux の起動で、こういう困った状況が起こります。

```text
  カーネルが起動した
        │
        ▼
  ルートファイルシステム（/）をマウントしたい
        │
        ▼
  でも、そのディスクを読むには「ドライバ」が必要
        │
        ▼
  そのドライバは…… ルートファイルシステムの中にある
        │
        ▼
  読むためにマウントしたいのに、マウントするには読まないといけない ← 詰み
```

**この行き詰まりを解くのが、初期RAMディスクです。**

ブートローダ（GRUB）が、カーネルと**一緒に**初期RAMディスクをメモリへ読み込みます。
カーネルはそれをメモリ上で展開し、**一時的なルートファイルシステム**として使います。
そこには必要なドライバが入っているので、本物のディスクを読めるようになります。

---

### 起動の流れ

```text
 ① GRUB が 2 つのファイルをメモリに読み込む
      /boot/vmlinuz-6.1.0      （カーネル本体）
      /boot/initrd.img-6.1.0   （初期RAMディスク）
                │
                ▼
 ② カーネルが起動し、initrd をメモリ上に展開する
      → メモリの中に、小さな「/」ができる
                │
                ▼
 ③ その中の /init（または linuxrc）が動き、必要なドライバを読み込む
      例：RAID / LVM / 暗号化 / NVMe / iSCSI のドライバ
                │
                ▼
 ④ 本物のルートファイルシステムをマウントできるようになる
                │
                ▼
 ⑤ ルートを本物のディスクに切り替える（switch_root / pivot_root）
      → メモリ上の一時的な「/」は捨てられる
                │
                ▼
 ⑥ /sbin/init（systemd）が起動して、通常の起動処理へ
```

**ポイント**

> 初期RAMディスクは **「ルートに切り替えるまでの足場」** です。
> 切り替えが終わったら役目を終えて、メモリから消えます。

---

### なぜ全部カーネルに組み込まないのか

「最初からカーネル本体に全ドライバを入れておけば要らないのでは？」という疑問が出ます。

| やり方 | 良い点 | 困る点 |
|:--|:--|:--|
| **全部カーネルに組み込む**（`y`） | 初期RAMディスクが不要になる | **あらゆる機種のドライバを積む**ので巨大になり、使わない分までメモリを占有する |
| **モジュールにして initrd に積む**（`m`） | カーネルが小さく済む。**1 つのカーネルでどんな機種でも動く** | 初期RAMディスクが必要になる |

ディストリビューションが配るカーネルは、**どんな PC やサーバでも動かなければいけません。**
そのため後者を選んでおり、**結果として初期RAMディスクが必須**になっています。

自分専用にビルドして、ルートFSのドライバを `y` で組み込めば、初期RAMディスクなしでも起動できます。

---

## initrdとinitramfsの違い

**ここが一番ややこしいところです。**表で並べます。

| | **initrd**（古い方式） | **initramfs**（現在の方式） |
|:--|:--|:--|
| **正式名称** | initial RAM **disk** | initial RAM **file system** |
| **中身の正体** | **ファイルシステムのイメージ**（ext2 などでフォーマットされた「仮想的なディスク」） | **cpio アーカイブ**（`tar` のようにファイルを 1 本にまとめたもの） |
| **圧縮** | gzip で圧縮されている | gzip（や lz4 / zstd）で圧縮されている |
| **カーネルの扱い** | **RAM ディスクという仮想ブロックデバイス**として認識し、そこにファイルシステムをマウントする | **tmpfs 上に直接展開する**。ブロックデバイスを作らない |
| **サイズ** | **作成時に決め打ち**。使わなくてもその分メモリを取る | **中身の分だけ**。無駄がない |
| **最初に動くプログラム** | **`/linuxrc`** | **`/init`** |
| **中を見る方法** | `gunzip` ＋ **`mount -o loop`** | `gunzip` ＋ **`cpio -id`** |
| **今使われているか** | ほぼ使われていない（古い環境のみ） | **現在のディストリはすべてこちら** |

### 一文で言うと

> **initramfs 形式のイメージは、`cpio` アーカイブを `gzip` 圧縮したものです。**

```text
   中のファイル群
        │ ① cpio でひとつにまとめる
        ▼
   cpio アーカイブ
        │ ② gzip で圧縮する
        ▼
   initramfs イメージ（/boot/initrd.img-…）
```

**この順番が問われます。**「gzip したものを cpio でまとめる」ではありません。

| 正しい組み合わせ | 誤り |
|:--|:--|
| **`cpio` アーカイブを `gzip` 圧縮** | `gzip` を `cpio` 圧縮 ／ `tar` を `gzip` 圧縮 ／ `zip` を `cpio` 圧縮 |

だから**開くときは逆順**になります。

```text
   ① gunzip で圧縮を解く  →  ② cpio -id で取り出す
```

---

### 名前にだまされない

**ファイル名が `initrd.img` でも、中身は initramfs であることがほとんどです。**

| ディストリ | ファイル名 | 中身の方式 |
|:--|:--|:--|
| **Debian / Ubuntu** | `/boot/initrd.img-6.1.0-18-amd64` | **initramfs**（名前だけ古い） |
| **RHEL / CentOS / Rocky** | `/boot/initramfs-5.14.0-70.el9.x86_64.img` | **initramfs** |

これは、**GRUB の設定や手順書が `initrd` という名前で書かれていた歴史があり、互換性のために名前を変えなかった**ためです。

**中身がどちらかは、ファイルを調べれば分かります。**

```bash
$ file /boot/initrd.img-6.1.0-18-amd64                # 中身の種類を判定する
/boot/initrd.img-6.1.0-18-amd64: ASCII cpio archive (SVR4 with no CRC)

$ zcat /boot/initrd.img-6.1.0-18-amd64 | file -       # 圧縮を解いてから判定する
/dev/stdin: ASCII cpio archive (SVR4 with no CRC)     ← cpio なので initramfs
```

| `file` の結果 | 判定 | 開き方 |
|:--|:--|:--|
| `ASCII cpio archive` | **initramfs** | `cpio -id` |
| `Linux rev 1.0 ext2 filesystem data` | **initrd** | `mount -o loop` |
| `gzip compressed data` | まだ圧縮されている | 先に `gunzip` |

---

### 図で並べる

```text
 ■ initramfs（現在）
    initrd.img.gz  ──gunzip──▶  initrd.img（cpio アーカイブ）
                                      │
                                   cpio -id
                                      ▼
                                中のファイルが取り出される

 ■ initrd（古い）
    initrd.img.gz  ──gunzip──▶  initrd.img（ext2 のディスクイメージ）
                                      │
                                mount -o loop
                                      ▼
                                /mnt の下に中身が見える
```

---

## 作成するコマンド

初期RAMディスクは、**カーネルをインストールすると自動で作られます**（`make install` やパッケージ更新のとき）。
手で作り直すのは、**ドライバを足したい／壊れたので作り直したい**ときです。

| コマンド | どのディストリ | 位置づけ |
|:--|:--|:--|
| **`mkinitramfs`** | **Debian 系**（Ubuntu 含む） | initramfs を作る**低レベルのツール** |
| **`update-initramfs`** | **Debian 系** | `mkinitramfs` を呼び出す**ラッパー**。実務ではこちらを使う |
| **`dracut`** | **RHEL 系**（RHEL / CentOS / Rocky / Fedora）、SUSE | 現在の標準。モジュール方式で拡張できる |
| **`mkinitrd`** | **古い RHEL 系**（RHEL 5 以前） | 現在は `dracut` へのラッパーとして残っている環境もある |

> **試験では `mkinitrd` / `mkinitramfs` / `dracut` の 3 つが「初期RAMディスクを作るコマンド」**として問われます。
> どれも同じ目的のコマンドで、**ディストリによって名前が違う**と理解しておけば十分です。

**存在しないコマンド名にだまされない**

選択肢には、**それらしいが実在しないコマンド**が混ざります。

| 名前 | 実在するか |
|:--|:--:|
| **`mkinitrd`** / **`mkinitramfs`** / **`dracut`** | **する** |
| `mkramdisk` | **しない** |
| `makeramdisk` | **しない** |
| `mkinitramdisk` | **しない** |

> 「RAM ディスク」という言葉から `ramdisk` を含む名前を選びたくなりますが、
> **実在するのは `initrd` / `initramfs` / `dracut` を含む 3 つだけ**です。

---

### 書式の違いに注意する

`mkinitrd` と `mkinitramfs` は、**出力先の書き方が違います。**ここが頻出です。

| コマンド | 書式 | 出力先の指定 |
|:--|:--|:--|
| **`mkinitrd`** | `mkinitrd 出力先 バージョン` | **オプション無し**で、そのまま引数に書く |
| **`mkinitramfs`** | `mkinitramfs -o 出力先 バージョン` | **`-o` が必須** |

```text
  mkinitrd      /boot/initrd.img  2.6.38.3      ← -o は付けない
  mkinitramfs -o /boot/initrd.img  2.6.38.3     ← -o が要る
                ▲
          ここの有無だけが違う
```

**作られる形式も違います。**

| コマンド | 作られる形式 | 中身 |
|:--|:--|:--|
| **`mkinitrd`** | **initrd** 形式 | ファイルシステムのイメージ |
| **`mkinitramfs`** | **initramfs** 形式 | **cpio アーカイブ** |
| **`dracut`** | **initramfs** 形式 | cpio アーカイブ |

> **「cpio アーカイブを利用した形式で作りたい」＝ `mkinitramfs`（または `dracut`）** です。
> `mkinitrd` では作れません。

**例文**

```bash
$ sudo mkinitramfs -o /boot/initrd.img 2.6.38.3      # cpio形式(initramfs)で作る。-o が必須
$ sudo mkinitrd /boot/initrd.img 2.6.38.3            # initrd形式で作る。-o は付けない
```

---

### mkinitramfs

**意味**

Debian 系で initramfs イメージを作る、低レベルのコマンドです。
**出力先の指定（`-o`）が必須**という点だけは押さえてください。

**例文**

```bash
$ mkinitramfs -o initrd.img.gz `uname -r`            # 今動いているカーネル用のイメージを作る
$ mkinitramfs -o /boot/initrd.img-6.1.0-18-amd64 6.1.0-18-amd64   # バージョンを明示して作る
$ mkinitramfs -o ~/test.img -v 6.1.0-18-amd64        # 何を入れたか表示しながら作る
```

**よく使うオプション**

| オプション | 意味 | 補足 |
|:--|:--|:--|
| **`-o 出力先`** | **出力先のファイルを指定する** | **必須**。指定しないとエラーになる |
| **`-v`** | **詳しく表示する**（verbose） | どのモジュールを取り込んだか分かる |
| **`-k`** | **作業用の一時ディレクトリを消さずに残す** | 中身を調べたいときに便利 |
| **`-c 圧縮方式`** | 圧縮方式を指定する（`gzip` / `lz4` / `zstd` / `xz`） | 設定ファイルの既定を上書きする |
| **`-l レベル`** | 圧縮レベルを指定する | サイズと展開速度のバランス調整 |
| **`-d 設定ディレクトリ`** | 設定ディレクトリを変える（既定 `/etc/initramfs-tools`） | 検証用の設定で作りたいとき |
| **`-r ルート`** | ルートデバイスの指定を上書きする | 別環境向けに作るとき |
| **`version`**（引数） | **対象のカーネルバージョン** | 省略すると**動いているカーネル**が対象 |

**補足**

- `` `uname -r` `` … バッククォートで囲むと、**その中のコマンドを実行した結果に置き換わります**。`$(uname -r)` とまったく同じ意味で、`$( )` のほうが新しく推奨される書き方
- 実務では、直接 `mkinitramfs` を打たずに **`update-initramfs`** を使うのが普通です

```bash
$ sudo update-initramfs -u                           # 動いているカーネルのイメージを更新する
$ sudo update-initramfs -u -k 6.1.0-18-amd64         # バージョンを指定して更新する
$ sudo update-initramfs -c -k 6.1.0-18-amd64         # 新規に作成する
$ sudo update-initramfs -u -k all                    # 入っている全カーネル分を作り直す
```

| `update-initramfs` のオプション | 意味 |
|:--|:--|
| **`-u`** | update。既存のイメージを**更新する** |
| **`-c`** | create。**新しく作る** |
| **`-d`** | delete。**削除する** |
| **`-k バージョン`** | 対象のカーネル。`all` で全部 |
| **`-v`** | 詳しく表示する |

---

### dracut

**意味**

RHEL 系で initramfs を作る、現在の標準コマンドです。
**`root` 権限が必要**です（ルートファイルシステムの中身を読む必要があるため）。

**例文**

```bash
$ sudo dracut -f                                     # 動いているカーネルのイメージを作り直す
$ sudo dracut -f /boot/initramfs-$(uname -r).img $(uname -r)   # 出力先とバージョンを明示する
$ sudo dracut --regenerate-all -f                    # 入っている全カーネル分を作り直す
$ sudo dracut -f --add "lvm crypt"                   # LVM と暗号化のモジュールを追加して作る
```

**よく使うオプション**

| オプション | 意味 | 補足 |
|:--|:--|:--|
| **`-f`** / `--force` | **既存のファイルを上書きする** | 付けないと「すでにある」と言われて止まる |
| **`--kver バージョン`** | 対象のカーネルバージョンを指定する | 出力先を書かずにバージョンだけ指定できる |
| **`--regenerate-all`** | **入っている全カーネル分**を作り直す | カーネル更新後の復旧で使う |
| **`-v`** / `--verbose` | 詳しく表示する（`-vv` のように重ねるとさらに詳しくなる） | 何を取り込んだか調べる |
| **`-H`** / `--hostonly` | **この機種で必要なドライバだけ**を入れる | 小さく速くなるが、**別の機種では起動できない** |
| **`-N`** / `--no-hostonly` | **汎用的に全部入れる** | ディスクを別サーバに移す可能性があるとき |
| **`--add モジュール`** | dracut モジュールを**追加**する | `lvm`、`crypt`、`nfs` など |
| **`--omit モジュール`** | dracut モジュールを**除外**する | サイズを削りたいとき |
| **`--add-drivers ドライバ`** | カーネルモジュール（`.ko`）を名指しで**追加**する | 特殊な NIC / HBA を認識させたいとき |
| **`-M`** / `--show-modules` | 取り込んだモジュールの一覧を表示する | 検証用 |
| **`--print-cmdline`** | 推定されたカーネルコマンドラインを表示する | 起動オプションの確認 |

**補足**

- **`-H`（hostonly）は既定で有効**なディストリが多いです。**ディスクイメージを別のハードウェアへ移すと起動しない**原因になります
- 出力先を省略すると、ディストリの既定の場所（RHEL 系なら `/boot/initramfs-<バージョン>.img`）に作られます

---

### mkinitrd

**意味**

古い RHEL 系（RHEL 5 以前）で使われていたコマンドです。
現在の RHEL 系では、**`dracut` を呼び出すだけの互換用スクリプト**として残っている場合があります。

**例文**

```bash
$ sudo mkinitrd /boot/initrd-$(uname -r).img $(uname -r)   # 出力先とバージョンを指定して作る
```

**補足**

- **引数の順番が `出力先` → `バージョン`** で、`mkinitramfs` のように `-o` を付けない点が違います
- 新しい環境では **`dracut` を使ってください**。`mkinitrd` は互換のために名前が残っているだけです

---

## 中身を取り出す

**専用ツールは要りません。**`gunzip` / `cpio` / `mount` という、もとから入っている汎用コマンドで開けます。

> **どちらの方式かで、手順が変わります。**
> - **initramfs（cpio）** → `gunzip` ＋ **`cpio`**
> - **initrd（ディスクイメージ）** → `gunzip` ＋ **`mount -o loop`**
>
> **cpio は initrd には使えません。** initrd は cpio アーカイブではなくファイルシステムだからです。

---

### initramfs を展開する

**手順**

| 手順 | コマンド | 何が起きるか |
|:--|:--|:--|
| **①** | `mkinitramfs -o initrd.img.gz \`uname -r\`` | 調べたいイメージを用意する（既存のものをコピーしてもよい） |
| **②** | `gunzip initrd.img.gz` | **gzip の圧縮を解く**。`initrd.img`（cpio アーカイブ）になる |
| **③** | `mkdir work && cd work` | 展開先の空ディレクトリを作って移動する（**散らかさないため**） |
| **④** | `cpio -id < ../initrd.img` | **cpio アーカイブから中身を取り出す** |

**例文**

```bash
$ mkinitramfs -o initrd.img.gz `uname -r`            # 現在のカーネル用のイメージを作る
$ gunzip initrd.img.gz                               # 圧縮を解く（initrd.img になる）
$ mkdir work                                         # 展開先のディレクトリを作る
$ cd work                                            # 中身が散らからないよう移動する
$ cpio -id < ../initrd.img                           # cpio アーカイブを展開する
$ ls                                                 # 展開された中身を確認する
bin  conf  cryptroot  etc  init  lib  run  sbin  scripts  usr  var
```

**補足**

- `gunzip` は**元の `.gz` を消して**展開後のファイルを残します。元を残したいなら `gunzip -c 元.gz > 先` または `zcat`
- `<` … ファイルの中身をコマンドの**標準入力へ流し込む**記号（リダイレクト）。`cpio` はアーカイブを標準入力から読むので必要です
- **空のディレクトリで実行してください。**`cpio -id` はカレントディレクトリに展開するので、ソースの上でやると混ざります

**1 行でやる書き方**

```bash
$ mkdir work && cd work && zcat /boot/initrd.img-$(uname -r) | cpio -idmv   # 展開先を作り、圧縮を解いて展開する
```

| 部品 | 意味 |
|:--|:--|
| `mkdir work` | 展開先のディレクトリを作る |
| `&&` | **前のコマンドが成功したときだけ**次を実行する |
| `cd work` | そこへ移動する |
| `zcat ファイル` | **gzip を解いた内容を標準出力へ流す**（`gunzip -c` と同じ） |
| `\|` | 左の出力を右の入力につなぐ（パイプ） |
| `cpio -idmv` | 展開する（`-d` ディレクトリ作成／`-m` 更新日時を保つ／`-v` 表示） |

---

### initrd をマウントする

古い方式の `initrd` は **ファイルシステムのイメージ**なので、**マウントして中を見ます。**

**手順**

| 手順 | コマンド | 何が起きるか |
|:--|:--|:--|
| **①** | `gunzip initrd.img.gz` | **gzip の圧縮を解く**。`initrd.img`（ext2 などのイメージ）になる |
| **②** | `mkdir /mnt/ram` | マウント先のディレクトリを用意する |
| **③** | `mount -o loop initrd.img /mnt/ram` | **ループバックでマウントする** |
| **④** | `ls /mnt/ram` | 中身が見える |
| **⑤** | `umount /mnt/ram` | 見終わったら**必ず外す** |

**例文**

```bash
$ gunzip initrd.img.gz                               # 圧縮を解く（initrd.img になる）
$ sudo mkdir -p /mnt/ram                             # マウント先のディレクトリを用意する
$ sudo mount -o loop initrd.img /mnt/ram             # ループバックデバイス経由でマウントする
$ ls /mnt/ram                                        # 中身を確認する
bin  dev  etc  lib  linuxrc  proc  sbin  sys
$ sudo umount /mnt/ram                               # 見終わったらアンマウントする
```

---

### なぜ loop が必要なのか

**`mount` は本来、「デバイスファイル」をマウントするコマンドです。**

```bash
$ sudo mount /dev/sdb1 /mnt                          # ふつうの使い方：デバイスファイルを指定する
```

`initrd.img` は `/dev/sdb1` のようなデバイスファイルではなく、**ただのファイル**です。
そのままでは `mount` が受け付けません。

そこで **ループバックデバイス** という仕組みを使います。

```text
   initrd.img （ただのファイル）
          │
          │  「これをディスクだと思って扱ってください」
          ▼
   /dev/loop0 （仮想的なブロックデバイス）
          │
          │  mount
          ▼
     /mnt/ram に中身が見える
```

**`-o loop` は、この「ファイルを仮想デバイスとして扱う」指定です。**

| 書き方 | 結果 |
|:--|:--|
| **`mount -o loop initrd.img /mnt/ram`** | **正しい**。`-o` はマウントオプションを指定する書き方で、その値として `loop` を渡す |
| `mount -loop initrd.img /mnt/ram` | **誤り**。`-loop` というオプションは存在しない |
| `mount -o initrd.img /mnt/ram` | **誤り**。`-o` の後ろはオプション名を書く場所で、ファイル名を書く場所ではない |
| `mount --loop initrd.img /mnt/ram` | **誤り**。長い形式でも `--loop` は無い |

**補足**

- `-o` は option の頭文字。`-o ro`（読み取り専用）、`-o noexec`（実行禁止）のように、カンマ区切りで複数並べられます
- 新しい `mount` は**ファイルを指定すると自動で loop を使ってくれる**ことがありますが、**明示するのが確実**です
- 読むだけなら `-o loop,ro` にすると、うっかり書き換える事故を防げます

```bash
$ sudo mount -o loop,ro initrd.img /mnt/ram          # 読み取り専用でマウントする
$ losetup -a                                         # 使用中のループバックデバイスを一覧する
```

---

### 展開せずに中身を一覧する

「ファイルが入っているか確認したいだけ」なら、展開せずに一覧できます。

```bash
$ lsinitramfs /boot/initrd.img-$(uname -r)           # Debian系：中身を一覧する
$ lsinitrd /boot/initramfs-$(uname -r).img           # RHEL系：中身を一覧する
$ zcat /boot/initrd.img-$(uname -r) | cpio -t        # 汎用：cpio の一覧モードで見る
```

| コマンド | ディストリ |
|:--|:--|
| **`lsinitramfs`** | Debian / Ubuntu |
| **`lsinitrd`** | RHEL / CentOS / Rocky / Fedora |
| **`cpio -t`** | どこでも使える |

```bash
$ lsinitrd /boot/initramfs-$(uname -r).img | grep xfs   # 特定のドライバが入っているか探す
```

---

## cpio のよく使うオプション

`cpio` は「ファイルをまとめる／取り出す」コマンドです（`tar` の仲間）。
**まず 3 つのモードのどれかを必ず指定します。**

### 3 つのモード

| モード | 指定 | 読み方 | 何をするか |
|:--|:--|:--|:--|
| **コピーアウト** | **`-o`** | copy-**out** | **アーカイブを作る**。標準入力からファイル名の一覧を読み、標準出力へアーカイブを書く |
| **コピーイン** | **`-i`** | copy-**in** | **アーカイブから取り出す**。標準入力からアーカイブを読む |
| **パススルー** | **`-p`** | pass-through | アーカイブを作らずに、**ディレクトリ間で直接コピーする** |

> **`-i` が「展開」、`-o` が「作成」です。**
> 「アーカイブ」を基準に考えると迷いません。
>
> ```text
>   -o （copy-out）   ファイル ──▶ アーカイブ    アーカイブを作る
>   -i （copy-in）    ファイル ◀── アーカイブ    アーカイブから取り出す
> ```
>
> **`tar` の `-c`（作成）が `cpio` の `-o`、`tar` の `-x`（展開）が `cpio` の `-i`** に対応します。

### 組み合わせるオプション

| オプション | 意味 | 補足 |
|:--|:--|:--|
| **`-d`** / `--make-directories` | **必要なディレクトリを作りながら展開する** | **これが無いとサブディレクトリのファイルが展開されない**。`-i` とほぼセット |
| **`-m`** / `--preserve-modification-time` | **更新日時を元のまま保つ** | 展開したものを比較したいとき |
| **`-v`** / `--verbose` | 処理したファイル名を表示する | 進捗確認 |
| **`-t`** / `--list` | **中身の一覧だけ表示**して、展開はしない | 中身確認に |
| **`-u`** / `--unconditional` | 既存のファイルを**無条件に上書きする** | 既定では新しいファイルを上書きしない |
| **`-F ファイル`** / `--file` | **標準入力の代わりにファイルを読む** | `< ファイル` の代わり |
| **`-H 形式`** / `--format` | アーカイブ形式を指定する | initramfs は **`newc`** 形式 |
| **`--no-absolute-filenames`** | 先頭の `/` を外して**相対パスで展開する** | システムを壊さないための安全策 |
| **`--null`** | ファイル名の区切りを改行ではなく `\0` にする | `find -print0` と組み合わせ、空白入りのファイル名に対応する |

**例文**

```bash
$ cpio -id < ../initrd.img                           # 展開する（ディレクトリも作る）
$ cpio -idmv < ../initrd.img                         # 展開しつつ日時を保ち、進捗を表示する
$ cpio -t < ../initrd.img                            # 中身の一覧だけ見る
$ cpio -i -F ../initrd.img                           # < を使わずファイルを指定して展開する
$ find . | cpio -o -H newc > ../new-initrd.img       # 現在地以下を newc 形式でアーカイブにする
$ find . | cpio -o -H newc | gzip -9 > ../new.img.gz # アーカイブして gzip 圧縮する
```

**補足**

- `find .` … カレントディレクトリ以下のすべてのパスを 1 行ずつ出力する。`cpio -o` はこの一覧を読んでアーカイブを作ります
- `-H newc` … initramfs で使われる形式（SVR4 portable format）。**この指定を忘れるとカーネルが読めません**
- 展開した中身を直して作り直したときは、**必ず元のファイルのバックアップを取ってから**置き換えてください

---

## gunzip と zcat の使い分け

初期RAMディスクは gzip で圧縮されているので、先に解く必要があります。
似たコマンドが並ぶので整理します。

| コマンド | 動作 | 元のファイル |
|:--|:--|:--|
| **`gunzip ファイル.gz`** | 展開して `ファイル` を作る | **消える** |
| **`gunzip -c ファイル.gz`** | 展開した内容を**標準出力へ流す** | **残る** |
| **`zcat ファイル.gz`** | `gunzip -c` と同じ | **残る** |
| **`gzip -d ファイル.gz`** | `gunzip` と同じ（decompress） | **消える** |
| **`gzip -9 ファイル`** | 最高圧縮率で圧縮する | 消える（`.gz` になる） |

**例文**

```bash
$ gunzip initrd.img.gz                               # 展開する（元の .gz は消える）
$ gunzip -c initrd.img.gz > initrd.img               # 元を残したまま展開する
$ zcat /boot/initrd.img-$(uname -r) | cpio -t        # 元に触らず中身を一覧する
```

**補足**

- **`/boot` の実物を直接 `gunzip` しないでください。**起動できなくなります。必ずコピーしてから作業します

```bash
$ cp /boot/initrd.img-$(uname -r) ~/work.img.gz      # 作業用にコピーしてから触る
```

---

## 結果画面の見方

### 展開した中身の見方

initramfs を展開すると、**小さな Linux 一式**が出てきます。

```bash
$ ls work/                                           # 展開した中身を確認する
bin  conf  cryptroot  etc  init  lib  run  sbin  scripts  usr  var
```

| ディレクトリ / ファイル | 中身 | どこを見るか |
|:--|:--|:--|
| **`init`** | **最初に実行されるスクリプト**（initramfs の場合） | 起動処理そのもの。ここから追う |
| **`linuxrc`** | 最初に実行されるスクリプト（**initrd の場合**） | 古い方式でのみ存在する |
| **`bin/` `sbin/`** | 最小限のコマンド（`sh`、`mount`、`modprobe` など） | **`busybox` へのリンク**になっていることが多い |
| **`lib/modules/`** | **取り込まれたカーネルモジュール（`.ko`）** | **必要なドライバが入っているかを確認する最重要ポイント** |
| **`etc/`** | 設定ファイル（`fstab`、`modprobe.d` など） | ルートデバイスの指定を確認する |
| **`scripts/`** | 起動段階ごとのスクリプト（Debian 系） | `local`、`nfs` など、ルートの種類ごとの処理 |
| **`conf/`** | 設定（Debian 系）。`conf/initramfs.conf` など | 圧縮方式や MODULES の設定 |
| **`cryptroot/`** | 暗号化ルートの情報 | LUKS を使っているとき |
| **`usr/` `var/` `run/`** | 補助的なディレクトリ | 通常は中身が少ない |

**確認の例**

```bash
$ ls work/lib/modules/*/kernel/drivers/scsi/         # ストレージのドライバが入っているか見る
$ cat work/etc/fstab                                 # 一時ルートの fstab を確認する
$ head -20 work/init                                 # 最初に走るスクリプトの冒頭を読む
```

---

### file コマンドで正体を判定する

| 実行 | 出力例 | 判定 |
|:--|:--|:--|
| `file initrd.img.gz` | `gzip compressed data, ...` | **まだ圧縮されている** |
| `file initrd.img`（展開後） | `ASCII cpio archive (SVR4 with no CRC)` | **initramfs**。`cpio -id` で開く |
| `file initrd.img`（展開後） | `Linux rev 1.0 ext2 filesystem data` | **initrd**。`mount -o loop` で開く |
| `file /boot/vmlinuz-…` | `Linux kernel x86 boot executable bzImage` | カーネル本体 |

```bash
$ file /boot/*                                       # /boot のファイルの種類を一覧で判定する
```

---

## よく使う確認コマンドまとめ

| やりたいこと | コマンド |
|:--|:--|
| **今のカーネルのバージョンを知る** | `uname -r` |
| **/boot に何があるか見る** | `ls -lh /boot/` |
| **中身の一覧を見る（Debian系）** | `lsinitramfs /boot/initrd.img-$(uname -r)` |
| **中身の一覧を見る（RHEL系）** | `lsinitrd /boot/initramfs-$(uname -r).img` |
| **中身の一覧を見る（汎用）** | `zcat イメージ \| cpio -t` |
| **特定のドライバが入っているか** | `lsinitrd イメージ \| grep ドライバ名` |
| **作り直す（Debian系）** | `sudo update-initramfs -u -k all` |
| **作り直す（RHEL系）** | `sudo dracut -f --regenerate-all` |
| **正体を判定する** | `file イメージ` |
| **ループバックの使用状況** | `losetup -a` |

---

## 参考リンク

- [man 8 mkinitramfs（Debian）](https://manpages.debian.org/bookworm/initramfs-tools-core/mkinitramfs.8.en.html)
- [man 8 update-initramfs（Debian）](https://manpages.debian.org/bookworm/initramfs-tools-core/update-initramfs.8.en.html)
- [man 8 dracut](https://man7.org/linux/man-pages/man8/dracut.8.html)
- [GNU cpio マニュアル](https://www.gnu.org/software/cpio/manual/cpio.html)
- [man 8 mount](https://man7.org/linux/man-pages/man8/mount.8.html)
- [man 8 losetup](https://man7.org/linux/man-pages/man8/losetup.8.html)
- [Linux kernel documentation — ramfs, rootfs and initramfs](https://www.kernel.org/doc/html/latest/filesystems/ramfs-rootfs-initramfs.html)
- [Red Hat — dracut でのブートイメージの再作成](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_monitoring_and_updating_the_kernel/)

---

[← 全体の目次にもどる](../README.md)
