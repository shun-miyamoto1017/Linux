# 無線LANの設定 iwconfigとiw

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★☆☆ |
| **Ping-t の範囲** | Linux1 / ネットワークの基礎(主題1.07) — 基本的なネットワーク構成 |
| **業務での使いどころ** | **GUI の無いサーバやラズパイを無線につなぐ。**現場で「とりあえず Wi-Fi に繋いで作業したい」ときに効く。信号強度の確認は設置場所の判断材料にもなる |

> **このノートは無線 LAN 専用のコマンド**です。
> **IP アドレスの設定（有線・無線を問わない）**は
> [IPアドレスの設定 ifconfigとip](./IPアドレスの設定_ifconfigとip.md)、
> **ネットワーク設定ファイル**は [ネットワーク設定ファイル](./ネットワーク設定ファイル.md) にあります。

---

## 目次

- [ifconfig と iwconfig の違い](#ifconfig-と-iwconfig-の違い)
- [iwconfig](#iwconfig)
- [iwlist](#iwlist)
- [iw](#iw)
- [iwconfig と iw の書式を混ぜない](#iwconfig-と-iw-の書式を混ぜない)
- [リンク品質と信号強度](#リンク品質と信号強度)
- [接続までの流れ](#接続までの流れ)
- [参考リンク](#参考リンク)

---

## ifconfig と iwconfig の違い

| | **`ifconfig`** | **`iwconfig`** |
|:--|:--|:--|
| **守備範囲** | **有線・無線を問わないインタフェース一般** | **無線 LAN 関連だけ** |
| **できること** | **IP アドレス、ネットマスク、有効・無効** | **ESSID、WEP キー、通信強度の確認、モード、チャネル** |
| **できないこと** | 無線固有の設定 | **IP アドレスの設定、インタフェースの有効・無効** |

**「無線 LAN に関連した状態表示・設定を行うコマンドを 2 つ」への答え**

| 選択肢 | 正誤 | 理由 |
|:--|:-:|:--|
| **`iwconfig`** | **○** | **無線 LAN インタフェースの操作を行う** |
| **`iw`** | **○** | **`iwconfig` を置き換える新しいコマンド** |
| `ifconfig` | ✕ | **有線・無線を問わないインタフェース一般の操作**。無線固有の機能は持たない |
| `arp` | ✕ | **ARP キャッシュの操作** |
| `route` | ✕ | **ルーティングテーブルの操作** |

**逆向きの誤答にも注意**

**「IP アドレスを設定するコマンド」に `iwconfig` は入りません。**
**無線・有線を問わず利用する機能は `ifconfig` が持っている**からです。

```text
  ifconfig   IP アドレス・ネットマスク・up/down     … 無線でも有線でも
  iwconfig   ESSID・WEP キー・信号強度・モード       … 無線だけ
        ▲ この線引きが設問の軸になる
```

---

## iwconfig

```text
iwconfig インタフェース名 操作内容
```

**「操作内容」に指定できるもの**

| 指定 | 意味 |
|:--|:--|
| **（指定なし）** | **現在の状態を表示する** |
| **`essid`** | **続けて ESSID を指定する** |
| **`key`** | **続けて WEP キーを指定する** |

> `iwconfig --help` を見ると、実際には
> **`mode` / `freq` / `channel` / `rate` / `enc` / `power` / `txpower` / `ap`** なども取れます
> （サンドボックスの Wireless-Tools version 30 で確認）。
> **試験で問われるのは `essid` と `key` の 2 つ**です。

**ESSID を指定して接続する**

**無線 LAN では ESSID が同じもの同士が通信できます。**

```bash
$ sudo iwconfig wlan0 essid "pubcafe"   # 識別名 pubcafe のアクセスポイントに繋ぐ
```

> **`pubcafe` を囲っているダブルクォートは、囲まれた部分全体が
> ひとつの引数と解釈されることを確実にするためのもの（シェルの機能）**で、
> **この場合は必須ではありません。**
> 名前に空白が入るときだけ必要になります。

**WEP キーを指定する**

**`key` という指定の直後に WEP キー（秘密鍵）となる値を指定します。**
**16 進数で直接書くこともできますが、通常は文字列によるパスワードを利用することが多く、
その場合はパスワードの直前に `s:` をつける必要があります。**

```bash
$ sudo iwconfig wlan0 key s:j8EfDx24    # 文字列形式で WEP キーを指定する
$ sudo iwconfig wlan0 key 1234-5678-90  # 16進数形式ならそのまま書ける
```

```text
  key s:j8EfDx24     文字列（ASCII）  … s: が要る
  key 1234-5678-90   16進数           … s: は不要
```

**まとめて書ける**

```bash
$ sudo iwconfig wlan0 essid "pubcafe" key s:j8EfDx24   # 複数の設定を続けて書ける
```

**このように複数の設定をまとめて書ける機能は `iwconfig` にも `ifconfig` にもあります。**

**書式の誤り**

| 書き方 | 正誤 | 理由 |
|:--|:-:|:--|
| **`iwconfig wlan0 essid "pubcafe"`** | **○** | **`essid` に続けて識別名を書く** |
| `iwconfig wlan0 "pubcafe"` | ✕ | **`essid` という指定をせず直接識別名を書くことはできない** |
| `iwconfig wlan0 "pubcafe" key "s:pubcafe"` | ✕ | **識別子の前に `essid` が無い**（`key` の書き方自体は正しい） |
| `iwconfig wlan0 id=pubcafe` | ✕ | **`id=値` のような形式では書けない** |
| `iwconfig wlan0 wep s:pubcafe` | ✕ | **`wep` / `pw` というキーワードは無い**。正しくは `key` |

---

## iwlist

```text
iwlist インタフェース名 scan[ning]
```

**インタフェースを指定して `scanning`（`scan` と省略可）とすると、
使用可能なアクセスポイントをスキャンします。**

```bash
$ sudo iwlist wlan0 scanning           # 周囲のアクセスポイントを探す
$ sudo iwlist wlan0 scan               # scan と省略しても同じ
```

**出力例**

```text
wlan0     Scan completed :
          Cell 01 - Address: 11:22:33:44:55:66
                    Channel:1
                    Frequency:2.412 GHz (Channel 1)
                    Quality=64/70  Signal level=-46 dBm
                    Encryption key:on
                    ESSID:"Montana"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 6 Mb/s; 9 Mb/s
```

| 欄 | 意味 |
|:--|:--|
| **`Cell 01`** | **見つかったアクセスポイントの通し番号** |
| **`Address`** | **アクセスポイントの MAC アドレス（BSSID）** |
| **`Channel` / `Frequency`** | **使用しているチャネルと周波数** |
| **`Quality` / `Signal level`** | **リンク品質と信号強度** |
| **`Encryption key`** | **`on` なら暗号化されている** |
| **`ESSID`** | **アクセスポイントの識別名** |

**語順を入れ替えた誤答**

| 書き方 | 正誤 |
|:--|:-:|
| **`iwlist wlan0 scan`** | **○** |
| **`iwlist wlan0 scanning`** | **○** |
| `iwlist scanning wlan0` | ✕（インタフェースが先） |
| `iwlist show wlan0` | ✕（`show` という指定は無い） |
| `iwlist wlan0 show` | ✕（同上） |

> **`iwlist` は `scanning` 以外も取れます。**
> `iwlist --help` では **`frequency` / `channel` / `bitrate` / `rate` / `encryption` /
> `keys` / `power` / `txpower` / `ap` / `accesspoints`** などが並びます（実機で確認）。

---

## iw

```text
iw オブジェクト コマンド
```

**`iwconfig` を置き換えるコマンド**です。**書式がまったく違います。**

**主なオブジェクト**

| オブジェクト | 何を引数に取るか | 主要なコマンド |
|:--|:--|:--|
| **`dev` インタフェース名** | **インタフェース名**（`wlan0` など）。インタフェースに関する情報の表示や設定を行う | **`link`**：無線の接続状況を表示<br>**`scan`**：接続可能な無線 AP をスキャン<br>**`connect` / `disconnect`**：ESSID を指定して接続・切断<br>**`station dump`**：統計情報を確認 |
| **`phy` デバイス名<br>`phy#`デバイス番号** | **デバイス名**（`phy0` など）。デバイスに関する情報の表示や設定を行う | **`interface add` / `del`**：インタフェースを追加・削除<br>**`info`**：デバイスの使用可能な情報等を表示 |

**`dev` と `phy` の違いがこのコマンドの肝**です。

```text
  phy0    物理的な無線デバイス（チップ）      … 何ができるハードか
    └ wlan0     そのデバイス上のインタフェース  … いま何に繋がっているか
    └ monwlan0  モニタ用に追加したインタフェース
```

**1 つの物理デバイスの上に、複数のインタフェースを作れます。**

**代表的な使い方**

```bash
$ iw dev                               # 全インタフェースの情報を表示する
$ iw dev wlan0 link                    # 接続状態（SSID、周波数、送受信量）を表示する
$ sudo iw dev wlan0 scan               # 接続可能な BSS をスキャンする
$ sudo iw dev wlan0 connect pubcafe    # ESSID を指定して接続する
$ sudo iw dev wlan0 disconnect         # 切断する
$ iw dev wlan0 station dump            # 接続端末の送受信状況をダンプする
$ iw phy phy0 info                     # デバイスが使える暗号化・周波数などを表示する
$ sudo iw phy phy0 interface add monwlan0 type monitor   # モニタ用IFを追加する
$ sudo iw dev monwlan0 del             # 追加したインタフェースを削除する
```

**「使用可能な暗号化や周波数を確認したい」への答え**

| 選択肢 | 正誤 | 理由 |
|:--|:-:|:--|
| **`iw phy phy0 info`** | **○** | **デバイスの情報を表示する**。`Supported Ciphers` や `Frequencies` が出る |
| `iw dev wlan0 scan` | ✕ | **使用可能な無線接続先をスキャンする**。デバイス自身の対応機能は出ない |
| `iw dev wlan0 station dump` | ✕ | **端末の通信情報を表示する**。暗号化や周波数の情報は無い |
| `iw phy phy0 station dump` | ✕ | **そのようなコマンドは無い**（`station` は `dev` のコマンド） |

**「リンク状態を確認したい」への答え**

| 選択肢 | 正誤 | 理由 |
|:--|:-:|:--|
| **`iw dev wlan0 link`** | **○** | **`dev` の `link` が接続状況を表示する** |
| `iw phy phy0 link` | ✕ | **`link` は `dev` のコマンド** |
| `iw phy wlan0 link` | ✕ | **`phy` にはデバイス名を渡す**（`wlan0` はインタフェース名） |
| `iw dev wlan0 dump` | ✕ | **`dump` 単体のコマンドは無い**（`station dump`） |
| `iw dev wlan0 scan` | ✕ | **スキャンであって接続状況ではない** |

> **`iw help` の実出力**でも
> **`dev <devname> link` / `dev <devname> scan` / `dev <devname> connect` /
> `dev <devname> disconnect` / `dev <devname> station dump` /
> `phy <phyname> info` / `phy <phyname> interface add`** が確認できます
> （サンドボックスの iw version 6.7）。

---

## iwconfig と iw の書式を混ぜない

**最もよく出る誤答が「書式の混同」**です。

```text
  iwconfig wlan0 essid "pubcafe"     ○  iwconfig の書式
  iw dev wlan0 connect pubcafe       ○  iw の書式
  iw wlan0 essid "pubcafe"           ×  iwconfig の書式を iw で書いている
```

**`iw` には `essid` というキーワードがありません。**
**インタフェースを指定するには `dev` が要り、接続するコマンドは `connect`** です。

**対応表**

| やりたいこと | `iwconfig` | `iw` |
|:--|:--|:--|
| **接続する** | **`iwconfig wlan0 essid "名前"`** | **`iw dev wlan0 connect 名前`** |
| **状態を見る** | **`iwconfig wlan0`** | **`iw dev wlan0 link`** |
| **スキャンする** | **`iwlist wlan0 scan`** | **`iw dev wlan0 scan`** |

---

## リンク品質と信号強度

**無線 LAN のリンク品質や信号強度は `iwconfig` / `iwlist` で確認できます。**

```text
$ iwconfig wlan0
wlan0     IEEE 802.11bg  ESSID:"Montana"
          Mode:Managed  Frequency:2.412 GHz  Access Point: 11:22:33:44:55:66
          Bit Rate=54 Mb/s   Tx-Power=20 dBm
          Encryption key:off
          Link Quality=63/70  Signal level=-47 dBm     ← ここ
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
```

| 欄 | 意味 |
|:--|:--|
| **`ESSID`** | **接続しているアクセスポイントの識別名** |
| **`Mode`** | **`Managed` はアクセスポイント経由、`Ad-Hoc` は端末同士** |
| **`Access Point`** | **接続先の MAC アドレス（BSSID）** |
| **`Bit Rate`** | **現在の通信速度** |
| **`Link Quality`** | **リンク品質**（分母は環境によって変わる） |
| **`Signal level`** | **信号強度**（dBm。**0 に近いほど強い**） |
| **`Encryption key`** | **`off` なら暗号化されていない** |

**`iwlist` のスキャン結果でも同じ情報が見られます。**

```text
$ iwlist wlan0 scanning
          Cell 01 - Address: 11:22:33:44:55:66
                    Quality=64/70  Signal level=-46 dBm     ← ここ
```

**リンク品質や信号強度が低くなると転送速度は下がります。**

| 選択肢 | 正誤 |
|:--|:-:|
| **`iwconfig`** | **○** |
| **`iwlist`** | **○** |
| `ifconfig` | ✕（無線に関連した機能を持たない） |
| `iwsurvey` | ✕（存在しないコマンド） |

> **`Signal level` は負の値**です。**`-46 dBm` のほうが `-80 dBm` より強い**という
> 直感に反する読み方をします。**0 に近いほど良い**と覚えます。

---

## 接続までの流れ

```text
  ① iwlist wlan0 scan          周囲のアクセスポイントを探す
        ▼
  ② iwconfig wlan0 essid 名前  ESSID を指定して接続する
        ▼
  ③ iwconfig wlan0 key s:鍵    暗号化キーを設定する（WEP の場合）
        ▼
  ④ ifconfig wlan0 up          インタフェースを有効にする
        ▼
  ⑤ dhclient wlan0             DHCP で IP アドレスを取る
        ▼
  ⑥ ping -c 3 8.8.8.8          疎通を確かめる
```

**④ 以降は無線固有の話ではありません。**
**IP アドレスの割り当ては [IPアドレスの設定 ifconfigとip](./IPアドレスの設定_ifconfigとip.md) の担当**です。

> **WPA2 / WPA3 は `iwconfig` では設定できません。**
> **`wpa_supplicant`（`wpa_supplicant.conf`）を使う**のが現在の実務です。
> **`iwconfig` の `key` で扱えるのは WEP まで**——ここは試験の範囲と実務がずれる部分です。

---

## 参考リンク

- [man 8 iwconfig](https://man7.org/linux/man-pages/man8/iwconfig.8.html)
- [man 8 iwlist](https://man7.org/linux/man-pages/man8/iwlist.8.html)
- [man 8 iw](https://man7.org/linux/man-pages/man8/iw.8.html)
- [man 5 wpa_supplicant.conf](https://man7.org/linux/man-pages/man5/wpa_supplicant.conf.5.html)
