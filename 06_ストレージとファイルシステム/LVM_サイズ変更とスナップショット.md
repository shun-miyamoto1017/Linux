# LVM_サイズ変更とスナップショット

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — 論理ボリュームマネージャの設定と管理 |
| **業務での使いどころ** | **「`/var` が溢れた」への即応。**`lvextend -r` で止めずに広げる。縮小とスナップショットは手順を間違えるとデータが消えるので、順番を身体で覚えておく |

> **このノートは作ったあとの LVM**（サイズ変更・削除・スナップショット・設定ファイル）です。
> **スナップショットからの復元（`lvconvert --merge`）と、容量を切らさない設定**もここにあります。
> **`/var` が溢れたときの通し手順とメタデータの巻き戻し**は
> [LVM_作業手順とトラブル対応](./LVM_作業手順とトラブル対応.md) に移してあります。

> **このノートの検証状況**
> **`lvm.conf` の既定値（自動拡張のしきい値、メタデータの保持数）は
> 手元の LVM 2.03.16 の `lvm dumpconfig --type default` で確認**しました。
> **`lvconvert --merge` の挙動、スナップショットが無効になる条件、XFS が縮小できないこと、
> `Attr` 各桁の意味は、`man` と Red Hat 公式ドキュメントで確認**しています（本文に出典を併記）。
> **作業環境に device-mapper が無いため、実際に LV やスナップショットを作っての確認はできていません。**
> **画面出力は載せず、コマンドの書式と確認ポイントにとどめています。**
> **PV / VG / LV の考え方と作り方**は
> [LVM_論理ボリュームの管理](./LVM_論理ボリュームの管理.md)、
> **ファイルシステムごとのツールの一覧**は
> [ファイルシステム別ユーティリティ](./ファイルシステム別ユーティリティ.md) にあります
> （`resize2fs` / `xfs_growfs` の使い方そのものは、このノートで扱います）。

---

## 目次

