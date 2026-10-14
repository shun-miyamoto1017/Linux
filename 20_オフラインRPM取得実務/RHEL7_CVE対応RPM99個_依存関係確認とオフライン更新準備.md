# RHEL 7.9：社内リポジトリ接続機で不足依存RPMを集めて持ち帰る

| | |
|:--|:--|
| **学習の順番** | 実務 ★★★★★ |
| **Ping-t の範囲** | 範囲外（**業務の実作業から作ったノート**） |
| **業務での使いどころ** | **CVE対応で自分が用意したRPMを、社内リポジトリにつながる別システムへ持ち込んで、足りない依存RPMを集めて持ち帰るまでの通し手順。**TeraTerm でログインし、WinSCP でファイルを行き来させる前提。**スクリプトは使わず、全部1行ずつのコマンドです。** |

> **このフォルダは「解説」と「手順書」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) | **なぜこの手順になるのか**。`createrepo` と目次、`clean all`、`--assumeno`、**署名検証の落とし穴**、エラータ、yum と dnf の違い |
> | 手順書 | [手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) | `yum` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 8 以降 openssh の更新](./手順書_RHEL8以降_openssh更新.md) | `dnf` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) | `yum` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) | `dnf` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | **手順書** | **このノート（社内リポジトリ接続機で不足依存RPMを集めて持ち帰る）** | **TeraTerm と WinSCP を使った実作業の通し手順。**別システムへ RPM を送る → 足りない依存を下見する → 取得する → 持ち帰る → 対象サーバーであてる前の確認 |
> | 解説 | [依存チェックスクリプトの読み方](./依存チェックスクリプトの読み方.md) | `check_deps.sh` を 1 ブロックずつ解説。**元版にあった不具合と、実機で確かめた修正内容** |
>
> **`dnf` / `yum` そのもののコマンド解説**は [07_パッケージ管理](../07_パッケージ管理/dnf解説①_基本とインストール系コマンド.md) にあります。

> **公式ドキュメントの確認日: 2026-10-14。**引用はその時点の記載です。
> **コマンドの実在とメッセージの文字列は、Yum 3 系と RPM 4.11 系の公式 man・開発元ソースで確認**しています。
> **RHEL 7.9 の実機で取った出力ではありません。**出力例は「こういう形で出る」という説明用です。
> 本番作業の前に、対象サーバーの `man yum` と `--help` でも裏を取ってください。

---

## 目次

