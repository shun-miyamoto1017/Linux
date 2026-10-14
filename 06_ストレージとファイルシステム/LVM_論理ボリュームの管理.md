# LVM_論理ボリュームの管理

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — 論理ボリュームマネージャの設定と管理 |
| **業務での使いどころ** | **サービスを止めずに容量を増やす。**「`/var` が溢れた」に対して、ディスクを足して `lvextend` するだけで済む。オンプレでもクラウドでもここは変わらない |

> **このノートは LVM の考え方と、作る側のコマンド**です。
> **通しの作業手順と、実際に出るエラーの対処**は
> [LVM_作業手順とトラブル対応](./LVM_作業手順とトラブル対応.md) に分けてあります。

> **このノートの検証状況**
> **`pvcreate` / `vgcreate` / `lvcreate` / `lvdisplay` / `pvs` / `vgs` / `lvs` の出力と
> エラーメッセージは、loop デバイス上の LVM 2.03.16 で実測**したものです
> （作業環境に device-mapper が無いため `--driverloaded n` を付けて
> **メタデータ操作だけ**を実行しています。マウントまでは確認できていません）。
> **PE サイズの既定、RHEL 9 の devices file、容量上限は Red Hat 公式ドキュメントで確認**しています。
> **`mkfs` 以降（ファイルシステムの作成・マウント・fstab）は実測できていません。**
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
  - [サイズ指定は -L と -l の2通り](#サイズ指定は--l-と--l-の2通り)
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

**通常の（linear な）LV は冗長化しません。**
**ディスクが 1 本壊れると、その PV 上にある LV と、その PV にまたがる LV が使えなくなります。**
冗長化は [RAIDの基礎とレベル](./RAIDの基礎とレベル.md) の担当です。

> **ただし LVM 自身で RAID を組むこともできます。**
> **`lvcreate --type raid1` / `raid5` / `raid10` などが使えます**（`lvcreate --help` で確認）。
> **内部では md と同じカーネルドライバを使い、`mdadm` コマンドは使いません。**
>
> ```bash
> $ sudo lvcreate --type raid1 -m1 -L 100G -n lv_safe vg1   # LVM だけで RAID1 を組む
> $ sudo lvcreate -i2 -L 200G -n lv_fast vg1                # ストライプ（RAID0 相当）
> ```
>
> **`-i`（`--stripes`）でストライプ化すれば速くもなります。**
> **「LVM は冗長化も高速化もしない」というのは、
> 何も指定しない既定の linear な LV の話**だと理解してください。

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
| 物理ボリュームは、後から自由にリサイズすることができる | ✕ | **PV はハードディスクやパーティションそのもの**なので、**ハードウェア上の制限内でしか扱えない**。「自由に」はできない（ただし下記の `pvresize` はある） |
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
**指定したサイズが PE の倍数でないときは、PE の倍数に切り上げられます。**

```bash
$ sudo lvcreate -L 101M -n lv1 vg1     # 101M は 4MiB の倍数ではない
```

```text
  Rounding up size to full physical extent 104.00 MiB   ← 26 PE 分に切り上がった
  Logical volume "lv1" created.
```

**切り上げられない場合は、このメッセージは出ません。**（実測）

```text
  -L 100M   100 ÷ 4 = 25 PE ちょうど  → メッセージは出ない
  -L 101M   101 ÷ 4 = 25.25          → 26 PE（104 MiB）に切り上げ
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

**PE サイズは VG を作るときに決める**

**PE サイズは `vgcreate -s`（`--physicalextentsize`）で指定します。**
**既定は 4 MiB** です（Red Hat の公式ドキュメント：
"Physical extents (PE) and logical extents (LE) has the default size of 4 MiB that you can configure."）。

```bash
$ sudo vgcreate -s 16M vg1 /dev/sdb1 /dev/sdc1   # PE を16MiBにして VG を作る
$ sudo vgdisplay vg1 | grep "PE Size"            # 設定されたか確認する
```

| PE サイズ | 向いている場面 |
|:--|:--|
| **小さい（4MiB など）** | **細かくサイズ調整したい**。PE 数が増えるので管理情報も増える |
| **大きい（16MiB〜）** | **数 TB 以上の大きな VG**。PE の個数を抑えられる |

> **PE サイズは、原則として VG を作るときに決めます。**
> Red Hat の公式ドキュメント（RHEL 9）は **変更するには VG の作り直しが必要**としています。
> `vgcreate` の man の表現は
> **"difficult to change without recreating the VG unless no extents need moving"**
> （extent の移動が不要な場合を除き、VG を作り直さずに変えるのは難しい）です。
>
> **実際には `vgchange -s`（`--physicalextentsize`）で変えられる場合があります。**
> 手元の LVM 2.03.16 では、LV がある VG に対して `vgchange -s 2M vgt` が成功しました（実測）。
>
> ```bash
> $ sudo vgchange -s 2M vg1              # PE サイズを変更する（成功しない場合もある）
> $ sudo vgs -o vg_name,vg_extent_size   # 変わったか確認する
> ```
>
> **ただし本番では公式の手順（作り直し）に従ってください。**
> **「できる場合がある」に頼る操作ではありません。**
>
> **判断に迷うなら既定の 4 MiB のままで問題ありません。**
> **LVM2 では PE 数による実用上の容量制限はほぼ問題になりません**
> （RHEL 7 のドキュメントに "The maximum device size with LVM is 8 Exabytes on 64-bit CPUs." とあります）。
> **なお「PE サイズが LV の最大サイズを決める」という古い説明は LVM1 時代の話**で、
> LVM2 でも同じかどうかは公式ドキュメントで確認できていません。

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
| **`pvextend`** | **存在しない**。**下のディスクが大きくなったことを反映させるのは `pvresize`** |
| **`pvreduce`** | **存在しない**（`pvresize --setphysicalvolumesize` で縮める指定はある） |
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
| **下のディスクが大きくなったのを PV に反映させる** | **`pvresize`** |
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

**クラウドでディスクそのものが大きくなった場合**

**EBS や Persistent Disk はボリュームを無停止で拡張できます。**
**ただしディスクが大きくなっただけでは、PV・LV・ファイルシステムは広がりません。**

```text
  ① クラウド側でボリュームを拡張する     （AWS コンソール / gcloud など）
        ▼
  ② growpart /dev/nvme0n1 1              パーティションを広げる
        ▼
  ③ pvresize /dev/nvme0n1p1              PV に反映させる   ★ここを忘れやすい
        ▼
  ④ lvextend -r -l +100%FREE /dev/vg/lv  LV と FS を広げる
```

```bash
$ lsblk                                # ディスクが大きくなったか確認する
$ sudo growpart /dev/nvme0n1 1         # パーティションを広げる
$ sudo pvresize /dev/nvme0n1p1         # PV のサイズを再認識させる
$ sudo pvs -o pv_name,pv_size,pv_free  # PFree が増えたことを確認する
$ sudo lvextend -r -l +100%FREE /dev/vg_data/lv_data   # LV と FS を広げる
$ df -h /data                          # 反映を確認する
```

> **`pvresize` を飛ばすと `vgs` の `VFree` が増えません。**
> **「EBS を広げたのに容量が増えない」の原因はほぼこれ**です。
> **パーティションを切らずにディスク全体を PV にしている場合は ② が不要**で、
> `pvresize /dev/nvme0n1` だけで済みます。

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
$ sudo lvcreate -L 100M -n lv1 vg1     # サイズ100MiB、名前 lv1 の LV を vg1 から作る
```

```text
  Logical volume "lv1" created.
```

（PE が 4MiB なら 100MiB は 25 PE ちょうどなので、切り上げは起きません）

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

### サイズ指定は -L と -l の2通り

**`-L` はサイズ、`-l` は PE の個数**です。
**`-L` の単位を省くと MiB** になります（`-L 8` で 8.00m。実測）。
**`M` / `G` は 1000 ではなく 1024 基準（MiB / GiB）**なので、
`-L 1G` は 1024 MiB です。
**実務でいちばん使うのは `-l` のパーセント指定**なので、ここを押さえておくと楽になります。

| 指定 | 意味 |
|:--|:--|
| **`-L 100M`** | **100MB**（PE の倍数に切り上げられる） |
| **`-L 10G`** | **10GB** |
| **`-l 50`** | **PE 50 個分**（PE が 4MiB なら 200MiB） |
| **`-l 100%FREE`** | **VG の空き容量を全部使う** |
| **`-l 50%FREE`** | **VG の空き容量の半分** |
| **`-l 100%VG`** | **VG の全容量**。**空きが足りなければ空き分に切り詰められる**（下記） |
| **`-l 80%PVS`** | **指定した PV の空き容量の 80%**（PV はコマンドの末尾に並べる） |

```bash
$ sudo lvcreate -l 50%FREE -n lv_data vg1    # ① まず空きの半分を使う
$ sudo lvcreate -l 100%FREE -n lv_log vg1    # ② 残りを全部使う
```

**順番が逆だと 2 本目が作れません。**
**`-l 100%FREE` を先に打つと空きがゼロになる**ので、
次の `-l 50%FREE` は「0 エクステント」になって失敗します。

**`%FREE` と `%VG` の違い**

```text
  VG 全体 392MiB、すでに LV が 212MiB 使っている状態で

  -l 100%FREE   残りの 180MiB を使う
  -l 100%VG     392MiB を要求するが、空き分に切り詰められる
```

**`lvcreate` では `%VG` でもエラーになりません。**（実測）

```text
  Reducing 100%VG to remaining free space 180.00 MiB in VG.
  Logical volume "vg100" created.
```

> **`lvcreate` で使う分には `%VG` と `%FREE` はほぼ同じ結果**になります。
> ただし **`lvextend` では意味が変わります**（`%VG` は VG 全体を基準にした絶対指定）。
> **迷ったら `%FREE` を使う**のが安全です。

**空きが 1 つも無い状態で `%FREE` を指定すると、こうなります。**（実測）

```text
  Calculated size of logical volume is 0 extents. Needs to be larger.
```

> **`-l 100%FREE` を使うときは「あとで別の LV を作る余地が無くなる」**点に注意してください。
> **スナップショット用の空きを残しておきたい**なら、
> **`-l 80%FREE` のように余裕を残す**のが実務での作法です
> （[LVM_サイズ変更とスナップショット](./LVM_サイズ変更とスナップショット.md)）。

**`-L` と `-l` を同時に指定するとどうなるか**

**両方は指定できません。**（実測）

```text
  Please specify either size or extents (not both).
  Run `lvcreate --help' for more information.
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
| **`/dev/mapper/VG名-LV名`** | **デバイスマッパーが用意する名前**。`/etc/fstab` でよく見る。**VG 名や LV 名にハイフンが含まれると `--` に二重化される**（`my-vg` / `my-lv` → `/dev/mapper/my--vg-my--lv`） |
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

**LVM 2.03 系（RHEL 8 / 9）の出力**（実測）

```text
  --- Logical volume ---
  LV Path                /dev/vgt/p80
  LV Name                p80
  VG Name                vgt
  LV UUID                dS3Pyc-IXfX-GkfB-SHaq-5mIC-U5w4-XUyqbs
  LV Write Access        read/write
  LV Creation host, time vm, 2026-10-08 15:45:14 +0000
  LV Size                52.00 MiB
```

| 欄 | 意味 |
|:--|:--|
| **`LV Path`** | **LV のデバイスファイル**（`/dev/VG名/LV名`） |
| **`LV Name`** | **LV の名前だけ**（パスではない） |
| **`LV Status`** | **`available` なら使える状態** |
| `LV Write Access` | 読み書き可か読み込み専用か |

> **古い LVM（2.02 系。RHEL 6 / 7）では `LV Path` が無く、
> `LV Name` にパスが入っていました。**
>
> ```text
>   LV Name                /dev/VolGroup00/LogVol01      ← 2.02 系
> ```
>
> **「パスはどの欄か」は LVM のバージョンで変わります。**
> 試験で古い形式が出ることもあるので、両方知っておくと安心です。

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
- [man 8 lvmdevices](https://man7.org/linux/man-pages/man8/lvmdevices.8.html)
- [Red Hat — Managing LVM volume groups (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_logical_volumes/managing-lvm-volume-groups_configuring-and-managing-logical-volumes)
- [Red Hat — Limiting LVM device visibility and usage (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_logical_volumes/limiting-lvm-device-visibility-and-usage_configuring-and-managing-logical-volumes)
