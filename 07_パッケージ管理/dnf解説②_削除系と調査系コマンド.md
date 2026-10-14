# dnf解説② 削除系と調査系コマンド

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **`dnf remove` は指定した 1 つだけを消すコマンドではない。**これを知らずに `-y` を付けて本番で打つのが、パッケージ管理でいちばん多い事故。調査系（`list` / `info` / `provides`）は障害対応で毎回使う |

> **このフォルダの dnf ノートは「解説」と「実践」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) | **`dnf` と `yum` の関係**、**`install` / `localinstall` / `update` / `upgrade` の違い**、`distro-sync`、`reinstall`、`downgrade` |
> | **解説** | **このノート（dnf解説②）** | **`remove` で何が一緒に消えるか**、`autoremove` / `mark` / `swap`、`list` / `info` / `provides`、`history` での切り戻し |
> | 解説 | [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) | **どのサブコマンドにも付くオプション**、`--nobest` と `--skip-broken` と `--allowerasing` の違い、終了ステータス |
> | 解説 | [dnf解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) | `.repo` の書式、`$releasever` / `$basearch`、GPG 鍵、プロキシ、キャッシュ、AppStream モジュール |
> | 解説 | [dnf解説⑤ 依存関係とセキュリティ更新の調べ方](./dnf解説⑤_依存関係とセキュリティ更新の調べ方.md) | `repoquery` の使い方、アドバイザリと CVE、`repoclosure`、`needs-restarting` |
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