- [この手順書でやること](#この手順書でやること)
- [最初に知っておくこと](#最初に知っておくこと)
  - [NEVRA（名前と版の正式な書き方）](#nevra名前と版の正式な書き方)
  - [なぜ「別システム」が必要なのか](#なぜ別システムが必要なのか)
- [1. 手元のWindowsでRPMをまとめる](#1-手元のwindowsでrpmをまとめる)
- [2. TeraTermで別システムにログインする](#2-teratermで別システムにログインする)
- [3. 作業フォルダと変数を用意する](#3-作業フォルダと変数を用意する)
- [4. WinSCPでアーカイブを送る](#4-winscpでアーカイブを送る)
- [5. アーカイブを展開する](#5-アーカイブを展開する)
- [6. 社内リポジトリを確認する](#6-社内リポジトリを確認する)
- [7. 足りない依存を下見する](#7-足りない依存を下見する)
  - [結果の読み方](#結果の読み方)
  - [黙って外されたRPMがないか確認する](#黙って外されたrpmがないか確認する)
  - [/tmp に残るファイルの注意](#tmp-に残るファイルの注意)
- [8. 足りないRPMの正体を調べる](#8-足りないrpmの正体を調べる)
  - [カッコ付きの記号は外して調べる](#カッコ付きの記号は外して調べる)
- [9. 足りないRPMを取得する](#9-足りないrpmを取得する)
  - [取得したら必ず7に戻る](#取得したら必ず7に戻る)
  - [参考 --resolve でまとめて取る場合](#参考---resolve-でまとめて取る場合)
- [10. 持ち帰り用にまとめる](#10-持ち帰り用にまとめる)
- [11. WinSCPで持ち帰る](#11-winscpで持ち帰る)
- [12. 対象サーバーであてる前の確認](#12-対象サーバーであてる前の確認)
  - [12.1 下見する](#121-下見する)
  - [12.2 トランザクションテストをする](#122-トランザクションテストをする)
  - [12.3 ここで確認できないこと](#123-ここで確認できないこと)
- [よく出るメッセージ早見表](#よく出るメッセージ早見表)
- [やってはいけないこと](#やってはいけないこと)
- [記録表](#記録表)
  - [下見のラウンド記録](#下見のラウンド記録)
  - [追加したRPMの台帳](#追加したrpmの台帳)
  - [保存されるファイル](#保存されるファイル)
  - [完了条件](#完了条件)
- [公式参照](#公式参照)
  - [この文書の検証範囲](#この文書の検証範囲)
- [変更履歴](#変更履歴)

---

## この手順書でやること

**自分で用意した CVE 対応 RPM を、社内リポジトリにつながる別システムへ持ち込み、足りない依存 RPM を集めて持ち帰ります。**
**どのシステムにもインストールはしません。**下見（`--assumeno`）とダウンロードだけです。

| 呼び名 | 何をする場所 | 接続方法 |
|:--|:--|:--|
| **手元のWindows** | RPM をまとめる。持ち帰った RPM を保管する | — |
| **別システム** | 社内リポジトリにつながる RHEL 7.9。**足りない依存RPMを取得する** | TeraTerm（コマンド）／WinSCP（ファイル） |
| **対象サーバー** | 更新したいオフラインの本番機。**あてる前の確認だけ**する | 社内で承認された方法 |

```text
手元のWindows
  │  ① RPM を1つのフォルダに集めて tar.gz にする
  ├──[WinSCP で送る]──▶ 別システム $HOME/rpm
  │                        │ ② tar.gz を展開する
  │                        │  ┌─▶ ③ 下見する（yum install --assumeno）
  │                        │  │       ├─ 足りないものなし ──────┐
  │                        │  │       └─ Requires: が出た       │
  │                        │  │   ④ 正体を調べる（repoquery）   │
  │                        │  │   ⑤ 取得する（yumdownloader）   │
  │                        │  └───┘（③に戻る）                  │
  │                        │ ⑥ 持ち帰り用に tar.gz にまとめる ◀──┘
  ◀──[WinSCP で持ち帰る]───┘
  │  ⑦ ハッシュ値を照合して保管する
  └──[承認された方法で送る]──▶ 対象サーバー
                                ⑧ あてる前の確認（下見 → トランザクションテスト）
```

**人が判断するのは ④ だけ**です。ほかは決まったコマンドを打つだけです。

> **別システムと対象サーバーは、入っているパッケージが違います。**
> 別システムで「足りないものなし」になっても、**対象サーバーでは足りないことがあります。**
> **最終判断は必ず対象サーバーでの結果を使います**（第12章）。

---

## 最初に知っておくこと

**RPM** は、プログラム・設定ファイル・依存条件が1つにまとまった配布ファイルです。
**依存関係**は「このプログラムを動かすには別の機能が必要」という条件で、
**リポジトリ**は RPM 本体と**目次（`repodata/`）**を置いた場所です。

```text
更新したいRPM
  ├─ libexample.so.1()(64bit) が必要
  │     └─ example-libs RPM がその機能を「提供」している
  └─ example-common = 1.2-3.el7 が必要
        └─ 同じバージョンの example-common RPM が必要
```

> **`libexample.so.1()(64bit)` は RPM のファイル名ではありません。RPM が「提供する機能の名前」です。**
> エラーの文字列をそのままファイル名だと思って探しても見つかりません。
> **「この機能を提供しているのはどの RPM か」を調べる**のが第8章です。

### NEVRA（名前と版の正式な書き方）

RPM を正確に指すときは **NEVRA**（Name・Epoch・Version・Release・Architecture）を使います。
例：**`openssl-libs-1:1.0.2k-26.el7_9.x86_64`**（Epoch が `1`、Version が `1.0.2k`、Release が `26.el7_9`）

> **Epoch は版の比較でいちばん強い数値です。**
> **Epoch が違えば、Version や Release の大小に関係なく Epoch の大きいほうが新しい**と判断されます。
> 未設定は通常 0 相当で、**ファイル名には入りません。**
> だから **ファイル名の文字の並びだけで「こっちが新しい」と判断してはいけません。**

### なぜ「別システム」が必要なのか

対象サーバーはオフラインなので、社内リポジトリから RPM を取れません。
そこで、**社内リポジトリにつながる同じ RHEL 7.9 の別システムを「取得係」として使います。**
別システムでやるのは**「足りない依存 RPM を探して、ファイルとして取ってくる」だけ**で、
**別システム自身にはインストールしません。**

---

## 1. 手元のWindowsでRPMをまとめる

**RPM を1つのフォルダに集めて、`tar.gz` という形式の1ファイルにします。**

```text
C:\work\rpm\  ← このフォルダに RPM を全部入れる
   openssh-7.4p1-23.el7_9.x86_64.rpm
   openssh-server-7.4p1-23.el7_9.x86_64.rpm
```

PowerShell を開いて実行します。

```powershell
cd C:\work                                  # rpm フォルダの1つ上へ移動する
tar --version                               # tar コマンドが使えるか確認する
tar -czf rpm.tar.gz rpm                     # rpm フォルダを rpm.tar.gz にまとめる
dir rpm.tar.gz                              # できたファイルのサイズを確認する
Get-FileHash -Algorithm SHA256 rpm.tar.gz   # ハッシュ値を控える
```

**期待値**：`rpm.tar.gz` ができてサイズが 0 ではない。**`Hash` 欄の値をメモしておく**（転送後の照合に使います）。

> **`tar` が使えないと言われたら**、7-Zip などで `tar.gz` を作ってください。
> **`.zip` は避けたほうが安全**です。展開に `unzip` が必要で、RHEL 7 に入っていないことがあります。
> **RPM は圧縮済みなので小さくはなりません。**小さくするためではなく、
> **1ファイルにまとめて転送の抜けを防ぐ**ためにやっています。

---

## 2. TeraTermで別システムにログインする

1. TeraTerm を起動して「新しい接続」
2. **ホスト**に別システムの IP かホスト名
3. **サービス**は **SSH**、**SSHバージョン**は **SSH2** を選んで「OK」
4. ユーザー名とパスワード（または鍵）を入れて「OK」

ログインできたら、**まず自分がどこにいるかを確認します。**

```bash
$ whoami                         # 今のユーザー名
$ hostname                       # 今いるサーバー名
$ cat /etc/redhat-release        # OS の版
$ rpm -E 'el%{rhel}'             # メジャーバージョンの記号
$ uname -m                       # CPU アーキテクチャ
$ echo $HOME                     # 自分のホームディレクトリ
```

**期待値**

| コマンド | 期待する表示 |
|:--|:--|
| `hostname` | **別システム**の名前（対象サーバーではないこと） |
| `cat /etc/redhat-release` | `Red Hat Enterprise Linux Server release 7.9 (Maipo)` |
| `rpm -E 'el%{rhel}'` | **`el7`** |
| `uname -m` | 対象サーバーと同じ（通常 `x86_64`） |

> **いちばん多い事故が「サーバーを間違える」ことです。`hostname` を必ず見てから**先に進んでください。

次に、必要な道具がそろっているか確認します。

```bash
$ rpm -q yum yum-utils           # yum と yum-utils が入っているか
$ which yumdownloader repoquery  # 取得と検索のコマンドがあるか
$ which tar sha256sum            # まとめる・ハッシュを取る道具があるか
```

**期待値**：すべてパスかパッケージ名が表示される

❌ `yum-utils` が `not installed` → **`yumdownloader` と `repoquery` が使えません。**管理者へ導入を依頼してください。
　**この手順書では道具の導入はしません。**

---

## 3. 作業フォルダと変数を用意する

**作業フォルダは2つだけです。`$HOME/rpm` に RPM、`$HOME/depcheck_log` にログを置きます。**

```bash
$ export LANG=C                              # yum の出力を英語にする
$ export RPM_DIR=$HOME/rpm                   # RPM を置く場所
$ export LOG_DIR=$HOME/depcheck_log          # ログを置く場所
$ export REPO_ID=internal-rhel7              # 社内リポジトリのID（第6章で確認する）
$ mkdir -p $RPM_DIR                          # RPM 置き場を作る
$ mkdir -p $LOG_DIR                          # ログ置き場を作る
$ ls -ld $RPM_DIR $LOG_DIR                   # 2つできたか確認する
```

**期待値**：`$HOME/rpm` と `$HOME/depcheck_log` の2行が表示される

> **`$HOME` の下に作る理由は、別システムに影響を出さないためです。**
> `/opt` や `/var/tmp` は他の人や他の作業と共用になりがちですが、**自分のホームならぶつかりません。**root 権限も要りません。
> **`$HOME/rpm` には RPM だけ、`$HOME/depcheck_log` にはログだけ**を置いてください。混ぜると持ち帰る中身が汚れます。

> **SSH を切って入り直したら、この `export` を全部もう一度実行してください。**
> `export` の値は**その接続の中だけ**で有効です。面倒なら `$HOME/rpm` とフルで打っても結果は同じです。
> **`LANG=C`** は、RHEL 7 の日本語環境だと **yum のメッセージが日本語になる**ためです。
> 本書やネット上の情報は英語前提なので、**英語にそろえたほうが調べやすく `grep` もしやすい**です。

---

## 4. WinSCPでアーカイブを送る

1. WinSCP を起動して「新しいセッション」
2. **転送プロトコル**を **SFTP**、**ホスト名**に別システムの IP かホスト名
3. ユーザー名とパスワード（または鍵）を入れて「ログイン」
4. 画面が左右に分かれる。**左が手元の Windows、右が別システム**
5. **右側のパス欄に `/home/ユーザー名/rpm` を入れて移動**する
6. 左側で `C:\work\rpm.tar.gz` を選び、**右へドラッグする**

> **転送モードは「バイナリ」にしてください。**「オプション」→「環境」→「転送」で**「バイナリ」**を選びます。
> **「テキスト」で転送すると改行コードが書き換えられて、RPM やアーカイブが壊れます。**

転送が終わったら、**TeraTerm 側で届いたことを確認します。**

```bash
$ ls -l $RPM_DIR                             # 届いたファイルを見る
$ sha256sum $RPM_DIR/rpm.tar.gz              # ハッシュ値を計算する
```

**期待値**：サイズが手元の `dir` と同じで、**ハッシュ値が第1章でメモした値と一致する**

❌ **ハッシュ値が違う** → 転送中に壊れています。**転送モードがバイナリか確認して送り直してください。**

---

## 5. アーカイブを展開する

```bash
$ cd $RPM_DIR                                # RPM 置き場へ移動する
$ tar -tzf rpm.tar.gz                        # 中身を一覧する（まだ展開しない）
$ tar -xzf rpm.tar.gz                        # 展開する
$ ls -l                                      # 何ができたかを見る
```

`tar` のオプションは **`-t` が一覧、`-x` が展開、`-c` が作成、`-z` が gzip、`-f` がファイル名の指定**です。

> **展開する前に必ず `-tzf` で中身を見てください。**
> **絶対パス（先頭が `/`）や `../` が入っていたら展開しないでください。**想定外の場所にファイルが置かれます。

第1章のやり方だと `rpm` というフォルダの中に展開されます。**RPM を `$HOME/rpm` の直下に移します。**

```bash
$ ls $RPM_DIR/rpm/*.rpm | wc -l              # 展開されたフォルダの中の RPM の数
$ mv $RPM_DIR/rpm/*.rpm $RPM_DIR/            # 直下へ移す
$ rmdir $RPM_DIR/rpm                         # 空になったフォルダを消す
$ rm -f $RPM_DIR/rpm.tar.gz                  # 送ってきたアーカイブを消す
$ ls $RPM_DIR/*.rpm | wc -l                  # 直下の RPM の数を数える
```

**期待値**：最後の数が、**手元で用意した RPM の数と一致する**

❌ **数が合わない** → 転送の抜けか、`tar` の作り方が違います。第1章からやり直してください。

**RPM の中身を一覧にして、ログ側に記録しておきます。**

```bash
$ rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' $RPM_DIR/*.rpm \
    > $LOG_DIR/original-inventory.tsv        # NEVRA の一覧を保存する
$ cat $LOG_DIR/original-inventory.tsv        # 内容を確認する
$ wc -l $LOG_DIR/original-inventory.tsv      # 行数＝RPM の数
```

**表示例**（説明用です）

```text
openssh         (none)  7.4p1   23.el7_9        x86_64
openssh-server  (none)  7.4p1   23.el7_9        x86_64
```

列は名前・Epoch・Version・Release・Architecture で、**`(none)` は Epoch が未設定**という意味です。

> **`-qp` と `-q` の違いは大事です。`-p / --package` が付いていれば「RPM ファイルを見ている」、**
> **付いていなければ「サーバーに入っているものを見ている」**です。
> なお **RPM の数と CVE の数は対応しません。**1つの CVE 対応に複数の RPM が必要なこともあり、その逆もあります。

---

## 6. 社内リポジトリを確認する

**使うリポジトリは `/etc/yum.repos.d/internal-rhel7.repo` です。**

```bash
$ cat /etc/yum.repos.d/internal-rhel7.repo          # 設定の中身を見る
$ grep '^\[' /etc/yum.repos.d/internal-rhel7.repo   # リポジトリIDを取り出す
$ ls /etc/yum.repos.d/                              # ほかにどんな .repo があるか
```

**期待値**：`grep` の結果が `[internal-rhel7]` のような1行

> **`[ ]` で囲まれた部分が「リポジトリID」**で、**ファイル名とは別物**です。
> ここで出た ID を第3章の `REPO_ID` に設定します。違っていたら `export REPO_ID=実際のID` で入れ直してください。

**このリポジトリだけを有効にして、つながるか確認します。**

```bash
$ yum --disablerepo='*' --enablerepo=$REPO_ID repolist -v \
    > $LOG_DIR/repolist.txt 2>&1                    # 詳しい情報をログに保存する
$ grep -E 'Repo-id|Repo-name|Repo-baseurl|Repo-pkgs|Repo-status' $LOG_DIR/repolist.txt   # 要点だけ見る
```

**期待値**：`Repo-id` が指定した ID、`Repo-pkgs` が 0 ではない、`Repo-baseurl` が社内のサーバーを指している

❌ `Cannot find a valid baseurl` → **リポジトリへの接続・認証の問題**です。依存不足とは別の話なので混同しないでください。

**`--disablerepo='*'` は「その呼び出しだけ全リポジトリを無効にする」、`--enablerepo=ID` は「指定した ID だけ有効に戻す」**指定です。

> **`'*'` をシングルクォートで囲む理由**：囲まないと**シェルが `*` をカレントディレクトリのファイル名に展開**してしまいます。
> `yum` に `*` という文字をそのまま渡すために囲みます。

> **設定ファイルは書き換えません。**`--disablerepo` / `--enablerepo` は**その1回のコマンドにだけ効く**指定で、
> 恒久的な `.repo` の作成や `createrepo` も、この手順では不要です。

> **このリポジトリは `gpgcheck=0` なので、本手順に署名検証（`rpm -K`）は入れていません。**
> ただし **`localpkg_gpgcheck` も既定が `0`** なので、**自分が持ち込んだ RPM の署名も検査されません。**
> **社内リポジトリ以外から入手した RPM を混ぜる場合は、入手元の確認を別途行ってください。**
> 署名検証そのものの話は [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) にあります。

---

## 7. 足りない依存を下見する

**ここが本体です。**`--assumeno` を付けて、**「もし入れたらどうなるか」だけを表示させます。**

```bash
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID install --assumeno $RPM_DIR/*.rpm \
    > $LOG_DIR/dryrun_01.txt 2>&1            # 下見の結果をログに保存する
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 20 $LOG_DIR/dryrun_01.txt          # ログの最後を見る
```

**なぜこの形なのか**

| 指定 | 理由 |
|:--|:--|
| `install` に**ファイルパス**を渡す | `yum` は**ファイル名を渡されるとローカルインストールとして扱う**（`yum.8` に明記）。`localinstall` は公式に「互換のため残しているだけ」とされているので `install` を使う |
| **1個ずつでなく全部まとめて**渡す | 1個ずつ試すと、**同時に入れる別の RPM が条件を満たす関係を「不足」と誤判定**する |
| `--assumeno` | 確認に自動で「いいえ」と答える。**実更新を絶対にしない** |
| `--enablerepo=$REPO_ID` | **社内リポジトリを使って依存を解決させる。**ここが「足りないものを埋める候補」になる |
| `> ファイル 2>&1` | 出力が長く画面では読めない。`2>&1` で**エラー出力も同じファイルへ**送る |
| `sudo` | yum は**下見でも root 権限が必要**（ロックやキャッシュを触るため） |

### 結果の読み方

| 最後に出ている文 | 意味 | 次にやること |
|:--|:--|:--|
| **`Exiting on user command`** | ✅ **依存はそろっている**（`--assumeno` で中止した正常終了） | 第10章へ |
| **`Error: Package: ...` ＋ `Requires: xxx`** | ❌ **依存が足りない** | 第8章へ |
| **`Protected multilib versions`** | ❌ **32bit 版と 64bit 版の版ずれ** | **i686 版も同じ版で取得する** |
| **`Nothing to do`** | ⚠️ **やることが無い** | RPM の取り違え、`el7` 以外の混入、別システムに同版が入っている |
| **`Cannot find a valid baseurl`** | ❌ リポジトリへの接続・認証の問題 | 第6章に戻る |

> **`Exiting on user command` は「成功」です。**
> `--assumeno` で確認を「いいえ」にしたので、**Yum が「ユーザーの指示で終了した」と言っているだけ**です。
> **このとき終了コードは 1 になります。**終了コードだけ見て「失敗した」と思わないでください。
> **`Operation aborted.` は RHEL 8 以降の `dnf` の表示で、RHEL 7 の `yum` では出ません。**

💡 `This system is not registered with an entitlement server.` は**無視してよい**です。

**足りないものの一覧を出します。**

```bash
$ grep 'Requires:' $LOG_DIR/dryrun_01.txt | sort -u   # 足りない条件を重複なしで並べる
$ grep -A2 'Error: Package:' $LOG_DIR/dryrun_01.txt   # 要求元と条件をセットで見る
```

**表示例**（説明用です）

```text
Error: Package: openssh-server-7.4p1-23.el7_9.x86_64 (/openssh-server-7.4p1-23.el7_9.x86_64)
           Requires: openssl-libs >= 1:1.0.2k-26
```

**`Requires:` の右側が「足りないもの」**、**`Error: Package:` の行が「欲しがっている RPM」**です。

### 黙って外されたRPMがないか確認する

**ここが一番見落としやすい落とし穴です。**`yum` は次の場合、**警告を1行出すだけでその RPM を計画から外します。**

| ログに出る文字列 | 起きていること |
|:--|:--|
| `Cannot open: ... Skipping.` | RPM ファイルを読めなかった（壊れ・権限） |
| `... does not update installed package.` | **別システムに同じ版か新しい版が入っている**ので更新にならない |
| `Not a compatible architecture` | アーキテクチャが合わない |
| `It is obsoleted by installed package` | 入っているパッケージに置き換えられている |
| `Excluding ...` | `/etc/yum.conf` の `exclude` に該当した |

**外された RPM を除いた残りだけで依存が閉じると、ログの最後は `Exiting on user command` になります。**
つまり**「依存OK」に見えるのに、CVE 対応 RPM の一部は何も確認されていない**状態が起こります。

```bash
$ grep -n -E 'Cannot open|Skipping|does not update installed package|Not a compatible architecture|obsoleted by installed package|^Excluding ' \
    $LOG_DIR/dryrun_01.txt                   # 計画から外された RPM の警告を探す
```

**期待値**：**何も表示されない**

❌ 表示された → **その RPM は計画に入っていません。**管理者と次のどちらかを決めてください。

- **別システムに同版が入っているだけ**なら、対象サーバーでは必要なので**そのまま持ち帰る**
- **ファイルが壊れている・アーキテクチャ違い**なら、**取り直す**

> **`does not update installed package.` は別システムではよく出ます。**
> **別システムの事情**なので、**対象サーバーで必要かどうかは第12章で判断します。ここで RPM を捨てないでください。**

### /tmp に残るファイルの注意

`--assumeno` で中止すると、Yum は**解決した計画をファイルに自動保存**して、こう案内してきます。

```text
Your transaction was saved, rerun it with:
 yum load-transaction /tmp/yum_save_tx.2026-10-14.10-30.AbCdEf.yumtx
```

> **この案内に従って `yum load-transaction` を実行してはいけません。実更新になります。**

```bash
$ ls -l /tmp/yum_save_tx.*.yumtx             # 自動保存されたファイルを確認する
```

**期待値**：下見した回数ぶんのファイルがある（**消さなくてよい。承認後に片付ける**）

---

## 8. 足りないRPMの正体を調べる

**`Requires:` に出た条件を、そのままの文字列で検索します。**

```bash
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID --show-duplicates \
    --whatprovides 'openssl-libs >= 1:1.0.2k-26'   # 条件を提供する RPM を探す
```

**表示例**（説明用です）

```text
1:openssl-libs-1.0.2k-26.el7_9.x86_64
1:openssl-libs-1.0.2k-27.el7_9.x86_64
```

**`--whatprovides '条件'` が「その条件を提供している RPM を探す」、`--show-duplicates` が「最新版だけに絞らず複数の版を表示する」**指定です。

> **`Requires:` というラベル自体は入れません。**右側の条件だけを、**クォートで囲んで**渡します。
> 条件には空白や `>=` が入るので、**囲まないとシェルが別々の引数として渡してしまいます。**

> **名前だけに削って検索しないでください。**
> `openssl-libs` だけだと、**版の条件（`>= 1:1.0.2k-26`）を満たさないものまで出てきます。**

**複数出たときの選び方**

- ファイル名に **対象サーバーと同じ `el7`** が入っているもの
- 条件が `()(64bit)` 付きなら **`x86_64` 版**
- **要求を満たす版で、今回の CVE と同じ時期のもの**
- **同じエラータ（RHSA）に入っている仲間はまとめて取る**（`openssl` と `openssl-libs` のように
  **仲間どうしは同じ版を要求し合うことが多い**ため、やり直し回数が減ります）

### カッコ付きの記号は外して調べる

```bash
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID \
    --whatprovides 'libcrypto.so.10()(64bit)'      # そのままの条件で探す
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID \
    --whatprovides 'libcrypto.so.10'               # カッコを外して探す
```

> **`()(64bit)` は「64bit 版である」という印**です。
> そのままで見つからないときは**外して検索**し、見つかった RPM の**アーキテクチャが `x86_64` であること**を確認します。

**よくある対応表（RHEL 7）**

| 条件の例 | 提供している RPM |
|:--|:--|
| `libcrypto.so.10()(64bit)` / `libssl.so.10()(64bit)` | `openssl-libs` |
| `libk5crypto.so.3()(64bit)` / `libkrb5.so.3()(64bit)` | `krb5-libs` |
| `libz.so.1()(64bit)` | `zlib` |
| `libselinux.so.1()(64bit)` | `libselinux` |
| `libpam.so.0()(64bit)` | `pam` |

> **この表は目安です。**必ず `repoquery --whatprovides` で**実際のリポジトリの中身**を確認してください。
> **対象サーバーで今その機能を提供しているパッケージ**は `rpm -q --whatprovides 'libcrypto.so.10'` で調べられます。
> **`rpm -q` は「サーバーに入っているもの」、`repoquery` は「リポジトリにあるもの」**で、調べる相手が違います。

---

## 9. 足りないRPMを取得する

**第8章で決めた NEVRA を指定して、`$HOME/rpm` にダウンロードします。**

```bash
$ yumdownloader --disablerepo='*' --enablerepo=$REPO_ID \
    --destdir $RPM_DIR 'openssl-libs-1:1.0.2k-26.el7_9.x86_64'   # 版まで指定して取得する
$ echo "exit code: $?"                       # 終了コードを見る
$ ls -lt $RPM_DIR/*.rpm | head -n 5          # 新しく増えたファイルを確認する
```

**期待値**：終了コードが 0 で、**指定した NEVRA のファイルが実際に増えている**

> **`yumdownloader` は「取るだけ」です。別システムにインストールしません。**
> **`--destdir` を指定しないとカレントディレクトリに落ちます。**

> **終了コードが 0 でも、ファイルが増えていないことがあります。必ず `ls -lt` で目で確認してください。**

> **パッケージ名だけを渡さないでください。**
> `yumdownloader openssl-libs` のように名前だけだと**リポジトリの最新版**が取れて、意図した版と違うものが混ざります。

**取ったものの中身も確認しておきます。**

```bash
$ rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' \
    $RPM_DIR/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm   # 版とアーキテクチャの確認
$ rpm -qp --provides $RPM_DIR/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm   # 何を提供するか
$ rpm -qpR $RPM_DIR/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm   # 何を要求するか
```

**`--provides` が「その RPM が与える機能」、`-R / --requires` が「その RPM が欲しがる機能」**です。

> **追加した RPM が、さらに別の RPM を要求することがあります。だから下見をやり直す必要があります。**

### 取得したら必ず7に戻る

```bash
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID install --assumeno $RPM_DIR/*.rpm \
    > $LOG_DIR/dryrun_02.txt 2>&1            # 2回目の下見（ファイル名の番号を変える）
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 20 $LOG_DIR/dryrun_02.txt          # 結果を見る
```

> **ログのファイル名の番号（`_01`, `_02`, `_03` …）を必ず変えてください。**
> 同じ名前にすると**前回の記録が上書きされて消えます。**
> **「何回目で何が足りなかったか」が作業の証跡になります。**

**`Exiting on user command` になるまで、第7章 → 第8章 → 第9章を繰り返します。**
**往復が数回になるのは普通**です。1回で終わらなくても異常ではありません。追加した理由は記録表の台帳に書きます。

### 参考 --resolve でまとめて取る場合

```bash
$ yumdownloader --disablerepo='*' --enablerepo=$REPO_ID --resolve \
    --destdir $HOME/resolve_test 'openssh-server'   # 依存ごとまとめて取る（別フォルダへ）
```

> **`--resolve` の結果をそのまま信用しないでください。**
> **`--resolve` は「別システムに入っていないもの」だけを取ります。**
> 別システムに入っていて対象サーバーに無いものは**取られません。**
> だから **`$HOME/rpm` とは別のフォルダに落として、中身を確認してから選ぶ**のが安全です。
> **本書の主手順は `--resolve` に依存しません。**第7〜9章の繰り返しが基本です。

---

## 10. 持ち帰り用にまとめる

**最終的な中身を確認してから、1ファイルにまとめます。**

```bash
$ ls $RPM_DIR                                # RPM だけになっているか確認する
$ ls $RPM_DIR/*.rpm | wc -l                  # 最終的な RPM の数
$ rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' $RPM_DIR/*.rpm \
    > $LOG_DIR/final-inventory.tsv           # 最終の NEVRA 一覧
$ diff $LOG_DIR/original-inventory.tsv $LOG_DIR/final-inventory.tsv   # 最初との差分を見る
```

**期待値**：`$HOME/rpm` の中が **`.rpm` ファイルだけ**で、`diff` に出るのが**自分が意図して追加した RPM だけ**

**まとめてハッシュ値を取ります。**

```bash
$ cd $HOME                                   # ホームへ移動する
$ tar -czf rpm_final.tar.gz rpm              # rpm フォルダをまとめる
$ sha256sum rpm_final.tar.gz > rpm_final.tar.gz.sha256   # ハッシュ値をファイルに残す
$ cat rpm_final.tar.gz.sha256                # ハッシュ値を表示してメモする
$ tar -tzf rpm_final.tar.gz | head -n 5      # 中身の先頭を確認する
$ tar -czf depcheck_log.tar.gz depcheck_log  # ログもまとめる
$ ls -l rpm_final.tar.gz rpm_final.tar.gz.sha256 depcheck_log.tar.gz   # 3つできたか確認する
```

**期待値**：3ファイルができていて、`tar -tzf` の中身が**すべて `rpm/` の下**（絶対パスや `../` が無い）

> **ログは証跡です。**「何回下見して、何が足りなくて、何を追加したか」が残ります。**審査や引き継ぎで必ず聞かれます。**

---

## 11. WinSCPで持ち帰る

1. WinSCP で別システムに接続する
2. **右側（別システム）のパス欄に `/home/ユーザー名` を入れて移動**する
3. `rpm_final.tar.gz`、`rpm_final.tar.gz.sha256`、`depcheck_log.tar.gz` を選ぶ
4. **左（手元の Windows）へドラッグする。転送モードはここでも「バイナリ」**

**手元に届いたら、ハッシュ値を照合します。**PowerShell で実行します。

```powershell
cd C:\work                                           # 保存先へ移動する
Get-FileHash -Algorithm SHA256 rpm_final.tar.gz      # 手元でのハッシュ値
type rpm_final.tar.gz.sha256                         # 別システムでのハッシュ値
```

**期待値**：`Get-FileHash` の `Hash` と `.sha256` の中の値が**一致する**

> **大文字・小文字は気にしなくてよいです**（`Get-FileHash` は大文字、`sha256sum` は小文字で出ます）。

❌ **一致しない** → 転送で壊れています。**もう一度持ち帰ってください。**

> **ハッシュの一致は「転送で壊れていない」ことの確認だけ**です。
> **「正しい Red Hat の修正版である」ことの確認にはなりません。**それは **RHSA と NEVRA の突き合わせ**で別に確認します。

> **別システムの `$HOME/rpm` と `$HOME/depcheck_log` は、照合が終わるまで消さないでください。**
> **削除は社内の承認後**に行います。ホームディレクトリは自動では消えないので、**作業完了後に自分で片付ける**必要があります。
> 本書に一括削除コマンドは載せません。

---

## 12. 対象サーバーであてる前の確認

**ここからは対象サーバー（オフラインの本番機）での作業です。作業承認を得てから実施してください。**
**別システムでの結果は参考値で、最終判断は対象サーバーの結果を使います。**入っているパッケージが違うからです。

社内で承認された方法で `rpm_final.tar.gz` と `.sha256` を送り、展開して現状を記録します。

```bash
$ export LANG=C                              # 出力を英語にする
$ export RPM_DIR=$HOME/rpm                   # RPM 置き場
$ export LOG_DIR=$HOME/depcheck_log          # ログ置き場
$ mkdir -p $LOG_DIR                          # ログ置き場を作る
$ cd $HOME                                   # ホームへ移動する
$ sha256sum -c rpm_final.tar.gz.sha256       # ハッシュ値を照合する
$ tar -tzf rpm_final.tar.gz | head -n 5      # 中身を確認する
$ tar -xzf rpm_final.tar.gz                  # 展開する
$ ls $RPM_DIR/*.rpm | wc -l                  # RPM の数を数える
$ rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' | sort \
    > $LOG_DIR/installed-before.tsv          # 導入済み一覧を記録する
$ df -h / /var /boot > $LOG_DIR/disk-space.txt   # 空き容量を記録する
$ sudo yum --noplugins --disablerepo='*' check > $LOG_DIR/yum-check-before.log 2>&1   # 既存の不整合を調べる
$ echo "check exit code: $?"                 # 終了コードを見る
```

**期待値**：`sha256sum -c` が **`rpm_final.tar.gz: OK`**、RPM の数が別システムでの最終件数と一致、`check` の終了コードが 0

❌ `check` が 0 以外 → **もともと不整合があります。**管理者に確認してください。**今回の RPM が原因だと決めつけないでください。**

> **この記録はバックアップではありません。**`installed-before.tsv` からシステムを復元することはできません。

### 12.1 下見する

```bash
$ sudo yum --noplugins --disablerepo='*' install --assumeno $RPM_DIR/*.rpm \
    > $LOG_DIR/offline-dryrun.txt 2>&1       # 外部リポジトリ無しで下見する
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 30 $LOG_DIR/offline-dryrun.txt     # 結果を見る
$ grep -n -E 'Cannot open|Skipping|does not update installed package|Not a compatible architecture|obsoleted by installed package|^Excluding ' \
    $LOG_DIR/offline-dryrun.txt              # 計画から外された RPM の警告を探す
```

**`--noplugins` は versionlock などプラグイン由来の制約を外す指定**で、**`yum.conf` の `exclude` は外れません。**
**`--disablerepo='*'` で外部リポジトリを一切使わず**、持ち込んだ RPM だけで依存が閉じるかを見ます。

| 計画に出る表示 | 読み方・確認すること |
|:--|:--|
| `Installing` | **新規導入。**追加して良いものか承認を確認する |
| `Updating` | 既存パッケージの更新。**意図した版か** |
| `Removing` と行中の `replacing` | 削除・置換。**想定外なら中断** |
| カーネルの追加・旧版削除 | **起動と復旧用カーネルへの影響**を個別に確認 |
| `Requires:` / `Error:` | **依存不足。**第8・9章に戻って別システムで取り直す |
| `Nothing to do` | 対象なし。**目的達成とは限らない** |
| `Exiting on user command` | `--assumeno` による正常な中止。**終了コードは1** |

**期待値**：最後の `grep` が**何も表示しない**こと（計画から外された RPM が無いこと）

> **`Obsoleting` は Yum 3 の計画表の見出しではありません。**
> 置き換えは **`Removing` と、各行に続く `replacing`** で表示されます。

> **「渡したのに計画に出てこない RPM」が、いちばん危険な見落としです。**
> 気になるパッケージは `grep -o 'openssh[^ ]*' $LOG_DIR/offline-dryrun.txt | sort -u` のように**名前で探して**確かめてください。

### 12.2 トランザクションテストをする

**実行条件**：計画の内容と、versionlock・exclude などの運用条件を管理者が確認済みであること。

> **`--setopt=tsflags=test` が実更新を防ぐ重要な指定です。削除・省略しないでください。**
> **`-y` は付けません。**確認画面で計画をもう一度見ます。

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=tsflags=test install $RPM_DIR/*.rpm \
    > $LOG_DIR/offline-test.txt 2>&1         # ファイルを書き換えないテストをする
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 30 $LOG_DIR/offline-test.txt       # 結果を見る
```

**確認画面が出たら、`tsflags=test` を打ったことと計画を確認し、進める場合だけ `y` を入力します。**

**期待値**：ログの中に次の3つが順に出ていること

```text
Running transaction check
Running transaction test
Transaction test succeeded
```

> **`Transaction test succeeded` の後に `Running transaction` と出ても、ファイルは更新されません。**`tsflags=test` が付いているためです。
> **このテストは `yum history` に記録されません。**`tsflags` に `test` が入っていると Yum は履歴の記録自体を行いません。
> **実施記録はこのログファイルで残してください。**

**テストの前後でパッケージ一覧が変わっていないことを確認します。**

```bash
$ rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' | sort \
    > $LOG_DIR/installed-after.tsv           # テスト後の一覧を取る
$ diff -u $LOG_DIR/installed-before.tsv $LOG_DIR/installed-after.tsv   # 前後を比べる
$ echo "diff exit code: $?"                  # 差分があれば 1 になる
```

**期待値**：**差分なし**（終了コードが 0）

❌ 差分があった → **完了にしないでください。**ほかの管理処理が同時に動いていないかも含めて調査します。

> **一覧が一致したことは「ファイルシステムへの書き込みが一切なかった」証明ではありません。**ログやキャッシュは作られます。

### 12.3 ここで確認できないこと

| 確認できたこと | まだ確認できていないこと |
|:--|:--|
| 対象サーバーの現状に対する依存解決 | 更新後のアプリケーション動作 |
| 計画の内容（追加・更新・削除・置換） | インストールスクリプトの実行成功 |
| トランザクションテストが通ること | サービスの正常再起動、OS の起動 |
| ファイルの整合性（ハッシュ値） | **目的の CVE が確実に修正されたこと** |

**この手順の結果を「本番更新できた」と報告しないでください。実際にあてる手順は別の作業**です
（[手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) /
[手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md)）。

実更新の前に、**バックアップと復元試験／停止・再起動の計画／対象を再現した環境での実更新試験とアプリケーション確認／
障害時の連絡先とコンソール接続手段／変更承認**をそろえます。
**`yum history undo` はバックアップ復元の代わりになりません**（旧版 RPM の入手可否やスクリプトによる変更が関係します）。
**カーネルを含む場合は、起動先と復旧用カーネルを必ず確認してください。**

---

## よく出るメッセージ早見表

| 表示 | 意味 | 次にやること |
|:--|:--|:--|
| `Exiting on user command` | `--assumeno` による正常な中止（終了コード1） | 異常ではない。計画本文を読む |
| `Error: Package: ...` ＋ `Requires: xxx` | 依存が足りない | 条件全文を `repoquery --whatprovides` で調べる |
| `Protected multilib versions` | x86_64 と i686 の版ずれ | **両アーキテクチャを同じ版で**取得する |
| `conflicts with file from package` | ファイルの所有・内容が競合 | 両 RPM の製品・版・提供元を確認 |
| `does not update installed package.` | 同版・旧版が入っていて更新にならない | **計画から外れている。**持ち帰る／取り直すを判断 |
| `Cannot open: ... Skipping.` | RPM を読めず計画から外された | ハッシュ・権限・破損を確認し、転送をやり直す |
| `Not a compatible architecture` / `Excluding ...` | アーキテクチャ違い／`yum.conf` の `exclude` に該当 | アーキテクチャを確認、または管理者に運用条件を確認 |
| `No package ... available` | 指定版が見えない | リポジトリID・同期内容・版指定・権利を確認 |
| `Cannot find a valid baseurl` | 取得元・接続・認証の問題 | **依存不足と混同しない。**第6章へ |
| `Nothing to do` | やることが無い | RPM の取り違え、`el7` 以外の混入、適用済みを確認 |
| `Existing lock` | 別の yum/rpm が動いている可能性 | 管理者に実行状況を確認。**ロックファイルを消さない** |

---

## やってはいけないこと

| やってはいけないこと | 理由 |
|:--|:--|
| **`yum load-transaction` を実行する** | `--assumeno` の案内に従うと**実更新になる** |
| **`--nodeps` / `--force` / `--ignorearch`** | 依存関係やアーキテクチャの判定を無視してシステムを壊す |
| **`--skip-broken`** | 問題のあるパッケージを**黙って計画から外す。**CVE 対応の抜けが隠れる |
| **`--nogpgcheck`** | 検証を飛ばす。先へ進めるための道具にしない |
| **`rpm -Uvh *.rpm`（`--test` 無し）** | yum の依存解決・運用設定と評価が違う。**カーネルの installonly 扱いも異なる** |
| **RPM を1個ずつ下見する** | 同時更新で解決する関係を「不足」と誤判定する |
| **ログのファイル名を使い回す** | 前回の証跡が消える |
| **転送モードを「テキスト」にする** | RPM とアーカイブが壊れる |

---

## 記録表

### 下見のラウンド記録

| 回 | ログファイル | RPM数 | 結果 | 足りなかった条件 | 追加したNEVRA | 実施日時 | 実施者 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 01 | `dryrun_01.txt` | | | | | | |
| 02 | `dryrun_02.txt` | | | | | | |

### 追加したRPMの台帳

| 不足条件 | 要求していたRPM | 採用NEVRA | 取得リポジトリ・取得日 | 追加理由・承認 |
|:--|:--|:--|:--|:--|
| ログから転記 | ログから転記 | 正確な版 | リポジトリIDと日付 | 対象サーバーの不足解消など |

### 保存されるファイル

| 場所 | ファイル | 内容 |
|:--|:--|:--|
| `$HOME/rpm` | `*.rpm` | **持ち帰る中身。RPM だけにする** |
| `$HOME/depcheck_log` | `original-inventory.tsv` / `final-inventory.tsv` / `dryrun_01.txt`, `_02.txt` … | 最初と最後の NEVRA 一覧、各回の下見結果 |
| `$HOME/depcheck_log` | `repolist.txt` | 社内リポジトリの詳細（**社内URLを含む。社外に出さない**） |
| `$HOME` | `rpm_final.tar.gz` ＋ `.sha256` / `depcheck_log.tar.gz` | 持ち帰るアーカイブ |
| 対象サーバー `$HOME/depcheck_log` | `offline-dryrun.txt` / `offline-test.txt` / `installed-before.tsv` / `installed-after.tsv` | 下見・トランザクションテストと、その前後の導入済み一覧 |

> **認証情報が入った設定ファイル（`.repo` など）は転送しないでください。**

### 完了条件

- [ ] 手元で用意した RPM の数と、別システムに届いた数が一致した
- [ ] 送り・持ち帰りの両方でハッシュ値が一致した
- [ ] 別システムでの最後の下見が `Exiting on user command` で終わった
- [ ] 別システムと対象サーバーの両方で、**除外警告（`Skipping` など）が出ていない**
- [ ] 持ち込んだ RPM が、対象サーバーの計画に現れている
- [ ] 対象サーバーで `Transaction test succeeded` になった
- [ ] テスト前後の導入済み一覧に差分がない
- [ ] 各 CVE・RHSA と採用した修正後 RPM の対応を確認した
- [ ] 追加・除外・置換の理由を台帳に記録した
- [ ] ログ一式を保管し、サーバー名・日時・実施者を対応付けた

---

## 公式参照

**開発元の文書には RHEL 7 に無い機能も含まれ得ます。**実行前に導入済み版の `man yum` / `man yum.conf` /
`man rpm` / `man yumdownloader` / `man repoquery` と `--help` でも確認してください。
**`access.redhat.com/solutions/` 配下の記事は、閲覧に Red Hat のサブスクリプションでのログインが必要**です。

| 資料 | 本書で確認した内容 |
|:--|:--|
| [Red Hat：RHEL 7 System Administrator's Guide — Yum](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-yum) | RHEL 7 の Yum、ローカル RPM の扱い |
| [Yum開発元：yum(8)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.8) | **`install` にファイル名を渡すとローカルインストールになること**、`localinstall` が互換目的であること、リポジトリ指定、`--assumeno` |
| [Yum開発元：yum.conf(5)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.conf.5) | `tsflags`、`localpkg_gpgcheck`（既定 `0`）、`exclude`、`assumeno` |
| [Yum Utils開発元：yumdownloader(1)](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/yumdownloader.1) | `--destdir`、`--resolve` |
| [Yum Utils開発元：repoquery(1)](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/repoquery.1) | `--whatprovides`、`--show-duplicates` |
| [RPM開発元：RPM 4.11系 rpm(8)](https://raw.githubusercontent.com/rpm-software-management/rpm/rpm-4.11.x/doc/rpm.8) | `-qp`、`--provides`、`-R`、`--qf` |
| [Red Hat：Security Backporting Practice](https://access.redhat.com/security/updates/backporting)（要ログインの場合あり） | バックポートと版番号での判断 |
| [Red Hat：RHEL 7 End of Maintenance FAQ](https://access.redhat.com/articles/7005471)（要ログインの場合あり） | RHEL 7.9 と ELS の対象・期間 |

### この文書の検証範囲

**公式 man と開発元ソースで確認した事項**：`Exiting on user command`（`--assumeno` 時の表示・終了コード1）／
`install` にファイル名を渡すとローカルインストールになること／`Cannot open: ... Skipping.`・
`does not update installed package.`・`Not a compatible architecture`・`It is obsoleted by installed package`・
`Excluding` で **RPM が計画から外れること**／計画表の見出しに **`Obsoleting` は含まれない**こと／
`Running transaction check` → `Running transaction test` → `Transaction test succeeded` の表示順／
`tsflags=test` のとき **`yum history` に記録されない**こと／`--assumeno` 中止時に
`/tmp/yum_save_tx.*.yumtx` が自動保存され `yum load-transaction` が案内されること／
`localpkg_gpgcheck` の既定が `0` であること。

**RHEL 7.9 の実機では未実行**です。実際の RPM・社内リポジトリ・対象サーバーでの出力は取得していません。
**出力例は説明用**で、実機の出力ではありません。
TeraTerm と WinSCP の画面の文言は、**版によって表記が異なる場合があります。**

---

## 変更履歴

| 日付 | 版 | 内容 |
|:--|:--|:--|
| 2026-10-14 | 2.0 | **実作業（TeraTerm でログイン → WinSCP で RPM を送る → 不足依存を取得 → WinSCP で持ち帰る）の流れに沿って全面的に書き直し。**シェルスクリプト風の記述（`mktemp`、サブシェル、配列、`set -e`、`for` ループ）を廃止し、**すべて1行ずつのコマンド**にした。作業場所を `$HOME/rpm` と `$HOME/depcheck_log` に固定。社内リポジトリを `/etc/yum.repos.d/internal-rhel7.repo`（`gpgcheck=0`）前提にして**署名検証の章を削除**（代わりに `localpkg_gpgcheck` も `0` である注意を追記）。初心者向けの用語解説、WinSCP のバイナリ転送、ハッシュ値の照合、TeraTerm でのサーバー取り違え防止を追加 |
| 2026-10-14 | 1.1 | 誤りの修正。`Operation aborted` → **`Exiting on user command`**、`rpm -Kv` の失敗語、**`install` / `localinstall` が警告だけで RPM を計画から外すこと**の検出手順、`/tmp/yum_save_tx.*.yumtx`、`--assumeno` では `localpkg_gpgcheck` が働かないこと、`tsflags=test` が `yum history` に残らないこと、`repoquery --pkgnarrow` の man と実装の食い違いを反映 |
| 2026-10-14 | 1.0 | 初版（3システム構成の準備手順として作成） |

---

[← 全体の目次にもどる](../README.md)
