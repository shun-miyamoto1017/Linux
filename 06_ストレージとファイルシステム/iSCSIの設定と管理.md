# iSCSIの設定と管理

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★☆☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — ファイルシステムの管理 |
| **業務での使いどころ** | **既存の LAN でストレージを共有する。**ファイバーチャネルの筐体を買わずに SAN を組める。オンプレの共有ストレージはこれで繋がっていることが多い |

> **このノートはネットワーク越しにブロックデバイスを繋ぐ**話です。
> **ローカル接続の規格（SATA / SCSI）**は
> [接続規格とデバイスファイル](./接続規格とデバイスファイル.md)、
> **ファイル単位で共有する NFS**は別系統です
> （繋いだあとの `mkfs` / `mount` は [ディスクを追加する手順](./ディスクを追加する手順.md) と同じ）。

---

## 目次

- [iSCSIとは](#iscsiとは)
- [イニシエータとターゲット](#イニシエータとターゲット)
- [3つの識別子](#3つの識別子)
- [iscsiadm コマンド](#iscsiadm-コマンド)
  - [3つのモード](#3つのモード)
  - [ターゲットを探す discovery](#ターゲットを探す-discovery)
  - [ログインとログアウト node](#ログインとログアウト-node)
- [設定ファイル](#設定ファイル)
- [起動時に自動で繋ぐ](#起動時に自動で繋ぐ)
- [2つのデーモンの役割](#2つのデーモンの役割)
- [全体の流れ](#全体の流れ)
- [存在しないコマンドの整理](#存在しないコマンドの整理)
- [参考リンク](#参考リンク)

---

## iSCSIとは

**SCSI（Small Computer System Interface）とは、
PC やサーバに直接接続されたハードディスクなどの周辺機器を制御し、
データ転送を行うための規格の一つ**です。

**この SCSI の機能を TCP/IP ネットワーク上で利用できるようにしたものが
iSCSI（Internet Small Computer System Interface）という規格**です。

```text
  【SCSI】
    サーバ ──ケーブル── ディスク         … 直接つながっている

  【iSCSI】
    サーバ ──TCP/IP── ストレージ装置     … LAN 越しにつながっている
        ↑ サーバからは ローカルディスクと同じ ように見える
```

**iSCSI を導入するメリット**

| メリット | 内容 |
|:--|:--|
| **安価** | **記憶装置とサーバ間のネットワーク（SAN：Storage Area Network）を構築する際、高価なファイバーチャネルではなく、既存のネットワークインフラを使用できる** |
| **統合管理** | **記憶装置を他のネットワーク機器と同様のネットワーク上で統合管理が可能になる** |

**NFS との違い**

| | **iSCSI** | **NFS** |
|:--|:--|:--|
| **共有する単位** | **ブロックデバイス**（ディスクそのもの） | **ファイルシステム**（ファイル単位） |
| **クライアント側で** | **`mkfs` してからマウントする** | **そのままマウントする** |
| 同時に複数台から | **原則 1 台だけ**（クラスタ FS なら可） | **複数台から同時に可** |
| 見え方 | **`/dev/sdc` のようなディスク** | ネットワークのフォルダ |

**iSCSI は「LAN 越しのディスク」、NFS は「LAN 越しのフォルダ」**——この区別が本質です。
**iSCSI で繋いだら、あとはローカルディスクとまったく同じ**に `fdisk` → `mkfs` → `mount` します。

---

## イニシエータとターゲット

**SCSI（iSCSI）では通常、ホスト側をイニシエータ、デバイス側をターゲットと呼びます。**

```text
  イニシエータ（Initiator）        ターゲット（Target）
  = ホスト側 = サーバ              = デバイス側 = ストレージ装置
        │                                 │
        │  ─── iscsiadm でログイン ───▶  │
        │                                 │
        └─ iscsid デーモンが動いている     └─ ディスクを提供している
```

| 役割 | 呼び方 | Linux で必要なもの |
|:--|:--|:--|
| **ホスト側**（使う側） | **イニシエータ** | **`iscsid` デーモン**、`iscsiadm` コマンド |
| **デバイス側**（提供する側） | **ターゲット** | ストレージ装置、または `targetcli` などで構築 |

**サーバを iSCSI イニシエータとして動作させるには `iscsid` デーモンを起動する必要があります。**

| 選択肢 | 正誤 |
|:--|:-:|
| **`iscsid`** | **○**（イニシエータとして動作させるためのデーモン） |
| `scsiinit` / `initscsi` / `initiator` / `iscsiinitiator` | ✕（**存在しないデーモン**） |

```bash
$ sudo systemctl start iscsid          # イニシエータのデーモンを起動する
$ sudo systemctl enable iscsid         # 起動時に自動で立ち上げる
```

---

## 3つの識別子

**iSCSI と SCSI には、似た名前の識別子が 3 つ出てきます。**

| 識別子 | 何を識別するか | 確認するコマンド |
|:--|:--|:--|
| **IQN**（iSCSI Qualified Name） | **iSCSI イニシエータや iSCSI ターゲットを一意に識別する** | `iscsiadm` の出力 |
| **WWID / WWN**（World Wide Identifier / Name） | **ファイバーチャネルや SCSI による SAN において、記憶装置を一意に識別する** | **`scsi_id`** |
| **LUN**（Logical Unit Number） | **記憶装置を識別するための論理的な単位**。この単位でサーバから 1 台の HDD と認識される | — |

**IQN の形**

```text
  iqn.2013-12.pingt.test1:target1
   │    │       │            │
   │    │       │            └─ 任意の名前
   │    │       └─ ドメイン名を逆さにしたもの
   │    └─ ドメインを取得した年月
   └─ iqn で始まる
```

**WWID と LUN を取り違えない**

| 説明 | どちらか |
|:--|:--|
| **SAN などにおいて記憶装置を一意に識別するためのもの** | **WWID / WWN** |
| **SCSI 接続の記憶装置の場合は `scsi_id` コマンドで確認できる** | **WWID / WWN** |
| **記憶装置を識別するための論理的な単位** | **LUN** |
| **SCSI 接続の記憶装置内に論理的に作成された記憶装置を識別するためのもの** | **LUN** |
| IP ネットワークに接続されたマシンを識別するためのもの | **IP アドレス**（どちらでもない） |
| `ifconfig` コマンドで確認できる | **どちらでもない**（`ifconfig` はネットワークインタフェース） |

```text
  WWID / WWN  装置 そのもの の世界で一意な名前   … iSCSI の IQN に相当する
  LUN         その装置の 中の 論理的な番号        … サーバからは 1 台の HDD に見える
```

**`scsi_id` で WWID を確認する**

**`scsi_id` コマンドで、SCSI 接続の記憶装置の WWID（World Wide Identifier）の確認を行えます。**

```bash
$ sudo /usr/lib/udev/scsi_id --page=0x83 --whitelisted --device=/dev/sda   # WWID を取り出す
1ATA     VBOX HARDDISK                           VBf9a02364-ba806d97
```

**`scsi_id` は `/usr/lib/udev/` にあるので、PATH が通っていない**ことが多いです。

```bash
$ whereis scsi_id                      # whereis の探索先に /usr/lib/udev は入っていないので見つからない
scsi_id:
$ find /usr/lib -name scsi_id          # パスが分からないときは find で探す
/usr/lib/udev/scsi_id
```

`whereis` については [コマンドの場所を探す](./コマンドの場所を探す.md) にあります。

**`scsi_id` と `iscsiadm` を混同しない**

| コマンド | 役割 |
|:--|:--|
| **`scsi_id`** | **WWID / WWN の確認などを行うためのコマンド** |
| **`iscsiadm`** | **iSCSI ターゲットへアクセスし、デバイスとして使用可能に設定する際に使用するコマンド** |
| `iscsi` / `iscsictl` / `iscsi_id` | **存在しないコマンド** |

---

## iscsiadm コマンド

**iSCSI イニシエータから iSCSI ターゲットへアクセスし、
デバイスとして使用可能にするには `iscsiadm` コマンドを利用します。**

```text
iscsiadm [オプション]
```

| オプション | 説明 |
|:--|:--|
| **`-m` \| `--mode` モード** | **モードの指定**。主に以下を使用<br>**`discovery`** 接続先の iSCSI ターゲットの一覧取得<br>**`node`** 登録済み iSCSI ターゲットの一覧取得<br>**`session`** セッションの一覧取得 |
| **`-l` \| `--login`** | **iSCSI ターゲットにログイン**（node モード時） |
| **`-u` \| `--logout`** | **iSCSI ターゲットからログアウト**（node モード時） |
| **`-t` \| `--type=タイプ`** | **タイプの指定**（discovery モード時）。主に **`sendtargets`** を指定する（使用可能な iSCSI ターゲットをイニシエータに送信） |
| **`-p` \| `--portal=IPアドレス[:ポート]`** | **接続先の指定**。**デフォルトのポート番号は 3260** |
| **`-T` \| `--targetname=IQN`** | **iSCSI ターゲットの指定** |

**`open-iscsi 2.1.9` の `--help` を実機で確認した抜粋**

```text
iscsiadm -m discovery [-t type -p ip:port -I ifaceN ... [-l]] ...
iscsiadm -m node [-L all,manual,automatic,onboot] ... [[-T targetname -p ip:port -I ifaceN] [-l | -u | -R | -s]] ...
iscsiadm -m session [-r sessionid | sysfsdir [-R | -u | -s]] ...
```

### 3つのモード

```text
  ① discovery  接続先のサーバに「どんなターゲットがある？」と聞く
        ▼        結果をローカルデータベースに登録する
  ② node       登録済みのターゲットを操作する（ログイン・ログアウト）
        ▼
  ③ session    いま繋がっているセッションを見る
```

| モード | 何をするか | よく使う組み合わせ |
|:--|:--|:--|
| **`discovery`** | **接続先の iSCSI ターゲットの一覧取得** | **`-t sendtargets -p IP`** |
| **`node`** | **登録済み iSCSI ターゲットの一覧取得**・ログイン・ログアウト | **`-l`** / **`-u`** |
| **`session`** | **セッションの一覧取得** | `-P 3` で詳細 |

### ターゲットを探す discovery

**iSCSI イニシエータでは、`iscsiadm` コマンドで接続先の iSCSI ターゲットの一覧を取得し、
ローカルデータベースへ登録する必要があります。**

**そのためには、discovery モードで `-t sendtargets` と `-p IPアドレス[:ポート]` を指定します。**

| オプション | 役割 |
|:--|:--|
| **`-p`** | **iSCSI ターゲットのある接続先サーバを指定するオプション** |
| **`-t sendtargets`** | **接続先の全ての iSCSI ターゲットを、iSCSI イニシエータのローカルデータベースに自動的に登録するオプション** |

```bash
$ sudo iscsiadm -m discovery -t sendtargets -p 192.168.1.9   # ターゲットを探して登録する
192.168.1.9:3260,1 iqn.2013-12.pingt.test1:target1
192.168.1.9:3260,1 iqn.2013-12.pingt.test1:target2
```

**この例では iSCSI ターゲットが 2 つあることが分かります。**
**表示されている `iqn.2013-12.pingt.test1:target1` と `iqn.2013-12.pingt.test1:target2` は
IQN（iSCSI Qualified Name）と呼ばれるもので、
iSCSI イニシエータや iSCSI ターゲットを一意に識別するものです。**

**`:3260` が既定のポート**なので、指定を省略できます。

**間違いやすい書き方**

| 書き方 | 成立するか | どこが違うか |
|:--|:-:|:--|
| **`iscsiadm -m discovery -t sendtargets -p 192.168.1.9`** | **○** | **モード・タイプ・接続先がそろっている** |
| `iscsiadm -m session -p sendtargets -t 192.168.1.9` | ✕ | **`-p` と `-t` が逆**。モードも違う |
| `iscsiadm -t node -m 192.168.1.9` | ✕ | **`-m` と `-t` の役割が逆** |
| `iscsiadm -m 192.168.1.9` | ✕ | **`-m` はモードを取る**。IP は `-p` |
| `iscsiadm -p 192.168.1.9` | ✕ | **モードの指定が無い** |

### ログインとログアウト node

**ローカルデータベースに登録されている全ての iSCSI ターゲットへ一括でログインする**

```bash
$ sudo iscsiadm -m node -l             # 登録済みの全ターゲットにログインする
Logging in to [iface: default, target: iqn.2013-12.pingt.test1:target2, portal: 192.168.1.9,3260] (multiple)
Logging in to [iface: default, target: iqn.2013-12.pingt.test1:target1, portal: 192.168.1.9,3260] (multiple)
Login to [iface: default, target: iqn.2013-12.pingt.test1:target2, portal: 192.168.1.9,3260] successful.
Login to [iface: default, target: iqn.2013-12.pingt.test1:target1, portal: 192.168.1.9,3260] successful.
```

**上記の例では、2 つの iSCSI ターゲットへのログインに成功しているのが分かります。**

**ローカルデータベースに登録されている全ての iSCSI ターゲットから一括でログアウトする**

```bash
$ sudo iscsiadm -m node -u             # 登録済みの全ターゲットからログアウトする
Logging out of session [sid: 1, target: iqn.2013-12.pingt.test1:target2, portal: 192.168.1.9,3260]
Logout of [sid: 1, target: iqn.2013-12.pingt.test1:target2, portal: 192.168.1.9,3260] successful.
```

**`-T` で 1 つだけ指定する**

**`-T` オプションを使用することで、ログイン／ログアウトする iSCSI ターゲットを指定することもできます。**

```bash
$ sudo iscsiadm -m node -l -T iqn.2013-12.pingt.test1:target1   # 1つだけログイン
Login to [iface: default, target: iqn.2013-12.pingt.test1:target1, portal: 192.168.1.9,3260] successful.
$ sudo iscsiadm -m node -u -T iqn.2013-12.pingt.test1:target1   # 1つだけログアウト
```

**組み合わせの早見表**

| やりたいこと | コマンド |
|:--|:--|
| **全ターゲットにログイン** | **`iscsiadm -m node -l`** |
| **全ターゲットからログアウト** | **`iscsiadm -m node -u`** |
| **1 つだけログイン** | **`iscsiadm -m node -l -T IQN`** |
| **1 つだけログアウト** | **`iscsiadm -m node -u -T IQN`** |
| セッションを見る | `iscsiadm -m session` |

**`-l` と `-u` を取り違えない**

```text
  -l  login    … ログイン（繋ぐ）
  -u  logout   … ログアウト（切る）
        ↑ どちらも node モードで使う
```

**ログイン後は普通のディスクとして見える**

```bash
$ lsblk                                # /dev/sdc などが増えている
$ sudo fdisk /dev/sdc                  # あとはローカルディスクと同じ手順
$ sudo mkfs -t ext4 /dev/sdc1          # ファイルシステムを作る
$ sudo mount /dev/sdc1 /mnt/iscsitarget   # マウントして使う
```

---

## 設定ファイル

**`iscsid` デーモンと `iscsiadm` コマンドの設定ファイルは `iscsid.conf`** です。

```bash
$ ls -l /etc/iscsi/iscsid.conf         # 実機での場所を確認する
-rw-r--r-- 1 root root 14613 Jun  4  2025 /etc/iscsi/iscsid.conf
```

| ディストリビューション | 場所 |
|:--|:--|
| **Debian / Ubuntu 系** | **`/etc/iscsi/iscsid.conf`**（実機で確認） |
| **RHEL 系** | **`/etc/iscsi/iscsid.conf`** |

**存在しない設定ファイル**

| 見かける名前 | 実際は |
|:--|:--|
| **`iscsid.conf`** | **これが正しい** |
| `iscsiadm.conf` | **存在しない**（コマンド名と設定ファイル名は違う） |
| `scsiinit.conf` / `initiator.conf` / `initiscsi.conf` | **存在しない** |

**`iscsid` というデーモン名がそのまま設定ファイル名**になっています。

---

## 起動時に自動で繋ぐ

**iSCSI ターゲットをサーバ起動時にマウントするには、2 つの設定が要ります。**

```text
  ① iscsid が起動時に 自動ログイン するよう設定する   … node.startup
        ▼
  ② /etc/fstab に _netdev 付きで書く                … マウントを待たせる
```

### node.startup で自動ログインを制御する

**`iscsid` デーモンは起動時にローカルデータベースに登録済みの iSCSI ターゲットにログインします。**
**ただしログインするのは、ターゲットのパラメータ `node.startup` に
`automatic` と設定されているターゲットです。**

```text
node.startup = automatic      ← 自動ログインする
node.startup = manual         ← 自動ログインしない
```

| やりたいこと | 設定値 |
|:--|:--|
| **起動時に自動的にログインする** | **`automatic`** |
| **起動時に自動的にログインしない** | **`manual`** |

| 選択肢 | 正誤 |
|:--|:-:|
| **`automatic`** / **`manual`** | **○**（この 2 つだけ） |
| `yes` / `no` / `login` / `nologin` | ✕（**無効なパラメータの値**） |

```bash
$ grep node.startup /etc/iscsi/iscsid.conf   # 既定値を確認する
# node.startup = automatic
node.startup = manual
```

**多くのディストリビューションの既定は `manual`**（実機で確認）です。
**自動で繋ぎたいなら明示的に `automatic` に変える**必要があります。

### fstab には `_netdev` を書く

**iSCSI ターゲットをサーバ起動時にマウントするには、
`iscsid` デーモンによる自動ログインの設定に加え、
`/etc/fstab` ファイルにマウントする iSCSI ターゲットを追加します。**
**その際、マウントオプションには `_netdev` を指定します。**

```text
/dev/sdc  /mnt/iscsitarget  ext4  _netdev  0 0
```

**`_netdev` は、対象となるデバイスがネットワークを通して利用可能になるまでマウントを待つオプション**です。
**このオプションを指定することで、iSCSI ターゲットは
`iscsid` デーモンの起動後（iSCSI ターゲットに自動ログイン後）にマウントされます。**

| 選択肢 | 正誤 |
|:--|:-:|
| **`_netdev`** | **○** |
| `_iscsitarget` / `_iscsi` / `iscsitarget` / `target` | ✕（**存在しないマウントオプション**） |

**`_netdev` が無いとどうなるか**

```text
  起動
    ▼
  /etc/fstab を読んでマウントを試す
    ▼
  まだネットワークが上がっていない → /dev/sdc が無い
    ▼
  マウント失敗 → 起動が緊急モードで止まる
```

**`_netdev` と `nofail` を併せて書く**のが実務では安全です。

```text
/dev/sdc  /mnt/iscsitarget  ext4  _netdev,nofail  0 0
```

マウントオプションは [fstabの書き方](./fstabの書き方.md) にあります。

---

## 2つのデーモンの役割

**`iscsid` と `iscsi` という、名前の似た 2 つの仕組みがあります。**
**常駐するのは `iscsid` のほうだけ**で、`iscsi` は起動時に一度だけ動いて終わる `oneshot` 型のサービスです（`systemctl status` では `active (exited)` になります）。

| デーモン | 役割 |
|:--|:--|
| **`iscsid`** | **サーバを iSCSI イニシエータとして動作させるために必要なデーモン**。**自動的にはログインしない** |
| **`iscsi`** | **ローカルデータベースに登録済みの iSCSI ターゲットに自動的にログインするデーモン** |

**つまり `iscsi` デーモンをサーバ起動時に自動起動とすることで、
サーバ起動時に iSCSI ターゲットをデバイスとして使用可能にします。**
**なおログインするのは、ターゲットのパラメータ `node.startup` に
`automatic` と設定されているターゲットです。**

```text
  iscsid    イニシエータとして 動ける ようにする    … 土台
  iscsi     登録済みターゲットに 自動ログイン する   … 起動時の接続
```

**問われ方ごとの答え**

| 問われ方 | 答え |
|:--|:--|
| **ホストを iSCSI イニシエータとして動作させるために必要なデーモンは** | **`iscsid`** |
| **登録済みの iSCSI ターゲットに自動的にログインするデーモンは** | **`iscsi`** |

**存在しないデーモン**：`ilogin` / `iscsiauto` / `iscsilogin` / `scsiinit` / `initscsi` / `initiator` / `iscsiinitiator`

```bash
$ sudo systemctl enable --now iscsid   # イニシエータの土台
$ sudo systemctl enable --now iscsi    # 起動時の自動ログイン
```

---

## 全体の流れ

```text
  ① iscsid デーモンを起動する
        ▼
  ② iscsiadm -m discovery -t sendtargets -p <ターゲットのIP>
        ▼   ローカルデータベースに登録される
  ③ iscsiadm -m node -l
        ▼   /dev/sdc などが生える
  ④ fdisk → mkfs → mount                 ← ここからローカルディスクと同じ
        ▼
  ⑤ node.startup = automatic に設定する
        ▼
  ⑥ /etc/fstab に _netdev 付きで書く
        ▼
  ⑦ iscsi デーモンを enable にする
```

**②〜④は手動の検証、⑤〜⑦は恒久化**という区切りで覚えると迷いません。

```bash
$ sudo systemctl start iscsid                                     # ①
$ sudo iscsiadm -m discovery -t sendtargets -p 192.168.1.9        # ②
$ sudo iscsiadm -m node -l                                        # ③
$ lsblk                                                           # ④ 何が増えたか確認する
$ sudo mkfs -t ext4 /dev/sdc && sudo mount /dev/sdc /mnt/iscsi    # ④
```

---

## 存在しないコマンドの整理

| 見かける名前 | 実際は |
|:--|:--|
| **`iscsiadm`** | **これが正しい**（iSCSI の管理コマンド） |
| **`scsi_id`** | **これも正しい**（WWID の確認） |
| **`iscsi`** / **`iscsictl`** / **`iscsi_id`** | **存在しないコマンド** |
| `iscsiadm.conf` | **存在しない設定ファイル**（正しくは `iscsid.conf`） |

**紛らわしい 4 つを並べる**

```text
  iscsid     デーモン    （イニシエータの土台）
  iscsi      デーモン    （自動ログイン）
  iscsiadm   コマンド    （操作する）
  iscsid.conf 設定ファイル（iscsid と iscsiadm の両方の設定）
       ↑ 末尾の d の有無、adm の有無で役割が変わる
```

---

## 参考リンク

- [man 8 iscsiadm](https://man7.org/linux/man-pages/man8/iscsiadm.8.html)
- [man 8 iscsid](https://man7.org/linux/man-pages/man8/iscsid.8.html)
- [man 5 iscsid.conf](https://man7.org/linux/man-pages/man5/iscsid.conf.5.html)
- [Open-iSCSI プロジェクト](https://www.open-iscsi.com/)
