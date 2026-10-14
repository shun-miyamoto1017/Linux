# ソフトウェアRAIDの管理_mdadm

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — ファイルシステムの管理 |
| **業務での使いどころ** | **ディスクが 1 本壊れた深夜に、手順を思い出せるかどうか。**`-f` → `-r` → `-a` の 3 手を体に入れておけば、サービスを止めずに交換できる |

> **このノートは `mdadm` で RAID を作り、壊れたディスクを交換するところまで**です。
> **RAID レベルの仕組みと容量計算**は [RAIDの基礎とレベル](./RAIDの基礎とレベル.md)、
> **監視・定期チェック・組み直し**は [RAIDの監視と保守](./RAIDの監視と保守.md)、
> **パーティションを作る `fdisk`** は [ディスクを追加する手順](./ディスクを追加する手順.md)、
> **できた RAID にファイルシステムを作る**のも同じノートにあります。

---

## 目次

- [全体の流れ](#全体の流れ)
- [事前準備 パーティションタイプを fd にする](#事前準備-パーティションタイプを-fd-にする)
- [mdadm のモード](#mdadm-のモード)
- [Create モード 作る](#create-モード-作る)
  - [作る前に知っておく3つのこと](#作る前に知っておく3つのこと)
  - [よく使うオプション](#よく使うオプション)
  - [RAID10とRAID5のレイアウト指定](#raid10とraid5のレイアウト指定)
  - [書き方の間違い探し](#書き方の間違い探し)
- [Manage モード 構成デバイスを操作する](#manage-モード-構成デバイスを操作する)
- [Misc モード 調べる止める](#misc-モード-調べる止める)
- [proc-mdstat を読む](#proc-mdstat-を読む)
  - [記号の意味](#記号の意味)
  - [正常なときと異常なとき](#正常なときと異常なとき)
  - [再構築中の見え方](#再構築中の見え方)
- [障害ディスクを交換する3手](#障害ディスクを交換する3手)
- [設定ファイル](#設定ファイル)
- [存在しないコマンドとファイルの整理](#存在しないコマンドとファイルの整理)
- [参考リンク](#参考リンク)

---

## 全体の流れ

```text
  ① fdisk でパーティションタイプを fd にする（任意。印として付ける）
        ▼
  ② mdadm -C で RAID デバイス /dev/md0 を作る
        ▼
  ③ cat /proc/mdstat で構築が終わるのを待つ
        ▼
  ④ mkfs でファイルシステムを作る（/dev/md0 に対して）
        ▼
  ⑤ mount する／/etc/fstab に書く
        ▼
  ⑥ mdadm --detail --scan | sudo tee -a /etc/mdadm.conf で構成を保存する
        ▼
  ⑦ 監視と定期チェックを有効にする（→ RAIDの監視と保守）
```

**`/dev/md0` は「1 台のディスク」として扱えます。**
**`mkfs` も `mount` も `fstab` も、普通のパーティションと同じ**です。

```bash
$ sudo mkfs -t ext4 /dev/md0           # RAID デバイスにファイルシステムを作る
$ sudo mount /dev/md0 /data            # 普通にマウントできる
```

---

## 事前準備 パーティションタイプを fd にする

**試験では「あらかじめ `fdisk` でパーティションタイプを `0xfd` に設定する」**と問われます。
**ただし実際には、これは必須ではありません。**

`man 8 mdadm` によると、**カーネルの自動検出が働くのは
「MS-DOS（MBR）のパーティションタイプが `FD`」かつ「v0.90 メタデータ」の場合だけ**で、
**しかも新規構築では非推奨**とされています。

| 環境 | `fd` が必要か |
|:--|:--|
| **MBR ＋ v0.90 メタデータ**（古い構成） | **自動検出のために意味がある** |
| **v1.2 メタデータ**（`mdadm` の現在の既定） | **不要**。`mdadm.conf` と initramfs で組み立てる |
| **GPT** | **`fd` という番号が無い** |
| **ディスク丸ごと使う**（クラウドでは普通） | **パーティション自体が無い** |

**それでも `fd` を付けておく意味はあります。**
**`fdisk -l` を見た次の担当者が「このディスクは RAID 用だ」と分かる**からです。
**LVM の `8e` と同じく、印として付けておく**のが作法です。

**先頭の `0x` は 16 進数表記であることを表しています。**

```bash
$ sudo fdisk /dev/sdb                  # 対話モードに入る
コマンド (m でヘルプ): t               # パーティションタイプの変更
パーティション番号 (1-4): 1
16進数コード (L コマンドでコードリスト表示): fd    # パーティションタイプの指定
パーティションのシステムタイプを 1 から fd (Linux raid 自動検出) に変更しました

コマンド (m でヘルプ): w               # 設定の保存
```

**実機で確かめると、タイプ欄が `fd Linux raid autodetect` になります。**

```bash
$ fdisk -l /dev/sdb                    # 変更されたか確認する
Device     Boot Start   End Sectors Size Id Type
/dev/sdb1        2048 16383   14336   7M fd Linux raid autodetect
```

| 指定 | 正誤 |
|:--|:-:|
| **`0xfd`** | **○**（`fd` と入力する） |
| `0xpc` / `0xra` / `0xsc` / `0xrd` | **✕**（**存在しないパーティションタイプ**） |
| `0x82` | ✕（**スワップ**） |
| `0x83` | ✕（**Linux の通常のパーティション**） |
| `0x8e` | ✕（**Linux LVM**） |

**`fd` は「Linux raid autodetect」**です。
**`8e`（LVM）と取り違えない**よう、一緒に覚えます。

`fdisk` の操作そのものは
[ディスクを追加する手順](./ディスクを追加する手順.md) にあります。

> **GPT では `fd` という番号は使いません。**
> `parted` なら `set N raid on`、`sgdisk` なら型 `FD00` を指定します。
> **試験で問われるのは MBR の `0xfd`** です。

---

## mdadm のモード

**`mdadm` コマンドは多くの機能を持っているためにモードが複数あり、機能が分類されています。**

**`man 8 mdadm` が挙げるモードは 9 つ**（Assemble / Build / Create / Follow or Monitor /
Grow / Incremental Assembly / Manage / Misc / Auto-detect）ですが、
**試験と実務で使うのは次の 6 つ**です。

| モード | 何をするか | 入り方 |
|:--|:--|:--|
| **Create** | **RAID を新規に作成する** | **`-C` または `--create`** |
| **Manage** | **RAID を構成するデバイスの追加・削除などを行う** | **`--manage`（省略可）** |
| **Misc** | **RAID の状態表示など雑多な機能** | **`--misc`（省略可）** |
| Assemble | 作成済みのアレイを再編成する（→ [RAIDの監視と保守](./RAIDの監視と保守.md)） | `-A` または `--assemble` |
| Monitor | 変化を監視して通知する（→ [RAIDの監視と保守](./RAIDの監視と保守.md)） | `-F` または `--follow` |
| Grow | サイズや構成を変更する | `-G` または `--grow` |

> **このノートのオプション表とヘルプの引用は mdadm 4.3 の `--help` を実機で確認したもの**です。
> ただし**作業環境のカーネルに md ドライバが無い**ため（`/proc/mdstat` が存在しない）、
> **アレイを実際に作って動かすところまでは確認できていません。**
> **`/proc/mdstat` の出力例は Ping-t の解説にあるもの**を使っています。
> **`man` と Red Hat / SUSE の公式ドキュメントからの引用には、その都度出典を併記**しています。
> **`mdadm: invalid raid level: 3` などのエラーメッセージは実測**です。

**Manage と Misc は省略できます**（mdadm 4.3 の `--help` で確認）。

> `mdadm --manage --help`:
> **The --manage option is not needed and is assumed if the first argument is a device name or a management option.**
> （`--manage` は不要で、最初の引数がデバイス名か管理用オプションなら自動的にそう解釈される）

```bash
$ sudo mdadm --manage /dev/md0 -a /dev/sdd1    # 明示的に書いてもよい
$ sudo mdadm /dev/md0 -a /dev/sdd1             # 省略しても同じ（これが普通）
```

**「はじめのオプションとして Manage モード用オプション（`-a` / `-r` / `-f`）を指定した場合は、
`--manage` が指定されていなくとも自動的に Manage モードになります。」**

**Misc も同様**です。
**モードを指定するオプション（`-C` / `--create` / `--manage`）や
Manage モードのオプション（`-a` / `-r` / `-f`）以外のオプションがはじめに見つかると、
`mdadm` は自動的に Misc モードとなります。**

**オプションをモード別に整理して覚える**

```text
  Create モード  -C   -l（level） -n（raid-devices） -x（spare-devices）
  Manage モード  -a（add）  -r（remove）  -f（fail）
  Misc   モード  -Q（query） -D（detail）  -S（stop）
```

**この 3 行を書けるようにしておけば、この分野の設問はほぼ落としません。**

---

## Create モード 作る

**Create モードでは RAID を新規に作成することができます。**

```text
mdadm -C|--create 作成先 [オプション] デバイス1 デバイス2 ...
```

**「作成先」には RAID を作成する先となるデバイスファイルを指定します。**
**通常は MD デバイスと呼ばれる `/dev/md0`, `/dev/md1` 等を使います。**

| デバイス名 | RAID デバイスとして正しいか |
|:--|:-:|
| **`/dev/md0`** / **`/dev/md1`** | **○**（**MD ＝ Multiple Device**） |
| `/dev/sda1` / `/dev/hda1` | ✕（**RAID を構築するために使用されるデバイス**。作成先ではない） |
| `/dev/raid1` / `/dev/rd1` | ✕（**存在しないデバイスファイル**） |

**「デバイス1 デバイス2 ...」の部分には RAID を構築するために使うデバイス（`/dev/sda1` など）を指定します。**
**スペースで区切って必要なだけ指定できます。**

### 作る前に知っておく3つのこと

**`mdadm --create --help` に書かれている、知らないと驚く挙動**です（mdadm 4.3 で確認）。

**① サイズの違うディスクを混ぜるとどうなるか**

> "If no --size is given, the apparent size of the smallest drive given is used for
> raid level 1 and greater, and the full device is used for other levels."

| レベル | サイズが違うディスクを混ぜた場合 |
|:--|:--|
| **RAID1 / 4 / 5 / 6 / 10** | **いちばん小さいディスクに合わせられる**。大きいディスクの余りは使われない |
| **RAID0 / linear** | **各ディスクの全容量が使われる** |

```text
  500GB + 500GB + 1TB で RAID5 を組むと
      → 500GB × (3-1) = 1TB しか使えない（1TB のうち 500GB が無駄）
```

**だから RAID は同容量のディスクで組みます。**
**`--size`（`-z`）で各ディスクから使う容量を明示的に揃える**こともできます。

**② サイズ差が 1% を超えると確認を求められる**

> "They are also checked to see if the variance in device size exceeds 1%.
> If any discrepancy is found, the user will be prompted for confirmation before the array is created."

**既存の RAID スーパーブロックやファイルシステムが残っていても同じく確認されます。**
**`--run`（`-R`）を付けると確認なしで進みます**が、**自動化スクリプトで安易に付けると
「実は使っていたディスク」を潰します。**

**③ `missing` でわざと欠けた状態で作れる**

> "In order to create an array with some devices missing, use the special word 'missing'
> in place of the relevant device name."

```bash
$ sudo mdadm -C /dev/md0 -l1 -n2 /dev/sdb1 missing   # 1台だけでRAID1を作る
$ sudo mdadm /dev/md0 -a /dev/sdc1                   # 後から2台目を足して同期させる
```

**既存ディスクのデータを RAID1 へ移す**ときに使う定石です。

```text
  ① 新しいディスク1本 ＋ missing で、縮退状態の RAID1 を作る
  ② 既存ディスクから、その RAID1 へデータをコピーする
  ③ コピーが正しいことを確認する        ★ここまでは元のディスクが無傷
  ④ 既存ディスクを RAID1 に -a で足す（ここで元のディスクが上書きされる）
```

> **③ までは元のディスクに手を付けていません。**
> **失敗したら元のディスクから起動し直せる**のがこの手順の利点です。
> **④ を打った瞬間に元のディスクは上書きされる**ので、そこだけ引き返せません。
>
> **新しいディスクは、元のパーティション以上の大きさが必要**です。
> **`mdadm` のメタデータが先頭（または末尾）を使うため、
> 使える容量は元より少し小さくなります。**

---

### よく使うオプション

| オプション | 説明 |
|:--|:--|
| **`-l`、`--level=`** | **RAID レベルを指定** |
| **`-n`、`--raid-devices=`** | **利用するデバイス数を指定** |
| **`-x`、`--spare-devices=`** | **予備デバイス数を指定** |
| `-c`、`--chunk=` | チャンクサイズ（KiB） |
| `-N`、`--name=` | アレイに名前を付ける |

**mdadm 4.3 の `--create --help` を実機で確認した抜粋**

```text
  --level=           -l : raid level: 0,1,4,5,6,10,linear,multipath and synonyms
  --raid-devices=    -n : number of active devices in array
  --spare-devices=   -x : number of spare (eXtra) devices in initial array
```

**`-x` の `x` は eXtra（予備）**——`--help` にそう書かれています。
**`-n` は Number（構成数）、`-l` は Level**と結びつけると取り違えません。

**予備デバイスとは**

**予備デバイスというのは、RAID を構築しているデバイスに障害が発生した場合に備えて、
今すぐ構築に使うことはせずに予備として取っておくデバイス**です。

**「デバイス1 デバイス2 ...」の部分で指定するデバイスの数と、`-n` `-x` オプションで指定する数の和は
一致していなければなりません。**
**例えば `-n 2 -x 1` と指定したならば、デバイスは 2 + 1 = 3 つ指定する**といった具合です。

```bash
$ sudo mdadm -C /dev/md0 -l1 -n2 -x1 /dev/sda1 /dev/sdb1 /dev/sdc1   # 2台でRAID1、予備1台
```

> **`-n2` のようにオプションとその値となる数字の間にスペースが入っていませんが、
> コマンドによってはこのようにオプション名とその値を続けて書いて、
> 合わせてひとつのオプションのように指定できるものがあるのです。**
> **もちろん通常のスペースを空ける指定方法でも問題ありません。**

**同じ意味になる書き方**

| 短い書き方 | 長い書き方 |
|:--|:--|
| **`-l 5`** / **`-l5`** | **`--level=5`** |
| **`-n 3`** | **`--raid-devices=3`** |
| **`-x 1`** | **`--spare-devices=1`** |
| **`-C`** | **`--create`** |

**長いオプションはハイフンを 2 つ重ねます。**
**`-raid-devices=3` のようにハイフンが 1 つだと存在しないオプション**になります。
**この例に限らず、Linux のオプションでは一般的に、長い名前になる場合はハイフンを 2 つ伴うことが多い**です。

### RAID10とRAID5のレイアウト指定

**`mdadm --create --help` にあるオプション**です（mdadm 4.3 で確認）。

```text
  --chunk=           -c : chunk size in kibibytes
  --parity=          -p : raid5/6 parity algorithm: {left,right}-{,a}symmetric
  --layout=             : same as --parity, for RAID10: [fno]NN
```

**RAID10 の `--layout`**

| 指定 | 意味 | 用途 |
|:--|:--|:--|
| **`n2`**（**既定**） | **near** — 複製を別デバイスの近い位置に置く | **一般的な用途** |
| **`f2`** | **far** — 複製を大きく離れた位置に置く | **読み込みが多い用途**（読み取り専用ファイルサーバなど） |
| **`o2`** | **offset** — ストライプを複製し、1 デバイス分ずらす | near と far の中間 |

`man 8 mdadm` の記述です。

> - "'n' signals 'near' copies. Multiple copies of one data block are at similar offsets in different devices."
> - "'f' signals 'far' copies (multiple copies have very different offsets)."
> - "'o' signals 'offset' copies."

**数字は複製の数**です。`n2` なら 2 重、`n3` なら 3 重になります。

```bash
$ sudo mdadm -C /dev/md0 -l10 -n4 --layout=f2 /dev/sd{b,c,d,e}1   # far レイアウトで組む
```

> **`mdadm` の `raid10` は、古典的な「RAID1+0」とは別の独自実装**です。
> **4 台でなくても、奇数台でも組めます**（`-n3 --layout=n2` など）。
> **far レイアウトが読み込みに強い理由は SUSE の公式ドキュメント**に
> **"best used for read-intensive operations such as for read-only file servers."** とあります。
> **既定が `n2` である点も SUSE の公式ドキュメントで確認**しました
> （"Near is the default layout for RAID 10."）。

**チャンクサイズ**

**既定は 512 KiB** です（`man 8 mdadm`: "The default when creating an array is 512KB."）。
**RAID1 には関係ありません**（区切る必要がないため）。
詳しくは [RAIDの基礎とレベル](./RAIDの基礎とレベル.md) の「チャンクサイズ」を参照してください。

---

### 書き方の間違い探し

**「2 台のディスクで RAID1 を構築する」正しいコマンド**

```bash
$ sudo mdadm -C /dev/md0 -l 1 -n 2 /dev/sda1 /dev/sdb1   # 2台でRAID1を作る
```

| 書き方 | 成立するか | どこが違うか |
|:--|:-:|:--|
| **`mdadm -C /dev/md0 -l 1 -n 2 /dev/sda1 /dev/sdb1`** | **○** | **`-l 1` で RAID1、`-n 2` で 2 台。デバイスも 2 つ** |
| `mdadm -C /dev/md0 -l 2 -n 1 /dev/sda1 /dev/sdb1` | ✕ | **値が逆**。しかも **`mdadm` は RAID2 に対応していない**ので `mdadm: invalid raid level: 2` で弾かれる（実測） |
| `mdadm --create /dev/md0 -l 1 -x 2 /dev/sda1 /dev/sdb1` | ✕ | **`-x` は予備デバイス数**。構成デバイス数の指定ではない |
| `mdadm --create /dev/md0 -l 2 -x 1 /dev/sda1 /dev/sdb1` | ✕ | **`-x` が誤りのうえ、数字も逆** |
| `mdadm create /dev/md0 --level=1 --raid-devices=2 /dev/sda1 /dev/sdb1` | ✕ | **`create` と書いている**。Create モードは **`-C` か `--create`** |

**`--create` と `-C` はどちらでも構いません。**
**`create`（ハイフン無し）だけが誤り**です。

**`-l` / `-n` / `-x` の取り違えが、この分野の誤答のほとんど**です。

| 指定 | 何の指定か | 取り違えやすい相手 |
|:--|:--|:--|
| **`-l5`** / **`--level=5`** | **RAID レベル**（Level） | `-n5`（台数）、`-x5`（予備数） |
| **`-n3`** / **`--raid-devices=3`** | **構成デバイス数**（Number） | `-l3`（**`mdadm: invalid raid level: 3`** で弾かれる。実測） |
| **`-x1`** / **`--spare-devices=1`** | **予備デバイス数**（eXtra） | `-n1`（構成 1 台になる） |

```text
  「RAID5 を構成3台＋予備1台で作る」 → -l 5 -n 3 -x 1
                                        │    │    └ 予備
                                        │    └───── 構成台数
                                        └────────── レベル
```

> **長いオプションはハイフン 2 つ**です。`-raid-devices=3` のようにハイフン 1 つは存在しません。
> **`--lv 5` というオプションもありません。**

---

## Manage モード 構成デバイスを操作する

**Manage モードでは RAID を構成するデバイスの追加・削除などを行うことができます。**

```text
mdadm [--manage] RAIDデバイス [オプション] デバイス1 デバイス2 ...
```

| オプション | 説明 |
|:--|:--|
| **`-a`、`--add`** | **構成デバイスを追加** |
| **`-r`、`--remove`** | **構成デバイスを削除** |
| **`-f`、`--fail`** | **構成デバイスに不良マーク付与** |
| `--re-add` | 一度外したデバイスを戻す |
| `--replace` | 予備と入れ替える（新しい方式） |
| `-S`、`--stop` | アレイを停止する（Misc でも使える） |

**これらのオプションはいずれかを指定して使います。**
**「デバイス1 デバイス2 ...」部に指定したデバイスを追加・削除・不良扱いすることができます。**

```bash
$ sudo mdadm /dev/md0 -f /dev/sdb1     # /dev/sdb1 に不良マークを付ける
$ sudo mdadm /dev/md0 -r /dev/sdb1     # 構成から取り外す
$ sudo mdadm /dev/md0 -a /dev/sdd1     # 新しいデバイスを追加する
```

**覚え方**

```text
  -a  add     足す
  -r  remove  外す
  -f  fail    壊れた印を付ける
```

---

## Misc モード 調べる止める

**Misc モードでは RAID に関係したその他の様々な機能を使うことができます。**

| オプション | 説明 |
|:--|:--|
| **`-Q`、`--query`** | **RAID の状態を表示** |
| **`-D`、`--detail`** | **RAID の詳細情報を表示** |
| **`-S`、`--stop`** | **RAID を停止** |
| `-E`、`--examine` | 構成デバイス側のスーパーブロックを見る（→ [RAIDの監視と保守](./RAIDの監視と保守.md)） |
| `--zero-superblock` | デバイスから RAID の痕跡を消す（→ [RAIDの監視と保守](./RAIDの監視と保守.md)） |
| `-t`、`--test` | 終了ステータスで状態を返す（0 正常 / 1 縮退 / 2 全滅） |

```bash
$ sudo mdadm -D /dev/md0               # 詳細を見る（レベル、台数、各デバイスの状態）
$ sudo mdadm -Q /dev/md0               # ざっくり見る
$ sudo mdadm -S /dev/md0               # 停止する
```

**停止された RAID デバイスは、再構成・再スタートされない限り、
マウントを行うなどして利用することができません。**

**`umount` と `-S` は別物**

| コマンド | 何が起きるか |
|:--|:--|
| **`umount /dev/md0`** | **ファイルシステムを外すだけ**。**デバイス自体は動いたまま** |
| **`mdadm -S /dev/md0`** | **RAID デバイスそのものを停止**する |

**「RAID デバイスを停止させる」と問われたら `mdadm -S`** です。
**`umount` はアンマウントであって停止ではありません。**

```bash
$ sudo umount /data                    # ① 先にアンマウントしてから
$ sudo mdadm -S /dev/md0               # ② 停止する
```

**動作状態を調べる 3 つの方法**

| 方法 | 得られるもの |
|:--|:--|
| **`cat /proc/mdstat`** | **全アレイの概要を一目で**。いちばん基本 |
| **`mdadm -D /dev/md0`** | **1 つのアレイの詳細**（各デバイスの状態、UUID、実効容量） |
| **`mdadm -Q /dev/md0`** | **ざっくりした状態** |

**`mdadm -C` は作成、`mdadm -S` は停止**なので、**状態を調べるためには使えません。**
**`mdstat` というコマンドは存在しません**（`/proc/mdstat` という**ファイル**なら存在します）。

---

## proc-mdstat を読む

**`/proc/mdstat` はシステム上の RAID アレイの状態を保持している仮想ファイル**です。
**`cat` コマンドなどを使ってこのファイルの内容を参照することで、
現在の RAID の動作状態をチェックすることができます。**

```bash
$ cat /proc/mdstat                     # RAID の状態をざっと見る
Personalities : [raid1]
md0 : active raid1 sdb1[1]
      244195904 blocks [2/1] [_U]

unused devices: <none>
```

### 記号の意味

| 行・記号 | 意味 |
|:--|:--|
| **`Personalities`** | **システム上で認識している RAID レベルの一覧**。複数あれば `[raid1] [raid5]` のように並ぶ |
| **`md0`** | **RAID デバイス名** |
| **`active`** | **稼働状態**。停止していると **`inactive`** |
| **`raid1`** | **このデバイスが構成されている RAID レベル** |
| **`sdb1[1]`** | **構成デバイスと、その番号** |
| **`(S)`** | **スペア（予備デバイス）** |
| **`[2/1]`** | **[構成デバイスの数 / 稼働中デバイスの数]** |
| **`[_U]`** | **`U` が稼働中（UP）、`_` は構成から外れている** |
| **`recovery`** | **構築中または修復中** |
| `unused devices` | どのアレイにも属していないデバイス |

**`[2/1]` と `[_U]` は同じことを 2 つの書き方で言っています。**

```text
  [2/1]   2台のうち 1台だけ 稼働中
  [_U]    1台目が脱落（_）、2台目は稼働（U）
             ↑ 位置で どのデバイスか が分かる
```

### 正常なときと異常なとき

**正常**

```text
md0 : active raid1 sdc1[1] sdb1[0]
      244195904 blocks [2/2] [UU]
                       └─ 2/2    └─ UU   ← どちらも「全部動いている」
```

**異常（1 台脱落）**

```text
md0 : active raid1 sdb1[1]
      244195904 blocks [2/1] [_U]
                       └─ 2/1    └─ _U   ← 1台しか動いていない
```

**この出力から読み取れること**

| 読み取り | 正誤 | 根拠 |
|:--|:-:|:--|
| **RAID1 として構成されている** | **○** | **`Personalities : [raid1]` と 3 行目の `raid1`** |
| **md0 は稼働状態である** | **○** | **`active` とある**（停止なら `inactive`） |
| **動作している RAID アレイは 1 つである** | **○** | **`md0` の行しかない**。複数あれば同じ形で並ぶ |
| **構成デバイスは正常に動作している** | **✕** | **`[2/1]` `[_U]` は 2 台中 1 台しか稼働していない**という意味 |

**判断基準は必ず 4 行目（`[x/y]` と `[UU]` の行）**です。
**`active` は「アレイが動いている」であって「全デバイスが健全」ではありません。**
**ここを混同すると、縮退運転を正常だと見誤ります。**

### 再構築中の見え方

```text
# cat /proc/mdstat
Personalities : [raid6] [raid5] [raid4]
md0 : active raid5 sdd1[4] sde1[3](S) sdc1[1] sdb1[0]
      10465280 blocks super 1.2 level 5, 512k chunk, algorithm 2 [3/2] [UU_]
      [===========>.........]  recovery = 59.2% (3101016/5232640) finish=0.6min speed=55375K/sec
```

| 見えているもの | 意味 |
|:--|:--|
| **`sde1[3](S)`** | **`sde1` は予備（スペア）** |
| **`[3/2]`** | **構成 3 台中 2 台が稼働** |
| **`[UU_]`** | **3 台目が構成から外れている** |
| **`recovery = 59.2%`** | **修復中**。進捗と残り時間も出る |
| `finish=0.6min` | あと 0.6 分で終わる見込み |

**終わると `[3/3] [UUU]` になります。**

```text
md0 : active raid5 sdd1[4] sde1[3](S) sdc1[1] sdb1[0]
      10465280 blocks super 1.2 level 5, 512k chunk, algorithm 2 [3/3] [UUU]
```

**`recovery` が出ているときの正しい判断**

| 判断 | 正誤 | 理由 |
|:--|:-:|:--|
| **現在修復中のため、修復を待ってステータスの確認と修復後の対応が必要である** | **○** | **これが正しい対応** |
| `[UU_]` は 1 台が稼働していないので、**物理交換を行わない限り修復不能**である | ✕ | **前半は正しいが、現在修復中**なので必ず物理交換が要るとは言い切れない |
| **`(S)` と表示されたデバイスが Stop を表し、RAID の役を果たさなくなっている** | ✕ | **`(S)` はスペア**。Stop ではない |
| `[3/2]` とあるのは **RAID3 から 2 にダウンした**ためなので、再構築が必要 | ✕ | **`[構成デバイスの数 / 稼働中デバイスの数]`**。RAID レベルの話ではない |

> **`recovery` の表示は構築中や修復中に表示されます。**
> **稼働していたデバイスが壊れた場合に、予備のデバイスがある場合は、自動的に修復が試みられます。**

**だから予備デバイス（`-x`）を確保しておくと、深夜に叩き起こされずに済みます。**

---

## 障害ディスクを交換する3手

**障害が発生したなどの理由で構成ディスクを切り替えるには、`-f`、`-r`、`-a` の順に `mdadm` の機能を使います。**

```text
  ① -f  不良マークを付ける   （RAID コントローラに「これは故障」と教える）
        ▼
  ② -r  構成から取り外す     （不良マークが無いと外せない）
        ▼
  ③ -a  新しいデバイスを足す （ここから再構築が始まる）
```

**なぜこの順番なのか**

| 手順 | 理由 |
|:--|:--|
| **① `-f`** | **これによりカーネルの md ドライバが、そのデバイスは故障しているものとして適切に取り扱うようになる**（ハードウェアの RAID カードのことではありません） |
| **② `-r`** | **不良マークがついていない構成デバイスは取り除くことはできない**（必ず先に不良マークをつける必要がある） |
| **③ `-a`** | **RAID 構成デバイスとして代わりの新しいデバイスを追加する** |

**実例**

```bash
# 障害発生した /dev/sdb1 を /dev/sdd1 に交換する
$ sudo mdadm --manage /dev/md0 -f /dev/sdb1    # ① 不良マークを付ける
$ sudo mdadm --manage /dev/md0 -r /dev/sdb1    # ② 構成から取り外す
$ sudo mdadm /dev/md0 -a /dev/sdd1             # ③ 新しいデバイスを追加する
```

**最終行では `--manage` を指定していませんが、
はじめのオプションとして `-a` が指定されているので、自動的に Manage モードとなり、正しく動作します。**

**「最初に行うコマンド」と問われたら**

**交換手順の最初は `-f`（不良マーク）**です。

| 選択肢 | 正誤 |
|:--|:-:|
| **`mdadm /dev/md0 -f /dev/sdb1`** | **○** |
| **`mdadm /dev/md0 --fail /dev/sdb1`** | **○**（`-f` の長い書き方） |
| `mdadm /dev/md0 -r /dev/sdb1` | ✕（**2 番目**。いきなりは外せない） |
| `mdadm /dev/md0 --remove /dev/sdb1` | ✕（同上） |
| `mdadm /dev/md0 -a /dev/sdb1` | ✕（**3 番目**） |

**「与えるオプションを順に並べよ」と問われたら `-f, -r, -a`** です。

| 並び | 正誤 |
|:--|:-:|
| **`-f, -r, -a`** | **○** |
| `-C, -a, -r` | ✕（**`-C` は Create モード**。交換には使わない） |
| `-c, -f, -r` | ✕（**`-c` は設定ファイルの指定**。この場面では役に立たない） |
| `-c, -r, -a` | ✕（同上。`-f` も抜けている） |
| `-f, -a, -C` | ✕（`-C` が混ざっている） |
| `-f, -r, -C` | ✕（同上） |

**`-c`（小文字）と `-C`（大文字）は別物**です。
**さらに `-c` は、どのモードで使うかによって意味が変わります。**

```text
  -C  Create モードに入る（--create）              … 大文字は常にこれ

  -c  Create / Build / Grow モードでは  --chunk   （チャンクサイズ）
      それ以外のモードでは              --config  （設定ファイル）
```

> **交換作業（Manage モード）の文脈では `-c` は `--config`** です。
> **アレイを作る文脈では `-c` はチャンクサイズ**です。
> `man 8 mdadm` がそう定義しています。

**交換後の確認**

```bash
$ cat /proc/mdstat                     # recovery が走っているか見る
$ sudo mdadm -D /dev/md0               # 各デバイスの状態を確認する
```

**`[UUU]` に戻るまでは冗長性がありません。** 終わるまで見届けます。

---

## 設定ファイル

**RAID を管理・操作するコマンド（`mdadm`）の動作を設定することができるファイルは `/etc/mdadm.conf`** です。
**また環境によっては `/etc/mdadm/mdadm.conf` となっていることもあります。**

| ディストリビューション | 場所 |
|:--|:--|
| **RHEL 系** | **`/etc/mdadm.conf`** |
| **Debian / Ubuntu 系** | **`/etc/mdadm/mdadm.conf`**（実機で確認） |

```bash
$ grep -v '^#' /etc/mdadm/mdadm.conf | grep -v '^$'    # 有効な設定行だけを見る
HOMEHOST <system>
MAILADDR root
```

| 設定行 | 意味 |
|:--|:--|
| **`ARRAY`** | **アレイの定義**（UUID とデバイス名の対応） |
| **`MAILADDR`** | **障害時に通知するメールアドレス**（→ [RAIDの監視と保守](./RAIDの監視と保守.md)） |
| `DEVICE` | 走査するデバイスの範囲 |
| `HOMEHOST` | どのホストのアレイかを識別する名前 |

**現在の構成を書き出す**

```bash
$ sudo mdadm --detail --scan                        # 現在のアレイ定義を出力する
ARRAY /dev/md0 metadata=1.2 name=host:0 UUID=1a2b3c4d:...
$ sudo mdadm --detail --scan | sudo tee -a /etc/mdadm.conf   # 設定ファイルに追記する
```

**これをやっておかないと、再起動後にデバイス名が `/dev/md127` などに変わることがあります。**
**構築したら必ず書き出す**、が実務での定石です。

**まぎらわしいファイルの整理**

| 名前 | 実際は |
|:--|:--|
| **`/etc/mdadm.conf`** | **これが設定ファイル**（正解） |
| **`/proc/mdstat`** | **設定ファイルではない**。**RAID アレイの状態を保持している仮想ファイル** |
| `/proc/mdadm` | **存在しない**。そもそも `/proc` に設定ファイル類が置かれることはない |
| `/etc/mdstat.conf` | **存在しない** |

```text
  /etc/mdadm.conf   設定を 書く 場所   … こちらは /etc（設定ファイルの置き場）
  /proc/mdstat      状態を 読む 場所   … こちらは /proc（仮想ファイルの置き場）
```

**`/proc` と `/etc` の役割の違い**は
[FHSとディレクトリ構成](./FHSとディレクトリ構成.md) にあります。

---

## 存在しないコマンドとファイルの整理

| 見かける名前 | 実際は |
|:--|:--|
| **`mdctl`** | **存在しない**。RAID の操作は **`mdadm`** |
| **`mdremove`** | **存在しない** |
| **`mdstat`**（コマンドとして） | **存在しない**。**`/proc/mdstat` というファイル**なら存在する |
| **`/dev/raid1`** / **`/dev/rd1`** | **存在しないデバイスファイル**。RAID デバイスは **`/dev/md0`** |
| **`/proc/mdadm`** / **`/proc/raid`** / **`/proc/rdstat`** | **存在しない**。正しくは **`/proc/mdstat`** |
| `/etc/mdstat.conf` | **存在しない**。設定は **`/etc/mdadm.conf`** |

**`mdadm` はコマンド、`mdstat` は `/proc/mdstat` として存在するファイル**です。
**名前が似ていますが区別して覚えておきましょう。**

```text
  mdadm    コマンド        … 操作する
  mdstat   /proc の ファイル … 状態を読む
```

**RAID アレイを操作するコマンドは `mdadm` です。**
**`mdadm` には多数のモードがあり、RAID に関係した操作はほぼすべて `mdadm` のみで行えるようになっています。**

---

## 参考リンク

- [man 8 mdadm](https://man7.org/linux/man-pages/man8/mdadm.8.html)
- [man 5 mdadm.conf](https://man7.org/linux/man-pages/man5/mdadm.conf.5.html)
- [man 4 md](https://man7.org/linux/man-pages/man4/md.4.html)
- [Linux RAID wiki](https://raid.wiki.kernel.org/index.php/Linux_Raid)
