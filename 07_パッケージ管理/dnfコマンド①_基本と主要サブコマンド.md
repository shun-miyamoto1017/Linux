# dnfコマンド① 基本と主要サブコマンド

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **RHEL 系サーバを触るなら毎日使う。**脆弱性対応のパッチ適用、ミドルウェアの導入、障害時の「いま何のバージョンが入っているか」の確認。ここを曖昧なまま覚えると、本番で `dnf update` を打って関係ないパッケージまで巻き込む |

> このノートは **`dnf` そのものの使い方**です。
> リポジトリの設定は [dnfコマンド② リポジトリとキャッシュの管理](./dnfコマンド②_リポジトリとキャッシュの管理.md)、
> 依存関係とセキュリティ更新の調べ方は [dnfコマンド③ 依存関係とセキュリティ更新の調べ方](./dnfコマンド③_依存関係とセキュリティ更新の調べ方.md)、
> **リポジトリに届く環境での通しの更新手順**は [dnfコマンド④ オンライン環境での更新手順](./dnfコマンド④_オンライン環境での更新手順.md) です。
> インターネットに出られない環境での取得と適用は [dnfコマンド⑤ オフライン環境でのパッケージの集め方](./dnfコマンド⑤_オフライン環境でのパッケージの集め方.md) と
> [dnfコマンド⑥ オフライン環境での適用と切り戻し](./dnfコマンド⑥_オフライン環境での適用と切り戻し.md) にあります。
> `rpm` コマンド単体の話は [RPMによるパッケージ管理](./RPMによるパッケージ管理.md) です。

---

## 目次

