# 名前解決の確認 digとhost

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / ネットワークの基礎(主題1.07) — 基本的なネットワークの問題解決 |
| **業務での使いどころ** | **「つながらない」の 3 割は DNS。**切り替え直後の障害、キャッシュの残存、Route 53 の伝播確認で必ず使う |

> **このノートは「名前が IP に変わるか」**です。
> **相手まで届くか**は [疎通確認 pingとtraceroute](./疎通確認_pingとtraceroute.md)、
> **自分側のアドレス設定**は [アドレスとルーティングの確認](./アドレスとルーティングの確認.md) にあります。
> DNS サーバを**立てる**側（BIND のゾーンファイルなど）は `09_DNS` フォルダで扱います。

---

## 目次

- [名前解決はどの順番で行われるか](#名前解決はどの順番で行われるか)
- [設定ファイル 3 つ](#設定ファイル-3-つ)
- [host コマンド](#host-コマンド)
- [dig コマンド](#dig-コマンド)
  - [dig のよく使うオプション](#dig-のよく使うオプション)
  - [dig の結果画面の見方](#dig-の結果画面の見方)
- [nslookup コマンド](#nslookup-コマンド)
- [3 つのコマンドの使い分け](#3-つのコマンドの使い分け)
- [主なリソースレコード](#主なリソースレコード)
- [DNS の障害を切り分ける](#dns-の障害を切り分ける)
- [参考リンク](#参考リンク)

---

## 名前解決はどの順番で行われるか

**アプリが `example.com` に接続しようとしたとき、OS は決まった順番で名前を調べます。**

```text
 アプリが「example.com に接続したい」
        ↓
 ① /etc/nsswitch.conf を見て、「どの順番で調べるか」を決める
        ↓
 ② /etc/hosts を見る          ← ここに書いてあれば、DNS には聞かない
        ↓ 無ければ
 ③ /etc/resolv.conf の DNS サーバに問い合わせる
        ↓
 ④ 返ってきた IP へ接続する
```

**この順番を知らないと切り分けられません。**

| 症状 | 原因 |
|:--|:--|
| **`dig` では正しい IP が返るのに、アプリは別の IP に繋ぐ** | **`/etc/hosts` に古い記述が残っている** |
| **`ping` は名前を引けるが `dig` が失敗する** | `/etc/hosts` で解決していて、**DNS 自体は壊れている** |
| どのコマンドでも引けない | `/etc/resolv.conf` の DNS サーバに届いていない |

> **`dig` と `host` の最大の違いはここです。**
> **`dig` は DNS サーバに直接聞く**ので、`/etc/hosts` を無視します。
> **`host` と `ping` は OS の解決順（`nsswitch.conf`）に従う**ので、`/etc/hosts` を先に見ます。
>
> **「アプリからは繋がらないのに `dig` は正しい」なら `/etc/hosts` を疑う**、が定石です。

---

## 設定ファイル 3 つ

### /etc/hosts

**IP アドレスとホスト名の対応を、手動で書いておくファイル**です。**DNS より先に参照されます。**

```bash
$ cat /etc/hosts                     # 静的な名前解決の設定を見る
127.0.0.1   localhost localhost.localdomain
::1         localhost localhost.localdomain
10.0.1.30   db01 db01.internal
```

```text
 10.0.1.30   db01  db01.internal
 └───┬───┘   └─┬─┘  └─────┬─────┘
  IPアドレス   別名   正式名（FQDN）
```

| 使いどころ | 内容 |
|:--|:--|
| **DNS を立てない小規模環境** | 数台なら `/etc/hosts` で足りる |
| **移行時の切り替え確認** | **DNS を変える前に、自分だけ新しい IP を向ける** |
| **障害時の緊急回避** | DNS が落ちても、ここに書けば通信できる |

> **`/etc/hosts` への追記は「その 1 台だけ」に効きます。**
> **消し忘れると、後日「なぜかこのサーバだけ古い IP に繋ぐ」という調査困難な障害**になります。
> **書いたら、いつ消すかも同時に決めます。**

### /etc/resolv.conf

**問い合わせ先の DNS サーバを指定するファイル**です。

```bash
$ cat /etc/resolv.conf               # 参照する DNS サーバを見る
search internal.example.com
nameserver 10.0.0.2
nameserver 8.8.8.8
options timeout:2 attempts:2
```

| 項目 | 意味 |
|:--|:--|
| **`nameserver`** | **問い合わせ先の DNS サーバ。**上から順に試す。**最大 3 つまで**（超えた分は無視される） |
| **`search`** | **ドメイン名を補完する。**`db01` と書くと `db01.internal.example.com` も試す |
| `domain` | 自分のドメイン（`search` に 1 つ書くのと同等。**両方書くと後に書いたほうが有効**） |
| `options timeout:2` | **1 台あたりの待ち時間**（既定 5 秒） |
| `options attempts:2` | 再試行の回数（既定 2 回） |

> **`nameserver` が複数あっても、負荷分散はしません。**
> **1 つ目がタイムアウトしてから 2 つ目**に行くので、**1 台目が落ちていると毎回待たされます**。
> `options timeout:2` を入れておくと、体感がかなり変わります。

**注意 … このファイルは自動生成されることが多い**

| 環境 | 誰が書き換えるか |
|:--|:--|
| **DHCP 環境** | **DHCP クライアントが上書きする** |
| **NetworkManager** | `nmcli` の設定から生成する |
| **systemd-resolved** | **`/etc/resolv.conf` が `stub-resolv.conf` へのシンボリックリンク**になる |

```bash
$ ls -l /etc/resolv.conf             # 実体かリンクかを確認する
lrwxrwxrwx 1 root root 39 Sep 14 01:00 /etc/resolv.conf -> ../run/systemd/resolve/stub-resolv.conf
```

**リンクになっている場合、直接編集しても再起動で消えます。**
`nmcli` や `systemd-resolved` 側で設定します。

```bash
$ resolvectl status                  # systemd-resolved が使う DNS を確認する
```

### /etc/nsswitch.conf

**「何を、どの順番で調べるか」を決めるファイル**です。

```bash
$ grep hosts /etc/nsswitch.conf      # 名前解決の順番を確認する
hosts:      files dns myhostname
```

| 値 | 意味 |
|:--|:--|
| **`files`** | **`/etc/hosts` を見る** |
| **`dns`** | **DNS に問い合わせる**（`/etc/resolv.conf` の設定を使う） |
| `myhostname` | 自分自身のホスト名を解決する |
| `mdns4_minimal` | mDNS（`.local`） |

**`files dns` の順なので、`/etc/hosts` が優先**されます。
**この順番を入れ替えることはまずありません**が、**「なぜ hosts が優先なのか」の根拠がここ**です。

---

## host コマンド

**`host` は、名前解決の結果を簡潔に表示するコマンド**です。**いちばん手軽**に使えます。

```text
host [オプション] 名前またはIP [問い合わせ先のDNSサーバ]
```

**例文**

```bash
$ host example.com                   # 名前から IP を引く
example.com has address 93.184.216.34
example.com has IPv6 address 2606:2800:220:1:248:1893:25c8:1946
example.com mail is handled by 0 .

$ host 8.8.8.8                       # 逆引き（IP から名前）
8.8.8.8.in-addr.arpa domain name pointer dns.google.

$ host -t MX example.com             # レコードの種類を指定する
example.com mail is handled by 0 .

$ host example.com 8.8.8.8           # 問い合わせ先の DNS サーバを指定する
Using domain server:
Name: 8.8.8.8
Address: 8.8.8.8#53
example.com has address 93.184.216.34
```

**よく使うオプション**

| オプション | 意味 |
|:--|:--|
| **`-t 種類`** | **レコードの種類を指定する**（`A` / `AAAA` / `MX` / `NS` / `TXT` / `CNAME` / `PTR`） |
| **`-a`** | **すべての情報を表示する**（`-t ANY` に近い詳細表示） |
| `-4` / `-6` | IPv4 / IPv6 で問い合わせる |
| `-v` | 詳細に表示する（`dig` に近い形式） |
| `-W 秒` | 応答を待つ時間 |

**`host` は `/etc/nsswitch.conf` に従う**ので、**`/etc/hosts` に書いた内容も反映されます**。
**「アプリと同じ見え方」を確認したいときは `host`** が適しています。

---

## dig コマンド

**`dig`（Domain Information Groper）は、DNS の問い合わせを詳細に行うコマンド**です。
**DNS サーバに直接問い合わせる**ため、**DNS 自体の状態を調べるのに最も向いています**。

```text
dig [@問い合わせ先のDNSサーバ] 名前 [レコードの種類] [+オプション]
```

**例文**

```bash
$ dig example.com                    # 既定の DNS サーバに A レコードを問い合わせる
$ dig +short example.com             # 結果だけを簡潔に表示する
93.184.216.34

$ dig @8.8.8.8 example.com           # 問い合わせ先を指定する
$ dig example.com MX                 # レコードの種類を指定する
$ dig -x 8.8.8.8                     # 逆引き
$ dig +trace example.com             # ルートから順にたどる
```

**補足 … `@` の位置**

```text
dig  @8.8.8.8   example.com   MX
      └──┬──┘    └────┬────┘   └┬┘
    問い合わせ先   調べる名前   種類
```

**`@` を付けた引数が「問い合わせ先の DNS サーバ」**です。**これを指定すると `/etc/resolv.conf` は使いません。**

### dig のよく使うオプション

| オプション | 意味 | 使いどころ |
|:--|:--|:--|
| **`+short`** | **答えだけを表示する** | **スクリプトで値を取る** |
| **`@サーバ`** | **問い合わせ先を指定する** | **権威サーバに直接聞いて、キャッシュを迂回する** |
| **`+trace`** | **ルートサーバから順にたどる** | **委任がどこで切れているか**を調べる |
| **`+noall +answer`** | **回答セクションだけ表示する** | 見やすくする定番 |
| **`+nocmd`** | 先頭のコマンド行を消す | 出力を短くする |
| `+stats` / `+nostats` | 統計を表示する／しない | — |
| **`+tcp`** | **TCP で問い合わせる** | 応答が大きいとき、UDP が塞がれているとき |
| **`+dnssec`** | DNSSEC の署名も要求する | 署名検証の確認 |
| `+time=秒` | タイムアウト | 反応の無いサーバを早く諦める |
| `+tries=回数` | 再試行の回数 | — |

```bash
$ dig +short example.com             # IP だけ
93.184.216.34

$ dig +noall +answer example.com     # 回答セクションだけ
example.com.        86400   IN  A   93.184.216.34

$ dig @ns1.example.com example.com   # 権威サーバに直接聞く（キャッシュを迂回する）
$ dig +trace example.com             # ルート → TLD → 権威 の順にたどる
```

### dig の結果画面の見方

```bash
$ dig example.com                    # 詳細な出力を見る

; <<>> DiG 9.18.28 <<>> example.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345      ← (1)
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1   ← (2)

;; QUESTION SECTION:                                            ← (3)
;example.com.                   IN      A

;; ANSWER SECTION:                                              ← (4)
example.com.            86400   IN      A       93.184.216.34

;; Query time: 24 msec                                          ← (5)
;; SERVER: 10.0.0.2#53(10.0.0.2) (UDP)                          ← (6)
;; WHEN: Sun Sep 14 01:00:00 JST 2026
;; MSG SIZE  rcvd: 56
```

| # | セクション | 何が分かるか |
|:-:|:--|:--|
| **(1)** | **`status`** | **問い合わせの結果。**ここが最重要（下の表） |
| **(2)** | **`flags`** と件数 | **`ANSWER: 0` なら答えが返っていない** |
| **(3)** | **QUESTION** | 何を聞いたか |
| **(4)** | **ANSWER** | **答え。名前 / TTL / クラス / 種類 / 値** |
| **(5)** | **`Query time`** | **応答にかかった時間。**遅いなら DNS サーバかネットワーク |
| **(6)** | **`SERVER`** | **実際に答えた DNS サーバ。**意図した相手か確認する |

**`status` の読み分け**

| `status` | 意味 | 疑うもの |
|:--|:--|:--|
| **`NOERROR`** | **問い合わせは成功** | ただし **`ANSWER: 0`** なら**そのレコードは存在しない** |
| **`NXDOMAIN`** | **その名前自体が存在しない** | **打ち間違い**、レコード未作成、委任の誤り |
| **`SERVFAIL`** | **DNS サーバ側の失敗** | 権威サーバに届いていない、DNSSEC の検証失敗 |
| `REFUSED` | 問い合わせを拒否された | **そのサーバが自分に対して応答しない設定** |
| `timed out` | 応答が無い | **53 番ポートが塞がれている**、サーバが落ちている |

> **`NOERROR` なのに `ANSWER: 0`** は見落としやすい組み合わせです。
> **「名前はあるが、そのレコード（A / MX など）は無い」**という意味になります。

**ANSWER セクションの読み方**

```text
 example.com.      86400    IN      A      93.184.216.34
 └────┬────┘      └─┬─┘   └┬┘    └┬┘    └──────┬──────┘
     名前           TTL   クラス  種類          値
```

| 項目 | 意味 |
|:--|:--|
| **名前** | 末尾の `.` はルートを表す（完全修飾名） |
| **TTL** | **キャッシュしてよい秒数。**切り替え時はここを事前に短くする |
| **クラス** | ほぼ常に `IN`（Internet） |
| **種類** | `A` / `AAAA` / `CNAME` / `MX` / `NS` / `TXT` / `PTR` |
| **値** | そのレコードの内容 |

**`+trace` の読み方**

```bash
$ dig +trace example.com             # ルートから順にたどる
.                  518400  IN  NS  a.root-servers.net.     ← ① ルートサーバ
com.               172800  IN  NS  a.gtld-servers.net.     ← ② .com を管理するサーバ
example.com.       172800  IN  NS  ns1.example.com.        ← ③ example.com の権威サーバ
example.com.       86400   IN  A   93.184.216.34           ← ④ 実際の答え
```

**途中で止まったところが、委任が切れている場所**です。
**「レコードは登録したのに引けない」ときは `+trace` で、どこまでたどれているかを見ます。**

---

## nslookup コマンド

**`nslookup` は、対話的にも使える古くからある名前解決コマンド**です。

```bash
$ nslookup example.com               # 名前を引く
Server:         10.0.0.2
Address:        10.0.0.2#53

Non-authoritative answer:
Name:   example.com
Address: 93.184.216.34

$ nslookup example.com 8.8.8.8       # 問い合わせ先を指定する（@ は付けない）
```

| 表示 | 意味 |
|:--|:--|
| **`Server`** | 問い合わせ先の DNS サーバ |
| **`Non-authoritative answer`** | **キャッシュからの回答**（権威サーバ本人ではない） |
| `Authoritative answer` | **その名前を管理しているサーバ本人**からの回答 |

**`nslookup` は BIND のツール群の中で非推奨扱いになった時期があり、
現在は `dig` と `host` が推奨**されています。
ただし**Windows には `nslookup` しか無い**ため、手順書では今も見かけます。

> **問い合わせ先の指定方法が `dig` と違います。**
> **`dig` は `@8.8.8.8`、`nslookup` は空白で区切って `8.8.8.8`** です。

---

## 3 つのコマンドの使い分け

| | **`host`** | **`dig`** | **`nslookup`** |
|:--|:--|:--|:--|
| **出力** | **短い。読みやすい** | **詳細。全セクション** | 中間 |
| **`/etc/hosts` を見るか** | **見る**（`nsswitch.conf` に従う） | **見ない**（DNS に直接聞く） | 見ない |
| **問い合わせ先の指定** | `host 名前 サーバ` | **`dig @サーバ 名前`** | `nslookup 名前 サーバ` |
| **スクリプト向け** | まずまず | **`+short` が最適** | 向かない |
| **障害調査** | 一次確認 | **本命**（`status` / `+trace`） | 代替 |
| 対話モード | 無し | 無し | **あり** |
| 主なパッケージ | `bind-utils` / `bind9-host` | `bind-utils` / `dnsutils` | 同左 |

```text
「とりあえず IP が知りたい」        → host または dig +short
「アプリと同じ見え方を確認したい」  → host（/etc/hosts も反映される）
「DNS そのものを疑っている」        → dig（status と SERVER を見る）
「委任・伝播を調べたい」            → dig +trace / dig @権威サーバ
```

**補足 … コマンドが入っていないとき**

```bash
$ sudo dnf install -y bind-utils     # RHEL 系
$ sudo apt install -y dnsutils       # Debian / Ubuntu 系
```

**`dig` も `host` も、多くの最小構成イメージには入っていません。**

---

## 主なリソースレコード

| 種類 | 意味 | 例 |
|:--|:--|:--|
| **`A`** | **名前 → IPv4 アドレス** | `example.com. IN A 93.184.216.34` |
| **`AAAA`** | **名前 → IPv6 アドレス** | `example.com. IN AAAA 2606:2800:…` |
| **`CNAME`** | **別名 → 正式名**（エイリアス） | `www.example.com. IN CNAME example.com.` |
| **`MX`** | **メールの配送先**（優先度つき） | `example.com. IN MX 10 mail.example.com.` |
| **`NS`** | **そのゾーンを管理する DNS サーバ** | `example.com. IN NS ns1.example.com.` |
| **`PTR`** | **IP → 名前**（逆引き） | `34.216.184.93.in-addr.arpa. IN PTR example.com.` |
| **`SOA`** | **ゾーンの管理情報**（シリアル、更新間隔） | — |
| **`TXT`** | **任意の文字列**（SPF / DKIM / 所有権確認） | `example.com. IN TXT "v=spf1 …"` |
| `SRV` | サービスの場所（ポート込み） | `_sip._tcp.example.com. IN SRV …` |

```bash
$ dig +noall +answer example.com A     # A レコードを引く
$ dig +noall +answer example.com MX    # メールの配送先を調べる
$ dig +noall +answer example.com NS    # 権威サーバを調べる
$ dig +noall +answer example.com TXT   # SPF などを確認する
```

**補足 … `CNAME` の注意点**

**`CNAME` を設定した名前には、他のレコードを共存させられません。**
また **ゾーンの頂点（`example.com` そのもの）には `CNAME` を置けません**。
AWS ではこの制約を回避するために **ALIAS レコード**（Route 53 独自）が用意されています。

**補足 … 逆引きは `in-addr.arpa`**

```text
 8.8.8.8 の逆引きは   8.8.8.8.in-addr.arpa
                      └─┬─┘
                  IP を逆順に並べる
```

**`dig -x 8.8.8.8` は、この変換を自動でやってくれます。**

---

## DNS の障害を切り分ける

**順番に確かめます。**

```bash
$ ping -c 1 8.8.8.8                  # ① IP では通信できるか（ここが駄目なら DNS 以前の問題）
$ cat /etc/resolv.conf                # ② どの DNS サーバを見ているか
$ dig @10.0.0.2 example.com          # ③ その DNS サーバは答えるか
$ dig @8.8.8.8 example.com           # ④ 外部の DNS なら答えるか
$ dig +trace example.com             # ⑤ 委任はどこまでたどれるか
$ grep example /etc/hosts             # ⑥ /etc/hosts に古い記述が無いか
```

| どこで失敗したか | 原因 |
|:--|:--|
| **①で失敗** | **DNS ではなくネットワークの問題** |
| **②が空／想定外** | DHCP の設定、`resolv.conf` の上書き |
| **③だけ失敗、④は成功** | **社内／VPC の DNS サーバの問題** |
| **③も④も失敗** | **53 番ポートが塞がれている**か、その名前が存在しない |
| **⑤が途中で止まる** | **委任（NS レコード）の設定漏れ** |
| **⑥に記述がある** | **`/etc/hosts` が優先されている**。アプリだけ挙動が違う原因 |

**キャッシュを疑うとき**

```bash
$ dig example.com | grep -E '^example|TTL|Query'   # TTL の残りを見る
$ sudo systemd-resolve --flush-caches               # systemd-resolved のキャッシュを消す
$ resolvectl flush-caches                           # 新しい書き方
$ dig @権威サーバ example.com                       # キャッシュを迂回して真の値を見る
```

> **「切り替えたのに古い IP に繋がる」の原因は、ほぼキャッシュです。**
> **`dig @権威サーバ` で真の値を確認**し、**TTL が切れるのを待つ**のが基本の対処になります。
> **切り替えの前に TTL を短くしておく**のが、事前にできる唯一の準備です。

---

## 参考リンク

- [man 1 dig](https://man7.org/linux/man-pages/man1/dig.1.html)
- [man 1 host](https://man7.org/linux/man-pages/man1/host.1.html)
- [man 1 nslookup](https://man7.org/linux/man-pages/man1/nslookup.1.html)
- [man 5 resolv.conf](https://man7.org/linux/man-pages/man5/resolv.conf.5.html)
- [man 5 hosts](https://man7.org/linux/man-pages/man5/hosts.5.html)
- [man 5 nsswitch.conf](https://man7.org/linux/man-pages/man5/nsswitch.conf.5.html)
- [man 1 resolvectl](https://man7.org/linux/man-pages/man1/resolvectl.1.html)
- [RFC 1034 — Domain Names: Concepts and Facilities](https://datatracker.ietf.org/doc/html/rfc1034)
- [AWS — VPC の DNS 属性](https://docs.aws.amazon.com/ja_jp/vpc/latest/userguide/vpc-dns.html)
- [AWS — Route 53 Resolver](https://docs.aws.amazon.com/ja_jp/Route53/latest/DeveloperGuide/resolver.html)
- [Kubernetes — Pod の DNS](https://kubernetes.io/ja/docs/concepts/services-networking/dns-pod-service/)

---

[← このフォルダの目次にもどる](./00_このフォルダにあるもの.md) ｜ [全体の目次にもどる](../README.md)
