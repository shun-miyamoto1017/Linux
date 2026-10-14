# LVM_作業手順とトラブル対応

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — 論理ボリュームマネージャの設定と管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **ディスクを渡されて「`/data` として使えるようにして」と言われたときに、上から順に潰していける手順書。**各段階の確認コマンドと、実際に出るエラーの読み方をまとめたもの |

> **このノートは LVM の作業手順と、困ったときの対処**です。
> **PV / VG / LV の考え方と各コマンドの意味**は
> [LVM_論理ボリュームの管理](./LVM_論理ボリュームの管理.md)、
> **サイズ変更・スナップショット・切り戻し**は
> [LVM_サイズ変更とスナップショット](./LVM_サイズ変更とスナップショット.md)、
> **fstab の書き方そのもの**は [fstabの書き方](./fstabの書き方.md) にあります。

> **このノートの検証状況**
> **`pvs` / `vgs` / `lvs` の列と、エラーメッセージの文言は、
> loop デバイス上の LVM 2.03.16 で実測**したものです
> （作業環境に device-mapper が無いため `--driverloaded n` を付けて
> **メタデータ操作だけ**を実行しています）。
> **RHEL 9 の devices file は Red Hat 公式ドキュメントと `man 8 lvmdevices` で確認**しています。
> **`mkfs` 以降（ファイルシステムの作成・マウント・fstab）は実測できていません。**
> **コマンドの書式と確認ポイントを示すにとどめ、作られた画面は載せていません。**

---

## 目次

