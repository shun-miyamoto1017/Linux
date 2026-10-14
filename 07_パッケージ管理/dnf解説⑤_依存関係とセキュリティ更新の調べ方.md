# dnf解説⑤ 依存関係とセキュリティ更新の調べ方

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **脆弱性対応の起点。**「この CVE に対応するには何を上げればいいか」「それを上げると何が巻き込まれるか」をここで確定させる。ここが甘いと、実践③でどれだけ丁寧に持ち込んでも当たらない |

> **このフォルダの dnf ノートは「解説」と「実践」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) | **`dnf` と `yum` の関係**、**`install` / `localinstall` / `update` / `upgrade` の違い**、`distro-sync`、`reinstall`、`downgrade` |
> | 解説 | [dnf解説② 削除系と調査系コマンド](./dnf解説②_削除系と調査系コマンド.md) | **`remove` で何が一緒に消えるか**、`autoremove` / `mark` / `swap`、`list` / `info` / `provides`、`history` での切り戻し |
> | 解説 | [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) | **どのサブコマンドにも付くオプション**、`--nobest` と `--skip-broken` と `--allowerasing` の違い、終了ステータス |
> | 解説 | [dnf解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) | `.repo` の書式、`$releasever` / `$basearch`、GPG 鍵、プロキシ、キャッシュ、AppStream モジュール |
> | **解説** | **このノート（dnf解説⑤）** | `repoquery` の使い方、アドバイザリと CVE、`repoclosure`、`needs-restarting` |
> | 解説 | [dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md) | **ディストリごとの `yum` / `dnf` 対応**、dnf-4 と dnf-5 の差分、**RHEL 10 で変わったこと** |
> | 実践 | [dnf実践① オンライン環境での更新手順](./dnf実践①_オンライン環境での更新手順.md) | **リポジトリに届く**サーバの、月次パッチと脆弱性対応の通し手順 |
> | 実践 | [dnf実践② オンライン環境での切り戻しと除外設定](./dnf実践②_オンライン環境での切り戻しと除外設定.md) | `history undo` / `rollback`、`exclude`、`versionlock`、`dnf-automatic` |
> | 実践 | [dnf実践③ オフライン環境でのパッケージの集め方](./dnf実践③_オフライン環境でのパッケージの集め方.md) | **社内リポジトリに届く場合と完全分離の場合**で、必要な rpm を集める |
> | 実践 | [dnf実践④ オフライン環境での適用と切り戻し](./dnf実践④_オフライン環境での適用と切り戻し.md) | 集めた rpm を対象サーバに当てて、問題が出たら戻す |
>
> `rpm` コマンド単体の話は [RPMによるパッケージ管理](./RPMによるパッケージ管理.md) です。
> `yum` 時代の書き方との対応は [YUMとDNFによるパッケージ管理](./YUMとDNFによるパッケージ管理.md) にあります。


> **公式ドキュメントの確認日: 2026-10-13。**引用はその時点の記載です。
> URL は末尾の「参考リンク」にあります。**本番作業の前に、対象バージョンのドキュメントで裏を取ってください。**

---

## 目次

