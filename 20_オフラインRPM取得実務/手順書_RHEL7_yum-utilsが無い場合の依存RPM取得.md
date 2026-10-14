# RHEL 7.9：yum-utils が無い別システムで不足依存RPMを取得する

| | |
|:--|:--|
| **学習の順番** | 実務 ★★★★☆ |
| **Ping-t の範囲** | 範囲外（**業務の実作業から作ったノート**） |
| **業務での使いどころ** | **`yumdownloader` と `repoquery` が使えない別システム**で、足りない依存RPMを調べて取得するときの代わりの手。標準の `yum` だけで、`yum provides` → `yum --showduplicates list` → **`yum install --downloadonly --downloaddir`** の順でやります。**本編の第8章・第9章の差し替え**です。 |

> **このフォルダは「解説」と「手順書」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) | **なぜこの手順になるのか**。`createrepo` と目次、`clean all`、`--assumeno`、**署名検証の落とし穴**、エラータ、yum と dnf の違い |
> | 手順書 | [手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) | `yum` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 8 以降 openssh の更新](./手順書_RHEL8以降_openssh更新.md) | `dnf` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) | `yum` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) | `dnf` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [社内リポジトリ接続機で不足依存RPMを集めて持ち帰る](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md) | **本編。**TeraTerm と WinSCP を使った実作業の通し手順。別システムへ RPM を送る → 足りない依存を下見する → 取得する → 持ち帰る → 対象サーバーであてる前の確認 |
> | **手順書** | **このノート（yum-utils が無い別システムで不足依存RPMを取得する）** | **本編の第8・9章の差し替え。**`yumdownloader` / `repoquery` が無いときに、標準の `yum` だけで調べて取得する |
> | 解説 | [下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) | **`yum install --assumeno` のログの読み方。**行の形ごとの意味、`Error:` の塊の読み方、計画の表と `Transaction Summary` の読み方、よくある読み違い |
> | 手順書 | [対象サーバーでの適用前確認](./手順書_RHEL7_対象サーバーでの適用前確認.md) | 持ち帰った RPM を対象サーバーで確認する（ハッシュ照合 → 下見 → トランザクションテスト → 前後比較）。**実際にあてる手順は含まない** |
> | 解説 | [依存チェックスクリプトの読み方](./依存チェックスクリプトの読み方.md) | `check_deps.sh` を 1 ブロックずつ解説。**元版にあった不具合と、実機で確かめた修正内容** |
>
> **`dnf` / `yum` そのもののコマンド解説**は [07_パッケージ管理](../07_パッケージ管理/dnf解説①_基本とインストール系コマンド.md) にあります。

> **公式ドキュメントの確認日: 2026-10-14。**引用はその時点の記載です。
> **コマンドの実在とメッセージの文字列は、Yum 3 系の公式 man・開発元ソースで確認**しています。
> **RHEL 7.9 の実機で取った出力ではありません。**出力例は「こういう形で出る」という説明用です。

---

## 目次

