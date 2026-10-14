# ネットワーク状態の確認 netstat

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / ネットワークの基礎(主題1.07) — 基本的なネットワークの問題解決 |
| **業務での使いどころ** | **「つながらない」の一次切り分け**。ポートが開いているか、接続が確立しているか、パケットが捨てられていないかを 1 コマンドで確認する |

> **このノートは「いまどうなっているか」「これまで何が起きたか」の状態と統計**を扱います。
> **相手まで届くか**は [疎通確認 pingとtraceroute](./疎通確認_pingとtraceroute.md)、
> **自分側のアドレスと経路**は [アドレスとルーティングの確認](./アドレスとルーティングの確認.md)、
> **名前が引けるか**は [名前解決の確認_digとhost](./名前解決の確認_digとhost.md) にあります。
> 通信量の推移（帯域）を見るコマンドは
> [04_プロセスとリソース管理 / リソース監視 IOとネットワーク](../04_プロセスとリソース管理/リソース監視_IOとネットワーク.md) です。

---

## 目次

- [netstat とは](#netstat-とは)
- [netstat と ss の関係](#netstat-と-ss-の関係)
- [よく使うオプション](#よく使うオプション)
- [結果画面の見方](#結果画面の見方)
  - [接続の一覧](#接続の一覧)
  - [netstat -i インタフェースの状態](#netstat--i-インタフェースの状態)
  - [netstat -s プロトコルごとの統計](#netstat--s-プロトコルごとの統計)
  - [netstat -r ルーティングテーブル](#netstat--r-ルーティングテーブル)
- [TCP の状態でよく見るもの](#tcp-の状態でよく見るもの)
- [ss との対応表](#ss-との対応表)
- [ポートを使っているプロセスを特定する](#ポートを使っているプロセスを特定する)
- [参考リンク](#参考リンク)

---

## netstat とは

**`netstat` はネットワークの状態に関する情報を表示するコマンド**です。
オプションによって、**まったく別の情報**が出てきます。

| オプション | 出てくるもの |
|:--|:--|
| （なし） | 接続の一覧 |
| **`-i`** | **インタフェースの状態**（送受信のカウンタ） |
| **`-s`** | **プロトコルごとの統計** |
| **`-r`** | **ルーティングテーブル** |

**「netstat の出力」と言われたら、まずどのオプションかを見ます。**
形がまったく違うので、見分けは難しくありません。

---

## netstat と ss の関係

`netstat` は **net-tools** という古いパッケージのコマンドです。
現在は **iproute2** の **`ss`** が後継とされ、多くのディストリビューションで
**`netstat` は標準ではインストールされていません**。

| | **`netstat`**（net-tools） | **`ss`**（iproute2） |
|:--|:--|:--|
| 位置づけ | 古くからあるコマンド | **後継。標準はこちら** |
| 速度 | 接続が多いと遅い | **速い**（カーネルから直接取る） |
| インストール | `net-tools` パッケージ | 標準で入っていることが多い |

```bash
$ sudo dnf install -y net-tools      # RHEL 系で netstat を入れる
$ sudo apt install -y net-tools      # Debian 系で netstat を入れる
```

**試験でも現場でも、両方の読み方を知っておく必要があります。**
古い手順書は `netstat`、新しい環境は `ss` で書かれていることが多いためです。

---

## よく使うオプション

| オプション | 意味 |
|:--|:--|
| **`-a`** / `--all` | **待ち受け中と接続中の両方**を表示する |
| **`-n`** / `--numeric` | **名前解決をせず、数字のまま**表示する（ホスト名・ポート名・ユーザ名） |
| **`-t`** / `--tcp` | **TCP** を対象にする |
| **`-u`** / `--udp` | **UDP** を対象にする |
| **`-l`** / `--listening` | **待ち受け中のソケットだけ**を表示する（既定では出ない） |
| **`-p`** / `--program` | **PID とプログラム名**を表示する（root 権限が要る場合がある） |
| **`-i`** / `--interfaces` | **インタフェースの一覧と送受信・エラーのカウンタ**を表示する |
| **`-s`** / `--statistics` | **プロトコルごとの統計（SNMP 統計）**を表示する |
| **`-r`** / `--route` | **カーネルのルーティングテーブル**を表示する |
| `-c` / `--continuous` | **1 秒ごとに繰り返し**表示する |
| `-e` / `--extend` | 追加情報を表示する（2 回指定すると最大限） |

```bash
$ netstat -tulnp                     # 待ち受け中のTCP/UDPポートをプロセス付きで一覧する
$ netstat -antp                      # TCPの全接続を数字表示でプロセス付きで一覧する
$ netstat -i                         # インタフェースごとの送受信カウンタを見る
$ netstat -s                         # プロトコルごとの統計を見る
$ netstat -rn                        # ルーティングテーブルを数字のまま見る
$ netstat -c -tn                     # TCP接続の一覧を1秒ごとに更新する
```

**`-tulnp` は「ティー・ユー・エル・エヌ・ピー」と 5 文字で覚える**のが定番です。
サーバ構築後の**「ちゃんと待ち受けているか」確認**は、ほぼこれ 1 つで終わります。

---

## 結果画面の見方

### 接続の一覧

```bash
$ netstat -antp                      # TCPの全接続をプロセス付きで表示する
Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address     Foreign Address    State       PID/Program name
tcp        0      0 0.0.0.0:22        0.0.0.0:*          LISTEN      912/sshd
tcp        0     64 192.168.1.10:22   192.168.1.50:53502 ESTABLISHED 3021/sshd: user
tcp6       0      0 :::80             :::*               LISTEN      1180/httpd
```

| 列 | 意味 | 見るポイント |
|:--|:--|:--|
| **`Proto`** | **プロトコル**（`tcp` / `tcp6` / `udp` / `raw`） | `tcp6` は IPv6 |
| **`Recv-Q`** | **接続中は「アプリがまだ受け取っていないバイト数」**。待ち受け中は**現在の accept キュー** | **溜まり続けるならアプリが処理できていない** |
| **`Send-Q`** | **接続中は「相手からの ACK がまだ返っていないバイト数」**。待ち受け中は**accept キューの上限（backlog）** | **溜まり続けるなら相手・経路が詰まっている** |
| **`Local Address`** | **自分側のアドレスとポート** | **`0.0.0.0` は全インタフェースで待ち受け**、`127.0.0.1` は自ホストからのみ |
| **`Foreign Address`** | **相手側のアドレスとポート** | 待ち受け中は `0.0.0.0:*` |
| **`State`** | **接続の状態** | `LISTEN` / `ESTABLISHED` など（後述） |
| **`PID/Program name`** | **プロセス ID とプログラム名** | `-p` を付けたときだけ出る |

**`Local Address` の `0.0.0.0` と `127.0.0.1` の違いは重要です**

```text
0.0.0.0:80    … すべてのインタフェースで待ち受け  → 外部から接続できる
127.0.0.1:80  … ループバックだけで待ち受け        → 自ホストからしか接続できない
```

**「サーバは起動しているのに外から繋がらない」**ときの典型的な原因がこれです。
アプリの設定（バインドアドレス）を見直します。

**補足 … `Recv-Q` / `Send-Q` は「詰まり」の指標**

どちらも通常は 0 です。**0 でない値が居座る**なら、
`Recv-Q` はアプリ側、`Send-Q` はネットワーク側か相手側が原因と当たりを付けます。

---

### netstat -i インタフェースの状態

**`-i` オプションを使用するとネットワークインタフェースの状態を表示します。**

```bash
$ netstat -i                         # インタフェースごとのカウンタを表示する
Kernel Interface table
Iface   MTU    RX-OK  RX-ERR RX-DRP RX-OVR  TX-OK  TX-ERR TX-DRP TX-OVR Flg
eth0    1500     614       0      0      0    640        0      0      0 BMRU
lo     16436   11440       0      0      0  11440        0      0      0 LRU
```

**`RX` が受信、`TX` が送信**です。

| 列 | 意味 | 見るポイント |
|:--|:--|:--|
| **`Iface`** | **インタフェース名** | `lo` はループバック |
| **`MTU`** | **一度に送れるデータの最大サイズ（バイト）** | 既定は 1500。**VPN や一部の環境では下げる必要がある** |
| **`RX-OK`** / **`TX-OK`** | **正常に受信／送信したパケット数** | **起動してからの累計** |
| **`RX-ERR`** / **`TX-ERR`** | **エラーになったパケット数** | **0 以外なら NIC・ケーブル・スイッチを疑う** |
| **`RX-DRP`** / **`TX-DRP`** | **破棄（drop）されたパケット数** | **バッファ不足**の可能性 |
| **`RX-OVR`** / **`TX-OVR`** | **オーバーラン（処理が追いつかず取りこぼした）数** | 高負荷時に増える |
| **`Flg`** | **インタフェースの状態フラグ** | `U` が無ければ**そもそも有効になっていない** |

**値は「起動してからの累計」です。** いま増えているかどうかは、
**2 回実行して差を見る**か、`sar -n EDEV` のような 1 秒あたりの値で確認します。

```bash
$ netstat -i ; sleep 5 ; netstat -i  # 5秒あけて2回取り、増分を比べる
```

**`Flg` の読み方**

`Flg` は `ip link` で表示される `<BROADCAST,MULTICAST,UP,LOWER_UP>` を
**1 文字ずつに略した表記**です。よく見るのは次の 5 つです。

| 文字 | 意味 |
|:--|:--|
| **`U`** | **UP。インタフェースが有効** |
| **`R`** | **RUNNING。リンクが上がっている** |
| `B` | BROADCAST。ブロードキャストが使える |
| `M` | マルチキャスト関連のフラグ |
| `L` | LOOPBACK。ループバックインタフェース |

**`man 8 netstat` には各文字の一覧が載っていません。**
確実に確認したいときは `ip link` の表示と突き合わせます。

```bash
$ ip link show eth0                  # フラグを省略しない形で確認する
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP ...
```

---

### netstat -s プロトコルごとの統計

**`-s` オプションを使用すると、プロトコルごとにパケットの送受信に関する情報（統計情報）を表示します。**

```bash
$ netstat -s                         # プロトコルごとの統計を表示する
Ip:
    Forwarding: 2
    58439 total packets received
    0 forwarded
    0 incoming packets discarded
    42634 incoming packets delivered
    37221 requests sent out
    51 dropped because of missing route
Icmp:
    10 ICMP messages received
... (略)
```

**`Ip:` `Icmp:` `Tcp:` `Udp:` のように、プロトコルごとの見出しで区切られます。**

**`Ip:` の主な項目**

| 項目 | 意味 |
|:--|:--|
| **`Forwarding`** | **IP フォワーディングの状態** |
| **`total packets received`** | **受信した IP パケットの総数** |
| **`forwarded`** | **転送した IP パケット数** |
| **`incoming packets discarded`** | **受信したものの破棄された IP パケット数** |
| **`incoming packets delivered`** | **上位プロトコルへ渡した IP パケット数** |
| **`requests sent out`** | **上位プロトコルから IP 層に送信を要求された IP パケット数** |
| **`dropped because of missing route`** | **送信先への経路がなく破棄された IP パケット数** |

**`Icmp:` の主な項目**

| 項目 | 意味 |
|:--|:--|
| **`ICMP messages received`** | **受信した ICMP メッセージ数** |

**`Forwarding: 2` の読み方**

この値は SNMP の MIB（RFC 1213 の `ipForwarding`）に由来し、
**`1` が「転送する」、`2` が「転送しない」**を表します。

```text
Forwarding: 1  … ルータとして動作する（IP 転送が有効）
Forwarding: 2  … 転送しない（通常のサーバ）  ← 上の例はこちら
```

```bash
$ cat /proc/sys/net/ipv4/ip_forward  # 0 = 無効 / 1 = 有効（こちらは 0/1 表記）
0
```

**数字の意味が逆になるので注意します。** `netstat -s` は `2` が無効、`/proc` は `0` が無効です。

**「渡した」と「要求された」の関係**

```text
total packets received      … NIC から IP 層が受け取った総数
      ↓
incoming packets delivered  … そのうち TCP / UDP など上位へ渡せた数
incoming packets discarded  … 受け取ったが捨てた数（不正なパケットなど）

requests sent out           … 上位から「送って」と言われた数
dropped because of missing route … 経路が無くて送れなかった数
```

**`dropped because of missing route` が増えている**なら、
**ルーティングの設定漏れ**です。`ip route` を確認します。

**値はすべて起動してからの累計です。** 差分を見るには時間をあけて 2 回実行します。

---

### netstat -r ルーティングテーブル

```bash
$ netstat -rn                        # ルーティングテーブルを数字のまま表示する
Kernel IP routing table
Destination     Gateway         Genmask         Flags   MSS Window  irtt Iface
0.0.0.0         192.168.1.1     0.0.0.0         UG        0 0          0 eth0
192.168.1.0     0.0.0.0         255.255.255.0   U         0 0          0 eth0
```

| 列 | 意味 |
|:--|:--|
| **`Destination`** | **宛先ネットワーク**。**`0.0.0.0` はデフォルトルート** |
| **`Gateway`** | **次に渡す相手**。`0.0.0.0` は「直接つながっている」 |
| `Genmask` | 宛先のサブネットマスク |
| **`Flags`** | **`U` = 有効、`G` = ゲートウェイ経由、`H` = ホスト宛** |
| `Iface` | 使用するインタフェース |

**現在は `ip route` を使うのが主流**です。

```bash
$ ip route show                      # iproute2 でのルーティングテーブル表示
default via 192.168.1.1 dev eth0
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.10
```

---

## TCP の状態でよく見るもの

`netstat` / `ss` の `State` 列に出る値のうち、実務で意味を持つものだけを挙げます。

| 状態 | 意味 | 見たときの判断 |
|:--|:--|:--|
| **`LISTEN`** | **待ち受け中** | **サービスが正しく起動している証拠** |
| **`ESTABLISHED`** | **接続が確立している** | 通信中。数が多すぎないか見る |
| `SYN_SENT` | こちらから接続を要求し、応答待ち | **返事が来ていない**。FW / SG を疑う |
| `SYN_RECV` | 相手からの接続要求を受け、応答待ち | 大量にあるなら SYN Flood の疑い |
| **`TIME_WAIT`** | **こちらから閉じたあとの待機** | **大量でも正常なことが多い**（後述） |
| `CLOSE_WAIT` | **相手が閉じたのに、こちらが閉じていない** | **アプリのバグ**を疑う。増え続けるなら要調査 |
| `FIN_WAIT1` / `FIN_WAIT2` | 切断処理の途中 | 滞留するなら相手が応答していない |

**`TIME_WAIT` が多いのは異常ではありません**

先に接続を閉じた側が、**遅れて届くパケットを処理するために一定時間待つ**仕組みです。
短時間に多数の接続を作って閉じるサーバでは、**数千あっても正常**です。

**`CLOSE_WAIT` が多いのは異常です**

相手は閉じているのに、**アプリがソケットを close していない**状態です。
再起動でいったん消えますが、**アプリ側の修正が本質的な対処**になります。

---

> **`ss` の詳しい使い方**は [ソケットの確認_ss](./ソケットの確認_ss.md) にあります。

## ss との対応表

| やりたいこと | **netstat** | **ss** |
|:--|:--|:--|
| 待ち受けポートの一覧 | **`netstat -tulnp`** | **`ss -tulnp`** |
| TCP の全接続 | `netstat -antp` | `ss -antp` |
| 統計 | `netstat -s` | `ss -s`（**内容は簡易的**） |
| インタフェース | `netstat -i` | **`ip -s link`** |
| ルーティング | `netstat -r` | **`ip route`** |
| 状態で絞る | `netstat -ant \| grep TIME_WAIT` | **`ss -ant state time-wait`** |

**オプション文字は `netstat` とほぼ同じ**なので、置き換えはすぐに慣れます。

```bash
$ ss -tulnp                          # 待ち受けポートをプロセス付きで一覧する
$ ss -s                              # ソケットのサマリを表示する
$ ss -ant state established          # 確立済みのTCP接続だけを表示する
```

---


## ポートを使っているプロセスを特定する

**`-p` を付けても出ないとき**は、権限が足りていない可能性があります。

```bash
$ sudo netstat -tulnp                # root 権限で実行するとプロセス名まで出る
$ sudo ss -tulnp                      # ss でも同じ
```

**別の手段として `lsof` があります。**
**`lsof` はファイルを開いているプロセスを表示するコマンド**で、
Linux では**ソケットもファイルとして扱われる**ため、ポートの持ち主も調べられます。

```bash
$ sudo lsof -i :80                   # 80番ポートを使っているプロセスを表示する
$ sudo lsof -i -P -n                 # 全ネットワーク接続を数字表示で一覧する
$ sudo fuser 80/tcp                  # 80番ポートを使っているPIDだけを表示する
```

| コマンド | 向いている場面 |
|:--|:--|
| **`ss -tulnp` / `netstat -tulnp`** | **一覧をざっと見る** |
| **`lsof -i :ポート`** | **特定のポートの持ち主を確実に突き止める** |
| `fuser ポート/tcp` | PID だけ欲しい（スクリプト向き） |

**「アドレスは既に使用中です（Address already in use）」**でサービスが起動しないときは、
この 3 つのどれかで**先に掴んでいるプロセス**を特定します。

---

## 参考リンク

- [man 8 netstat](https://man7.org/linux/man-pages/man8/netstat.8.html)
- [man 8 ss](https://man7.org/linux/man-pages/man8/ss.8.html)
- [man 8 ip](https://man7.org/linux/man-pages/man8/ip.8.html)
- [man 8 ip-route](https://man7.org/linux/man-pages/man8/ip-route.8.html)
- [man 8 lsof](https://man7.org/linux/man-pages/man8/lsof.8.html)
- [RFC 1213 — MIB-II（ipForwarding の定義）](https://datatracker.ietf.org/doc/html/rfc1213)
- [AWS — VPC フローログ](https://docs.aws.amazon.com/ja_jp/vpc/latest/userguide/flow-logs.html)

---

[← 全体の目次にもどる](../README.md)