- [通しの実例 ディスク2本から使えるまで](#通しの実例-ディスク2本から使えるまで)
  - [ステップ0 いまの状態を確認する](#ステップ0-いまの状態を確認する)
  - [ステップ1 パーティションを作る（任意）](#ステップ1-パーティションを作る任意)
  - [ステップ2 PV にする](#ステップ2-pv-にする)
  - [ステップ3 VG にまとめる](#ステップ3-vg-にまとめる)
  - [ステップ4 LV を切り出す](#ステップ4-lv-を切り出す)
  - [ステップ5 ファイルシステムを作る](#ステップ5-ファイルシステムを作る)
  - [ステップ6 マウントする](#ステップ6-マウントする)
  - [ステップ7 fstab に書いて永続化する](#ステップ7-fstab-に書いて永続化する)
  - [全体をもう一度](#全体をもう一度)
- [pvs vgs lvs を読む](#pvs-vgs-lvs-を読む)
- [つまずきやすいエラーと対処](#つまずきやすいエラーと対処)
  - [デバイスが見えないとき](#デバイスが見えないとき)
- [通しの実例 varが溢れたときの対応](#通しの実例-varが溢れたときの対応)
  - [ステップ1 どこに空きがあるかを確定させる](#ステップ1-どこに空きがあるかを確定させる)
  - [ステップ2 ディスクを足して VG を広げる](#ステップ2-ディスクを足して-vg-を広げる)
  - [ステップ3 LV とファイルシステムを広げる](#ステップ3-lv-とファイルシステムを広げる)
  - [ステップ4 記録を残す](#ステップ4-記録を残す)
- [メタデータのバックアップと巻き戻し](#メタデータのバックアップと巻き戻し)
- [参考リンク](#参考リンク)

---

## 通しの実例 ディスク2本から使えるまで

**ここまでのコマンドを、1 本の作業としてつなげます。**
**各段階に「ここまで来たか」を確かめるコマンド**を入れてあります。
**この確認を飛ばさないのが、つまずかないコツ**です。

**やること**：`/dev/sdb` と `/dev/sdc`（各 500GB）を束ねて、`/data` として使う。

### ステップ0 いまの状態を確認する

```bash
$ lsblk                                # ディスクが見えているか、未使用か
$ sudo pvs                             # 既に PV になっていないか
$ sudo vgs                             # 既存の VG を確認する
$ sudo blkid /dev/sdb /dev/sdc         # 何か入っていないか（空なら何も出ない）
```

> **`blkid` で何か出たら、そのディスクは使用中かもしれません。**
> **`pvcreate` は既存のシグネチャを見つけると確認を求めてきます。**
> **よくある事故は、ここで中身を確かめずに `y` と答えてしまうこと**です。

### ステップ1 パーティションを作る（任意）

```bash
$ sudo fdisk /dev/sdb                  # n で作成 → t で 8e（Linux LVM）→ w で保存
$ sudo fdisk /dev/sdc                  # sdc も同じようにする
$ sudo fdisk -l /dev/sdb /dev/sdc      # 両方のタイプが 8e になったか確認する
```

> **ディスク全体を LVM に使うなら、パーティションを作らず
> `pvcreate /dev/sdb /dev/sdc` としても動きます。**
> **このステップを飛ばす場合は、以降の `/dev/sdb1` `/dev/sdc1` を
> `/dev/sdb` `/dev/sdc` に読み替えてください。**
>
> **業務では切っておくことを勧めます。**
> `fdisk -l` を見た次の担当者が「このディスクは LVM 用だ」と分かるからです。
> **タイプ `8e` は印であって、LVM の動作条件ではありません。**
>
> **GPT では `8e` という番号は使いません。**
> `parted` なら `set N lvm on`、`sgdisk` なら型 `8E00` を指定します。
> （GPT 用の型名の表示は実機で確認してください）

### ステップ2 PV にする

```bash
$ sudo pvcreate /dev/sdb1 /dev/sdc1    # 2本まとめて PV にする
$ sudo pvs                             # PV になったか確認する
```

### ステップ3 VG にまとめる

```bash
$ sudo vgcreate vg_data /dev/sdb1 /dev/sdc1   # 2つの PV を束ねて VG を作る
$ sudo vgs                             # VSize と VFree を確認する
$ sudo vgdisplay vg_data               # Free PE / Size で空きを確認する
```

**ここで `Free PE / Size` を見ます。**
**この数字が、これから LV に切り出せる容量の上限**です。

### ステップ4 LV を切り出す

```bash
$ sudo lvcreate -L 300G -n lv_data vg_data   # 300GB の LV を作る
$ sudo lvs                             # LSize を確認する
$ ls -l /dev/vg_data/lv_data           # デバイスファイルができたか確認する
$ lsblk                                # ディスクの下に LV がぶら下がって見える
```

> **`-l 100%FREE` で全部使い切らず、あえて余らせています。**
> **スナップショット用と、あとで別の LV を作る余地**を残すためです。

### ステップ5 ファイルシステムを作る

```bash
$ sudo mkfs -t xfs /dev/vg_data/lv_data   # XFS を作る（RHEL の既定）
$ sudo blkid /dev/vg_data/lv_data         # UUID を確認する（fstab に使う）
```

> **`mkfs` の対象は LV のデバイスファイル**です。
> **`/dev/sdb1` に `mkfs` してしまう**のが典型的な間違いです。
> **それをやると PV のメタデータを壊します。**

### ステップ6 マウントする

```bash
$ sudo mkdir -p /data                  # マウントポイントを作る
$ sudo mount /dev/vg_data/lv_data /data   # 手動でマウントして動作を確かめる
$ df -h /data                          # 容量が見えるか確認する
$ sudo touch /data/test && ls -l /data # 書き込めるか確かめる
```

### ステップ7 fstab に書いて永続化する

**ここを忘れると、再起動でマウントが消えます。**

```bash
$ sudo blkid /dev/vg_data/lv_data      # UUID を取得する
$ sudo cp /etc/fstab /etc/fstab.bak    # 先にバックアップを取る
$ sudo vi /etc/fstab                   # 1行追記する
```

**書き方は 4 通りありますが、推奨順はこうです。**

| 書き方 | 評価 |
|:--|:--|
| **`UUID=a1b2c3d4-e5f6-7890-abcd-ef1234567890 /data xfs defaults 0 0`** | **いちばん安全**。デバイス名が変わっても影響を受けない |
| **`/dev/mapper/vg_data-lv_data /data xfs defaults 0 0`** | **可**。VG 名 ＋ LV 名で決まるので安定している |
| **`/dev/vg_data/lv_data /data xfs defaults 0 0`** | **可**。上と同じものを指す |
| `/dev/dm-0 /data xfs defaults 0 0` | **だめ**。**番号は起動のたびに変わりうる** |

> **クラウドで外部ストレージをマウントする場合は `nofail` を付ける**ことも検討してください。
> **ボリュームが付いていない状態で起動したときに、緊急モードに落ちるのを避けられます**
> （[fstabの書き方](./fstabの書き方.md)）。

```bash
$ sudo mount -a                        # fstab の記述が正しいか、再起動前に検証する
$ df -h /data                          # マウントされたか確認する
$ findmnt /data                        # どのデバイスがどう付いているかを見る
```

> **`mount -a` を必ず実行してください。**
> **fstab の書き間違いは、再起動時に緊急モードで止まります。**
> **再起動前に `mount -a` が無言で通ることを確かめる**のが鉄則です。
> 詳しくは [fstabの書き方](./fstabの書き方.md) にあります。

### 全体をもう一度

```text
  lsblk / blkid        ① いまの状態を確認する
        ▼
  fdisk （任意）        ② タイプ 8e のパーティションを作る
        ▼
  pvcreate → pvs       ③ PV にする
        ▼
  vgcreate → vgs       ④ VG にまとめる（Free PE を確認）
        ▼
  lvcreate → lvs       ⑤ LV を切り出す
        ▼
  mkfs → blkid         ⑥ ファイルシステムを作り、UUID を取る
        ▼
  mount → df           ⑦ 手でマウントして動作確認
        ▼
  fstab → mount -a     ⑧ 永続化して、再起動前に検証する
```

---

## pvs vgs lvs を読む

**`display` 系は試験で問われますが、実務で毎日打つのは `s` 系**です。
**1 行 1 件の表で出るので、全体を把握しやすい**からです。

```bash
$ sudo pvs                             # PV の一覧
$ sudo vgs                             # VG の一覧
$ sudo lvs                             # LV の一覧
```

**それぞれの列の読み方**（`lvs -o help` でフィールド一覧が出ます）

| `pvs` の列 | 意味 |
|:--|:--|
| **`PV`** | デバイスファイル |
| **`VG`** | **所属する VG**（空欄なら未所属） |
| **`PSize`** | この PV の容量 |
| **`PFree`** | **この PV の空き**。`pvmove` の移動先を選ぶときに見る |

| `vgs` の列 | 意味 |
|:--|:--|
| **`#PV` / `#LV`** | 構成 PV 数 / 切り出した LV 数 |
| **`VSize`** | VG 全体の容量 |
| **`VFree`** | **VG の空き**。**`lvextend` できるかはここで判断する** |

| `lvs` の列 | 意味 |
|:--|:--|
| **`LV` / `VG`** | LV 名 / 所属 VG |
| **`Attr`** | **状態を表す 10 文字**（読み方は[サイズ変更とスナップショットのノート](./LVM_サイズ変更とスナップショット.md)） |
| **`LSize`** | この LV の容量 |
| **`Origin`** | **スナップショットなら、元の LV 名** |
| **`Data%`** | **スナップショット / シンプールの使用率**。**スナップショットなら 100% で無効化、シンプールなら 100% で書き込みが止まる** |

**容量不足を調べるときの定番**

```bash
$ sudo vgs -o vg_name,vg_size,vg_free            # VG にどれだけ空きがあるか
$ sudo lvs -o lv_name,lv_size,data_percent,origin   # LV とスナップショットの使用率
$ sudo pvs -o pv_name,vg_name,pv_size,pv_free    # どの PV に空きがあるか
$ df -h                                          # ファイルシステム側の空き
```

> **`df` と `lvs` は別のものを見ています。**
> **`lvs` の `LSize` は LV の大きさ、`df` はその上のファイルシステムの大きさ**です。
> **`lvextend` したのに `df` が増えない**のは、この 2 つがずれているからです
> （[LVM_サイズ変更とスナップショット](./LVM_サイズ変更とスナップショット.md)）。

---

## つまずきやすいエラーと対処

**初めて LVM を触るときに出会う順に並べています。**

| エラー / 症状 | 原因 | 対処 |
|:--|:--|:--|
| **`WARNING: ext4 signature detected on /dev/sdb1. Wipe it? [y/n]`** | **そのデバイスに既存のファイルシステムがある** | **`y` の前に `blkid` と `lsblk` で中身を確認する。** 本当に不要か確かめてから進む |
| **`Cannot use /dev/sdb1: device is rejected by filter config`** | **`lvm.conf` の `filter` で除外されている** | 下の「デバイスが見えないとき」を参照（旧版では `Device ... excluded by a filter.`） |
| **`Cannot use /dev/sdb1: device is not in devices file`** | **devices file に登録されていない**（RHEL 9） | `sudo lvmdevices --adddev /dev/sdb1` で登録する |
| **`Can't open /dev/sdb1 exclusively. Mounted filesystem?`** | **マウント中か、他のプロセスが使っている** | `lsblk`・`findmnt`・`lsof` で使用者を探し、`umount` してから実行する |
| **`Volume group "vg1" not found`**<br>`Cannot process volume group vg1` | **VG 名の打ち間違い / PV が見えていない / filter か devices file で除外されている**。**この 3 つで同じメッセージが出ます**（実測） | `sudo vgs` で名前を確認 → `sudo pvs` で PV が見えるか確認 → 見えないなら下の「デバイスが見えないとき」へ |
| **LV が見えるのに使えない** | **LV が非アクティブ** | `sudo lvs -o lv_name,lv_attr` で `Attr` の 5 桁目を見る。`a` でなければ `sudo vgchange -ay vg1` |
| **`Volume group "vg1" has insufficient free space (170 extents): 5120 required.`**（`lvcreate`）<br>**`Insufficient free space: 5094 extents needed, but only 170 available`**（`lvextend`） | **VG に空きが足りない**。**コマンドによって文言が違います**（実測） | `vgs` で `VFree` を確認。`vgextend` で PV を足す |
| **`Rounding up size to full physical extent 104.00 MiB`** | **指定サイズが PE の倍数でない** | **エラーではない**。PE の倍数に切り上げられただけ |
| **`Please specify either size or extents (not both).`** | **`-L` と `-l` を両方指定した** | どちらか一方にする |
| **再起動したら `/data` が無い** | **`/etc/fstab` に書いていない** | fstab に追記し、`mount -a` で検証する |
| **`mkfs` したのに容量が想定と違う** | **`/dev/sdb1` に `mkfs` してしまった**（LV ではなく PV に） | PV のメタデータが壊れている。`vgcfgrestore` での復旧を検討する |

### デバイスが見えないとき

**LVM が「そのデバイスを見ない」設定になっていることがあります。**
**見る仕組みが 2 つあり、どちらが有効かで確認先が変わります。**

| 仕組み | 設定場所 | 確認コマンド |
|:--|:--|:--|
| **devices file**（**RHEL 9 で既定**） | **`/etc/lvm/devices/system.devices`** | **`sudo lvmdevices`** |
| **filter**（従来の方式） | **`/etc/lvm/lvm.conf` の `filter`** | **`sudo lvmconfig devices/filter`** |

```bash
$ sudo lvmconfig devices/use_devicesfile      # どちらが有効か（1 なら devices file）
$ sudo lvmdevices                             # devices file の一覧を見る
$ sudo lvmdevices --adddev /dev/sdb1          # 使いたいデバイスを登録する
$ sudo lvmconfig devices/filter               # filter の設定を見る
$ sudo lvmdevices --check                     # devices file と実デバイスのずれを調べる
$ sudo vgscan                                 # VG を探し直す
```

**Red Hat の公式ドキュメント（RHEL 9）にこうあります。**

> - "The LVM devices file is the list of devices that lvm commands will use."
> - "By default, the system.devices file feature is enabled in Red Hat Enterprise Linux 9."
> - devices file が有効なとき … "it replaces the LVM device filter."

**つまり `system.devices` がある間は、`lvm.conf` の `filter` を書いても効きません。**

```text
  system.devices がある   → devices file で絞る。filter は無視される
  system.devices が無い   → 従来どおり filter が効く
      ▲ RHEL 8 からの移行で「filter を書いたのに効かない」のはこれ
```

`man 8 lvmdevices` の記述です。

> "When the devices file is used, lvm commands ignore the lvm.conf filter setting,
> except for vgimportdevices."

> **RHEL 8 から RHEL 9 へ移行した環境で `system.devices` が作られているかは、
> まず現物を確認してください。**
> **あるかないかで、どちらを触るべきかが変わります。**

> **`system.devices` を直接編集するのは非推奨**です。
> **`lvmdevices` コマンド（`--adddev` / `--deldev` / `--check` / `--update`）
> または `vgimportdevices` を使います。**
> **従来の `filter` を使いたい場合は `use_devicesfile=0` にします**
> （`system.devices` を削除しても実質無効になります）。

---

## 通しの実例 varが溢れたときの対応

**このノートのいちばん実務に近い使いどころ**です。
**`/var` が 95% になった、というアラートから始めます。**

### ステップ1 どこに空きがあるかを確定させる

```bash
$ df -h                                # どのファイルシステムが溢れているか
$ sudo lvs -o lv_name,vg_name,lv_size  # その LV の現在のサイズ
$ sudo vgs -o vg_name,vg_size,vg_free  # VG に空きがあるか  ★ここが分岐点
$ findmnt /var                          # /var がどの LV かを確定させる
```

**`VFree` の値で、やることが決まります。**

| `VFree` | やること |
|:--|:--|
| **空きがある** | **ステップ3 へ**（`lvextend` だけで済む） |
| **空きが無い** | **ステップ2 でディスクを足す** |

> **先に「本当に容量が足りないのか」も確認してください。**
> **古いログやキャッシュが溜まっているだけ**なら、拡張する前に片付けるのが筋です。
>
> ```bash
> $ sudo du -sh /var/* 2>/dev/null | sort -h | tail -10   # 何が容量を食っているか
> $ sudo journalctl --disk-usage                           # journal のサイズ
> $ df -i /var                                             # inode 枯渇かもしれない
> ```
>
> **`df -h` に空きがあるのに書けない場合、原因は 3 つ考えられます。**
>
> | 原因 | 確認方法 | 対処 |
> |:--|:--|:--|
> | **inode 枯渇** | **`df -i`** で `IUse%` が 100% | **ext4 は `resize2fs` で拡張すると inode も増えます**（100MB → 300MB で inode が 25600 → 76800 になることを実測）。XFS は inode を動的に確保するのでこの問題は起きにくい |
> | **削除済みだが開かれたままのファイル** | **`sudo lsof +L1`** | そのプロセスを再起動する |
> | **予約ブロック**（ext 系） | `sudo tune2fs -l` の `Reserved block count` | root 以外は使えない領域。通常は 5% |
>
> **まず `df -i` と `lsof +L1` を見てください。**
> **拡張する前に原因を切り分ける**のが先です
> （[ext系ファイルシステムの内部構造](./ext系ファイルシステムの内部構造.md)）。

### ステップ2 ディスクを足して VG を広げる

```bash
$ lsblk                                # 新しいディスクが見えているか
$ sudo pvcreate /dev/sdd1              # ① PV にする
$ sudo vgextend vg_system /dev/sdd1    # ② VG に足す
$ sudo vgs -o vg_name,vg_size,vg_free  # ③ VFree が増えたことを確認する
```

### ステップ3 LV とファイルシステムを広げる

```bash
$ sudo lvextend -r -L +50G /dev/vg_system/lv_var   # +50GB 広げ、FS も一緒に広げる
$ df -h /var                                        # 反映を確認する
$ sudo lvs -o lv_name,lv_size                       # LV 側も確認する
```

**`-L +50G` の `+` を忘れないでください。**

```text
  -L +50G    いまが 100G なら → 150G になる        （相対・意図どおり）
  -L 50G     いまが 100G なら → 拒否される          （絶対。lvextend は縮めない）
```

> **`lvextend` なら縮小方向は拒否されます**（`New size given ... not larger than existing size`）。
> **止まらないのは `lvreduce` と `lvresize`** です。
> **`+` を付ける癖を体に入れてください。**

### ステップ4 記録を残す

```bash
$ sudo lvs > /var/tmp/after-lvs.txt    # 作業後の状態を記録する
$ sudo vgs > /var/tmp/after-vgs.txt    # 同じく
$ df -h > /var/tmp/after-df.txt        # 同じく
```

**サービスを止めずにここまで終わります。**
**これが LVM を使う最大の理由**です。

---

## メタデータのバックアップと巻き戻し

**LVM は構成を変えるたびに、メタデータを自動でバックアップしています。**

| 場所 | 中身 |
|:--|:--|
| **`/etc/lvm/backup/`** | **現在のメタデータ** |
| **`/etc/lvm/archive/`** | **変更前の過去の版**。ファイル名は `<VG名>_<連番>-<乱数>.vg`（例：`vgt_00000-162220135.vg`。実測） |

**Red Hat の公式ドキュメント（RHEL 7）に
"Metadata backups and archives are automatically created whenever there is a configuration change"
（構成変更のたびに自動で作られる）とあります。**

**保持の既定値**（手元の LVM 2.03.16 の `lvm dumpconfig --type default` で確認）

| 設定 | 既定値 | 意味 |
|:--|:--|:--|
| **`retain_min`** | **`10`** | **最低 10 個は残す** |
| **`retain_days`** | **`30`** | **最低 30 日は残す** |

**ファイル名には乱数が入るので、`--list` の出力から取るのが確実**です。

```bash
$ ls -lt /etc/lvm/archive/ | head          # 過去の版を新しい順に見る
$ sudo vgcfgbackup vg_data                  # 手動でバックアップを取る
$ sudo vgcfgrestore --list vg_data          # 復元できる候補を一覧する
$ sudo vgcfgrestore -f /etc/lvm/archive/vg_data_00012-1234567890.vg vg_data   # 指定した版に戻す
```

**何に効くか**

```text
  間違って lvremove した
      → /etc/lvm/archive に「消す前」のメタデータが残っている
      → vgcfgrestore でメタデータを巻き戻せば、LV の定義は戻る
```

> **ただし「戻る」のはメタデータ（構成情報）だけ**です。
> **データ領域が既に上書きされていれば、中身は戻りません。**
> **`lvremove` 後の復旧について、Red Hat の公式ドキュメントに明確な記述は確認できていません。**
> **期待して運用するものではなく、最後の悪あがきと考えてください。**
>
> **シンプールを削除した場合は戻せません。**
> RHEL 8 のトラブルシューティングに
> **"If you remove a thin pool, LVM cannot reverse the operation."** とあります。
> `vgcfgrestore` の man にも、シンプールを含む VG では
> **"changes to thin metadata cannot be reverted"** とあり `--force` が必要です。

**作業前にやっておくこと**

```bash
$ sudo vgcfgbackup                          # 全 VG のメタデータを取る
$ sudo cp -a /etc/lvm/backup /var/tmp/lvm-backup-$(date +%F)   # 別の場所にも退避する
```

> **`/etc/lvm/archive` はそのサーバの中にあります。**
> **ディスクが丸ごと死んだら一緒に消えます。**
> **構成変更の前に、別の場所へコピーしておく**のが実務での作法です。

---

## 参考リンク

- [man 8 lvm](https://man7.org/linux/man-pages/man8/lvm.8.html)
- [man 8 lvcreate](https://man7.org/linux/man-pages/man8/lvcreate.8.html)
- [man 8 lvs](https://man7.org/linux/man-pages/man8/lvs.8.html)
- [man 8 lvmdevices](https://man7.org/linux/man-pages/man8/lvmdevices.8.html)
- [man 5 lvm.conf](https://man7.org/linux/man-pages/man5/lvm.conf.5.html)
- [Red Hat — Limiting LVM device visibility and usage (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_logical_volumes/limiting-lvm-device-visibility-and-usage_configuring-and-managing-logical-volumes)
- [Red Hat — Troubleshooting LVM (RHEL 8)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/configuring_and_managing_logical_volumes/troubleshooting-lvm_configuring-and-managing-logical-volumes)

---

[← 全体の目次にもどる](../README.md)
