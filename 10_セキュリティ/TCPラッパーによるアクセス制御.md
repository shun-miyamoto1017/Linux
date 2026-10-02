# TCPラッパーによるアクセス制御

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★☆☆ |
| **Ping-t の範囲** | Linux1 / セキュリティ(主題110) — ホストのセキュリティ設定 |
| **業務での使いどころ** | **古い機器に残っている「もう一段の鍵」**。ファイアウォールの手前ではなく、サービスの直前で効くので、多層防御の1枚として今も監査で問われる。現代の同等機能は firewalld / nftables と sshd の `AllowUsers` |

> **パケットフィルタによる制御**は firewalld / iptables の担当です。
> **外からポートが開いているかの確認**は [ポートスキャンと疎通 nmapとnc](./ポートスキャンと疎通_nmapとnc.md) にまとめています。

---

## 目次

- [TCPラッパーとは](#tcpラッパーとは)
- [どこで効くのか](#どこで効くのか)
- [2つの設定ファイル](#2つの設定ファイル)
- [書式](#書式)
- [評価の順番](#評価の順番)
  - [実測で確かめる](#実測で確かめる)
  - [どちらにも無ければ許可される](#どちらにも無ければ許可される)
- [ホストの指定方法](#ホストの指定方法)
  - [ネットワーク全体を指定する](#ネットワーク全体を指定する)
  - [CIDR は使えるのか](#cidr-は使えるのか)
  - [ワイルドカード](#ワイルドカード)
- [hosts.allow だけで完結させる](#hostsallow-だけで完結させる)
- [効かないときに疑うこと](#効かないときに疑うこと)
- [確認に使うコマンド](#確認に使うコマンド)
- [現在の位置づけ](#現在の位置づけ)
- [参考リンク](#参考リンク)

---

## TCPラッパーとは

**TCP ラッパー（TCP Wrapper）は、ネットワークサービスへの接続を
「どのホストから来たか」で許可・拒否する仕組み**です。

```text
   デーモン   … tcpd
   ライブラリ … libwrap
```

**2つの使われ方があります。**

```text
  ① inetd / xinetd から tcpd を経由して起動する      （古い形）
  ② サービス自身が libwrap をリンクしている           （現在よく見る形）
```

検証環境で、libwrap をリンクしているバイナリを探してみます。

```bash
$ for b in /usr/sbin/*; do ldd "$b" 2>/dev/null | grep -q libwrap && echo "$b"; done   # libwrap 依存を探す
```

```text
/usr/sbin/in.ntalkd
/usr/sbin/in.talkd
/usr/sbin/inetd
/usr/sbin/rpc.statd
/usr/sbin/rpcbind
/usr/sbin/tcpd
/usr/sbin/tcpdchk
/usr/sbin/tcpdmatch
/usr/sbin/try-from
```

後半の 4 つは **TCP ラッパー自身のツール**なので、制御対象のサービスは前半の 5 つです。

**この一覧に出てこないサービスは、TCP ラッパーの制御対象外**です。
`hosts.deny` にいくら書いても効きません。ここが最大のつまずきどころです。

---

## どこで効くのか

**ファイアウォールとは別の層で働きます。**

```text
   [クライアント]
        │
        ▼
   ┌──────────────────────┐
   │ パケットフィルタ       │  ← firewalld / iptables / nftables
   │ （IP・ポートで遮断）   │     パケットそのものを落とす
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ TCP ラッパー           │  ← hosts.allow / hosts.deny
   │ （接続元ホストで判定） │     接続は成立するが、サービスが受け付けない
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ サービス自身の認証     │  ← sshd の AllowUsers、アプリの認証
   └──────────────────────┘
```

**TCP ラッパーで拒否されても、TCP の接続自体は一度成立します。**
パケットフィルタのように「無反応」にはならず、**接続後に切られる**点が違います。

---

## 2つの設定ファイル

| ファイル | 役割 |
|:--|:--|
| **`/etc/hosts.allow`** | **許可**する条件を書く |
| **`/etc/hosts.deny`** | **拒否**する条件を書く |

**単数形の `/etc/host.allow` / `/etc/host.deny` というファイルは存在しません。**

```bash
$ ls -l /etc/host.allow /etc/host.deny      # 単数形は無いことを確認する
```

```text
ls: cannot access '/etc/host.allow': No such file or directory
ls: cannot access '/etc/host.deny': No such file or directory
```

**どちらも `hosts`（複数形）**です。試験でもよく出る引っかけです。

**変更は即座に反映されます。** `tcpd` やサービスの再起動は要りません。
接続のたびにファイルが読み直されるためです。

---

## 書式

```text
サービス名 : ホスト名またはIPアドレス [: オプション]
```

```text
in.telnetd : 192.168.10.5
sshd : 192.168.10.
ALL : ALL
```

**サービス名は「デーモンのプロセス名」**です。`telnet` ではなく `in.telnetd`、
`ftp` ではなく `vsftpd` のように書きます。

**複数をカンマや空白で並べられます。**

```text
in.telnetd, in.ftpd : 192.168.10.5, 192.168.20.5
```

---

## 評価の順番

**この順番が、TCP ラッパーの理解の核心です。**

```text
   ① /etc/hosts.allow を見る
          └─ 一致した  →  【許可】して終わり（hosts.deny は見ない）
          └─ 一致しない →  ②へ

   ② /etc/hosts.deny を見る
          └─ 一致した  →  【拒否】
          └─ 一致しない →  【許可】
```

**ポイントは3つ。**

```text
   1. hosts.allow が先に評価される
   2. allow に一致したら、deny は一切見られない
   3. どちらにも一致しなければ「許可」になる（既定は通す）
```

> **例外** … 第3フィールドに `ALLOW` / `DENY` を書いた場合は、
> **`hosts.allow` での一致がそのまま拒否になることもあります。**
> 詳細は [hosts.allow だけで完結させる](#hostsallow-だけで完結させる) を参照してください。

### 実測で確かめる

`tcpdmatch` を使うと、**実際にサービスを動かさずに判定結果を確認できます。**

**まず「allow が deny より優先される」ことを確かめます。**
両方に同じホストを書いてみます。

```bash
$ cat /etc/hosts.allow                      # 許可設定を確認する
$ cat /etc/hosts.deny                       # 拒否設定を確認する
```

```text
in.telnetd : 192.168.10.5
in.telnetd : 192.168.10.5
```

```bash
$ tcpdmatch in.telnetd 192.168.10.5         # 判定結果を確認する
```

```text
client:   address  192.168.10.5
server:   process  in.telnetd
access:   granted
```

**`granted`。両方に書いても、先に見られる `hosts.allow` が勝ちます。**

**次に「deny を書いても allow にあれば通る」典型例**です。

```text
[hosts.allow]  in.telnetd : 192.168.10.
[hosts.deny]   ALL : ALL
```

```bash
$ tcpdmatch in.telnetd 192.168.10.5         # 許可された側
$ tcpdmatch in.telnetd 10.0.0.5             # 許可されていない側
$ tcpdmatch in.ftpd 192.168.10.5            # 別のサービス
```

```text
client:   address  192.168.10.5
server:   process  in.telnetd
access:   granted

client:   address  10.0.0.5
server:   process  in.telnetd
access:   denied

client:   address  192.168.10.5
server:   process  in.ftpd
access:   denied
```

**`in.ftpd` は `hosts.allow` に無いので、`hosts.deny` の `ALL : ALL` に落ちて拒否されました。**
**サービス名も条件のうち**だということが分かります。

### どちらにも無ければ許可される

**両方のファイルを空にして試します。**

```bash
$ : > /etc/hosts.allow                      # 許可設定を空にする
$ : > /etc/hosts.deny                       # 拒否設定を空にする
$ tcpdmatch in.telnetd 10.0.0.5             # 判定結果を確認する
```

```text
client:   address  10.0.0.5
server:   process  in.telnetd
access:   granted
```

**何も書かなければ全部通ります。**
**`hosts.deny` に `ALL : ALL` を置いて「原則拒否」にするのが基本形**です。

```text
[hosts.deny]   ALL : ALL          ← まず全部拒否
[hosts.allow]  sshd : 192.168.10. ← 必要なものだけ許可
```

---

## ホストの指定方法

### ネットワーク全体を指定する

| 書き方 | 意味 |
|:--|:--|
| **`192.168.10.`** | **末尾をドットで終える**と、そのネットワーク全体 |
| **`192.168.20.0/255.255.255.0`** | **アドレス / ネットマスク**の形式 |
| `.example.com` | **先頭がドット**なら、そのドメインに属するホスト全体 |

実測します。

```text
[hosts.allow]
in.telnetd : 192.168.10.
in.ftpd : 192.168.20.0/255.255.255.0
[hosts.deny]
ALL : ALL
```

```bash
$ tcpdmatch in.telnetd 192.168.10.99        # 末尾ドット形式
$ tcpdmatch in.ftpd 192.168.20.99           # アドレス/ネットマスク形式
```

```text
access:   granted
access:   granted
```

**どちらも効きました。**

### CIDR は使えるのか

**教材では「CIDR のプレフィックス表記は使えない」と書かれていることがあります。**
**しかし Debian / Ubuntu の libwrap では使えました。** 実測します。

```text
[hosts.allow]
in.fingerd : 192.168.30.0/24
in.finger2 : 192.168.40.0/26
[hosts.deny]
ALL : ALL
```

```bash
$ for h in 192.168.30.1 192.168.30.255 192.168.31.1; do tcpdmatch in.fingerd $h | tail -1; done   # /24 の境界
```

```text
access:   granted
access:   granted
access:   denied
```

```bash
$ for h in 192.168.40.1 192.168.40.63 192.168.40.64 192.168.40.200; do tcpdmatch in.finger2 $h | tail -1; done   # /26 の境界
```

```text
access:   granted
access:   granted
access:   denied
access:   denied
```

**`/26` の境界（`.63` は許可、`.64` は拒否）が正確に効いています。**
プレフィックス長が本当に解釈されている、という証拠です。

```bash
$ dpkg -s libwrap0 | grep -E '^(Package|Version)'   # ライブラリの版を確認する
```

```text
Package: libwrap0
Version: 7.6.q-33
```

```text
   検証環境: Ubuntu 24.04 / libwrap0 7.6.q-33  →  CIDR 表記が使える
```

> **ただし移植性はありません。**
> **本家の仕様には無い**書き方です。`hosts_access(5)` は
> **IPv4 では `n.n.n.n/m.m.m.m`（アドレス/ネットマスク）のみ**と規定しており、
> プレフィックス長の表記は **IPv6 用**として記載されています。
> Red Hat のドキュメントも
> 「When working in the IPv4 address space, the address/prefix length (prefixlen) pair
> declarations (CIDR notation) are not supported.」と明記しています。
> **Ubuntu の libwrap で通るのはディストリ側の実装差**です（出自までは確認できていません）。
>
> **試験では「使えない」が正答として扱われる可能性が高く、
> 実務でも移植性を考えれば末尾ドットかネットマスク形式で書くのが無難**です。

### ワイルドカード

| キーワード | 意味 |
|:--|:--|
| **`ALL`** | **すべて**（サービス名にもホストにも使える） |
| `LOCAL` | ホスト名にドットを含まない相手（同一ドメイン内） |
| `KNOWN` | 名前解決できる相手 |
| `UNKNOWN` | 名前解決できない相手 |
| **`PARANOID`** | **名前と逆引きが一致しない相手** |
| **`EXCEPT`** | **除外**する |

`EXCEPT` の実測です。

```text
[hosts.allow]  ALL : ALL EXCEPT 10.0.0.5
[hosts.deny]   ALL : ALL
```

```bash
$ tcpdmatch in.telnetd 192.168.10.5         # 除外されていないホスト
$ tcpdmatch in.telnetd 10.0.0.5             # 除外されたホスト
```

```text
access:   granted
access:   denied
```

**`10.0.0.5` は allow から除外され、deny の `ALL : ALL` に落ちて拒否されました。**

---

## hosts.allow だけで完結させる

**第3フィールドに `ALLOW` / `DENY` を書くと、`hosts.allow` 1つで許可も拒否も表せます。**

```text
サービス名 : ホスト : ALLOW
サービス名 : ホスト : DENY
```

```text
[hosts.allow]
in.telnetd : 192.168.10. : ALLOW
in.telnetd : ALL : DENY
[hosts.deny]（空）
```

```bash
$ tcpdmatch in.telnetd 192.168.10.5         # 許可したいホスト
$ tcpdmatch in.telnetd 10.0.0.5             # それ以外
```

```text
access:   granted
access:   denied
```

**狙いどおりです。ここで順番を逆にすると破綻します。** 実測します。

```text
[hosts.allow]
in.telnetd : ALL : DENY        ← DENY を先に書いてしまった
in.telnetd : 192.168.10. : ALLOW
```

```bash
$ tcpdmatch in.telnetd 192.168.10.5         # 許可したかったホスト
$ tcpdmatch in.telnetd 10.0.0.5             # それ以外
```

```text
access:   denied
access:   denied
```

**許可したかったホストまで拒否されました。**

```text
   ファイルは上から順に読まれ、最初に一致した行で判定が確定する
        ↓
   許可する行を先に、全拒否の行を最後に置く
```

**`ALL : DENY` は必ず最終行**です。これは `hosts.allow` 内でも同じ鉄則です。

---

## 効かないときに疑うこと

**「`hosts.deny` に書いたのにアクセスできてしまう」場合、原因は次のどれかです。**

| 原因 | 確認方法 |
|:--|:--|
| **`hosts.allow` に該当する記述がある** | allow が先に評価されるので、そちらが勝つ |
| **サービスが libwrap をリンクしていない** | `ldd $(which サービス) \| grep libwrap` |
| **サービス名の綴りが違う** | `in.telnetd` を `telnet` と書いていないか |
| ファイル名が単数形になっている | `/etc/host.deny` ではなく `/etc/hosts.deny` |
| そもそも inetd 経由で起動していない | systemd から直接起動しているサービスは対象外のことがある |

**現代の Linux では、2番目が圧倒的に多い**です。
**`sshd` も、ディストリビューションによっては libwrap を外してビルドされています。**
**必ず `ldd` で確認してから設定してください。**

---

## 確認に使うコマンド

| コマンド | 用途 |
|:--|:--|
| **`tcpdmatch サービス名 ホスト`** | **特定の組み合わせの判定結果を確認する** |
| **`tcpdchk`** | **設定ファイルの構文と整合性をチェックする** |

```bash
$ tcpdchk -v                                # 全ルールの内容と判定を表示する
```

```text
Using network configuration file: /etc/inetd.conf

>>> Rule /etc/hosts.allow line 1:
daemons:  in.telnetd
clients:  192.168.10.
access:   granted

>>> Rule /etc/hosts.allow line 2:
daemons:  nosuchd
clients:  10.0.0.1
access:   granted
```

**`tcpdchk` は `/etc/inetd.conf` を参照して、
「そんなサービスは登録されていない」といった不整合も検出します。**

> **注意 … 警告は端末に出ません。**
> Debian / Ubuntu の `tcpdchk` は共有 libwrap をリンクしており、
> 警告は `tcpd_warn()` 経由で **syslog に記録されます。**
> 上の実行例で `nosuchd` という存在しないサービス名を書いていますが、
> 標準出力にも標準エラー出力にも何も出ず、終了ステータスも 0 でした。
> syslog 側には次のように出ています。
>
> ```text
> tcpdchk: warning: hosts.allow, line 1: nosuchd: no such process name in /etc/inetd.conf
> tcpdchk: warning: hosts.allow, line 1: host address 10.0.0.1->name lookup failed
> ```
>
> **`journalctl -t tcpdchk` や `/var/log/syslog` を確認してください。**
> `tcpdchk -v` が端末に出すのは、ルールの一覧だけです。

**設定を変えたら、まず `tcpdmatch` で狙いどおりか確かめる。**
本番のサービスを止めずに検証できるので、必ず通してください。

---

## 現在の位置づけ

**TCP ラッパーは、もはや第一の防御ではありません。**

```text
   1990年代      … inetd + tcpd がアクセス制御の主役
        ↓
   2000年代      … iptables（パケットフィルタ）が主役に
        ↓
   現在          … firewalld / nftables + サービス自身の設定が主役
                   TCP ラッパーは「残っていれば使う」程度
```

**現代の同等機能**

| やりたいこと | 現在の手段 |
|:--|:--|
| IP で接続を遮断する | `firewalld` の rich rule、`nftables`、クラウドのセキュリティグループ |
| ssh を特定の IP からだけ許す | `sshd_config` の `Match Address` + `AllowUsers`、または firewalld |
| サービス単位で細かく制御する | systemd の `IPAddressAllow=` / `IPAddressDeny=` |

**それでも学ぶ価値があるのは、多層防御の考え方そのもの**です。

```text
   ネットワークで止める（SG / firewalld）
   ホストで止める      （TCP ラッパー / systemd）
   サービスで止める    （認証設定）
        ↓
   1枚破られても、次の層が残る
```

**古いシステムの引き継ぎでは実際に残っています。**
**`/etc/hosts.allow` と `/etc/hosts.deny` を読めることは、そのまま調査能力**です。

---

## 参考リンク

- [Red Hat Enterprise Linux 6 セキュリティガイド — TCP Wrappers の設定ファイル](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/6/html/security_guide/sect-security_guide-tcp_wrappers_and_xinetd-tcp_wrappers_configuration_files)
- [TCP Wrappers（Wikipedia）](https://en.wikipedia.org/wiki/TCP_Wrappers)
- [Debian Sources — hosts_access.c](https://sources.debian.org/src/tcp-wrappers/7.6.q-24/hosts_access.c/)

---

[← 全体の目次にもどる](../README.md)
