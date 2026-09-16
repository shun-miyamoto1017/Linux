# Btrfsとサブボリューム

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★☆☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — ファイルシステムの管理 |
| **業務での使いどころ** | **更新前に一瞬で戻せる状態を作る。**「パッケージ更新したら起動しなくなった」を、スナップショットからの復帰で数十秒に縮められる |

> **このノートは Btrfs の操作**です。
> **ファイルシステムの種類の一覧と選び方、`mkfs` での作成**は
> [ファイルシステムの種類と作成](./ファイルシステムの種類と作成.md)、
> **マウント**は [マウントとアンマウント](./マウントとアンマウント.md) にあります。

---

## 目次

- [まずこれだけ](#まずこれだけ)
- [Btrfs の特徴](#btrfs-の特徴)
  - [マルチデバイスへの対応](#マルチデバイスへの対応)
  - [サブボリュームとスナップショット](#サブボリュームとスナップショット)
  - [圧縮](#圧縮)
  - [押さえておく誤解](#押さえておく誤解)
  - [そのほかの特徴](#そのほかの特徴)
- [btrfs コマンド](#btrfs-コマンド)
  - [サブコマンドの一覧](#サブコマンドの一覧)
  - [ファイルシステムの情報を表示する](#ファイルシステムの情報を表示する)
  - [サブボリュームを操作する](#サブボリュームを操作する)
  - [スナップショットを取る](#スナップショットを取る)
- [ファイルシステムの変換](#ファイルシステムの変換)
  - [変換できる組み合わせ](#変換できる組み合わせ)
  - [ext2 から ext3 への変換](#ext2-から-ext3-への変換)
  - [ext3 から btrfs への変換](#ext3-から-btrfs-への変換)
  - [逆は必ずしもできない](#逆は必ずしもできない)
- [結果画面の見方](#結果画面の見方)
- [つまずきポイント](#つまずきポイント)
- [クラウド実務メモ](#クラウド実務メモ)
- [参考リンク](#参考リンク)

---

## まずこれだけ

| やりたいこと | コマンド |
|:--|:--|
| **ファイルシステムの情報を表示する** | **`btrfs filesystem show`** |
| **サブボリュームを作成する** | **`btrfs subvolume create パス`** |
| サブボリュームを削除する | `btrfs subvolume delete パス` |
| **サブボリュームの一覧を表示する** | **`btrfs subvolume list パス`** |
| **スナップショットを作成する** | **`btrfs subvolume snapshot 元 先`** |
| ext3 から btrfs へ変換する | `btrfs-convert デバイス` |
| ext2 から ext3 へ変換する | `tune2fs -j デバイス` |

**押さえる 3 点**

| 論点 | 結論 |
|:--|:--|
| 操作コマンドの形 | **`btrfs サブコマンド`**。`btrfs show` や `btrfs make snapshot` という書き方は**存在しない** |
| スナップショットを取る単位 | **サブボリューム**。だから `subvolume snapshot` という 2 語になる |
| 変換の向き | **`ext2 → ext3 → ext4`、`ext3 → btrfs` は可能。逆は必ずしもできない** |

---

## Btrfs の特徴

**Btrfs（B-tree File System：バターエフエス、またはビーツリーエフエスと発音します）は
比較的新しく高機能な Linux のファイルシステム**です。

Btrfs は以下の機能を持っています。

### マルチデバイスへの対応

**これまでの ext2/ext3/ext4 は、単一デバイスの単一パーティションにしかファイルシステムを
作成できませんでした。** その後「**論理ボリュームマネージャ（LVM：Logical Volume Manager）**」によって
複数デバイスを論理的に 1 つのデバイスとして扱うことで、
複数のデバイスにまたがってファイルシステムを作成することができるようになりました。

**しかし、Btrfs はファイルシステム自身が複数のデバイス（マルチデバイス）を直接扱えるようになっています。**

```text
【ext4 の場合】複数ディスクをまたぐには LVM が必要
  ディスク1 ┐
  ディスク2 ├─→ LVM（論理ボリューム）─→ ext4
  ディスク3 ┘

【Btrfs の場合】ファイルシステム自身が複数ディスクを扱える
  ディスク1 ┐
  ディスク2 ├─→ Btrfs
  ディスク3 ┘
```

**層が 1 つ減る**のがポイントです。公式ドキュメントでも
「ボリューム管理を内蔵し、ソフトウェア RAID 0 / 1 / 10 などに対応する」と説明されています。

```bash
$ sudo mkfs.btrfs /dev/sdb /dev/sdc  # 2本のディスクにまたがる Btrfs を作る
$ sudo btrfs device add /dev/sdd /data   # 運用中にディスクを追加する
```

### サブボリュームとスナップショット

**Btrfs は、ディレクトリの一部を「サブボリューム」として個別のファイルシステムのように扱えます。
サブボリュームを使うことで、ある時点のファイルシステムの状態を「スナップショット」として
取得することができるようになります。**

```bash
$ sudo btrfs subvolume create /data/app       # サブボリュームを作る
$ sudo btrfs subvolume snapshot /data/app /data/app_20260902   # スナップショットを取る
```

**スナップショットは全コピーではありません。** 公式ドキュメントは
「スナップショットはファイルの完全なコピーを作らない」と明記しています。
**COW（Copy on Write：書き込み時にコピー）** という仕組みで、
**変更があった部分だけ**を新しく書くため、一瞬で取得でき、容量もほとんど使いません。

```text
スナップショット取得直後
  app ────┐
          ├─→ 同じデータを共有（容量は増えない）
  app_バックアップ ┘

app の一部を書き換えたあと
  app ─→ 変更した部分だけ新しく書く
  app_バックアップ ─→ 元のデータを指したまま
```

パッケージ更新の前にスナップショットを取り、問題があれば戻す、という運用に使われます。

### 圧縮

**Btrfs は、ファイルシステムが自動でデータを圧縮できるようになっています。
圧縮用の特別な操作を必要とせず、マウント時に自動圧縮を有効にするオプションを指定するだけで動作します。**

```bash
$ sudo mount -o compress=zstd /dev/sdb1 /data   # 自動圧縮を有効にしてマウントする
```

「ファイルの圧縮はサポートしていない」というのは**誤り**です。

### 押さえておく誤解

| よくある誤解 | 正しくは |
|:--|:--|
| 「inode の数が制限される」 | **Btrfs は動的 inode**。公式ドキュメントも「Dynamic inode allocation」を機能として挙げている |
| 「ファイルの圧縮はサポートしていない」 | **マウントオプションで透過的に圧縮できる** |
| 「ext3 の後継である」 | **ext3 の後継は ext4**。Btrfs は**独立した設計**の新しいファイルシステム（ext2/3/4 からの変換機能はある） |

**「ext2 → ext3 → ext4」は一本の系譜**、**Btrfs はその外側にある別系統**、という整理で覚えます。

### そのほかの特徴

| 機能 | 内容 |
|:--|:--|
| **チェックサムと自己修復** | データとメタデータにチェックサムを持ち、**サイレントなデータ破損を自動検出**する。RAID 構成なら正しい側から自動修復する |
| **RAID の内蔵** | RAID 0 / 1 / 10 などをファイルシステム自身が持つ |
| **リフリンク（reflink）** | 実体を共有した高速なファイルコピー |
| **send / receive** | 差分だけを取り出して別のマシンへ転送できる（増分バックアップ） |

---

## btrfs コマンド

**Btrfs ファイルシステムを操作するコマンドは `btrfs`** です。
**サブコマンドを続けて書く**形をとります。

```text
btrfs サブコマンド [引数]
```

**`btrfs` はサブコマンドが階層になっている**のが特徴です。
`filesystem` や `subvolume` といった**グループ名**の後ろに、実際の動作を書きます。

```text
btrfs  filesystem  show
  │        │         └─ 動作
  │        └─────────── グループ
  └──────────────────── コマンド
```

### サブコマンドの一覧

| サブコマンド | 説明 |
|:--|:--|
| **`filesystem show`** | **ファイルシステムの情報を表示** |
| **`subvolume create`** | **サブボリュームを作成** |
| **`subvolume delete`** | **サブボリュームを削除** |
| **`subvolume list`** | **サブボリュームの一覧を表示** |
| **`subvolume snapshot`** | **スナップショットを作成** |
| `filesystem df` | 使用状況を表示（`df` より正確） |
| `device add` / `device delete` | 運用中にデバイスを追加・削除 |
| `balance start` | データをデバイス間で再配置する |
| `scrub start` | チェックサムを照合して破損を検出・修復する |

**存在しない書き方に注意**

| 見かける書き方 | 実際は |
|:--|:--|
| `btrfs show` | **存在しない**（正しくは `btrfs filesystem show`） |
| `btrfs show filesystem` | **語順が逆**。グループが先 |
| `btrfs filesystem info` | **存在しない**（`show` が正しい） |
| `btrfs snapshot` | **存在しない**（正しくは `btrfs subvolume snapshot`） |
| `btrfs make snapshot` | **存在しない** |
| `mkfs.btrfs-snapshot` | **存在しない**（`mkfs.btrfs` は作成コマンドで、スナップショットとは無関係） |

**覚え方** … **「何に対する操作か」を先に書く**と考えると迷いません。
ファイルシステム全体なら `filesystem`、サブボリュームなら `subvolume` です。

---

### ファイルシステムの情報を表示する

**意味** … **Btrfs ファイルシステムの情報（UUID・構成デバイス・使用量）を表示します。**

**例文**

```bash
$ sudo btrfs filesystem show                  # すべての Btrfs ファイルシステムを表示する
Label: 'data'  uuid: 4f1e50d8-1c12-4290-94c0-ee9c3d721500
        Total devices 2 FS bytes used 1.21GiB
        devid    1 size 10.00GiB used 2.01GiB path /dev/sdb
        devid    2 size 10.00GiB used 2.01GiB path /dev/sdc
```

**補足** … **`Total devices` が 2 になっている**のが Btrfs らしいところです。
**1 つのファイルシステムが 2 本のディスクにまたがっている**ことが、この 1 行で分かります。

```bash
$ sudo btrfs filesystem show /data            # マウントポイントを指定して絞り込む
$ sudo btrfs filesystem df /data              # 使用状況を種類別に表示する
```

**補足** … **Btrfs では `df` の値が実態とずれる**ことがあります。
メタデータやスナップショットの共有分があるためで、
**正確に見たいときは `btrfs filesystem df`** を使います。

---

### サブボリュームを操作する

**意味** … **サブボリュームは、ディレクトリの一部を個別のファイルシステムのように扱う単位**です。
**スナップショットを取る単位でもあります。**

**例文**

```bash
$ sudo btrfs subvolume create /data/app       # サブボリュームを作成する
Create subvolume '/data/app'
$ sudo btrfs subvolume list /data             # サブボリュームの一覧を表示する
ID 256 gen 12 top level 5 path app
$ sudo btrfs subvolume delete /data/app       # サブボリュームを削除する
Delete subvolume (no-commit): '/data/app'
```

| 出力の欄 | 意味 |
|:--|:--|
| **`ID`** | サブボリュームの識別番号 |
| `gen` | 世代番号（更新のたびに増える） |
| `top level` | 親サブボリュームの ID |
| **`path`** | **サブボリュームのパス** |

**補足** … **サブボリュームは `mkdir` で作ったディレクトリとは別物**です。
見た目はディレクトリですが、**個別にマウントでき、個別にスナップショットが取れます。**

```bash
$ sudo mount -o subvol=app /dev/sdb /mnt/app  # サブボリュームだけをマウントする
```

---

### スナップショットを取る

**意味** … **ある時点のサブボリュームの状態を保存します。**

**例文**

```bash
$ sudo btrfs subvolume snapshot /data/app /data/app_20260915   # スナップショットを作成する
Create a snapshot of '/data/app' in '/data/app_20260915'
```

**書式は「元」「先」の順**です。`cp` と同じ並びだと覚えます。

```bash
$ sudo btrfs subvolume snapshot -r /data/app /data/app_ro      # 読み取り専用で作る
```

**補足** … **`-r` を付けた読み取り専用スナップショットは、`btrfs send` で別マシンへ転送できます。**
増分バックアップの土台になります。

**戻し方**

```bash
$ sudo btrfs subvolume delete /data/app                          # ① 壊れた側を消す
$ sudo btrfs subvolume snapshot /data/app_20260915 /data/app     # ② スナップショットから戻す
```

**スナップショットからスナップショットを取れる**ので、**「戻す」＝「取り直す」**で済みます。

---

## ファイルシステムの変換

**各ファイルシステム間の移行は、原則としては現行のデータをバックアップし、
新しいファイルシステムを作成したのち、バックアップからコピーをするような形になります。**

**しかし、一部のファイルシステム間では、コマンドにより変換が可能**です。
**この場合、新たにデータを手動でコピーすることなく、新しいファイルシステムに移行できます。**

### 変換できる組み合わせ

| 変換 | できるか | コマンド |
|:--|:-:|:--|
| **ext2 → ext3** | **○** | **`tune2fs -j`** |
| ext2 / ext3 → ext4 | ○ | `tune2fs -O` でフィーチャを追加する |
| **ext3 → btrfs** | **○** | **`btrfs-convert`** |
| **ext4 → ext2** | **✕** | **逆方向はできない** |
| **ext2 → xfs** | **✕** | **新規に作成してデータを移す**しかない |
| xfs → ext4 | ✕ | 同上 |

**「変換できる場合でも、変換の逆は必ずしも可能ではない」**——ここが繰り返し問われます。

```text
  ext2 ──▶ ext3 ──▶ ext4        （一方向。戻れない）
    └──────▶ btrfs               （btrfs-convert。巻き戻し用の領域を残せば戻せる）

  ext系 ──✕──▶ xfs              （コマンドでの変換は無い）
```

**「ファイルシステムはそれぞれ独立した機構をもっているので、変換はできない」は誤り**です。
**できる組み合わせがあります。**

---

### ext2 から ext3 への変換

**`ext3` は `ext2` にジャーナリング機能を加えたもの**なので、
**ジャーナルを後から足すだけ**で変換できます。

```bash
$ sudo tune2fs -j /dev/sdb1                   # ジャーナルを追加して ext3 にする
$ sudo blkid /dev/sdb1                        # 種類が ext3 になったことを確認する
/dev/sdb1: UUID="..." TYPE="ext3"
```

**`/etc/fstab` の種類欄も `ext3` に書き換えます。** 忘れると次の起動で困ります。

**補足** … `tune2fs` は**ファイルシステムのパラメータを変更するコマンド**です。

| オプション | 意味 |
|:--|:--|
| **`-j`** | **ジャーナルを追加する（ext2 → ext3）** |
| `-l` | **スーパーブロックの情報を表示する**（UUID もここで分かる） |
| `-L ラベル` | ラベルを設定する |
| `-U UUID` | UUID を設定する |
| `-m 割合` | **root 用の予約ブロックの割合**を変更する |
| `-c 回数` / `-i 間隔` | 自動チェックの条件を変更する |

```bash
$ sudo tune2fs -l /dev/sdb1 | grep UUID       # UUID を調べる
$ sudo dumpe2fs /dev/sdb1 | grep UUID         # dumpe2fs でも同じことができる
Filesystem UUID:          5d17357c-8497-45b2-8592-008ea43f5487
```

**`dumpe2fs` はスーパーブロックとブロックグループの情報を表示するコマンド**です。
**UUID を調べる方法は `blkid` / `lsblk -f` / `/dev/disk/by-uuid` / `tune2fs -l` / `dumpe2fs` と複数あります。**

---

### ext3 から btrfs への変換

**`btrfs-convert` を使うと、ext3 のデータを保ったまま btrfs にできます。**

```bash
$ sudo umount /data                           # ① 必ずアンマウントしてから実行する
$ sudo btrfs-convert /dev/sdb1                # ② 変換する
$ sudo mount /dev/sdb1 /data                  # ③ マウントし直す
$ sudo btrfs filesystem show /data            # ④ btrfs になったことを確認する
```

**変換の仕組み**

```text
  元の ext3 のデータはそのまま置いておき、
  btrfs のメタデータを「空いている場所」に作る
        │
        ▼
  元のファイルシステムは ext2_saved というサブボリュームとして残る
        │
        ▼
  問題が無ければ ext2_saved を削除して領域を解放する
```

```bash
$ sudo btrfs subvolume list /data             # 巻き戻し用のサブボリュームを確認する
ID 256 gen 8 top level 5 path ext2_saved
$ sudo btrfs subvolume delete /data/ext2_saved   # 問題なければ削除して領域を空ける
```

**`ext2_saved` を消すまでは元に戻せます。** 消したあとは戻せません。

> **変換は必ずバックアップを取ってから行ってください。**
> **コマンドで変換できる場合も、万が一のためのバックアップは必要**です。

---

### 逆は必ずしもできない

| 言われ方 | 正しいか |
|:--|:--|
| ext3 ファイルシステムは btrfs ファイルシステムに変換できる | **○**（`btrfs-convert`） |
| ext4 ファイルシステムは ext2 ファイルシステムに変換できる | **✕**（**ext2 から ext4 へは移行できるが、その逆はできない**） |
| ext2 ファイルシステムは xfs ファイルシステムに変換できる | **✕**（**通常どおり、新規に作成してからデータを移す必要がある**） |
| ファイルシステムはそれぞれ独立した機構をもっているので、変換はできない | **✕**（**できる場合がある**） |

---

## 結果画面の見方

**`btrfs filesystem show` の出力**

```text
Label: 'data'  uuid: 4f1e50d8-1c12-4290-94c0-ee9c3d721500
        Total devices 2 FS bytes used 1.21GiB
        devid    1 size 10.00GiB used 2.01GiB path /dev/sdb
        devid    2 size 10.00GiB used 2.01GiB path /dev/sdc
```

| 欄 | 意味 | どこを見るか |
|:--|:--|:--|
| **`Label`** | ファイルシステムのラベル | `/etc/fstab` に `LABEL=` で書ける |
| **`uuid`** | ファイルシステムの UUID | `/etc/fstab` に `UUID=` で書ける |
| **`Total devices`** | **構成しているデバイスの本数** | **本数が想定と違えばデバイスが外れている** |
| `FS bytes used` | 実際に使っている容量 | `df` の値とずれることがある |
| **`devid`** | デバイスの識別番号 | **`missing` と出たらそのディスクが見えていない** |
| `size` / `used` | そのデバイスの容量と使用量 | 片寄っていたら `balance` を検討する |
| **`path`** | デバイスファイル | どのディスクか |

**`btrfs filesystem df` の出力**

```text
Data, RAID1: total=2.00GiB, used=1.19GiB
System, RAID1: total=32.00MiB, used=16.00KiB
Metadata, RAID1: total=256.00MiB, used=2.66MiB
GlobalReserve, single: total=16.00MiB, used=0.00B
```

| 行 | 意味 |
|:--|:--|
| **`Data`** | **実データの領域**。ここが枯れると書けなくなる |
| **`Metadata`** | **メタデータの領域**。**Data に空きがあってもここが枯れると書けなくなる** |
| `System` | ファイルシステム自身の管理情報 |
| `GlobalReserve` | 緊急用に確保された領域 |
| **`RAID1` / `single`** | **その領域の冗長化方式** |

**「空きがあるのに `No space left on device` になる」**という Btrfs 特有の現象は、
**`Metadata` が枯れている**ことが原因のことがあります。**`df` では分かりません。**

---

## つまずきポイント

| 症状 | 原因 | 対処 |
|:--|:--|:--|
| **`btrfs show` が動かない** | **サブコマンドが足りない** | **`btrfs filesystem show`** と書く |
| **`btrfs snapshot` が動かない** | 同上 | **`btrfs subvolume snapshot`** と書く |
| **`subvolume delete` できない** | そのサブボリュームがマウントされている／中に別のサブボリュームがある | アンマウントする。入れ子は内側から消す |
| **空きがあるのに書き込めない** | **`Metadata` が枯れている** | `btrfs filesystem df` で確認し、`btrfs balance start` で再配置する |
| **`btrfs-convert` が失敗する** | **マウントしたまま実行した** | **必ずアンマウントしてから**実行する |
| **変換後に起動しない** | **`/etc/fstab` の種類欄が古いまま** | `ext3` → `btrfs` のように書き換える |
| **スナップショットを取っても容量が減らない** | **スナップショットは元データを参照し続ける** | 不要なスナップショットを削除する |
| `df` の値が合わない | Btrfs は共有分があるため | **`btrfs filesystem df`** を使う |

---

## クラウド実務メモ

**更新前のスナップショットは「1 コマンドのロールバック」**

```bash
$ sudo btrfs subvolume snapshot -r / /.snapshots/before_update   # 更新前に取る
$ sudo dnf update                                                 # 更新する
```

**パッケージ更新やミドルウェアの設定変更の直前に取っておく**と、
**問題が起きたときにスナップショットから戻すだけ**で済みます。
openSUSE の `snapper` のように、**更新のたびに自動でスナップショットを取る仕組み**もあります。

**EBS スナップショットとの違い**

| | **Btrfs のスナップショット** | **EBS スナップショット** |
|:--|:--|:--|
| 取る場所 | **同じディスクの中** | **ディスクの外（S3）** |
| 速さ | **一瞬**（COW） | 初回は時間がかかる |
| **ディスクが壊れたら** | **一緒に失われる** | **残る** |
| 用途 | **直前の状態に戻す** | **バックアップ・複製** |

**Btrfs のスナップショットはバックアップではありません。**
**同じディスク上にあるので、ディスクが壊れれば一緒に失われます。**
**バックアップは EBS スナップショットや `btrfs send` で外へ出す**——この使い分けが要点です。

```bash
$ sudo btrfs send /.snapshots/daily | ssh backup-host 'btrfs receive /backup'   # 外へ送る
```

**コンテナのストレージドライバ**

**Docker のストレージドライバに `btrfs` を選ぶと、
イメージのレイヤをサブボリュームとスナップショットで表現**します。
いまは `overlay2` が既定ですが、**なぜ `btrfs` が候補に挙がるのか**はこの仕組みで説明できます。

**EC2 で使うなら**

```bash
$ sudo mkfs.btrfs /dev/nvme1n1                # EBS ボリュームに Btrfs を作る
$ sudo mount -o compress=zstd /dev/nvme1n1 /data   # 圧縮を有効にしてマウントする
```

**圧縮を効かせると EBS の容量と I/O を節約できます。**
ただし**既定の選択肢は ext4 か XFS** で、**Btrfs は要件があるときに選ぶ**のが実務の感覚です。

---

## 参考リンク

- [Btrfs 公式ドキュメント](https://btrfs.readthedocs.io/en/latest/)
- [btrfs(8) — man page](https://btrfs.readthedocs.io/en/latest/btrfs.html)
- [btrfs-subvolume(8)](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html)
- [btrfs-filesystem(8)](https://btrfs.readthedocs.io/en/latest/btrfs-filesystem.html)
- [btrfs-convert(8)](https://btrfs.readthedocs.io/en/latest/btrfs-convert.html)
- [man 8 tune2fs](https://man7.org/linux/man-pages/man8/tune2fs.8.html)
- [man 8 dumpe2fs](https://man7.org/linux/man-pages/man8/dumpe2fs.8.html)
- [Docker — Use the BTRFS storage driver](https://docs.docker.com/engine/storage/drivers/btrfs-driver/)

---

[← このフォルダの目次にもどる](./00_このフォルダにあるもの.md) ｜ [全体の目次にもどる](../README.md)