- [dnf とは何か](#dnf-とは何か)
- [yum との関係](#yum-との関係)
- [ディストリごとのバージョン対応](#ディストリごとのバージョン対応)
- [まず自分の環境を確かめる](#まず自分の環境を確かめる)
- [サブコマンド一覧](#サブコマンド一覧)
- [パッケージを入れる install](#パッケージを入れる-install)
- [更新する upgrade と check-update](#更新する-upgrade-と-check-update)
- [消す remove と autoremove](#消す-remove-と-autoremove)
- [調べる list と info と provides と search](#調べる-list-と-info-と-provides-と-search)
- [戻す downgrade と history](#戻す-downgrade-と-history)
- [グローバルオプション一覧](#グローバルオプション一覧)
- [結果画面の見方](#結果画面の見方)
- [終了ステータス](#終了ステータス)
- [dnf4 と dnf5 の違い](#dnf4-と-dnf5-の違い)
- [このノートの検証環境](#このノートの検証環境)
- [参考リンク](#参考リンク)

---

## dnf とは何か

**`dnf` は RHEL 系ディストリのパッケージ管理コマンド**です。
Dandified YUM の略で、`yum` の後継にあたります。

`rpm` との違いは **依存関係を自動で解決するかどうか**の一点に尽きます。

```text
  rpm  … 「このファイルを入れろ」            依存が足りなければエラーで止まる
  dnf  … 「このパッケージを使える状態にしろ」 足りない依存をリポジトリから探して一緒に入れる
```

`dnf` は自分でパッケージを配るわけではなく、**リポジトリ**（パッケージ本体とその依存情報が置かれた場所）を見に行きます。
リポジトリはインターネット上にあることも、社内の HTTP サーバにあることも、ローカルのディレクトリであることもあります。

---

## yum との関係

**RHEL 8 以降、`yum` は `dnf` の別名**です。
Red Hat の公式ドキュメントは「yum is an alias to dnf for compatibility」（互換性のための alias）と書いています。

つまり RHEL 8 / 9 では次の 2 つは同じ動きをします。

```bash
$ sudo yum install httpd              # RHEL 8 以降ではこれも
$ sudo dnf install httpd              # 中身は同じ dnf が動く
```

**手順書には `dnf` と書くのが無難**です。
`yum` のままでも動きますが、将来 `yum` の別名が外れたときに手順書が壊れます。

> **RHEL 7 以前は本物の `yum`（yum-3）**で、`dnf` は入っていません。
> コマンド体系はよく似ていますが、オプションが違う箇所があります（後述）。

---

## ディストリごとのバージョン対応

| ディストリ | 標準のコマンド | 中身 |
|:--|:--|:--|
| **RHEL 7 / CentOS 7** | **`yum`** | **yum-3**。`dnf` は無い |
| **RHEL 8 / Rocky 8 / Alma 8 / OL8** | **`dnf`**（`yum` は別名） | **dnf-4**。Red Hat は「YUM v4」と呼ぶ |
| **RHEL 9 / Rocky 9 / Alma 9 / OL9** | **`dnf`**（`yum` は別名） | **dnf-4** |
| **RHEL 10 系** | **`dnf`** | **実機で `dnf --version` を見て確認すること**（下記） |
| **Fedora 41 以降** | **`dnf`** | **dnf-5** |

> **RHEL 10 が dnf-4 なのか dnf-5 なのかは、Red Hat の公式ドキュメントに明記がありませんでした**（調査時点）。
> RHEL 10.0 のリリースノートには `dnf-plugins-core 4.7.0` という **dnf-4 系のパッケージ名**が載っており、
> 一方 Fedora の移行計画（SwitchToDnf5）には「RHEL は RHEL 11 を目標」と書かれています。
> **断定できないので、対象サーバで `dnf --version` を実行して確かめてください。** これが唯一確実な方法です。

**dnf-4 と dnf-5 ではオプション名が一部違います。**
バージョンを確かめないまま手順書を書くと、本番で `Command line error` になります。

---

## まず自分の環境を確かめる

**作業前に必ずこの 3 つを打ちます。**

```bash
$ dnf --version                       # dnf のバージョン（4系か5系か）
$ cat /etc/redhat-release             # ディストリとマイナーバージョン
$ rpm -qf $(which yum)                # yum の実体がどのパッケージか
```

検証環境（dnf-4.14.0）での `dnf --version` の実測は次のとおりです。

```text
4.14.0
```

**数字だけが `4.` で始まって返れば dnf-4** です。
**dnf-5 は `dnf5 version 5.x.y` のような形**で返ります（dnf-5 の実機では未確認）。
**いずれにせよ、先頭の数字が 4 か 5 かで判断**してください。
以下、このノートは **dnf-4 を基準**に書き、dnf-5 で違う箇所は都度注記します。

---

## サブコマンド一覧

**dnf-4 の `dnf --help` に出る一覧**です（実測）。
「本体」は `dnf` 本体が持つもの、「プラグイン」は `dnf-plugins-core` などが追加するものです。

### よく使う本体のサブコマンド

| サブコマンド | 何をするか |
|:--|:--|
| **`install`** | **パッケージを入れる**（依存も一緒に） |
| **`upgrade`** | **更新する**（`update` は別名） |
| **`upgrade-minimal`** | **問題を直す最小限のバージョンまでしか上げない** |
| **`remove`** | **消す**（`erase` は別名） |
| **`autoremove`** | **依存として入ったが、もう誰も使っていないものを消す** |
| **`reinstall`** | 同じバージョンを入れ直す |
| **`downgrade`** | **前のバージョンに戻す** |
| **`distro-sync`** | 導入済みを、リポジトリにある版へ揃える（上げも下げもする） |
| **`swap`** | 片方を消して片方を入れる、を 1 トランザクションで |
| **`check-update`** | **更新があるか調べるだけ**（適用しない） |
| **`list`** | パッケージの一覧 |
| **`info`** | **パッケージの詳細** |
| **`provides`** | **このファイルはどのパッケージが持っているか** |
| **`search`** | 名前と説明から探す |
| **`repoquery`** | **リポジトリに問い合わせる**（依存調査の主役。③で詳説） |
| **`repolist`** | **リポジトリの一覧** |
| **`makecache`** | メタデータのキャッシュを作る |
| **`clean`** | キャッシュを消す |
| **`history`** | **トランザクションの履歴。元に戻せる** |
| **`mark`** | 「ユーザが入れた」「依存で入った」の印を付け替える |
| **`module`** | **AppStream のモジュールを操作する**（RHEL 8 / 9） |
| **`group`** | パッケージグループを操作する |
| **`updateinfo`** | **アドバイザリ（セキュリティ情報）を見る**（③で詳説） |
| `check` | パッケージDBの整合性を調べる |
| `repository-packages` | 指定リポジトリのパッケージだけを対象に操作する |
| `shell` | 対話シェル |

### プラグインが追加するサブコマンド

**`dnf-plugins-core`（RHEL 8 以降。RHEL 8.1 で `dnf-utils` から `yum-utils` に改名）**が入っていないと使えません。

| サブコマンド | 何をするか |
|:--|:--|
| **`download`** | **入れずにダウンロードだけする**（⑤の主役） |
| **`config-manager`** | **リポジトリの有効・無効を切り替える、設定を書き換える** |
| **`repoclosure`** | **依存が閉じているか（足りない依存が無いか）を調べる** |
| **`reposync`** | **リポジトリをまるごとローカルに複製する** |
| **`needs-restarting`** | **更新後に再起動が要るサービスを調べる** |
| **`repomanage`** | 古い版の rpm を整理する |
| **`builddep`** | ソースビルドに必要な依存を入れる |
| **`changelog`** | パッケージの変更履歴を見る |
| **`repodiff`** | 2 つのリポジトリの差分を出す |
| **`repograph`** | 依存グラフを dot 形式で出す |
| `versionlock` | **バージョンを固定する**（別パッケージ `python3-dnf-plugin-versionlock`） |
| `modulesync` | モジュールのパッケージをダウンロードする |
| `leaves` | どこからも必要とされていない導入済みパッケージを出す |

**入っているか確かめる**

```bash
$ rpm -q dnf-plugins-core             # 入っていれば版が出る。無ければ not installed
$ sudo dnf install -y dnf-plugins-core   # 入っていなければこれで導入する
```

---

## パッケージを入れる install

```bash
$ sudo dnf install httpd              # 依存も含めて入れる（確認あり）
$ sudo dnf install -y httpd           # 確認を出さずに入れる
$ sudo dnf install httpd-2.4.62       # バージョンを指定して入れる
$ sudo dnf install ./foo-1.0.rpm      # ローカルの rpm ファイルを依存解決つきで入れる
```

**`dnf install ./ファイル.rpm` は `rpm -ivh` と違います。**
`rpm` は依存が足りなければ止まりますが、`dnf` は**リポジトリから足りない依存を探してきて一緒に入れます**。
オフライン環境ではこの違いが効いてきます（⑤）。

**よく使う組み合わせ**

| 書き方 | 効果 |
|:--|:--|
| **`--downloadonly`** | **実際には入れず、ダウンロードだけする** |
| **`--destdir=ディレクトリ`** | **ダウンロード先を指定する**（`--downloaddir` は別名） |
| **`--setopt=install_weak_deps=False`** | **推奨パッケージ（Recommends）を入れない**。最小構成にしたいとき |
| **`--nogpgcheck`** | GPG 署名を確認しない（**原則使わない**） |
| **`--skip-broken`** | 依存が壊れているパッケージを飛ばす。**脆弱性対応では使わない**（直したいパッケージ自体が黙って飛ばされる） |
| **`--allowerasing`** | 依存解決のために導入済みを消すことを許す（**危険。内容を読んでから**） |
| **`--best`** / **`--nobest`** | 最新版にこだわる / こだわらない |

---

## 更新する upgrade と check-update

**まず「何が更新対象か」を見てから上げる**のが鉄則です。

```bash
$ dnf check-update                    # 更新があるか調べるだけ。何も変更しない
$ sudo dnf upgrade                    # 全部更新する
$ sudo dnf upgrade httpd              # httpd とその依存だけ更新する
$ sudo dnf upgrade --security         # セキュリティ関連の更新だけ
```

検証環境で `libfoo-1.0` を入れた状態の `dnf check-update` の実測です。

```text
libfoo.noarch                            2.0-1                             local
```

**左からパッケージ名.アーキテクチャ / 新しいバージョン / どのリポジトリか**の 3 列です。

> **`dnf update` は `dnf upgrade` の別名**です。動きは同じです。
> RHEL 8 以降は `yum` が `dnf` の別名なので、**`yum update` も `dnf upgrade` も同じ動き**です。
> `update` と `upgrade` で obsoletes の扱いが違ったのは **RHEL 7 の yum-3** の話です。
> それでも**手順書には `upgrade` と書くほう**が、何をするかが明確になります。

**`upgrade` と `upgrade-minimal` の違い**

| コマンド | 何をするか | 使いどころ |
|:--|:--|:--|
| **`upgrade`** | **利用できる最新版まで上げる** | 通常の更新 |
| **`upgrade-minimal`** | **問題を直す最小限の版までしか上げない** | **本番で変更量を抑えたいとき**。`--security` と組み合わせる |

---

## 消す remove と autoremove

```bash
$ sudo dnf remove httpd               # httpd を消す（それに依存するものも一緒に消える）
$ sudo dnf autoremove                 # 依存で入ったが、もう誰も使っていないものを消す
```

**`dnf remove` は「それを必要としているパッケージ」も一緒に消します。**
実行前に必ず **Removing:** の一覧を読んでください。ここを読まずに `-y` を付けるのが事故の元です。

```bash
$ sudo dnf remove --assumeno httpd    # 消える一覧だけ見て、最後は No と答えさせる
```

---

## 調べる list と info と provides と search

| コマンド | 何を調べるか |
|:--|:--|
| **`dnf list --installed`** | **入っているもの一覧** |
| **`dnf list --available`** | リポジトリにあって、まだ入っていないもの |
| **`dnf list --upgrades`** | **更新があるもの** |
| **`dnf info パッケージ`** | **詳細**（バージョン、サイズ、どのリポジトリ由来か） |
| **`dnf provides ファイルパス`** | **そのファイルはどのパッケージが持っているか** |
| **`dnf search キーワード`** | 名前と説明文から探す |

検証環境での `dnf list --installed` の実測です。

```text
Installed Packages
libbar.noarch                            1.0-1                            @local
libbaz.noarch                            1.0-1                            @local
libfoo.noarch                            1.0-1                            @local
```

**リポジトリ名の頭に `@` が付いているのが「導入済み」の印**です。
`@local` は「local というリポジトリから入れた」という意味になります。

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
From repo    : local
Summary      : test package libfoo

Available Packages
Name         : libfoo
Version      : 2.0
Release      : 1
Architecture : noarch
Size         : 6.0 k
Repository   : local
```

| 欄 | 意味 |
|:--|:--|
| **`Repository : @System`** | **導入済み**（システムの rpmdb にある）という意味 |
| **`From repo : local`** | **どのリポジトリから入れたか** |
| **`Repository : local`**（Available 側） | まだ入っておらず、local リポジトリから取れる |

**`dnf provides` は「このファイルは誰の持ち物か」を調べるコマンド**です。
設定ファイルやコマンドの出どころを追うときに使います。

```bash
$ dnf provides /usr/sbin/sshd         # このファイルを持っているパッケージを探す
$ dnf provides '*/nginx.conf'         # ワイルドカードも使える（クォートを忘れない）
```

---

## 戻す downgrade と history

**`dnf history` は、やったことを全部覚えていて、元に戻せます。**
本番作業では「戻せること」が何より大事なので、ここは必ず押さえてください。

```bash
$ dnf history                         # トランザクションの一覧
$ dnf history info 12                 # ID 12 の中身を見る
$ sudo dnf history undo 12            # ID 12 だけを取り消す
$ sudo dnf history rollback 12        # ID 12 より後を全部取り消す（12 自体は残る）
```

検証環境での `dnf history` の実測です。

```text
ID     | Command line             | Date and time    | Action(s)      | Altered
-------------------------------------------------------------------------------
     1 | -c dnf.conf --installroo | 2026-09-29 14:46 | Install        |    4
```

**`undo` と `rollback` は別物です。取り違えると被害が広がります。**

| コマンド | 何を取り消すか |
|:--|:--|
| **`undo 12`** | **ID 12 の 1 件だけ**。入れたものは消し、消したものは入れ直し、上げたものは下げる |
| **`rollback 12`** | **ID 12 より後のトランザクションを全部**。ID 12 自体は取り消さない |

> **`rollback` は影響範囲が広い**ので、まず `dnf history` で「12 より後に何があるか」を数えてください。

**`downgrade` は単発で戻したいとき**に使います。

```bash
$ sudo dnf downgrade httpd            # 1つ前のバージョンに戻す
$ sudo dnf downgrade httpd-2.4.57     # 戻す先を指定する
```

**前の版がリポジトリに残っていないと戻せません。**
社内リポジトリを運用しているなら、**古い版を消さない設計にしておく**ことが実質的なロールバック手段になります。

---

## グローバルオプション一覧

**`dnf --help` の「General DNF options」に出るもの**です（dnf-4.14.0 の実測から、業務で使うものを抜粋）。
これらは **どのサブコマンドにも付けられます**。

### 対象を絞る

| オプション | 効果 |
|:--|:--|
| **`--enablerepo=ID`** | **そのコマンドの間だけリポジトリを有効にする** |
| **`--disablerepo=ID`** | **そのコマンドの間だけリポジトリを無効にする**（`'*'` で全部） |
| **`--repo=ID`** / `--repoid=ID` | **そのリポジトリだけを使う**（`--disablerepo` とは**併用できない**） |
| **`--repofrompath=ID,パス`** | **設定ファイルを作らずに、その場でリポジトリを足す** |
| **`-x パッケージ`** / `--exclude=` | 対象から外す |
| `--disableexcludes=repo` | 設定ファイルの exclude を無効にする |

> **`--disablerepo='*' --repo=xxx` はエラーになります。** 実測での表示は次のとおりです。
>
> ```text
> Command line error: argument --repo/--repoid: not allowed with argument --disablerepo
> ```
>
> **1 つのリポジトリだけを使いたいなら `--repo=xxx` だけ**を書きます。

### 動きを変える

| オプション | 効果 |
|:--|:--|
| **`-y`** / `--assumeyes` | すべて yes と答える |
| **`--assumeno`** | **すべて no と答える**。**変更内容の下見に最適** |
| **`--downloadonly`** | **ダウンロードだけして、入れない** |
| **`--destdir=パス`** | **ダウンロード先を指定する** |
| **`--setopt=キー=値`** | **設定を一時的に上書きする** |
| **`--releasever=バージョン`** | `$releasever` の値を上書きする |
| **`--installroot=パス`** | **そのディレクトリを `/` とみなして動く** |
| **`--refresh`** | **キャッシュを期限切れ扱いにして取り直す** |
| **`-C`** / `--cacheonly` | **キャッシュだけで動く。ネットワークを見に行かない** |
| **`--nogpgcheck`** | GPG 署名を確認しない |
| **`--skip-broken`** | 依存が解決できないものを飛ばす |
| **`--allowerasing`** | 依存解決のために導入済みを消すことを許す |
| **`--best`** / **`--nobest`** | 最新版にこだわる / こだわらない |
| **`--forcearch=アーキ`** | アーキテクチャを強制する |
| `--noplugins` | プラグインを全部無効にする |
| `--disableplugin=名前` | 特定のプラグインだけ無効にする |
| `-q` / `--quiet` | 出力を減らす |
| `-v` / `--verbose` | 出力を増やす |

### アドバイザリで絞る

**脆弱性対応で毎回使うもの**です。詳しくは③にまとめています。

| オプション | 効果 |
|:--|:--|
| **`--security`** | **セキュリティ関連のものだけ** |
| **`--bugfix`** | バグ修正のものだけ |
| **`--enhancement`** | 機能追加のものだけ |
| **`--newpackage`** | 新規パッケージのものだけ |
| **`--advisory=ID`** | **指定したアドバイザリ**（`RHSA-2026:0001` など）**に必要なものだけ** |
| **`--cve=ID`** | **指定した CVE に必要なものだけ** |
| **`--sec-severity=重大度`** | `Critical` / `Important` / `Moderate` / `Low` で絞る。**1 つ書くとその重大度だけ**になる。複数欲しければ**複数回書く**（実測） |
| `--bz=ID` | 指定した Bugzilla に必要なものだけ |

---

## 結果画面の見方

`dnf install` を実行したときの実測です（検証環境）。

```text
 Package           Architecture      Version             Repository        Size
Installing:
 appx              noarch            1.0-1               local            6.0 k
Installing dependencies:
 libbar            noarch            1.0-1               local            6.0 k
 libbaz            noarch            1.0-1               local            6.0 k
 libfoo            noarch            2.0-1               local            6.0 k

Transaction Summary
Install  4 Packages

Total size: 24 k
Installed size: 42
```

**読む順番は決まっています。**

| 見出し | 意味 | ここを見る理由 |
|:--|:--|:--|
| **`Installing:`** | **自分が指定したパッケージ** | 意図したものか |
| **`Installing dependencies:`** | **依存として一緒に入るもの** | **想定外のものが混ざっていないか** |
| **`Installing weak dependencies:`** | 推奨パッケージ（Recommends） | **要らなければ `install_weak_deps=False`** |
| **`Upgrading:`** | 更新されるもの | **関係ないものまで上がっていないか** |
| **`Removing:`** | **消えるもの** | **ここが空でないときは必ず中身を読む** |
| **`Downgrading:`** | 下がるもの | 意図しない降格が無いか |
| **`Skipping packages with broken dependencies:`** | 飛ばされたもの | `--skip-broken` を付けたとき |
| **`Transaction Summary`** | **件数の合計** | 事前の想定と件数が合っているか |

**本番作業では、この画面をそのまま作業記録に残します。**
「何を入れたか」の証跡になり、あとで `dnf history` と突き合わせられます。

---

## 終了ステータス

**スクリプトや監視で判定に使うもの**です。

| コマンド | 終了ステータス | 意味 |
|:--|:--|:--|
| **`dnf check-update`** | **0** | **更新なし** |
| | **100** | **更新あり** |
| | 1 | エラー |
| **`dnf needs-restarting -r`** | **0** | **再起動は不要** |
| | **1** | **再起動が必要** |
| **`dnf repoclosure`** | **0** | **依存が閉じている** |
| | **1** | **足りない依存がある** |
| その他のサブコマンド | 0 | 成功 |
| | 1 | エラー |

検証環境での実測です。

```bash
$ dnf check-update --security > /dev/null ; echo "exit=$?"   # 終了ステータスだけ見る
```

```text
exit=100
```

**`check-update` が 0 以外でもエラーとは限りません。**
`set -e` を書いたシェルスクリプトの中で `dnf check-update` を素で呼ぶと、更新があるだけでスクリプトが落ちます。

```bash
$ dnf check-update || true            # 100 で落ちないようにする
```

---

## dnf4 と dnf5 の違い

**dnf-5 を使う環境（Fedora 41 以降など）では、次の点が変わっています。**
手順書を両方で使い回すときはここを確認してください。

| 項目 | dnf-4 | dnf-5 |
|:--|:--|:--|
| **アドバイザリ表示** | **`dnf updateinfo`** | **`dnf advisory`**（`updateinfo` は別名として残る）。**サブコマンド必須**（`list` / `info` / `summary`） |
| **ダウンロード先** | `--destdir` と `--downloaddir` の両方 | **`--destdir` のみ**（`--downloaddir` は廃止） |
| **`download --source`** | `--source` | **`--srpm` に改名** |
| **`download --resolve` / `--alldeps`** | あり | **あり。名前も同じ** |
| **`install --downloadonly`** | あり | **あり**（保存先指定は `dnf5 download --destdir` を使う） |
| **`repoquery`** | `-a` / `--alldeps` / `--nevra` / `--envra` / `--nvr` / `--unsatisfied` あり | **これらは廃止** |
| **`needs-restarting -r`** | **終了ステータスで判定** | **再起動判定が既定動作。`-r` は互換のため残っているだけで効果なし** |
| **`config-manager`** | オプション形式（`--add-repo` など） | **サブコマンド形式**（`addrepo` / `setopt` / `enable` / `disable` など）。既存の repo ファイルは書き換えず drop-in に書く |
| **`reposync`** | `--downloadcomps` あり | **廃止。`--download-metadata` を使う** |
| **`repoclosure --pkg`** | オプションで指定 | **廃止。位置引数で指定** |
| **`history`** | サブコマンド省略可 | **サブコマンド必須** |
| **プラグインのパッケージ** | `dnf-plugins-core` | **`dnf5-plugins`** |
| **`versionlock`** | プラグイン | **本体のコマンド** |

> **RHEL 7（yum-3）との対応表**は [dnfコマンド⑥ オフライン環境での適用と切り戻し](./dnfコマンド⑥_オフライン環境での適用と切り戻し.md) の末尾にまとめてあります。

---

## このノートの検証環境

**このノートに載せた出力は、次の環境で実際に実行した結果**です。

| 項目 | 内容 |
|:--|:--|
| dnf | **dnf-4.14.0** |
| rpm | rpm-4.18.2 |
| createrepo_c | あり |
| リポジトリ | **`rpmbuild` で作った検証用パッケージ**（`appx` / `libfoo` / `libbar` / `libbaz`）を `createrepo_c` でリポジトリ化したもの |
| 依存関係 | `appx` → `libfoo >= 1.0`, `libbar` → `libbaz` |

**RHEL の実機で取った出力ではありません。**
コマンドの挙動・オプションの有無・終了ステータスは実測ですが、
`httpd` や `openssh` を対象にした例の画面そのものは載せていません（実測できていないため）。

**同じ検証環境は手元で再現できます。**
`rpmbuild` で小さな noarch パッケージを数個作り、`createrepo_c` でディレクトリをリポジトリ化すれば、
本番に触らずに `dnf` の依存解決の挙動を確かめられます。手順は⑥の「手元で練習する」に書いています。

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — Considerations in adopting RHEL 9 / Software management](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/considerations_in_adopting_rhel_9/assembly_software-management_considerations-in-adopting-rhel-9)
- [Red Hat — Considerations in adopting RHEL 8 / Software management](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/considerations_in_adopting_rhel_8/software-management_considerations-in-adopting-rhel-8)
- [DNF ドキュメント（dnf4）](https://dnf.readthedocs.io/en/latest/)
- [DNF5 ドキュメント — Changes from DNF4](https://dnf5.readthedocs.io/en/latest/changes_from_dnf4.7.html)
- [dnf-plugins-core ドキュメント](https://dnf-plugins-core.readthedocs.io/en/latest/)

---

[← 全体の目次にもどる](../README.md)
