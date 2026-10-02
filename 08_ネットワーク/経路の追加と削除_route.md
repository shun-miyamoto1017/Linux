# 経路の追加と削除 route

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★☆ |
| **Ping-t の範囲** | Linux1 / ネットワークの基礎(主題109) — 基本的なネットワーク構成 |
| **業務での使いどころ** | **「同じ VPC なのに繋がらない」の正体はたいてい経路**。オンプレとの VPN、Transit Gateway 経由、検証用のセグメント追加。AWS のルートテーブルを触るときも、頭の中でやっていることは `route add` と同じ |

> **経路表の読み方と `ip route` の全体像**は [アドレスとルーティングの確認](./アドレスとルーティングの確認.md)、
> **経路表を `netstat -r` で見る話**は [ネットワーク状態の確認 netstat](./ネットワーク状態の確認_netstat.md) にまとめています。
> このノートは **`route` コマンドの書式**に絞っています。

---

## 目次

- [ルーティングとは何をしているのか](#ルーティングとは何をしているのか)
- [経路表を表示する](#経路表を表示する)
  - [結果画面の見方](#結果画面の見方)
- [経路を追加する](#経路を追加する)
  - [ネットワーク宛の経路](#ネットワーク宛の経路)
  - [ホスト宛の経路](#ホスト宛の経路)
  - [ハイフンの有無が決まっている](#ハイフンの有無が決まっている)
- [デフォルトゲートウェイ](#デフォルトゲートウェイ)
  - [専用の書式がある](#専用の書式がある)
  - [複数あるときはメトリックで決まる](#複数あるときはメトリックで決まる)
- [経路を削除する](#経路を削除する)
- [ip route での書き方](#ip-route-での書き方)
  - [route の書式は通らない](#route-の書式は通らない)
- [route と ip route の対応表](#route-と-ip-route-の対応表)
- [恒久化する](#恒久化する)
- [参考リンク](#参考リンク)

---

## ルーティングとは何をしているのか

**パケットは、いくつものルータを経由して宛先へ運ばれます。**
その各中継点で「**次にどこへ渡すか**」を決める処理がルーティングです。

```text
  [自ホスト] ──▶ [ルータA] ──▶ [ルータB] ──▶ [宛先]
       │             │             │
       └─ どこへ渡す？ └─ どこへ渡す？ └─ どこへ渡す？
              ↑ それぞれが自分のルーティングテーブルを見て決める
```

**判断材料がルーティングテーブル（経路表）**です。

| 混同しやすいもの | 本当の役割 |
|:--|:--|
| **ARP** | **IP アドレスと MAC アドレスの対応付け**。ルーティングとは別 |
| 暗号化 | IPsec や TLS の仕事 |
| プロトコルの選択 | アプリケーションが決めること |

> ARP については [ARPキャッシュの操作 arp](./ARPキャッシュの操作_arp.md) を参照してください。

---

## 経路表を表示する

**`route` は引数なしで実行すると経路表を表示します。**

```bash
$ route -n                                  # 名前解決せず経路表を表示する
```

```text
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         192.0.2.1       0.0.0.0         UG    0      0        0 eth0
192.0.2.0       0.0.0.0         255.255.255.0   U     0      0        0 eth0
```

**`netstat -r` でも経路表は見られますが、列が違います。**

```bash
$ netstat -rn                               # netstat で経路表を見る
$ netstat -rne                              # -e を足すと route -n と同じ列になる
```

```text
Destination     Gateway         Genmask         Flags   MSS Window  irtt Iface
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
```

**素の `netstat -r` には、このノートで重視する `Metric` 列がありません。**
**メトリックまで見たいなら `route -n` か `netstat -rne`** を使ってください。

### 結果画面の見方

| 列 | 意味 |
|:--|:--|
| **`Destination`** | **宛先のネットワークアドレス**。`0.0.0.0` は「それ以外すべて」＝デフォルト |
| **`Gateway`** | **次に渡す相手**。`0.0.0.0` は「ゲートウェイ不要」＝直接届く |
| **`Genmask`** | 宛先のネットマスク。`255.255.255.255` ならホスト1台宛 |
| **`Flags`** | `U`＝経路が有効、`G`＝ゲートウェイ経由、`H`＝ホスト宛 |
| **`Metric`** | **経路のコスト。同じ宛先が複数あるとき、小さいほうが選ばれる** |
| `Ref` | 参照回数（Linux では使われない） |
| `Use` | この経路が検索された回数 |
| **`Iface`** | 出ていくインタフェース |

```text
   Gateway が 0.0.0.0 かつ Flags が U   → 同じネットワーク内。直接届く
   Gateway に IP があり Flags が UG     → その IP のルータに渡す
   Flags に H がある                     → ホスト1台だけへの経路
```

**`-n` を付けないと、`0.0.0.0` が `default` と表示されたり、逆引きで待たされたりします。**
**調査では `route -n` を使ってください。**

---

## 経路を追加する

```text
route add [-net|-host] 宛先 [netmask マスク] [gw ゲートウェイ] [metric 値] [dev インタフェース]
```

### ネットワーク宛の経路

**宛先の書き方は2通り**あります。実測で両方を確かめます。

```bash
$ route add -net 10.9.0.0 netmask 255.255.255.0 gw 192.0.2.1   # netmask で指定する
$ route add -net 10.9.1.0/24 gw 192.0.2.1                      # プレフィックスで指定する
```

どちらも成功し、結果は同じ形で入ります。

```bash
$ route -n                                  # 追加された経路を確認する
```

```text
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         192.0.2.1       0.0.0.0         UG    0      0        0 eth0
10.9.0.0        192.0.2.1       255.255.255.0   UG    0      0        0 eth0
10.9.1.0        192.0.2.1       255.255.255.0   UG    0      0        0 eth0
192.0.2.0       0.0.0.0         255.255.255.0   U     0      0        0 eth0
```

**`Genmask` はどちらも `255.255.255.0` になっています。** 書き方が違うだけで同じ意味です。

### ホスト宛の経路

**特定の1台だけへの経路は `-host`** です。

```bash
$ route add -host 10.9.2.5 gw 192.0.2.1     # ホスト1台への経路を足す
$ route -n | grep 10.9.2.5                  # 追加されたか確認する
```

```text
10.9.2.5        192.0.2.1       255.255.255.255 UGH   0      0        0 eth0
```

**`Genmask` が `255.255.255.255`、`Flags` に `H`** が付きます。

### ハイフンの有無が決まっている

**ここが試験でも実務でも引っかかるところです。**

```text
   add / del        … ハイフン無し   （サブコマンド）
   -net / -host     … ハイフン有り   （宛先の種別）
   netmask / gw / metric / dev … ハイフン無し（キーワード）
```

間違えるとどうなるか、実測しました。

```bash
$ route -add -net 10.9.3.0/24 gw 192.0.2.1  # add にハイフンを付けた
```

```text
route: invalid option -- 'a'
route: invalid option -- 'd'
route: invalid option -- 'd'
    inet (DARPA Internet) inet6 (IPv6) ax25 (AMPR AX.25) 
（以下、使い方の表示が続く。全 20 行）
```

**`add` の `d` が 2 つあるので `invalid option` は 3 行出ます。**
**終了ステータスは 0** なので、スクリプトで `$?` を見ても失敗を検知できません。

```bash
$ route add net 10.9.3.0/24 gw 192.0.2.1    # -net のハイフンを落とした
```

```text
net: No address associated with name
```

**`net` がホスト名として名前解決されようとしています。**

```bash
$ route add -net 10.9.3.0/24 -gw 192.0.2.1  # gw にハイフンを付けた
```

```text
route: invalid option -- 'g'
route: invalid option -- 'w'
```

**`add` にハイフンは付けない。`-net` / `-host` にはハイフンを付ける。`gw` には付けない。**

---

## デフォルトゲートウェイ

**デフォルトゲートウェイは、経路表に載っていない宛先をすべて任せる相手**です。
通常は**自ホストと同じネットワークにいて、外部と繋がっているルータ**の IP を指定します。

### 専用の書式がある

**`-net` / `-host` と宛先アドレスの代わりに、`default` というキーワードを置きます。**

```text
route add default gw ゲートウェイのIP
```

```bash
$ route add default gw 192.0.2.1            # デフォルトゲートウェイを設定する
```

**この語順は固定**です。次のような書き方は通りません。

```text
   ✗ route add gw default 192.0.2.1   …  default と gw が逆
                                          → gw: No address associated with name
   ✗ route default gw 192.0.2.1       …  add が無い
                                          → 使い方の表示が出る
```

> **`route add -net default gw 192.0.2.1` は通ります。**
> net-tools は `-net default` を `0.0.0.0/0` として受け付けるためです（実測）。
> ただし既存のデフォルト経路と重複すると `SIOCADDRT: File exists` になります。
> **書式としては `route add default gw ...` が素直**なので、こちらを使ってください。

### 複数あるときはメトリックで決まる

**`metric` を指定して、デフォルト経路を2本入れてみます。**

```bash
$ route add default gw 192.0.2.1 metric 100   # メトリック 100 でもう1本足す
$ route -n                                    # 2本並んだことを確認する
```

```text
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         192.0.2.1       0.0.0.0         UG    0      0        0 eth0
0.0.0.0         192.0.2.1       0.0.0.0         UG    100    0        0 eth0
10.9.1.0        192.0.2.1       255.255.255.0   UG    0      0        0 eth0
192.0.2.0       0.0.0.0         255.255.255.0   U     0      0        0 eth0
```

**同じ宛先（`0.0.0.0`）の経路が2本共存できます。**
このとき**実際に使われるのはメトリックの小さいほう**です。上の例なら `Metric 0` の経路が使われます。

```text
   同じ宛先が複数ある  →  Metric が小さいほうを選ぶ
                          （TTL やホップ数では決まらない）
```

**デフォルトゲートウェイは普通 1 ホップ先**なので、ホップ数では優劣が付きません。
**選択の基準はメトリックだけ**だと覚えてください。

> 経路が重複していても通信できなくなるわけではありません。
> どちらが実際に選ばれているかは `traceroute` の第1ホップを見れば分かります。

---

## 経路を削除する

```text
route del [-net|-host] 宛先 [gw ゲートウェイ] [metric 値]
```

**識別できるなら、宛先だけの指定で消せます。**

```bash
$ route del -net 10.9.0.0/24                # ネットワーク宛の経路を消す
$ route del -host 10.9.2.5                  # ホスト宛の経路を消す
```

どちらも終了ステータス 0 で成功しました。

**`-net` / `-host` を省くと失敗します。** 実測します。

```bash
$ route del 10.9.1.0/24                     # -net を付けずに消そうとする
```

```text
route: netmask 000000ff doesn't make sense with host route
Usage: inet_route [-vF] del {-host|-net} Target[/prefix] [gw Gw] [metric M] [[dev] If]
（以下、使い方の表示が続く）
```

**省略するとホスト宛（`-host`）とみなされ、プレフィックス付きの宛先と矛盾します。**
**削除でも `-net` / `-host` は明示してください。**

**`remove` というキーワードはありません。**

```bash
$ route remove -net 10.9.1.0/24             # remove と書いてみる
```

```text
Usage: route [-nNvee] [-FC] [<AF>]           List kernel routing tables
       route [-v] [-FC] {add|del|flush} ...  Modify routing table for AF.
```

**使えるのは `add` / `del` / `flush` だ**と、使い方の表示そのものが教えてくれます。

**ただし IPv4 では `flush` は実装されていません。** 実測します。

```bash
$ route flush                               # 経路表を全消ししてみる
```

```text
Flushing `inet' routing table not supported
Usage: inet_route [-vF] del {-host|-net} Target[/prefix] [gw Gw] [metric M] [[dev] If]
```

**実際に使えるのは `add` と `del` の2つ**です。全消しは `ip route flush` を使ってください。

**メトリック付きで足した経路は、メトリックも指定して消します。**

```bash
$ route del default gw 192.0.2.1 metric 100   # メトリックまで指定して消す
```

> **メトリックを省くと、消したいほうではなく `metric 0` の経路が消えます。**
> 隔離した環境で試すと、`metric 0` と `metric 100` が並んだ状態で
> `route del default gw 192.0.2.1`（メトリック省略）を実行したところ、
> **エラーも警告も出さずに `metric 0`、つまり実際に使われている経路のほうが消えました。**
> リモート作業中なら、その瞬間に自分の接続が切れます。
> **デフォルト経路を消すときは、必ずメトリックまで指定してください。**

---

## ip route での書き方

**`route` は net-tools の古いコマンド**で、現在の標準は `ip route` です。

```bash
$ ip route show                             # 経路表を表示する
```

```text
default via 192.0.2.1 dev eth0 
192.0.2.0/24 dev eth0 proto kernel scope link src 192.0.2.2 
```

```bash
$ ip route add 10.9.5.0/24 via 192.0.2.1    # 経路を足す
$ ip route add default via 192.0.2.1 metric 200   # デフォルト経路を足す
$ ip route del 10.9.5.0/24                  # 経路を消す
```

**`gw` ではなく `via`** です。ここだけ置き換えれば、あとは素直に読めます。

### route の書式は通らない

**`ip route` に `route` の書式を混ぜると、はっきりエラーになります。** 実測します。

```bash
$ ip route add -net 10.9.6.0/24 via 192.0.2.1        # -net を付けてみる
```

```text
Error: any valid prefix is expected rather than "-net".
```

```bash
$ ip route add 10.9.6.0 netmask 255.255.255.0 via 192.0.2.1   # netmask を使ってみる
```

```text
Error: either "to" is duplicate, or "netmask" is a garbage.
```

```text
   ip route に使えないもの
     ✗ -net / -host     → プレフィックス表記だけを使う（10.9.6.0/24）
     ✗ netmask          → 同上
     ✗ gw               → via を使う
```

---

## route と ip route の対応表

| やりたいこと | `route`（古い） | `ip route`（新しい） |
|:--|:--|:--|
| 経路表を表示 | `route -n` | `ip route show` |
| ネットワーク宛の経路を追加 | `route add -net 10.9.0.0/24 gw 192.0.2.1` | `ip route add 10.9.0.0/24 via 192.0.2.1` |
| ホスト宛の経路を追加 | `route add -host 10.9.2.5 gw 192.0.2.1` | `ip route add 10.9.2.5 via 192.0.2.1` |
| デフォルトゲートウェイを追加 | `route add default gw 192.0.2.1` | `ip route add default via 192.0.2.1` |
| 経路を削除 | `route del -net 10.9.0.0/24` | `ip route del 10.9.0.0/24` |
| デフォルトを削除 | `route del default gw 192.0.2.1` | `ip route del default` |
| メトリックの指定 | `metric 100` | `metric 100` |
| 出力インタフェースの指定 | `dev eth0` | `dev eth0` |

**宛先の書き方の違い**

```text
   route     …  -net 10.9.0.0 netmask 255.255.255.0
                -net 10.9.0.0/24              （どちらでもよい）

   ip route  …  10.9.0.0/24                   （プレフィックス表記のみ）
```

---

## 恒久化する

**`route add` も `ip route add` も、再起動すると消えます。**
残したい場合はディストリビューションの設定に書きます。

| 環境 | 書く場所 |
|:--|:--|
| RHEL 系（NetworkManager） | `nmcli connection modify <接続名> +ipv4.routes "10.9.0.0/24 192.0.2.1"` |
| RHEL 7 以前 | `/etc/sysconfig/network-scripts/route-eth0` |
| Ubuntu（netplan） | `/etc/netplan/*.yaml` の `routes:` |
| Debian（ifupdown） | `/etc/network/interfaces` の `up ip route add ...` |

> 設定ファイルの詳細は [ネットワーク設定ファイル](./ネットワーク設定ファイル.md) を参照してください。

**確認の手順**

```text
  1. route -n / ip route show で今の経路を控える（作業前の記録）
  2. 経路を足す
  3. ping や traceroute で意図どおりに流れるか確かめる
  4. 設定ファイルに書く
  5. 再起動するか nmcli connection up で読み直し、もう一度 route -n で確かめる
```

**4 を飛ばすと、次の再起動で戻ります。**
**5 を飛ばすと、書式ミスに再起動するまで気づきません。** どちらもよくある事故です。

> **デフォルト経路を消すときは特に注意してください。**
> リモート作業中に `route del default` を打つと、その瞬間に自分の ssh が切れます。
> 消して足すのではなく、**先に新しい経路をメトリック小で足してから古いほうを消す**か、
> `at` や `cron` で「5 分後に元に戻す」保険を仕掛けてから作業してください。

---

## 参考リンク

- [man 8 route](https://man7.org/linux/man-pages/man8/route.8.html)
- [man 8 ip-route](https://man7.org/linux/man-pages/man8/ip-route.8.html)
- [man 8 netstat](https://man7.org/linux/man-pages/man8/netstat.8.html)

---

[← 全体の目次にもどる](../README.md)
