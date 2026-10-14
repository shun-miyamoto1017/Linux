# ソケットの確認_ss

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / ネットワークの基礎(主題109) — ネットワークの設定とトラブルシューティング |
| **業務での使いどころ** | **「ポートが開いていない」と言われたときに、最初に打つコマンド。**待ち受けているのか、繋がっているのか、どのプロセスが握っているのかを 1 コマンドで確定させる。`netstat` より速く、状態での絞り込みができる |

> **`netstat` との対応と、`netstat` 自体の使い方**は
> [ネットワーク状態の確認_netstat](./ネットワーク状態の確認_netstat.md)、
> **外から見てポートが開いているか**は
> [ポートスキャンと疎通_nmapとnc](../10_セキュリティ/ポートスキャンと疎通_nmapとnc.md)、
> **実際に流れているパケット**は
> [パケットキャプチャ_tcpdump](./パケットキャプチャ_tcpdump.md) にあります。

> **このノートの検証状況**
> **10.10.0.x が出てくる出力例は iproute2-6.1.0 の `ss` で実測**したものです
> （ネットワーク名前空間で 10.10.0.1 ↔ 10.10.0.2 をつなぎ、実際に接続を張って取得）。
> **`ss -h` のフィルタ定義も実測**です。
> **それ以外のアドレス（192.168.x.x など）が出てくる出力は、説明のための例**です。

---

## 目次

