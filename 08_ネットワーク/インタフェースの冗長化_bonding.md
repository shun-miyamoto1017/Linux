# インタフェースの冗長化 bonding

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★☆☆ |
| **Ping-t の範囲** | Linux2 / ネットワーク構成(主題205) — 高度なネットワーク構成 |
| **業務での使いどころ** | **NIC 1 枚の故障でサービスを止めないための定番構成**。オンプレのサーバは 2 ポート以上を束ねるのが前提。クラウドでは ENA の冗長化が裏でやってくれるが、ハイブリッド構成や専用線終端では今も自分で組む |

> **インタフェースの状態確認**は [アドレスとルーティングの確認](./アドレスとルーティングの確認.md)、
> **1 枚の NIC に複数アドレスを付ける話**は [IPアドレスの設定 ifconfigとip](./IPアドレスの設定_ifconfigとip.md) にまとめています。

---

## 目次

- [この環境では実測できていません](#この環境では実測できていません)
- [bonding とは](#bonding-とは)
- [マスターとスレーブとアクティブ](#マスターとスレーブとアクティブ)
- [7つのモード](#7つのモード)
  - [冗長化のためのモード](#冗長化のためのモード)
  - [負荷分散のためのモード](#負荷分散のためのモード)
  - [スイッチ側の設定が要るもの](#スイッチ側の設定が要るもの)
- [モードの選び方](#モードの選び方)
- [設定する](#設定する)
  - [nmcli で組む](#nmcli-で組む)
  - [状態を確認する](#状態を確認する)
- [まぎらわしい用語の整理](#まぎらわしい用語の整理)
- [運用上の注意](#運用上の注意)
- [参考リンク](#参考リンク)

---

## この環境では実測できていません

**このノートの内容は、ドキュメントに基づく記述です。**
検証環境のカーネルに `bonding` モジュールが無いため、実際の動作は確認できていません。

```bash
$ modprobe bonding                          # モジュールを読み込もうとする
$ ip link add bond0 type bond               # bond インタフェースを作ろうとする
$ ls /proc/net/bonding                      # 状態ファイルがあるか確認する
```

```text
modprobe: FATAL: Module bonding not found in directory /lib/modules/6.18.44-fc-v37
Error: Unknown device type.
ls: cannot access '/proc/net/bonding': No such file or directory
```

**`nmcli`（NetworkManager）も入っていません。**
以下のコマンド例は**書式を示すもので、この環境での実行結果ではありません。**
実機で試す際は、手元で必ず挙動を確認してください。

---

## bonding とは

**bonding は、複数の物理 NIC を 1 本の論理インタフェースに束ねる仕組み**です。
Linux では **`bonding` カーネルモジュール**が提供します。

```text
   ┌──────────────────────────┐
   │        bond0             │  ← 論理インタフェース（IP はここに付ける）
   └────┬────────────┬────────┘
        │            │
   ┌────▼────┐  ┌────▼────┐
   │  eth0   │  │  eth1   │      ← 物理 NIC
   └─────────┘  └─────────┘
```

**得られるものは2つ**です。

| 目的 | 効果 |
|:--|:--|
| **冗長化** | **1 枚が故障しても、残りで通信を継続できる** |
| **帯域の増加** | 複数のリンクにトラフィックを分散し、合計の帯域を増やす |

**どちらを重視するかでモードが変わります。** 両方を同時に得られるモードもあります。

**IP アドレスは `bond0` に割り当てます。** 物理側には付けません。

> **チーミング（teaming）** は bonding の後継として作られた別実装（`teamd`）ですが、
> **RHEL 9 / Oracle Linux 9 で非推奨**となり、bonding に一本化されました。
> Oracle Linux 9 のリリースノートは
> 「The teamd service, and the libteam library, and support for configuring network teams
> are deprecated in favor of network bonds.」と明記しています。
> 試験も実務も bonding を押さえれば足ります。

---

## マスターとスレーブとアクティブ

**bonding では、3つの呼び名を使い分けます。**

| 呼び名 | 指すもの |
|:--|:--|
| **マスター（master）** | **束ねた結果できる論理インタフェース**（`bond0`） |
| **スレーブ（slave）** | **束ねられる個々の物理インタフェース**（`eth0`、`eth1`） |
| **アクティブ（active）** | **その時点で実際に送受信を担っているスレーブ** |

```text
   マスター  bond0      … 1 つ。IP を持つ。上位から見える唯一のインタフェース
   スレーブ  eth0, eth1 … 複数。IP を持たない
   アクティブ eth0      … スレーブのうち、いま使われているもの
```

**`active-backup` では常に 1 本だけがアクティブ**です。
負荷分散のモードでは、複数がアクティブになります。

---

## 7つのモード

**モードは番号でも名前でも指定できます。**

| 番号 | 名前 | 種類 | スイッチの設定 |
|:--|:--|:--|:--|
| **0** | **`balance-rr`** | 送信をラウンドロビンで分散 | 要る |
| **1** | **`active-backup`** | **1 本だけ使い、障害時に切り替える** | **不要** |
| **2** | **`balance-xor`** | **ハッシュで分散**（既定 `xmit_hash_policy=layer2` は送信元と宛先の MAC、およびパケット種別 ID の XOR） | 要る |
| 3 | `broadcast` | 全スレーブに同じものを送る | 要る |
| **4** | **`802.3ad`** | **LACP によるリンクアグリゲーション** | **要る（LACP 対応）** |
| **5** | **`balance-tlb`** | **負荷に応じて送信だけ分散** | **不要** |
| **6** | **`balance-alb`** | **負荷に応じて送信と受信の両方を分散** | **不要** |

**既定は `balance-rr`（0）**です。

### 冗長化のためのモード

**`active-backup`（1）** が冗長化の基本形です。

```text
   [bond0]
     ├── eth0  ← アクティブ。ここだけを使う
     └── eth1  ← 待機。eth0 が落ちたら昇格する
```

```text
   通常時     eth0 だけにトラフィックが流れる
              eth1 のカウンタはゼロのまま

   eth0 障害  eth1 がアクティブに昇格し、通信が継続する
```

**トラフィック監視ツールで見ると、片方にしかカウンタが立たない**のが特徴です。
「冗長化しているのに帯域が増えていない」のではなく、**そういうモード**です。

**スイッチ側の設定が不要**なので、相手側の機器を選ばず最も導入しやすい構成です。

### 負荷分散のためのモード

| モード | 分散するもの | 分散のしかた |
|:--|:--|:--|
| `balance-rr`（0） | 送信 | **パケットごとに順番に**振り分ける |
| `balance-xor`（2） | 送信 | **宛先などのハッシュ**で決める。同じ宛先は常に同じ NIC |
| `balance-tlb`（5） | **送信のみ** | **各スレーブの負荷**に応じて振り分ける |
| `balance-alb`（6） | **送信と受信** | `balance-tlb` に受信の分散を加えたもの |

**`balance-tlb` と `balance-alb` の違いが最もよく問われます。**

```text
   tlb … Transmit Load Balancing        → 送信だけ
   alb … Adaptive Load Balancing        → 送信 + 受信
```

**`balance-rr` はパケット単位で分散する**ため帯域は出やすいのですが、
**到着順が入れ替わり、TCP の再送が増えることがあります。**
`balance-xor` は同じ通信が同じ NIC を通るため、順序が乱れません。

### スイッチ側の設定が要るもの

**`802.3ad`（4）は LACP を使うリンクアグリゲーション**です。

```text
   リンクアグリゲーション
     機器間の複数の物理リンクを束ねて1本の論理回線として扱う技術
        ↓
     帯域が増え、一部のリンクが切れても残りで通信が続く
        ↓
     標準規格が IEEE 802.3ad、制御プロトコルが LACP
```

**LACP は、両端の機器が互いに「束ねる合意」を取るためのプロトコル**です。
したがって **スイッチ側にも LACP の設定が必要**で、
**サーバ側だけ設定しても動きません。**

```text
   スイッチ側の設定が不要    …  active-backup, balance-tlb, balance-alb
   スイッチ側の設定が必要    …  balance-rr, balance-xor, broadcast, 802.3ad
```

**この区別は実務で効きます。**
スイッチを触れない環境（共用ラック、データセンター事業者の機器）では、
**選べるのは `active-backup` / `balance-tlb` / `balance-alb` の3つ**です。

---

## モードの選び方

```text
   とにかく止めたくない / スイッチを触れない
        → active-backup（1）

   帯域も増やしたい / スイッチを設定できる
        → 802.3ad（4）        ← 現在の標準的な選択

   スイッチは触れないが送信の帯域は増やしたい
        → balance-tlb（5）

   スイッチは触れないが送受信とも増やしたい
        → balance-alb（6）
```

**迷ったら `active-backup`**です。
効果が読みやすく、相手側の機器に依存せず、障害時の挙動が単純だからです。

---

## 設定する

### nmcli で組む

**手順は3段階**です。

```bash
$ nmcli connection add type bond con-name bond0 ifname bond0 mode active-backup   # ① マスターを作る
$ nmcli connection add type bond-slave con-name bond0-eth0 ifname eth0 master bond0   # ② スレーブを従属させる
$ nmcli connection add type bond-slave con-name bond0-eth1 ifname eth1 master bond0   # ③ もう1枚も従属させる
```

> **スレーブ側の書式には新旧があります。**
> `type bond-slave` は `nmcli-examples(5)` に載っている書き方で、試験でもこの形で問われます。
> 一方、現行の RHEL / Oracle Linux の公式手順は次の形です。
>
> ```text
> nmcli connection add type ethernet slave-type bond con-name bond0-eth0 ifname eth0 master bond0
> ```
>
> さらに NetworkManager 側では **master / slave から controller / port への用語置き換え**が進んでいます
> （1.42 で D-Bus プロパティ `Controller` を導入、1.58 で `nmcli connection show` の列名が `PORT` に）。
> **手元のバージョンの man を確認**してください。

**最後にマスターへ IP を割り当てます。**

```bash
$ nmcli connection modify bond0 ipv4.method manual ipv4.addresses 192.168.1.10/24   # ④ IP を設定する
$ nmcli connection modify bond0 ipv4.gateway 192.168.1.1                            # ⑤ ゲートウェイを設定する
$ nmcli connection up bond0                                                         # ⑥ 有効にする
```

```text
   ① type bond        でマスターを作り、mode でポリシーを決める
   ② type bond-slave  で物理 NIC を master 指定して従属させる
   ③ IP はマスター側にだけ付ける
```

**`mode` はマスター側にだけ指定**します。スレーブ側には書きません。

### 状態を確認する

```bash
$ ip addr show                              # MASTER / SLAVE のフラグを確認する
```

物理側に **`SLAVE`**、`bond0` に **`MASTER`** のフラグが付きます。

**より詳しい状態は `/proc/net/bonding/bond0`** で読めます。

```bash
$ cat /proc/net/bonding/bond0               # bonding の詳細な状態を見る
```

ここには **`Bonding Mode`（現在のモード）、`MII Status`（各スレーブのリンク状態）、
`Link Failure Count`（各スレーブのリンク障害回数）、`Permanent HW addr`** などが並びます。
**`Currently Active Slave`（アクティブなスレーブ）は
`active-backup` / `balance-tlb` / `balance-alb` のときだけ**表示されます。
**障害後に「いつ切り替わったか」を調べるときの第一の情報源**です。

> **実測できていないこと** … この環境には bonding モジュールが無いため、
> `ip addr show` の MASTER / SLAVE 表示も `/proc/net/bonding/bond0` の内容も確認していません。

---

## まぎらわしい用語の整理

| 用語 | 正体 | bonding との関係 |
|:--|:--|:--|
| **bonding** | **複数 NIC を 1 本に束ねる** | — |
| **マルチホーム** | **外部への接続経路を複数持つ構成** | 別概念。IP エイリアシングでも実現できる |
| **IP エイリアシング** | **1 枚の NIC に複数の IP を付ける** | 逆方向。束ねるのではなく増やす |
| **NetworkManager** | ネットワーク設定を動的に管理するプログラム | bonding の設定手段の 1 つ |
| **kdump** | カーネルクラッシュ時にメモリをダンプする | まったくの別物 |

```text
   bonding          …  NIC を 減らして 見せる（2枚 → bond0 1本）
   IP エイリアシング …  アドレスを 増やす    （1枚 → IP 2つ）
```

**bonding は既定で設定されているものではありません。**
`bonding` モジュールを読み込み、明示的に構成して初めて使えます。

---

## 運用上の注意

**1. 切り替わりを実際に試す**

```text
   構築したら、必ずケーブルを片方抜いて試験する
        → 何秒で切り替わるか
        → セッションが切れるか、保たれるか
        → 戻したときに元へ戻るか（primary の設定次第）
```

**試験していない冗長化は、冗長化ではありません。**

**2. 監視対象に入れる**

```text
   /proc/net/bonding/bond0 の
     ・現在のアクティブスレーブ
     ・各スレーブの MII Status（up / down）
        ↓
   片肺運転に気づかないまま、残り 1 本も落ちる、が最悪のパターン
```

**片方が落ちても通信は続くので、監視しないと誰も気づきません。**
**スレーブ単位の状態を必ず監視項目に入れてください。**

**3. リンク監視の方式を決める**

| 方式 | 見るもの | 弱点 |
|:--|:--|:--|
| **MII 監視**（`miimon`） | **NIC のリンク状態** | ケーブルは生きているが先が死んでいる場合を検知できない |
| **ARP 監視**（`arp_interval` + `arp_ip_target`） | 指定先への ARP の応答 | **`arp_interval` は間隔、監視先は `arp_ip_target` で別途指定**する |

**スイッチの先で障害が起きる構成なら、ARP 監視を検討してください。**

**4. スイッチ側と食い違わせない**

```text
   サーバ側 802.3ad / スイッチ側 設定なし
        → LACP の合意が取れず、通信が不安定になる

   サーバ側 balance-rr / スイッチ側 設定なし
        → 同じ MAC が複数ポートから見えて、スイッチが混乱する
          （ボンドの全スレーブが同じ MAC を共有することから起きる。
            カーネル公式ドキュメントに明記はなく、現場で広く知られた挙動）
```

**「スイッチ側の設定が必要かどうか」の表を、設計時に必ず確認してください。**

---

## 参考リンク

- [Linux Ethernet Bonding Driver HOWTO（カーネル公式）](https://docs.kernel.org/networking/bonding.html)
- [Red Hat Enterprise Linux 7 ネットワークガイド — チャネルボンディング](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/networking_guide/sec-using_channel_bonding)
- [man 1 nmcli](https://man7.org/linux/man-pages/man1/nmcli.1.html)

---

[← 全体の目次にもどる](../README.md)
