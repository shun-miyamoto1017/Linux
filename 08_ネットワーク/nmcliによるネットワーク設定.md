# nmcliによるネットワーク設定

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★★ |
| **Ping-t の範囲** | Linux2 / ネットワーク設定 — ネットワーク設定の管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **RHEL 8 / 9 で IP を設定する正規の方法。**`ifcfg-eth0` を直接編集する時代は終わっている。**構築手順書に書くのも、障害時に直すのも `nmcli`** |

> **設定ファイルそのもの**は [ネットワーク設定ファイル](./ネットワーク設定ファイル.md)、
> **`ip` コマンドでその場で設定する方法**は
> [アドレスとルーティングの確認](./アドレスとルーティングの確認.md) にあります。
> **`ip` は再起動で消え、`nmcli` は残る**——これが使い分けの軸です。

> **このノートの検証状況**
> **`connection add` / `modify` / `show` / `delete` と、出力オプション（`-t` `-f` `-g` `-p`）は
> NetworkManager 1.46.0 で実測**しました。
> **ただし作業環境のインタフェースが `unmanaged` のままで、
> `connection up` による実際の有効化までは確認できていません。**
> **有効化の挙動と RHEL 固有のパスは、公式ドキュメントに基づいて記述**しています。

---

## 目次

- [なぜ nmcli を使うのか](#なぜ-nmcli-を使うのか)
- [3つの対象を区別する](#3つの対象を区別する)
- [まず現状を見る](#まず現状を見る)
- [設定を作る connection add](#設定を作る-connection-add)
  - [静的IPで作る](#静的ipで作る)
  - [DHCPで作る](#dhcpで作る)
  - [ipv4.method に指定できる値](#ipv4method-に指定できる値)
- [設定を変える connection modify](#設定を変える-connection-modify)
- [反映する up と down](#反映する-up-と-down)
- [設定の中身を全部見る](#設定の中身を全部見る)
- [出力を加工する](#出力を加工する)
- [設定ファイルはどこにあるか](#設定ファイルはどこにあるか)
- [業務でよく使う通しの手順](#業務でよく使う通しの手順)
  - [新しいサーバに静的IPを設定する](#新しいサーバに静的ipを設定する)
  - [既存サーバの DNS だけ変える](#既存サーバの-dns-だけ変える)
  - [トラブル時の確認順](#トラブル時の確認順)
- [nmtui という選択肢](#nmtui-という選択肢)
- [参考リンク](#参考リンク)

---

## なぜ nmcli を使うのか

**RHEL 8 以降、ネットワーク設定の持ち主は NetworkManager です。**

```text
  RHEL 6 まで   /etc/sysconfig/network-scripts/ifcfg-eth0 を直接編集 → service network restart
  RHEL 7        NetworkManager が入るが、ifcfg も現役
  RHEL 8        NetworkManager が主。ifcfg は NetworkManager が読む
  RHEL 9        ifcfg 形式は 非推奨。keyfile 形式（.nmconnection）が既定
  RHEL 10       ifcfg 形式の サポートが削除
```

**RHEL 9 でも ifcfg 形式は読まれますが、
同じ接続について keyfile と ifcfg が併存すると、どちらが効いているか分からなくなります。**
**手で編集した場合は `nmcli connection reload` が必要**で、忘れると設定が反映されません。
**`nmcli` から設定すれば、この食い違いが起きません。**

**`ip` との違い**

| | **`ip`** | **`nmcli`** |
|:--|:--|:--|
| **いつ効くか** | **すぐ効く** | **すぐ効く**（`up` した時点） |
| **再起動すると** | **消える** | **残る** |
| **設定の保存先** | **どこにも保存されない** | **`.nmconnection` ファイル** |
| **使いどころ** | **その場の切り分け・一時的な確認** | **本番の設定** |

```text
  障害対応で「とりあえず疎通させたい」   → ip addr add
  その設定を残したい                    → nmcli connection modify
      ▲ ip で直して満足して帰ると、次の再起動で元に戻る
```

---

## 3つの対象を区別する

**`nmcli` は「何に対する操作か」で 3 つに分かれます。**
**ここを混同すると、コマンドが組み立てられません。**

| 対象 | 省略形 | 何か |
|:--|:--|:--|
| **`connection`** | **`c`** / `con` | **設定（プロファイル）**。ファイルとして保存される |
| **`device`** | **`d`** / `dev` | **実際のインタフェース**（eth0 など） |
| **`general`** | `g` | **NetworkManager 全体の状態** |

```text
  connection   「こう設定する」という 定義         … 複数作れる。1つのNICに複数の定義を持てる
       │
       │  up / down で 結びつける
       ▼
  device       実際の NIC                          … 一度に1つの connection しか有効にできない
```

**この関係が分かると、次の使い分けが腑に落ちます。**

```bash
$ nmcli connection show                # どんな「設定」があるか
$ nmcli device status                  # 実際の NIC がどうなっているか
```

> **オフィス用とデータセンター用で 2 つの `connection` を作っておき、
> `nmcli connection up` で切り替える**——という使い方ができるのはこの構造のためです。

---

## まず現状を見る

```bash
$ nmcli general status                 # NetworkManager 全体の状態
```

```text
STATE         CONNECTIVITY  WIFI-HW  WIFI     WWAN-HW  WWAN    
disconnected  unknown       missing  enabled  missing  enabled 
```

```bash
$ nmcli device status                  # NIC の一覧と状態
```

```text
DEVICE  TYPE      STATE      CONNECTION 
eth0    ethernet  unmanaged  --         
nmv0    ethernet  unmanaged  --         
lo      loopback  unmanaged  --         
```

**`STATE` の読み方**

| STATE | 意味 |
|:--|:--|
| **`connected`** | **接続済み**。正常 |
| **`disconnected`** | **NIC はあるが、接続していない** |
| **`unmanaged`** | **NetworkManager の管理外**。**プロファイルは作れるが、有効化（`up`）できない** |
| **`unavailable`** | **ケーブルが抜けているなど、使える状態にない** |
| `connecting` | 接続処理中 |

> **`unmanaged` が出たら、設定より先にそこを解決します。**
> **`unmanaged` のままでも `connection add` でプロファイルは作れます**が、
> **`connection up` は
> `Error: Connection activation failed: ... device is strictly unmanaged` で失敗します**（実測）。
>
> ```bash
> $ nmcli device set eth0 managed yes    # 一時的に管理下に入れる
> ```
>
> **ただし設定ファイルで `unmanaged` にされている場合は、このコマンドは効きません**（実測）。
> **`/etc/NetworkManager/NetworkManager.conf` と
> `/etc/NetworkManager/conf.d/*.conf` の `unmanaged-devices` を確認**してください。

```bash
$ nmcli connection show                # 設定（プロファイル）の一覧
```

```text
NAME        UUID                                  TYPE      DEVICE 
srv-static  ebcca0f3-357c-40eb-9d63-b074ec07274b  ethernet  --     
```

| 列 | 意味 |
|:--|:--|
| **`NAME`** | **プロファイル名**。自分で付ける。以降はこの名前で操作する |
| **`UUID`** | **一意な ID**。名前を変えても変わらない |
| **`TYPE`** | 接続の種類（`ethernet` / `wifi` / `bond` / `vlan` など） |
| **`DEVICE`** | **いま結びついている NIC**。`--` なら未使用 |

```bash
$ nmcli connection show --active       # 有効になっている接続だけ
$ nmcli device show eth0               # NIC の詳細（IP、MTU、ゲートウェイ）
```

---

## 設定を作る connection add

```text
nmcli connection add type 種類 ifname NIC名 con-name 名前 [プロパティ 値] ...
```

### 静的IPで作る

```bash
$ sudo nmcli connection add type ethernet ifname nmv0 con-name srv-static \
    ipv4.method manual \
    ipv4.addresses 192.168.77.10/24 \
    ipv4.gateway 192.168.77.1 \
    ipv4.dns "8.8.8.8,1.1.1.1" \
    ipv4.dns-search "example.local" \
    connection.autoconnect yes          # 静的IPの接続を作る
```

```text
Connection 'srv-static' (ebcca0f3-357c-40eb-9d63-b074ec07274b) successfully added.
```

**この 1 コマンドの中身**

| 指定 | 意味 |
|:--|:--|
| **`type ethernet`** | **有線の接続** |
| **`ifname nmv0`** | **どの NIC に結びつけるか** |
| **`con-name srv-static`** | **プロファイルの名前**（省略すると `ethernet-nmv0` のような名前になる） |
| **`ipv4.method manual`** | **静的IP**。**これを忘れると DHCP のまま** |
| **`ipv4.addresses`** | **IP アドレスとプレフィックス**。**`/24` まで書く** |
| **`ipv4.gateway`** | **デフォルトゲートウェイ** |
| **`ipv4.dns`** | **DNS サーバ**。複数はカンマ区切り（空白やセミコロンを含むときはクォートする） |
| **`ipv4.dns-search`** | **検索ドメイン** |
| **`connection.autoconnect yes`** | **起動時に自動で有効にする** |

> **`ipv4.method manual` を書き忘れるのが最頻出の間違い**です。
> **アドレスだけ指定しても `method` は `auto` のまま**で（実測）、
> **指定した静的アドレスが意図どおりに使われません。**
> **`nmcli -g ipv4.method connection show 名前` で必ず確認**してください。

### DHCPで作る

```bash
$ sudo nmcli connection add type ethernet ifname nmv1 con-name srv-dhcp ipv4.method auto   # DHCPの接続を作る
```

```text
Connection 'srv-dhcp' (b5b39283-c702-4985-b396-0fcb9933be15) successfully added.
```

### ipv4.method に指定できる値

| 値 | 意味 |
|:--|:--|
| **`auto`** | **DHCP**（既定） |
| **`manual`** | **静的IP** |
| **`disabled`** | **IPv4 を使わない** |
| `link-local` | 169.254.x.x を自動で付ける |
| `shared` | **この機器が DHCP と DNS を提供し、NAT も行う**（簡易ルータになる） |

> **IPv6 を使わないサーバでは `ipv6.method disabled` も明示**しておくと、
> **意図しない IPv6 アドレスが付くのを防げます。**

---

## 設定を変える connection modify

**ここが `nmcli` でいちばん間違えやすいところ**です。
**プロパティ名の前に付ける記号で、動作がまったく変わります。**

| 書き方 | 動作 |
|:--|:--|
| **`ipv4.addresses 値`** | **置き換える**（既存は消える） |
| **`+ipv4.addresses 値`** | **追加する** |
| **`-ipv4.addresses 値`** | **その値を削除する** |

**実測で確かめます。**

```bash
$ sudo nmcli connection modify srv-static ipv4.addresses 192.168.77.20/24   # 置き換え
$ sudo nmcli connection modify srv-static +ipv4.addresses 192.168.77.21/24  # 追加
$ nmcli -g ipv4.addresses connection show srv-static                        # 確認
```

```text
192.168.77.20/24, 192.168.77.21/24
```

**最初に書いた `192.168.77.10/24` は消え、`+` で足した分だけ残っています。**

```bash
$ sudo nmcli connection modify srv-static +ipv4.dns 9.9.9.9   # DNS を1つ足す
$ nmcli -g ipv4.dns connection show srv-static                # 確認
```

```text
8.8.8.8,1.1.1.1,9.9.9.9
```

```bash
$ sudo nmcli connection modify srv-static -ipv4.dns 9.9.9.9   # 足した DNS を消す
$ nmcli -g ipv4.dns connection show srv-static                # 確認
```

```text
8.8.8.8,1.1.1.1
```

> **`+` を付け忘れて DNS を 1 つ指定すると、既存の DNS が全部消えます。**
> **本番で「名前が引けなくなった」事故の典型**です。
> **変更前に `nmcli -g ipv4.dns connection show 名前` で現状を控える**習慣を付けてください。

**よく使う変更**

```bash
$ sudo nmcli connection modify srv-static ipv4.gateway 192.168.77.254        # GW を変える
$ sudo nmcli connection modify srv-static connection.autoconnect no          # 自動接続を切る
$ sudo nmcli connection modify srv-static 802-3-ethernet.mtu 9000            # MTU を変える
$ sudo nmcli connection modify srv-static connection.id srv-static-new       # 名前を変える
$ sudo nmcli connection modify srv-static ipv6.method disabled               # IPv6 を無効にする
$ sudo nmcli connection modify srv-static +ipv4.routes "10.1.0.0/24 192.168.77.254"   # 経路を足す
```

> **`modify` は設定ファイルを書き換えるだけで、すぐには反映されません。**
> **反映するには有効化し直す**必要があります（次節）。

---

## 反映する up と down

```bash
$ sudo nmcli connection up srv-static        # 有効にする（ここで初めて反映される）
$ sudo nmcli connection down srv-static      # 無効にする
$ sudo nmcli connection reload               # 設定ファイルを読み直す（手でファイルを編集した場合）
$ sudo nmcli device reapply nmv0             # NIC に設定を適用し直す（有効化済みのNICのみ）
```

**`modify` したあとの正しい流れ**

```text
  ① nmcli connection modify ...       設定ファイルを書き換える
        ▼
  ② nmcli connection up 名前           反映する
        ▼
  ③ ip -br a / ip route                実際に反映されたか ip で確認する
```

> **`nmcli connection up` を SSH 経由で実行すると、自分の接続が切れることがあります。**
> **IP アドレスやゲートウェイを変える作業は、コンソール（iLO / iDRAC / クラウドのシリアルコンソール）
> から行うか、戻せる仕掛けを用意してから**実施してください。
>
> **戻せる仕掛けの例**
>
> ```bash
> $ sudo systemd-run --on-active=300 nmcli connection up 元の接続名   # 5分後に元へ戻す保険
> ```
>
> **`sleep 300 && ... &` でバックグラウンドに置く書き方は使わないでください。**
> **SSH が切れた瞬間に SIGHUP でそのジョブも消えます**（実測）。
> **保険が必要になる場面で、保険のほうが先に消える**ことになります。
> **`systemd-run` なら、セッションから切り離された状態で動きます。**
>
> **作業が成功したら、`systemctl stop` でそのタイマーを止めてください。**

**削除**

```bash
$ sudo nmcli connection delete srv-dhcp      # プロファイルごと消す
```

```text
Connection 'srv-dhcp' (b5b39283-c702-4985-b396-0fcb9933be15) successfully deleted.
```

---

## 設定の中身を全部見る

**`nmcli connection show 名前` で、設定可能なプロパティが全部出ます。**
**実測では 108 行**ありました。

```bash
$ nmcli connection show srv-static     # すべてのプロパティを出す
```

```text
connection.id:                          srv-static
connection.uuid:                        ebcca0f3-357c-40eb-9d63-b074ec07274b
connection.type:                        802-3-ethernet
connection.interface-name:              nmv0
connection.autoconnect:                 yes
connection.autoconnect-priority:        0
connection.zone:                        --
802-3-ethernet.mac-address:             --
802-3-ethernet.mtu:                     auto
ipv4.method:                            manual
ipv4.dns:                               8.8.8.8,1.1.1.1
ipv4.dns-search:                        example.local
ipv4.addresses:                         192.168.77.10/24
ipv4.gateway:                           192.168.77.1
ipv4.never-default:                     no
ipv4.may-fail:                          yes
ipv6.method:                            auto
```

**プロパティ名は「セクション.項目」の形**です。

| セクション | 何の設定か |
|:--|:--|
| **`connection.`** | **プロファイル共通**（名前、自動接続、ゾーン） |
| **`ipv4.`** / **`ipv6.`** | **IP の設定** |
| **`802-3-ethernet.`** | **有線固有**（MAC、MTU） |
| `802-11-wireless.` | 無線固有 |
| `bond.` / `vlan.` / `bridge.` | それぞれの種類固有 |

**知っておくと効くプロパティ**

| プロパティ | 意味 |
|:--|:--|
| **`ipv4.never-default`** | **`yes` にすると、この接続をデフォルトゲートウェイにしない**。NIC が複数あるときに使う |
| **`ipv4.may-fail`** | **`no` にすると、IPv4 が取れないと接続失敗扱いになる** |
| **`connection.zone`** | **firewalld のゾーン**を指定する |
| **`ipv4.route-metric`** | **経路の優先度**。小さいほど優先 |
| `connection.autoconnect-priority` | 複数の接続があるときの優先度 |

---

## 出力を加工する

**スクリプトや手順書で使うときの必須オプション**です。

| オプション | 何をするか |
|:--|:--|
| **`-t`**（`--terse`） | **区切り文字（`:`）だけの簡潔な出力**。スクリプト向き |
| **`-f`**（`--fields`） | **出す列を指定する** |
| **`-g`**（`--get-values`） | **値だけを出す**。`nmcli --help` では **`-m tabular -t -f` の短縮**と説明される。複数列を指定すると `:` 区切りになり、MAC や IPv6 の `:` は `\:` にエスケープされる |
| **`-p`**（`--pretty`） | **見出しを付けて整形する**（人が読む用） |
| **`-m`**（`--mode`） | **`tabular`（表）か `multiline`（1行1項目）か** |
| `-c`（`--colors`） | 色の有無（`yes` / `no` / `auto`） |
| `-e`（`--escape`） | 区切り文字のエスケープの有無 |
| `-o`（`--overview`） | 既定値の項目を省いて要点だけ出す |
| `-s`（`--show-secrets`） | パスワードなどを隠さず出す |
| `-a`（`--ask`） | 足りない値を対話で聞く |
| `-w 秒`（`--wait`） | 完了を待つ秒数。`up` をスクリプトで使うときに指定する |

> **`-t` の区切りは `:` です。**
> **MAC アドレスや IPv6 のように値そのものに `:` が含まれる場合は `\:` とエスケープ**されます（実測）。
> **スクリプトで切り出すときは、この点に注意してください。**

> **`TYPE` の表示は出力形式で変わります。**（実測）
> **表形式では `ethernet`、`-t` を付けると `802-3-ethernet`** になります。
> **`connection show 名前` の `connection.type` も `802-3-ethernet`** です。

**実測**

```bash
$ nmcli -t -f NAME,UUID,TYPE connection show     # 簡潔な出力
```

```text
srv-static:ebcca0f3-357c-40eb-9d63-b074ec07274b:802-3-ethernet
```

```bash
$ nmcli -f DEVICE,TYPE,STATE device status       # 列を指定する
```

```text
DEVICE  TYPE      STATE     
eth0    ethernet  unmanaged 
nmv0    ethernet  unmanaged 
nmv1    ethernet  unmanaged 
```

```bash
$ nmcli -g ipv4.addresses,ipv4.dns connection show srv-static   # 値だけ取り出す
```

```text
192.168.77.20/24, 192.168.77.21/24
8.8.8.8,1.1.1.1
```

**`-g` が構築手順書の確認コマンドに向いています。**

```bash
$ nmcli -g GENERAL.STATE device show eth0        # 状態だけを取る
$ nmcli -t -f NAME connection show --active      # 有効な接続名だけを並べる
```

> **`awk '{print $3}'` のように列番号で切り出す書き方は、
> 列幅や項目が変わると壊れます。**
> **`-g` か `-t -f` を使う**のが、手順書を長持ちさせるコツです。

---

## 設定ファイルはどこにあるか

**`nmcli` で設定すると、ファイルとして保存されます。**

| 形式 | 場所 | いつのもの |
|:--|:--|:--|
| **keyfile**（`.nmconnection`） | **`/etc/NetworkManager/system-connections/`** | **RHEL 9 の既定**（新規作成はこちら） |
| **ifcfg** | `/etc/sysconfig/network-scripts/ifcfg-*` | RHEL 7 / 8。**RHEL 9 では非推奨**だが、**既存のものは ifcfg のまま更新される** |

> **RHEL 8 から RHEL 9 へアップグレードした機器では、
> `.nmconnection` が無く ifcfg のままということがあります。**
> **「RHEL 9 だから keyfile のはず」と決めつけず、両方の場所を見てください。**
>
> **RHEL 10 では ifcfg 形式のサポートが削除**されています。

```bash
$ sudo ls -l /etc/NetworkManager/system-connections/   # 保存されたプロファイルを見る
$ sudo cat /etc/NetworkManager/system-connections/srv-static.nmconnection   # 中身を見る
```

> **keyfile のパーミッションは `600`** です。
> **パスワードなどが平文で入りうる**ため、他ユーザから読めてはいけません。
> **手でコピーするときは権限を崩さないよう注意**してください。

> **ファイルを手で編集した場合は `nmcli connection reload` が必要**です。
> ただし **手編集は推奨されません。**`nmcli connection modify` を使ってください。

> **検証環境（Ubuntu）では netplan が間に入ります。**
> **永続する設定は `/etc/netplan/90-NM-<UUID>.yaml`** で、
> `/run/NetworkManager/system-connections/netplan-NM-<UUID>.nmconnection` は
> **そこから生成された一時ファイル**（tmpfs 上）でした。
> **ディストリビューションによって保存先が変わる**ので、
> **実機では `nmcli -f NAME,FILENAME connection show` で確認**してください。

---

## 業務でよく使う通しの手順

### 新しいサーバに静的IPを設定する

```bash
$ nmcli device status                            # ① NIC 名を確認する
$ nmcli connection show                          # ② 既存のプロファイルを確認する
$ sudo nmcli connection add type ethernet ifname ens192 con-name ens192 \
    ipv4.method manual ipv4.addresses 10.0.1.50/24 \
    ipv4.gateway 10.0.1.1 ipv4.dns "10.0.1.10,10.0.1.11" \
    ipv6.method disabled connection.autoconnect yes   # ③ 作る
$ sudo nmcli connection up ens192                # ④ 反映する
$ ip -br a show ens192                           # ⑤ ip 側で確認する
$ ip route                                       # ⑥ 経路を確認する
$ cat /etc/resolv.conf                           # ⑦ DNS が反映されたか確認する
$ ping -c 3 10.0.1.1                             # ⑧ ゲートウェイへ疎通確認
```

### 既存サーバの DNS だけ変える

```bash
$ nmcli -g ipv4.dns connection show ens192       # ① 変更前を控える  ★必ずやる
$ sudo nmcli connection modify ens192 ipv4.dns "10.0.2.10,10.0.2.11"   # ② 置き換える
$ sudo nmcli connection up ens192                # ③ 反映する
$ cat /etc/resolv.conf                           # ④ 確認する
$ dig @10.0.2.10 example.com +short              # ⑤ 実際に引けるか確認する
```

### トラブル時の確認順

```bash
$ nmcli general status                 # ① NetworkManager は動いているか
$ nmcli device status                  # ② NIC は connected か（unmanaged でないか）
$ nmcli connection show --active       # ③ どのプロファイルが有効か
$ nmcli connection show ens192         # ④ そのプロファイルの中身は正しいか
$ ip -br a                             # ⑤ 実際に IP が付いているか
$ ip route                             # ⑥ 経路はあるか
$ journalctl -u NetworkManager -n 50   # ⑦ NetworkManager のログを見る
```

> **②で `unmanaged`、③で何も出ない、というのがよくある詰まり方**です。
>
> ```text
>   ② が unmanaged      → up を打っても失敗する。先に unmanaged を解消する
>   ② が disconnected   → 設定はあるが有効になっていない。nmcli connection up を打つ
>   ③ に何も出ない      → autoconnect が no になっていないか確認する
> ```

---

## nmtui という選択肢

**`nmtui` は `nmcli` と同じことを、文字ベースの画面でできるツール**です。

```bash
$ sudo nmtui                           # 対話的な画面を開く
```

| | **`nmcli`** | **`nmtui`** |
|:--|:--|:--|
| **手順書に書ける** | **書ける**（コマンドをそのまま載せられる） | **書きにくい**（画面操作になる） |
| **自動化できる** | **できる** | できない |
| **間違えにくさ** | プロパティ名を知っている必要がある | **項目が画面に出るので迷いにくい** |

> **初めて触るときは `nmtui` で設定し、
> あとから `nmcli connection show` でどのプロパティが設定されたかを見る**——
> **という学び方が効率的**です。

---

## 参考リンク

- [man 1 nmcli](https://man7.org/linux/man-pages/man1/nmcli.1.html)
- [man 5 nm-settings-nmcli](https://man7.org/linux/man-pages/man5/nm-settings-nmcli.5.html)
- [man 5 NetworkManager.conf](https://man7.org/linux/man-pages/man5/NetworkManager.conf.5.html)
- [man 1 nmtui](https://man7.org/linux/man-pages/man1/nmtui.1.html)
- [Red Hat — Configuring and managing networking (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/index)

---

[← 全体の目次にもどる](../README.md)