- [まず覚える3つの形](#まず覚える3つの形)
- [列の読み方](#列の読み方)
  - [Recv-Q と Send-Q は行によって意味が違う](#recv-q-と-send-q-は行によって意味が違う)
  - [0.0.0.0 と 127.0.0.1 の違い](#0000-と-127001-の違い)
- [ss の基本](#ss-の基本)
  - [ss のよく使うオプション](#ss-のよく使うオプション)
  - [ss の結果画面の見方](#ss-の結果画面の見方)
- [状態で絞り込む](#状態で絞り込む)
- [アドレスとポートで絞り込む](#アドレスとポートで絞り込む)
- [サマリと内部情報](#サマリと内部情報)
  - [-s 全体のサマリ](#-s-全体のサマリ)
  - [-i TCP の内部情報](#-i-tcp-の内部情報)
  - [-o タイマーを見る](#-o-タイマーを見る)
- [どのプロセスがポートを握っているか](#どのプロセスがポートを握っているか)
- [参考リンク](#参考リンク)

---

## まず覚える3つの形

**`ss` は組み合わせが多く見えますが、実務で打つのはほぼこの3つ**です。

```bash
$ sudo ss -tulnp                       # ① 何が待ち受けているか（いちばん使う）
$ sudo ss -tunap                       # ② 待ち受けも接続中も全部
$ ss -tn state established             # ③ いま繋がっているものだけ
```

**① の `-tulnp` を分解するとこうなります。**

```text
  ss -t u l n p
      │ │ │ │ └ process   どのプロセスが使っているか     （root 権限が要る）
      │ │ │ └── numeric   名前に変換せず数字のまま出す
      │ │ └──── listening 待ち受けているものだけ
      │ └────── udp       UDP も対象にする
      └──────── tcp       TCP を対象にする
```

**実測**（ns2 で 8080 番を待ち受け、ns1 から接続した状態）

```bash
$ sudo ss -tunap                       # TCP/UDP を数字表示・全状態・プロセス付きで
```

```text
Netid State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process                     
tcp   LISTEN 0      1            0.0.0.0:8080      0.0.0.0:*     users:(("nc",pid=499,fd=3))
tcp   ESTAB  0      0          10.10.0.2:8080    10.10.0.1:49662 users:(("nc",pid=499,fd=4))
```

**この 2 行で状況が確定します。**

```text
  1行目  LISTEN  0.0.0.0:8080        → 8080 番で待ち受けている。全インタフェースで受ける
  2行目  ESTAB   10.10.0.2:8080      → 10.10.0.1 から実際に繋がっている
         users:(("nc",pid=499))      → nc というプロセス（PID 499）が握っている
```

---

## 列の読み方

| 列 | 意味 |
|:--|:--|
| **`Netid`** | **ソケットの種類**（`tcp` / `udp` / `u_str`＝UNIXドメイン など） |
| **`State`** | **TCP の状態**（`LISTEN` / `ESTAB` / `TIME-WAIT` など）。**UDP は `bind` だけなら `UNCONN`、`connect()` 済みなら `ESTAB`**（実測） |
| **`Recv-Q`** | **受信キューに溜まっている量**。**`LISTEN` 行では意味が変わる**（下記） |
| **`Send-Q`** | **送信キューに溜まっている量**。**`LISTEN` 行では意味が変わる**（下記） |
| **`Local Address:Port`** | **自分側**のアドレスとポート |
| **`Peer Address:Port`** | **相手側**のアドレスとポート。`LISTEN` では `0.0.0.0:*` |
| **`Process`** | **使っているプロセス**（`-p` を付けたときだけ） |

### Recv-Q と Send-Q は行によって意味が違う

**ここが `ss` の最大の落とし穴**です。

| 行の種類 | `Recv-Q` | `Send-Q` |
|:--|:--|:--|
| **`LISTEN`** | **接続待ちのキューに溜まっている数** | **そのキューの上限（backlog）** |
| **`ESTAB` など** | **アプリがまだ読んでいないバイト数** | **相手がまだ ACK していないバイト数** |

```text
  LISTEN 0      1      0.0.0.0:8080
         │      └ backlog は 1（これ以上同時に来ると溢れる）
         └─ いま待たされている接続は 0 件（正常）

  LISTEN 128    128    0.0.0.0:443
         │      └ backlog 128
         └─ 128 件が詰まっている ＝ アプリが accept できていない   ★異常
```

> **`LISTEN` 行の `Recv-Q` が常に 0 でないなら、アプリが接続を受け切れていません。**
> **アプリのワーカー数やスレッド数を疑うところ**です。
>
> **`ESTAB` 行の `Send-Q` が減らないなら、相手に届いていない**か、
> **相手が受信を止めている**（受信ウィンドウが 0）ことを疑います。

### 0.0.0.0 と 127.0.0.1 の違い

**「待ち受けているのに外から繋がらない」の原因はほぼこれ**です。

| `Local Address` | 意味 | 外から繋がるか |
|:--|:--|:--|
| **`0.0.0.0:8080`** | **全ての IPv4 インタフェースで待ち受け** | **繋がる** |
| **`[::]:8080`** | **全ての IPv6 インタフェースで待ち受け** | **繋がる**（多くの環境では IPv4 も受ける） |
| **`127.0.0.1:8080`** | **ループバックだけ** | **繋がらない**。同じサーバの中からだけ |
| **`10.0.1.5:8080`** | **そのアドレスだけ** | **そのアドレス宛てなら繋がる** |

```text
  ss -tlnp して 127.0.0.1:3306 と出た
      → MySQL はローカル専用で待ち受けている
      → ファイアウォールを開けても外からは繋がらない
      → 直すのはアプリの設定（bind-address）であって、ファイアウォールではない
```

---

## ss の基本

**`ss` は `netstat` を代替するコマンドとして、ネットワークの状態に関する情報を表示します。**
**iproute2 パッケージに含まれ、多くのディストリビューションで標準的に使えます。**

```text
ss [オプション] [フィルタ]
```

### ss のよく使うオプション

| オプション | 意味 |
|:--|:--|
| **`-a`** / `--all` | **待ち受け中と接続中の両方**を表示する（既定では待ち受けが省かれる） |
| **`-n`** / `--numeric` | **サービス名を解決せず、数字のまま**表示する |
| **`-t`** / `--tcp` | **TCP のソケット**を表示する |
| **`-u`** / `--udp` | **UDP のソケット**を表示する |
| **`-l`** / `--listening` | **待ち受け中のソケットだけ**を表示する |
| **`-p`** / `--processes` | **ソケットを使っているプロセス**を表示する（root 権限が要る） |
| **`-s`** / `--summary` | **サマリの統計**を表示する |
| `-x` / `--unix` | UNIX ドメインソケットを表示する |
| `-4` / `-6` | IPv4 のみ / IPv6 のみに絞る |
| **`-r`** / `--resolve` | 数字のアドレスやポートを名前に解決する |
| `-m` / `--memory` | ソケットが使っているメモリを表示する |
| `-i` / `--info` | TCP の内部情報（RTT、輻輳ウィンドウなど）を表示する |
| `-o` / `--options` | タイマー情報を表示する |
| `-e` / `--extended` | 詳細なソケット情報を表示する |
| `-H` / `--no-header` | 見出し行を出さない |

```bash
$ ss -nt                             # TCP接続をアドレス・ポートを数字で表示する
$ ss -tulnp                          # 待ち受け中のTCP/UDPをプロセス付きで一覧する
$ ss -s                              # ソケットのサマリ統計を表示する
$ ss -ntp                            # TCP接続をプロセス付きで表示する（sudo 推奨）
$ ss -x                              # UNIXドメインソケットを表示する
```

**オプション文字は `netstat` とほぼ同じ**なので、`netstat -tulnp` → `ss -tulnp` と置き換えられます。

**`-n` を付ける理由**

**名前解決を待たなくなるので表示が速くなります。** 接続数が多い本番サーバでは体感差が大きく出ます。

### ss の結果画面の見方

```bash
$ ss -nt                             # TCP接続を数字表示で一覧する
State   Recv-Q  Send-Q  Local Address:Port   Peer Address:Port  Process
ESTAB   0       64      192.168.66.91:22     192.168.66.1:53502
ESTAB   0       0       192.168.66.91:22     192.168.66.1:54267
ESTAB   0       0       127.0.0.1:49796      127.0.0.1:5910
```

| 列 | 意味 | 見るポイント |
|:--|:--|:--|
| **`State`** | **接続の状態** | **`ESTAB` は確立済み**、`LISTEN` は待ち受け中 |
| **`Recv-Q`** | **アプリがまだ受け取っていないバイト数** | **溜まり続けるならアプリが処理できていない** |
| **`Send-Q`** | **相手からの ACK がまだ返っていないバイト数** | **溜まり続けるなら相手・経路が詰まっている** |
| **`Local Address:Port`** | **自分側のアドレスとポート** | `0.0.0.0` は全インタフェースで待ち受け |
| **`Peer Address:Port`** | **相手側のアドレスとポート** | `netstat` の `Foreign Address` に相当 |
| **`Process`** | **ソケットを使っているプロセス** | **`-p` を付けたときだけ**中身が出る |

**`netstat` との表示の違い**

| | **`netstat -antp`** | **`ss -ntp`** |
|:--|:--|:--|
| 相手側の列名 | **`Foreign Address`** | **`Peer Address:Port`** |
| プロトコル列 | **`Proto`（`tcp` / `tcp6`）がある** | **無い**（`-t` などで指定するため） |
| 状態の表記 | **`ESTABLISHED`** | **`ESTAB`**（短縮形） |
| 表示の速さ | 接続が多いと遅い | **速い** |

**`ESTABLISHED` と `ESTAB` は同じ状態**です。表記が違うだけなので、
**`grep ESTABLISHED` を `ss` に流用すると何も引っかかりません**。

```bash
$ ss -nt | grep ESTAB                # ss では ESTAB で絞る
$ netstat -ant | grep ESTABLISHED    # netstat では ESTABLISHED で絞る
```

**`ss -s` のサマリ**

```bash
$ ss -s                              # ソケットの種類ごとの数をまとめて表示する
Total: 231
TCP:   12 (estab 5, closed 3, orphaned 0, timewait 3)

Transport Total     IP        IPv6
RAW       1         0         1
UDP       6         4         2
TCP       9         7         2
```

**接続数の全体像を 1 画面で把握できます。**
**`timewait` が極端に多いとき**は、短時間に大量の接続を作って閉じている状態です。

## 状態で絞り込む

**`ss` が `netstat` より優れている点がこれ**です。
**`grep` を挟まずに、TCP の状態で直接絞れます。**

```bash
$ ss -tn state established             # 確立済みだけ
$ ss -tn state time-wait               # TIME-WAIT だけ
$ ss -tn state syn-sent                # SYN を送って応答待ちのもの
$ ss -tln state listening              # 待ち受けだけ（-l と同じ）
```

**実測**

```bash
$ ss -tn state established             # 確立済みの接続だけを出す
```

```text
Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
0      0          10.10.0.1:49662    10.10.0.2:8080       
```

**まとめて指定できる便利な名前**

| 指定 | 含まれるもの |
|:--|:--|
| **`state connected`** | **`LISTEN` と `CLOSED` 以外すべて**（繋がっている or 後始末中） |
| **`state synchronized`** | **`syn-sent` 以外すべて**（`SYN-RECV` は**含まれる**） |
| `state bucket` | `TIME-WAIT` と `SYN-RECV` |
| `state big` | `bucket` 以外（`LISTEN` と `CLOSED` を含む） |

**定義は `ss -h` で確認できます。**（実測）

```text
    connected := {established|syn-sent|syn-recv|fin-wait-{1,2}|time-wait|close-wait|last-ack|closing}
 synchronized := {established|syn-recv|fin-wait-{1,2}|time-wait|close-wait|last-ack|closing}
       bucket := {syn-recv|time-wait}
          big := {established|syn-sent|fin-wait-{1,2}|closed|close-wait|last-ack|listening|closing}
```

```bash
$ ss -tn state connected               # 繋がっているものと後始末中のものを全部
```

```text
State     Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
ESTAB     0      0          10.10.0.1:44834    10.10.0.2:8080       
ESTAB     0      0          10.10.0.1:49662    10.10.0.2:8080       
TIME-WAIT 0      0          10.10.0.1:60094    10.10.0.2:8080       
```

> **`TIME-WAIT` が大量にあっても、それ自体は異常ではありません。**
> **接続を閉じた側に 60 秒ほど残る、正常な状態**です。
> **数万件まで増えてポートが枯渇する場合だけ**対処を考えます。

---

## アドレスとポートで絞り込む

**`ss` にはフィルタ構文があります。**`grep` より正確です。

```bash
$ ss -tn 'dport = :8080'               # 宛先ポートが 8080 のもの
$ ss -tn 'sport = :22'                 # 送信元ポートが 22 のもの
$ ss -tn 'dst 10.10.0.2'               # 宛先アドレスが 10.10.0.2
$ ss -tn 'src 10.10.0.1'               # 送信元アドレスが 10.10.0.1
$ ss -tn 'dst 10.10.0.0/24'            # 宛先がこのネットワーク
$ ss -tn 'dport > :1024'               # 宛先ポートが 1024 より大きい
```

**実測**

```bash
$ ss -tn 'dport = :8080'               # 8080番へ繋ぎに行っている接続を探す
```

```text
State Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
ESTAB 0      0          10.10.0.1:44834    10.10.0.2:8080       
ESTAB 0      0          10.10.0.1:49662    10.10.0.2:8080       
```

**組み合わせ**

```bash
$ ss -tn 'dst 10.10.0.2 and dport = :8080'      # 相手とポートの両方で絞る
$ ss -tn 'dport = :80 or dport = :443'          # どちらかに一致
$ ss -tnp state established 'dport = :5432'     # DB へ繋いでいるプロセスを特定する
```

> **フィルタはシングルクォートで囲んでください。**
>
> **ポート番号の前のコロンは、付けなくても動きます。**（実測）
> `dport = :8080` / `dport = 8080` / `dport 8080` はいずれも同じ結果でした。
> **コロン付きが man の書き方**（`アドレス:ポート` のアドレスを省略した形）なので、
> **手順書にはコロン付きで書く**のを勧めます。

---

## サマリと内部情報

### -s 全体のサマリ

```bash
$ ss -s                                # ソケット数の集計を見る
```

```text
Total: 3
TCP:   28 (estab 1, closed 26, orphaned 0, timewait 0)

Transport Total     IP        IPv6
RAW	  0         0         0        
UDP	  0         0         0        
TCP	  2         2         0        
INET	  2         2         0        
FRAG	  0         0         0        
```

**「接続数が増えすぎていないか」を一目で見る**のに使います。

| 見るところ | 意味 |
|:--|:--|
| **`estab`** | **確立済みの接続数**。サーバの負荷の目安 |
| **`timewait`** | **TIME-WAIT の数**。数万件なら枯渇を疑う |
| `orphaned` | アプリが閉じたのにカーネルに残っているもの |

### -i TCP の内部情報

**「遅い」の原因を探るときに使います。**

```bash
$ ss -ti                               # TCP の内部パラメータを出す
```

```text
ESTAB 0      0          10.10.0.1:49662    10.10.0.2:http-alt
	 bbr wscale:10,10 rto:200 rtt:0.053/0.026 mss:1448 pmtu:1500 rcvmss:536 advmss:1448 cwnd:10 bytes_acked:1 segs_out:2 segs_in:1 send 2.19Gbps lastsnd:1532 lastrcv:1532 lastack:1532 pacing_rate 6.25Gbps delivered:1 app_limited rcv_space:14480 rcv_ssthresh:64088 minrtt:0.053 snd_wnd:65160
```

| 項目 | 意味 |
|:--|:--|
| **`rtt:0.053/0.026`** | **往復時間（ミリ秒）と、そのばらつき**。大きければ経路が遠いか混んでいる |
| **`cwnd:10`** | **輻輳ウィンドウ**。小さいままなら、パケットロスで絞られている |
| **`retrans:`** | **再送**（この出力には無い＝再送ゼロ）。**出ていたらロスが起きている** |
| `mss:1448` | 1 セグメントの最大サイズ |
| `pmtu:1500` | 経路上の MTU |
| `bbr` / `cubic` | 輻輳制御アルゴリズム |

> **`retrans` が出ているかどうかが、いちばん実務的な見どころ**です。
> **再送が多いならパケットロスが起きています**。経路を
> [mtrによる経路品質の調査](./mtrによる経路品質の調査.md) で追ってください。

### -o タイマーを見る

```bash
$ ss -tno                              # タイマー情報付きで表示する
```

**タイマーが動いているソケットにだけ `timer:(...)` が付きます。**
**何も起きていない確立済み接続には出ません**（実測）。

| 表示 | 意味 |
|:--|:--|
| **`timer:(retrans,...)`** | **いま再送中**。相手に届いていない |
| **`timer:(keepalive,...)`** | キープアライブ待ち |
| `timer:(on,...)` | 再送タイマー作動中 |
| **（何も出ない）** | **タイマーが動いていない。正常** |

---

## どのプロセスがポートを握っているか

**「ポートが使用中で起動できない」への対処**です。

```bash
$ sudo ss -tlnp 'sport = :8080'        # 8080 番を握っているプロセスを特定する
```

```text
State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process                     
LISTEN 0      1            0.0.0.0:8080      0.0.0.0:*     users:(("nc",pid=499,fd=3))
```

**`pid=499` が分かれば、あとは追えます。**

```bash
$ ps -p 499 -o pid,ppid,user,cmd       # そのプロセスの正体を見る
$ sudo ls -l /proc/499/exe             # 実行ファイルの実体を確認する
$ sudo kill 499                        # 止める（必要なら）
```

> **他ユーザのプロセスを見るには root 権限が必要**です。
> **自分が起動したプロセスなら一般ユーザでも表示されます**が、
> **他人のものは `Process` 列が空になり、「誰も使っていない」ように見えます。**
> **`sudo` を付け忘れて「原因不明」になるのがよくある詰まり方**です。

---

## 参考リンク

- [man 8 ss](https://man7.org/linux/man-pages/man8/ss.8.html)
- [man 8 netstat](https://man7.org/linux/man-pages/man8/netstat.8.html)
- [Red Hat — Verifying network configuration (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/index)

---

[← 全体の目次にもどる](../README.md)
