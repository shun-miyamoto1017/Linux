# dnf解説⑥ 環境の見極めとバージョン差分

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **手順書を書く前と、他人の手順書を自分の環境で使う前に開くノート。**RHEL 7 / 8 / 9 / 10 と Amazon Linux で `yum` と `dnf` のどちらが標準かが違い、dnf-4 と dnf-5 ではオプション名が変わっている。ここを確かめずに手順書を書くと、本番で `Command line error` になる |

> **このフォルダの dnf ノートは「解説」と「実践」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) | **`dnf` と `yum` の関係**、**`install` / `localinstall` / `update` / `upgrade` の違い**、`distro-sync`、`reinstall`、`downgrade` |
> | 解説 | [dnf解説② 削除系と調査系コマンド](./dnf解説②_削除系と調査系コマンド.md) | **`remove` で何が一緒に消えるか**、`autoremove` / `mark` / `swap`、`list` / `info` / `provides`、`history` での切り戻し |
> | 解説 | [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) | **どのサブコマンドにも付くオプション**、`--nobest` と `--skip-broken` と `--allowerasing` の違い、終了ステータス |
> | 解説 | [dnf解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) | `.repo` の書式、`$releasever` / `$basearch`、GPG 鍵、プロキシ、キャッシュ、AppStream モジュール |
> | 解説 | [dnf解説⑤ 依存関係とセキュリティ更新の調べ方](./dnf解説⑤_依存関係とセキュリティ更新の調べ方.md) | `repoquery` の使い方、アドバイザリと CVE、`repoclosure`、`needs-restarting` |
> | **解説** | **このノート（dnf解説⑥）** | **ディストリごとの `yum` / `dnf` 対応**、dnf-4 と dnf-5 の差分、**RHEL 10 で変わったこと** |
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

