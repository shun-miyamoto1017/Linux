# パケットキャプチャ tcpdump

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★★ |
| **Ping-t の範囲** | Linux2 / ネットワーク構成(主題205) — ネットワークの問題解決 |
| **業務での使いどころ** | **「本当にパケットが出ているのか」を確かめる最後の手段**。設定は正しいのに繋がらない、ALB のヘルスチェックが落ちる、SG は開いているのに応答が無い。ログが何も言わないときに、事実を見せてくれるのがこれ |

> **疎通できるかどうか**は [疎通確認 pingとtraceroute](./疎通確認_pingとtraceroute.md)、
> **接続の一覧と統計**は [ネットワーク状態の確認 netstat](./ネットワーク状態の確認_netstat.md) にまとめています。

---

## 目次

- [tcpdump とは](#tcpdump-とは)
- [書式](#書式)
- [インタフェースを指定する](#インタフェースを指定する)
- [結果画面の見方](#結果画面の見方)
  - [ウェルノウンポートは名前に置き換わる](#ウェルノウンポートは名前に置き換わる)
  - [TCP の3ウェイハンドシェイク](#tcp-の3ウェイハンドシェイク)
- [よく使うオプション](#よく使うオプション)
  - [名前を引かせない](#名前を引かせない)
  - [中身を16進数で見る](#中身を16進数で見る)
  - [ファイルに保存する](#ファイルに保存する)
- [条件式で絞り込む](#条件式で絞り込む)
  - [host と src と dst](#host-と-src-と-dst)
  - [port で絞る](#port-で絞る)
  - [プロトコルで絞る](#プロトコルで絞る)
  - [条件式を組み合わせる](#条件式を組み合わせる)
  - [書けない条件式](#書けない条件式)
- [オプションと条件式を取り違えない](#オプションと条件式を取り違えない)
- [実務での使い方](#実務での使い方)
- [参考リンク](#参考リンク)

---

## tcpdump とは

**`tcpdump` は、インタフェースを流れるパケットをその場で捕まえて表示するコマンド**です。

```text
   ping      … 相手に届くかどうか          （○×が分かる）
   netstat   … 自ホストの接続の一覧        （状態が分かる）
   tcpdump   … 実際に流れているパケットそのもの（中身が分かる）
```

**「設定は合っているはずなのに繋がらない」の切り分けは、最後はここに行き着きます。**

| こう見えたら | 分かること |
|:--|:--|
| 自分の SYN が出ていない | **こちらのルーティングか名前解決の問題** |
| SYN は出ているが応答が無い | **経路の途中かファイアウォールで落ちている** |
| RST（`[R.]`）が返ってくる | **相手まで届いている**。ポートが閉じているか、ファイアウォールが RST で拒否している |

**実行には通常 root 権限が必要です。** 他人の通信まで見えてしまうためです。

---

## 書式

```text
tcpdump [オプション] [条件式]
```

**条件式を省略すると、そのインタフェースを流れる全パケットが対象**になります。

```bash
$ tcpdump -i lo -n -c 4 icmp                # lo を流れる ICMP を4個だけ捕まえる
```

```text
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on lo, link-type EN10MB (Ethernet), snapshot length 262144 bytes
15:43:32.024493 IP 127.0.0.1 > 127.0.0.1: ICMP echo request, id 1013, seq 1, length 64
15:43:32.024505 IP 127.0.0.1 > 127.0.0.1: ICMP echo reply, id 1013, seq 1, length 64
15:43:32.345538 IP 127.0.0.1 > 127.0.0.1: ICMP echo request, id 1013, seq 2, length 64
15:43:32.345552 IP 127.0.0.1 > 127.0.0.1: ICMP echo reply, id 1013, seq 2, length 64
4 packets captured
12 packets received by filter
0 packets dropped by kernel
```

末尾の3行は**統計**です。

| 行 | 意味 |
|:--|:--|
| `4 packets captured` | 条件に合致して**表示した**数 |
| `12 packets received by filter` | **条件式に合致してカーネルが渡した数**。`captured` との差は `-c` による打ち切りなどで生じる（**意味は OS 依存**。Linux では合致した数） |
| **`0 packets dropped by kernel`** | **カーネルが取りこぼした数。ここが増えるなら負荷が高い** |

---

## インタフェースを指定する

**`-i` で監視するインタフェースを指定**します。使えるものは `-D` で一覧できます。

```bash
$ tcpdump -D                                # キャプチャできるインタフェースを一覧する
```

```text
1.eth0 [Up, Running, Connected]
2.any (Pseudo-device that captures on all interfaces) [Up, Running]
3.lo [Up, Running, Loopback]
4.ifb0 [none]
5.ifb1 [none]
6.bluetooth-monitor (Bluetooth Linux Monitor) [Wireless]
7.nflog (Linux netfilter log (NFLOG) interface) [none]
8.nfqueue (Linux netfilter queue (NFQUEUE) interface) [none]
```

**物理 NIC のほかに `nflog` / `nfqueue` / `bluetooth-monitor` といった擬似デバイスも並びます。**

**`-i any` で全インタフェースをまとめて見られます。**

**`-i` を省略するとどうなるか**は誤解が多いところです。実測します。

```bash
$ tcpdump -n -c 1                           # -i を付けずに実行する
```

```text
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
```

**`listening on eth0`** — 全インタフェースではなく、**有効なもののうち1つが自動で選ばれます。**
狙ったインタフェースを見たいなら、**`-i` は必ず付けてください。**

---

## 結果画面の見方

オプションを何も付けない出力は、次の並びになります。

```text
時刻              プロトコル  送信元 > 送信先 : 内容
15:43:32.024493   IP         127.0.0.1 > 127.0.0.1: ICMP echo request, id 1013, seq 1, length 64
```

| 位置 | 意味 |
|:--|:--|
| 先頭 | **時刻**（マイクロ秒まで） |
| `IP` | プロトコル（IPv4。IPv6 なら `IP6`） |
| `>` の左 | **送信元** |
| `>` の右 | **送信先** |
| `:` の後ろ | パケットの内容 |

**アドレスとポートはドットでつながって表示されます。**

```text
   127.0.0.1.45356
   └───┬───┘ └─┬─┘
    IPアドレス  ポート番号
```

**区切りがコロンではなくドット**なので、IP アドレスの一部と見間違えないよう注意してください。

### ウェルノウンポートは名前に置き換わる

**既定では、ポート番号がサービス名に置き換えられます。** 実測で並べます。

```bash
$ tcpdump -i lo -c 3 tcp port 80            # 名前解決あり（既定）
```

```text
15:44:17.681722 IP localhost.45352 > localhost.http: Flags [S], seq 3584627835, win 65495, ...
```

```bash
$ tcpdump -i lo -n -c 3 tcp port 80         # -n を付けて名前解決を止める
```

```text
15:44:21.204721 IP 127.0.0.1.45356 > 127.0.0.1.80: Flags [S], seq 655226366, win 65495, ...
```

**`localhost.http` と `127.0.0.1.80` は同じもの**です。
**番号を知らないと読めない**ので、主なウェルノウンポートは覚えておく必要があります。

| ポート | サービス | tcpdump の表示 |
|:--|:--|:--|
| 20 / 21 | FTP | `ftp-data` / `ftp` |
| 22 | SSH | `ssh` |
| 23 | TELNET | `telnet` |
| 25 | SMTP | `smtp` |
| 53 | DNS | `domain` |
| 80 | HTTP | `http` |
| 110 | POP3 | `pop3` |
| 443 | HTTPS | `https` |

**対応表の元ネタは `/etc/services`** です。

### TCP の3ウェイハンドシェイク

接続の始まりは、`Flags` を見れば一目で分かります。

```bash
$ tcpdump -i lo -n -c 3 tcp port 80         # 接続開始の3パケットを捕まえる
```

```text
15:44:21.204721 IP 127.0.0.1.45356 > 127.0.0.1.80: Flags [S], seq 655226366, win 65495, options [mss 65495,sackOK,TS val 1456231442 ecr 0,nop,wscale 10], length 0
15:44:21.204737 IP 127.0.0.1.80 > 127.0.0.1.45356: Flags [S.], seq 176315348, ack 655226367, win 65483, options [mss 65495,sackOK,TS val 647116801 ecr 1456231442,nop,wscale 10], length 0
15:44:21.204749 IP 127.0.0.1.45356 > 127.0.0.1.80: Flags [.], ack 1, win 64, options [nop,nop,TS val 1456231442 ecr 647116801], length 0
```

```text
   ① Flags [S]   … SYN        クライアント → サーバ  「つなぎたい」
   ② Flags [S.]  … SYN+ACK    サーバ → クライアント  「いいよ」
   ③ Flags [.]   … ACK        クライアント → サーバ  「了解」
```

**`.` は ACK を表します。**

| 表示 | フラグ | 意味 |
|:--|:--|:--|
| `[S]` | SYN | 接続の開始要求 |
| `[S.]` | SYN+ACK | 接続要求への応答 |
| `[.]` | ACK | 確認応答だけ |
| `[P.]` | PSH+ACK | **データが乗っている** |
| `[F.]` | FIN+ACK | 正常な切断 |
| **`[R.]`** | **RST+ACK** | **接続の拒否。待ち受けていないポートへの SYN に返る** |
| `[R]` | RST | ACK を伴わない RST。確立済み接続の強制切断などで出る |

**SYN への拒否は `[R]` ではなく `[R.]`（RST+ACK）**です。実測します。

```bash
$ tcpdump -i lo -n -c 2 'tcp port 9998'     # 待ち受けていないポートへ繋いでみる
```

```text
23:11:21.891915 IP 127.0.0.1.43966 > 127.0.0.1.9998: Flags [S], seq 804889772, win 65495, options [mss 65495,sackOK,TS val 3365489840 ecr 0,nop,wscale 10], length 0
23:11:21.891937 IP 127.0.0.1.9998 > 127.0.0.1.43966: Flags [R.], seq 0, ack 804889773, win 0, length 0
```

**`.` が付くのは、SYN を受け取ったことへの ACK を兼ねているから**です。

**`[S]` を送ったのに `[R.]` が返るなら、相手までは届いています。**
**`[S]` を送ったきり何も返らないなら、途中で落とされています。** この2つの区別が切り分けの要です。

> **ただし `[R.]` だけでポートが閉じているとは断定できません。**
> ファイアウォールが `REJECT --reject-with tcp-reset` で拒否している場合も、
> **待ち受けているポートに対して同じ `[R.]` が返ります。**
> 相手にログインできるなら `ss -lnt` で待ち受けの有無を確かめてください。

`mss` `sackOK` `wscale` といった `options` は接続開始時に交換される TCP オプションで、
**SYN のパケットに並ぶのが普通**です。

---

## よく使うオプション

| オプション | 意味 |
|:--|:--|
| **`-i インタフェース`** | 監視するインタフェースを指定する（`any` で全部） |
| **`-n`** | **名前解決をしない**（IP とポート番号のまま表示） |
| `-nn` | **`-n` を 2 回指定した形**。名前解決の抑止をさらに強めるという意味だが、**TCP/IP の出力は `-n` と変わらなかった**（実測。同じ pcap を `-n` と `-nn` で読んで差分ゼロ） |
| **`-c 個数`** | 指定した数だけ捕まえたら終了する |
| **`-X`** | **中身を16進数と ASCII で表示する** |
| `-A` | 中身を ASCII だけで表示する |
| `-w ファイル` | **結果をファイルに保存する**（Wireshark で開ける） |
| `-r ファイル` | 保存したファイルを読み込む |
| `-v` / `-vv` | 詳細に表示する |
| `-s バイト` | 1 パケットあたり読み取る長さ（**既定 262144 バイト**。通常のフレームなら実質全部入る） |
| `-p` | **プロミスキャスモードにしない**。プロミスキャスモードとは「自分宛て以外のパケットも拾う受信モード」のこと（`-p` はポート指定ではない） |
| `-D` | キャプチャできるインタフェースを一覧する |

### 名前を引かせない

**`-n` は実務ではほぼ必須**です。

```text
  ✓ DNS の逆引きが遅い環境で待たされない
  ✓ tcpdump 自身が出す DNS パケットが混ざらない
  ✓ IP アドレスのまま見えるので grep しやすい
```

**`-n` は `ping` `traceroute` `netstat` `arp` でも同じ意味**です。まとめて覚えてください。

> **`-n` だけでポート番号も数字になります。** tcpdump 4.99.4 で実測すると、
> `-n` と `-nn` の出力は IP・ポートの表示に関しては同一でした。
> ```text
> [-n ]  23:11:24.431295 IP 127.0.0.1.58820 > 127.0.0.1.80: Flags [S], ...
> [-nn]  23:11:26.967615 IP 127.0.0.1.58832 > 127.0.0.1.80: Flags [S], ...
> ```

### 中身を16進数で見る

**`-X` はパケットの中身を16進数と ASCII の対応表で表示**します。
独自プロトコルや、文字化けしているデータの中身を見るときに使います。

```bash
$ tcpdump -i lo -n -X -c 1 'tcp port 80 and greater 100'   # 中身のあるパケットを1つ捕まえる
```

```text
15:44:29.566873 IP 127.0.0.1.59824 > 127.0.0.1.80: Flags [P.], seq 749768378:749768421, ack 397157831, win 64, options [nop,nop,TS val 3520016343 ecr 2091727373], length 43: HTTP: GET /index.html HTTP/1.0
	0x0000:  4500 005f 1e5c 4000 4006 1e3b 7f00 0001  E.._.\@.@..;....
	0x0010:  7f00 0001 e9b0 0050 2cb0 8eba 17ac 25c7  .......P,.....%.
	0x0020:  8018 0040 fe53 0000 0101 080a d1cf 2fd7  ...@.S......../.
	0x0030:  7cad 3a0d 4745 5420 2f69 6e64 6578 2e68  |.:.GET./index.h
	0x0040:  746d 6c20 4854 5450 2f31 2e30 0d0a 486f  tml.HTTP/1.0..Ho
	0x0050:  7374 3a20 6578 616d 706c 650d 0a0d 0a    st:.example....
```

**右側の ASCII で `GET /index.html HTTP/1.0` が読めます。**
左端の `0x0000:` はパケット先頭からのオフセットです。

> **注意** … 平文のプロトコルは中身が丸見えになります。
> 本番環境で取ったキャプチャには**認証情報が含まれている可能性がある**ので、
> 保存先と共有範囲には十分注意してください。

### ファイルに保存する

**長時間の調査は、画面に出さずファイルに落として後で解析するのが定石**です。

```bash
$ tcpdump -i eth0 -n -w /tmp/cap.pcap tcp port 443   # ファイルに保存する（画面には出ない）
$ tcpdump -n -r /tmp/cap.pcap | head -20             # 保存したものを読む
```

**`.pcap` は Wireshark でそのまま開けます。**
現地でキャプチャして手元で解析する、という分担ができます。

---

## 条件式で絞り込む

**条件式（フィルタ）を書かないと、全部のパケットが流れてきて読めません。**

### host と src と dst

**この3つの違いが最もよく問われます。** 実測で並べます。

`127.0.0.2` から `127.0.0.1` へ ping を打ち、条件式だけを変えて捕まえました。

```bash
$ tcpdump -i lo -n -c 2 host 127.0.0.2      # 送信元・送信先のどちらかが一致
```

```text
15:43:55.732988 IP 127.0.0.2 > 127.0.0.1: ICMP echo request, id 1043, seq 1, length 64
15:43:55.733001 IP 127.0.0.1 > 127.0.0.2: ICMP echo reply, id 1043, seq 1, length 64
```

**要求と応答の両方が出ました。**

```bash
$ tcpdump -i lo -n -c 2 src host 127.0.0.2  # 送信元が一致するものだけ
```

```text
15:43:57.065474 IP 127.0.0.2 > 127.0.0.1: ICMP echo request, id 1048, seq 1, length 64
15:43:57.369578 IP 127.0.0.2 > 127.0.0.1: ICMP echo request, id 1048, seq 2, length 64
```

**要求だけになりました。**

```bash
$ tcpdump -i lo -n -c 2 dst host 127.0.0.2  # 送信先が一致するものだけ
```

```text
15:43:59.097453 IP 127.0.0.1 > 127.0.0.2: ICMP echo reply, id 1053, seq 1, length 64
15:43:59.417561 IP 127.0.0.1 > 127.0.0.2: ICMP echo reply, id 1053, seq 2, length 64
```

**応答だけになりました。**

```text
   host  IP    … その IP が「送信元または送信先」  → 往復とも見える
   src   host  … その IP が「送信元」              → 行きだけ
   dst   host  … その IP が「送信先」              → 帰りだけ
```

**`src` / `dst` は型（`host` / `net` / `port`）を省くと `host` とみなされます。**
`src 127.0.0.2` は `src host 127.0.0.2` と同じです。実測します。

```bash
$ tcpdump -i lo -n -c 2 src 127.0.0.2       # host を省いて書く
```

```text
23:11:19.853905 IP 127.0.0.2 > 127.0.0.1: ICMP echo request, id 1537, seq 1, length 64
23:11:20.178118 IP 127.0.0.2 > 127.0.0.1: ICMP echo request, id 1537, seq 2, length 64
```

**同じ結果になります。** ただし読み手に意図が伝わるよう、**`src host` と明示するのを勧めます。**

### port で絞る

```bash
$ tcpdump -i eth0 -n port 80                # 送信元・送信先どちらかが 80 番
$ tcpdump -i eth0 -n src port 80            # 送信元が 80 番
$ tcpdump -i eth0 -n dst port 443           # 送信先が 443 番
$ tcpdump -i eth0 -n portrange 8000-8100    # ポートの範囲で絞る
```

### プロトコルで絞る

**条件式に直接書けるのは、TCP/IP のレベルのプロトコル名だけ**です。

| 書ける | `tcp` / `udp` / `icmp` / `arp` / `ip` / `ip6` / `rarp` |
|:--|:--|
| **書けない** | **`http` / `ftp` / `smtp` など、アプリケーション層のプロトコル名** |

**HTTP を見たいときはポート番号で指定**します。

```bash
$ tcpdump -i eth0 -n tcp port 80            # HTTP を見たいときはこう書く
```

### 条件式を組み合わせる

| 演算子 | 意味 |
|:--|:--|
| `and` / `&&` | かつ |
| `or` / `\|\|` | または |
| `not` / `!` | でない |

```bash
$ tcpdump -i eth0 -n 'host 10.0.0.5 and tcp port 443'      # 両方を満たす
$ tcpdump -i eth0 -n 'port 80 or port 443'                 # どちらか
$ tcpdump -i eth0 -n 'not port 22'                         # SSH 以外（自分の接続を除く）
$ tcpdump -i eth0 -n 'src host 10.0.0.5 and dst port 3306' # あのホストから DB への接続だけ
```

**`not port 22` は実務で必ず使います。**
ssh でログインして tcpdump を叩くと、**自分の ssh 通信で画面が埋まる**からです。

**条件式はシングルクォートで囲んでください。** `(` `)` `!` はシェルが解釈してしまいます。

### 書けない条件式

実測すると、どれも同じエラーになります。

```bash
$ tcpdump -i lo -c 1 http                   # アプリケーション層のプロトコル名
$ tcpdump -i lo -c 1 tcp:21                 # コロンでポートをつなぐ書き方
$ tcpdump -i lo -c 1 destination host 127.0.0.1   # destination という綴り
```

```text
tcpdump: can't parse filter expression: syntax error
tcpdump: can't parse filter expression: syntax error
tcpdump: can't parse filter expression: syntax error
```

**`destination` / `source` / `dest` は存在しません。** 正しくは `dst` / `src` です。
**`tcp:21` や `21/tcp` という書き方もできません。** `tcp port 21` と書きます。

---

## オプションと条件式を取り違えない

**`-p` はポート指定ではありません。** man で確認します。

```bash
$ man tcpdump | grep -A3 '^ *-p$'           # -p の意味を確認する
```

```text
       -p
       --no-promiscuous-mode
	      Don't put the interface into promiscuous mode.
```

**プロミスキャスモードを使わない**という意味です。
ポートを指定したいときは、オプションではなく**条件式の `port`** を使ってください。

```text
   ✗ tcpdump -i eth0 -p 80        →  -p はプロミスキャスモードの抑止
   ○ tcpdump -i eth0 port 80      →  条件式でポートを指定する
```

**インタフェースも同じです。** 条件式の位置に書くと構文エラーになります。

```text
   ✗ tcpdump eth0                 →  eth0 を条件式として解釈しようとする
   ○ tcpdump -i eth0              →  オプションで指定する
```

---

## 実務での使い方

**1. 「出ているか」と「返ってきているか」を分けて見る**

```bash
$ tcpdump -i eth0 -n 'host 10.0.0.5' | head -20   # 相手との往復をまとめて見る
```

```text
   自分の SYN が出ていない        → ルーティングか名前解決を疑う
   SYN は出たが応答が無い          → 経路の途中かファイアウォール
   RST が返る                      → 相手は生きているがポートが閉じている
```

**2. 相手を絞ってから見る**

いきなり全部を見ると流れが速すぎて読めません。
**まず `host` で相手を絞り、次に `port` を足す**、という順番が確実です。

**3. 長時間はファイルへ**

```bash
$ tcpdump -i eth0 -n -w /tmp/cap.pcap -C 100 -W 5 'host 10.0.0.5'   # 100MB×5本で循環させる
```

`-C` でファイルを分割し、`-W` で本数を制限すると、**ディスクを食い尽くしません。**
長時間の再現待ちではこの形にしてください。

**4. 負荷に注意する**

```text
  ✗ 本番の高トラフィック機で条件式なしの tcpdump を放置する
       → CPU を食い、packets dropped by kernel が増え、
         ディスクも埋まる

  ○ 条件式で絞り、-c か -W で上限を付け、終わったら必ず止める
```

**`packets dropped by kernel` が 0 でないキャプチャは、取りこぼしがあります。**
その数字を見ずに「パケットが来ていない」と結論づけないでください。

---

## 参考リンク

- [man 1 tcpdump](https://man7.org/linux/man-pages/man1/tcpdump.1.html)
- [man 7 pcap-filter（条件式の文法）](https://man7.org/linux/man-pages/man7/pcap-filter.7.html)
- [tcpdump 公式](https://www.tcpdump.org/)

---

[← 全体の目次にもどる](../README.md)
