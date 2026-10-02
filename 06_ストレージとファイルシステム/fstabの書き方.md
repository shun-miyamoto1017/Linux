# fstabの書き方

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / デバイス、Linuxファイルシステム、FHS(主題104) — ファイルシステムのマウントとアンマウント |
| **業務での使いどころ** | EBS / EFS の追加、ディスク増設時の恒久設定。**書き間違えると起動しなくなる**ので、業務で最も慎重さが要る設定ファイルのひとつ |

> **このノートは `/etc/fstab` という 1 つのファイルだけを扱います。**
> `mount` / `umount` コマンドそのものは [マウントとアンマウント](./マウントとアンマウント.md)、
> ファイルシステムを**作る**側（`mkfs`・ext4 / XFS の選定）は [ファイルシステムの種類と作成](./ファイルシステムの種類と作成.md)、
> スワップの行（`swap` / `mkswap` / `swapon`）は [スワップ領域](./スワップ領域.md) にあります。

---

## 目次

- [fstab は何のためにあるか](#fstab-は何のためにあるか)
- [6つの設定項目](#6つの設定項目)
- [1つ目 デバイス名の3つの書き方](#1つ目-デバイス名の3つの書き方)
  - [UUIDとラベルの調べ方](#uuidとラベルの調べ方)
- [3つ目 ファイルシステムの種類](#3つ目-ファイルシステムの種類)
- [4つ目 マウントオプション](#4つ目-マウントオプション)
- [1行を読み解く](#1行を読み解く)
  - [例1 defaults だけの行](#例1-defaults-だけの行)
  - [例2 オプションを重ねた行](#例2-オプションを重ねた行)
  - [例3 defaults を上書きした行](#例3-defaults-を上書きした行)
- [起動時に自動マウントする条件](#起動時に自動マウントする条件)
- [書き間違いから身を守る](#書き間違いから身を守る)
- [一般ユーザにマウントさせる](#一般ユーザにマウントさせる)
- [クラウドでのfstab設計](#クラウドでのfstab設計)
- [参考リンク](#参考リンク)

---

## fstab は何のためにあるか

**`/etc/fstab` は、利用するファイルシステムのマウント設定を事前に行っておく設定ファイル**です。
`mount` コマンドはこのファイルの設定内容を参照して動作します。

**このファイルがあると、2 つのことができるようになります。**

| できること | 具体的には |
|:--|:--|
| **起動時に自動でマウントされる** | システムは起動時に `mount -a` を実行し、`auto` が設定されたものをすべてマウントする |
| **短い指定でマウントできる** | `mount /mnt/usb` のように**マウントポイントだけ**で済む（デバイス名は fstab から引かれる） |

```bash
$ sudo mount /dev/sdb1 /data         # fstab に書いていない場合は両方を指定する
$ sudo mount /data                   # fstab に書いてあれば、これだけで済む
```

**補足 … `mount` コマンドだけの設定は、再起動で消えます**

`mount` コマンドは**その場でつなぐだけ**です。恒久的にしたいなら `/etc/fstab` に書きます。
「ディスクを追加したのに再起動したら消えた」は、ほぼこの書き忘れです。

---

## 6つの設定項目

**`/etc/fstab` の設定項目は 6 つ**で、空白（スペースまたはタブ）で区切って 1 行に書きます。

```bash
$ cat /etc/fstab                     # 設定内容を確認する
LABEL=/         /          ext3    defaults    1 1
LABEL=/boot     /boot      ext3    defaults    1 2
none            /proc      proc    defaults    0 0
none            /dev/shm   tmpfs   defaults    0 0
/dev/hda4       swap       swap    defaults    0 0
   (1)           (2)        (3)      (4)      (5)(6)
```

| # | 項目 | 内容 |
|:-:|:--|:--|
| **(1)** | **デバイス名** | `/dev/sda1` のようなデバイスファイル、`LABEL=`、`UUID=` のいずれか |
| **(2)** | **マウントポイント** | どのディレクトリに繋ぐか。スワップの場合は `swap` |
| **(3)** | **ファイルシステムの種類** | `ext4` / `xfs` / `iso9660` / `vfat` / `swap` / `proc` / `tmpfs` など |
| **(4)** | **マウントオプション** | `defaults` / `noauto` / `ro` / `users` などをカンマ区切りで |
| **(5)** | **dump フラグ** | `dump` コマンドのバックアップ対象にするか。`0`＝しない、`1`＝する |
| **(6)** | **fsck フラグ** | 起動時のファイルシステムチェックの順番。`0`＝しない、`1`＝最初（ルート）、`2`＝その後 |

**(5) と (6) の実務での扱い**

- **dump フラグ** … 現在 `dump` コマンドはほとんど使われないため、**`0` が普通**です
- **fsck フラグ** … ルートファイルシステムに `1`、それ以外に `2`、チェック不要なもの（ネットワークファイルシステムや `tmpfs`）に `0` を書きます。**同じ数字のものは並行してチェック**されます

**補足 … デバイス名に `none` と書く行がある**

`proc` や `tmpfs` のように**実体のディスクを持たないファイルシステム**は、
1 つ目に指定するものがありません。慣習として **`none`** と書きます。

**並び順を取り違えない**

**いちばん紛らわしいのは先頭の 2 つ**です。

```text
  ○ デバイス   マウント先   種類   オプション   dump   fsck
  ✕ マウント先 デバイス     種類   オプション   dump   fsck    ← 逆
  ✕ デバイス   マウント先   種類   オプション   fsck   dump    ← 末尾2つが逆
```

**「一番左がデバイス、二番目がマウント先」**——ここを固定して覚えます。
**末尾は dump が先、fsck が後**です。

```text
/dev/sda2 /root ext2 defaults 1 0
    │       │     │     │     │ └─ fsck フラグ … 0 なので起動時のチェック対象にならない
    │       │     │     │     └─── dump フラグ … 1 なので dump の対象になる
    │       │     │     └───────── オプション
    │       │     └─────────────── 種類（ext2 形式のファイルシステムがある）
    │       └───────────────────── マウント先（/root に繋いで使う）
    └───────────────────────────── デバイス
```

**`fsck` フラグの 0 は「最初」ではなく「やらない」**

| 値 | 意味 |
|:--|:--|
| **`0`** | **例外。チェックを省く**（マウント時に `fsck` の対象とならない） |
| **`1`** | **最初にチェックする**。ルートファイルシステムに付ける |
| `2` | 1 のあとにチェックする |

**数字が小さいものから順にチェックされますが、`0` だけは例外で「チェックしない」**という指定です。
**「0 なので最初にチェックされる」は誤り**で、ここが繰り返し問われます。

**エントリの順番にも意味がある**

**`mount` コマンドは `/etc/fstab` の先頭のエントリから順に設定記述を参照して動作します。**
そのため、**`/`（ルートディレクトリ）は最初の方に記述する**など、**エントリの順番が重要**です。

---

## 1つ目 デバイス名の3つの書き方

**1 つ目の項目にはデバイス名を指定します。** 書き方は 3 通りあります。

| 書き方 | 例 | 特徴 |
|:--|:--|:--|
| **デバイスファイル** | `/dev/sda1` | 直接的。ただし**接続順で名前が変わることがある** |
| **ラベル** | `LABEL=/boot` | あらかじめファイルシステムに付けておいた名前で指定 |
| **UUID** | `UUID=3b80b96c-df15-401e-b74c-e8dcbfb68cec` | **推奨**。全世界で重複しない一意の値 |

```text
/dev/sda1                                        ← デバイスファイルをそのまま書く
LABEL=/boot                                      ← LABEL= の後ろにラベル名を書く
UUID=3b80b96c-df15-401e-b74c-e8dcbfb68cec        ← UUID= の後ろに UUID 文字列を書く
```

**`defaults` や `ext3` は 1 つ目には書けません。** これらはそれぞれ 4 つ目・3 つ目の項目です。

**なぜ UUID が推奨されるのか**

USB メモリや増設ディスクのように**外付けのドライブを接続する際、接続する順番や環境によって
`/dev` ディレクトリ配下のどのデバイスファイルとしてマウントされるのかが定まっていません**。

```text
1回目に挿したとき … /dev/sdb1
2回目に挿したとき … /dev/sdc1   ← 名前が変わってしまった
```

`/etc/fstab` に `/dev/sdb1` と書いてあると、名前が変わった瞬間に
**起動時のマウントが失敗して、システムが上がらなくなる**ことがあります。
UUID はファイルシステムに紐づいた値なので、**どのデバイス名になっても変わりません**。

### UUIDとラベルの調べ方

**UUID は `blkid` コマンドや `lsblk` コマンドで確認できます。**

```bash
$ sudo blkid                         # 全デバイスの UUID・ラベル・種類を表示する
/dev/sda1: LABEL="TRANSCEND" UUID="0898-00BA" TYPE="vfat"

$ sudo blkid /dev/sdb1               # 特定のデバイスだけ調べる
/dev/sdb1: LABEL="TESTLABEL" UUID="b7be915b-083c-4dd0-872f-adc6c47a1f76" TYPE="ext4"

$ sudo blkid -s UUID -o value /dev/sdb1   # UUID の値だけを取り出す（スクリプト向け）
b7be915b-083c-4dd0-872f-adc6c47a1f76

$ lsblk -f                           # ツリー表示で種類・ラベル・UUID・マウント先を見る
NAME   FSTYPE LABEL     UUID                                 MOUNTPOINTS
sdb
└─sdb1 ext4   TESTLABEL b7be915b-083c-4dd0-872f-adc6c47a1f76 /data
```

**UUID を表示できるのは `blkid` と `lsblk` の 2 つ**です。
`mount` や `ps` では表示できませんし、`showblk` というコマンドは**存在しません**。

**もう 1 つの調べ方 … `/dev/disk/by-uuid`**

**udev が自動生成する `/dev/disk/by-uuid` を見ることでも UUID を確認できます。**
**コマンドではなくディレクトリ**なので、`ls` で見ます。

```bash
$ ls -l /dev/disk/by-uuid                        # UUID から実デバイスへのシンボリックリンクを見る
合計 0
lrwxrwxrwx. 1 root root 10 12月  2 14:38 01103e70-d67c-4505-b1e4-9638eee106a9 -> ../../dm-0
lrwxrwxrwx. 1 root root 10 12月  2 14:38 4f1e50d8-1c12-4290-94c0-ee9c3d721500 -> ../../dm-1
lrwxrwxrwx. 1 root root 10 12月  2 14:38 5aa92267-4a0c-4420-8ad9-40407055f0de -> ../../sda1
```

**ファイル名が UUID、リンク先が実デバイス**です。
**UUID からデバイスを逆引きしたいとき**はこちらが早くなります。

| 調べ方 | 形 | 向いている場面 |
|:--|:--|:--|
| **`blkid`** | コマンド | **デバイス → UUID** を引きたいとき |
| `lsblk -f` | コマンド | **親子関係も一緒に**見たいとき |
| **`/dev/disk/by-uuid`** | **ディレクトリ** | **UUID → デバイス**を引きたいとき |

**まぎらわしい誤りに注意**

| 見かける書き方 | 実際は |
|:--|:--|
| `/etc/udev/by-uuid` | **存在しない**（`/dev/disk/by-uuid` が正しい） |
| `/proc/sys/by-uuid` | **存在しない** |
| `uuid_info` コマンド | **存在しないコマンド** |
| `mount` コマンドで確認する | **UUID は表示されない** |

**補足 … `/dev/disk/` の下には by-uuid 以外もあります**

```bash
$ ls /dev/disk/                                  # udev が作る逆引き用のディレクトリ群
by-id  by-label  by-partuuid  by-path  by-uuid
```

| ディレクトリ | 何で引けるか |
|:--|:--|
| `by-uuid` | **ファイルシステムの UUID** |
| `by-label` | **ラベル** |
| `by-id` | ディスクのシリアル番号など、装置固有の識別子 |
| `by-path` | 接続経路（どのポートに挿さっているか） |
| `by-partuuid` | **パーティション**の UUID（GPT） |

udev の仕組みは [ハードウェアの確認とudev](../05_起動プロセスとカーネル/ハードウェアの確認とudev.md) にあります。

**ラベルの付け方**

**ラベルは、事前に `tune2fs` コマンドや `e2label` コマンドでファイルシステムに対して付けておく名前**です。

```bash
$ sudo e2label /dev/sdb1 myboot                  # ext系にラベルを付ける
$ sudo tune2fs -L myboot /dev/sdb1               # tune2fs でも同じことができる
$ sudo e2label /dev/sdb1                         # 付いているラベルを確認する
myboot
```

```bash
$ sudo xfs_admin -L myboot /dev/sdb1             # XFS の場合は専用コマンドを使う
```

**`LABEL=myboot` と書けば、このラベルで `/etc/fstab` から指定できます。**

**`blkid` … ブロックデバイスの情報を表示する**

**`blkid` はブロックデバイス（HDD や CD-ROM などのように
ブロック単位でデータを転送するデバイス）の情報を表示するコマンド**です。
**デバイス名や、UUID、ファイルシステムのタイプを表示できます。**

```bash
$ sudo blkid                         # すべてのブロックデバイスを一覧する
/dev/sda1: UUID="52abae61-09b5-4093-b66a-e2812fb964fc" TYPE="ext4"
/dev/sda2: UUID="a9L13h-NOmX-RAj4-g82D-kVAy-nxqr-RCO6Ac" TYPE="LVM2_member"
/dev/mapper/vg_server1-lv_root: UUID="7ee5e8bb-240c-4c15-9d4c-80350c934f2f" TYPE="ext4"
/dev/mapper/vg_server1-lv_swap: UUID="2be3b09a-a5f4-4995-9fce-8913b4e81876" TYPE="swap"
```

`TYPE="LVM2_member"` は「このパーティションは LVM の部品として使われている」という意味で、
`TYPE="swap"` はスワップ領域です（[スワップ領域](./スワップ領域.md) 参照）。

**`lsblk` … ブロックデバイスをツリー状に一覧する**

**`lsblk` はブロックデバイスをツリー状に一覧表示するコマンド**です。
**`--output` オプションで表示項目を指定することによって、UUID やファイルシステムのタイプを表示できます。**

```bash
$ lsblk --output NAME,UUID,FSTYPE    # 表示する項目を自分で選ぶ
NAME                            UUID                                   FSTYPE
sr0
sda
├─sda1                          52abae61-09b5-4093-b66a-e2812fb964fc   ext4
└─sda2                          a9L13h-NOmX-RAj4-g82D-kVAy-nxqr-RCO6Ac LVM2_member
  ├─vg_server1-lv_root (dm-0)   7ee5e8bb-240c-4c15-9d4c-80350c934f2f   ext4
  └─vg_server1-lv_swap (dm-1)   2be3b09a-a5f4-4995-9fce-8913b4e81876   swap
```

**ツリー表示なので「どのディスクの、どのパーティションか」という親子関係が一目で分かります。**
LVM を使っていると階層が深くなるので、`blkid` の平坦な一覧より読みやすくなります。

`--output` は `-o` と短く書けます。`lsblk -f` は
`--output NAME,FSTYPE,LABEL,UUID,MOUNTPOINTS` を指定したのとほぼ同じ意味の近道です。

**使い分け**

| | `blkid` | `lsblk` |
|:--|:--|:--|
| 表示の形 | **平坦な一覧** | **ツリー** |
| 親子関係 | 分からない | **分かる** |
| 値だけ取り出す | **得意**（`-s UUID -o value`） | やや面倒 |
| 一部のディストリで root 権限 | **必要なことがある** | 不要 |
| 主な用途 | **スクリプトで UUID を取る** | **人が構成を眺める** |

**書き込むときの定番**

```bash
$ echo "UUID=$(sudo blkid -s UUID -o value /dev/sdb1) /data xfs defaults 0 0" | sudo tee -a /etc/fstab   # UUID を自動で埋め込んで追記する
```

手で UUID を打ち込むと**タイプミスで起動しなくなる**ため、コマンドで埋め込むのが安全です。

---

## 3つ目 ファイルシステムの種類

**3 つ目にはデバイス部で指定したファイルシステムの種類を書きます。**
**名前と概要をセットで覚えておくべきもの**を並べます。

| 種類 | 概要 |
|:--|:--|
| **`ext2`** | **Linux で標準的に使われる**（ジャーナリング機能は無い） |
| **`ext3`** | **`ext2` にジャーナリング機能を加えたもの** |
| **`ext4`** | **`ext3` の後継。大容量（1EiB）のファイルシステムをサポート** |
| **`btrfs`** | 比較的新しい Linux のファイルシステム。**サブボリュームを構成しスナップショットなどの機能を持つ** |
| **`xfs`** | **古くからあり、ジャーナリング機能を持つ** |
| **`iso9660`** | **CD-ROM で使われる** |
| **`FAT` / `vfat`** | **フラッシュメモリ等で使われる**。Windows では古いファイルシステム。**UEFI のシステムパーティション（ESP）や ISOLINUX のイメージでも使われている** |
| **`ntfs`** | **近年の Windows で使われる** |
| **`nfs`** | **ネットワークファイルシステム** |
| **`tmpfs`** | **メモリ上に配置（RAM ディスク）** |
| **`swap`** | **物理メモリのスワップ先** |
| **`ZFS`** | **Oracle の Solaris で使用**。**`btrfs` が参考としたファイルシステム** |

**それぞれの詳しい説明と選び方**は
[ファイルシステムの種類と作成](./ファイルシステムの種類と作成.md) にまとめています。

---

## 4つ目 マウントオプション

主なマウントオプションは以下のとおりです。カンマ区切りで複数指定できます。

| オプション | 説明 |
|:--|:--|
| `async` | 非同期で入出力を行う |
| **`auto`** | **`mount -a` コマンド実行時にマウント** |
| **`noauto`** | **`mount -a` コマンド実行時にマウントしない** |
| **`defaults`** | **デフォルト指定**（`async, auto, dev, exec, nouser, rw, suid`） |
| `exec` | バイナリの実行を許可 |
| `noexec` | バイナリの実行を禁止 |
| `ro` | 読み取り専用 |
| `rw` | 読み書きを許可 |
| **`suid`** | **SUID と SGID を有効化** |
| `nosuid` | SUID と SGID を無効化 |
| `dev` | デバイスファイルを有効にする |
| `nodev` | デバイスファイルを無効にする |
| **`user`** | **一般ユーザでマウント可、本人のみアンマウント可** |
| **`users`** | **一般ユーザでマウント可、誰でもアンマウント可** |
| `nouser` | 一般ユーザによるマウントを禁止 |
| **`uid=ユーザ`** | **マウントしたファイルシステム上のファイルの所有者を指定する** |
| `gid=グループ` | 同じく所有グループを指定する |
| `umask=値` | ファイルやディレクトリ新規作成時のデフォルトのパーミッション |
| `noatime` / `relatime` | アクセス時刻の更新を抑制する |
| `nofail` | **そのデバイスが無くても起動を止めない** |
| `_netdev` | **ネットワークが上がってからマウントする**（NFS / EFS など） |

**`defaults` の中身を覚えておく**

```text
defaults = async + auto + dev + exec + nouser + rw + suid
```

この 7 つが一度に指定されたことになります。**`auto` が含まれている**点が重要で、
これが「`defaults` でも起動時に自動マウントされる」理由です。

**SUID / SGID を有効化するオプションは `suid` です。**
`exec`（バイナリの実行許可）とは別物なので混同しないようにします。

| 紛らわしい組 | 違い |
|:--|:--|
| `suid` / `exec` | `suid` は**特殊パーミッションの有効化**、`exec` は**実行そのものの許可** |
| `user` / `users` | アンマウントできるのが**本人だけ**か**誰でも**か |
| `nouser` / `nosuid` | `nouser` は**マウントの禁止**、`nosuid` は**SUID の無効化** |

SUID / SGID そのものについては
[03_ユーザ管理とパーミッション / SGID_特殊パーミッション](../03_ユーザ管理とパーミッション/SGID_特殊パーミッション.md) を参照してください。

**`uid=` は FAT / NTFS のためにある**

**`uid=` は、FAT・NTFS など、Linux で使われる管理情報を保持できないファイルシステムで使います。**

**FAT32 は Win9x 系のファイルシステムで、ユーザによる管理や権限を付加する概念がほとんどなく、
Linux の管理情報（所有者・パーミッション）を保持できません。**
**この差を吸収する方法の一つが、マウント時に `uid` を指定して、特定のユーザとして動作させる方法**です。

```bash
$ sudo mount -o uid=staff /dev/sdb1 /mnt/usb     # staff ユーザの持ち物として見せる
$ ls -l /mnt/usb                                  # 所有者が staff になっている
-rwxr-xr-x 1 staff staff 1024 Sep 15 10:00 memo.txt
```

`/etc/fstab` に書くなら次のようになります。

```text
/dev/sdb1  /mnt/usb  vfat  uid=staff  0 0
```

**存在しない書き方に注意**

| 見かける書き方 | 実際は |
|:--|:--|
| `staff=rw` | **存在しない** |
| `user=staff` | **`user` は「一般ユーザでマウント可」のオプション**。値は取らない |
| `writable=staff` | **存在しない** |
| `rw` | **読み書きは許可されるが、所有者は変わらない**。特定ユーザが書けるようにはならない |

**`rw` と `uid=` は別の話**です。`rw` は「書き込みを許すか」、`uid=` は「誰の持ち物に見せるか」です。

**注意 … `user` / `users` を書くと `nosuid,nodev,noexec` が自動で付きます**

ここは Ping-t の表には載っていませんが、実機で確認できる重要な挙動です。
`defaults`（`suid` `dev` `exec` を含む）を書いていても、**`users` を併記すると打ち消されます**。

```bash
$ tail -1 /etc/fstab                 # defaults と users を両方書いた設定
UUID=b7be915b-... /tmp/mt/mnt ext4 defaults,noauto,users 0 0

$ sudo mount /tmp/mt/mnt             # マウントする
$ grep /tmp/mt/mnt /proc/mounts      # 実際に効いているオプションを見る
/dev/loop0 /tmp/mt/mnt ext4 rw,nosuid,nodev,noexec,relatime 0 0
                          └────────┬────────┘
                          defaults に書いたはずの suid/dev/exec が
                          nosuid/nodev/noexec に化けている
```

一般ユーザにマウントを許す以上、**そのユーザが SUID 付きバイナリを持ち込んで
権限昇格するのを防ぐ**ための安全策です。
どうしても実行を許したい場合は `users,exec` のように**後ろに書いて上書き**します。
（マウントオプションは**後に書いたほうが勝ちます**）

---

## 1行を読み解く

**Ping-t は「この 1 行から何が言えるか」を繰り返し問います。**
**読み方の手順を決めておく**と、どの行が来ても同じやり方で処理できます。

```text
① 2 番目を見る      … どこにマウントされるか（/ ならルートファイルシステム）
② 4 番目を分解する  … defaults を展開し、後ろのオプションで上書きする
③ 6 番目を見る      … 0 なら起動時のチェック対象外
```

### 例1 defaults だけの行

```text
/dev/hda1 / ext3 defaults 1 1
```

| 言われ方 | 判定 | 根拠 |
|:--|:--:|:--|
| `/dev/hda1` はルートファイルシステムとして利用される | **○** | **2 番目がルート（`/`）になっている** |
| `/dev/hda1` はシステム起動時に自動マウントされる | **○** | **`defaults` には `auto` が含まれる** |
| **`/dev/hda1` はユーザ権限でもマウントが可能である** | **✕** | **`defaults` には `nouser` が含まれる**。ユーザ権限でのマウントは**禁止**されている |

**`defaults` は「何も指定しない」ではなく「既定の 7 つ（`async` `auto` `dev` `exec` `nouser` `rw` `suid`）を指定した」と同じ**です。
**`nouser` が含まれている**ことを見落とすと、この 1 問を落とします。

### 例2 オプションを重ねた行

```text
/dev/cdrom /mnt/cd iso9660 noauto,user 0 0
```

| 言われ方 | 判定 | 根拠 |
|:--|:--:|:--|
| `/dev/cdrom` はシステム起動時に自動マウントされない | **○** | **`noauto` が含まれている** |
| `/dev/cdrom` はユーザ権限でもマウントが可能である | **○** | **`user` が含まれている** |
| `/dev/cdrom` はシステム起動時のファイルシステムの自動チェックを行わない | **○** | **最も右側の `fsck` フラグが `0`** |

### 例3 defaults を上書きした行

```text
/dev/cdrom /mnt/cdrom iso9660 defaults,users,noauto 0 0
```

**まず `defaults` を展開してから、後ろのオプションで上書きします。**

```text
  defaults        → async, auto, dev, exec, nouser, rw, suid
        │
  users を適用    → nouser を上書き（一般ユーザでマウント可、誰でもアンマウント可）
        │
  noauto を適用   → auto を上書き（自動マウント対象外）
        │
  結果            → async, noauto, dev, exec, users, rw, suid
```

| 言われ方 | 判定 | 根拠 |
|:--|:--:|:--|
| **誰でもマウントできる** | **○** | `users` |
| **誰でもアンマウントできる** | **○** | **`users` は本人以外でもアンマウントできる** |
| **`mount /mnt/cdrom` でマウントできる** | **○** | **`/etc/fstab` にエントリがあるので、マウント先だけの指定でよい** |
| `mount /dev/cdrom` コマンドではマウントできない | **✕** | **エントリがあれば、デバイスファイルの指定でもマウントできる** |
| 起動時に自動的にマウントされる | **✕** | **`noauto`** |
| ファイルシステムチェックの対象になる | **✕** | **`fsck` フラグが `0`** |
| マウントしたユーザしかアンマウントできない | **✕** | **それは `user` の挙動**。`users` は誰でも外せる |

**`user` と `users` は 1 文字違いで意味が変わります。**

```text
  user  … 一般ユーザでマウント可 ／ アンマウントは マウントした本人だけ
  users … 一般ユーザでマウント可 ／ アンマウントは 誰でも
```

**確かめ方**

```bash
$ grep cdrom /etc/fstab               # 設定を確認する
/dev/cdrom /mnt/cdrom iso9660 defaults,users,noauto 0 0
$ sudo mount -a                        # noauto なので、これではマウントされない
$ mount | grep cdrom                   # 何も表示されない
$ mount /mnt/cdrom                     # マウント先だけの指定でマウントできる
$ mount | grep cdrom                   # マウントされたことを確認する
/dev/sr0 on /mnt/cdrom type iso9660 (ro,nosuid,nodev,noexec,relatime)
```

**`mount -a` で付かないのに `mount /mnt/cdrom` では付く**——
これが `noauto` の意味そのものです。

---

## 起動時に自動マウントする条件

起動時に走る `mount -a` が対象にするのは、**4 つ目に `auto` が効いているエントリだけ**です（冒頭の「起動時に自動でマウントされる」で触れたとおり）。
つまり**起動時に自動マウントさせたいなら、`auto` か `defaults` のどちらかを書きます**。

| 4つ目の記述 | 起動時に自動マウントされるか |
|:--|:-:|
| `defaults` | **○**（`auto` を含むため） |
| `auto` | **○** |
| `defaults,noauto` | ✕ |
| `noauto` | ✕ |

**例文** … `ext3` の `/dev/sda1` を起動時から `/boot` に自動マウントする

```text
/dev/sda1 /boot ext3 defaults 1 1        ← 正しい
/dev/sda1 /boot ext3 auto     1 1        ← これも正しい
/dev/sda1 /boot ext3 noauto   1 1        ← 自動マウントされない
/boot /dev/sda1 ext3 defaults 1 1        ← (1)と(2)が逆。誤り
```

**項目の順番は「デバイス名 → マウントポイント」です。** `mount` コマンドと同じ並びと覚えます。

**実機で確かめる**

```bash
$ tail -1 /etc/fstab                 # noauto を付けた設定
LABEL=TESTLABEL /tmp/mt/mnt ext4 defaults,noauto 0 0
$ sudo mount -a                      # 一括マウントを実行する
$ findmnt /tmp/mt/mnt                # マウントされていない（noauto が効いている）

$ tail -1 /etc/fstab                 # noauto を外した設定
LABEL=TESTLABEL /tmp/mt/mnt ext4 defaults 0 0
$ sudo mount -a                      # もう一度実行する
$ findmnt /tmp/mt/mnt                # 今度はマウントされた
TARGET      SOURCE     FSTYPE OPTIONS
/tmp/mt/mnt /dev/loop0 ext4   rw,relatime
```

**補足 … `noauto` はどんなときに使うか**

CD-ROM や USB メモリのように**普段は繋がっていないもの**に使います。
`auto` にしておくと、メディアが無い状態で起動したときにマウントが失敗します。

---

## 書き間違いから身を守る

**`/etc/fstab` の書き間違いは起動不能に直結します。**
存在しないデバイスを `auto` で書くと、起動時のマウントに失敗して
**緊急モードで止まる**ことがあります。編集したら、再起動する前に必ず検証します。

```bash
$ sudo cp /etc/fstab /etc/fstab.bak  # ① まず控えを取る
$ sudo vi /etc/fstab                 # ② 編集する
$ sudo mount -a                      # ③ 再起動せずに記述を試す
$ sudo findmnt --verify              # ④ 記述を静的にチェックする
```

| 検証の方法 | 何が分かるか |
|:--|:--|
| **`mount -a`** | **実際にマウントしてみる**。エラーが出れば、その行が起動時にも失敗する |
| **`findmnt --verify`** | **マウントせずに書式を調べる**。存在しないマウントポイントや不正なオプションを指摘する |

**保険として `nofail` を付けておく**

そのデバイスが無くても**起動を止めない**オプションです。

```bash
$ echo "UUID=... /data xfs defaults,nofail 0 2" | sudo tee -a /etc/fstab   # nofail 付きで追記する
```

> **`nofail` は「マウントしなくてよい」ではありません。**
> **「マウントできなくても起動は続ける」**という意味です。
> 起動を優先したい追加ディスクには付け、ルートや `/boot` のように**無いと動かないものには付けません**。

---

## 一般ユーザにマウントさせる

USB メモリを一般ユーザが `mount /mnt/usb` だけでマウントできるようにする、という場面です。

**必要な準備は 2 つ**

| やること | 理由 |
|:--|:--|
| **`/etc/fstab` にマウント設定を書く** | マウントポイントだけの指定でマウントするには、事前設定が必要 |
| **UUID を確認してデバイス名に書く** | USB は接続順でデバイスファイルが変わるため |

**手順**

```bash
$ sudo blkid                         # ① USB メモリの UUID を確認する
/dev/sda1: LABEL="TRANSCEND" UUID="0898-00BA" TYPE="vfat"
```

```bash
$ sudo vi /etc/fstab                 # ② fstab に設定を追記する
```

```text
UUID=0898-00BA  /mnt/usb  vfat  defaults,user,umask=000,noauto  0  0
     (1)          (2)     (3)              (4)                 (5)(6)
```

| # | 値 | なぜそう書くか |
|:-:|:--|:--|
| (1) | `UUID=0898-00BA` | デバイス名。**UUID を指定**して接続順に左右されないようにする |
| (2) | `/mnt/usb` | マウントポイント |
| (3) | `vfat` | ファイルシステムの種類。**USB メモリが FAT32 フォーマットの場合は `vfat`** |
| (4) | `defaults,user,umask=000,noauto` | **`user`** で一般ユーザのマウントを許可、**`umask=000`** で全ユーザが読み書きできるように、`noauto` で起動時には繋がない |
| (5)(6) | `0 0` | dump しない、fsck しない |

```bash
$ mount /mnt/usb                     # ③ 一般ユーザでマウントできる（sudo 不要）
$ ls /mnt/usb                        # 中身を確認する
OneDrive  System Volume Information  usb.txt
$ umount /mnt/usb                    # アンマウントする
```

**補足 … `vfat` とは**

**VFAT は FAT の拡張仕様で、長いファイル名に対応するためのファイルシステム**です。
USB メモリや SD カードでよく使われる FAT32 は、Linux では `vfat` として扱います。

**補足 … `umask=000` の意味**

`umask` は**ファイルやディレクトリの新規作成時のデフォルトのパーミッション**を決める値です。
`vfat` にはパーミッションの概念が無いため、マウント時に指定した値が全体に適用されます。
`umask=000` なら `777`（全ユーザが読み書き実行可能）になります。

**やってはいけない書き方**

| 書き方 | なぜ誤りか |
|:--|:--|
| デバイスファイル（`/dev/sda1`）で書く | **接続する順番や環境によってデバイスファイルが変わる**ため |
| 何も設定しない | `mount /mnt/usb` はマウントポイントだけの指定なので、**fstab の設定が必須** |

「一般ユーザではマウントできない」というのも誤りで、
**上記のように事前設定しておけば一般ユーザでもマウントできます**。

---

## クラウドでのfstab設計

**クラウドで特に効くポイント**

| 項目 | 理由 |
|:--|:--|
| **必ず UUID で書く** | EC2 では **Nitro 世代でデバイス名が `/dev/nvme*` に変わる**ため、`/dev/xvdf` 決め打ちは危険 |
| **`nofail` を付ける** | ボリュームのアタッチが間に合わなくても**起動を止めない**。EBS はインスタンス起動と非同期にアタッチされることがある |
| **`_netdev` を使う（EFS / NFS）** | ネットワークが上がってからマウントさせる。付けないと起動時に失敗する |
| **6つ目（fsck）は `2` か `0`** | ルート以外は `2`。EFS など**ネットワーク越しのものは `0`** |

**EFS をマウントする例**

```bash
$ sudo dnf install -y amazon-efs-utils        # EFS 用のヘルパーを入れる
$ echo "fs-0123456789abcdef0:/ /mnt/efs efs _netdev,tls 0 0" | sudo tee -a /etc/fstab   # EFS の設定を追記する
$ sudo mount -a                               # マウントする
```

`_netdev` を書かないと、**ネットワークが上がる前にマウントを試みて失敗**します。
オンプレの NFS でも同じ考え方です。

**`noexec` / `nosuid` はセキュリティ設計の定番**

ユーザがファイルを置ける領域（`/tmp`、`/var/tmp`、アップロード先）には、
**実行と SUID を禁止**するのが CIS ベンチマークの推奨です。

```text
/dev/nvme2n1  /var/upload  xfs  defaults,nodev,nosuid,noexec  0 2
```

侵入されても、そこに置かれたバイナリを実行できなくなります。

**`noatime` で I/O を減らす**

読み取りのたびに atime を書き戻すのは無駄な I/O です。
ログ集約サーバや大量のファイルを読むワークロードでは効きます。

```text
UUID=...  /data  xfs  defaults,noatime  0 2
```

詳しくは
[01_シェルとコマンドライン / ファイルの種類とタイムスタンプ](../01_シェルとコマンドライン/ファイルの種類とタイムスタンプ.md)
の「アクセス時刻の更新は抑制されている」を参照してください。

## 参考リンク

- [man 5 fstab](https://man7.org/linux/man-pages/man5/fstab.5.html)
- [man 8 mount](https://man7.org/linux/man-pages/man8/mount.8.html)
- [man 8 blkid](https://man7.org/linux/man-pages/man8/blkid.8.html)
- [man 8 lsblk](https://man7.org/linux/man-pages/man8/lsblk.8.html)
- [man 8 findmnt](https://man7.org/linux/man-pages/man8/findmnt.8.html)
- [AWS — Amazon EBS ボリュームを使用できるようにする](https://docs.aws.amazon.com/ja_jp/ebs/latest/userguide/ebs-using-volumes.html)
- [AWS — EFS ファイルシステムの自動マウント](https://docs.aws.amazon.com/ja_jp/efs/latest/ug/mount-fs-auto-mount-onreboot.html)

---

[← 全体の目次にもどる](../README.md)
