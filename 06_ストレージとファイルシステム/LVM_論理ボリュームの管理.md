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

- [まずこれだけ](#まずこれだけ)
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
- [手を動かして確かめる](#手を動かして確かめる)
- [つまずきポイント](#つまずきポイント)
- [クラウド実務メモ](#クラウド実務メモ)
- [参考リンク](#参考リンク)

---

## まずこれだけ

| 層 | 略語 | 何か |
|:--|:--|:--|
| **物理ボリューム** | **PV** | **ハードディスク・パーティションなどの物理的な記憶デバイス**を LVM が扱うデータ領域にしたもの |
| **ボリュームグループ** | **VG** | **PV を 1 つ以上束ねた仮想的な領域** |
| **論理ボリューム** | **LV** | **VG の一部を自由に切り出したもの**。**仮想的なパーティション** |

**やりたいこと早見表**

| やりたいこと | コマンド |
|:--|:--|
| **PV を作る** | **`pvcreate /dev/sdb1`** |
| **VG を作る** | **`vgcreate vg1 /dev/sdb1 /dev/sdc1`** |
| **LV を作る** | **`lvcreate -L 100M -n lv1 vg1`** |
| **LV を増やす** | **`lvextend -L +1G /dev/vg1/lv1`** |
| **LV を減らす** | **`lvreduce -L -1G /dev/vg1/lv1`** |
| **LV を消す** | **`lvremove /dev/vg1/lv1`** |
| **VG から PV を外す** | **`vgreduce vg1 /dev/sdc1`** |
| **PV の印を消す** | **`pvremove /dev/sdc1`** |
| **スナップショットを作る** | **`lvcreate -s -L 1024M -n sn /dev/vg1/lv1`** |

> **下 5 行（増やす・減らす・消す・外す・スナップショット）の詳しい手順**は
> [LVM_サイズ変更とスナップショット](./LVM_サイズ変更とスナップショット.md) にあります。

**押さえる 3 点**

| 論点 | 結論 |
|:--|:--|
| **`remove` と `reduce`** | **`remove` はそのものを消す、`reduce` は中身を減らす**。`vgremove` は VG を消す、`vgreduce` は VG から PV を外す |
| **`extend` と `expand`** | **正しいのは `extend`**。`lvexpand` / `vgexpand` / `pvexpand` は**存在しない** |
| **`lvreduce` の注意** | **先にファイルシステムを縮小しておく**。忘れるとデータが壊れる |

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

**既定の PE サイズは 4MB**（実機で確認）です。
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
  ① pvcreate   デバイスを PV にする
        ▼
  ② vgcreate   PV を束ねて VG を作る
        ▼
  ③ lvcreate   VG から LV を切り出す
        ▼
  ④ mkfs       LV にファイルシステムを作る
        ▼
  ⑤ mount      使えるようにする
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

**存在しないオプション**：`-a` / `-S`（大文字）

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

> **実体は `/dev/mapper/VG名-LV名` へのシンボリックリンク**です。
> `ls -l /dev/vg1/lv1` を見ると `../dm-0` などを指しているのが分かります。
> **試験で問われるのは `/dev/VG名/LV名` の形**です。

```bash
$ ls -l /dev/vg1/                      # 実体を確かめる
lrwxrwxrwx 1 root root 7 Sep 16 10:00 lv1 -> ../dm-0
$ ls -l /dev/mapper/                   # こちらの名前でも同じものを指す
lrwxrwxrwx 1 root root 7 Sep 16 10:00 vg1-lv1 -> ../dm-0
```

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

## 手を動かして確かめる

**① ループバックデバイスで PV と VG を作る**

```bash
$ for i in 1 2; do dd if=/dev/zero of=p$i.img bs=1M count=200; done   # 200MBを2つ
$ sudo losetup -f --show p1.img        # ループバックデバイスに割り当てる
/dev/loop0
$ sudo losetup -f --show p2.img        # 2つ目も同様に割り当てる
/dev/loop1
$ sudo pvcreate /dev/loop0 /dev/loop1  # PV にする
  Physical volume "/dev/loop0" successfully created.
  Physical volume "/dev/loop1" successfully created.
$ sudo vgcreate vg1 /dev/loop0 /dev/loop1   # VG にまとめる
  Volume group "vg1" successfully created
```

**② PE の数を確かめる**

```bash
$ sudo vgdisplay vg1 | grep -E "PE|VG Size"   # PE 関連の行だけ抜き出す
  VG Size               392.00 MiB
  PE Size               4.00 MiB
  Total PE              98
  Alloc PE / Size       0 / 0
  Free  PE / Size       98 / 392.00 MiB
```

**読み取れること**

| 観察 | 意味 |
|:--|:--|
| **`VG Size` が 392MiB** | **200MB × 2 = 400MB から、メタデータぶんが引かれている** |
| **`PE Size` が 4.00 MiB** | **既定の PE サイズ** |
| **`Total PE` が 98** | **392 ÷ 4 = 98。計算が合う** |
| **`Free PE` が 98** | **まだ LV を作っていないので全部空き** |

**③ 片方の PV だけ見る**

```bash
$ sudo pvdisplay /dev/loop0 | grep -E "PV Name|VG Name|Total PE|Free PE"   # 主要な行だけ
  PV Name               /dev/loop0
  VG Name               vg1
  Total PE              49
  Free PE               49
```

**2 つの PV がそれぞれ 49 PE を持ち、合計 98 PE** になっていることが確認できます。

**④ 後片付け**

```bash
$ sudo vgremove vg1                    # VG を消す
$ sudo pvremove /dev/loop0 /dev/loop1  # PV の印を消す
$ sudo losetup -d /dev/loop0 /dev/loop1   # ループバックを外す
```

> **このノートの `pvcreate` / `vgcreate` / `pvdisplay` / `vgdisplay` の出力はサンドボックスの実測値**です。
> **`lvcreate` 以降はカーネルに device-mapper が無いため実行できませんでした**
> （`Required device-mapper target(s) not detected in your kernel.`）。
> **`lvcreate` 以降の出力例は Ping-t の解説にあるもの**を使っています。

---

## つまずきポイント

| 症状 | 原因 | 対処 |
|:--|:--|:--|
| **`lvexpand` が `command not found`** | **`expand` ではなく `extend`** | **`lvextend`** |
| **`pvcreate` が 2 回目でエラーになる** | **すでに PV になっている** | 状態を `pvdisplay` で確かめてから。自動化では専用モジュールを使う |
| **`Insufficient free space`** | **VG に空きが無い** | **`vgdisplay` の `Free PE` を確認**する。`vgextend` で PV を足す |
| **`/dev/LV名/VG名` でマウントできない** | **VG と LV の順番が逆** | **`/dev/VG名/LV名`**。ディレクトリ側が VG |
| **`lvcreate -L 100M` なのに 128MB になる** | **PE の倍数に切り上げられた** | 仕様。**既定の PE は 4MB** |
| **`vgremove` できない** | **中に LV が残っている** | **先に `lvremove`** |

---

## クラウド実務メモ

**① EBS + LVM は「止めずに増やす」ための定番構成**

```text
  【LVM なし】
    EBS を拡張 → growpart → resize2fs      … 1本の上限まで

  【LVM あり】
    EBS を足す → pvcreate → vgextend → lvextend -r   … 何本でも足せる
```

**新しい EBS をアタッチしたあとの手順**

```bash
$ sudo pvcreate /dev/nvme2n1                    # ① PV にする
$ sudo vgextend vg_data /dev/nvme2n1            # ② VG に足す
$ sudo lvextend -r -l +100%FREE /dev/vg_data/lv_data   # ③ LV とFSを一気に広げる
$ df -h /data                                   # ④ 確認する
```

**サービスを止めずに、数十秒で終わります。**

**② LVM を使うかどうかの判断**

| 状況 | LVM を使うか |
|:--|:--|
| **データ領域が育つ見込みがある** | **使う**。あとから足せる |
| **スナップショットでバックアップを取りたい** | **使う** |
| **ルートボリュームだけの小さなインスタンス** | **使わなくてよい**。EBS の拡張 + `growpart` で足りる |
| **コンテナホスト** | **使わないことが多い**。ノードは使い捨てにする |
| **オートスケールで使い捨てる** | **使わない**。構成が複雑になるだけ |

**「このサーバは何年も生きるか？」がいちばんの判断軸**です。
**使い捨てのインスタンスに LVM を入れると、構成管理が面倒になるだけ**になります。

---

## 参考リンク

- [man 8 lvm](https://man7.org/linux/man-pages/man8/lvm.8.html)
- [man 8 pvcreate](https://man7.org/linux/man-pages/man8/pvcreate.8.html)
- [man 8 vgcreate](https://man7.org/linux/man-pages/man8/vgcreate.8.html)
- [man 8 lvcreate](https://man7.org/linux/man-pages/man8/lvcreate.8.html)
- [man 8 pvdisplay](https://man7.org/linux/man-pages/man8/pvdisplay.8.html)
