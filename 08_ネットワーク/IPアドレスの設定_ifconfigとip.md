# IPアドレスの設定 ifconfigとip

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / ネットワークの基礎(主題1.07) — 基本的なネットワーク構成 |
| **業務での使いどころ** | **アドレスを「その場で」付け替える。**検証機に一時的なアドレスを足す、疎通試験のためにセカンダリを付ける、インタフェースを落として切り分ける。恒久設定は設定ファイル側の仕事 |

> **このノートはアドレスを設定するコマンド**です。
> **見る側（`ip a` / `ip r` / `ip neigh` の読み方）**は
> [アドレスとルーティングの確認](./アドレスとルーティングの確認.md)、
> **恒久化する設定ファイル**は [ネットワーク設定ファイル](./ネットワーク設定ファイル.md)、
> **ARP キャッシュの操作**は [ARPキャッシュの操作 arp](./ARPキャッシュの操作_arp.md)、
> **無線 LAN の設定**は [無線LANの設定 iwconfigとiw](./無線LANの設定_iwconfigとiw.md) にあります。

---

## 目次

- [ifconfig の書式](#ifconfig-の書式)
- [ip の書式](#ip-の書式)
- [状態を一覧で見る](#状態を一覧で見る)
- [IPv4 アドレスを設定する](#ipv4-アドレスを設定する)
- [IPv6 アドレスを設定する](#ipv6-アドレスを設定する)
- [有効化と無効化](#有効化と無効化)
- [MACアドレスを調べる](#macアドレスを調べる)
- [セカンダリアドレス](#セカンダリアドレス)
- [まぎらわしいコマンドと書式の誤り](#まぎらわしいコマンドと書式の誤り)
- [参考リンク](#参考リンク)

---

## ifconfig の書式

```text
ifconfig インタフェース名 操作内容
```

**「操作内容」に指定できるもの**

| 指定 | 意味 |
|:--|:--|
| **（指定なし）** | **現在の状態を表示する** |
| **`up`** | **有効化する** |
| **`down`** | **無効化する** |
| **IPv4 アドレス** | **IPv4 アドレスを割り当てる** |
| **`netmask`** | **続けてネットマスクを指定する** |
| **`inet6 add` IPv6アドレス[/プレフィックス長]** | **IPv6 アドレスを追加する** |
| **`inet6 del` IPv6アドレス[/プレフィックス長]** | **IPv6 アドレスを削除する** |

**`up` 以外は通らない**

「無効化されているインタフェースを有効にする指定は」という設問では、
**`start` / `on` / `active` はすべて誤り**です。**正しいのは `up` だけ**。

```text
  up      有効化する     ← これだけ
  start   × 通らない
  on      × 通らない
  active  × 通らない
```

**操作内容は続けて書ける**

```bash
$ sudo ifconfig eth0 192.168.2.10 netmask 255.255.255.0 up   # 割当・マスク・有効化を一度に
```

**`ifconfig` は表示もできる**

**「設定するコマンド」という印象が強い**ですが、
**操作内容を省略すれば表示コマンドとして使えます。**
この性質は「一覧表示できるコマンドはどれか」という設問でそのまま問われます。

---

## ip の書式

```text
ip [オプション] オブジェクト コマンド
```

**`ip` は `ifconfig` だけでなく `route` と `arp` の守備範囲もまとめて置き換えます。**

**主なオプション**

| オプション | 意味 |
|:--|:--|
| **`-4`** | **IPv4 を指定する** |
| **`-6`** | **IPv6 を指定する** |

> **アドレスを見れば IPv4 か IPv6 かは分かる**ので、
> **`-4` / `-6` は省略できます。**
> `ip addr add 2001:db8::1/64 dev eth0` は `-6` を付けなくても通ります。

**主なオブジェクトとコマンド**

| オブジェクト | 何を扱うか | 主要なコマンド |
|:--|:--|:--|
| **`link`** | **ネットワークデバイス関連** | **`up`** / **`down`** / **`set`** / **`show`** |
| **`addr`（`address`）** | **ネットワークプロトコル（アドレス）** | **`add`** / **`delete`** / **`show`** |
| **`route`** | **ルーティング関連** | `add` / `delete` / `show` |
| **`neigh`（`neighbour`）** | **ARP など** | `add` / `delete` / `show` |

> **デバイスを指定せずコマンドも省くと、`show` と同じ結果**になります。
> **`ip addr` は `ip addr show` と同じ**です。

**オブジェクト名は省略できる、コマンド名は省略できない**

```text
  ip address add …   ○  正式
  ip addr add …      ○  よく使う省略形
  ip a add …         ○  さらに短くしても通る
  ip add addr …      ×  add と addr が入れ替わっている
```

**`address` は `add` まで縮められます**が、
**そのあとのコマンドを `addr` と書くことはできません。**
`ip add addr 〜` は「オブジェクトが `add`、コマンドが `addr`」と読まれて成立しません。

---

## 状態を一覧で見る

| コマンド | 出るもの |
|:--|:--|
| **`ifconfig`** | **現在有効になっているインタフェースだけ** |
| **`ifconfig -a`** | **無効になっているものも含めて全部** |
| **`ip addr`** | **ダウンしているものも含めて全部**（`ip addr show` と同じ） |

**実機での差**（サンドボックスで確認）

```bash
$ ifconfig | grep -E "^[a-z]"     # 有効なものだけ出る
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1400
lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
$ ifconfig -a | grep -E "^[a-z]"  # ダウンしている ifb0 / ifb1 も出る
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1400
ifb0: flags=130<BROADCAST,NOARP>  mtu 1500
ifb1: flags=130<BROADCAST,NOARP>  mtu 1500
lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
```

**`ip addr` の出力**（同じ環境）

```bash
$ ip addr                              # オプションもコマンドも省ける
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    inet 127.0.0.1/8 scope host lo
2: ifb0: <BROADCAST,NOARP> mtu 1500 qdisc noop state DOWN
3: ifb1: <BROADCAST,NOARP> mtu 1500 qdisc noop state DOWN
4: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1400 qdisc pfifo_fast state UP
    link/ether 02:fc:00:00:00:01 brd ff:ff:ff:ff:ff:ff
    inet 192.0.2.2/24 brd 192.0.2.255 scope global eth0
```

**「一覧表示できるコマンドを 3 つ」への答え**

| 選択肢 | 正誤 | 理由 |
|:--|:-:|:--|
| **`ifconfig`** | **○** | **有効なインタフェースを一覧表示する** |
| **`ifconfig -a`** | **○** | **無効なものも含めて一覧表示する** |
| **`ip addr`** | **○** | **`ip addr show` と同じ。全部出る** |
| `ip addr -a` | ✕ | **`ip` のオプションはオブジェクトの前**。`-a` というオプションもコマンドも無い |
| `arp -a` | ✕ | **ARP キャッシュを表示するコマンド**。インタフェースの状態は出ない |
| `arp -v` | ✕ | 同上（`-v` は詳細表示） |

---

## IPv4 アドレスを設定する

**`ifconfig` はインタフェース名に続けてアドレスを書く**だけです。

```bash
$ sudo ifconfig eth0 192.168.11.9      # IPv4 アドレスを割り当てる
```

**`ip` は `addr` オブジェクトに `add` コマンド**を使います。

```bash
$ sudo ip addr add 192.168.11.9/24 dev eth0   # プレフィックス長と dev が要る
```

| 書き方 | 正誤 | 理由 |
|:--|:-:|:--|
| **`ifconfig eth0 192.168.11.9`** | **○** | **インタフェース名 → アドレスの順** |
| **`ip addr add 192.168.11.9/24 dev eth0`** | **○** | **`dev` でインタフェースを指定する** |
| `ipconfig eth0 192.168.11.9` | ✕ | **`ipconfig` は Windows のコマンド**。Linux には無い |
| `iwconfig 192.168.11.9 eth0` | ✕ | **`iwconfig` は無線 LAN 専用**。IP アドレスは扱えない |
| `route 192.168.11.9 eth0` | ✕ | **`route` はルーティングテーブルの操作**。インタフェースは扱えない |

> **`ifconfig` と `iwconfig` は名前も書式も似ています。**
> **`iwconfig` の `w` は Wireless の `w`** と覚えると取り違えません。

---

## IPv6 アドレスを設定する

**IPv6 はシステムが対応していれば自動で設定されます**が、
手で設定するときは次のようにします。

**追加する**

```bash
$ sudo ifconfig eth0 inet6 add 1234:5678::1234:0:0:9ABC        # inet6 add に続けて書く
$ sudo ip addr add 1234:5678::1234:0:0:9ABC/64 dev eth0        # ip なら add + dev
```

**削除する**

```bash
$ sudo ifconfig eth0 inet6 del 1234:5678::1234:0:0:9ABC        # inet6 del に続けて書く
$ sudo ip addr del 1234:5678::1234:0:0:9ABC/64 dev eth0        # ip なら del + dev
```

**語順を入れ替えた誤答**

| 書き方 | 正誤 | 理由 |
|:--|:-:|:--|
| **`ifconfig eth0 inet6 add アドレス`** | **○** | **`inet6 add` → アドレス** |
| `ifconfig eth0 inet6 アドレス` | ✕ | **`add` が無い**。書式として成立しない |
| `ifconfig eth0 inet6 アドレス del` | ✕ | **`del` は `inet6` の直後**に置く |
| `iwconfig アドレス eth0 del` | ✕ | **無線専用のコマンド** |
| `ipconfig eth0 inet6 del アドレス` | ✕ | **Linux に `ipconfig` は無い** |

**`ip` 側で落とされる書き方**

| 書き方 | 正誤 | 理由 |
|:--|:-:|:--|
| **`ip addr add 2345:6789::abcd/24 dev eth0`** | **○** | 正しい書式 |
| **`ip -6 addr add 2345:6789::abcd/24 dev eth0`** | **○** | **`-6` は省略可能なので付けても通る** |
| **`ip -6 addr add 2345:6789::abcd dev eth0`** | **○** | **プレフィックス長を省くと `/128` 扱い**。設定自体はできる |
| `ip add addr 2345:6789::abcd/24 dev eth0` | ✕ | **`add` と `addr` が逆**。`address` を `add` と略せても、コマンド側は `addr` にできない |
| `ip addr add 2345:6789::abcd/24 eth0` | ✕ | **`dev` が抜けている** |

> **「入力できないものを選べ」という設問**では、
> **`/128` になるだけで実行はできる**選択肢を誤答に数えないよう注意します。
> **書式として通らないのは `dev` 抜きと `add addr` の 2 つ**です。

---

## 有効化と無効化

```bash
$ sudo ifconfig eth0 down              # 無効化する
$ sudo ifconfig eth0 up                # 有効化する
$ sudo ip link set eth0 down           # ip なら link オブジェクト + set
$ sudo ip link set eth0 up             # 同上
```

| 書き方 | 正誤 | 理由 |
|:--|:-:|:--|
| **`ifconfig eth0 down`** | **○** | **操作内容に `down`** |
| **`ip link set eth0 down`** | **○** | **`link` では `set デバイス名` でデバイスを指定してから `down` / `up`** |
| `ip link eth0 down` | ✕ | **`set` が抜けている** |
| `ipconfig eth0 down` | ✕ | **Linux に `ipconfig` は無い** |
| `iwconfig eth0 stop` | ✕ | **無線専用**。しかも `stop` という指定は `ifconfig` にも無い |

> **「一時的に無効化したい」という問題文の「一時的に」**は、
> **`ifconfig` / `ip` での変更が再起動で消える**ことを指しています。
> 恒久的に落としたいなら設定ファイル側（`ONBOOT=no` など）を触ります。

---

## MACアドレスを調べる

**MAC アドレスは NIC に一意に割り当てられた物理アドレス**です。
被らないように割り当てられているので、**機器のネットワークデバイスを識別**できます。

```bash
$ ifconfig eth0                        # ether の行が MAC アドレス
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1400
        inet 192.0.2.2  netmask 255.255.255.0  broadcast 192.0.2.255
        ether 02:fc:00:00:00:01  txqueuelen 1000  (Ethernet)
$ ip addr                              # link/ether の行が MAC アドレス
4: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1400
    link/ether 02:fc:00:00:00:01 brd ff:ff:ff:ff:ff:ff
```

| 表示 | どこに出るか |
|:--|:--|
| **`ifconfig`** | **`ether`**（古い net-tools では **`HWaddr`**） |
| **`ip addr`** | **`link/ether`** |

**誤答として並ぶもの**

| 選択肢 | 理由 |
|:--|:--|
| `ifconfig -m eth0` / `iwconfig -m eth0` | **`-m` というオプションは無い** |
| `iwconfig eth0` | **無線インタフェースの情報**。有線の MAC は出ない |
| `arp eth0` | **ARP キャッシュのコマンド**。自分の MAC ではなく**相手の MAC** を扱う |

> **自分の MAC は `ifconfig` / `ip addr`、相手の MAC は `arp`** ——
> この使い分けが問われます。詳しくは
> [ARPキャッシュの操作 arp](./ARPキャッシュの操作_arp.md)。

---

## セカンダリアドレス

**1 つのインタフェースには複数のアドレスを割り当てられます。**
**最初に割り当てたものがプライマリ、追加したものがセカンダリ**です。

> **3 つ目・4 つ目もすべてセカンダリ**と呼びます。
> **順位があるわけではなく、「プライマリ以外」という意味**です。

**設定のしかたはコマンドによって違います。**

**`ifconfig` はエイリアスを使う**

**`ifconfig` では直接セカンダリアドレスを設定できません。**
**インタフェースに別名（エイリアス）を付け、そちらにアドレスを割り当てます。**

```bash
$ sudo ifconfig eth0:0 198.51.100.5/24   # eth0 のエイリアス eth0:0 を作って割り当てる
$ ifconfig eth0:0                        # エイリアス側に付いているのが分かる
eth0:0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1400
        inet 198.51.100.5  netmask 255.255.255.0  broadcast 198.51.100.255
        ether 02:fc:00:00:00:01  txqueuelen 1000  (Ethernet)
```

**プライマリはそのまま残ります。**

```bash
$ ip addr show eth0 | grep inet          # ip から見ると scope の後ろに eth0:0 と出る
    inet 192.0.2.2/24 brd 192.0.2.255 scope global eth0
    inet 198.51.100.5/24 brd 198.51.100.255 scope global eth0:0
```

**`ip` はプライマリと同じコマンド**

```bash
$ sudo ip addr add 198.51.100.1/24 dev eth0   # 追加すればそれがセカンダリになる
```

**`ip` で付けたものは `ifconfig` から見えない**

```bash
$ sudo ip addr add 198.51.100.1/24 dev eth0   # ラベル無しで追加する
$ ip addr show eth0 | grep inet               # ip では見える
    inet 192.0.2.2/24 brd 192.0.2.255 scope global eth0
    inet 198.51.100.1/24 scope global eth0
$ ifconfig | grep inet                        # ifconfig には出てこない
        inet 192.0.2.2  netmask 255.255.255.0  broadcast 192.0.2.255
        inet 127.0.0.1  netmask 255.0.0.0
```

**`ifconfig` から見えるようにするには `label` を付ける**

```bash
$ sudo ip addr add 203.0.113.1/24 dev eth0 label eth0:1   # エイリアス名を明示する
$ ifconfig eth0:1                                         # 今度は ifconfig でも見える
eth0:1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1400
        inet 203.0.113.1  netmask 255.255.255.0  broadcast 0.0.0.0
```

**上の 3 つの出力はサンドボックスの実測値**です。

**セカンダリ設定の正誤表**

| 書き方 | 正誤 | 理由 |
|:--|:-:|:--|
| **`ifconfig eth0:0 192.168.200.1/24`** | **○** | **エイリアスに割り当てる** |
| **`ip addr add 192.168.200.1/24 dev eth0`** | **○** | **プライマリと同じコマンドで足す** |
| `ifconfig eth0 192.168.200.1 netmask 255.255.255.0` | ✕ | **エイリアスを指定していないのでプライマリが書き換わる** |
| `ifconfig eth0 192.168.200.1 netmask 255.255.255.0 secondary` | ✕ | **`ifconfig` に `secondary` は無い**。しかもエイリアス指定が無い |
| `ip addr add secondary 192.168.200.1/24 dev eth0` | ✕ | **`ip` にも `secondary` は無い** |

> **`ifconfig` のエイリアス方式は現在では非推奨**です。
> **`ip` によるアドレス設定が推奨**されています。

---

## まぎらわしいコマンドと書式の誤り

| 名前 | 実際は |
|:--|:--|
| **`ipconfig`** | **Windows のコマンド**。Linux には存在しない |
| **`iwconfig`** | **無線 LAN 専用**。IP アドレスやインタフェースの有効・無効は扱えない |
| **`route`** | **ルーティングテーブルの操作**。インタフェースの設定はできない |
| **`arp`** | **ARP キャッシュの操作**。インタフェースの状態表示はできない |
| `ifconfig eth0 stop` | **`stop` という操作内容は無い**（正しくは `down`） |
| `ip link eth0 down` | **`set` が抜けている** |
| `ip addr -a` | **`ip` のオプションはオブジェクトの前**。`-a` は無い |
| `ip add addr 〜` | **`add` と `addr` が逆** |
| `ip addr add 〜 eth0` | **`dev` が抜けている** |

**覚え方**

```text
  ifconfig  インタフェース名  操作内容        … 名前が先、やることが後
  ip  [オプション]  オブジェクト  コマンド     … 何を、どうする
       ▲ -4 / -6   ▲ link/addr   ▲ up,down,set,add,del,show
```

---

## 参考リンク

- [man 8 ifconfig](https://man7.org/linux/man-pages/man8/ifconfig.8.html)
- [man 8 ip](https://man7.org/linux/man-pages/man8/ip.8.html)
- [man 8 ip-address](https://man7.org/linux/man-pages/man8/ip-address.8.html)
- [man 8 ip-link](https://man7.org/linux/man-pages/man8/ip-link.8.html)