- [この手順書でやること](#この手順書でやること)
- [1. yum-utils が使えるか判定する](#1-yum-utils-が使えるか判定する)
- [2. 標準 yum での代わり](#2-標準-yum-での代わり)
- [3. 足りないRPMの正体を調べる](#3-足りないrpmの正体を調べる)
  - [3.1 機能名からパッケージ名を探す](#31-機能名からパッケージ名を探す)
  - [3.2 版の候補を並べて選ぶ](#32-版の候補を並べて選ぶ)
  - [3.3 依存をさらにたどる](#33-依存をさらにたどる)
- [4. 足りないRPMを取得する](#4-足りないrpmを取得する)
  - [4.1 取得用の一時フォルダに落とす](#41-取得用の一時フォルダに落とす)
  - [4.2 中身を確認して、採用するものだけ移す](#42-中身を確認して採用するものだけ移す)
  - [4.3 別システムにすでに入っている版を取りたい場合](#43-別システムにすでに入っている版を取りたい場合)
  - [4.4 本編の第7章に戻る](#44-本編の第7章に戻る)
- [この方法の弱点](#この方法の弱点)
- [よく出るメッセージ早見表](#よく出るメッセージ早見表)
- [やってはいけないこと](#やってはいけないこと)
- [公式参照](#公式参照)
  - [この文書の検証範囲](#この文書の検証範囲)
- [変更履歴](#変更履歴)

---

## この手順書でやること

**[本編](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md) の第8章・第9章だけを差し替えます。**
ほかの章（送る・展開する・下見する・持ち帰る・対象サーバーで確認する）は**本編のまま**です。

```text
本編 第7章  下見する（yum install --assumeno）  ← ここは共通
      │
      ├─ yumdownloader / repoquery が使える  → 本編の第8・9章へ
      └─ 使えない                            → **このノート**へ
                                                  │
                                                  │ ① 名前を特定する（yum provides）
                                                  │ ② 版を並べて選ぶ（--showduplicates list）
                                                  │ ③ 取得する（install --downloadonly）
                                                  │ ④ 採用するものだけ $HOME/rpm へ移す
                                                  ▼
本編 第7章  下見する（繰り返し）               ← ここへ戻る
```

**作業場所と変数は本編と同じ**です。別システムにログインし直したら、本編の第3章の `export` をもう一度実行してください。

| 変数 | 値 | 用途 |
|:--|:--|:--|
| `RPM_DIR` | `$HOME/rpm` | **持ち帰る RPM の置き場所** |
| `LOG_DIR` | `$HOME/depcheck_log` | ログの置き場所 |
| `REPO_ID` | `internal-rhel7` | 社内リポジトリのID |

このノートではもう1つ、**取得用の一時フォルダ `$HOME/rpm_dl`** を使います。

---

## 1. yum-utils が使えるか判定する

**まず、どちらのパターンなのかを確定させます。**

```bash
$ rpm -q yum-utils                                   # yum-utils が入っているか
$ which yumdownloader repoquery                      # コマンドの実体があるか
$ yumdownloader --help > /dev/null 2>&1              # 実際に起動するか試す
$ echo "yumdownloader rc=$?"                         # 起動したら 0
$ repoquery --help > /dev/null 2>&1                  # 実際に起動するか試す
$ echo "repoquery rc=$?"                             # 起動したら 0
```

**判定**

| `rpm -q yum-utils` | `which` の結果 | `rc=` | パターン | 進む先 |
|:--|:--|:--|:--|:--|
| パッケージ名が出る | 両方のパスが出る | 両方 `0` | **A：使える** | **[本編の第8章](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md)** へ |
| `package yum-utils is not installed` | 何も出ない | — | **B：使えない** | **このまま第2章へ** |
| パッケージ名は出る | パスは出る | どちらか `0` 以外 | **B 扱い**（壊れている可能性） | 管理者に状況を伝えてから第2章へ |

> **`which` でパスが出るのに `--help` が失敗する**のは、Python の依存が壊れているときなどに起こり得ます。
> **パスの有無だけで判断せず、実際に起動するところまで確認**してください。

**先に相談してほしいこと**

> **いちばん簡単な解決は `sudo yum install yum-utils` で入れてもらうことです。**
> 別システムは社内リポジトリにつながっているので、通常はこれで入ります。
> ただし**別システムへのパッケージ導入は構成変更**なので、**必ず管理者の承認を取ってください。**
> 承認が取れないときに、このノートの手順を使います。

---

## 2. 標準 yum での代わり

| yum-utils が要るもの | 標準 `yum` での代わり | 差がある点 |
|:--|:--|:--|
| `repoquery --whatprovides '条件'` | **`yum provides '機能名'`** | **版の条件（`>= 1:1.0.2k-26`）を渡せない。**名前・ファイル名・ワイルドカードだけ |
| `repoquery --show-duplicates` | **`yum --showduplicates list`** | `info` / `list` / `search` に効く |
| `repoquery` で依存をたどる | **`yum deplist パッケージ名`**、ローカルRPMは `rpm -qpR` | `deplist` は既定で最新版・最新の提供元だけを出す |
| `yumdownloader --destdir DIR` | **`yum install --downloadonly --downloaddir=DIR`** | **別システムに入っているものは落ちない。**依存もまとめて落ちる |

> **`yumdownloader` の `--destdir` は、内部的には `--downloaddir` と同じ設定（`conf.downloaddir`）です。**
> 落ちる場所の指定の仕方は同じで、**違うのは「何を落とすか」の決め方**です。

> **いちばん大きな差は、版の条件で検索できないこと**です。
> そのため **①名前を特定する → ②版を並べる → ③条件を満たす版を人が選ぶ**、という2段構えになります。

---

## 3. 足りないRPMの正体を調べる

本編の第7章の下見で出た **`Requires:` の条件**を手元に置いて始めます。
例：`Requires: openssl-libs >= 1:1.0.2k-26` や `Requires: libcrypto.so.10()(64bit)`

### 3.1 機能名からパッケージ名を探す

```bash
$ yum --disablerepo='*' --enablerepo=$REPO_ID provides 'libcrypto.so.10()(64bit)' \
    > $LOG_DIR/provides_01.txt 2>&1          # 機能を提供するパッケージを探す
$ cat $LOG_DIR/provides_01.txt               # 結果を見る
```

**表示例**（説明用です）

```text
openssl-libs-1:1.0.2k-26.el7_9.x86_64 : A general purpose cryptography library
Repo        : internal-rhel7
```

**1件ごとに「NEVRA : 概要」の行と `Repo` の行が出ます。**ここで知りたいのは**パッケージ名**（この例なら `openssl-libs`）です。

> **`provides` に版の条件を書かないでください。**
> `yum provides 'openssl-libs >= 1:1.0.2k-26'` は使えません。
> 公式 man も「**specific name or a file-glob-syntax wildcards**」と書いています。
> **条件の左側（機能名・ファイル名）だけ**を渡します。

条件が `openssl-libs >= 1:1.0.2k-26` のように**最初からパッケージ名**なら、この節は飛ばして 3.2 へ進めます。

**見つからないときは、カッコを外して探します。**

```bash
$ yum --disablerepo='*' --enablerepo=$REPO_ID provides 'libcrypto.so.10'   # カッコを外して探す
$ yum --disablerepo='*' --enablerepo=$REPO_ID provides '*/libcrypto.so.10'   # ファイルパスとして探す
```

> **`()(64bit)` は「64bit 版である」という印**です。外して探したときは、
> 見つかった RPM の**アーキテクチャが `x86_64` であること**を必ず確認してください。

### 3.2 版の候補を並べて選ぶ

```bash
$ yum --disablerepo='*' --enablerepo=$REPO_ID --showduplicates list all openssl-libs \
    > $LOG_DIR/versions_01.txt 2>&1          # 利用できる版を全部並べる
$ cat $LOG_DIR/versions_01.txt               # 結果を見る
```

**表示例**（説明用です）

```text
Available Packages
openssl-libs.x86_64      1:1.0.2k-25.el7_9      internal-rhel7
openssl-libs.x86_64      1:1.0.2k-26.el7_9      internal-rhel7
openssl-libs.x86_64      1:1.0.2k-27.el7_9      internal-rhel7
```

**左から、パッケージ名.アーキテクチャ／Epoch:Version-Release／リポジトリID** です。
ここから、**`Requires:` の条件を満たし、対象サーバーと同じ `el7` のもの**を選びます。

> **`list all` にしている理由**：`list available` は**別システムにすでに入っている版を除いて**表示します。
> `all` なら `Installed Packages` と `Available Packages` の両方が出るので、
> **「必要な版が、別システムに入っているせいで候補から消えている」**状況に気づけます。

> **`--showduplicates` が無いと最新版しか出ません。**条件が「ちょうどこの版」のときに取り違えます。

**選ぶときのコツ**（本編と同じです）

- ファイル名に **対象サーバーと同じ `el7`** が入っているもの
- 条件が `()(64bit)` 付きなら **`x86_64` 版**
- **同じエラータ（RHSA）に入っている仲間はまとめて取る**（`openssl` と `openssl-libs` など）

### 3.3 依存をさらにたどる

```bash
$ rpm -qpR $RPM_DIR/openssh-server-7.4p1-23.el7_9.x86_64.rpm   # RPMファイルが要求する条件
$ yum --disablerepo='*' --enablerepo=$REPO_ID deplist openssh-server \
    > $LOG_DIR/deplist_01.txt 2>&1           # 依存と提供元をまとめて見る
$ head -n 20 $LOG_DIR/deplist_01.txt         # 先頭を見る
```

**表示例**（説明用です）

```text
package: openssh-server-7.4p1-23.el7_9.x86_64
  dependency: libcrypto.so.10()(64bit)
   provider: openssl-libs-1:1.0.2k-26.el7_9.x86_64
```

**`dependency:` が「要求している条件」、`provider:` が「それを提供する RPM」**です。

> **`deplist` は既定で「最新版だけ・最新の提供元だけ」を出します。**
> すべて見たいときは `--showduplicates` を、提供元を全部見たいときは `-v` を足してください（`yum.8` に明記）。

> **`rpm -qpR` は RPM ファイルを直接読む**ので、リポジトリにもサーバーにも依存しません。
> **「このファイルが何を欲しがっているか」を確実に知りたいときは `rpm -qpR`** が確実です。

---

## 4. 足りないRPMを取得する

### 4.1 取得用の一時フォルダに落とす

**`$HOME/rpm` には直接落としません。**必ず別のフォルダに落として、中身を見てから移します。

```bash
$ mkdir -p $HOME/rpm_dl                      # 取得用の一時フォルダを作る
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID \
    --downloadonly --downloaddir=$HOME/rpm_dl install 'openssl-libs-1:1.0.2k-26.el7_9' \
    > $LOG_DIR/download_01.txt 2>&1          # インストールせずにダウンロードだけする
$ echo "exit code: $?"                       # 終了コードを見る
$ cat $LOG_DIR/download_01.txt               # 結果を見る
$ ls -l $HOME/rpm_dl                         # 落ちたファイルを見る
```

**期待値**：ログの最後に **`exiting because "Download Only" specified`** が出て、`$HOME/rpm_dl` に RPM が増えている

| 指定 | 意味 |
|:--|:--|
| `--downloadonly` | **インストールせず、ダウンロードだけして終了する** |
| `--downloaddir=DIR` | 落とす先。**指定しないと `/var/cache/yum` の下**に入る |
| `install 'NEVRA'` | 版まで指定して「これを入れるとしたら何が要るか」を解決させる |

> **`--downloadonly` は確認プロンプトを出しません。**
> Yum は `--downloadonly` が付いているとき、**`-y` を付けたのと同じ扱い**で確認を省きます。
> **`--assumeno` を足してはいけません。**中止になって何も落ちません。
> **計画そのものは、本編の第7章の下見ログ（`dryrun_*.txt`）で先に確認しておいてください。**

> **依存もまとめて落ちます。**指定した1個だけではなく、**その依存として必要な RPM も一緒に**落ちます。
> 便利ですが、**対象サーバーに要らないものまで混ざる**ので、次の 4.2 で選別します。

❌ `Nothing to do` / `Package ... already installed and latest version` と出た
　→ **その版が別システムにすでに入っています。**何も落ちません。4.3 へ。

❌ `No such option: --downloadonly` と出た
　→ ごく古い Yum では別パッケージ（`yum-plugin-downloadonly`）が必要な場合があります。
　 `yum --help` の出力に `--downloadonly` があるか確認し、無ければ管理者に相談してください。

### 4.2 中身を確認して、採用するものだけ移す

```bash
$ ls $HOME/rpm_dl/*.rpm                      # 落ちたものを一覧する
$ rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' $HOME/rpm_dl/*.rpm   # NEVRA を確認する
$ mv $HOME/rpm_dl/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm $RPM_DIR/   # 採用するものだけ移す
$ ls $RPM_DIR/*.rpm | wc -l                  # 本編の RPM 置き場の件数
$ ls $HOME/rpm_dl                            # 残ったものを確認する
```

**期待値**：`$RPM_DIR` の件数が、移した数だけ増えている

> **`mv $HOME/rpm_dl/*.rpm $RPM_DIR/` とまとめて移さないでください。**
> **意図しない依存まで持ち帰ることになります。**採用の判断は 1 件ずつして、**理由を台帳に記録**します。

> **`$HOME/rpm_dl` に残ったものは消さなくてよい**です。
> 「何が落ちてきて、何を採用しなかったか」が証跡になります。片付けは承認後にします。

### 4.3 別システムにすでに入っている版を取りたい場合

```bash
$ rpm -q openssl-libs                        # 別システムに入っている版を見る
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID \
    --downloadonly --downloaddir=$HOME/rpm_dl reinstall openssl-libs \
    > $LOG_DIR/download_reinstall.txt 2>&1   # 導入済みと同じ版をダウンロードする
$ echo "exit code: $?"                       # 終了コードを見る
$ ls -l $HOME/rpm_dl                         # 落ちたファイルを見る
```

**期待値**：`rpm -q` で出た版と同じ NEVRA の RPM が `$HOME/rpm_dl` に落ちている

> **`reinstall` で取れるのは「いま別システムに入っているのと同じ版」だけ**です（`yum.8`：
> "Will reinstall the identically versioned package as is currently installed"）。
> **対象サーバーに必要な版がそれと違うなら、この方法では取れません。**
> その場合は **管理者に `yum-utils` の導入を依頼**するか、**社内リポジトリから直接ファイルを受け取る**ことを相談してください。

> **`reinstall` はカーネルなどの installonly パッケージには使えません**（`yum.8` に明記）。
> カーネル関連が必要なときは、この方法では取れないと考えてください。

### 4.4 本編の第7章に戻る

**RPM を追加したら、必ず本編の下見をやり直します。**

```bash
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID install --assumeno $RPM_DIR/*.rpm \
    > $LOG_DIR/dryrun_02.txt 2>&1            # 次の回の下見（ファイル名の番号を変える）
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 20 $LOG_DIR/dryrun_02.txt          # 結果を見る
```

**`Exiting on user command` になるまで、第3章 → 第4章 → この下見を繰り返します。**
**そろったら、本編の第10章（持ち帰り用にまとめる）へ進みます。**

---

## この方法の弱点

**本編（`yumdownloader` が使える場合）より弱い点を、作業前に把握しておいてください。**

| 弱点 | 内容 | 対処 |
|:--|:--|:--|
| **版の条件で検索できない** | `yum provides` は名前・ファイル名・ワイルドカードだけ。`>= 1:1.0.2k-26` は渡せない | 名前を特定 → `--showduplicates list all` で版を並べて**人が選ぶ** |
| **別システムに入っているものは落ちない** | `--downloadonly` は「入っていないもの」だけを落とす | 同版でよければ `reinstall --downloadonly`。**違う版は取れない** |
| **余計な依存までまとめて落ちる** | 指定した1個だけでなく、トランザクション全体が落ちる | `$HOME/rpm_dl` に落として、**採用するものだけ `mv`** |
| **確認プロンプトが出ない** | `--downloadonly` は `-y` 相当として扱われる | **本編の第7章の下見で、先に計画を確認しておく** |
| **カーネル関連が取りにくい** | installonly パッケージは `reinstall` できない | 管理者に相談する |

> **これらはどれも「別システムの導入状態に引きずられる」という同じ原因から来ています。**
> だからこそ、**最終判断は対象サーバーでの結果**（本編の第12章）を使います。
> 別システムで「足りないものなし」になっても、**対象サーバーでは足りないことがあります。**

---

## よく出るメッセージ早見表

| 表示 | 意味 | 次にやること |
|:--|:--|:--|
| `exiting because "Download Only" specified` | ✅ ダウンロードだけして正常終了した | `ls` で落ちたファイルを確認する |
| `Background downloading packages, then exiting:` | ダウンロードを始めた | そのまま待つ |
| `Package ... already installed and latest version` | その版が別システムに入っている | 4.3 の `reinstall --downloadonly` へ |
| `Nothing to do` | 落とすものが無かった | 版の指定、リポジトリID、すでに入っていないかを確認 |
| `No package ... available` | 指定した NEVRA が見えない | `--showduplicates list all` で実際の版を確認 |
| `No such option: --downloadonly` | その Yum に `--downloadonly` が無い | `yum --help` で確認し、管理者に相談 |
| `Error: Nothing to download` | 対象が解決できなかった | 名前・版・アーキテクチャの指定を見直す |
| `Cannot find a valid baseurl` | リポジトリへの接続・認証の問題 | **依存不足と混同しない。**本編の第6章へ |

---

## やってはいけないこと

| やってはいけないこと | 理由 |
|:--|:--|
| **`--downloadonly` に `--assumeno` を足す** | 中止扱いになって**何も落ちない** |
| **`$HOME/rpm` に直接ダウンロードする** | 意図しない依存が持ち帰る中身に混ざる |
| **`mv $HOME/rpm_dl/*.rpm $RPM_DIR/`** | 同上。**1件ずつ判断して移す** |
| **`yum provides` に版の条件を渡す** | 使えない書き方。**機能名だけ**を渡す |
| **`--showduplicates` を省く** | 最新版しか出ず、必要な版を取り違える |
| **承認なしで `yum install yum-utils` を実行する** | 別システムへの構成変更になる |
| **`yum update` / `yum install` を `--downloadonly` 無しで実行する** | **別システムが実際に更新されてしまう** |

---

## 公式参照

**開発元の文書には RHEL 7 に無い機能も含まれ得ます。**実行前に導入済み版の `man yum` と `yum --help` でも確認してください。

| 資料 | 本書で確認した内容 |
|:--|:--|
| [Yum開発元：yum(8)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.8) | **`--downloadonly`（"Don't update, just download."）と `--downloaddir=directory`**、`provides` / `whatprovides`（"a specific name or a file-glob-syntax wildcards"）、`--showduplicates`（info / list / search に効く）、`deplist`（既定で最新版・最新の提供元のみ）、`reinstall`（同一版のみ・installonly 不可） |
| [Yum開発元：yum.conf(5)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.conf.5) | `assumeno`、`alwaysprompt` |
| [Yum Utils開発元：yumdownloader(1)](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/yumdownloader.1) | `--destdir` が `conf.downloaddir` と同じ仕組みであること |
| [Red Hat：RHEL 7 System Administrator's Guide — Yum](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-yum) | RHEL 7 の Yum、パッケージの検索と取得 |

### この文書の検証範囲

**公式 man と開発元ソースで確認した事項**：`--downloadonly` と `--downloaddir` が**プラグインではなく Yum 本体のオプション**であること（`cli.py` のオプション定義と `conf.downloaddir` の参照）／
**`--downloadonly` が付くと確認プロンプトを出さない**こと（`_promptWanted()` が `downloadonly` のとき False を返す）／
完了時のメッセージが **`exiting because "Download Only" specified`** であること／
`yum provides` が版の条件ではなく名前・ファイル glob を取ること／`reinstall` が同一版のみで installonly に使えないこと。

**RHEL 7.9 の実機では未実行**です。**出力例は説明用**で、実機の出力ではありません。
`yum provides` と `deplist` の表示の細かな体裁は、版によって異なる場合があります。

---

## 変更履歴

| 日付 | 版 | 内容 |
|:--|:--|:--|
| 2026-10-14 | 1.0 | 初版。本編（[社内リポジトリ接続機で不足依存RPMを集めて持ち帰る](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md)）の第8・9章の差し替えとして新設。**`yum-utils` が使えるかの判定**、`yum provides` → `yum --showduplicates list all` → **`yum install --downloadonly --downloaddir`** の流れ、`reinstall --downloadonly` による同一版の取得、この方法の弱点を記載 |

---

[← 全体の目次にもどる](../README.md)
