# ネットワークの基礎知識_サブネットとMTUとホスト名

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★☆ |
| **Ping-t の範囲** | Linux1 / ネットワークの基礎(主題109)、Linux2 / ネットワーク設定 |
| **業務での使いどころ** | **設計レビューで必ず聞かれる「そのサブネットで何台入るか」と、
「MTU はいくつか」。**クラウドでも VPC の CIDR 設計と、VPN/オーバーレイ経由の MTU 調整で毎回出てくる |

> **`ip` コマンドの使い方そのもの**は
> [アドレスとルーティングの確認](./アドレスとルーティングの確認.md)、
> **設定ファイルでの恒久化**は
> [ネットワーク設定ファイル](./ネットワーク設定ファイル.md) にあります。

---

## 目次

- [サブネットマスクとプレフィックス](#サブネットマスクとプレフィックス)
- [MTU とジャンボフレーム](#mtu-とジャンボフレーム)
- [ホスト名と ifup / ifdown](#ホスト名と-ifup--ifdown)
  - [hostname コマンド](#hostname-コマンド)
  - [hostname のオプション一覧](#hostname-のオプション一覧)
  - [ifup と ifdown](#ifup-と-ifdown)
- [参考リンク](#参考リンク)

---

## サブネットマスクとプレフィックス

**同じことを 2 通りで表します。**

| プレフィックス | サブネットマスク | ホスト数（使える数） |
|:--|:--|--:|
| **`/24`** | **255.255.255.0** | 254 |
| `/25` | 255.255.255.128 | 126 |
| `/26` | 255.255.255.192 | 62 |
| **`/16`** | **255.255.0.0** | 65534 |
| `/8` | 255.0.0.0 | 16777214 |
| **`/32`** | 255.255.255.255 | **1（そのアドレスだけ）** |
| **`/0`** | 0.0.0.0 | **すべて（default 経路）** |

**プレフィックスは「先頭から何ビットがネットワーク部か」**を表します。

```text
 10.0.1.25/24

 10.0.1.  25
 └──┬──┘  └┬┘
 ネットワーク部  ホスト部
  （24ビット）  （8ビット）

 → 同じ 10.0.1.x 同士なら、ルータを経由せず直接やりとりできる
```

**サブネットマスクを間違えるとどうなるか**

```text
 正しい   10.0.1.25/24 → 10.0.1.30 は「同じネットワーク」→ 直接届く
 誤り     10.0.1.25/25 → 10.0.1.30 とは同じネットワークのまま（どちらも 0-127 の範囲）
          10.0.1.25/28 → 10.0.1.30 は「別のネットワーク」→ ゲートウェイ経由になり、届かないことがある
```

**「同じセグメントのはずの相手に届かない」ときは、サブネットマスクの確認**が定番です。

```bash
$ ip a show eth0 | grep inet         # 自分のプレフィックスを確認する
    inet 10.0.1.25/24 brd 10.0.1.255 scope global dynamic eth0
```

**使えるホスト数が「−2」なのはなぜか**

```text
 ネットワークアドレス（ホスト部が全部 0）… そのネットワーク自体を指すので機器には使えない
 ブロードキャストアドレス（全部 1）      … 全員宛なので機器には使えない
```

> **AWS の VPC では、さらに各サブネットの先頭 4 つと末尾 1 つ、計 5 つが予約**されています。
> `/24` のサブネットで使えるのは **251 個**です。

---

## MTU とジャンボフレーム

**MTU（Maximum Transmission Unit）は、1 回に送れるデータの最大サイズ**です。
**イーサネットの標準は 1500 バイト**。

```text
   MTU 1500 を超えるフレームを扱うこと  →  ジャンボフレーム
```

**大きなデータを少ない回数で送れるので、高速回線での転送効率が上がります。**
一般的には **9000 バイト**が使われます。

**確認は `ip link show` でも `ip addr show` でもできます。**

```bash
$ ip link show lo                    # MTU を確認する
```

```text
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
```

> **ループバック（`lo`）の 65536 はカーネルの既定値**で、ジャンボフレームとは関係ありません。
> 外に出ないので大きくても困らない、というだけです。

**判断するのは物理 NIC の値です。物理 NIC の `mtu` が 1500 を超えていれば、
ジャンボフレームの設定が入っています。**

**変更は `ip link set`** です。

```bash
$ sudo ip link set eth0 mtu 9000     # ジャンボフレームを有効にする
$ ip link show eth0 | head -1        # 反映されたか確認する
```

```text
4: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9000 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
```

**`ifconfig` でも設定できます。**

```bash
$ sudo ifconfig eth0 mtu 9000        # 古いコマンドでの書き方
```

**ジャンボフレームを使うときの前提**

```text
   経路上の 全ての機器 が対応している必要がある
        サーバの NIC、スイッチ、ルータ、相手側のサーバ
        ↓
   1 箇所でも 1500 のままだと、そこでフラグメントされるか破棄される
        → 「大きいファイルだけ転送が止まる」という症状になる
```

**片側だけ 9000 にするのが最もありがちな事故**です。
必ず両端と経路上の機器をそろえてください。

**実際に通るかは `ping -M do -s` で確かめられます。**

```bash
$ ping -c 1 -M do -s 8972 10.0.0.5   # 分割せずに 9000 バイト分を送れるか
```

```text
   ping のデータサイズ 8972 + ICMP ヘッダ 8 + IP ヘッダ 20 = 9000
```

> クラウドでは AWS の一部インスタンスが既定で **9001**、
> Azure や GCP はサービスによって異なります。
> AWS の公表値では **Transit Gateway 経由が 8500**、**Site-to-Site VPN 経由が 1500** です。
> さらに IPsec のヘッダ分だけ実効ペイロードは下がるため、
> **設計時に経路全体の MTU を確認してください。**

> `ping -M do` の詳細は [疎通確認 pingとtraceroute](./疎通確認_pingとtraceroute.md) を参照してください。

---

## ホスト名と ifup / ifdown

### hostname コマンド

**意味** … **自分のホスト名を表示・変更する**

```bash
$ hostname                           # 現在のホスト名を表示する
web01

$ hostname -f                        # FQDN（完全修飾ドメイン名）を表示する
web01.internal.example.com

$ hostname -i                        # ホスト名に対応する IP を表示する
10.0.1.25

$ sudo hostname web02                # 一時的に変更する（再起動で戻る）
```

**恒久的に変更するのは `hostnamectl`**

```bash
$ hostnamectl                        # 現在の設定を詳しく見る
$ sudo hostnamectl set-hostname web02.internal.example.com   # 恒久的に変更する
```

**`hostnamectl set-hostname` は `/etc/hostname` に書き込みます。**
`hostname` コマンドだけの変更は**再起動で消えます**。

| コマンド | 効果 | 恒久か |
|:--|:--|:--|
| **`hostname`**（引数なし） | **表示する** | — |
| `hostname 新しい名前` | その場で変える | **消える** |
| **`hostnamectl set-hostname 名前`** | **`/etc/hostname` に書く** | **残る** |

> **ホスト名を変えたら `/etc/hosts` も合わせます。**
> `127.0.0.1` の行に古い名前が残っていると、**`sudo` が数秒固まる**などの症状が出ます。

### hostname のオプション一覧

**`hostname` は、名前まわりの情報をひととおり表示できます。**
`/etc/hosts` に FQDN を書いた状態で、実測で並べます。

```bash
$ cat /etc/hosts                     # 検証用の設定を確認する
```

```text
192.0.2.2 vm.example.internal vm vm-alias
```

```bash
$ hostname                           # ホスト名
$ hostname -s                        # ドメインを除いた短い名前
$ hostname -f                        # FQDN
$ hostname -d                        # DNS ドメイン名
$ hostname -a                        # エイリアス
$ hostname -i                        # 対応する IP アドレス
$ hostname -I                        # 割り当てられている全 IP アドレス
```

```text
vm
vm
vm.example.internal
example.internal
vm vm-alias
192.0.2.2
192.0.2.2 
```

| オプション | 表示されるもの | 覚え方 |
|:--|:--|:--|
| なし | ホスト名 | — |
| **`-f`** / `--fqdn` | **FQDN（完全修飾ドメイン名）** | **f**ully qualified |
| **`-d`** / `--domain` | **DNS ドメイン名** | **d**omain |
| **`-a`** / `--alias` | **エイリアス**（man では非推奨） | **a**lias |
| **`-i`** / `--ip-address` | **対応する IP アドレス**（man では `-I` を推奨） | **i**p |
| `-I` / `--all-ip-addresses` | **ループバックと IPv6 リンクローカルを除く**全 IP | 大文字は「（ループバック以外の）全部」 |
| `-s` / `--short` | ドメインを除いた短い名前 | **s**hort |

**`-f` `-d` `-a` `-i` はすべて `/etc/hosts` と名前解決の結果に依存します。**
`/etc/hosts` に FQDN を書いていないと、**`-d` と `-a` は何も表示されません。**

**`127.0.0.1 ホスト名` の行が別にあると、そちらが先に引かれて結果が変わります。**

```text
   [ 127.0.0.1 vm の行を残したまま FQDN 行を追記した場合 ]
     hostname -f  →  vm            （FQDN にならない）
     hostname -d  →  （空）
     hostname -i  →  127.0.0.1 192.0.2.2
```

**`-f` と `-i` も同じ影響を受けます。**
`/etc/hosts` は上から順に引かれるので、**FQDN の行を先に置く**か、
`127.0.0.1` の行からホスト名を外してください。

```text
   ✗ 「hostname -d が空だからドメインが設定されていない」
   ○ 「hostname -d が空 = /etc/hosts か DNS に FQDN が登録されていない」
```

**紛らわしいコマンドとの区別**

| コマンド | 用途 |
|:--|:--|
| **`hostname`** | **自ホストの名前まわりを表示・一時変更する** |
| `nslookup` / `dig` | **DNS へ問い合わせる**。自ホストの情報を見るものではない |
| `ifconfig` / `ip addr` | インタフェースの状態（その中に IP も含まれる） |
| `dnslookup` | **存在しないコマンド** |

### ifup と ifdown

**意味** … **設定ファイルの内容にしたがって、インタフェースを有効／無効にする**

```bash
$ sudo ifup eth0                     # 設定ファイルどおりに有効化する
$ sudo ifdown eth0                   # 無効化する
```

**`ip link set up` との違い**

| | **`ip link set eth0 up`** | **`ifup eth0`** |
|:--|:--|:--|
| **やること** | **インタフェースを上げるだけ** | **設定ファイルを読んで、IP・経路・DNS までまとめて適用** |
| 設定ファイル | 見ない | **見る**（`ifcfg-eth0` / `/etc/network/interfaces`） |
| 現在の位置づけ | **どの環境でも使える** | **NetworkManager 環境では `nmcli` に置き換わっている** |

**RHEL 8 / 9 では、`ifup` / `ifdown` は NetworkManager のラッパー**になっており、
**`nmcli connection up` / `down` を使うのが本来の形**です。

```bash
$ sudo nmcli connection up eth0      # RHEL 系ではこちらが正式
$ sudo nmcli connection down eth0    # 無効にする
```

**Debian / Ubuntu で `ifupdown` を使っている環境**では、`ifup` / `ifdown` が現役です。

---

## 参考リンク

- [man 8 ip](https://man7.org/linux/man-pages/man8/ip.8.html)
- [man 1 hostname](https://man7.org/linux/man-pages/man1/hostname.1.html)
- [man 1 hostnamectl](https://man7.org/linux/man-pages/man1/hostnamectl.1.html)
- [man 8 ifup](https://man7.org/linux/man-pages/man8/ifup.8.html)
- [RFC 1918 — Address Allocation for Private Internets](https://datatracker.ietf.org/doc/html/rfc1918)

---

[← 全体の目次にもどる](../README.md)