- [消す remove と autoremove と mark](#消す-remove-と-autoremove-と-mark)
  - [remove は指定した1つだけを消すコマンドではない](#remove-は指定した1つだけを消すコマンドではない)
  - [3つの見出しの意味は「上か下か」ではない](#3つの見出しの意味は上か下かではない)
  - [消える範囲を変える 2 つのスイッチ](#消える範囲を変える-2-つのスイッチ)
  - [autoremove と mark の関係](#autoremove-と-mark-の関係)
- [入れ替える swap](#入れ替える-swap)
- [調べる list と info と provides と search](#調べる-list-と-info-と-provides-と-search)
  - [list は「どの集合を見るか」を必ず書く](#list-はどの集合を見るかを必ず書く)
  - [info の Repository 欄で導入済みか分かる](#info-の-repository-欄で導入済みか分かる)
  - [provides はファイル名の書き方に癖がある](#provides-はファイル名の書き方に癖がある)
- [履歴を見て戻す history](#履歴を見て戻す-history)
- [結果画面の見方](#結果画面の見方)
- [やりたいこと別の早見表](#やりたいこと別の早見表)
- [このノートの検証環境](#このノートの検証環境)
- [参考リンク](#参考リンク)

---

## 消す remove と autoremove と mark

### remove は指定した1つだけを消すコマンドではない

**これがいちばん事故る操作**です。
**`dnf remove` は「それを必要としているパッケージ」も、「それを消すと誰も使わなくなるパッケージ」も、一緒に消します。**

検証環境は次の依存関係です。**`appx` だけを `dnf install appx` で入れ、残り 3 本は依存として自動で入った状態**です。

```text
      appx            ← ユーザが入れた
     ╱    ╲
  libbar  libfoo      ← 依存で自動的に入った
    │
  libbaz              ← 依存で自動的に入った
```

**いちばん下の `libbaz` を 1 つ消そうとすると、こうなります。**

```bash
$ sudo dnf remove --assumeno libbaz   # 消える一覧だけ見る（最後は No と答えさせる）
```

```text
 Package          Architecture     Version           Repository            Size
================================================================================
Removing:
 libbaz           noarch           1.1-1             @httplocal             4
Removing dependent packages:
 appx             noarch           1.0-1             @httplocal             9
Removing unused dependencies:
 libbar           noarch           1.1-1             @httplocal             4
 libfoo           noarch           2.0-1             @httplocal            11

Transaction Summary
================================================================================
Remove  4 Packages

Freed space: 28
```

**1 つ指定して 4 つ消えます。**
`libfoo` は `libbaz` と何の関係もないのに消える、というのが怖いところです。

### 3つの見出しの意味は「上か下か」ではない

**ここは誤解されやすい**ので、実測で詰めます。
上の例で、**`libbaz` に依存している `libbar`** は `Removing dependent packages:` ではなく
**`Removing unused dependencies:` のほうに入っています。**
つまり**依存グラフの上下で分けているのではありません。**

**分けているのは「そのパッケージが、ユーザが入れたものか、依存で入ったものか」**です。

| 見出し | 入るもの |
|:--|:--|
| **`Removing:`** | **自分がコマンドラインで指定したもの** |
| **`Removing dependent packages:`** | **消す対象を必要としているので、消さざるを得ないもの**のうち、**「ユーザが入れた」印のもの** |
| **`Removing unused dependencies:`** | **「依存で入った」印のもの**（消さざるを得ないものも、単に不要になったものも、まとめてここ） |

**この仮説は実測で確かめました。**
`libbar` を `dnf mark install` で「ユーザが入れた」扱いに変えてから、同じ `remove libbaz` を打ちます。

```bash
$ sudo dnf mark install libbar        # libbar を「ユーザが入れた」扱いに変える
$ sudo dnf remove --assumeno libbaz   # もう一度、同じ削除を下見する
```

```text
libbar-1.1-1.noarch marked as user installed.

Removing:
 libbaz           noarch           1.1-1             @httplocal             4
Removing dependent packages:
 appx             noarch           1.0-1             @httplocal             9
 libbar           noarch           1.1-1             @httplocal             4
Removing unused dependencies:
 libfoo           noarch           2.0-1             @httplocal            11
```

**`libbar` が `unused dependencies` から `dependent packages` へ移りました。**
依存関係は 1 つも変えていないのに、**印を変えただけで見出しが変わった**わけです。

**読むときの実用的な結論。**

| 見たいこと | 見るところ |
|:--|:--|
| **自分の意図どおりか** | `Removing:` が指定したものだけか |
| **壊れるものが無いか** | **`Removing dependent packages:` に、自分が知らないものが無いか**（ここは抑えられない） |
| **消えすぎていないか** | **`Removing unused dependencies:` の件数**（ここは `--noautoremove` で抑えられる） |
| **最終判断** | **`Remove N Packages` の N が、事前の想定と合っているか** |

**実行前に必ずこの一覧を読んでください。ここを読まずに `-y` を付けるのが事故の元です。**

### 消える範囲を変える 2 つのスイッチ

**`Removing unused dependencies:`（＝依存で入った印のもの）は、設定で抑えられます。**

| 書き方 | 効果 |
|:--|:--|
| **`clean_requirements_on_remove=True`** | **消した結果不要になった依存も消す**。**これが既定値**（検証環境の libdnf の既定値も `True`） |
| **`clean_requirements_on_remove=False`** | 不要になった依存を残す |
| **`dnf remove --noautoremove 名前`** | **そのコマンドだけ、不要になった依存を残す** |

`appx`（ユーザが入れたもの）を消すときの比較です。

```bash
$ sudo dnf remove --assumeno appx     # 既定（clean_requirements_on_remove=True）
```

```text
Removing:
 appx             noarch           1.0-1             @httplocal             9
Removing unused dependencies:
 libbar           noarch           1.1-1             @httplocal             4
 libbaz           noarch           1.1-1             @httplocal             4
 libfoo           noarch           2.0-1             @httplocal            11

Remove  4 Packages
```

```bash
$ sudo dnf remove --assumeno --noautoremove appx   # 依存を残す
```

```text
Removing:
 appx            noarch            1.0-1            @httplocal              9

Remove  1 Package
```

**4 本から 1 本になりました。**

> **`--noautoremove` は「不要になった依存を残す」だけで、「消さざるを得ないもの」は残せません。**
> さきほどの `remove libbaz` に `--noautoremove` を付けた実測では、
> **`libbar` は `Removing dependent packages:` に移って、やはり消えます**（`libbaz` が無いと動かないため）。
> 残るのは `libfoo`（`libbaz` と無関係な、単に不要になった依存）だけで、**3 本が消えます。**
>
> ```text
> Removing:                      libbaz
> Removing dependent packages:   appx, libbar
> Remove  3 Packages
> ```
>
> **`Removing dependent packages:` に想定外のものが並んでいたら、作業を止めて見直してください。**

### autoremove と mark の関係

**`dnf autoremove` は「依存として入ったが、もう誰も必要としていないもの」を消します。**

```bash
$ sudo dnf autoremove --assumeno      # 消える候補だけ見る（先にこれ）
$ sudo dnf autoremove                 # 実際に消す
```

> **下見でも `sudo` が要ります。**`dnf` は変更系のサブコマンドを root 以外で実行できず、
> `--assumeno` を付けていても `Error: This command has to be run with superuser privileges` で止まります。
> **`--assumeno` で中止したときの終了ステータスは 1** です（`Operation aborted.`）。

**判断に使っているのは「ユーザが入れたか、依存で入ったか」の印**です。
`--noautoremove` で残した依存を、あとから掃除する実測です。

```text
Removed:
  libbar-1.1-1.noarch       libbaz-1.1-1.noarch       libfoo-2.0-1.noarch
Complete!
```

**この印は `dnf mark` で付け替えられます。**

```bash
$ sudo dnf mark install libfoo        # 「ユーザが入れた」扱いにする（autoremove の対象外になる）
$ sudo dnf mark remove libfoo         # 「依存で入った」扱いに戻す（autoremove の対象になる）
$ sudo dnf mark group libfoo          # 「グループで入った」扱いにする
```

実測です。`libfoo` を「ユーザが入れた」扱いにしてから `autoremove` を打つと、`libfoo` だけ残ります。

```text
libfoo-2.0-1.noarch marked as user installed.

Removed:
  libbar-1.1-1.noarch                    libbaz-1.1-1.noarch
```

**使いどころ。**
「依存で入ったが、実は自分で使っているツール」を `autoremove` から守りたいときに `mark install` します。
逆に「手で入れたが、もう依存としてだけ残しておきたい」ものは `mark remove` します。

---

## 入れ替える swap

**「A を消して B を入れる」を 1 回の依存解決・1 トランザクションで**やります。

```bash
$ sudo dnf swap libfoo libbaz         # libfoo を消して libbaz を入れる
```

```text
Transaction Summary
Install  1 Package
Remove   1 Package

Installed:
  libbaz-1.1-1.noarch
Removed:
  libfoo-2.0-1.noarch
Complete!
```

**実務で効くのは、同じ機能（同じ Provides）を持つ別パッケージに乗り換えるとき**です。
RHEL 9 の `curl-minimal` から `curl` への入れ替えが代表例です（**実機では未検証**）。

**`remove` → `install` と 2 回打つ場合との違いは 2 つ**です。

| | `remove` → `install` の 2 回 | `swap A B` |
|:--|:--|:--|
| **依存解決** | 2 回。1 回目で「A を消すと壊れる」と言われて止まることがある | **1 回**。A が消えて B が入る前提で解決する |
| **どちらも入っていない時間** | **2 コマンドの間にできる** | **できない**（1 トランザクション） |

> **「rpm の実行中に失敗しても必ず元に戻る」とまでは言えません**（そこまでは確認していません）。
> **`swap` の利点は「依存解決が 1 回で済む」ことだと理解しておくのが安全**です。
> **`A` が入っていないと、削除側は何もせず `B` だけが入ります。** `swap` の前に `dnf list installed A` で確かめてください。

---

## 調べる list と info と provides と search

| コマンド | 何を調べるか |
|:--|:--|
| **`dnf list installed`** | **入っているもの一覧** |
| **`dnf list available`** | **リポジトリから入れられるもの**。**導入済みパッケージの「より新しい版」もここに出る** |
| **`dnf list updates`** | **更新があるもの** |
| **`dnf list extras`** | **どのリポジトリにも名前が無いのに入っているもの**（手で入れた rpm の洗い出し） |
| **`dnf info パッケージ`** | **詳細**（バージョン、サイズ、どのリポジトリ由来か） |
| **`dnf provides ファイルパス`** | **そのファイルはどのパッケージが持っているか** |
| **`dnf search キーワード`** | 名前と説明文から探す |
| **`dnf repoquery ...`** | **依存関係を機械的に調べる**（解説⑤） |

### list は「どの集合を見るか」を必ず書く

**`dnf list` だけだと「導入済み＋利用可能」が全部出ます。**何千行にもなるので、必ず絞ります。

```bash
$ dnf list installed                  # 入っているもの
$ dnf list available                  # リポジトリにあって未導入のもの
$ dnf list updates                    # 更新があるもの
$ dnf list installed 'httpd*'         # 名前で絞る（ワイルドカードはクォートする）
```

> `--installed` / `--available` / `--upgrades` という**ハイフン付きの書き方も通ります**（実測で確認。同じ意味）。
> 短い `installed` / `available` / `updates` のほうがタイプが少なく、`yum` 時代の手順書とも揃います。
>
> **`available` は「未導入のもの」ではありません。**
> `libfoo-1.0` が入っていて `2.0` がリポジトリにあれば、**`available` にはその `2.0` が出ます。**
> 「入っていないもの」を見たいつもりで読むと取り違えます。

> **`list` / `info` / `repoquery` は `versionlock` を反映しません。**
> `dnf-plugins-core` の公式ドキュメントに
> **「Note the versionlock plugin does not apply any excludes in non-transactional operations
> like repoquery, list, info, etc.」**と明記されています。
> dnf 本体のソースでも、**`plugin_filtering_enabled = True` を明示しているのは `check-update` だけ**で、
> ほかはトランザクションを解決するコマンドだけが対象になることを確認しました。
>
> | コマンド | `versionlock` が効くか |
> |:--|:--|
> | **`dnf list` / `dnf info` / `dnf repoquery`** | **効かない**（固定した版より新しいものも出る） |
> | **`dnf check-update`** | **効く**（固定したものは一覧から消える） |
> | **`dnf install` / `upgrade` など** | **効く**（固定を超えて上げられない） |
>
> **だから「`dnf list --showduplicates available` には出たのに `upgrade` で上がらない」**ということが起きます。
> **上がらないときは `dnf versionlock list` を確認してください**（実践②）。

> **`list` は該当が 0 件だと終了ステータス 1 を返します。**実測です。
>
> ```text
> $ dnf list available libfoo     # 最新版がすでに入っている状態
> Error: No matching Packages to list      （exit=1）
> ```
>
> **スクリプトで `dnf list` を使うなら、0 件とエラーを区別できません。**
> 「入っているか」を判定したいなら `rpm -q 名前` のほうが素直です
> （[RPMによるパッケージ管理](./RPMによるパッケージ管理.md)）。

実測です。

```text
Installed Packages
libbaz.noarch                          1.0-1                          @httplocal
libfoo.noarch                          1.0-1                          @httplocal
```

**リポジトリ名の頭に `@` が付いているのが「導入済み」の印**です。

**`extras` は「名前」で判定します。**
導入済みのパッケージ名が、どの有効リポジトリにも無いときだけ `Extra Packages` に出ます。
**版が違うだけでは出ません。**

実測は、**古い版だけを持つリポジトリ `oldonly`（`libfoo-1.0` と `libbaz-1.0` だけ）を唯一の有効リポジトリにして**取りました。

| 手で入れたもの | `oldonly` に同じ名前があるか | `list extras` に出るか |
|:--|:--|:--|
| `libbaz-1.1`（リポジトリには 1.0 だけ） | **ある** | **出ない** |
| `newbaz-1.0`（リポジトリに名前ごと無い） | **無い** | **出る** |

```text
Extra Packages
newbaz.noarch                        1.0-1                         @@commandline
```

**`available` は既定で「各パッケージの最新版 1 つ」しか出しません。**
古い版も見たいときは `--showduplicates` を付けます（**切り戻し先を探すときに必須**）。

```bash
$ dnf list available libfoo                      # 最新版だけ出る
$ dnf list --showduplicates available libfoo     # リポジトリにある全部の版が出る
```

```text
Available Packages
libfoo.noarch                          1.0-1                           httplocal
libfoo.noarch                          2.0-1                           httplocal
```

### info の Repository 欄で導入済みか分かる

`dnf info` の実測（導入済みと利用可能が両方出ている例）です。

```text
Installed Packages
Name         : libfoo
Version      : 1.0
Release      : 1
Architecture : noarch
Size         : 11
Source       : libfoo-1.0-1.src.rpm
Repository   : @System
From repo    : httplocal
Summary      : test package libfoo

Available Packages
Name         : libfoo
Version      : 2.0
Release      : 1
Architecture : noarch
Size         : 6.0 k
Repository   : httplocal
```

| 欄 | 意味 |
|:--|:--|
| **`Repository : @System`** | **導入済み**（システムの rpmdb にある）という意味 |
| **`From repo : httplocal`** | **どのリポジトリから入れたか**。ここが `@commandline` なら手で入れた rpm |
| **`Repository : httplocal`**（Available 側） | まだ入っておらず、httplocal リポジトリから取れる |

**`Size` の意味が上下で違う**点に注意してください。
**Installed 側は展開後のサイズ、Available 側は rpm ファイルのサイズ**です。

### provides はファイル名の書き方に癖がある

**`dnf provides` は「このファイルは誰の持ち物か」を調べるコマンド**です。
設定ファイルやコマンドの出どころを追うときに使います。

```bash
$ dnf provides /usr/sbin/sshd         # フルパスで指定する（これが基本）
$ dnf provides '*/nginx.conf'         # パスが分からないときは */ を前に付ける
$ dnf provides 'libcrypto.so.3()(64bit)'   # 能力名（Provides）でも引ける
```

実測。フルパスなら引けます。**ただし 1 件では終わりません。**
`libfoo-2.0` が入っていて、リポジトリに 1.0 と 2.0 がある状態での実測です。

```text
libfoo-1.0-1.noarch : test package libfoo
Repo        : httplocal
Matched from:
Filename    : /usr/share/libfoo

libfoo-2.0-1.noarch : test package libfoo
Repo        : @System
Matched from:
Filename    : /usr/share/libfoo

libfoo-2.0-1.noarch : test package libfoo
Repo        : httplocal
Matched from:
Filename    : /usr/share/libfoo
```

**同じ `libfoo-2.0` が 2 回出ています。**
`Repo : @System` が**サーバに入っているもの**、`Repo : httplocal` が**リポジトリが持っているもの**で、
**両方が同じ版を持っていれば、両方とも並びます。**

**ファイル名だけを渡すと、ヒットしません。**実測のエラーです。

```text
Error: No matches found. If searching for a file, try specifying the full path or
using a wildcard prefix ("*/") at the beginning.
```

**エラーメッセージ自体が答えを言っています。**
**「フルパスで書く」か「`*/` を前に付ける」**のどちらかにしてください。
ワイルドカードはシェルに食われるので、**必ずクォートします**。

> **RHEL 10 では、ファイル一覧のメタデータ（filelists）が既定でダウンロードされなくなりました。**
> Red Hat の「Considerations in adopting RHEL 10」に
> **「この更新により、このメタデータはデフォルトでダウンロードされなくなり、応答性が向上し、ディスク領域が節約されます」**
> とあります。ただし
> **「`dnf` コマンドにファイルリストメタデータが必要な場合、またはファイル関連の引数が含まれている場合、
> メタデータは自動的にロードされます」**とも書かれているので、**`dnf provides /パス` は自動で読み込まれます**
> （初回は少し待たされます）。
>
> **一方で、ファイルパスの依存を解決する必要があるトランザクションは失敗することがあります。**
> そのときは **`--setopt=optional_metadata_types=filelists`** を付けるヒントが出ます。
> **恒久的に戻すなら `/etc/dnf/dnf.conf` の `optional_metadata_types` に `filelists` を追加**します。

> `dnf provides` は**導入済みとリポジトリの両方**を探すので、**同じパッケージが複数行出ます。**
>
> | `Repo` 欄 | 意味 |
> |:--|:--|
> | **`@System`** | **サーバに入っている**（rpmdb にある） |
> | **リポジトリ名** | **そのリポジトリがその版を持っている**。入っているかどうかとは無関係 |
>
> **「リポジトリ名の行があるから未導入」ではありません。**
> いま入っているものだけを知りたいなら、`rpm -qf /パス/ファイル` のほうが 1 件で返って確実です。

---

## 履歴を見て戻す history

**`dnf history` は、やったことを全部覚えていて、元に戻せます。**
本番作業では「戻せること」が何より大事なので、ここは必ず押さえてください。

```bash
$ dnf history                         # トランザクションの一覧
$ dnf history info 12                 # ID 12 の中身を見る
$ sudo dnf history undo 12            # ID 12 だけを取り消す
$ sudo dnf history rollback 12        # ID 12 より後を全部取り消す（12 自体は残る）
$ sudo dnf history redo 12            # ID 12 と同じことをもう一度やる
```

検証環境での `dnf history` の実測です。

```text
ID     | Command line             | Date and time    | Action(s)      | Altered
-------------------------------------------------------------------------------
     2 | -c /home/claude/dnflab/d | 2026-10-13 01:08 | Upgrade        |    1
     1 | -c /home/claude/dnflab/d | 2026-10-13 01:08 | Install        |    2
```

`dnf history info` は **実行したコマンドラインまで残します**。作業記録としてそのまま使えます。

```text
Transaction ID : 1
Begin time     : Tue Oct 13 01:08:02 2026
User           : System <unset>
Return-Code    : Success
Releasever     : 9
Command Line   : ... -y install libfoo-1.0 libbaz-1.0
Comment        :
Packages Altered:
    Install libbaz-1.0-1.noarch @httplocal
    Install libfoo-1.0-1.noarch @httplocal
```

**`undo` と `rollback` は別物です。取り違えると被害が広がります。**

| コマンド | 何を取り消すか |
|:--|:--|
| **`undo 12`** | **ID 12 の 1 件だけ**。入れたものは消し、消したものは入れ直し、上げたものは下げる |
| **`rollback 12`** | **ID 12 より後のトランザクションを全部**。ID 12 自体は取り消さない |
| **`redo 12`** | ID 12 と同じ操作をもう一度やる |

`upgrade` のトランザクションを `undo` した実測です。**ちゃんと `Downgrading` になります。**

```text
Downgrading:
Transaction Summary
Downgrade  1 Package
Downgraded:
  libfoo-1.0-1.noarch
Complete!
```

> **`rollback` は影響範囲が広い**ので、まず `dnf history` で「12 より後に何があるか」を数えてください。
> **`undo` が成立する条件**（当時の rpm が取れるか）と失敗パターンは
> [dnf実践② オンライン環境での切り戻しと除外設定](./dnf実践②_オンライン環境での切り戻しと除外設定.md) に詳しく書いています。

---

## 結果画面の見方

`dnf install` を実行したときの実測です（検証環境）。

```text
 Package          Architecture     Version            Repository           Size
================================================================================
Installing:
 appx             noarch           1.0-1              httplocal           6.0 k
Installing dependencies:
 libbar           noarch           1.1-1              httplocal           6.0 k
 libbaz           noarch           1.1-1              httplocal           6.1 k
 libfoo           noarch           2.0-1              httplocal           6.0 k

Transaction Summary
================================================================================
Install  4 Packages

Total download size: 24 k
Installed size: 28
```

**読む順番は決まっています。**

| 見出し | 意味 | ここを見る理由 |
|:--|:--|:--|
| **`Installing:`** | **自分が指定したパッケージ** | 意図したものか |
| **`Installing dependencies:`** | **依存として一緒に入るもの** | **想定外のものが混ざっていないか** |
| **`Installing weak dependencies:`** | 推奨パッケージ（Recommends） | **要らなければ `install_weak_deps=False`** |
| **`Upgrading:`** | 更新されるもの | **関係ないものまで上がっていないか** |
| **`Downgrading:`** | 下がるもの | **意図しない降格が無いか**（`install` で版を指定したときに出る） |
| **`Reinstalling:`** | 入れ直されるもの | 同じ版の入れ直しか |
| **`Removing:`** | **消えるもの** | **ここが空でないときは必ず中身を読む** |
| **`Removing dependent packages:`** | **それを必要としていたので消えるもの** | **ここに想定外があれば作業を止める** |
| **`Removing unused dependencies:`** | 不要になった依存 | `--noautoremove` で残せる |
| **`Skipping packages with broken dependencies:`** | 飛ばされたもの | `--nobest` を付けたとき |
| **`Transaction Summary`** | **件数の合計** | 事前の想定と件数が合っているか |

**本番作業では、この画面をそのまま作業記録に残します。**
「何を入れたか」の証跡になり、あとで `dnf history` と突き合わせられます。

---

## やりたいこと別の早見表

| やりたいこと | コマンド |
|:--|:--|
| **入れる** | `sudo dnf install 名前` |
| **版を指定して入れる** | `sudo dnf install 名前-版` |
| **手元の rpm を入れる** | `sudo dnf install ./ファイル.rpm` |
| **更新があるか調べる** | `dnf check-update` |
| **全部更新する** | `sudo dnf upgrade` |
| **セキュリティ更新だけ** | `sudo dnf upgrade --security` |
| **変更量を抑えて更新する** | `sudo dnf upgrade-minimal --security` |
| **リポジトリの版に揃える** | `sudo dnf distro-sync` |
| **消す** | `sudo dnf remove 名前` |
| **消えるものを先に見る** | `sudo dnf remove --assumeno 名前` |
| **不要な依存を掃除する** | `sudo dnf autoremove` |
| **autoremove から守る** | `sudo dnf mark install 名前` |
| **入れ直す** | `sudo dnf reinstall 名前` |
| **前の版に戻す** | `sudo dnf downgrade 名前` |
| **直前の作業を取り消す** | `sudo dnf history undo ID` |
| **A を B に入れ替える** | `sudo dnf swap A B` |
| **入っているか調べる** | `dnf list installed 名前` |
| **戻せる版を探す** | `dnf list --showduplicates available 名前` |
| **手で入れた rpm を洗い出す** | `dnf list extras` |
| **このファイルは誰の物か** | `dnf provides /パス/ファイル` |
| **詳細を見る** | `dnf info 名前` |
| **リポジトリを見る** | `dnf repolist` / `dnf repoinfo` |

---

## このノートの検証環境

**このノートに載せた出力は、`rpmbuild` で作った検証用パッケージを使った自前のリポジトリで実際に実行した結果**です。
**構成の詳細（dnf の版・リポジトリ ID・パッケージと依存関係・設定）は
[dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) の「このノートの検証環境」に
まとめてあります。**

**RHEL の実機で取った出力ではありません。**
コマンドの挙動・オプションの有無・エラーメッセージの文面・終了ステータスは実測ですが、
`httpd` や `openssh` を対象にした例の画面そのものは載せていません（実測できていないため）。

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [DNF ドキュメント（dnf4）— Commands](https://dnf.readthedocs.io/en/latest/command_ref.html)
- [DNF ドキュメント（dnf4）— Configuration Reference](https://dnf.readthedocs.io/en/latest/conf_ref.html)
- [dnf-plugins-core ドキュメント — versionlock](https://dnf-plugins-core.readthedocs.io/en/latest/versionlock.html)（**非トランザクション操作では効かない**の出典）
- [Red Hat — Considerations in adopting RHEL 10 / ソフトウェア管理](https://docs.redhat.com/ja/documentation/red_hat_enterprise_linux/10/html/considerations_in_adopting_rhel_10/software-management)（**filelists メタデータ**の出典）
- [DNF5 ドキュメント — Changes from DNF4](https://dnf5.readthedocs.io/en/latest/changes_from_dnf4.7.html)

---

[← 全体の目次にもどる](../README.md)