- [このノートの使い方](#このノートの使い方)
- [ディストリごとのバージョン対応](#ディストリごとのバージョン対応)
- [まず自分の環境を確かめる](#まず自分の環境を確かめる)
- [dnf4 と dnf5 の違い](#dnf4-と-dnf5-の違い)
- [RHEL 10 で変わったこと](#rhel-10-で変わったこと)
- [参考リンク](#参考リンク)

---

## このノートの使い方

**作業前に「対象サーバがどれなのか」を 1 分で見極めるためのノート**です。
手順書を書く前と、他人の手順書を自分の環境で使う前に開いてください。

| 知りたいこと | 読むところ |
|:--|:--|
| **このディストリの標準は `yum` か `dnf` か** | [ディストリごとのバージョン対応](#ディストリごとのバージョン対応) |
| **dnf-4 か dnf-5 か、どう見分けるか** | [まず自分の環境を確かめる](#まず自分の環境を確かめる) |
| **dnf-4 の手順書を dnf-5 で使えるか** | [dnf4 と dnf5 の違い](#dnf4-と-dnf5-の違い) |
| **RHEL 10 で消えた・非推奨になったもの** | [RHEL 10 で変わったこと](#rhel-10-で変わったこと) |

---

## ディストリごとのバージョン対応

| ディストリ | 標準のコマンド | 中身 |
|:--|:--|:--|
| **RHEL 7 / CentOS 7** | **`yum`** | **yum-3**。`dnf` は無い |
| **RHEL 8 / Rocky 8 / Alma 8 / OL8** | **`dnf`**（`yum` は別名） | **dnf-4**。Red Hat は「YUM v4」と呼ぶ |
| **RHEL 9 / Rocky 9 / Alma 9 / OL9** | **`dnf`**（`yum` は別名） | **dnf-4** |
| **RHEL 10 系** | **`dnf`** | **実機で `dnf --version` を見て確認すること**（下記） |
| **Fedora 41 以降** | **`dnf`** | **dnf-5** |
| **Amazon Linux 2** | **`yum`** | AWS 公式は **「DNF is the successor to YUM, the package management tool in AL2.」**とだけ記載。**YUM の版数の記載は無い** |
| **Amazon Linux 2023** | **`dnf`**（`yum` は `dnf` を指すポインタ） | **AWS 公式に DNF のバージョン番号の記載なし。実機で `dnf --version` を確認すること** |

> **RHEL 10 が dnf-4 なのか dnf-5 なのかは、Red Hat の公式ドキュメントに明記を見つけられませんでした**（2026-10-13 時点で再確認）。
> 確認できたのは**間接的な手がかりだけ**です。
>
> | 公式ドキュメント | 記載 | 読めること |
> |:--|:--|:--|
> | RHEL 10.0 リリースノート（Software management） | **`dnf-plugins-core` を 4.7.0 で提供** | **dnf-4 系のパッケージ名**（dnf-5 のプラグインは `dnf5-plugins`） |
> | 同上 | 設定ファイルとして **`/etc/dnf/dnf.conf`** を案内 | dnf-4 と同じパス |
> | RHEL 10.0 リリースノート（New features） | **`dnf needs-restarting` に `--exclude-services` が追加された**（「A new `--exclude-services` flag to exclude `systemd` services from the list of stale processes」） | **dnf-5 では `needs-restarting` が「開いているファイルを調べる」仕様自体をやめている。**RHEL 10 はまだ「調べる」側の仕様に対してオプションを足している |
>
> **「おそらく dnf-4 系」という状況証拠は揃っていますが、断定はしません。**
> **対象サーバで `dnf --version` を実行して確かめてください。** これが唯一確実な方法です。

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

**先頭行が `4.` で始まっていれば dnf-4** です。
**RHEL の実機では、この後ろに `Installed:` / `Built :` の行が続きます**（`dnf` と `rpm` の導入情報。
検証環境は rpmdb に `dnf` 自身が登録されていないので 1 行だけになっています）。
**dnf-5 は `dnf5 version 5.x.y` のような形**で返ります（dnf-5 の実機では未確認）。
**いずれにせよ、先頭の数字が 4 か 5 かで判断**してください。
以下、このノートは **dnf-4 を基準**に書き、dnf-5 で違う箇所は都度注記します。

---

## dnf4 と dnf5 の違い

**dnf-5 を使う環境（Fedora 41 以降など）では、次の点が変わっています。**
手順書を両方で使い回すときはここを確認してください。

**以下は `dnf5` 公式ドキュメントの「Changes between DNF and DNF5」の記載に基づきます。**

| 項目 | dnf-4 | dnf-5 |
|:--|:--|:--|
| **`best` の既定値** | **`False`** | **`true` に変更された**（**挙動が変わる最重要の差分**） |
| **`strict` 設定** | `strict` の 1 つ | **`skip_broken` と `skip_unavailable` の 2 つに分割** |
| **`upgrade --skip-broken`** | **実質 no-op**（yum 互換のために残っているだけ） | **削除された。**`best` / `no-best` で制御する |
| **`--nobest`** | `--nobest` | **`--no-best`**。真偽値オプションを `--<option>` / `--no-<option>` の形に揃えた改名で、**元の名前は当面「互換の別名」として残る**（「The options with original names are retained for now as compatibility aliases.」）。**「Global options scoping」には「`--best`, `--no-best` are only relevant to several transaction commands.」と書かれている** |
| **アドバイザリ表示** | **`dnf updateinfo`** | **`dnf advisory` に改名**（`updateinfo` は互換の別名）。**サブコマンド必須**。引数なしの `updateinfo` は `advisory summary` に相当 |
| **`--sec-severity`** | `--sec-severity` | **`--advisory-severities` に改名** |
| **ダウンロード先** | `--destdir` と `--downloaddir` の両方 | **`--downloaddir` は廃止。`download` コマンドでは `--destdir` のみ** |
| **`download --source`** | `--source` | **`--srpm` に改名** |
| **`repoquery --resolve`** | `--resolve` | **`--providers-of=PACKAGE_ATTRIBUTE` に改名** |
| **`repoquery` の廃止オプション** | `-a`/`--all` / `--alldeps` / `--nevra` / `--envra` / `--nvr` / `--unsatisfied` あり。`--archlist` は `--arch` の別名、`-f` は `--file` の別名 | **`-a`/`--all` / `--alldeps` / `--nevra` / `--envra` / `--nvr` / `--unsatisfied` を廃止**（`--unsatisfied` は `dnf check --dependencies` へ）。**別名の `--archlist` と `-f` も廃止**（`--arch` と `--file` 自体は残る）。**`repoquery-n` / `repoquery-na` / `repoquery-nevra` も廃止。`--file` の引数は空白区切りからカンマ区切りに変更** |
| **`repoquery` の改名** | `--source` / `--groupmember` | **`--source` → `--sourcerpm`、`--groupmember` → `--contains-pkgs`（`group` と `advisory` のサブコマンドへ移動）** |
| **`needs-restarting`** | 開いているファイルを調べる。**`-r` の終了ステータスで判定** | **開いているファイルは調べない。**`reboot_suggested` のアドバイザリを当てたかで判断。**`-r` / `--reboothint` は既定動作になったので削除**。`-u` / `--useronly` も削除 |
| **`config-manager`** | オプション形式（`--add-repo` など） | **サブコマンド形式**（`addrepo` / `setopt` など）。既存の repo ファイルは書き換えず drop-in に書く。**`--dump` は廃止 → `dnf5 --dump-main-config` と `dnf5 --dump-repo-config=REPO_ID`。`--dump-variables` も廃止 → `dnf5 --dump-variables`** |
| **`reposync`** | `--downloadcomps` あり | **廃止。`--download-metadata` を使う**（comps だけでなく全メタデータを取る） |
| **`repoclosure --pkg`** | オプションで指定 | **廃止。位置引数で指定** |
| **`history`** | サブコマンド省略可 | **サブコマンド必須**（`dnf5 history list`） |
| **`versionlock`** | プラグイン | **設定ファイルの書式が変わった** |
| **プラグインのパッケージ** | `dnf-plugins-core` | **`dnf5-plugins`**（**この点は公式の該当ページに記載が無く、未確認**） |

> **dnf-5 で `best` の既定値が `true` になったのが、いちばん影響の大きい変更**です。
> dnf-4 の既定（`False`）のまま書いた手順書を dnf-5 に持っていくと、
> **`install` が勝手に更新する／`upgrade` が依存の壊れた最新版を狙って止まる**という違いが出ます。
> **ただし RHEL 系の実環境では dnf-4 でも `best=True` になっていることが多い**ため、実務上は差が出にくい**可能性があります**。
> **「RHEL が配る `dnf.conf` が `best=True`」という Red Hat 公式の明記は確認できませんでした**（確認日 2026-10-13）。
> 根拠として確認できたのは、**dnf 公式の「ディストリの設定で上書きされうる」という記載**と、
> **Rocky Linux 9 の公式ドキュメントに載っている `/etc/dnf/dnf.conf` が `best=True` であること**だけです。
> **対象サーバで `grep -nE '^best' /etc/dnf/dnf.conf` を打って確かめてください。**

> **RHEL 7（yum-3）との対応表**は [dnf実践④ オフライン環境での適用と切り戻し](./dnf実践④_オフライン環境での適用と切り戻し.md) の末尾にまとめてあります。

---

## RHEL 10 で変わったこと

**RHEL 8 / 9 の手順書を RHEL 10 に持っていくときに効く変更**です。
**出典は項目ごとに違うので、表の「公式の記載」欄に、どのドキュメントの記載かを明記しました。**
**`Considerations`** は「Considerations in adopting RHEL 10」第22章 ソフトウェア管理、
**`10.0 リリースノート`** は「RHEL 10.0 Release Notes — New features and enhancements」です（いずれも 2026-10-13 に確認）。

| 変わったこと | 公式の記載 | 手順書への影響 |
|:--|:--|:--|
| **モジュール機能（Modularity）が非推奨** | **`Considerations`**：**「RHEL 10 では、モジュール機能は非推奨となり、今後のメジャーリリースで削除される予定です。」**／**「したがって、RHEL 10 ではモジュールコンテンツは配布されません。」**／**「そのため、DNF `module` コマンドで非推奨の警告が表示されます。」** | **`dnf module` を使った手順を作り直す** |
| **filelists メタデータが既定で落ちてこない** | **`Considerations`**：**「この更新により、このメタデータはデフォルトでダウンロードされなくなり、応答性が向上し、ディスク領域が節約されます。」**／**「`dnf` コマンドにファイルリストメタデータが必要な場合、またはファイル関連の引数が含まれている場合、メタデータは自動的にロードされます。」** | **`dnf provides /パス` は自動で読み込まれるので動く。**ただし**ファイルパスの依存を解決する必要があるトランザクションは失敗することがある**（`--setopt=optional_metadata_types=filelists` のヒントが出る） |
| **`debug` プラグインが削除** | **`Considerations`**：**「`dnf debug-dump` コマンドと `dnf debug-restore` コマンドが含まれていた DNF `debug` プラグインが、`dnf-plugins-core` パッケージから削除されました。」** | 代わりに **`dnf list --installed` / `dnf repoquery --installed`** で一覧を保存し、`dnf install` に渡して複製する |
| **`libreport` のサポート削除** | **`Considerations`**：**「`libreport` ライブラリーのサポートが DNF から削除されました。」** | DNF のログをバグレポートに添付する手順を自分で用意する |
| **`dnf-plugins-core` が 4.7.0 に** | **`Considerations`**：**「`dnf-plugins-core` パッケージがバージョン 4.7.0 にリベースされ、新しい `python3-dnf-plugin-pre-transaction-actions` パッケージが提供されます。」** | RPM トランザクションの開始時にコマンドを実行できる（`dnf-pre-transaction-actions(8)`） |
| **推奨パッケージ（weak deps）の扱い** | **`10.0 リリースノート`**：**`exclude_from_weak_autodetect`** が既定で有効になり、**更新時は「新しく推奨されたパッケージ」だけ**を入れるようになった（「The `exclude_from_weak_autodetect` option can auto-detect unmet weak dependencies of installed packages」）。`/etc/dnf/dnf.conf` で変更できる | 「更新したら想定外のパッケージが増える」が減る |
| **`needs-restarting --exclude-services`** | **`10.0 リリースノート`**：**「A new `--exclude-services` flag to exclude `systemd` services from the list of stale processes」**。**upstream の `dnf-plugins-core` 公式ドキュメントには載っていない RHEL 固有の追加**（2026-10-13 時点） | 再起動対象から外したいサービスを指定できる |

> **filelists を恒久的に戻す方法も公式に書かれています。**
> **「デフォルトのファイルリストメタデータのダウンロードを再度有効にする場合は、`/etc/dnf/dnf.conf` 設定ファイルの
> `optional_metadata_types` オプションに `filelists` 値を追加します。」**
>
> `optional_metadata_types` の**既定値は空のリスト**です（dnf 公式 Configuration Reference：「Default is an empty list.」）。
>
> ```bash
> $ grep -nE '^optional_metadata_types' /etc/dnf/dnf.conf   # 現在の設定を見る
> $ dnf provides /usr/sbin/sshd                             # ファイル検索は自動でメタデータを読む
> ```

---

## 参考リンク

- [DNF ドキュメント（dnf4）— Command Reference](https://dnf.readthedocs.io/en/latest/command_ref.html)
- [DNF ドキュメント（dnf4）— Configuration Reference](https://dnf.readthedocs.io/en/latest/conf_ref.html)
- [DNF5 ドキュメント — Changes between DNF and DNF5](https://dnf5.readthedocs.io/en/latest/changes_from_dnf4.7.html)（**dnf-4 / dnf-5 差分**の出典）
- [Red Hat — Considerations in adopting RHEL 8 / Software management](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/considerations_in_adopting_rhel_8/software-management_considerations-in-adopting-rhel-8)
- [Red Hat — Considerations in adopting RHEL 9 / Software management](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/considerations_in_adopting_rhel_9/assembly_software-management_considerations-in-adopting-rhel-9)
- [Red Hat — Considerations in adopting RHEL 10 / ソフトウェア管理](https://docs.redhat.com/ja/documentation/red_hat_enterprise_linux/10/html/considerations_in_adopting_rhel_10/software-management)
- [Red Hat — RHEL 10.0 Release Notes / New features（Software management）](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/10.0_release_notes/new-features-and-enhancements)
- [Red Hat — RHEL 10.1 Release Notes / Deprecated features](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/10.1_release_notes/deprecated-features)
- [AWS — Package management tool (Amazon Linux 2023)](https://docs.aws.amazon.com/linux/al2023/ug/package-management.html)

---

[← 全体の目次にもどる](../README.md)
