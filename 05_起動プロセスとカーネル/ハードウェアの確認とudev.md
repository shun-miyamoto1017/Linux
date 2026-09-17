# ハードウェアの確認とudev

| | |
|:--|:--|
| **学習の順番** | Phase2 ★★★★☆（ハードウェア設定の決定と設定 ／ Linuxカーネルの構成要素） |
| **Ping-t の範囲** | Linux2 / システムの起動とLinuxカーネル(主題2.01) — ハードウェア設定の決定と設定、Linuxカーネルの構成要素 |
| **業務での使いどころ** | **「このサーバにどんな機器が付いているか」を調べる**。NIC が認識されない、ディスクが見えない、USB が反応しない、という調査の入口 |

> モジュールの読み込み・依存関係は
> [カーネルモジュールの管理](./カーネルモジュールの管理.md)、
> `/proc/sys` とカーネルパラメータは
> [カーネルの実行時管理 dmesgとsysctl](./カーネルの実行時管理_dmesgとsysctl.md) にまとめています。
> このノートは**機器そのものを見る側**の話です。

---

## 目次

- [機器を一覧するコマンド](#機器を一覧するコマンド)
- [udev デバイスファイルを自動で作る仕組み](#udev-デバイスファイルを自動で作る仕組み)
- [udev を操作するコマンド](#udev-を操作するコマンド)
- [udev.conf の設定項目](#udevconf-の設定項目)
- [参考リンク](#参考リンク)

---

## 機器を一覧するコマンド

### 4つの ls 系コマンドの使い分け

名前が似ていて混同しやすいので、**まず何を見るコマンドか**を並べます。

| コマンド | 見えるもの | 元になっている情報 |
|:--|:--|:--|
| **`lspci`** | **PCI デバイス**（NIC、ビデオカード、ストレージコントローラ、USB コントローラ） | PCI バスの情報 |
| **`lsusb`** | **USB デバイス** | USB バスの情報 |
| **`lsdev`** | **DMA・IRQ・I/O ポート**の割り当て | **`/proc/dma`** ／ **`/proc/interrupts`** ／ **`/proc/ioports`** |
| **`lsmod`** | **読み込まれているカーネルモジュール** | `/proc/modules` |

> **`lsmod` だけは「機器」ではなく「モジュール」のコマンド**です。
> 名前が `ls` で始まるので一緒に並びますが、見ているものが違います。
> → [カーネルモジュールの管理](./カーネルモジュールの管理.md)

**存在しないコマンド名にだまされない**

| 名前 | 実在するか |
|:--|:--:|
| **`lspci`** / **`lsusb`** / **`lsdev`** / **`lsmod`** | **する** |
| `showpci` / `pcishow` | **しない** |
| `devinfo --usb` | **しない** |
| `cat /proc/pci` / `cat /proc/usb` | **しない**（そういうファイルは無い） |

---

### lspci

**意味**

**PCI デバイス**の情報を表示します。
PCI は、マザーボードに機器をつなぐための規格です。**NIC・ビデオ・ストレージ・USB コントローラ**は、たいていここに出てきます。

**例文**

```bash
$ lspci                                              # PCIデバイスを一覧する
00:00.0 Host bridge: Intel Corporation 440FX - 82441FX PMC [Natoma] (rev 02)
00:01.0 ISA bridge: Intel Corporation 82371SB PIIX3 ISA [Natoma/Triton II]
00:01.1 IDE interface: Intel Corporation 82371AB/EB/MB PIIX4 IDE (rev 01)
00:02.0 VGA compatible controller: InnoTek Systemberatung GmbH VirtualBox Graphics Adapter
00:03.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet Controller (rev 02)

$ lspci -k                                           # どのドライバが使われているかも表示する
$ lspci -nn                                          # ベンダIDとデバイスIDを番号でも表示する
$ lspci -v                                           # 詳しく表示する
$ lspci -t                                           # バスの接続をツリーで表示する
$ lspci | grep -i ethernet                           # NICだけ拾う
```

**よく使うオプション**

| オプション | 意味 | 使いどころ |
|:--|:--|:--|
| **`-v`** | **詳しく表示する** | 割り込み番号やメモリ範囲まで見たいとき |
| **`-vv`** / `-vvv` | さらに詳しく | 深掘りの調査 |
| **`-k`** | **使われているカーネルドライバ**と、使用可能なモジュールを表示する | **ドライバが当たっていない機器を探す最短手段** |
| **`-n`** | ベンダ名・デバイス名を**番号で**表示する | 名前が不明な機器のIDを調べたいとき |
| **`-nn`** | **番号と名前の両方**を表示する | 番号で検索したいとき |
| **`-s アドレス`** | **指定したアドレス**の機器だけ表示する | `00:03.0` などで絞る |
| **`-d ベンダ:デバイス`** | 指定した ID の機器だけ表示する | 同種の機器をまとめて見る |
| **`-t`** | **ツリー表示**する | 機器のつながりを俯瞰する |
| **`-m`** | 機械処理しやすい形式で出力する | スクリプトで解析するとき |

**補足**

- `lspci` は **`pciutils`** パッケージに入っています
- **`-k` が実務で一番効きます。**「機器は見えているのにドライバが無い」状態がすぐ分かります

```bash
$ lspci -k | grep -A 3 -i ethernet                   # NICとそのドライバを確認する
00:03.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet Controller
	Subsystem: Intel Corporation PRO/1000 MT Desktop Adapter
	Kernel driver in use: e1000
	Kernel modules: e1000
```

| `-k` の出力行 | 意味 |
|:--|:--|
| **`Kernel driver in use:`** | **今この機器を動かしているドライバ**。**この行が無ければドライバが当たっていない** |
| **`Kernel modules:`** | 使える候補のモジュール |

---

### lsusb

**意味**

**USB デバイス**の情報を表示します。

**例文**

```bash
$ lsusb                                              # USBデバイスを一覧する
Bus 001 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub

$ lsusb -t                                           # 接続の階層をツリーで表示する
$ lsusb -v                                           # 詳しく表示する
$ lsusb -s 001:002                                   # バス001のデバイス002だけ表示する
$ lsusb -d 1d6b:0001                                 # 指定したID の機器だけ表示する
```

**結果画面の見方**

```text
   Bus 001  Device 001:  ID 1d6b:0001  Linux Foundation 1.1 root hub
   ───────  ───────────  ───────────   ──────────────────────────────
   バス番号   デバイス番号   ベンダ:製品ID        機器の名前
```

| 位置 | 意味 | どこを見るか |
|:--|:--|:--|
| **`Bus 001`** | **バス番号** | `-s` で絞り込むときに使う |
| **`Device 001`** | **デバイス番号**。挿し直すと変わる | 同上 |
| **`ID 1d6b:0001`** | **ベンダID : 製品ID**（16 進数） | **機器を一意に特定できる**。検索やルール作成に使う |
| 末尾の文字列 | 機器の名前 | 人が読むための表示。**udev のハードウェアデータベースから引かれる** |

**よく使うオプション**

| オプション | 意味 |
|:--|:--|
| **`-v`** / `--verbose` | **詳しく表示する**（ディスクリプタまで） |
| **`-t`** / `--tree` | **ツリー表示**する |
| **`-s [バス]:[デバイス]`** | 指定したバス／デバイスだけ表示する（10 進数） |
| **`-d ベンダ:製品`** | 指定した ID の機器だけ表示する（16 進数） |
| **`-D デバイスファイル`** | 指定したファイルの情報だけ表示する（`root` 権限が必要） |

**補足**

- `lsusb` は **`usbutils`** パッケージに入っています
- **`Device` 番号は挿し直すと変わります。**恒久的に機器を指すには、**ベンダID と製品ID** を使ってください

---

### lsdev

**意味**

**DMA・IRQ・I/O ポート**の割り当てを、1 つの表にまとめて表示します。
中身は **`/proc/dma`・`/proc/interrupts`・`/proc/ioports`** の 3 つのファイルを読んで整形したものです。

```text
   /proc/dma          ┐
   /proc/interrupts   ├─→  lsdev  が 1 つの表に整形して表示
   /proc/ioports      ┘
```

| 用語 | 意味 |
|:--|:--|
| **DMA**（Direct Memory Access） | CPU を通さずに、機器がメモリと直接やり取りする仕組み。その通り道の番号 |
| **IRQ**（Interrupt ReQuest） | **割り込み要求**。機器が「処理してほしい」と CPU に知らせるための番号 |
| **I/O ポート** | CPU が機器とやり取りするための**アドレスの範囲** |

**例文**

```bash
$ lsdev                                              # DMA・IRQ・I/Oポートをまとめて一覧する
Device            DMA   IRQ  I/O Ports
------------------------------------------------
0000:00:02.0                 1800-1807
0000:00:1d.0                 1820-183f
ath                      19
cascade             4
dma                          0080-008f
i8042                  1 12
keyboard                     0060-0060 0064-0064

$ cat /proc/interrupts                               # 割り込みの生データを見る
$ cat /proc/ioports                                  # I/Oポートの生データを見る
$ cat /proc/dma                                      # DMAの生データを見る
```

**結果画面の見方**

| 列 | 意味 | どこを見るか |
|:--|:--|:--|
| **`Device`** | **機器の名前**、または PCI のアドレス | どの機器の行か |
| **`DMA`** | その機器が使っている **DMA チャネル番号** | 空欄なら DMA を使っていない |
| **`IRQ`** | その機器が使っている **割り込み番号** | **同じ番号を複数の機器が使っている＝共有している** |
| **`I/O Ports`** | その機器に割り当てられた**アドレスの範囲** | 重複があれば競合 |

**`/proc/interrupts` の見方**

```bash
$ cat /proc/interrupts                               # CPUごとの割り込み回数を見る
           CPU0       CPU1
  0:     590865          0   IO-APIC-edge      timer
  1:       1128          0   IO-APIC-edge      i8042
 12:        153     163445   IO-APIC-edge      i8042
 14:      61845          0   IO-APIC-edge      ata_piix
```

| 列 | 意味 | 異常と判断する目安 |
|:--|:--|:--|
| **1 列目**（`0:`） | **割り込み番号（IRQ）** | — |
| **`CPU0` / `CPU1` …** | **その CPU が処理した回数** | **特定の CPU に極端に偏る**なら割り込みの分散が効いていない |
| **`IO-APIC-edge`** | 割り込みコントローラの種類 | — |
| **最後の列** | **その割り込みを使っているドライバ名** | 見覚えのない名前があれば調査対象 |

**補足**

- `lsdev` は **`procinfo`** パッケージに入っています。**入っていない環境も多い**ので、そのときは `/proc/interrupts` などを直接見ます
- 昔は IRQ の競合がよくある障害でしたが、現在は自動で割り当てられるため、**手で設定することはほぼありません**

---

## udev デバイスファイルを自動で作る仕組み

### 何をしてくれるのか

Linux では、機器を **`/dev/sda`** や **`/dev/ttyUSB0`** のような**デバイスファイル**を通して操作します。

昔は、あり得る機器の分だけデバイスファイルをあらかじめ作って置いていました。
現在は **udev** が、**機器がつながったときに、その機器に対応するデバイスファイルを自動で作ります。**

```text
 ① USBメモリを挿す
        │
        ▼
 ② カーネルが機器を検出する          ← 検出するのはカーネルの仕事
        │
        │  uevent（「機器が付いたよ」という通知）を送る
        ▼
 ③ udevd（udev のデーモン）が受け取る
        │
        │  /etc/udev/rules.d/ のルールに照らして、どう扱うか決める
        ▼
 ④ /dev/sdb1 のようなデバイスファイルを自動で作る
```

> **役割分担がそのまま問われます。**
>
> | | 誰がやるか |
> |:--|:--|
> | **ハードウェアを検出する** | **カーネル** |
> | **デバイスファイルを自動で作る** | **udevd** |
> | **ファイルシステムを自動でマウント／アンマウントする** | **`automount`**（autofs のデーモン。udev の仕事ではない） |

**`udevd` は「接続されたハードウェアに対応するデバイスファイルを自動的に作成する」デーモンです。**
検出そのものはカーネルがやっており、udevd はカーネルから通知を受け取って動いています。

| 用語 | 意味 |
|:--|:--|
| **デーモン** | 裏で常駐して動き続けるプログラム |
| **`uevent`** | カーネルが「機器の状態が変わった」とユーザ空間へ送る通知 |
| **デバイスファイル** | 機器をファイルとして扱うための特殊なファイル。`/dev` の下に置かれる |

---

### 設定ファイルとルールファイル

**2 種類あります。混同しやすいので分けて覚えます。**

| | **本体の設定ファイル** | **ルールファイル** |
|:--|:--|:--|
| **場所** | **`/etc/udev/udev.conf`** | **`/etc/udev/rules.d/` の中** |
| **何が書いてあるか** | udev **そのものの動作**（ログの詳しさ、同時実行数、タイムアウト） | **機器ごとに、どう扱うか**（名前、権限、シンボリックリンク、実行するコマンド） |
| **ファイル名** | `udev.conf` の 1 つだけ | `99-my.rules` のように**番号 + ハイフン + 名前 + `.rules`** |

```text
/etc/udev/
 ├── udev.conf          ← udev 本体の設定ファイル（これが「メインの設定」）
 └── rules.d/           ← ルールファイルを入れるディレクトリ
      ├── 60-persistent-storage.rules
      └── 99-my.rules   ← 自分で作ったルールはここへ置く
```

> **紛らわしいパスの整理**
>
> | パス | 何か |
> |:--|:--|
> | **`/etc/udev/udev.conf`** | **udev 本体の設定ファイル**（正解） |
> | **`/etc/udev/rules.d`** | ルールファイルを入れる**ディレクトリ**。設定ファイルではない |
> | `/etc/udev` | udev 関連をまとめた**親ディレクトリ**。ここ直下にルールを置いても**認識されない** |
> | `/etc/udev.conf` | **存在しない** |
> | `/etc/udev/rules.d/udev.conf` | **存在しない** |
> | `/etc/rules.d` | **存在しない** |

---

### ルールファイルの名前のつけ方

```text
   99  -  my  .rules
   ──     ──  ──────
   番号   名前  拡張子（必ず .rules）
```

| 部分 | 意味 |
|:--|:--|
| **先頭の 2 桁の番号** | **ルールの優先度**。**小さい番号から順に読まれる** |
| **ハイフン + 名前** | 何のルールか分かる名前 |
| **`.rules`** | **拡張子。これでないと読まれない** |

**自分で作るルールは `99-` で始めるのが定番です。**
番号が大きい＝**あとから読まれる**ので、ディストリの既定ルールを上書きできます。

**例文**

```bash
$ ls /etc/udev/rules.d/                              # 置かれているルールファイルを見る
$ sudo vi /etc/udev/rules.d/99-my.rules              # 自分のルールを作る
$ sudo udevadm control --reload                      # ルールを読み込み直す
$ sudo udevadm trigger                               # イベントを起こして適用する
```

**補足**

- ルールの読み込み先は `/etc/udev/rules.d`（管理者用）のほか `/run/udev/rules.d`、`/usr/lib/udev/rules.d`（パッケージ用）があります。**同じ名前なら `/etc` のものが勝ちます**
- **ルールを置いただけでは反映されません。**`udevadm control --reload` が必要です

---

## udev を操作するコマンド

### 新しい形と古い形

udev のコマンドは、**古い個別のコマンド**が **`udevadm` のサブコマンド**に統合されました。
**試験では両方が問われます。**

| 古いコマンド | 新しい書き方 | 何をするか |
|:--|:--|:--|
| **`udevinfo`** | **`udevadm info`** | **udev が認識しているデバイス情報を表示する** |
| **`udevmonitor`** | **`udevadm monitor`** | **カーネルの uevent と、udev ルールによるイベントを監視してコンソールに出力する** |
| **`udevcontrol`** | **`udevadm control`** | **udev を操作する**（動作・停止・ルールの再読み込みなど） |
| — | `udevadm trigger` | イベントを起こし直す |
| — | `udevadm settle` | 処理中のイベントが片付くまで待つ |
| — | `udevadm test` | ルールの動作を試す |

> **`udevadm` は、必ずサブコマンドを付けて使います。**
> `udevadm` だけでは動きません。
>
> **存在しない書き方**
>
> | 書き方 | 実在するか |
> |:--|:--:|
> | `udevadm info` / `udevadm monitor` / `udevadm control` | **する** |
> | `udev info` / `udev monitor`（スペース区切りで `udev`） | **しない** |
> | `udevadm show` | **しない** |

---

### udevadm info でデバイス情報を見る

**意味**

**udev が認識しているデバイスの情報**を表示します。
`/sys`（sysfs）上のパス、シンボリックリンク、属性などが分かります。

**例文**

```bash
$ udevadm info -q path -n /dev/sda1                  # sysfs上のパスだけを表示する
/devices/pci0000:00/0000:00:0d.0/host2/target2:0:0/2:0:0:0/block/sda/sda1

$ udevinfo -q path -n /dev/sda1                      # 古い書き方。結果は同じ
$ udevadm info -q all -n /dev/sda1                   # すべての情報を表示する
$ udevadm info -a -n /dev/sda1                       # 親をさかのぼって属性を表示する（ルール作成用）
$ udevadm info -q symlink -n /dev/sda1               # シンボリックリンクだけ表示する
```

**よく使うオプション**

| オプション | 意味 |
|:--|:--|
| **`-q 種類`** / `--query` | **表示する情報の種類**を指定する。`name` / `symlink` / `path` / `property` / `all` |
| **`-n ファイル`** / `--name` | **デバイスファイル名**で指定する（`/dev/sda1` など） |
| **`-p パス`** / `--path` | **`/sys` のパス**で指定する |
| **`-a`** / `--attribute-walk` | **ルールで使える属性を、親をさかのぼってすべて表示する** |
| **`-x`** / `--export` | シェルで読み込める形式で出力する |

**`-q` に指定できる種類**

| 種類 | 表示されるもの |
|:--|:--|
| **`path`** | **`/sys` 上のパス**（`/devices/pci0000:00/…`） |
| **`name`** | デバイスファイル名 |
| **`symlink`** | その機器を指すシンボリックリンク |
| **`property`** | 環境変数の形の属性 |
| **`all`** | **すべて** |

**結果画面の見方（`-q all` の場合）**

```bash
$ udevadm info -q all -n /dev/sda1                   # すべての情報を表示する
P: /devices/pci0000:00/0000:00:0d.0/host2/target2:0:0/2:0:0:0/block/sda/sda1
N: sda1
S: block/8:1
S: disk/by-id/ata-VBOX_HARDDISK_VB4c585906-aefd3dca-part1
S: disk/by-uuid/52abae61-09b5-4093-b66a-e2812fb964fc
```

| 先頭の記号 | 意味 | どこを見るか |
|:--|:--|:--|
| **`P:`** | **`/sys` 上のパス**（devpath） | 機器が物理的にどこにつながっているか |
| **`N:`** | **デバイスファイルの名前** | `/dev/` からの相対名 |
| **`S:`** | **シンボリックリンク** | **`disk/by-uuid/…` は `/etc/fstab` で使える安定した名前** |
| `E:` | 属性（環境変数の形） | ルールを書くときの材料 |

**補足**

- **`by-uuid` や `by-id` のリンクは udev が作っています。**ディスクの順番が変わっても同じ名前で指せるのは、この仕組みのおかげです

---

### udevadm monitor でイベントを見る

**意味**

**カーネルから送られてくる `uevent` と、udev ルールの処理後に出るイベントを、リアルタイムでコンソールに表示します。**
「機器を挿したときに何が起きているか」を確かめるためのコマンドです。

**例文**

```bash
$ sudo udevadm monitor                               # イベントを監視する（Ctrl+C で終了）
$ sudo udevmonitor                                   # 古い書き方。同じ動作
$ sudo udevadm monitor --kernel                      # カーネルからの uevent だけ見る
$ sudo udevadm monitor --udev                        # ルール処理後のイベントだけ見る
$ sudo udevadm monitor --property                    # 属性も一緒に表示する
```

**よく使うオプション**

| オプション | 意味 |
|:--|:--|
| **`-k`** / `--kernel` | **カーネルの `uevent`** だけ表示する |
| **`-u`** / `--udev` | **ルール処理後のイベント**だけ表示する |
| **`-p`** / `--property` | **イベントの属性も**表示する |
| `-s サブシステム` / `--subsystem-match` | 特定のサブシステムだけに絞る |

**使い方のコツ**

```text
  ① 別の端末で  udevadm monitor  を起動しておく
  ② USB メモリを挿す
  ③ 流れてくるイベントを見る
       → 何も出ない  … カーネルが機器を検出していない（ハード側かドライバの問題）
       → KERNEL は出るが UDEV が出ない … ルールの処理で止まっている
```

---

### udevadm control で udev を操作する

**意味**

**動いている udev デーモンの状態を操作します。**ルールを書き換えたあとの再読み込みが主な用途です。

**例文**

```bash
$ sudo udevadm control --reload                      # ルールファイルを読み込み直す
$ sudo udevcontrol --reload-rules                    # 古い書き方
$ sudo udevadm control --log-priority=debug          # ログを詳しく出すようにする
$ sudo udevadm control --stop-exec-queue             # イベントの実行を一時的に止める
$ sudo udevadm control --start-exec-queue            # 実行を再開する
$ sudo udevadm trigger                               # イベントを起こし直してルールを適用する
```

**よく使うオプション**

| オプション | 意味 |
|:--|:--|
| **`--reload`** | **ルールファイルを読み込み直す**（最頻出） |
| **`--log-priority=レベル`** | ログの詳しさを変える（`err` / `info` / `debug`） |
| **`--stop-exec-queue`** | イベントの実行を止める |
| **`--start-exec-queue`** | イベントの実行を再開する |

---

## udev.conf の設定項目

**`/etc/udev/udev.conf`** に書ける、主な設定です。

| 項目 | 意味 |
|:--|:--|
| **`udev_log`** | **ログの詳しさ**（`err` / `info` / `debug`） |
| **`children_max`** | **同時に処理するイベントの最大数** |
| **`exec_delay`** | ルールの `RUN` を実行する前に待つ秒数 |
| **`event_timeout`** | **イベントの処理を打ち切るまでの秒数**（既定 180 秒） |
| **`resolve_names`** | ユーザ名・グループ名を解決するタイミング（`early` / `late` / `never`） |
| **`timeout_signal`** | タイムアウト時に送るシグナル（既定 `SIGKILL`） |

**例文**

```bash
$ cat /etc/udev/udev.conf                            # udev本体の設定を確認する
udev_log="info"

$ sudo udevadm control --log-priority=debug          # 再起動せずにログレベルだけ変える
```

---

## 参考リンク

- [man 8 udevadm](https://man7.org/linux/man-pages/man8/udevadm.8.html)
- [man 7 udev（ルールの書き方）](https://man7.org/linux/man-pages/man7/udev.7.html)
- [man 5 udev.conf](https://man7.org/linux/man-pages/man5/udev.conf.5.html)
- [man 8 lspci](https://man7.org/linux/man-pages/man8/lspci.8.html)
- [man 8 lsusb](https://man7.org/linux/man-pages/man8/lsusb.8.html)
- [man 8 lsdev（procinfo）](https://manpages.debian.org/trixie/procinfo/lsdev.8.en.html)
- [man 5 proc](https://man7.org/linux/man-pages/man5/proc.5.html)

---

[← このフォルダの目次にもどる](./00_このフォルダにあるもの.md) ｜ [全体の目次にもどる](../README.md)