- [調べる順番](#調べる順番)
- [いま何が入っているか](#いま何が入っているか)
- [repoquery が主役](#repoquery-が主役)
  - [対象を絞るオプション](#対象を絞るオプション)
  - [出し方を変えるオプション](#出し方を変えるオプション)
- [依存を下へたどる requires](#依存を下へたどる-requires)
- [依存を上へたどる whatrequires](#依存を上へたどる-whatrequires)
- [rpm だけで調べる](#rpm-だけで調べる)
- [アドバイザリとセキュリティ更新](#アドバイザリとセキュリティ更新)
- [CVE から対象を特定する](#cve-から対象を特定する)
- [適用前に影響範囲を確定させる](#適用前に影響範囲を確定させる)
- [依存が閉じているか確かめる repoclosure](#依存が閉じているか確かめる-repoclosure)
- [更新後に再起動が要るか](#更新後に再起動が要るか)
- [調査のテンプレート](#調査のテンプレート)
- [参考リンク](#参考リンク)

---

## 調べる順番

**脆弱性対応でやることは、結局この 5 段階**です。

```text
  ① いま何が入っているか        rpm -q / dnf list --installed
        ↓
  ② その CVE に対応する版は何か  dnf updateinfo / dnf repoquery --upgrades
        ↓
  ③ それを上げると何が動くか    dnf upgrade --assumeno / repoquery --requires
        ↓
  ④ 必要な rpm をすべて集める    dnf ... --downloadonly（実践③のノート）
        ↓
  ⑤ 集めたもので依存が閉じるか   dnf repoclosure
```

**①と③を飛ばして④から始めると、必ず足りない rpm が出ます。**
「本番で `Error: Problem: cannot install ...` が出て切り戻し」はここを省いたときに起きます。

---

## いま何が入っているか

```bash
$ rpm -q sudo openssh-server          # 入っているか、版は何か（速い）
$ rpm -qa | sort > /tmp/installed.txt # 全部を一覧して控えを取る
$ dnf list --installed sudo           # dnf 側から見る（どのリポジトリ由来かも出る）
$ rpm -qi sudo                        # 詳細（インストール日時、ベンダ、署名）
```

**`rpm -q` はリポジトリを見に行かないので、切断環境でも必ず動きます。**
一方 `dnf list --available` や `dnf list --upgrades` は**リポジトリのメタデータを読む**ため、届かないと待たされます。
（`dnf list --installed` は導入済みだけを見るので、到達不能なリポジトリが有効でも待たされません。実測）
**「まず `rpm -q`」**が切断環境での鉄則です。

**作業前に必ず控えを取ります。**

```bash
$ rpm -qa --qf '%{NAME} %{EPOCH}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | sort > /tmp/before.txt   # 作業前の状態
```

**作業後に同じものを取って `diff` すれば、何が変わったかが 1 行ずつ分かります。**

```bash
$ diff /tmp/before.txt /tmp/after.txt   # 変わったパッケージだけが出る
```

---

## repoquery が主役

**`dnf repoquery` は「リポジトリに問い合わせる」コマンド**です。
`dnf list` や `dnf info` より細かく、**何も変更しない**ので本番でも安全に打てます。

### 対象を絞るオプション

| オプション | 何を出すか |
|:--|:--|
| **`--installed`** | **導入済みのものだけ** |
| **`--available`** | リポジトリにあって、まだ入っていないもの |
| **`--upgrades`** | **更新版があるものだけ** |
| **`--extras`** | **どのリポジトリにも無いもの**（手で入れた rpm の検出に使える） |
| **`--unneeded`** | `autoremove` の対象になるもの |
| **`--userinstalled`** | ユーザが明示的に入れたもの |
| **`--duplicates`** | 同じ名前で複数バージョン入っているもの |
| **`--unsatisfied`** | **依存が満たされていない導入済みパッケージ**（dnf-5 では廃止） |
| `--recent` | 最近更新されたもの |

### 出し方を変えるオプション

| オプション | 効果 |
|:--|:--|
| **`--qf '書式'`** / `--queryformat` | **書式を指定して出す**。スクリプト向き |
| **`--querytags`** | 使えるタグの一覧 |
| **`--location`** | **その rpm の URL を出す**（ダウンロードに使える） |
| **`-i`** / `--info` | 詳細 |
| **`-l`** / `--list` | 入っているファイルの一覧 |
| **`--nevra`** | `名前-エポック:版-リリース.アーキ` 形式（既定） |
| **`--nvr`** | `名前-版-リリース` 形式 |
| **`--changelogs`** | 変更履歴 |
| **`--latest-limit N`** | 新しいほうから N 件 |
| `--source` / `--srpm` | 対応するソース RPM |

検証環境での実測です。

```bash
$ dnf repoquery --qf '%{name} %{evr} %{arch} %{size} %{repoid}' libfoo   # 書式を指定して出す
```

```text
libfoo 1.0-1 noarch 6177 local
libfoo 2.0-1 noarch 6177 local
```

```bash
$ dnf repoquery --location libfoo     # ダウンロード元の URL を出す
```

```text
file:///home/claude/dnflab/repo/libfoo-1.0-1.noarch.rpm
file:///home/claude/dnflab/repo/libfoo-2.0-1.noarch.rpm
```

```bash
$ dnf repoquery --upgrades            # 更新版があるものを出す
```

```text
libfoo-0:2.0-1.noarch
```

> **`--location` は「どこから落ちてくるか」を先に確かめられます。**
> 社内リポジトリを向いているつもりが外を向いていた、という事故はこれで防げます。

---

## 依存を下へたどる requires

**「このパッケージを入れるには何が要るか」**を調べます。**オフラインで rpm を集めるときの基礎**です。

| 書き方 | 何が出るか |
|:--|:--|
| **`--requires`** | **直接の依存（能力名のまま）** |
| **`--requires --resolve`** | **その依存を満たす「パッケージ名」** |
| **`--requires --resolve --recursive`** | **芋づる式に全部**（依存の依存も） |
| **`--requires --resolve --tree`** | **木構造で表示** |
| `--provides` | そのパッケージが提供している能力 |
| `--conflicts` | 衝突する相手 |
| `--recommends` / `--suggests` | 弱い依存 |
| `--requires-pre` | スクリプト実行に必要な依存 |
| `--deplist` | 依存と、それを提供するパッケージの対応 |

**検証環境で `appx`（`libfoo >= 1.0` と `libbar` に依存。`libbar` は `libbaz` に依存）を調べた実測**です。

```bash
$ dnf repoquery --requires appx       # 直接の依存を「能力名」で出す
```

```text
libbar
libfoo >= 1.0
```

```bash
$ dnf repoquery --requires --resolve appx   # 依存を満たすパッケージ名に変換する
```

```text
libbar-0:1.0-1.noarch
libfoo-0:2.0-1.noarch
```

```bash
$ dnf repoquery --requires --resolve --recursive appx   # 依存の依存まで全部たどる
```

```text
libbar-0:1.0-1.noarch
libbaz-0:1.0-1.noarch
libfoo-0:2.0-1.noarch
```

```bash
$ dnf repoquery --requires --resolve --tree appx   # 木構造で見る
```

```text
appx-0:1.0-1.noarch
 \_ libbar-0:1.0-1.noarch [1: libbaz]
 |   \_ libbaz-0:1.0-1.noarch [0: ]
 \_ libfoo-0:2.0-1.noarch [0: ]
```

**3 つの違いがそのまま「集めるべき rpm の数」の違い**になります。

| 結果 | 出たもの | 集め方として |
|:--|:--|:--|
| **`--requires` だけ** | `libbar` / `libfoo >= 1.0` | **能力名なので rpm が特定できない**。これだけでは集められない |
| **`--resolve` あり** | 2 個 | **1 階層分しか出ない**。`libbaz` が抜ける |
| **`--recursive` あり** | **3 個** | **これが必要なものの全体像** |

> **`--recursive` を付け忘れて「`libbaz` が足りません」で止まる**のが、オフライン作業でいちばん多い失敗です。
> ただし `repoquery` の結果は「リポジトリ上の依存の全体像」であって、
> **対象サーバに何が入っているかは考慮していません**。実際に何を持っていくかは実践③で決めます。

---

## 依存を上へたどる whatrequires

**「このパッケージを上げたら、何が影響を受けるか」**を調べます。**変更の影響範囲を出すときに使います。**

| 書き方 | 何が出るか |
|:--|:--|
| **`--whatrequires 名前`** | **そのパッケージを必要としているもの** |
| **`--whatrequires 名前 --recursive`** | **さらにその上まで** |
| **`--whatprovides ファイルや能力`** | **その能力を提供しているのは誰か** |
| `--whatdepends` | requires に加えて recommends / suggests なども含む |
| `--whatconflicts` | 衝突する相手 |
| `--whatobsoletes` | 置き換える相手 |

検証環境での実測です。

```bash
$ dnf repoquery --whatrequires libbaz   # libbaz を必要としているパッケージを出す
```

```text
libbar-0:1.0-1.noarch
```

**実務での使い方**

```bash
$ dnf repoquery --installed --whatrequires openssl-libs            # 導入済みのうち openssl-libs に依存するもの
$ dnf repoquery --installed --whatrequires openssl-libs --recursive   # さらに上までたどる
$ dnf repoquery --whatprovides 'libcrypto.so.3()(64bit)'           # この共有ライブラリの出どころ
```

> **`--whatrequires` に `--installed` を付けるかどうかで意味がまったく変わります。**
>
> | 付ける | 意味 |
> |:--|:--|
> | **付けない** | **リポジトリ上で**そのパッケージを必要としているもの（＝世の中の全体像） |
> | **`--installed` を付ける** | **このサーバに入っているもののうち**、必要としているもの（＝**実際の影響範囲**） |
>
> **影響範囲の報告には `--installed` 付き**を使います。

---

## rpm だけで調べる

**リポジトリに届かない環境**でも、`rpm` なら手元の情報だけで調べられます。

| コマンド | 何を調べるか |
|:--|:--|
| **`rpm -qR パッケージ名`** | **導入済みパッケージの依存** |
| **`rpm -qpR ファイル.rpm`** | **rpm ファイルの依存**（入れる前に読める） |
| **`rpm -q --whatprovides 能力`** | その能力を提供している導入済みパッケージ |
| **`rpm -q --whatrequires 能力`** | その能力を必要としている導入済みパッケージ |
| **`rpm -qf ファイルパス`** | **そのファイルの持ち主** |
| **`rpm -V パッケージ名`** | **改変されていないか検証する** |
| **`rpm -Uvh --test ファイル.rpm`** | **入れずに、依存が足りるかだけ試す** |

検証環境での実測です。

```bash
$ rpm -qpR out3/appx-1.0-1.noarch.rpm   # rpm ファイルの依存を読む
```

```text
libbar
libfoo >= 1.0
rpmlib(CompressedFileNames) <= 3.0.4-1
rpmlib(FileDigests) <= 4.6.0-1
rpmlib(PayloadFilesHavePrefix) <= 4.0-1
```

**`rpmlib(...)` で始まる行は rpm 自身の機能要件**です。パッケージとして集める対象ではありません。無視して構いません。

```bash
$ sudo rpm -Uvh --test /var/tmp/patch/appx-1.0-1.noarch.rpm   # 依存が足りるかだけ試す
```

依存が足りないときの実測です。

```text
error: Failed dependencies:
	libbar is needed by appx-1.0-1.noarch
	libfoo >= 1.0 is needed by appx-1.0-1.noarch
```

> **`rpm -Uvh --test` は、持ち込んだ rpm を本番で当てる直前の最終確認に使えます。**
> 何も変更せず、足りない依存だけを教えてくれます。

---

## アドバイザリとセキュリティ更新

**アドバイザリ（advisory）は「この更新は何のためか」を表す情報**です。
`RHSA-2026:0001` のような ID が付き、**セキュリティ / バグ修正 / 機能追加**に分類されます。

| 種別 | ID の形 | 意味 |
|:--|:--|:--|
| **RHSA** | `RHSA-年:番号` | **Security Advisory（セキュリティ）** |
| **RHBA** | `RHBA-年:番号` | Bug Fix Advisory（バグ修正） |
| **RHEA** | `RHEA-年:番号` | Enhancement Advisory（機能追加） |

```bash
$ dnf updateinfo summary               # 何件あるかの要約
$ dnf updateinfo list                  # 一覧
$ dnf updateinfo list --security       # セキュリティ関連だけ
$ dnf updateinfo info RHSA-2026:0001   # 中身を読む
```

検証環境で、セキュリティアドバイザリを 1 件持たせたリポジトリでの実測です。

```text
Updates Information Summary: available
    1 Security notice(s)
        1 Important Security notice(s)
```

```bash
$ dnf updateinfo list --security      # セキュリティ関連のアドバイザリを一覧する
```

```text
RHSA-2026:0001 Important/Sec. libfoo-2.0-1.noarch
```

**左から アドバイザリ ID / 重大度と種別 / 対象パッケージ** の 3 列です。

```bash
$ dnf updateinfo info RHSA-2026:0001  # アドバイザリの中身を読む
```

```text
===============================================================================
  Important: libfoo security update
===============================================================================
  Update ID: RHSA-2026:0001
       Type: security
    Updated: 2026-09-01 00:00:00
       CVEs: CVE-2026-11111
Description: libfoo に任意コード実行の脆弱性があります。
   Severity: Important
```

**`CVEs:` の行が、CVE 番号とアドバイザリの対応**です。ここが報告書に必要になります。

> **`updateinfo` が空のときは、リポジトリに `updateinfo.xml` が無い可能性**があります。
> 社内リポジトリを `reposync` で作るときに `--download-metadata` を付け忘れると、
> **アドバイザリ情報だけが欠けて `--security` が効かなくなります**（実践①で詳述）。
>
> **dnf-5 では `dnf advisory list --security` に変わりました**（`updateinfo` は別名として残っています）。

---

## CVE から対象を特定する

**「CVE-2026-XXXXX に対応してください」と言われたときの手順**です。

```bash
$ dnf updateinfo list --cve CVE-2026-11111    # その CVE を直すアドバイザリと対象を出す
$ dnf updateinfo info --cve CVE-2026-11111    # 詳細を読む
$ dnf upgrade --cve CVE-2026-11111 --assumeno # 何が上がるかだけ見る（適用しない）
```

**絞り込みの指定は 4 通りあり、`upgrade` / `upgrade-minimal` / `check-update` / `updateinfo` に付けられます。**
**`dnf download` には効きません**（オプションは受け付けるが無視される。実測）。

| 指定 | 書き方 | 使いどころ |
|:--|:--|:--|
| **CVE 番号** | **`--cve CVE-2026-11111`** | **脆弱性管理ツールから CVE で指示が来たとき** |
| **アドバイザリ ID** | **`--advisory RHSA-2026:0001`** | **Red Hat のアドバイザリで指示が来たとき** |
| **種別** | **`--security`** | **セキュリティ全部** |
| **重大度** | **`--sec-severity Critical --sec-severity Important`** | **Critical と Important だけ当てたいとき。**`--sec-severity Important` だけだと **Critical が入りません**（実測）。複数回書くと OR になります。**dnf-5 では `--advisory-severities` に改名された**（公式） |

検証環境で 3 通りとも試した実測です。**いずれも同じ 1 個の rpm が選ばれました。**

```bash
$ sudo dnf upgrade --security --downloadonly --destdir=/var/tmp/sec      # セキュリティ指定
$ sudo dnf upgrade --cve CVE-2026-11111 --downloadonly --destdir=/var/tmp/cve   # CVE 指定
$ sudo dnf upgrade --advisory RHSA-2026:0001 --downloadonly --destdir=/var/tmp/adv   # ID 指定
```

```text
libfoo-2.0-1.noarch.rpm
```

> **`--security` と `upgrade-minimal` の組み合わせ**が、本番でいちばん変更量が少ない当て方です。
>
> ```bash
> $ sudo dnf upgrade-minimal --security --assumeno   # 問題を直す最小限だけ。まず下見する
> ```
>
> `upgrade` が「最新版まで上げる」のに対し、`upgrade-minimal` は
> **そのアドバイザリを満たす最小のバージョンで止まります**。

---

## 適用前に影響範囲を確定させる

**`--assumeno` を使うと、実行計画だけを出して最後に No と答えてくれます。**
本番で「何が起きるか」を安全に見られる唯一の方法です。

```bash
$ sudo dnf upgrade --security --assumeno    # 何が上がるか、何が消えるかを見るだけ
$ sudo dnf install httpd --assumeno         # 入れたら何が付いてくるかを見るだけ
$ sudo dnf remove httpd --assumeno          # 消したら何が巻き込まれるかを見るだけ
```

**必ず見る 3 か所**

| 見出し | 見る理由 |
|:--|:--|
| **`Installing dependencies:`** | **想定外のパッケージが増えていないか** |
| **`Upgrading:`** | **指示された以外のものまで上がっていないか** |
| **`Removing:`** | **何かが消える計画になっていないか。ここが空でないなら必ず中身を読む** |

**更新対象の一覧をファイルに残す**

```bash
$ sudo dnf upgrade --security --assumeno > /tmp/plan.txt 2>&1   # 計画を控えに取る
$ dnf repoquery --upgrades --qf '%{name}-%{evr}.%{arch}\n' | sort > /tmp/upgrades.txt   # 機械可読な一覧
```

---

## 依存が閉じているか確かめる repoclosure

**集めた rpm だけで依存が足りているか**を機械的に判定します。
オフラインで持ち込む前の最終チェックです。

```bash
$ dnf --refresh repoclosure --repofrompath=chk,file:///var/tmp/patch --repo=chk   # 足りない依存が無いか調べる
```

**足りないものがあるときの実測**です（わざと `libbaz` を抜いた状態）。

```text
package: libbar-1.0-1.noarch from chk
  unresolved deps (1):
    libbaz
Error: Repoclosure ended with unresolved dependencies (1) across 1 packages.
```

**足りているときは何も出ません。**

**終了ステータスで判定できます。**

| 終了ステータス | 意味 |
|:--|:--|
| **0** | **依存が閉じている** |
| **1** | **足りない依存がある** |

```bash
$ dnf --refresh repoclosure --repofrompath=chk,file:///var/tmp/patch --repo=chk ; echo "exit=$?"   # 判定を見る
$ # 0 なら依存が閉じている。1 なら足りない依存がある
```

> **`repoclosure` が見るのは「指定したリポジトリの中だけ」です。**
> **導入済みパッケージは依存を満たすものとして数えられません**（dnf-4.14.0 で実測）。
> つまり **`--alldeps` で依存を全部集めたディレクトリ**なら `exit=0` になりますが、
> **方法1 や方法3 で作った「対象サーバに足りない分だけ」の最小セットは、単独では閉じません。**
>
> | 集め方 | `repoclosure` の判定 |
> |:--|:--|
> | **方法2（`--alldeps`）** | **閉じるべき。`exit=1` なら集め漏れ** |
> | **方法1 / 方法3（最小セット）** | **閉じなくて正常**。対象サーバの導入済みが前提だから |
>
> **最小セットの確認は、対象サーバ上での `rpm -Uvh --test` と `dnf ... --assumeno` で行います。**
>
> また **`--refresh` を付けないと、古いキャッシュのまま判定して誤った結果が出ます。**
> 実際にこの検証でも、キャッシュが残ったまま実行して「閉じている」と誤判定しました。**必ず `--refresh` を付けてください。**

---

## 更新後に再起動が要るか

**更新したが、古いバイナリを掴んだままのプロセスが残っている**という状態を検出します。

```bash
$ sudo dnf needs-restarting            # 再起動が必要なプロセスを一覧する
$ sudo dnf needs-restarting -s         # 影響を受ける systemd サービスだけ出す
$ sudo dnf needs-restarting -r         # OS 再起動が必要かだけ判定する
```

**`-r` は終了ステータスで答えます。**

| 終了ステータス | 意味 |
|:--|:--|
| **0** | **再起動は不要** |
| **1** | **再起動が必要** |

```bash
$ sudo dnf needs-restarting -r ; echo "exit=$?"   # 判定を終了ステータスで受け取る
```

**スクリプトから使うとき**

```bash
$ sudo dnf needs-restarting -r || echo "再起動が必要です"   # 1 が返ったらメッセージを出す
```

> **dnf-4 の `-r` の終了ステータスは公式ドキュメントに明記されています。**
> `dnf-plugins-core` の needs-restarting の項に
> **「Only report whether a reboot is required (exit code 1) or not (exit code 0).」**とあります。
>
> **dnf-5 では `-r` / `--reboothint` は削除されました**（`dnf5` の「Changes between DNF and DNF5」に記載）。
> 判定が既定の動作になったためです。**`-u` / `--useronly` も削除**されています。
> さらに **dnf-5 の `needs-restarting` は開いているファイルを調べません。**
> **`reboot_suggested` が付いたアドバイザリのパッケージを入れたかどうか**で判断します。
> **`-s` / `--services` も開いているファイルを見ず**、サービス起動後にそのパッケージか依存が更新されたかで判断します。
> **判定の根拠が変わるので、dnf-5 の環境では結果が dnf-4 と一致しないことがあります。**

**`needs-restarting -s` で出たサービスだけ再起動する**のが、影響を最小にする当て方です。

```bash
$ sudo dnf needs-restarting -s         # 再起動が要るサービス名を出す
$ sudo systemctl restart sshd          # 出たサービスを個別に再起動する
```

> **`sshd` を再起動しても、既存の SSH 接続は切れません**（新しい接続だけが新しいプロセスになります）。
> ただし**設定に誤りがあると次から入れなくなる**ので、**別セッションを開いたまま**実行してください。

---

## 調査のテンプレート

**「CVE-2026-XXXXX に対応せよ」と来たとき、この順番でコマンドを打つ**だけで報告書が書けます。

```bash
$ rpm -qa --qf '%{NAME} %{EPOCH}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | sort > /tmp/before.txt   # ① 現状を控える
$ dnf --refresh updateinfo list --cve CVE-2026-XXXXX       # ② 対応するアドバイザリと対象を特定する
$ dnf updateinfo info --cve CVE-2026-XXXXX                 # ③ 内容と重大度を読む
$ sudo dnf upgrade --cve CVE-2026-XXXXX --assumeno         # ④ 何が上がるかを確定させる
$ dnf repoquery --installed --whatrequires <上がるパッケージ>   # ⑤ 影響を受ける導入済みパッケージを洗う
$ dnf versionlock list                                     # ⑥ 固定していて上がらないものが無いか確認する
```

**報告書に載せる項目**

| 項目 | どのコマンドから取るか |
|:--|:--|
| 対象 CVE と アドバイザリ ID | `dnf updateinfo info --cve` |
| 重大度 | 同上（`Severity:`） |
| 更新前のバージョン | `rpm -q パッケージ名` |
| 更新後のバージョン | `dnf repoquery --upgrades` |
| 影響を受けるパッケージ | `dnf upgrade --cve ... --assumeno` の `Upgrading:` |
| 再起動の要否 | `dnf needs-restarting -r` |
| 実施記録 | `dnf history info <ID>` |

> **`--refresh` を付けるのを忘れないでください。**
> 社内リポジトリを更新した直後にキャッシュが古いままだと、
> **「対象のアドバイザリが見つかりません」と出て 30 分溶けます。**
>
> **出力が空のときは「もう適用済み」の可能性もあります。**
> `updateinfo list` は既定では**未適用のものしか出しません**。
> **`--all` を付けると、適用済みのものが行頭 `i` 付きで出ます**（実測）。
>
> ```text
>   RHSA-2026:0002 Critical/Sec.  libbar-1.1-1.noarch
> i RHSA-2026:0001 Important/Sec. libfoo-2.0-1.noarch
> ```
>
> **この `i` が「適用済み」の証跡**になるので、報告書にも使えます。

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — Is it possible to limit yum so that it lists or installs only security updates?](https://access.redhat.com/solutions/10021)
- [DNF5 — advisory コマンド](https://dnf5.readthedocs.io/en/latest/commands/advisory.8.html)
- [dnf-plugins-core — needs-restarting](https://dnf-plugins-core.readthedocs.io/en/latest/needs_restarting.html)（**`-r` の終了ステータス**の出典）
- [DNF5 ドキュメント — Changes between DNF and DNF5](https://dnf5.readthedocs.io/en/latest/changes_from_dnf4.7.html)（**dnf-5 の `needs-restarting` と `--advisory-severities`**の出典）
- [dnf-plugins-core — repoclosure](https://dnf-plugins-core.readthedocs.io/en/latest/repoclosure.html)
- [man 8 dnf](https://man7.org/linux/man-pages/man8/dnf.8.html)

---

[← 全体の目次にもどる](../README.md)
