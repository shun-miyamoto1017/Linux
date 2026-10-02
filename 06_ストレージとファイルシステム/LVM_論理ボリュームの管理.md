# LVM_論理ボリュームの管理

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — 論理ボリュームマネージャの設定と管理 |
| **業務での使いどころ** | **サービスを止めずに容量を増やす。**「`/var` が溢れた」に対して、ディスクを足して `lvextend` するだけで済む。オンプレでもクラウドでもここは変わらない |

> **このノートは LVM の考え方と、作る側のコマンド**です。
> **サイズ変更・削除・スナップショット・lvm.conf** は
> [LVM_サイズ変更とスナップショット](./LVM_サイズ変更とスナップショット.md)、
> **物理ディスクの追加手順**は [ディスクを追加する手順](./ディスクを追加する手順.md)、
> **RAID との違い**は [RAIDの基礎とレベル](./RAIDの基礎とレベル.md)、
> **できた LV のマウント**は [マウントとアンマウント](./マウントとアンマウント.md) にあります。

---

## 目次

- [3階層の考え方](#3階層の考え方)
- [PEという単位](#peという単位)
- [コマンドの命名規則](#コマンドの命名規則)
- [コマンド一覧](#コマンド一覧)
- [作る手順](#作る手順)
  - [pvcreate 物理ボリュームを作る](#pvcreate-物理ボリュームを作る)
  - [vgcreate ボリュームグループを作る](#vgcreate-ボリュームグループを作る)
  - [lvcreate 論理ボリュームを作る](#lvcreate-論理ボリュームを作る)
- [LVのデバイスファイル](#lvのデバイスファイル)
- [情報を見る display系](#情報を見る-display系)
- [参考リンク](#参考リンク)

---

## 3階層の考え方

**LVM ではハードディスク・パーティションなどの物理的な記憶デバイスを、
物理ボリューム（PV）と呼ばれるデータ領域として扱います。**

**そして PV を 1 つ以上束ね、ボリュームグループ（VG）と呼ばれる仮想的な領域とします。**

**作成した VG は、その一部を自由に論理ボリューム（LV）として切り出して利用できます。**

**LV は仮想的なパーティションで、ファイルシステムを作成してマウントするなど、
物理的なパーティションと同様の扱いが可能です。**

```text
  物理ディスク    /dev/sdb1      /dev/sdc1
                     │              │
                  pvcreate       pvcreate
                     ▼              ▼
  物理ボリューム   PV             PV
                     └──────┬───────┘
                         vgcreate
                            ▼
  ボリュームグループ      VG（プール）
                            │
                    ┌───────┼───────┐
                 lvcreate lvcreate lvcreate
                    ▼       ▼       ▼
  論理ボリューム    LV      LV      LV
                    │
                  mkfs → mount
                    ▼
                 /data として使える
```

**何がうれしいのか**

| 物理パーティション | LVM |
|:--|:--|
| **サイズ変更が難しい** | **`lvextend` / `lvreduce` で後から変えられる** |
| **1 台のディスクを超えられない** | **複数ディスクを束ねて 1 つの領域にできる** |
| **スナップショットが取れない** | **`lvcreate -s` で一瞬の状態を記録できる** |
| 隣のパーティションに邪魔されて拡張できない | **VG に空きがあれば、どの LV も伸ばせる** |

**「`/var` だけ足りない」を解決できる**のが、LVM を使う最大の理由です。

**RAID との違い**

```text
  RAID   冗長性 と 速度 のための仕組み     … 壊れても動くようにする
  LVM    柔軟性 のための仕組み             … あとから増やす・減らす・分ける

  両方使うこともある： 物理ディスク → RAID → PV → VG → LV
```

**LVM 自体は冗長化しません。** ディスクが 1 本壊れれば、その PV を含む VG は壊れます。
冗長化は [RAIDの基礎とレベル](./RAIDの基礎とレベル.md) の担当です。

**「LVM のメリットはどれか」への答え**

| 選択肢 | 正誤 | 理由 |
|:--|:-:|:--|
| **動的に各領域をリサイズすることができる** | **○** | **これが LVM を使う理由** |
| ハードディスクの障害に備えることができる | ✕ | **LVM を利用してもデータが冗長化されることはない**。それは **RAID1 / RAID5** |
| 転送速度を高速化することができる | ✕ | **LVM で速くなることはない**。それは **RAID0 / RAID5** |
| ファイルシステムを自動的に作成することができる | ✕ | **LV の上のファイルシステムは別途構築する**（`mkfs`）。LVM は面倒を見ない |

**3 階層の対応関係で誤答になるもの**

| 説明 | 正誤 | 理由 |
|:--|:-:|:--|
| **ボリュームグループに、後から物理ボリュームを加えることができる** | **○** | **VG は 1 つ以上の PV で構成され、後から追加・削除できる**（`vgextend` / `vgreduce`） |
| **論理ボリュームは、物理エクステントを最小単位として切り出される** | **○** | **PE が LVM における領域の最小単位**。LV は「PE 1000 個分」のように切り出される |
| ボリュームグループは、複数の論理ボリューム領域から構成される | ✕ | **VG を構成するのは LV ではなく PV**。LV は VG の一部を使って作る仮想的なパーティション |
| 論理ボリュームと物理ボリュームの間には、一対一対応の関係がある | ✕ | **LVM は PE 単位で管理する**ので**対応関係は決まっていない**。1 つの PV に複数の LV が入ることも、1 つの LV が複数の PV にまたがることもある |
| 物理ボリュームは、後から自由にリサイズすることができる | ✕ | **PV はハードディスクやパーティションそのもの**なので、**ハードウェア上の制限内でしか扱えない**。自由にリサイズはできない |
| 物理エクステントは、物理的な記憶デバイスの領域のことである | ✕ | **PE は LVM による領域管理の最小単位**。**物理的な記憶デバイスの領域は物理ボリューム（PV）** |

```text
  PV ─────────┬──── LV      1つの PV に複数の LV が入ることもある
              └──── LV
  PV ──┐
       ├────────── LV       1つの LV が複数の PV にまたがることもある
  PV ──┘
        ▲ 一対一ではない。PE 単位で自由に割り当てられる
```

---

## PEという単位

**LVM では領域を物理エクステント（PE：Physical Extent）と呼ばれる単位で扱います。**
**物理ボリューム（PV）、ボリュームグループ（VG）、論理ボリューム（LV）のいずれも、
この PE がいくつ分、という数え方で容量が管理されています。**

```text
  PV ─┬─ PE ─┬─┐
      ├─ PE ─┤ │  VG の中で PE がプールされる
      ├─ PE ─┤ │
  PV ─┼─ PE ─┤ ├─▶ LV に何個か割り当てる
      └─ PE ─┴─┘
```

**既定の PE サイズは 4MiB**（実機で確認）です。
**`lvcreate -L 100M` と指定しても、PE の倍数に切り上げられます。**

```bash
$ sudo lvcreate -L 100M -n lv1 vg1     # 100M と指定しても
  Rounding up size to full physical extent 128.00 MB   ← PE の倍数に切り上がる
  Logical volume "lv1" created
```

**PE 関連の用語**

| 用語 | 意味 |
|:--|:--|
| **Total PE** | **その PV / VG が持つ PE の総数** |
| **Alloc PE**（Allocated PE） | **すでに LV に割り当てられた PE** |
| **Free PE** | **まだ割り当てられていない PE**（＝増やせる余地） |
| **PE Size** | **PE 1 個の大きさ**（既定 4MB） |

**「未割り当ての物理エクステントがいくつあるか」を調べたいときは
`vgdisplay` の `Free PE` を見ます。**

```bash
$ sudo vgdisplay vg1                   # VG の PE 情報を見る
  --- Volume group ---
  VG Name               vg1
  Format                lvm2
  VG Size               392.00 MiB
  PE Size               4.00 MiB
  Total PE              98
  Alloc PE / Size       0 / 0
  Free  PE / Size       98 / 392.00 MiB
```

**`Free PE` が 0 なら、その VG からはもう LV を増やせません。**
**PV を足して `vgextend` する**必要があります。

---

## コマンドの命名規則

**LVM のコマンドは「対象 ＋ 動詞」で機械的にできています。**

```text
  pv / vg / lv   ＋   create / remove / extend / reduce / display / scan / s
   │                        │
   どの層か                 何をするか
```

| 動詞 | 意味 |
|:--|:--|
| **`create`** | **作る** |
| **`remove`** | **そのものを削除する** |
| **`extend`** | **大きくする**（PV を足す / LV を伸ばす） |
| **`reduce`** | **小さくする**（PV を外す / LV を縮める） |
| **`display`** | **詳細情報を表示する** |
| `scan` | 探す |
| `s`（`lvcreate -s`） | スナップショット |

**この表を覚えれば、コマンド名は暗記しなくても組み立てられます。**

**存在しないコマンド**

| 見かける名前 | 実際は |
|:--|:--|
| **`lvexpand`** / **`vgexpand`** / **`pvexpand`** | **存在しない**。**正しくは `expand` ではなく `extend`** |
| **`pvextend`** | **存在しない**（PV は「伸ばす」対象ではない） |
| **`pvreduce`** | **存在しない** |
| **`rvcreate`** / **`rvdisplay`** | **存在しない**（`r` で始まる層は無い） |
| **`pvstat`** / **`vgstat`** / **`lvstat`** | **存在しない**（情報表示は `display`） |
| **`pvinfo`** / **`vginfo`** / **`lvinfo`** | **存在しない**（同上） |

> **入力問題で出題される可能性を考え、スペルも覚えておくといいでしょう。**
> **`extend`（e-x-t-e-n-d）**であって **`expand`** ではありません。

---

## コマンド一覧

| 層 | 作る | 削除・縮小 | 拡大 | 表示 |
|:--|:--|:--|:--|:--|
| **PV** | **`pvcreate`** | **`pvremove`** | — | **`pvdisplay`** |
| **VG** | **`vgcreate`** | **`vgremove`**（VG 自体）<br>**`vgreduce`**（PV を外す） | **`vgextend`**（PV を足す） | **`vgdisplay`** |
| **LV** | **`lvcreate`** | **`lvremove`**（LV 自体）<br>**`lvreduce`**（容量を減らす） | **`lvextend`**（容量を増やす） | **`lvdisplay`** |

**役割で引く早見表**

| やりたいこと | コマンド |
|:--|:--|
| **指定したデバイスを PV として初期化する** | **`pvcreate`** |
| **指定したデバイスから、物理ボリュームとしてのデータ構造を削除する** | **`pvremove`** |
| **PV から VG を作成する** | **`vgcreate`** |
| **作成済みの VG に PV を追加する** | **`vgextend`** |
| **作成済みの VG から指定した PV を取り除き、VG の容量を減らす** | **`vgreduce`** |
| **VG そのものを削除する** | **`vgremove`** |
| **VG から LV を切り出す** | **`lvcreate`** |
| **LV の容量を増やす** | **`lvextend`** |
| **LV の容量を減らす** | **`lvreduce`** |
| **LV を削除し、VG の空き領域に戻す** | **`lvremove`** |

---

## 作る手順

```text
  ① fdisk      パーティションを作り、タイプを 8e（Linux LVM）にする
        ▼
  ② pvcreate   デバイスを PV にする
        ▼
  ③ vgcreate   PV を束ねて VG を作る
        ▼
  ④ lvcreate   VG から LV を切り出す
        ▼
  ⑤ mkfs       LV にファイルシステムを作る
        ▼
  ⑥ mount      使えるようにする
```

**前後を空欄にして問われる 2 つ**

**「LVM を構成する手順」の穴埋めでは、
`pvcreate` の前にくる `fdisk` と、`mount` の前にくる `mkfs` が問われます。**

| 位置 | 作業 | まぎらわしい誤答 |
|:--|:--|:--|
| **`pvcreate` の前** | **`fdisk` コマンドによるパーティションの作成** | **`mkdir` によるディレクトリの作成**（マウントポイントは `mount` の直前） |
| **`mount` の前** | **`mkfs` コマンドによるファイルシステムの作成** | **`fdisk` によるパーティションの作成**（それは最初） |

```text
$ fdisk /dev/sdc
Command (m for help): t                    ← パーティションタイプを変える
8  AIX            4f  QNX4.x 3rd part  8e  Linux LVM       ← これを選ぶ
```

**`fdisk` でパーティションタイプを `8e`（Linux LVM）に設定します。**
**RAID の `fd`（Linux raid autodetect）と取り違えない**よう注意します
（[ソフトウェアRAIDの管理_mdadm](./ソフトウェアRAIDの管理_mdadm.md)）。

```bash
$ sudo mkfs -t ext3 /dev/vg1/lv1       # ⑤ LV にファイルシステムを作る
$ sudo mkdir /mnt/lv1                  # マウントポイントを用意する
$ sudo mount /dev/vg1/lv1 /mnt/lv1     # ⑥ マウントする
```

### pvcreate 物理ボリュームを作る

**指定したデバイスを PV として初期化するには、`pvcreate` コマンドを使います。**

```bash
$ sudo pvcreate /dev/loop0 /dev/loop1   # 2つのデバイスを PV にする（実機で確認）
  Physical volume "/dev/loop0" successfully created.
  Physical volume "/dev/loop1" successfully created.
```

**複数のデバイスをスペース区切りでまとめて指定**できます。

> **物理パーティションを PV にする場合は、`fdisk` でタイプを `8e`（Linux LVM）にしておく**のが作法です。
> **必須ではありません**が、`fdisk -l` で見たときに用途が分かります。
> （RAID の `fd` と取り違えないよう注意。詳しくは
> [ソフトウェアRAIDの管理_mdadm](./ソフトウェアRAIDの管理_mdadm.md)）

### vgcreate ボリュームグループを作る

**PV を 1 つ以上束ねて VG にします。**

```text
vgcreate VG名 PV [PV ...]
```

```bash
$ sudo vgcreate vg1 /dev/loop0 /dev/loop1   # 2つの PV を束ねて vg1 を作る（実機で確認）
  Volume group "vg1" successfully created
```

**あとから PV を足したいときは `vgextend`** です。

```bash
$ sudo pvcreate /dev/sdd1              # 新しいディスクを PV にして
$ sudo vgextend vg1 /dev/sdd1          # VG に足す（VG の容量が増える）
```

### lvcreate 論理ボリュームを作る

**作成した VG は、その一部を自由に論理ボリューム（LV）として切り出して利用できます。
その際に利用するコマンドが `lvcreate` です。**

```text
lvcreate [オプション] ボリュームグループ名
```

| オプション | 説明 |
|:--|:--|
| **`-L`** | **続けてボリュームサイズを指定** |
| **`-n`** | **続けて論理ボリューム名を指定** |
| **`-s`** | **スナップショットを作成** |
| `-l` | PE の個数でサイズを指定する |

```bash
$ sudo lvcreate -L 100M -n lv1 vg1     # サイズ100MB、名前 lv1 の LV を vg1 から作る
  Rounding up size to full physical extent 128.00 MB
  Logical volume "lv1" created
```

**`-L` はサイズ、`-n` は名前**——この 2 つを取り違えるのが典型的な誤答です。

```text
  -L  Length / Large  … サイズ
  -n  name            … 名前
  -s  snapshot        … スナップショット
```

**`-a`（`--activate y|n|ay`）は実在します**。作成直後に LV を有効化するかどうかの指定です（`lvcreate --help` で確認）。
**存在しないオプション**：`-S`（大文字）

**できた LV にファイルシステムを作ってマウントする**

```bash
$ sudo mkfs -t ext4 /dev/vg1/lv1       # LV は仮想的なパーティションなので mkfs できる
$ sudo mount /dev/vg1/lv1 /data        # 普通にマウントできる
```

---

## LVのデバイスファイル

**VG 名と LV 名が決まるとデバイスファイルのパス・名前も決まり、
`/dev/VG名/LV名` がその LV を表すデバイスファイルとなります。**

```text
  /dev/VolGroup00/LogVol02
       │           │
       │           └─ LV 名（ファイル名にあたる）
       └───────────── VG 名（ディレクトリ名にあたる）
```

**VG を切り出して LV を作るという包括関係を覚えていれば、
ディレクトリ名の方が VG 名、ファイル名の方が LV 名となることが納得できる**はずです。

```bash
$ sudo mount /dev/VolGroup00/LogVol02 /home   # VG名/LV名 の順に書く
```

| 書き方 | 正誤 | 理由 |
|:--|:-:|:--|
| **`/dev/VolGroup00/LogVol02`** | **○** | **VG が上、LV が下** |
| `/dev/LogVol02/VolGroup00` | ✕ | **位置が逆** |
| `/dev/VolGroup00_LogVol02` | ✕ | **アンダーバーで結合した名前にはならない** |
| `/dev/LogVol02_VolGroup00` | ✕ | 同上 |
| `VolGroup00-LogVol02` | ✕ | **`mount` の第一引数にはデバイスファイルを指定する必要がある** |
| `LogVol02-VolGroup00` | ✕ | 同上 |

**同じ LV を指す名前が 3 つある**

**LVM の仮想的なブロックデバイスは、デバイスマッパー（Device mapper）と呼ばれる機能によって実現**されています。
**そのため、1 つの LV に対して次の 3 つの名前が使えます。**

| 形式 | どういう名前か |
|:--|:--|
| **`/dev/VG名/LV名`** | **LVM が用意する名前**。試験で問われるのは基本これ |
| **`/dev/mapper/VG名-LV名`** | **デバイスマッパーが用意する名前**。`/etc/fstab` でよく見る |
| **`/dev/dm-`数字** | **カーネル内で扱われる名前**。**数字部分が変動する**ので、通常ユーザが直接使うことはない |

```text
  /dev/vg1/lv1  ─┐
                 ├─▶  同じ LV を指す
  /dev/mapper/vg1-lv1 ─┤
                 │
  /dev/dm-0     ─┘     ← 番号は起動のたびに変わりうる
```

```bash
$ ls -l /dev/vg1/                      # LVM が用意する名前の実体を見る
lrwxrwxrwx 1 root root 7 Sep 16 10:00 lv1 -> ../dm-0
$ ls -l /dev/mapper/                   # デバイスマッパー側の名前でも同じものを指す
lrwxrwxrwx 1 root root 7 Sep 16 10:00 vg1-lv1 -> ../dm-0
```

**「アクセスできるデバイス名の形式を 3 つ」への答え**

| 形式 | 正誤 | 理由 |
|:--|:-:|:--|
| **`/dev/VG/LV`** | **○** | **LVM が用意する名前** |
| **`/dev/mapper/VG-LV`** | **○** | **デバイスマッパーが用意する名前。区切りはハイフン** |
| **`/dev/dm-1`** | **○** | **カーネル内で扱われる名前** |
| `/dev/mapper/VG/LV` | ✕ | **`/dev/mapper` 配下はスラッシュではなくハイフンで繋ぐ** |
| `/dev/mapper-VG-LV` | ✕ | **`mapper` はディレクトリ**。ハイフンで繋がらない |
| `lvm-1` | ✕ | **このようなデバイス名は無い** |

> **`/dev/VG名/LV名` はどの環境でも使えます**が、
> **デバイスマッパーを利用するアプリケーションによっては、
> デバイスマッパーが用意するデバイス名とは別のデバイス名が用意されることもあります。**

---

## 情報を見る display系

| コマンド | 何を表示するか | 出力の 1 行目 |
|:--|:--|:--|
| **`pvdisplay`** | **PV の情報** | **`--- Physical volume ---`** |
| **`vgdisplay`** | **VG の情報** | **`--- Volume group ---`** |
| **`lvdisplay`** | **LV の情報** | **`--- Logical volume ---`** |

**出力の 1 行目を見れば、どのコマンドの結果か分かります。**
**これが「この出力が得られるコマンドはどれか」という設問の解き方です。**

**`pvdisplay` の出力**（実機で確認）

```bash
$ sudo pvdisplay /dev/loop0            # PV 単体の情報を見る
  --- Physical volume ---
  PV Name               /dev/loop0
  VG Name               vg1
  PV Size               200.00 MiB / not usable 4.00 MiB
  Allocatable           yes
  PE Size               4.00 MiB
  Total PE              49
  Free PE               49
  Allocated PE          0
  PV UUID               JBz1r6-yNug-V0Fq-rvRh-U5tG-UWBK-F5b1R3
```

| 欄 | 意味 |
|:--|:--|
| **`PV Name`** | **この PV のデバイスファイル** |
| **`VG Name`** | **どの VG に属しているか**（空なら未所属） |
| **`Allocatable`** | **LV に割り当て可能か** |
| **`Total PE` / `Free PE`** | **この PV が持つ PE の総数と空き** |

**`vgdisplay` の出力**（実機で確認）

```bash
$ sudo vgdisplay vg1                   # VG 全体の情報を見る
  --- Volume group ---
  VG Name               vg1
  Format                lvm2
  VG Access             read/write
  VG Status             resizable
  Cur LV                0
  Cur PV                2
  VG Size               392.00 MiB
  PE Size               4.00 MiB
  Total PE              98
  Alloc PE / Size       0 / 0
  Free  PE / Size       98 / 392.00 MiB
```

| 欄 | 意味 |
|:--|:--|
| **`Cur PV`** | **この VG を構成している PV の数** |
| **`Cur LV`** | **この VG から切り出された LV の数** |
| **`Free PE / Size`** | **まだ割り当てられていない領域**。ここを見て増設の余地を判断する |

**`lvdisplay` の出力**

```text
  --- Logical volume ---
  LV Name                /dev/VolGroup00/LogVol01
  VG Name                VolGroup00
  LV UUID                DSDZea-R4IO-ZXKv-X8iP-3w65-ILXg-5pQA3E
  LV Write Access        read/write
  LV Status              available
```

| 欄 | 意味 |
|:--|:--|
| **`LV Name`** | **LV のデバイスファイル**（`/dev/VG名/LV名`） |
| **`LV Status`** | **`available` なら使える状態** |
| `LV Write Access` | 読み書き可か読み込み専用か |

**短くまとめて見る `s` 系**

```bash
$ sudo pvs                             # PV を1行ずつ表で見る
$ sudo vgs                             # VG を1行ずつ
$ sudo lvs                             # LV を1行ずつ
```

**実務では `pvs` / `vgs` / `lvs` のほうがよく使います。**
**試験で問われるのは `display` 系**です。

---

## 参考リンク

- [man 8 lvm](https://man7.org/linux/man-pages/man8/lvm.8.html)
- [man 8 pvcreate](https://man7.org/linux/man-pages/man8/pvcreate.8.html)
- [man 8 vgcreate](https://man7.org/linux/man-pages/man8/vgcreate.8.html)
- [man 8 lvcreate](https://man7.org/linux/man-pages/man8/lvcreate.8.html)
- [man 8 pvdisplay](https://man7.org/linux/man-pages/man8/pvdisplay.8.html)
