# dnf解説① 基本とインストール系コマンド

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **RHEL 系サーバを触るなら毎日使う。**脆弱性対応のパッチ適用、ミドルウェアの導入、障害時の「いま何のバージョンが入っているか」の確認。ここを曖昧なまま覚えると、本番で `dnf update` を打って関係ないパッケージまで巻き込む |

> **このフォルダの dnf ノートは「解説」と「実践」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | **解説** | **このノート（dnf解説①）** | **`dnf` と `yum` の関係**、**`install` / `localinstall` / `update` / `upgrade` の違い**、`distro-sync`、`reinstall`、`downgrade` |
> | 解説 | [dnf解説② 削除系と調査系コマンド](./dnf解説②_削除系と調査系コマンド.md) | **`remove` で何が一緒に消えるか**、`autoremove` / `mark` / `swap`、`list` / `info` / `provides`、`history` での切り戻し |
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

- [dnf とは何か](#dnf-とは何か)
- [yum との関係](#yum-との関係)
- [自分の環境を先に確かめる](#自分の環境を先に確かめる)
- [サブコマンド一覧](#サブコマンド一覧)
  - [よく使う本体のサブコマンド](#よく使う本体のサブコマンド)
  - [プラグインが追加するサブコマンド](#プラグインが追加するサブコマンド)
- [install と localinstall と update と upgrade の違い](#install-と-localinstall-と-update-と-upgrade-の違い)
  - [まず結論](#まず結論)
  - [公式ドキュメントは「非推奨の別名」と書いている](#公式ドキュメントは非推奨の別名と書いている)
  - [install は「指定したものを、その状態にする」コマンド](#install-は指定したものをその状態にするコマンド)
  - [install が更新してしまうのは best 設定のせい](#install-が更新してしまうのは-best-設定のせい)
  - [install は降格もする](#install-は降格もする)
  - [localinstall は引数が rpm ファイルに限られる](#localinstall-は引数が-rpm-ファイルに限られる)
  - [update は upgrade の「非推奨の別名」](#update-は-upgrade-の非推奨の別名)
  - [使い分けの指針](#使い分けの指針)
- [パッケージを入れる install](#パッケージを入れる-install)
- [更新する upgrade と check-update](#更新する-upgrade-と-check-update)
  - [upgrade と upgrade-minimal](#upgrade-と-upgrade-minimal)
  - [distro-sync は「リポジトリに合わせる」](#distro-sync-はリポジトリに合わせる)
- [入れ直す reinstall](#入れ直す-reinstall)
- [戻す downgrade](#戻す-downgrade)
- [結果画面の読み方は解説②へ](#結果画面の読み方は解説②へ)
- [このノートの検証環境](#このノートの検証環境)
- [参考リンク](#参考リンク)

---

## dnf とは何か

**`dnf` は RHEL 系ディストリのパッケージ管理コマンド**です。
Dandified YUM の略で、`yum` の後継にあたります。

`rpm` との最大の違いは **依存関係を自動で解決するかどうか**です。
ほかに**トランザクションの履歴を持って元に戻せる**こと、**リポジトリからパッケージを取ってくる**ことも `dnf` 側の仕事です。

```text
  rpm  … 「このファイルを入れろ」            依存が足りなければエラーで止まる
  dnf  … 「このパッケージを使える状態にしろ」 足りない依存をリポジトリから探して一緒に入れる
```

`dnf` は自分でパッケージを配るわけではなく、**リポジトリ**（パッケージ本体とその依存情報が置かれた場所）を見に行きます。
リポジトリはインターネット上にあることも、社内の HTTP サーバにあることも、ローカルのディレクトリであることもあります。

---

## yum との関係

**RHEL 8 以降、`yum` は `dnf` の別名**です。Red Hat の公式ドキュメントの記載はこうです。

| ドキュメント | 記載 |
|:--|:--|
| **Considerations in adopting RHEL 8** | **「installing software is ensured by the YUM tool, which is based on the DNF technology (YUM v4)」**／**「`yum` is an alias to `dnf` for compatibility」** |
| **Managing software with the DNF tool (RHEL 9)** | **「`yum` is an alias for `dnf`」** |
| **Amazon Linux 2023 User Guide** | **「In AL2023 the `yum` command is still available, but as a pointer to the `dnf` command」** |

つまり RHEL 8 / 9 では次の 2 つは同じ動きをします。

```bash
$ sudo yum install httpd              # RHEL 8 以降ではこれも
$ sudo dnf install httpd              # 中身は同じ dnf が動く
```

**手順書には `dnf` と書くのが無難**です。
`yum` のままでも動きますが、将来 `yum` の別名が外れたときに手順書が壊れます。

> **RHEL 7 以前は本物の `yum`（yum-3）**で、`dnf` は入っていません。
> コマンド体系はよく似ていますが、オプションが違う箇所があります（[dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md)）。

---

## 自分の環境を先に確かめる

**どのディストリか、dnf-4 か dnf-5 かで、使えるオプションが変わります。**
**作業前に必ずこの 3 つを打ってください。**

```bash
$ dnf --version                       # dnf のバージョン（4系か5系か）
$ cat /etc/redhat-release             # ディストリとマイナーバージョン
$ rpm -q dnf-plugins-core yum-utils dnf-utils   # プラグインがどの名前で入っているか
```

**ディストリごとの対応表、`dnf --version` の読み方、dnf-4 と dnf-5 の差分**は
[dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md) にまとめました。
**RHEL 7（yum-3）／RHEL 10／Amazon Linux の扱いもそこにあります。**

---

## サブコマンド一覧

**dnf-4 の `dnf --help` に出る一覧**です（実測）。
「本体」は `dnf` 本体が持つもの、「プラグイン」は `dnf-plugins-core` などが追加するものです。

### よく使う本体のサブコマンド

**公式ドキュメントは「別名（Aliases）」と「非推奨の別名（Deprecated aliases）」を分けて書いています。**
**非推奨の別名は、手順書に書かないでください。**

| サブコマンド | 別名 | 非推奨の別名 | 何をするか |
|:--|:--|:--|:--|
| **`install`** | `in`／`install-n`・`install-na`・`install-nevra` | **`localinstall`** | **パッケージを入れる**（依存も一緒に） |
| **`upgrade`** | `up` | **`update`** / `upgrade-to` / `update-to` / `localupdate` | **更新する** |
| **`upgrade-minimal`** | — | — | **バグ修正・機能追加・セキュリティ修正を含む、いちばん近い版までしか上げない** |
| **`remove`** | `rm`／`remove-n`・`remove-na`・`remove-nevra` | **`erase`** / `erase-n` / `erase-na` / `erase-nevra` | **消す** |
| **`autoremove`** | — | — | **依存として入ったが、もう誰も使っていないものを消す** |
| **`reinstall`** | `rei` | — | 同じバージョンを入れ直す |
| **`downgrade`** | `dg` | — | **前のバージョンに戻す** |
| **`distro-sync`** | `dsync` | `distrosync` / `distribution-synchronization` | 導入済みを、リポジトリにある版へ揃える（**上げも下げもする**） |
| **`swap`** | — | — | 片方を消して片方を入れる、を 1 トランザクションで |
| **`check-update`** | `check-upgrade` | — | **更新があるか調べるだけ**（適用しない） |
| **`list`** | パッケージの一覧 |
| **`info`** | **パッケージの詳細** |
| **`provides`** | **このファイルはどのパッケージが持っているか** |
| **`search`** | 名前と説明から探す |
| **`repoquery`** | **リポジトリに問い合わせる**（依存調査の主役。解説⑤で詳説） |
| **`repolist`** / `repoinfo` | **リポジトリの一覧 / その詳細** |
| **`makecache`** | メタデータのキャッシュを作る |
| **`clean`** | キャッシュを消す |
| **`history`** | **トランザクションの履歴。元に戻せる** |
| **`mark`** | 「ユーザが入れた」「依存で入った」の印を付け替える |
| **`module`** | **AppStream のモジュールを操作する**（RHEL 8 / 9）。**RHEL 10 ではモジュール機能が非推奨**で、`dnf module` は非推奨の警告を出す（[dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md)） |
| **`group`** | パッケージグループを操作する |
| **`updateinfo`** | **アドバイザリ（セキュリティ情報）を見る**（解説⑤で詳説） |
| `check` | パッケージDBの整合性を調べる |
| `repository-packages` | 指定リポジトリのパッケージだけを対象に操作する |
| `alias` | `dnf` 自身のコマンド別名を作る |
| `shell` | 対話シェル |
| `deplist` | **非推奨**。`repoquery --deplist` を使う |

> **RHEL 10 ではモジュール機能（Modularity）が非推奨になりました。**
> Red Hat の「Considerations in adopting RHEL 10」には
> **「RHEL 10 では、モジュール機能は非推奨となり、今後のメジャーリリースで削除される予定です」**
> **「したがって、RHEL 10 ではモジュールコンテンツは配布されません」**
> **「そのため、DNF `module` コマンドで非推奨の警告が表示されます」**と書かれています。
> **RHEL 8 / 9 から 10 へ移るときは、`dnf module` に依存した手順書を作り直す必要があります。**
> RHEL 10 の変更点は [dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md) にまとめました。

### プラグインが追加するサブコマンド

**`dnf-plugins-core`** が入っていないと使えません。
**`yum-utils` / `dnf-utils` という名前でも入るという話がありますが、公式に裏を取れていません**（下記）。
**対象サーバで `rpm -q dnf-plugins-core yum-utils dnf-utils` を実行して、入っているものを確かめてください。**

| サブコマンド | 何をするか |
|:--|:--|
| **`download`** | **入れずにダウンロードだけする**（実践③の主役） |
| **`config-manager`** | **リポジトリの有効・無効を切り替える、設定を書き換える** |
| **`repoclosure`** | **依存が閉じているか（足りない依存が無いか）を調べる** |
| **`reposync`** | **リポジトリをまるごとローカルに複製する** |
| **`needs-restarting`** | **更新後に再起動が要るサービスを調べる** |
| **`repomanage`** | 古い版の rpm を整理する |
| **`builddep`** | ソースビルドに必要な依存を入れる |
| **`changelog`** | パッケージの変更履歴を見る |
| **`repodiff`** | 2 つのリポジトリの差分を出す |
| **`repograph`** | 依存グラフを dot 形式で出す |
| `debug-dump` / `debug-restore` | 導入済みパッケージの一覧を保存・復元。**RHEL 10 で `dnf-plugins-core` から削除された**（[dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md)） |
| `versionlock` | **バージョンを固定する**（別パッケージ `python3-dnf-plugin-versionlock`） |
| `modulesync` | モジュールのパッケージをダウンロードする |
| `leaves` | どこからも必要とされていない導入済みパッケージを出す |
| `debuginfo-install` | デバッグ情報のパッケージを入れる |
| `copr` | Copr リポジトリを操作する |
| `local` | ローカルディレクトリを自動でリポジトリ化する |
| `migrate` | yum-3 の履歴・グループデータを dnf へ移行する |
| `post-transaction-actions` | トランザクション完了後にコマンドを実行する |
| `show-leaves` | トランザクション後に「葉」になったパッケージを出す |
| `system-upgrade` | メジャーバージョンアップを行う |
| `groups-manager` | グループのメタデータを作る・編集する |

> **上の一覧は `dnf-plugins-core` 公式ドキュメントのプラグイン一覧（2026-10-13 時点で 23 本）に合わせています。**
> **検証環境の `dnf --help` には `playground` も出ましたが、公式の一覧には載っていません。**
> **プラグインの顔ぶれはディストリと版で変わるので、`dnf --help` の「List of Plugin Commands」を見てください。**
>
> ```bash
> $ dnf --help | sed -n '/List of Plugin Commands/,$p'   # その環境で使えるプラグインを見る
> ```

**入っているか確かめる**

```bash
$ rpm -q dnf-plugins-core             # 入っていれば版が出る。無ければ not installed
$ sudo dnf install -y dnf-plugins-core   # 入っていなければこれで導入する
```

> **RHEL 8 以降のパッケージ名について（2026-10-13 時点の確認結果）。**
> Red Hat の「Considerations in adopting RHEL 8」には
> **「Selected yum plug-ins and utilities have been ported to the new DNF back end,
> and can be installed under the same names as in RHEL 7.」**（RHEL 7 と同じ名前で入れられる）
> と書かれています。
>
> **ただし、このページは `yum-utils` / `dnf-utils` / `dnf-plugins-core` というパッケージ名を一つも挙げていません。**
> **「だから `yum-utils` で入る」は、この文からの私の推測です。公式の裏付けはありません。**
> **正式名がどれかも、Red Hat 公式ドキュメントでは確認できませんでした。**対象サーバで確かめてください。
>
> ```bash
> $ rpm -q dnf-plugins-core yum-utils dnf-utils   # 入っているものだけ版が出る
> ```

> **RHEL 10 では `debug` プラグイン（`debug-dump` / `debug-restore`）が削除されました。**
> 代わりに `dnf list --installed` か `dnf repoquery --installed` で一覧を保存し、
> `dnf install` に渡して複製するよう案内されています。
> **RHEL 10 のそのほかの変更点（モジュール非推奨・filelists メタデータ・`libreport` 削除）は
> [dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md) にまとめました。**

---

## install と localinstall と update と upgrade の違い

**ここがいちばん誤解されるところ**なので、先に片付けます。

### まず結論

| 書き方 | 実体 | 引数に取れるもの | すること |
|:--|:--|:--|:--|
| **`dnf install 名前`** | `install` | **パッケージ名 / 名前-版 / ローカルの rpm / URL** | **指定したものを「導入済み」の状態にする**。足りなければ入れ、古ければ上げ、**版を明示すれば下げることもある** |
| **`dnf localinstall ファイル`** | **`install` の別名** | **ローカルの rpm / URL だけ** | 上と同じ。**パッケージ名を渡すと拒否される** |
| **`dnf update`** | **`upgrade` の別名** | パッケージ名（省略可） | **導入済みのものを、より新しい版へ上げる**。入っていないものは入れない |
| **`dnf upgrade`** | `upgrade` | パッケージ名（省略可） | 同上 |

**ひとことで言うと、こうです。**

```text
  install  … 「この状態にしろ」      入っていなくてもよい。上げも下げもありうる
  upgrade  … 「入っているものを上げろ」入っていないものは対象外。下げはしない
```

**`localinstall` と `update` は、覚える必要がある別のコマンドではありません。**
`localinstall` は `install` の、`update` は `upgrade` の、**同じ実装を呼ぶ別名**です。

### 公式ドキュメントは「非推奨の別名」と書いている

**DNF の公式コマンドリファレンス（`dnf.readthedocs.io` の Command Reference）には、こう書かれています。**
（**各コマンドの項から該当行だけを抜き出して並べたもの**です。原文は出典を参照してください。）

```text
Command: install
  Aliases: in
  Aliases for explicit NEVRA matching: install-n, install-na, install-nevra
  Deprecated aliases: localinstall

Command: upgrade
  Aliases: up
  Deprecated aliases: update, upgrade-to, update-to, localupdate

Command: remove
  Aliases: rm
  Aliases for explicit NEVRA matching: remove-n, remove-na, remove-nevra
  Deprecated aliases: erase, erase-n, erase-na, erase-nevra
```

**`localinstall` と `update` は「Deprecated aliases（非推奨の別名）」**です。
動きますが、**公式に非推奨とされているので、手順書には書かないでください。**

dnf-4 のソースでも同じことが確認できます。検証環境で実際に確認した行です。
（**置き場所はディストリと python のバージョンで違います。**RHEL 9 なら `/usr/lib/python3.9/site-packages/dnf/cli/commands/`、
検証環境の Debian 系は `/usr/lib/python3/dist-packages/dnf/cli/commands/` でした。**パスは決め打ちせず、次のように探してください。**）

```text
upgrade.py:  aliases = ('upgrade', 'update', 'upgrade-to', 'update-to', 'localupdate', 'up')
install.py:  aliases = ('install', 'localinstall', 'in') + tuple(nevra_forms.keys())
remove.py:   aliases = ('remove', 'erase', 'rm') + tuple(nevra_forms.keys())
```

**同じ `aliases` に並んでいる名前は、すべて同じクラスが処理します。**
`update` と `upgrade` の挙動が違うという話は、**RHEL 7 の yum-3 までの事情**で、dnf には当てはまりません。

> 自分の環境でも確かめられます。
>
> ```bash
> $ rpm -ql python3-dnf | grep 'cli/commands/upgrade.py'    # まず置き場所を調べる
> $ grep -n 'aliases = ' "$(rpm -ql python3-dnf | grep 'cli/commands/upgrade.py$')"   # 別名の定義を直接見る
> ```

### install は「指定したものを、その状態にする」コマンド

**`install` は「入れる」ではなく「その状態にする」コマンド**です。
だから **すでに古い版が入っていると、黙って更新します。**

検証環境の実測です。`libfoo-1.0` が入っていて、リポジトリに `libfoo-2.0` がある状態で `dnf install libfoo` を打ちます。

```bash
$ sudo dnf install libfoo             # 入れるつもりで打った
```

```text
Upgraded:
  libfoo-2.0-1.noarch

Complete!
```

**`Installed:` ではなく `Upgraded:` と出ています。**
「入れるだけのつもりだったのに、version が上がっていた」という事故は、ここから起きます。

**上げたくないなら、版まで指定します。**

```bash
$ sudo dnf install libfoo-1.0         # 1.0 を名指しする。すでに 1.0 なら Nothing to do
```

### install が更新してしまうのは best 設定のせい

**この挙動は `best` という設定で変わります。**

**公式に確認できたこと**（2026-10-13 時点）。

| 何を | 公式の記載 |
|:--|:--|
| **dnf 本体の既定値** | **DNF 公式 Configuration Reference：`best` は「The default is `False`.」** |
| **ディストリが上書きしうること** | **同じページに「`best` and `skip_if_unavailable` can be overridden by your distribution's configuration」** |
| **実際に `True` になっている例** | **Rocky Linux 9 の公式ドキュメントに載っている `/etc/dnf/dnf.conf` は `best=True`**（`gpgcheck=1` / `installonly_limit=3` / `clean_requirements_on_remove=True` / `skip_if_unavailable=False` と並んで記載） |

> **「RHEL が配る `dnf.conf` は `best=True`」という明記は、Red Hat の公式ドキュメントでは見つけられませんでした。**
> **RHEL 系の実環境では `True` になっている可能性が高い**（Rocky は RHEL の再ビルドで、検証環境もこの値で揃えています）
> **ものの、断定はしません。対象サーバで必ず確かめてください**（確認コマンドは下記）。

検証環境で libdnf の既定値そのものも確認しました（`ConfigMain().best()` の値と優先度が「`False` / 既定」）。

同じ状態（`libfoo-1.0` が入っていて `2.0` がある）で、設定だけ変えて比較した実測です。

```bash
$ sudo dnf install libfoo --setopt=best=False   # best を False にして install
```

```text
Package libfoo-1.0-1.noarch is already installed.
Dependencies resolved.
Nothing to do.
Complete!
```

```bash
$ sudo dnf install libfoo --setopt=best=True    # best を True にして install
```

```text
Upgrading:
 libfoo           noarch           2.0-1              httplocal           6.0 k
```

| `best` の値 | `dnf install 名前`（古い版が入っている） |
|:--|:--|
| **`False`**（dnf の既定値） | **`Nothing to do`**。すでに入っているので何もしない |
| **`True`**（RHEL 系の実環境でよく見る値） | **最新版へ `Upgrading`** |

**つまり「install が更新するかどうか」はサーバの設定次第**です。
自分の環境がどちらかは、次で分かります。

```bash
$ grep -nE '^best' /etc/dnf/dnf.conf                       # 設定ファイルに書かれているか見る
$ dnf config-manager --dump 2>/dev/null | grep -E '^best'  # 実際に効いている値を見る
```

### install は降格もする

**版を明示すると、`install` は降格（downgrade）もします。**
`libfoo-2.0` が入っている状態で、1.0 を名指しした実測です。

```bash
$ sudo dnf install libfoo-1.0         # 2.0 が入っているのに 1.0 を指定した
```

```text
Downgrading:
Downgrade  1 Package
Downgraded:
  libfoo-1.0-1.noarch
```

**ローカルの rpm ファイルを渡した場合も同じ**です。

```bash
$ sudo dnf install ./libfoo-1.0-1.noarch.rpm   # 2.0 が入っている状態で古い rpm を渡した
$ dnf list installed libfoo                    # 結果を確認する
```

```text
Installed Packages
libfoo.noarch                        1.0-1                         @@commandline
```

> **`@@commandline`** は「リポジトリ経由ではなく、コマンドラインで渡した rpm から入った」という印です。
> `@` が 2 つ付いているのは、`@`（導入済み）＋ `@commandline`（擬似リポジトリ名）が並んでいるためです。
>
> **「リポジトリ由来ではないから更新されない」と思いがちですが、それは誤りです。**
> **同じ名前のパッケージが有効なリポジトリにあれば、`@commandline` で入れたものも普通に更新対象になります。**実測しました。
>
> ```text
> $ dnf list installed libfoo   → libfoo.noarch  1.0-1  @@commandline
> $ dnf check-update            → libfoo.noarch  2.0-1  httplocal     （exit=100）
> $ sudo dnf upgrade libfoo     → Upgraded: libfoo-2.0-1.noarch
> $ dnf list installed libfoo   → libfoo.noarch  2.0-1  @httplocal    （印が変わる）
> ```
>
> **更新されないのは「どの有効リポジトリにも、その名前が無い」場合だけ**です。
> その場合は `dnf list extras` に出てきます（解説②）。**手で入れた rpm は、台帳に残しておくこと。**

**この挙動は公式ドキュメントにも明記されています。**
DNF 公式 Command Reference の `install` の項には、版を指定した場合についてこう書かれています。

```text
Install the package with a specific version. If the package is already installed it
will automatically try to downgrade or upgrade to the specific version.
```

`--best` を付けた場合についてはこうです。

```text
Install the latest available version of the package. If the package is already installed it
will try to automatically upgrade to the latest version. If the latest version
of the package cannot be installed, the installation will fail.
```

**まとめると `install` は「指定した版に合わせる」コマンド**で、
上がるか下がるか何もしないかは **「指定の仕方」と「best 設定」の組み合わせ**で決まります。

> **`--best` の効き方には公式の但し書きがあります。**
> **最新版が保証されるのは「直接指定したパッケージ」だけ**で、
> **依存として引かれるパッケージは古い版が選ばれることがあります。**
> 「依存まで全部最新になる」と思って使わないでください。

### localinstall は引数が rpm ファイルに限られる

**`localinstall` は `install` と同じクラスが処理しますが、引数のチェックだけが違います。**
実測で確かめた違いは次の 1 点です。

```bash
$ sudo dnf localinstall libfoo        # リポジトリのパッケージ名を渡してみる
```

```text
Not a valid rpm file path: libfoo
Error: Nothing to do.
```

```bash
$ sudo dnf install libfoo             # install なら通る
```

```text
Installed:
  libfoo-2.0-1.noarch
```

**グループ指定（`@グループ名`）でも、返るエラーが違います。**

| コマンド | `@core` を渡したときのエラー（実測） |
|:--|:--|
| **`dnf localinstall '@core'`** | **`Not a valid rpm file path: @core`**（rpm のパスとしか解釈しない） |
| **`dnf install '@core'`** | **`Module or Group 'core' is not available.`**（グループとして解釈してから探す） |

> **`install` 側のエラー文面は、検証環境にグループ情報（comps）が無いために出たもの**です。
> **RHEL の実機には `core` グループが実在するので、`dnf install '@core'` は実際にインストールが走ります。**
> ここで見てほしいのは **「`localinstall` は引数を rpm のパスとしか解釈しない」**という点だけです。

**rpm ファイルのパスと URL は、どちらでも同じように通ります。**

```bash
$ sudo dnf install ./libfoo-1.0-1.noarch.rpm        # ローカルの rpm（install）
$ sudo dnf localinstall ./libfoo-1.0-1.noarch.rpm   # 同じものを localinstall で（結果は同じ）
$ sudo dnf install http://repo.example.com/libfoo-1.0-1.noarch.rpm      # URL も通る
$ sudo dnf localinstall http://repo.example.com/libfoo-1.0-1.noarch.rpm # localinstall でも通る
```

| | `install` | `localinstall` |
|:--|:--|:--|
| パッケージ名（`httpd`） | **可** | **不可** |
| 名前-版（`httpd-2.4.62`） | **可** | **不可** |
| グループ（`@core`） | **可** | **不可** |
| ローカルの rpm（`./foo.rpm`） | **可** | **可** |
| URL（`http://.../foo.rpm`） | **可** | **可** |

**結論。`localinstall` を使う理由はほぼありません。**
`dnf install ./ファイル.rpm` で足ります。**手順書には `install` と書くほうが、読む人が迷いません。**
**`localinstall` は公式に「Deprecated aliases（非推奨の別名）」と明記されています。**
古い `yum` 時代の手順書との互換のために残っているだけです。

> **「yum-3 では `install` にローカルファイルを渡せず、`localinstall` が必要だった」という説明を見かけますが、
> これは誤りです。**yum-3 の man ページ（`man 8 yum`）には、はっきりこう書かれています。
>
> ```text
> localinstall
>   Is used to install a set of local rpm files.
>   If required the enabled repositories will be used to resolve dependencies.
>   Note that the install command will do a local install, if given a filename.
>
> install
>   If the name is a file, then install works like localinstall.
> ```
>
> **yum-3 の時点でも `yum install ./foo.rpm` は通りました。**
> `localinstall` は「ローカルの rpm ファイルだけを受け取る専用コマンド」で、
> **`install` で代用できることが man ページ自体に明記されています。**
> なお **yum-3 の man ページは `localinstall` を「非推奨」とは書いていません。**非推奨にしたのは dnf です。
> （出典は yum プロジェクトの man ページ本文。**Red Hat の製品ドキュメントではありません。**
> RHEL 7 の実機があれば `man 8 yum` で同じ記述を確認できます。）

### update は upgrade の「非推奨の別名」

**`dnf update` と `dnf upgrade` は、同じクラスを呼ぶので挙動が完全に同じ**です。
ただし**公式ドキュメントは `update` を「Deprecated aliases（非推奨の別名）」に分類しています。**
前述の `aliases` に両方が並んでいます。検証環境で `update` が実際に動くことも確認しました。

**手順書には必ず `upgrade` と書いてください。**理由は 3 つです。

1. **公式ドキュメントが `update` を「Deprecated aliases（非推奨の別名）」に分類している**
2. **dnf-5 では `upgrade-to` と `localupdate` の別名が実際に削除された**（`dnf5` の「Changes between DNF and DNF5」に記載）
3. **`update` は「更新」という日本語に引かれて意味が広く受け取られる。**`upgrade` なら「版を上げる」と読める

**`upgrade` は「入っていないものは入れない」のが `install` との決定的な違い**です。

```bash
$ sudo dnf upgrade libbar             # libbar は入っていない状態で打った
```

```text
Package libbar available, but not installed.
No match for argument: libbar
Error: No packages marked for upgrade.
```

**`Package libbar available, but not installed.`** が出たら、
**「リポジトリにはあるが、このサーバには入っていない」**という意味です。入れたいなら `install` を使います。

### 使い分けの指針

| やりたいこと | 書くコマンド | 理由 |
|:--|:--|:--|
| **新しくミドルウェアを導入する** | **`dnf install 名前`** | 依存も含めて入る |
| **版を指定して導入する** | **`dnf install 名前-版`** | `best=True` でも勝手に上がらない |
| **手元の rpm を入れる** | **`dnf install ./ファイル.rpm`** | 依存はリポジトリから補われる |
| **入っているものだけ上げる** | **`dnf upgrade`** / **`dnf upgrade 名前`** | 入っていないものを巻き込まない |
| **セキュリティ更新だけ当てる** | **`dnf upgrade --security`** | 解説⑤・実践① |
| **リポジトリの版に揃える（下げも含む）** | **`dnf distro-sync`** | 後述 |
| **元の版に戻す** | **`dnf downgrade 名前`** / **`dnf history undo ID`** | 後述 |

---

## パッケージを入れる install

```bash
$ sudo dnf install httpd              # 依存も含めて入れる（確認あり）
$ sudo dnf install -y httpd           # 確認を出さずに入れる
$ sudo dnf install httpd-2.4.62       # バージョンを指定して入れる
$ sudo dnf install httpd mod_ssl      # 複数まとめて入れる（1トランザクションになる）
$ sudo dnf install ./foo-1.0.rpm      # ローカルの rpm ファイルを依存解決つきで入れる
```

**`dnf install ./ファイル.rpm` は `rpm -ivh` と違います。**
`rpm` は依存が足りなければ止まりますが、`dnf` は**リポジトリから足りない依存を探してきて一緒に入れます**。

ローカルの rpm を 1 つ渡しただけで、依存が 3 つリポジトリから降ってきた実測です。

```bash
$ sudo dnf install ./appx-1.0-1.noarch.rpm   # appx の rpm だけを渡した
```

```text
 Package          Architecture     Version         Repository              Size
================================================================================
Installing:
 appx             noarch           1.0-1           @commandline           6.0 k
Installing dependencies:
 libbar           noarch           1.1-1           httplocal              6.0 k
 libbaz           noarch           1.1-1           httplocal              6.1 k
 libfoo           noarch           2.0-1           httplocal              6.0 k

Transaction Summary
================================================================================
Install  4 Packages

Total size: 24 k
Total download size: 18 k
Installed size: 28
```

**ここで 2 つ、ローカル rpm のときだけ現れるものがあります。**

| 見えるもの | 意味 |
|:--|:--|
| **Repository 欄が `@commandline`** | **コマンドラインで渡した rpm**（リポジトリ由来ではない）という印 |
| **`Total size` と `Total download size` が別に出る** | **`Total size` は 4 本ぶん（24 k）、`Total download size` は落とす 3 本ぶん（18 k）**。手元にある rpm は落とさないので差が出る |

**オフライン環境ではこの違いが効いてきます**（依存がリポジトリから降ってこないので、自分で集める必要がある。実践③）。

**よく使う組み合わせ**

| 書き方 | 効果 |
|:--|:--|
| **`--downloadonly`** | **実際には入れず、ダウンロードだけする** |
| **`--destdir=ディレクトリ`** | **ダウンロード先を指定する**（`--downloaddir` は別名） |
| **`--setopt=install_weak_deps=False`** | **推奨パッケージ（Recommends）を入れない**。最小構成にしたいとき |
| **`--nogpgcheck`** | GPG 署名を確認しない（**原則使わない**） |
| **`--allowerasing`** | 依存解決のために導入済みを消すことを許す（**危険。内容を読んでから**） |
| **`--best`** / **`--nobest`** | 最新版にこだわる / こだわらない |

> オプションの詳しい挙動（**`--skip-broken` と `--nobest` の違い**など）は
> [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) にまとめています。

---

## 更新する upgrade と check-update

**まず「何が更新対象か」を見てから上げる**のが鉄則です。

```bash
$ dnf check-update                    # 更新があるか調べるだけ。何も変更しない
$ sudo dnf upgrade                    # 導入済みのものを全部更新する
$ sudo dnf upgrade httpd              # httpd とその依存だけ更新する
$ sudo dnf upgrade --security         # セキュリティ関連の更新だけ
```

検証環境で `libfoo-1.0` を入れた状態の `dnf check-update` の実測です。

```text
libfoo.noarch                          2.0-1                           httplocal
```

**左からパッケージ名.アーキテクチャ / 新しいバージョン / どのリポジトリか**の 3 列です。

**`check-update` は終了ステータスで「更新の有無」を返します。**

```bash
$ dnf check-update > /dev/null ; echo "exit=$?"   # 終了ステータスだけ見る
```

```text
exit=100
```

| 終了ステータス | 意味 |
|:--|:--|
| **0** | **更新なし** |
| **100** | **更新あり** |
| 1 | エラー（リポジトリに届かない等） |

> **`set -e` のシェルスクリプトで `dnf check-update` を素で呼ぶと、更新があるだけで落ちます。**
> **`|| true` は 1（リポジトリに届かない等の本当のエラー）も握りつぶします。**
> 100 だけを許す書き方は [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) の終了ステータスの節にあります。

### upgrade と upgrade-minimal

| コマンド | 何をするか | 使いどころ |
|:--|:--|:--|
| **`upgrade`** | **利用できる最新版まで上げる** | 通常の更新 |
| **`upgrade-minimal`** | **「バグ修正・機能追加・セキュリティ修正のいずれかを含む、いちばん近い版」までしか上げない** | **本番で変更量を抑えたいとき**。`--security` と組み合わせる |

公式コマンドリファレンスの `upgrade-minimal` の説明は、**「バグ修正・機能追加・セキュリティ修正のいずれかを
提供する、いちばん近い利用可能なバージョンへ各パッケージを更新する」**という内容です
（原文は `Updates each package to the nearest available version that provides a bugfix,
enhancement or a fix for a security issue (security).` ／出典は参考リンク）。

**「セキュリティ修正だけ」ではなく「バグ修正・機能追加・セキュリティ修正のどれかを含む最も近い版」**が基準です。

**「最小限」の基準はアドバイザリ（updateinfo）**です。
`libfoo` に 1.0 → 1.1 → 2.0 とあり、脆弱性を直したのが 1.1 なら、`upgrade-minimal --security` は **1.1 で止まります**。
`upgrade --security` は **2.0 まで上げます**（最新版にも修正が入っているため）。

> **ここに落とし穴があります。`upgrade-minimal` は、リポジトリに updateinfo が無いと何もしません。**
> 検証環境で、updateinfo を持たないリポジトリに対して実行した実測です。
>
> ```text
> Dependencies resolved.
> Nothing to do.
> Complete!
> ```
>
> `libfoo-1.0` が入っていて `2.0` が利用できる状態でも、**「最小限」の判断材料が無いので上げません。**
> **RHEL の公式リポジトリには updateinfo がありますが、社内で `createrepo_c` だけで作ったリポジトリには入っていません。**
> 自分のリポジトリで updateinfo が配られているかは、次で確かめられます。
>
> ```bash
> $ dnf updateinfo summary              # アドバイザリの件数を見る。何も出なければ updateinfo が無い
> ```
>
> 検証環境（updateinfo を持たないリポジトリ）での実測は、**件数の行が 1 行も出ません**（終了ステータスは 0）。

### distro-sync は「リポジトリに合わせる」

**`upgrade` 系のサブコマンドの中で、「下げる」方向にも動くのは `distro-sync` だけ**です。
（`install 名前-版` と `downgrade`、`history undo` も下げますが、あれは「下げてくれ」と指定して下げるものです。
`distro-sync` は**こちらが版を指定しなくても下げます**。ここが怖いところです。）
「リポジトリにある版と、サーバに入っている版を一致させる」コマンドだからです。

検証環境で、**サーバに 2.0 が入っていて、リポジトリには 1.0 しか無い**状態を作って比較した実測です。

```bash
$ sudo dnf upgrade                    # 上げるものは無いので何もしない
```

```text
Dependencies resolved.
Nothing to do.
Complete!
```

```bash
$ sudo dnf distro-sync                # 同じ状態で distro-sync を打つ
$ dnf list installed libfoo           # 結果を確認する
```

```text
Downgrading:
Downgrade  1 Package
  Downgrading      : libfoo-1.0-1.noarch                                    1/2
Downgraded:
  libfoo-1.0-1.noarch
Complete!
```

```text
Installed Packages
libfoo.noarch                           1.0-1                           @oldonly
```

| コマンド | 導入済みがリポジトリより**古い** | 導入済みがリポジトリより**新しい** |
|:--|:--|:--|
| **`upgrade`** | **上げる** | **何もしない** |
| **`distro-sync`** | **上げる** | **下げる** |

**使いどころは 2 つ**です。

- **マイナーバージョンを固定している環境**（`releasever` を 9.4 に固定など）で、
  **何らかの理由で 9.4 より新しい版が入ってしまったパッケージを、9.4 の版へ揃え直す**
- **EPEL など別リポジトリから手で新しい版を入れてしまったサーバ**を、標準のリポジトリの状態へ戻す

> **本番でいきなり打たないこと。**「下げる」方向に動くので、`--assumeno` で一覧を見てから判断します。

---

## 入れ直す reinstall

**ファイルを消してしまった・設定ファイルを壊した**ときに、同じ版を上書きで入れ直します。

```bash
$ sudo dnf reinstall httpd            # 同じバージョンを入れ直す
```

```text
Reinstalling     : libfoo-1.0-1.noarch                                    1/2
Cleanup          : libfoo-1.0-1.noarch                                    2/2

Reinstalled:
  libfoo-1.0-1.noarch

Complete!
```

**成立する条件は「いま入っているのと同じ版が、リポジトリにもある」ことだけ**です。
**失敗したときのエラーは、原因によって文面が変わります。**どちらも実測です。

**① リポジトリに同じ版が無い**（`libfoo-2.0` が入っているが、リポジトリには 1.0 しか無い）

```text
Installed package libfoo-2.0-1.noarch (from httplocal) not available.
Error: No packages marked for reinstall.
```

**② そもそも入っていない**（`appx` は未導入）

```text
Package appx available, but not installed.
No match for argument: appx
Error: No packages marked for reinstall.
```

**①なら「古い版を消してしまった社内リポジトリ」を疑い、②なら `install` を使う**、という切り分けになります。

> **`reinstall` は設定ファイルを元に戻してくれません。**
> `%config(noreplace)` が付いた設定ファイルを**書き換えてある場合、同じ版を入れ直しても書き換えた内容がそのまま残ります**
> （同じ版なので rpm 側の中身に差が無く、`.rpmnew` も作られません）。**消してしまった場合は復元されます。**
> **書き換えた設定を元に戻したいなら、`rpm2cpio` で rpm から取り出すのが確実です**
> （[RPMによるパッケージ管理](./RPMによるパッケージ管理.md)）。

---

## 戻す downgrade

**`downgrade` は単発で前の版に戻したいとき**に使います。

```bash
$ sudo dnf downgrade httpd            # 1つ前のバージョンに戻す
$ sudo dnf downgrade httpd-2.4.57     # 戻す先を指定する
$ sudo dnf downgrade ./httpd-2.4.57-1.el9.x86_64.rpm   # 手元の rpm に戻す
```

実測です。`libfoo-2.0` が入っている状態で打ちました。

```text
Downgrading      : libfoo-1.0-1.noarch                                    1/2
Cleanup          : libfoo-2.0-1.noarch                                    2/2

Downgraded:
  libfoo-1.0-1.noarch

Complete!
```

**前の版がリポジトリに残っていないと戻せません。**
社内リポジトリを運用しているなら、**古い版を消さない設計にしておく**ことが実質的なロールバック手段になります。

| 戻し方 | 範囲 | 前提 |
|:--|:--|:--|
| **`dnf downgrade 名前`** | **そのパッケージ 1 つ**（＋必要な依存） | 前の版がリポジトリか手元にある |
| **`dnf history undo ID`** | **そのトランザクション全体** | 当時の rpm が取れる |
| **`dnf install 名前-版`** | 版を名指しして合わせる | 同上 |

---

## 結果画面の読み方は解説②へ

**`Installing:` / `Upgrading:` / `Removing:` など、確認画面の見出しの読み方**は
[dnf解説② 削除系と調査系コマンド](./dnf解説②_削除系と調査系コマンド.md) の「結果画面の見方」にまとめました。
**`Removing:` が 3 段に分かれる理由**もそちらにあります。

---

## このノートの検証環境

**このノートに載せた出力は、次の環境で実際に実行した結果**です。

| 項目 | 内容 |
|:--|:--|
| dnf | **dnf-4.14.0** |
| rpm | rpm-4.18.2 |
| createrepo_c | あり |
| リポジトリ | **`rpmbuild` で作った検証用パッケージ**を `createrepo_c` でリポジトリ化し、**HTTP で配信**したもの。リポジトリ ID は **`httplocal`**（新しい版も持つ側）と **`oldonly`**（古い版だけを持つ側） |
| パッケージ | `appx-1.0` / `libfoo-1.0, 2.0` / `libbar-1.0, 1.1` / `libbaz-1.0, 1.1`（すべて noarch） |
| 依存関係 | `appx` → `libbar` と `libfoo >= 1.0`、`libbar` → `libbaz` |
| updateinfo | **無し**（`createrepo_c` だけで作ったため。`--security` 系と `upgrade-minimal` はこのリポジトリでは動かない） |
| 設定 | `best=True` / `clean_requirements_on_remove=True` / `installonly_limit=3`（**Rocky Linux 9 の公式ドキュメントに載っている `/etc/dnf/dnf.conf` と同じ値に揃えたもの**） |

> **このノートの出力は、上記のリポジトリ（`libfoo` は 1.0 と 2.0 だけ）で取っています。**
> [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) では、
> `--nobest` と `--allowerasing` を試すために **依存が壊れた `libfoo-3.0` と、`libbaz` と衝突する `newbaz-1.0`** を
> 同じリポジトリに足しています。**それらを足すと、このノートの出力は再現しません**（最新版が 3.0 になるため）。

**RHEL の実機で取った出力ではありません。**
コマンドの挙動・オプションの有無・終了ステータスは実測ですが、
`httpd` や `openssh` を対象にした例の画面そのものは載せていません（実測できていないため）。

**同じ検証環境は手元で再現できます。**
`rpmbuild` で小さな noarch パッケージを数個作り、`createrepo_c` でディレクトリをリポジトリ化すれば、
本番に触らずに `dnf` の依存解決の挙動を確かめられます。手順は実践④の「手元で練習する」に書いています。

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — Software management tools in RHEL 9](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/con_software-management-tools-in-red-hat-enterprise-linux-9_managing-software-with-the-dnf-tool)（**`yum` is an alias for `dnf`** の出典）
- [Red Hat — Considerations in adopting RHEL 8 / Software management](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/considerations_in_adopting_rhel_8/software-management_considerations-in-adopting-rhel-8)（**YUM v4** とプラグイン名の出典）
- [Red Hat — Considerations in adopting RHEL 10 / ソフトウェア管理](https://docs.redhat.com/ja/documentation/red_hat_enterprise_linux/10/html/considerations_in_adopting_rhel_10/software-management)（**モジュール非推奨 / filelists / debug プラグイン削除**の出典）
- [Red Hat — RHEL 10.0 Release Notes / New features（Software management）](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/10.0_release_notes/new-features-and-enhancements)
- [Red Hat — Managing software with the DNF tool (RHEL 10)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html-single/managing_software_with_the_dnf_tool/index)
- [AWS — Package management tool (Amazon Linux 2023)](https://docs.aws.amazon.com/linux/al2023/ug/package-management.html)
- [Red Hat — Considerations in adopting RHEL 9 / Software management](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/considerations_in_adopting_rhel_9/assembly_software-management_considerations-in-adopting-rhel-9)
- [DNF ドキュメント（dnf4）— Command Reference](https://dnf.readthedocs.io/en/latest/command_ref.html)（**別名 / 非推奨の別名 / 終了ステータス**の出典）
- [DNF ドキュメント（dnf4）— Configuration Reference](https://dnf.readthedocs.io/en/latest/conf_ref.html)（**設定の既定値**の出典）
- [DNF5 ドキュメント — Changes between DNF and DNF5](https://dnf5.readthedocs.io/en/latest/changes_from_dnf4.7.html)（**dnf-4 / dnf-5 差分**の出典）
- [dnf-plugins-core ドキュメント](https://dnf-plugins-core.readthedocs.io/en/latest/)

---

[← 全体の目次にもどる](../README.md)
