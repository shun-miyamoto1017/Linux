# LVM_サイズ変更とスナップショット

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — 論理ボリュームマネージャの設定と管理 |
| **業務での使いどころ** | **「`/var` が溢れた」への即応。**`lvextend -r` で止めずに広げる。縮小とスナップショットは手順を間違えるとデータが消えるので、順番を身体で覚えておく |

> **このノートは作ったあとの LVM**（サイズ変更・削除・スナップショット・設定ファイル）です。
> **PV / VG / LV の考え方と作り方**は
> [LVM_論理ボリュームの管理](./LVM_論理ボリュームの管理.md)、
> **ファイルシステムのリサイズそのもの**は
> [ファイルシステム別ユーティリティ](./ファイルシステム別ユーティリティ.md) にあります。

---

## 目次

- [まずこれだけ](#まずこれだけ)
- [サイズを変える](#サイズを変える)
  - [lvextend 増やす](#lvextend-増やす)
  - [lvreduce 減らす](#lvreduce-減らす)
- [削除する remove系とreduce系](#削除する-remove系とreduce系)
- [スナップショット](#スナップショット)
- [設定ファイル lvm.conf](#設定ファイル-lvmconf)
- [つまずきポイント](#つまずきポイント)
- [クラウド実務メモ](#クラウド実務メモ)
- [参考リンク](#参考リンク)

---

## まずこれだけ

| やりたいこと | コマンド |
|:--|:--|
| **LV を増やす** | **`lvextend -L +1G /dev/vg1/lv1`** |
| **LV を減らす** | **`lvreduce -L -1G /dev/vg1/lv1`** |
| **LV を消す** | **`lvremove /dev/vg1/lv1`** |
| **VG そのものを消す** | **`vgremove vg1`** |
| **VG から PV を外す** | **`vgreduce vg1 /dev/sdc1`** |
| **PV の印を消す** | **`pvremove /dev/sdc1`** |
| **VG に PV を足す** | **`vgextend vg1 /dev/sdd1`** |
| **スナップショットを作る** | **`lvcreate -s -L 1024M -n sn /dev/vg1/lv1`** |

**押さえる 3 点**

| 論点 | 結論 |
|:--|:--|
| **`remove` と `reduce`** | **`remove` はそのものを消す、`reduce` は中身を減らす**。`vgremove` は VG を消す、`vgreduce` は VG から PV を外す |
| **`extend` と `expand`** | **正しいのは `extend`**。`lvexpand` / `vgexpand` / `pvexpand` は**存在しない** |
| **`lvreduce` の注意** | **先にファイルシステムを縮小しておく**。忘れるとデータが壊れる |

**サイズ変更の向きと順番**

```text
  増やす   LV を広げる  →  ファイルシステムを広げる      （lvextend → resize2fs）
  減らす   ファイルシステムを縮める  →  LV を縮める      （resize2fs → lvreduce）
             ▲ 向きによって順番が逆になる。ここが最大のつまずきどころ
```

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

**`+` の有無で意味がまったく変わります。**

```text
  -L +1G    いまが 3G なら → 4G になる     （相対）
  -L 1G     いまが 3G なら → 1G になる     （絶対・縮小してしまう）
```

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
| **XFS** | **`xfs_growfs`** | **できる**（マウント必須） |
| Btrfs | `btrfs filesystem resize` | できる |

**`lvextend -r` で両方まとめて**

```bash
$ sudo lvextend -r -L +1G /dev/vg1/lv1   # -r でファイルシステムも自動でリサイズする
```

**`-r`（`--resizefs`）を付けるのが実務では定番**です。忘れる事故が防げます。

### lvreduce 減らす

**論理ボリューム（LV）を縮小するコマンドは `lvreduce` です。**
**元のサイズ以下の任意のサイズに領域を縮小することができます。**
**また、その際にアンマウントやシステムの再起動は必要ありません。**

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

**ext2/ext3/ext4 であれば `resize2fs`、ReiserFS であれば `resize_reiserfs` を利用して、
事前に縮小後の LV サイズに合わせてファイルシステムも縮小しておく必要があります。**

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
| **整合性のあるバックアップを取る** | **スナップショットを取ってから、そちらをバックアップする**。元の LV は止めなくてよい |
| **更新前に戻せるようにする** | 作業前にスナップショットを取り、失敗したら `lvconvert --merge` で戻す |

```bash
$ sudo lvcreate -s -L 5G -n snap /dev/vg1/data   # ① スナップショットを取る
$ sudo mount -o ro /dev/vg1/snap /mnt/snap       # ② 読み込み専用でマウントする
$ tar czf /backup/data.tar.gz -C /mnt/snap .     # ③ こちらからバックアップする
$ sudo umount /mnt/snap && sudo lvremove /dev/vg1/snap   # ④ 済んだら消す
```

**スナップショットの容量に注意**

**スナップショットは「元の LV が変更された分」を貯めていきます。**
**確保した容量を使い切ると、スナップショットは無効になります。**

```bash
$ sudo lvs                             # Data% が 100% に近づいたら危ない
  LV    VG   Attr       LSize  Pool Origin Data%
  snap  vg1  swi-a-s---  5.00g      data    23.45
```

**元の LV の更新量を見積もって、余裕を持った容量**を確保します。

> **Btrfs のスナップショットとは仕組みが違います。**
> **LVM は「変更分を別領域に退避する」方式**で、**容量を先に確保**します。
> Btrfs は CoW なので事前確保が要りません
> （[Btrfsとサブボリューム](./Btrfsとサブボリューム.md)）。

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

## つまずきポイント

| 症状 | 原因 | 対処 |
|:--|:--|:--|
| **`lvextend` したのに `df` が増えない** | **ファイルシステムを広げていない** | **`resize2fs`** を実行する。または `lvextend -r` |
| **`lvreduce` したらデータが壊れた** | **先にファイルシステムを縮めていない** | **必ず `resize2fs` → `lvreduce` の順**。バックアップを取ってから |
| **XFS を縮小しようとした** | **XFS は縮小できない** | 作り直すしかない。縮小の可能性があるなら ext4 を選ぶ |
| **`lvexpand` が `command not found`** | **`expand` ではなく `extend`** | **`lvextend`** |
| **`pvremove` で VG から PV を外そうとした** | **それは `vgreduce`** | **`vgreduce vg1 /dev/sdc1`** |
| **`-L 1G` で縮んでしまった** | **`+` を忘れた** | **`-L +1G`** と書く |
| **`Insufficient free space`** | **VG に空きが無い** | **`vgdisplay` の `Free PE` を確認**する。`vgextend` で PV を足す |
| **スナップショットが無効になった** | **確保した容量を使い切った** | もっと大きく確保する。使い終わったら早めに消す |
| **`vgremove` できない** | **中に LV が残っている** | **先に `lvremove`** |
| **起動時に VG が見つからない** | **`lvm.conf` の filter で除外されている** | **filter を確認**する |

---

## クラウド実務メモ

**① スナップショットは EBS スナップショットと役割が違う**

| | **LVM スナップショット** | **EBS スナップショット** |
|:--|:--|:--|
| **どこに保存されるか** | **同じ VG の中** | **S3（別の場所）** |
| **ディスクが壊れたら** | **一緒に消える** | **残る** |
| **向いている用途** | **整合性のあるバックアップを取るための一時停止点** | **災害対策・別リージョンへの複製** |

**LVM スナップショットはバックアップそのものではありません。**
**「静止点を作る」ための道具**であって、**そこから EBS スナップショットや `tar` で外へ出す**のが正しい使い方です。

```bash
$ sudo lvcreate -s -L 5G -n snap /dev/vg_data/lv_data   # ① 静止点を作る
$ sudo mount -o ro /dev/vg_data/snap /mnt/snap          # ② 読み取り専用で開く
$ aws s3 sync /mnt/snap s3://backup-bucket/data/        # ③ 外へ出す
$ sudo umount /mnt/snap && sudo lvremove -f /dev/vg_data/snap   # ④ 片付ける
```

**② Terraform / Ansible では冪等性に気を付ける**

**`pvcreate` や `vgcreate` は 2 回目でエラーになります。**

```yaml
- name: 物理ボリュームとボリュームグループを作る（冪等）
  community.general.lvg:
    vg: vg_data
    pvs: /dev/nvme1n1,/dev/nvme2n1       # このモジュールは冪等に動く

- name: 論理ボリュームを作る／広げる（冪等）
  community.general.lvol:
    vg: vg_data
    lv: lv_data
    size: 100%FREE
    resizefs: true                        # ファイルシステムも一緒にリサイズする
```

**`command` モジュールで生コマンドを叩くより、専用モジュールを使う**ほうが安全です。
**`resizefs: true` を忘れない**のがここでも効いてきます。

**③ 監視は VG の空きを見る**

```bash
$ sudo vgs --units g --noheadings -o vg_name,vg_free   # VG の空きを取り出す
  vg_data 12.00g
```

**LV が満杯になる前に、VG の空きが尽きるほうが先に困ります。**
**「VG の空きが 10% を切ったらアラート」**を仕込んでおくと、増設の判断が間に合います。

---

## 参考リンク

- [man 8 lvextend](https://man7.org/linux/man-pages/man8/lvextend.8.html)
- [man 8 lvreduce](https://man7.org/linux/man-pages/man8/lvreduce.8.html)
- [man 8 lvremove](https://man7.org/linux/man-pages/man8/lvremove.8.html)
- [man 8 vgreduce](https://man7.org/linux/man-pages/man8/vgreduce.8.html)
- [man 8 resize2fs](https://man7.org/linux/man-pages/man8/resize2fs.8.html)
- [man 5 lvm.conf](https://man7.org/linux/man-pages/man5/lvm.conf.5.html)