- [サイズを変える](#サイズを変える)
  - [lvextend 増やす](#lvextend-増やす)
  - [lvreduce 減らす](#lvreduce-減らす)
- [削除する remove系とreduce系](#削除する-remove系とreduce系)
- [lvs の Attr 10文字を読む](#lvs-の-attr-10文字を読む)
- [スナップショット](#スナップショット)
- [スナップショットから戻す lvconvert --merge](#スナップショットから戻す-lvconvert---merge)
  - [基本の流れ](#基本の流れ)
  - [「すぐ戻る」か「次回まで待つ」かが分かれる](#すぐ戻るか次回まで待つかが分かれる)
  - [root ファイルシステムの場合は再起動が必要](#root-ファイルシステムの場合は再起動が必要)
  - [マージの注意点](#マージの注意点)
- [スナップショットの容量を切らさない](#スナップショットの容量を切らさない)
  - [① 使用率を監視する](#①-使用率を監視する)
  - [② 自動拡張を有効にする](#②-自動拡張を有効にする)
  - [③ シンプロビジョニングのスナップショットを使う](#③-シンプロビジョニングのスナップショットを使う)
- [設定ファイル lvm.conf](#設定ファイル-lvmconf)
- [参考リンク](#参考リンク)

---

## サイズを変える

**LV のサイズは後からでも変更が可能で、
`lvextend` コマンドにより容量を増やすことが、
`lvreduce` コマンドにより容量を減らすことが、それぞれ可能です。**

### lvextend 増やす

```bash
$ sudo lvextend -L +1G /dev/vg1/lv1    # lv1 の容量を 1GB 増やす
```

| 書き方 | 意味 |
|:--|:--|
| **`-L +1G`** | **現在の容量に 1GB 足す**（**`+` が付く**） |
| **`-L 5G`** | **容量を 5GB にする**（`+` なし＝絶対値） |
| `-l +100%FREE` | VG の空きをすべて使う |

**`+` の有無で意味が変わります。**

```text
  -L +1G    いまが 3G なら → 4G になる     （相対）
  -L 1G     いまが 3G なら → 1G を要求     （絶対）
```

**ただし `lvextend` は小さい値を受け付けません。**（実測）

```text
  New size given (13 extents) not larger than existing size (39 extents)
```

| コマンド | 小さい値を指定したら |
|:--|:--|
| **`lvextend`** | **拒否される**（上のメッセージ） |
| **`lvreduce`** | **縮む**（ファイルシステムを先に縮めていないとデータが壊れる） |
| **`lvresize`** | **縮む**（拡張も縮小も両方できる） |

> **`lvextend` で誤って縮めてしまう事故は起きません。**
> **危ないのは `lvreduce` と `lvresize`** です。
> それでも **`+` を付ける癖**を付けておくと、コマンドを打ち間違えたときに効きます。

**ファイルシステムも広げる**

**LV を広げただけでは、その上のファイルシステムは広がりません。**

```bash
$ sudo lvextend -L +1G /dev/vg1/lv1    # ① LV を広げる
$ sudo resize2fs /dev/vg1/lv1          # ② ext系のファイルシステムを広げる
$ df -h /data                          # ③ 反映を確認する
```

| ファイルシステム | 広げるコマンド | マウントしたままできるか |
|:--|:--|:-:|
| **ext2 / ext3 / ext4** | **`resize2fs`** | **できる** |
| **XFS** | **`xfs_growfs /data`**（**マウントポイントを指定**） | **できる**（マウント必須） |
| Btrfs | `btrfs filesystem resize` | できる |

**`lvextend -r` で両方まとめて**

```bash
$ sudo lvextend -r -L +1G /dev/vg1/lv1   # -r でファイルシステムも自動でリサイズする
```

**`-r`（`--resizefs`）を付けるのが実務では定番**です。忘れる事故が防げます。

**`-r` は何をしているのか**

**`-r` は、ファイルシステムに応じたリサイズコマンドを LVM が代わりに呼ぶ**ものです。
**新しい LVM の man には**
**"Resize the fs using the fs-specific resize command (See: resize2fs(8), xfs_growfs(8), btrfs(8))."**
**とあります。**

```text
  ext2/3/4   → resize2fs を呼ぶ
  XFS        → xfs_growfs を呼ぶ
  Btrfs      → btrfs filesystem resize を呼ぶ
```

> **古い LVM では `fsadm` という仲介コマンドを経由していました。**
> 現在の LVM にも **`--fs resize_fsadm`** として残っていますが、
> man には **"deprecated"**（非推奨）と書かれています。
> **「`-r` は内部で `fsadm` を呼ぶ」という説明は旧仕様**です。
> **どちらの挙動になるかは LVM のバージョンによります**
> （手元の LVM 2.03.16 には `--fs` オプションがなく `-r` のみでした。
> RHEL 9 でどちらかは実機で確認できていません）。

### lvreduce 減らす

**論理ボリューム（LV）を縮小するコマンドは `lvreduce` です。**
**元のサイズ以下の任意のサイズに領域を縮小することができます。**
**`lvreduce` コマンドそのものにアンマウントやシステムの再起動は必要ありません。**
**ただし ext 系のファイルシステムを縮小するにはアンマウントが必要**です（後述の手順を参照）。

**ただし、ここに落とし穴があります。**

> **`lvreduce` で LV を縮小する際、
> その LV 上に構築されているファイルシステムのサイズまで自動的に縮小されるわけではありません。**
> **LV を縮小した結果、LV 上のファイルシステムのサイズより小さくなると、データが破損してしまいます。**

```text
  【間違った順番】
    lvreduce で LV を小さくする
        ▼
    ファイルシステムは元の大きさのまま
        ▼
    はみ出した部分が消える → データ破損

  【正しい順番】
    先に ファイルシステムを小さくする（resize2fs）
        ▼
    そのあと LV を小さくする（lvreduce）
```

**ext2/ext3/ext4 であれば `resize2fs` を利用して、
事前に縮小後の LV サイズに合わせてファイルシステムも縮小しておく必要があります。**

> **試験では `resize_reiserfs`（ReiserFS 用）も一緒に問われます。**
> ただし **ReiserFS は Linux 6.13 でカーネルから削除**されており、
> **実務で出会うことはまずありません。**

**「`lvreduce` を使って論理ボリュームの縮小を行う際に、注意するべき点は」の答え**

| 選択肢 | 正誤 | 理由 |
|:--|:-:|:--|
| **縮小後に合わせ、ファイルシステムをリサイズしておく必要がある** | **○** | **これが正しい注意点** |
| 縮小を行う際は、論理ボリュームをアンマウントしておく必要がある | ✕ | **LV の縮小にアンマウントは必要ない**（ただし**ファイルシステムのリサイズを行う際にはアンマウントが必要になることがある**） |
| 縮小により空いた領域は、ボリュームグループに追加し直す必要がある | ✕ | **縮小により解放された領域は自動的に元の VG の空き容量となる**ので、明示的に操作を行う必要はない |
| 縮小を行った後、システムを再起動する必要がある | ✕ | **再起動は必要ない** |

**安全な縮小手順**

```bash
$ sudo umount /data                    # ① ext の縮小はアンマウントが要る
$ sudo e2fsck -f /dev/vg1/lv1          # ② 先に整合性をチェックする（resize2fs が要求する）
$ sudo resize2fs /dev/vg1/lv1 3G       # ③ ファイルシステムを 3G に縮める
$ sudo lvreduce -L 3G /dev/vg1/lv1     # ④ そのあと LV を 3G に縮める
$ sudo mount /dev/vg1/lv1 /data        # ⑤ 戻す
```

> **XFS は縮小できません。** 拡張のみです。
> **縮小する可能性がある領域には ext4 を選ぶ**、という設計判断がここに効いてきます。

**XFS をどうしても小さくしたいとき**

**RHEL の既定は XFS です。** そして **XFS には縮小する機能がありません。**

**Red Hat の公式ドキュメント（RHEL 9 *Managing file systems*）の記述**です。

> - **"XFS has no utility to reduce the size of a file system."**
> - **"You can only increase the size of an XFS file system."**

**正攻法は「作り直す」しかありません。**

```text
  ① バックアップを取る          xfsdump / tar / rsync
        ▼
  ② LV ごと作り直す             lvremove → lvcreate（小さいサイズで）
        ▼
  ③ XFS を作る                  mkfs.xfs
        ▼
  ④ リストアする                xfsrestore / tar / rsync
```

```bash
$ sudo xfsdump -f /backup/data.xfsdump -L data -M media0 /data   # ① バックアップ
$ sudo umount /data                                              # ② アンマウント
$ sudo lvremove /dev/vg_data/lv_data                             #   LV を削除
$ sudo lvcreate -L 200G -n lv_data vg_data                       #   小さく作り直す
$ sudo mkfs -t xfs /dev/vg_data/lv_data                          # ③ XFS を作る
$ sudo mount /dev/vg_data/lv_data /data                          #   マウント
$ sudo xfsrestore -f /backup/data.xfsdump /data                  # ④ リストア
$ sudo blkid /dev/vg_data/lv_data                                # ⑤ 新しい UUID を取る
$ sudo vi /etc/fstab                                             #   fstab の UUID を更新する
$ sudo mount -a                                                  #   書き換えを検証する
```

> **`mkfs.xfs` をやり直すと UUID が変わります。**
> **fstab を `UUID=` で書いている場合、更新しないと次の再起動でマウントできません。**
> **⑤ を忘れないでください。**

> **この手順は一般的なものとして書いていますが、
> Red Hat の公式な縮小手順としては確認できていません。**
> **サービス停止が必要**で、**`-r` で楽に縮める方法はありません。**
>
> **だから設計時にこう考えます。**
>
> ```text
>   あとで縮める可能性がある        → ext4 にする
>   増やす一方でいい（普通はこちら） → XFS で問題ない
>   そもそも LV を大きく作りすぎない → これがいちばん効く
> ```

**`lvreduce -r` を使う**

```bash
$ sudo lvreduce -r -L 3G /dev/vg1/lv1  # -r ならファイルシステムも一緒に縮めてくれる
```

**それでもバックアップは取ってから**行います。縮小は拡張と違って取り返しがつきません。

---

## 削除する remove系とreduce系

**`remove` と `reduce` は似ていますが、きちんと区別する必要があります。**

| コマンド | 何を削除するか |
|:--|:--|
| **`lvremove`** | **論理ボリューム（LV）そのものを削除する**。解放された領域は VG の空き領域に戻る |
| **`vgremove`** | **ボリュームグループ（VG）そのものを削除する** |
| **`pvremove`** | **指定したデバイスから、物理ボリューム（PV）としてのデータ構造を削除する** |
| **`vgreduce`** | **作成済みの VG から指定した PV を取り除き、VG の容量を減らす** |
| **`lvreduce`** | **論理ボリューム（LV）の容量を減らす** |

**`lvremove` — LV を消して VG に返す**

**LV は不要になれば `lvremove` コマンドで削除することが可能です。**
**削除により解放された領域は VG の空き領域となり、
別の LV を作成したり、既に存在する他の LV の容量を増やしたりするために利用することができます。**

```bash
$ sudo lvremove /dev/vg1/lv1           # lv1 を削除（中のデータは消える）
```

**`pvmove` — 外す前にデータを逃がす**

**VG から特定の PV を取り除きたい場合、
その PV 内に書かれていたデータを失わないように他の PV に移す**必要があります。
**PE を他の PV に移す、ということです。**

**この操作を行うコマンドが `pvmove`** です。

```text
pvmove 移動元PV 移動先PV
```

```bash
$ sudo pvmove /dev/sdc1 /dev/sdd1      # sdc1 の PE を sdd1 へ逃がす
$ sudo vgreduce vg1 /dev/sdc1          # 空になったので VG から外せる
$ sudo pvremove /dev/sdc1              # PV としての印も消す
```

**引数の順番は「元 → 先」**です。逆に書くと意図と反対の移動になります。

| 書き方 | 正誤 |
|:--|:-:|
| **`pvmove /dev/sdc1 /dev/sdd1`**（sdc1 を外したい） | **○** |
| `pvmove /dev/sdd1 /dev/sdc1` | ✕（移動元と移動先が逆） |
| `lvmove /dev/sdc1 /dev/sdd1` | ✕（**そのようなコマンドは無い**） |
| `pvcopy /dev/sdc1 /dev/sdd1` | ✕（**そのようなコマンドは無い**） |
| `pemove /dev/sdc1 /dev/sdd1` | ✕（**そのようなコマンドは無い**） |

> **移動するのは PV そのものではなく、PV 内の PE** です。
> **それでもコマンド名は `pvmove`**（`pv` を使う）という点に注意します。

**`vgreduce` では PE は移動しません。**
**データが書き込まれている PV を取り除く際は、
`vgreduce` の前に `pvmove` で PE を移動させる必要があります。**

```text
  ① pvmove    PE を他の PV へ逃がす      … これを忘れるとデータが失われる
        ▼
  ② vgreduce  VG から PV を外す
        ▼
  ③ pvremove  PV としての印を消す
```

**`vgreduce` と `pvremove` の違い**

**ここが最頻出の引っかけどころ**です。

```text
  vgreduce vg1 /dev/sdc1    VG から その PV を 外す        … PV 自体はまだ PV のまま
        ▼
  pvremove /dev/sdc1        PV としての 印を消す           … ただのデバイスに戻る
```

| 問われ方 | 答え | 誤答しやすいもの |
|:--|:--|:--|
| **ボリュームグループから、構成している物理ボリュームを取り除く** | **`vgreduce`** | **`pvremove`**（名前から「PV を取り除く」に見えてしまう） |
| **指定したデバイスから、物理ボリュームとしてのデータ構造を削除する** | **`pvremove`** | `vgreduce` |
| **論理ボリュームを削除し、VG の空き領域に戻す** | **`lvremove`** | `lvreduce` |
| **ボリュームグループそのものを削除する** | **`vgremove`** | `vgreduce` |

> **コマンド名から考えると、`pvremove` が「構成している物理ボリュームを取り除く」コマンドのようにも
> 見えてしまうので注意して区別しましょう。**

**覚え方**

```text
  ◯◯remove   ◯◯ そのもの を消す        … lvremove は LV を、vgremove は VG を
  ◯◯reduce   ◯◯ の中身 を減らす        … vgreduce は VG から PV を、lvreduce は LV の容量を
```

**片付ける順番**

```text
  ① umount          使用をやめる
  ② lvremove        LV を消す
  ③ vgremove        VG を消す
  ④ pvremove        PV の印を消す
        ▲ 上から順に。逆順にはできない
```

---

## lvs の Attr 10文字を読む

**`lvs` の `Attr` 列は 10 文字の記号**です。
**スナップショットの状態判断はこの列を読むしかない**ので、ここを先に押さえます。

```text
  s w i - a - s - - -
  │ │ │ │ │ │ │ │ │ └ 10 アクティベーションをスキップするか
  │ │ │ │ │ │ │ │ └── 9  健全性（p=一部欠損 など）
  │ │ │ │ │ │ │ └──── 8  ゼロ埋めするか
  │ │ │ │ │ │ └────── 7  ターゲット種別
  │ │ │ │ │ └──────── 6  デバイスが open か
  │ │ │ │ └────────── 5  状態（a=active など）  ★いちばん見る桁
  │ │ │ └──────────── 4  マイナー番号固定
  │ │ └────────────── 3  割り当てポリシー
  │ └──────────────── 2  パーミッション（w=読み書き）
  └────────────────── 1  ボリューム種別           ★次に見る桁
```

**まず 1 桁目（種別）を見ます。**

| 1 桁目 | 意味 |
|:--|:--|
| **`-`** | **通常の LV（linear）** |
| **`s`** | **スナップショット** |
| **`o`** | **スナップショットの元（origin）** |
| **`O`** | **マージ中のスナップショットを持つ origin** |
| **`S`** | **マージ中のスナップショット** |
| **`V`** | **シンボリューム**（thin LV） |
| **`t`** | **シンプール** |
| **`r`** | **RAID LV** |
| `m` | ミラー LV |

**次に 5 桁目（状態）を見ます。**

| 5 桁目 | 意味 |
|:--|:--|
| **`a`** | **アクティブ**（正常） |
| **`s`** | **サスペンド中** |
| **`I`** | **スナップショットが無効（invalid）** ← **領域を使い切った状態** |
| **`S`** | サスペンド中かつ無効なスナップショット |
| **`m`** | **スナップショットのマージに失敗した** |
| `d` | テーブルの無いデバイス |
| `i` | テーブルが非アクティブなデバイス |

**6 桁目は `o` ならそのデバイスが open（使用中）**です。

**実際の見え方**

```text
  owi-aos---   元の LV。origin（o）、読み書き（w）、アクティブ（a）、open（o）
  swi-a-s---   スナップショット。正常
  swi-I-s---   スナップショットが 無効 になっている   ★これが出たら手遅れ
  Owi-a-s---   マージ中のスナップショットを持つ origin
  Swi-a-s---   マージ中のスナップショット
```

```bash
$ sudo lvs -o lv_name,lv_attr,lv_size,data_percent,origin   # 必要な列だけ出す
$ sudo lvs -o +lv_snapshot_invalid,lv_merging                # 無効か / マージ中かを明示的に見る
```

> **`I`（大文字のアイ）が 5 桁目に出たら、そのスナップショットはもう使えません。**
> **元に戻すこともバックアップを取ることもできません。**
> Red Hat のナレッジベースにも
> **"LVM Snapshot has become invalid with `I` listed under the `Attr` column of `lvs`."** とあります。
>
> **`swi-I-s---` という文字列そのものを載せた公式ページは見つかっておらず、
> これは各桁の定義（`man 8 lvs`）から組み立てたもの**です。
> **実機で確かめる際は、5 桁目が `I` かどうかだけを見てください。**

---

## スナップショット

**スナップショットは、ある瞬間の論理ボリュームの状態を記録しておくことができる機能**です。

**`lvcreate` に `-s` を指定して作成します。**

```bash
$ sudo lvcreate -s -L 1024M -n sn /dev/myvg/lv1   # lv1 のスナップショットを sn として作成
```

| オプション | 役割 |
|:--|:--|
| **`-s`** | **スナップショットを作成** |
| **`-L 1024M`** | **スナップショット用に確保する容量** |
| **`-n sn`** | **スナップショットの名前** |
| 最後の引数 | **元になる LV**（VG 名ではない） |

**通常の `lvcreate` との違い**

```text
  通常     lvcreate -L 100M -n lv1 vg1              最後は VG 名
  スナップ lvcreate -s -L 1024M -n sn /dev/myvg/lv1  最後は 元の LV
```

**何に使うか**

| 場面 | 使い方 |
|:--|:--|
| **止めずにバックアップを取る** | **スナップショットを取ってから、そちらをバックアップする**。元の LV は止めなくてよい（下の注意を参照） |
| **更新前に戻せるようにする** | 作業前にスナップショットを取り、失敗したら `lvconvert --merge` で戻す（次節） |

```bash
$ sudo lvcreate -s -L 5G -n snap /dev/vg1/data   # ① スナップショットを取る
$ sudo mount -o ro /dev/vg1/snap /mnt/snap       # ② 読み込み専用でマウントする（ext系）
$ tar czf /backup/data.tar.gz -C /mnt/snap .     # ③ こちらからバックアップする
$ sudo umount /mnt/snap && sudo lvremove /dev/vg1/snap   # ④ 済んだら消す
```

> **XFS では `-o ro` だけではマウントできません。**
> **スナップショットは元の XFS と同じ UUID を持つため、
> 元がマウント中だと UUID の重複で弾かれます。**
>
> ```text
>   XFS: Filesystem has duplicate UUID ... can't mount
> ```
>
> **`nouuid` を足してください。**
>
> ```bash
> $ sudo mount -o ro,nouuid /dev/vg1/snap /mnt/snap   # XFS はこう書く
> ```
>
> **RHEL の既定は XFS** なので、実務ではこちらが本番です。
> （この挙動は広く知られたものですが、作業環境では再現確認ができていません）

> **スナップショットから取れるのは「電源を抜いた瞬間」と同じ状態**です
> （クラッシュコンシステント）。
> **データベースのように、メモリ上にまだ書き出していないデータを持つものは、
> これだけでは整合が取れません。**
> **DB 側でフラッシュやバックアップモードに入れてから**スナップショットを取ります。

**スナップショットの容量に注意**

**スナップショットは「元の LV が変更された分」を貯めていきます。**
**確保した容量を使い切ると、スナップショットは無効になります。**

```bash
$ sudo lvs                             # Data% が 100% に近づいたら危ない
  LV    VG   Attr       LSize  Pool Origin Data%
  snap  vg1  swi-a-s---  5.00g      data    23.45
```

**元の LV の更新量を見積もって、余裕を持った容量**を確保します。
**目安として元ボリュームの 10% から 30% 程度**がよく使われますが、
**これは経験則**です。**実際は作業中にどれだけ書き換わるかで決まります。**
**パッチ適用やバッチ処理の最中は、想定よりはるかに書き換わる**ことがあります。

**仕組みと、そこから導ける性質**

**スナップショットが作成されていると、元ボリュームに対する変更内容が監視され、
必要に応じてスナップショット領域にデータが移されます。**

**退避されるのはファイル単位ではなく、ブロック（チャンク）単位**です。
カーネルの device-mapper 文書にも **"Changed chunks of \<chunksize\> sectors"**
（変更されたチャンク）と書かれています。

```text
  1GB のファイルの1バイトだけ書き換えても、
  退避されるのはその1バイトが含まれるチャンクだけ（既定は数十KB程度）
      ▲ ファイル全体がコピーされるわけではない
```

```text
  作成直後   スナップショット領域は空
       ▼ 元の LV のファイル A が書き換えられる
  変更時     A の「変更直前の姿」をスナップショット領域に退避する
       ▼
  参照時     退避したものと、変わっていない元のデータを組み合わせて見せる
```

**こうすることで、スナップショット領域は元ボリュームのデータのうち、
スナップショット作成後に変更があったものだけを保持すればよいことになり、容量を節約できます。**

| 説明 | 正誤 | 理由 |
|:--|:-:|:--|
| **スナップショットは、差分を利用したバックアップ方法である** | **○** | **全データをコピーするわけではない** |
| **スナップショットの作成サイズは、元ボリュームより小さくてよい** | **○** | **差分だけを持つから**。全部コピーするなら元と同じ容量が要る |
| **スナップショット領域を使い切ると、元の状態は復元できなくなる** | **○** | **以降の変更内容を移せなくなり、スナップショットは破壊される** |
| スナップショット作成前には、アンマウントを行っておく必要がある | ✕ | **監視と差分で状態を保存する仕組み**なので、**作成元のボリュームを読み込み専用にしたり、アンマウントしたりする必要はない** |

> **スナップショットを作成したままにしておくと、その後も変更点の監視がずっと続き、
> 変更点がスナップショット領域に蓄積され続けてしまいます。**
> **これはパフォーマンスに響く**ので、**不要になった際にきちんと削除**します。

> **Btrfs のスナップショットとは仕組みが違います。**
> **どちらも copy-on-write と呼ばれますが、何をコピーするかが逆**です。
>
> ```text
>   LVM    書く前に 旧データ を別領域（スナップショット領域）へコピーしてから上書きする
>          → 事前に領域を確保する必要がある。書き込みが遅くなる
>
>   Btrfs  新データ を別の場所へ書き、参照を切り替える（旧データはそのまま残る）
>          → 事前確保が要らない
> ```
>
> **LVM 方式は、スナップショットがある間ずっと書き込みが遅くなります。**
> **これも「不要になったら消す」理由**です
> （[Btrfsとサブボリューム](./Btrfsとサブボリューム.md)）。

---

## スナップショットから戻す lvconvert --merge

**スナップショットは「バックアップを取るための足場」だけでなく、
「取った瞬間の状態に戻す」ためにも使えます。**
**これがパッチ適用やアプリ更新の前に取る理由**です。

```text
  ① 作業前にスナップショットを取る
        ▼
  ② 更新作業をする（パッチ適用、設定変更、アプリのバージョンアップ）
        ▼
  ③a うまくいった  → スナップショットを lvremove で消す
  ③b 失敗した      → lvconvert --merge で取った瞬間に戻す
```

### 基本の流れ

```bash
$ sudo lvcreate -s -L 5G -n snap_before vg_data/lv_data   # ① 作業前に取る
$ sudo lvs -o lv_name,lv_attr,origin,data_percent          # 取れたか確認する
# （ここで更新作業をする）
$ sudo umount /data                                        # ③b 元 LV を未使用にして
$ sudo lvconvert --merge vg_data/snap_before               #     戻す
```

**`umount` を先に入れているのが肝**です。理由は次の節にあります。

### 「すぐ戻る」か「次回まで待つ」かが分かれる

**ここがいちばんつまずくところ**です。
**元 LV とスナップショットの両方が未使用（closed）なら即座にマージが始まります。**
**どちらかが使用中（open）なら、次にアクティベートされるまで延期**されます。

`lvconvert` の man にこうあります。

> - "if both the origin and snapshot LVs are not open, the merge will start immediately."
> - "Otherwise, the merge will start the first time either the origin or snapshot LV are activated and both are closed."
> - "When the merge finishes, the merged snapshot is removed."

```text
  /data がマウント中のまま lvconvert --merge を打つと

      "Delaying merge since snapshot is open."
      "Merging of snapshot ... will occur on next activation."
          ▲ この表示が出たら、まだ戻っていない
```

**だから手順はこうなります。**

```bash
$ sudo umount /data                                # ① 元 LV を未使用にする
$ sudo lvconvert --merge vg_data/snap_before        # ② ここで即座にマージが始まる
$ sudo lvs -o lv_name,lv_attr                      # ③ Attr の1桁目が S / O になっている
$ sudo mount /dev/vg_data/lv_data /data            # ④ マージ開始後はマウントしてよい
$ sudo lvs                                          # ⑤ 終わるとスナップショットが消えている
```

**`-i`（`--interval`）で進捗を定期表示させられます**（`lvconvert --help` で確認）。

```bash
$ sudo lvconvert --merge -i 5 vg_data/snap_before   # 5秒ごとに進捗を表示する
```

> **`lvs` の `Cpy%Sync`（`copy_percent`）はマージの進捗には使えません。**
> `lvs -o help` によると `copy_percent` は
> **「キャッシュ / RAID / ミラー / `pvmove` の同期率」**で、スナップショットのマージは対象外です。
> **進捗は `lvconvert -i` で見る**か、**`Attr` の 1 桁目が `-` に戻ったかで判断**します。
>
> **マージが始まったあとは、元 LV をマウントして使えます。**
> カーネルの device-mapper 文書にも、マージ開始後は origin を開いてよい旨の記述があります。

### root ファイルシステムの場合は再起動が必要

**`/`（root）はアンマウントできません。**
**そのため `lvconvert --merge` を打っても、実際のマージは次回起動時**になります。

```bash
$ sudo lvconvert --merge vg_rhel/root_snap   # マージを予約する
$ sudo reboot                                # 次回起動時にマージされる
```

```text
  RHEL 9 のドキュメントに出てくるデバッグ出力の例
      "Merging of thin snapshot ... will occur on next activation of rhel/root."
```

> **root の巻き戻しには、LVM だけでは足りない前提が 2 つあります。**
>
> **① `/boot` は巻き戻りません。**
> `/boot` は通常 LVM の外にあるため、スナップショットの対象外です。
> **カーネルを更新したあとに root だけ巻き戻すと、
> `/boot` に新しいカーネル、`/lib/modules` に古いモジュールが残る**ことになり、
> **起動に失敗しうる状態**になります。
>
> **② `/var` や `/usr` が別のファイルシステムだと、そこは巻き戻りません。**
>
> **Red Hat が公式に手順を示しているのは、RHEL 8 → 9 の Leapp アップグレード向けで、
> `boom` によるブートエントリの作成を前提にした構成**です
> （*Managing system upgrades with snapshots* の章）。
> **「普段のパッチ適用で気軽に root を巻き戻す」用途は、公式に示された手順ではありません。**
>
> **やるなら必ず検証環境で、`/boot` の扱いまで含めて一度通してください。**

### マージの注意点

| 注意点 | 内容 |
|:--|:--|
| **終わるとスナップショットは自動で消える** | man: **"When the merge finishes, the merged snapshot is removed."** 手で `lvremove` する必要はない |
| **「取ったあとの変更」は全部失われる** | 当然ながら、スナップショットを取った瞬間の状態に戻る |
| **マージ中に電源が落ちたら** | 再起動後に続きから進む。**`Attr` の 5 桁目が `m` ならマージ失敗**なので状態を確認する |
| **スナップショットが無効（`I`）だと戻せない** | 容量を使い切ったスナップショットでは**マージできません** |
| **シン LV の場合は `--mergethin`** | `--merge` はその別名。`lvmthin(7)`: **"Any content that was unique to the origin thin LV is lost after the merge."** |

> **「戻せる」ことに安心して、スナップショットの容量監視を怠るのが最悪のパターン**です。
> **無効になったスナップショットは、戻すこともバックアップすることもできません。**

---

## スナップショットの容量を切らさない

**スナップショットが壊れる原因はほぼ 1 つ——領域を使い切ること**です。
**ここを防ぐ方法が 3 つあります。**

### ① 使用率を監視する

```bash
$ sudo lvs -o lv_name,origin,lv_size,data_percent   # スナップショットの使用率を見る
$ watch -n 60 'sudo lvs -o lv_name,data_percent'    # 作業中は1分おきに見張る
```

**`Data%` が 100 に達した時点で無効になります。**
**Red Hat の公式ドキュメント（RHEL 9）に
"If a snapshot reaches 100% of its allocated space, it becomes invalid." とあります。**

**無効になると何が起きるか**

| | どうなるか |
|:--|:--|
| **スナップショット** | **使えなくなる**。RHEL 6 のドキュメントには "A snapshot that is 100% full is lost completely" とあり、**そのスナップショットをマウントしていた場合は強制的にアンマウントされる** |
| **元の LV** | **公式ドキュメントに明記がありません。** 実運用では「元は無事」と言われていますが、**公式では確認できていません** |

> **「元の LV は無事」は二次情報です。**
> **本番で確かめるものではないので、そもそも使い切らせない**のが答えです。

### ② 自動拡張を有効にする

**`lvm.conf` の 2 つの設定で、しきい値を超えたら自動で広げられます。**

| 設定 | 既定値 | 意味 |
|:--|:--|:--|
| **`snapshot_autoextend_threshold`** | **`100`** | **何 % を超えたら拡張するか。`100` は「拡張しない」** |
| **`snapshot_autoextend_percent`** | **`20`** | **1 回で何 % 広げるか** |

**既定では自動拡張は無効**です（手元の LVM 2.03.16 の `lvm dumpconfig --type default` で確認）。

```bash
$ sudo lvmconfig activation/snapshot_autoextend_threshold   # いまの設定を確認する
$ sudo lvmconfig activation/snapshot_autoextend_percent     # 同じく確認する
```

**有効にするには `/etc/lvm/lvm.conf` の `activation` セクションを編集します。**

```text
activation {
    snapshot_autoextend_threshold = 70
    snapshot_autoextend_percent = 20
}
```

```bash
$ sudo systemctl restart lvm2-monitor   # 設定を反映させる
$ systemctl status lvm2-monitor         # 監視が動いているか確認する
```

```text
  threshold 70 / percent 20 で、1GB のスナップショットを作った場合

  700MB を超えた    → 1GB の 20% ＝ 200MB 足して 1.2GB になる
  840MB を超えた    → さらに 20% 足される
      ▲ VG に空きがある限り繰り返される
```

| 注意点 | 内容 |
|:--|:--|
| **`dmeventd` の監視が必要** | `lvm.conf` の説明に **"Automatic extension requires dmeventd to be monitoring the LV."** とある。RHEL では **`lvm2-monitor.service`** |
| **VG に空きが必要** | RHEL 6 のドキュメントに **"This feature requires that there be unallocated space in the volume group."** |
| **`threshold` の最小値は 50** | **"The minimum value is 50 (a smaller value is treated as 50.)"**（`percent` ではなく `threshold` の話） |
| **元 LV と同じ大きさまで育つと監視対象から外れる** | RHEL 6 のドキュメントにその記述がある |

> **自動拡張は保険です。**
> **「VG に空きが無ければ広げられない」**ので、
> **`-l 100%FREE` で LV を作ってしまうと保険が効きません。**
> **スナップショットを使う VG では、必ず空きを残しておく**ことがここで効いてきます。

### ③ シンプロビジョニングのスナップショットを使う

**従来の COW スナップショットと、シン（thin）スナップショットは別の仕組み**です。

| | **COW スナップショット**（`lvcreate -s -L ...`） | **シンスナップショット**（thin LV に対する `lvcreate -s`） |
|:--|:--|:--|
| **容量の事前確保** | **必要**（`-L` で指定する） | **不要** |
| **使い切ると** | **無効になる** | **プールが尽きるまでは問題にならない**（尽きたときは下記） |
| **スナップショットのスナップショット** | **取れない** | **取れる** |
| **元 LV の種別** | 通常の LV | **シン LV である必要がある** |

**`lvmthin(7)` にこうあります。**

> - "Snapshots may be taken of thin LVs or of other thin snapshots."
> - "There is no limit to or degradation from sequences of snapshots."

```bash
$ sudo lvcreate --type thin-pool -L 500G -n pool0 vg_data   # シンプールを作る
$ sudo lvcreate --type thin -V 200G --thinpool pool0 -n lv_data vg_data   # シン LV を作る
$ sudo lvcreate -s -n snap0 vg_data/lv_data                 # サイズ指定なしでスナップショット
$ sudo lvchange -ay -K vg_data/snap0                        # 有効化する（-K が必要）
$ sudo lvs -o lv_name,lv_attr,data_percent,pool_lv          # プールと LV の使用率を見る
```

> **シンスナップショットは作成直後はアクティブになりません。**
> **`lvs` の `Attr` の 10 桁目が `k`（activation skip）になり、
> `lvchange -ay -K`（`-K` は `--ignoreactivationskip`）を付けないと有効化されません**
> （`lvmthin(7)`）。
> **「作ったのにデバイスファイルが無い」のはこれ**です。

> **スナップショットの種類は元 LV の種類で決まります。**
> Red Hat の公式ドキュメントに **"If your original LV is thin, your snapshots will be thin."** とあります。
> **シン LV に `-s -L サイズ` と書くと、従来の COW スナップショットになります。**
>
> **シンプールにも同じ自動拡張の設定があります**
> （`thin_pool_autoextend_threshold` / `thin_pool_autoextend_percent`、
> 既定はどちらも `100` / `20`。手元の LVM 2.03.16 で確認）。
>
> **プールを使い切ると、新しいブロックの割り当てが必要な書き込みが最大 60 秒キューされ、
> その後エラーになります**（`lvmthin(7)`。`--errorwhenfull` と `no_space_timeout` で挙動を変えられます）。
> **プールの上に乗っている全 LV が影響を受ける**ので、
> **COW スナップショット以上に監視が要ります。**
>
> ```bash
> $ sudo lvs -o lv_name,lv_attr,data_percent,metadata_percent   # プールの使用率とメタデータ使用率
> ```
>
> **`metadata_percent` も見てください。**
> **データ領域に空きがあっても、メタデータが満杯になればプールは止まります。**

---

## 設定ファイル lvm.conf

**システム起動時にどの物理ブロックデバイスを LVM ボリュームとして検索対象とするかを、
正規表現を用いて、指定することができます。**

**ボリューム検索には `vgscan` という VG を検索するコマンドが動作しますが、
これに対するフィルタを `lvm.conf` に記載することになります。**

```bash
$ ls -l /etc/lvm/lvm.conf              # 実機での場所（確認済み）
-rw-r--r-- 1 root root 111692 Nov 27  2024 /etc/lvm/lvm.conf
```

| 名前 | 何か |
|:--|:--|
| **`lvm.conf`** | **設定ファイル**（これが正解） |
| **`/etc/lvm`** | **`lvm.conf` のあるデフォルトのディレクトリ** |
| `vgscan.conf` / `pvscan.conf` | **このような設定ファイルはありません** |

**filter の書き方**

```text
filter = [ "a|/dev/hd.*|", "r|.*|" ]
```

**この例は、全ての IDE デバイスを検索し、それ以外のブロックデバイスを除外します。**

| 記号 | 意味 |
|:--|:--|
| **`a`** | **accept（検索対象にする）** |
| **`r`** | **reject（除外する）** |
| **`\|` で囲む** | 正規表現の区切り（`/` でも書ける） |

**実機の `lvm.conf` にあるコメント例**

```text
	# filter = [ "a|.*|" ]                                   全部を対象にする
	# filter = [ "r|/dev/cdrom|" ]                           CD-ROM だけ除外する
	# filter = [ "a|loop|", "r|.*|" ]                        loop だけ対象にする
```

**上から順に評価され、最初にマッチしたルールが適用されます。**
**最後に `"r|.*|"` を置いて「それ以外は全部除外」**とするのが定石です。

**いつ使うか**

| 場面 | 理由 |
|:--|:--|
| **マルチパス環境** | **同じディスクが複数の経路で見えるので、片方だけを対象にする** |
| **iSCSI を使っている** | **起動時にまだ繋がっていないデバイスをスキャンさせない** |
| **スキャンが遅い** | 対象を絞ると起動が速くなる |

```bash
$ sudo vgscan                          # 設定を変えたらスキャンし直す
$ sudo pvscan                          # PV の一覧を再取得する
```

---

## 参考リンク

- [man 8 lvextend](https://man7.org/linux/man-pages/man8/lvextend.8.html)
- [man 8 lvreduce](https://man7.org/linux/man-pages/man8/lvreduce.8.html)
- [man 8 lvremove](https://man7.org/linux/man-pages/man8/lvremove.8.html)
- [man 8 vgreduce](https://man7.org/linux/man-pages/man8/vgreduce.8.html)
- [man 8 resize2fs](https://man7.org/linux/man-pages/man8/resize2fs.8.html)
- [man 5 lvm.conf](https://man7.org/linux/man-pages/man5/lvm.conf.5.html)
- [man 8 lvs](https://man7.org/linux/man-pages/man8/lvs.8.html)
- [man 8 lvconvert](https://man7.org/linux/man-pages/man8/lvconvert.8.html)
- [man 8 vgcfgrestore](https://man7.org/linux/man-pages/man8/vgcfgrestore.8.html)
- [man 7 lvmthin](https://man7.org/linux/man-pages/man7/lvmthin.7.html)
- [Red Hat — Advanced logical volume management (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_logical_volumes/advanced-logical-volume-management_configuring-and-managing-logical-volumes)
- [Red Hat — Overview of available file systems (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_file_systems/overview-of-available-file-systems_managing-file-systems)
- [Red Hat — Troubleshooting LVM (RHEL 8)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/configuring_and_managing_logical_volumes/troubleshooting-lvm_configuring-and-managing-logical-volumes)
