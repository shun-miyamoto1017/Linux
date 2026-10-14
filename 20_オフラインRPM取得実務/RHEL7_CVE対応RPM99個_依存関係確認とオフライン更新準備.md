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
> | 手順書 | [yum-utils が無い別システムで不足依存RPMを取得する](./手順書_RHEL7_yum-utilsが無い場合の依存RPM取得.md) | **本ノートの第8・9章の差し替え。**`yumdownloader` / `repoquery` が無いときに、`yum provides` → `yum --showduplicates list` → `yum install --downloadonly` で調べて取得する |
> | 解説 | [下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) | **`yum install --assumeno` のログの読み方。**行の形ごとの意味、`Error:` の塊の読み方、計画の表と `Transaction Summary` の読み方、よくある読み違い |
> | 手順書 | [対象サーバーでの適用前確認](./手順書_RHEL7_対象サーバーでの適用前確認.md) | **本ノートの続き。**持ち帰った RPM を対象サーバーで確認する（ハッシュ照合 → 下見 → トランザクションテスト → 前後比較）。**実際にあてる手順は含まない** |
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
  - [LANG=C は exit したら元に戻るのか](#lang=c-は-exit-したら元に戻るのか)
- [4. WinSCPでアーカイブを送る](#4-winscpでアーカイブを送る)
- [5. アーカイブを展開する](#5-アーカイブを展開する)
- [6. 社内リポジトリを確認する](#6-社内リポジトリを確認する)
- [7. 足りない依存を下見する](#7-足りない依存を下見する)
  - [7.1 持ち込んだRPMだけで足りるか見る](#71-持ち込んだrpmだけで足りるか見る)
  - [7.2 社内リポジトリで何を足せばよいか調べる](#72-社内リポジトリで何を足せばよいか調べる)
  - [7.3 ログの読み方](#73-ログの読み方)
  - [7.4 確認用のまとめログを作って持ち帰る](#74-確認用のまとめログを作って持ち帰る)
  - [7.5 黙って外されたRPMがないか確認する](#75-黙って外されたrpmがないか確認する)
  - [7.6 /tmp に残るファイルの注意](#76-tmp-に残るファイルの注意)
- [8. 足りないRPMの正体を調べる](#8-足りないrpmの正体を調べる)
  - [見つからないときはグロブで探す](#見つからないときはグロブで探す)
- [9. 足りないRPMを取得する](#9-足りないrpmを取得する)
  - [取得したら必ず7に戻る](#取得したら必ず7に戻る)
  - [参考 --resolve でまとめて取る場合](#参考---resolve-でまとめて取る場合)
- [10. 持ち帰り用にまとめる](#10-持ち帰り用にまとめる)
- [11. WinSCPで持ち帰る](#11-winscpで持ち帰る)
- [12. 対象サーバーへ渡す](#12-対象サーバーへ渡す)
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
                                ⑧ あてる前の確認 → 別ノート「対象サーバーでの適用前確認」
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

> **`tar` が使えないと言われたら**、7-Zip などで `tar.gz` を作ってください（tar にしてから gzip にする2段階です）。
> **`.zip` は避けたほうが安全**です。展開に `unzip` が必要で、RHEL 7 に入っていないことがあります。
> **RPM は圧縮済みなので小さくはなりません。**1ファイルにまとめて**転送の抜けを防ぐ**ためにやっています。

---

## 2. TeraTermで別システムにログインする

1. TeraTerm を起動して「新しい接続」
2. **ホスト**に別システムの IP かホスト名
3. **サービス**は **SSH**、**SSHバージョン**は **SSH2** を選んで「OK」
4. ユーザー名とパスワード（または鍵）を入れて「OK」

ログインできたら、**まず自分がどこにいるかを確認します。**

```bash
$ export LANG=C                  # この接続だけメッセージを英語にそろえる（第3章で解説）
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

> **コードブロックの先頭の `$ ` は入力しません。**プロンプトの印として書いてあるだけです。
> `$ ` ごと貼り付けると `$: command not found` になります。

次に、必要な道具がそろっているか確認します。**ここで手順が2つに分かれます。**

```bash
$ which tar sha256sum                        # まとめる・ハッシュを取る道具があるか
$ rpm -q yum-utils                           # yum-utils が入っているか
$ which yumdownloader repoquery              # 取得と検索のコマンドがあるか
$ yumdownloader --help > /dev/null 2>&1      # 実際に起動するか試す
$ echo "yumdownloader rc=$?"                 # 起動したら 0
$ repoquery --help > /dev/null 2>&1          # 実際に起動するか試す
$ echo "repoquery rc=$?"                     # 起動したら 0
```

**期待値**：`tar` と `sha256sum` のパスが出ること。出なければ管理者に相談します。

| `yum-utils` の判定結果 | パターン | 第8・9章でやること |
|:--|:--|:--|
| パスが出て、`rc=0` が2つ出る | **A：`yumdownloader` が使える** | **このノートのまま**進める |
| `package yum-utils is not installed` | **B：使えない** | **[yum-utils が無い場合の依存RPM取得](./手順書_RHEL7_yum-utilsが無い場合の依存RPM取得.md)** に差し替える |
| パスは出るが `rc=0` 以外 | **B 扱い**（壊れている可能性） | 管理者に状況を伝えてから同上 |

> **パスの有無だけで判断せず、実際に起動するところまで確認**してください。
> `which` でパスが出るのに `--help` が失敗することがあります（Python の依存が壊れている場合など）。

> **いちばん簡単な解決は `sudo yum install yum-utils` で入れてもらうことです。**
> 別システムは社内リポジトリにつながっているので通常は入りますが、
> **別システムへのパッケージ導入は構成変更**なので、**必ず管理者の承認を取ってください。**

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

変数が空のまま次へ進むと、`$RPM_DIR/...` が `/...` に化けます。**値が入っていることを必ず見てください。**

```bash
$ echo "RPM_DIR=$RPM_DIR LOG_DIR=$LOG_DIR REPO_ID=$REPO_ID"   # 3つとも値が入っているか
```

**期待値**：3つとも `/home/ユーザー名/...` や `internal-rhel7` が表示される（空が1つでもあれば `export` からやり直す）

### LANG=C は exit したら元に戻るのか

**戻ります。** `export LANG=C` が効くのは**そのログインセッション（そのシェルと、そこから起動したコマンド）の中だけ**で、
**ディスク上のファイルは一切書き換えません。**TeraTerm の接続を閉じればシェルごと消えます。

次にログインしたときに `ja_JP.UTF-8` に戻るのは、**ログインのたびにロケールの設定が読み直される**からです。RHEL 7 では次の順で決まります。

| 場所 | 役割 |
|:--|:--|
| `/etc/locale.conf` | **システム全体**のロケール設定 |
| `$HOME/.i18n` | **ユーザーごと**のロケール設定 |
| `/etc/profile.d/lang.sh` | 対話シェルの起動時に、上の2つを（この順で）読み込んで `LANG` を設定する |

> **ただし `LANG` がすでに設定されている場合、`lang.sh` はその値をそのまま残します。**
> SSH クライアント側がロケールを送ってくる構成だと、ログイン直後から別の値になっていることがあります。
> 根拠：[Red Hat：How to change system locale on RHEL7?](https://access.redhat.com/node/974273)

**今どうなっているかを見るコマンド**（どれも表示するだけで、何も変えません）

```bash
$ echo $LANG                                 # 今のシェルの LANG
$ locale                                     # LANG と LC_* の一覧
$ cat /etc/locale.conf                       # システム全体の設定（書き換えない）
$ ls -l $HOME/.i18n                          # 個人設定の有無（無ければ No such file）
$ localectl status                           # systemd が見ているロケール
```

**日本語に戻したいとき**は、次のどれかです。

| やり方 | 内容 |
|:--|:--|
| **`exit` して入り直す** | いちばん確実。`lang.sh` が読み直される |
| `export LANG=ja_JP.UTF-8` | その場のシェルだけ戻す |
| TeraTerm をもう1本開く | 日本語の窓と英語の窓を並べて使える |

> **`~/.bashrc` や `~/.bash_profile` に `export LANG=C` を書かないでください。**
> 恒久的な変更になり、あなたの他の作業にも影響します。
> **`localectl set-locale` や `/etc/locale.conf` の書き換えは、別システム全体の構成変更**です。承認なしに行わないでください。

> **`LC_ALL` が設定されていると `LANG=C` は効きません。**
> 優先順位は **`LC_ALL` > `LC_MESSAGES` などの個別の `LC_*` > `LANG`** です。
> `locale` の表示で `LC_ALL` に値が入っていたら、`export LC_ALL=C` のほうを使ってください。

> **`sudo` の先に引き継がれるかは環境によります。**本書の `yum` は `sudo` 越しに動くので、ここが効かないと英語になりません。

```bash
$ sudo printenv LANG                         # sudo 先の LANG を確認する
```

> `C` 以外が表示されたら、`sudo -E yum ...` のように `-E` を付けるか、
> `sudo env LANG=C yum ...` のようにコマンドごとに指定してください。

---

## 4. WinSCPでアーカイブを送る

1. WinSCP を起動して、接続先（サイト）を新規に作る
2. **ファイルプロトコル**を **SFTP**、**ホスト名**に別システムの IP かホスト名
3. ユーザー名とパスワード（または鍵）を入れて「ログイン」
4. 画面が左右に分かれる。**左が手元の Windows、右が別システム**
5. **右側のパス欄に `/home/ユーザー名` を入れて移動**する（**`/rpm` は付けません**）
6. 左側で `C:\work\rpm.tar.gz` を選び、**右へドラッグする**

> **送り先は `$HOME` です。`$HOME/rpm` ではありません。**
> アーカイブの中身が `rpm/` というフォルダなので、**`$HOME` で展開すると `$HOME/rpm/` ができます**（第5章）。
> `$HOME/rpm` に送って展開すると `$HOME/rpm/rpm/` という余計な入れ子ができます。

> **転送モードは「バイナリ」にしてください。**
> 既定は「自動」で、拡張子で判定します。`.rpm` や `.tar.gz` は通常バイナリ扱いですが、
> **「テキスト」で転送されると改行コードが書き換えられて壊れます。**転送設定で明示的に「バイナリ」を選ぶのが確実です。
> 画面の項目名は WinSCP の版や日本語化の有無で変わるので、**実際の画面の表記に読み替えてください。**

転送が終わったら、**TeraTerm 側で届いたことを確認します。**

```bash
$ ls -l $HOME/rpm.tar.gz                     # 届いたファイルを見る
$ sha256sum $HOME/rpm.tar.gz                 # ハッシュ値を計算する
```

**期待値**：サイズが手元の `dir` と同じで、**ハッシュ値が第1章でメモした値と一致する**

❌ **ハッシュ値が違う** → 転送中に壊れています。**転送モードがバイナリか確認して送り直してください。**

---

## 5. アーカイブを展開する

**まず中身を見ます。ここで止まれるように、展開とはブロックを分けています。**

```bash
$ cd $HOME                                   # ホームへ移動する
$ tar -tzf rpm.tar.gz                        # 中身を一覧する（まだ展開しない）
$ tar -tzf rpm.tar.gz | wc -l                # 中身の数（rpm/ の行も1行入る）
```

`tar` のオプションは **`-t` が一覧、`-x` が展開、`-c` が作成、`-z` が gzip、`-f` がファイル名の指定**です。

**期待値**：すべての行が **`rpm/` で始まっている**こと

> **絶対パス（先頭が `/`）や `../` が入っていたら、ここで止めてください。**想定外の場所にファイルが置かれます。
> **確認してから、次のブロックを実行します。**

```bash
$ cd $HOME                                   # ホームへ移動する
$ tar -xzf rpm.tar.gz                        # 展開する（$HOME/rpm/ ができる）
$ ls $RPM_DIR/*.rpm | wc -l                  # RPM の数を数える
$ ls $RPM_DIR | grep -v '\.rpm$'             # RPM 以外が混ざっていないか
```

**期待値**：RPM の数が**手元で用意した数と一致**し、最後の `grep` が**何も表示しない**

> **アーカイブの中身は `rpm/` なので、`$HOME` で展開すると `$HOME/rpm/`（＝`$RPM_DIR`）に入ります。**
> 第3章で `mkdir -p $RPM_DIR` を済ませていても問題ありません。`tar` が同じ場所に重ねて展開します。

❌ **数が合わない** → 転送の抜けか、`tar` の作り方が違います。第1章からやり直してください。
❌ **`$HOME/rpm/rpm` ができた** → アーカイブを `$HOME/rpm` に送ってしまっています。第4章の送り先を確認してください。

送ってきたアーカイブは、展開を確認してから消します。

```bash
$ rm -f $HOME/rpm.tar.gz                     # 送ってきたアーカイブを消す
$ ls $HOME                                   # ホームの中身を確認する
```

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
> **設定ファイルは書き換えません。**`--disablerepo` / `--enablerepo` は**その1回のコマンドにだけ効く**指定で、
> 恒久的な `.repo` の作成や `createrepo` も、この手順では不要です。

> **このリポジトリは `gpgcheck=0` なので、本手順に署名検証（`rpm -K`）は入れていません。**
> ただし **`localpkg_gpgcheck` も既定が `0`** なので、**自分が持ち込んだ RPM の署名も検査されません。**
> **社内リポジトリ以外から入手した RPM を混ぜる場合は、入手元の確認を別途行ってください。**
> 署名検証そのものの話は [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) にあります。

---

## 7. 足りない依存を下見する

**ここが本体です。**`--assumeno` を付けて、**「もし入れたらどうなるか」だけを表示させます。**
**下見は2回に分けます。役割が違うので、必ず両方やってください。**

| | 社内リポジトリ | 何が分かるか |
|:--|:--|:--|
| **7.1** | **使わない**（`--disablerepo='*'`） | **持ち込んだ RPM だけで依存が閉じるか。**対象サーバーに近い条件 |
| **7.2** | 使う（`--enablerepo=$REPO_ID`） | **リポジトリから何を足せば閉じるか。**ここに出たものが取得対象 |

> **7.2 だけで判断してはいけません。**
> 社内リポジトリを有効にすると、Yum は足りない依存を**リポジトリから自動で補って**計画を作ります。
> その結果 `Error: ... Requires:` は出ず、**`Exiting on user command` で正常終了します。**
> これを「依存がそろった」と読むと、**補われた RPM を持ち帰らないまま先へ進んでしまいます。**
> 根拠：`yum.8` の localinstall の項に「*If required the enabled repositories will be used to resolve dependencies*」とあります。

### 7.1 持ち込んだRPMだけで足りるか見る

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/dryrun_01.txt 2>&1            # リポジトリを使わずに下見する
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 20 $LOG_DIR/dryrun_01.txt          # ログの最後を見る
```

**なぜこの形なのか**

| 指定 | 理由 |
|:--|:--|
| `install` に**ファイルパス**を渡す | `yum` は**ファイル名を渡されるとローカルインストールとして扱う**（`yum.8` に明記）。`localinstall` は公式に「互換のため残しているだけ」とされているので `install` を使う |
| **1個ずつでなく全部まとめて**渡す | 1個ずつ試すと、**同時に入れる別の RPM が条件を満たす関係を「不足」と誤判定**する |
| `--assumeno` | 確認に自動で「いいえ」と答える。**実更新を絶対にしない** |
| `--setopt=alwaysprompt=1` | **確認を必ず出させる。**`alwaysprompt=0` の環境では、確認が出ない計画で `--assumeno` が働かないため（保険） |
| `--disablerepo='*'` | **外部リポジトリを一切使わない。**持ち込んだ RPM と別システムの導入済みパッケージだけで判定する |
| `--noplugins` | versionlock などプラグイン由来の制約を外す。**`yum.conf` の `exclude` は外れない** |
| `${RPM_DIR:?}` | 変数が空のときに `/*.rpm` へ化けるのを防ぐ。**未設定ならその場でエラーになる** |
| `> ファイル 2>&1` | 出力が長く画面では読めない。`2>&1` で**エラー出力も同じファイルへ**送る |
| `sudo` | `yum install` は **root でないと実行できない**（`You need to be root to perform this command.`） |

**結果の読み方**

| 最後に出ている文 | 意味 | 次にやること |
|:--|:--|:--|
| **`Error: Package: ...` ＋ `Requires: xxx`** | **足りない依存がある**（想定どおり） | そのまま 7.2 へ |
| **`Exiting on user command`** | 持ち込んだ RPM と**別システムの導入済み**だけで閉じた | **それでも 7.2 をやる**（別システムに入っているせいで隠れている分がある） |
| **`Protected multilib versions`** | 32bit 版と 64bit 版の版ずれ | **i686 版も同じ版で取得する** |
| **`Nothing to do`** | やることが無い | RPM の取り違え、`el7` 以外の混入、別システムに同版が入っている |

> **`Exiting on user command` は「成功」です。**`--assumeno` で「いいえ」と答えた正常な中止で、**終了コードは 1** になります。
> **`Operation aborted.` は RHEL 8 以降の `dnf` の表示で、RHEL 7 の `yum` では出ません。**
> 検索するときは版による大文字小文字の違いを避けて `grep -i 'exiting on user'` が確実です。
> `This system is not registered with an entitlement server.` は**無視してよい**です。

**足りないものの一覧を出します。**

```bash
$ grep 'Requires:' $LOG_DIR/dryrun_01.txt | sort -u   # 足りない条件を重複なしで並べる
$ grep -A6 'Error: Package:' $LOG_DIR/dryrun_01.txt   # 要求元・導入済み・候補をセットで見る
```

**`Requires:` の右側が「足りないもの」**、**`Error: Package:` の行が「欲しがっている RPM」**です。
`Installed:` / `Available:` の読み方は [下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) にあります。

### 7.2 社内リポジトリで何を足せばよいか調べる

```bash
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/dryrun_01_repo.txt 2>&1       # 社内リポジトリを使って下見する
$ echo "exit code: $?"                       # 終了コードを見る
$ grep -n -E '^(Installing|Updating|Removing) for dependencies:' $LOG_DIR/dryrun_01_repo.txt   # 自動で足された節を探す
$ tail -n 30 $LOG_DIR/dryrun_01_repo.txt     # 計画の末尾を見る
```

**`... for dependencies:` の下に並ぶ RPM が「取得する対象」です。**

**表示例**（説明用です）

```text
Installing for dependencies:
 openssl-libs    x86_64    1:1.0.2k-26.el7_9    internal-rhel7    1.2 M
```

左から **パッケージ名／アーキテクチャ／`Epoch:Version-Release`／リポジトリID／サイズ**です。
これを **`名前-Epoch:Version-Release.アーキテクチャ`** の形につなぐと、第9章でそのまま使える NEVRA になります
（上の例なら **`openssl-libs-1:1.0.2k-26.el7_9.x86_64`**）。

| 7.2 の結果 | 意味 | 次にやること |
|:--|:--|:--|
| `... for dependencies:` が出た | **リポジトリから補われた。**その RPM を取得する必要がある | **第9章へ**（名前と版が分かっているので `repoquery` は不要） |
| `... for dependencies:` が無く `Exiting on user command` | 追加は不要 | **第10章へ** |
| `Error: ... Requires:` が残る | **リポジトリにも無い** | **第8章へ**（提供元を自分で探す） |
| `Removing for dependencies:` が出た | **何かが削除される計画になっている** | **中断して管理者に確認**。想定外の削除は危険 |

> **`Removing for dependencies:` は特に注意してください。**依存の都合で既存パッケージが消える計画です。
> 対象サーバーで同じことが起きるとサービスが止まる可能性があります。

### 7.3 ログの読み方

**ログの読み方は [下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) にまとめてあります。**
`Examining` と `Marking`、`--> Processing Dependency:`、`Error:` の塊（`Requires:` / `Installed:` / `Available:`）、
計画の表と `Transaction Summary` を、**1行ずつ**解説しています。

**最低限、この5つだけは毎回見てください。**

- [ ] **① 外された RPM はないか** … `Examining` と `Marking` の数が一致するか（7.5）
- [ ] **② `Error:` の塊はあるか** … あれば `Requires:` の右側が「足りないもの」
- [ ] **③ `... for dependencies:` はあるか** … あればそれが**取得対象**（7.2）
- [ ] **④ 消えるものはないか** … `Removing` / `Removing for dependencies` / 行中の `replacing`
- [ ] **⑤ 終わり方** … `Exiting on user command` か、`Error:` か、`Nothing to do` か

### 7.4 確認用のまとめログを作って持ち帰る

**下見のログは長いので、要点だけを1つのファイルにまとめて、WinSCP で持ち帰って落ち着いて読みます。**

```bash
$ cd $LOG_DIR                                                      # ログ置き場へ移動する
$ echo "=== 1. いつ・どこで ===" > summary_01.txt                   # 新規作成（以降は >> で追記）
$ date >> summary_01.txt                                           # 日時
$ hostname >> summary_01.txt                                       # サーバー名
$ echo "=== 2. 持ち込んだRPMの数 ===" >> summary_01.txt   # 見出しを追記する
$ ls $RPM_DIR/*.rpm | wc -l >> summary_01.txt                      # 件数
$ echo "=== 3. 読み込みと計画入りの数（一致するのが正常） ===" >> summary_01.txt   # 見出しを追記する
$ grep -c 'Examining ' dryrun_01.txt >> summary_01.txt             # 読み込まれた数
$ grep -c 'Marking '   dryrun_01.txt >> summary_01.txt             # 計画に入った数
$ echo "=== 4. 計画から外されたRPMの警告（空が正常） ===" >> summary_01.txt   # 見出しを追記する
$ grep -E 'Cannot open|Skipping|does not update installed package|Not a compatible architecture|obsoleted by installed package' \
    dryrun_01.txt dryrun_01_repo.txt >> summary_01.txt             # 警告を集める
$ echo "=== 5. 7.1 の結論（リポジトリ無し） ===" >> summary_01.txt   # 見出しを追記する
$ tail -n 5 dryrun_01.txt >> summary_01.txt                        # 末尾だけ
$ echo "=== 6. 足りない条件 ===" >> summary_01.txt   # 見出しを追記する
$ grep 'Requires:' dryrun_01.txt | sort -u >> summary_01.txt       # 条件の一覧
$ echo "=== 7. 要求元とセット ===" >> summary_01.txt   # 見出しを追記する
$ grep -A6 'Error: Package:' dryrun_01.txt >> summary_01.txt       # 要求元・導入済み・候補
$ echo "=== 8. 7.2 でリポジトリから補われたもの（＝取得対象） ===" >> summary_01.txt   # 見出しを追記する
$ grep -A20 -E '^(Installing|Updating|Removing) for dependencies:' dryrun_01_repo.txt >> summary_01.txt   # 取得対象の節
$ echo "=== 9. 7.2 の件数まとめ ===" >> summary_01.txt   # 見出しを追記する
$ grep -A12 'Transaction Summary' dryrun_01_repo.txt >> summary_01.txt   # 件数のまとめ
$ echo "=== ここまで ===" >> summary_01.txt   # 終わりの目印
$ wc -l summary_01.txt                                             # 行数を確認する
$ cat summary_01.txt                                               # 内容を確認する
```

**期待値**：9つの見出しがそろっていて、**4 の節が空**であること

> **最初の1行だけ `>`（上書き）で、あとは `>>`（追記）**です。
> ここを間違えると前の節が消えます。**回ごとに `summary_02.txt` のように番号を変えてください。**

> **`grep` が何も見つけないと、その節は見出しだけになります。**これは正常です。
> **4 の節が見出しだけ＝外された RPM なし**で、これが期待する状態です。

**WinSCP で手元に持ち帰ります。**

1. WinSCP で別システムに接続する
2. **右側のパス欄に `/home/ユーザー名/depcheck_log` を入れて移動**する
3. `summary_01.txt` を選び、**左（手元の Windows）へドラッグする**
4. メモ帳やエディタで開いて、[下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) を見ながら読む

> **元のログ（`dryrun_01.txt` など）も最後にまとめて持ち帰ります**（第10章）。
> **まとめログは「その場で判断するため」、元のログは「証跡として残すため」**です。両方必要です。

### 7.5 黙って外されたRPMがないか確認する

**ここが一番見落としやすい落とし穴です。**`yum` は、RPM ファイルを読めなかったとき、
同じ版が入っているとき、アーキテクチャが合わないときなどに、**警告を1行出すだけでその RPM を計画から外します。**
**外された分を除いた残りで依存が閉じると、ログの最後は `Exiting on user command` になります。**
つまり**「依存OK」に見えるのに、CVE 対応 RPM の一部は何も確認されていない**状態が起こります。

```bash
$ grep -c 'Examining ' $LOG_DIR/dryrun_01.txt        # 読み込まれた RPM の数
$ grep -c 'Marking '   $LOG_DIR/dryrun_01.txt        # 計画に入った RPM の数
$ grep -n 'Skipped (dependency problems)' $LOG_DIR/dryrun_01.txt $LOG_DIR/dryrun_01_repo.txt   # skip_broken による除外
```

**期待値**：`Examining` と `Marking` の数が**一致**し、`Skipped` が**出ない**こと

❌ 数が合わない → 7.4 の「4 の節」に出ている警告が手がかりです。文字列ごとの意味は
[下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) にあります。管理者と次のどちらかを決めてください。

- **別システムに同版が入っているだけ**なら、対象サーバーでは必要なので**そのまま持ち帰る**
- **ファイルが壊れている・アーキテクチャ違い**なら、**取り直す**

> **`Excluding ...` は既定の出力レベルでは出力されないので、grep では見つかりません。**設定のほうを先に見ます。

```bash
$ grep -H -E '^[[:space:]]*(exclude|includepkgs|alwaysprompt|assumeyes|assumeno|skip_broken|localpkg_gpgcheck|tsflags)' \
    /etc/yum.conf /etc/yum.repos.d/*.repo    # 除外や自動応答の設定を確認する
```

**期待値**：`exclude` と `includepkgs` が無い。`alwaysprompt` が `0` でない。`assumeyes` が `1` でない。

❌ `exclude` があった → 下見に `-d 3` を足して実行し、`Excluding` が出ないか確認します。
❌ `assumeyes=1` / `alwaysprompt=0` があった → **`--assumeno` が効かない構成**です。管理者に報告してください。

### 7.6 /tmp に残るファイルの注意

`--assumeno` で中止したとき、**依存解決まで進めた回**は、Yum が計画をファイルに自動保存して案内してきます。

```text
Your transaction was saved, rerun it with:
 yum load-transaction /tmp/yum_save_tx.2026-10-14.10-30.AbCdEf.yumtx
```

> **この案内に従って `yum load-transaction` を実行してはいけません。実更新になります。**

```bash
$ ls -l /tmp/yum_save_tx.*.yumtx             # 自動保存されたファイルを確認する
```

**期待値**：**依存解決まで進んだ回ぶん**のファイルがある（`Error: ... Requires:` で終わった回は作られません）。
**消さなくてよい。承認後に片付けます。**

---

## 8. 足りないRPMの正体を調べる

> **7.2 で `... for dependencies:` に名前と版が出ていれば、この章は飛ばして第9章へ進めます。**
> この章は、**7.2 でも `Error: ... Requires:` が残った**とき（社内リポジトリにも無いとき）に、
> 条件を提供する RPM を自分で探すためのものです。

> **この章と第9章は `yumdownloader` / `repoquery` が使える前提（パターンA）です。**
> 第2章の判定がBだった場合は、[yum-utils が無い場合の依存RPM取得](./手順書_RHEL7_yum-utilsが無い場合の依存RPM取得.md) に差し替えてください。

**`Requires:` に出た条件を、そのままの文字列で検索します。**

```bash
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID --show-duplicates \
    --whatprovides 'openssl-libs >= 1:1.0.2k-26'   # 条件を提供する RPM を探す
```

**表示例**（説明用です）：`openssl-libs-1:1.0.2k-26.el7_9.x86_64` のように、条件を満たす NEVRA が並びます。

**`--whatprovides '条件'` が「その条件を提供している RPM を探す」、`--show-duplicates` が「最新版だけに絞らず複数の版を表示する」**指定です。

> **`Requires:` というラベル自体は入れません。**右側の条件だけを、**必ずクォートで囲んで**渡します。
> **囲まないと `>=` の `>` がリダイレクトとして解釈され**、カレントディレクトリに `=` というファイルができ、版の条件が渡りません。
> **名前だけに削るのもいけません。**`openssl-libs` だけだと**版の条件を満たさないものまで出ます。**

**複数出たときは**、対象サーバーと同じ **`el7`**、条件が `()(64bit)` なら **`x86_64` 版**、
**要求を満たす版で今回の CVE と同じ時期のもの**を選びます。
**同じエラータ（RHSA）の仲間（`openssl` と `openssl-libs` など）はまとめて取る**と、やり直し回数が減ります。

### 見つからないときはグロブで探す

```bash
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID \
    --whatprovides 'libcrypto.so.10()(64bit)'      # そのままの条件で探す（これが基本）
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID \
    --whatprovides 'libcrypto.so.10*'              # 見つからなければ末尾を * にする
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID \
    --whatprovides 'libc.so.6()(64bit)'            # 真ん中のカッコの中身だけ外す
```

> **`libcrypto.so.10()(64bit)` は、カッコまで含めて1つの「提供する機能の名前」**です。検索は完全一致なので、
> **カッコを外した `libcrypto.so.10` では一致しません。**見つからないときは `*` を付けます。
> ただし **`libc.so.6(GLIBC_2.14)(64bit)` のように真ん中のカッコに版が入っている形は別**で、
> **版の部分だけ外した `libc.so.6()(64bit)`** で提供元が見つかります。**末尾の `()(64bit)` は残します。**

**よくある対応表（RHEL 7）**

| 条件の例 | 提供している RPM |
|:--|:--|
| `libcrypto.so.10()(64bit)` / `libssl.so.10()(64bit)` | `openssl-libs` |
| `libk5crypto.so.3()(64bit)` / `libkrb5.so.3()(64bit)` | `krb5-libs` |
| `libz.so.1()(64bit)` | `zlib` |
| `libselinux.so.1()(64bit)` | `libselinux` |
| `libc.so.6()(64bit)` / `libpthread.so.0()(64bit)` | `glibc` |

> **この表は目安です。**必ず `repoquery --whatprovides` で**実際のリポジトリの中身**を確認してください。
> **対象サーバーで今その機能を提供しているパッケージ**は `rpm -q --whatprovides 'libcrypto.so.10()(64bit)'` で調べられます。
> **`rpm -q` は「サーバーに入っているもの」、`repoquery` は「リポジトリにあるもの」**で、調べる相手が違います。

---

## 9. 足りないRPMを取得する

**7.2（または第8章）で決めた NEVRA を指定してダウンロードします。**
**`$HOME/rpm` には直接落としません。**別のフォルダに落として、中身を見てから採用分だけ移します。

```bash
$ mkdir -p $HOME/rpm_dl                      # 取得用の一時フォルダを作る
$ yumdownloader --disablerepo='*' --enablerepo=$REPO_ID \
    --destdir $HOME/rpm_dl 'openssl-libs-1:1.0.2k-26.el7_9.x86_64'   # 版まで指定して取得する
$ echo "exit code: $?"                       # 終了コードを見る
$ ls -l $HOME/rpm_dl                         # 落ちたファイルを見る
```

**期待値**：終了コードが 0 で、**指定した NEVRA のファイルが `$HOME/rpm_dl` にある**

> **`yumdownloader` は「取るだけ」です。別システムにインストールしません。**
> **`--destdir` を指定しないとカレントディレクトリに落ちます。**

> **終了コードが 0 でも、ファイルが増えていないことがあります。必ず `ls` で目で確認してください。**

> **パッケージ名だけを渡さないでください。**
> `yumdownloader openssl-libs` のように名前だけだと**リポジトリの最新版**が取れて、意図した版と違うものが混ざります。

**中身を確認してから、採用するものだけ移します。**

```bash
$ rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' $HOME/rpm_dl/*.rpm   # 版とアーキテクチャの確認
$ rpm -qp --provides $HOME/rpm_dl/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm   # 何を提供するか
$ rpm -qpR $HOME/rpm_dl/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm   # 何を要求するか
$ mv -i $HOME/rpm_dl/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm ${RPM_DIR:?}/   # 採用するものだけ移す
$ ls $RPM_DIR/*.rpm | wc -l                  # 持ち帰る RPM の件数
```

**`--provides` が「その RPM が与える機能」、`-R / --requires` が「その RPM が欲しがる機能」**です。

> **`mv -i` にしているのは、同じ名前のファイルを黙って上書きしないためです。**
> **「上書きしますか」と聞かれたら `n` で止めて**、自分が持ち込んだ RPM と同じ名前でないか確認してください。
> **`mv $HOME/rpm_dl/*.rpm $RPM_DIR/` とまとめて移さないでください。**意図しない依存まで持ち帰ることになります。

> **追加した RPM が、さらに別の RPM を要求することがあります。だから下見をやり直す必要があります。**

### 取得したら必ず7に戻る

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/dryrun_02.txt 2>&1            # 2回目の 7.1（ファイル名の番号を変える）
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/dryrun_02_repo.txt 2>&1       # 2回目の 7.2
$ tail -n 20 $LOG_DIR/dryrun_02.txt          # 7.1 の結果を見る
$ grep -n -E '^(Installing|Updating|Removing) for dependencies:' $LOG_DIR/dryrun_02_repo.txt   # 7.2 の追加分を見る
```

> **ログのファイル名の番号（`_01`, `_02`, `_03` …）を必ず変えてください。**
> 同じ名前にすると**前回の記録が上書きされて消えます。**
> **「何回目で何が足りなかったか」が作業の証跡になります。**

**7.1 が `Exiting on user command` で終わり、かつ 7.2 に `... for dependencies:` が出なくなるまで繰り返します。**
**往復が数回になるのは普通**です。追加した理由は記録表の台帳に書きます。

### 参考 --resolve でまとめて取る場合

```bash
$ yumdownloader --disablerepo='*' --enablerepo=$REPO_ID --resolve \
    --destdir $HOME/resolve_test 'openssh-server'   # 依存ごとまとめて取る（別フォルダへ）
```

> **`--resolve` は「別システムに入っていないもの」だけを取ります。**
> 別システムに入っていて対象サーバーに無いものは**取られないので、結果をそのまま信用しないでください。**
> 同じ弱点の詳しい説明は [yum-utils が無い場合の依存RPM取得](./手順書_RHEL7_yum-utilsが無い場合の依存RPM取得.md) の「この方法の弱点」にあります。

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

> **ログは証跡です**（何回下見して、何が足りなくて、何を追加したか）。**審査や引き継ぎで必ず聞かれます。**
> `$HOME/rpm_dl` に残した「採用しなかった RPM」も、判断の記録として一緒に残しておくと説明しやすくなります。

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
> **「正しい Red Hat の修正版である」ことの確認にはなりません**（それは **RHSA と NEVRA の突き合わせ**で別に行います）。
> **別システムの `$HOME/rpm`・`$HOME/rpm_dl`・`$HOME/depcheck_log` は、照合が終わるまで消さないでください。**
> **削除は社内の承認後**です。ホームは自動では消えないので、作業完了後に自分で片付けます。本書に一括削除コマンドは載せません。

---

## 12. 対象サーバーへ渡す

**ここからは対象サーバー（オフラインの本番機）での作業です。**
**分量があるので別ノートにしています。**

**→ [対象サーバーでの適用前確認](./手順書_RHEL7_対象サーバーでの適用前確認.md)**

社内で承認された方法で `rpm_final.tar.gz` と `rpm_final.tar.gz.sha256` を渡し、
そのノートの手順で **ハッシュ照合 → 現状の記録 → 下見 → トランザクションテスト → 前後比較** まで行います。

> **別システムでの結果は参考値で、最終判断は対象サーバーの結果を使います。**入っているパッケージが違うからです。
> **別システムで「足りないものなし」でも、対象サーバーでは足りないことがあります。**
> 対象サーバーで `Requires:` が出たら、その条件を持ってこの本編の第7〜9章に戻ります。

> **この手順の結果を「本番更新できた」と報告しないでください。**実際にあてる手順はさらに別の作業です
> （[手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) /
> [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md)）。

---

## よく出るメッセージ早見表

| 表示 | 意味 | 次にやること |
|:--|:--|:--|
| `Exiting on user command` | `--assumeno` による正常な中止（終了コード1） | 異常ではない。計画本文を読む |
| `Error: Package: ...` ＋ `Requires: xxx` | 依存が足りない | 条件全文を `repoquery --whatprovides` で調べる |
| `Protected multilib versions` | x86_64 と i686 の版ずれ | **両アーキテクチャを同じ版で**取得する |
| `does not update installed package.` | 同版・旧版が入っていて更新にならない | **計画から外れている。**持ち帰る／取り直すを判断 |
| `No package ... available` | 指定版が見えない | リポジトリID・同期内容・版指定・権利を確認 |
| `Cannot find a valid baseurl` | 取得元・接続・認証の問題 | **依存不足と混同しない。**第6章へ |
| `Nothing to do` | やることが無い | RPM の取り違え、`el7` 以外の混入、適用済みを確認 |

---

## やってはいけないこと

| やってはいけないこと | 理由 |
|:--|:--|
| **`yum load-transaction` を実行する** | `--assumeno` の案内に従うと**実更新になる** |
| **`--nodeps` / `--force` / `--ignorearch`**（`rpm` のオプション） | 依存関係やアーキテクチャの判定を無視してシステムを壊す。**`yum` には無いか意味が違う** |
| **`--skip-broken`** | 問題のあるパッケージを**黙って計画から外す。**CVE 対応の抜けが隠れる |
| **`--nogpgcheck`** | 検証を飛ばす。先へ進めるための道具にしない |
| **RPM を1個ずつ下見する** | 同時更新で解決する関係を「不足」と誤判定する |
| **ログのファイル名を使い回す** | 前回の証跡が消える |
| **転送モードを「テキスト」にする** | RPM とアーカイブが壊れる |

---

## 記録表

### 下見のラウンド記録

| 回 | ログファイル | RPM数 | 結果 | 足りなかった条件 | 追加したNEVRA | 実施日時 | 実施者 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 01 | `dryrun_01.txt` | | | | | | |

### 追加したRPMの台帳

| 不足条件 | 要求していたRPM | 採用NEVRA | 取得リポジトリ・取得日 | 追加理由・承認 |
|:--|:--|:--|:--|:--|
| ログから転記 | ログから転記 | 正確な版 | リポジトリIDと日付 | 対象サーバーの不足解消など |

### 保存されるファイル

| 場所 | ファイル | 内容 |
|:--|:--|:--|
| `$HOME/rpm` / `$HOME/rpm_dl` | `*.rpm` | **持ち帰る中身（RPM だけにする）／取得したが採用しなかったものも証跡として残す** |
| `$HOME/depcheck_log` | `original-inventory.tsv` / `final-inventory.tsv` / `dryrun_01.txt` / `dryrun_01_repo.txt` … | 最初と最後の NEVRA 一覧、各回の下見結果（7.1 と 7.2 の2本） |
| `$HOME/depcheck_log` | `summary_01.txt`, `_02.txt` … | **各回のまとめログ。**WinSCP で持ち帰って読む |
| `$HOME/depcheck_log` | `repolist.txt` | 社内リポジトリの詳細（**社内URLを含む。社外に出さない**） |
| `$HOME` | `rpm_final.tar.gz` ＋ `.sha256` / `depcheck_log.tar.gz` | 持ち帰るアーカイブ |
| 対象サーバー | — | [対象サーバーでの適用前確認](./手順書_RHEL7_対象サーバーでの適用前確認.md) を参照 |

> **認証情報が入った設定ファイル（`.repo` など）は転送しないでください。**

### 完了条件

- [ ] 手元で用意した RPM の数と、別システムに届いた数が一致した
- [ ] 送り・持ち帰りの両方でハッシュ値が一致した
- [ ] 7.1（リポジトリ無し）の最後の下見が `Exiting on user command` で終わった
- [ ] 7.2（リポジトリ有り）に `... for dependencies:` が出なくなった
- [ ] `exclude` / `assumeyes=1` / `alwaysprompt=0` が設定されていないことを確認した
- [ ] **除外警告（`Skipping` / `does not update installed package` など）が出ていない**
- [ ] [対象サーバーでの適用前確認](./手順書_RHEL7_対象サーバーでの適用前確認.md) の完了条件をすべて満たした
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

**公式 man と開発元ソースで確認した事項**：`install` にファイル名を渡すとローカルインストールになること／
**社内リポジトリを有効にすると不足依存がリポジトリから補われる**こと／`--assumeno` 時の `Exiting on user command` と終了コード1／
**`alwaysprompt=0` だと `--assumeno` が働かない計画があり得る**こと／`Cannot open: ... Skipping.` などで
**RPM が黙って計画から外れる**ことと、**`Excluding` だけは既定の出力レベルで出ない**こと／
計画表の見出しに **`Obsoleting` は含まれない**こと／`--assumeno` 中止時の `/tmp/yum_save_tx.*.yumtx` の自動保存（**依存解決まで進んだ回だけ**）／
`localpkg_gpgcheck` の既定が `0` であること／`yum install` が root を要求すること。
ログの文字列の詳細は [下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) の検証範囲にまとめています。

**RHEL 7.9 の実機では未実行**です。**出力例は説明用**で、実機の出力ではありません。
TeraTerm と WinSCP の画面の文言は、**版によって表記が異なる場合があります。**

---

## 変更履歴

| 日付 | 版 | 内容 |
|:--|:--|:--|
| 2026-10-14 | 2.1 | **重大な誤りの修正。**社内リポジトリを有効にしたまま下見すると、Yum が足りない依存を**リポジトリから自動で補って**計画を作るため `Exiting on user command` で正常終了してしまい、**補われた RPM を持ち帰らないまま先へ進む**危険があった。下見を **7.1（リポジトリ無し＝不足の洗い出し）**と**7.2（リポジトリ有り＝取得リスト作り）**の2段に分けた。あわせて **`--setopt=alwaysprompt=1`**（`alwaysprompt=0` だと `--assumeno` が働かない計画がある）、**`${RPM_DIR:?}`**（変数未設定でパスが `/` に化けるのを防ぐ）、**`Excluding` は既定の出力レベルでは出ない**ため設定側を確認する手順、`Skipped (dependency problems)` の確認、`Removing for dependencies` の危険性、取得先を `$HOME/rpm_dl` にして `mv -i` で採用分だけ移す方式、`()(64bit)` は外さずグロブで探すこと、`>=` を囲まないとリダイレクトになること、**`LANG=C` の有効範囲の解説**を追加。アーカイブの送り先を `$HOME` にして `$HOME/rpm/rpm/` の入れ子を解消。第12章は分量が増えたため別ノートへ切り出し |
| 2026-10-14 | 2.0 | **実作業（TeraTerm でログイン → WinSCP で RPM を送る → 不足依存を取得 → WinSCP で持ち帰る）の流れに沿って全面的に書き直し。**シェルスクリプト風の記述（`mktemp`、サブシェル、配列、`set -e`、`for` ループ）を廃止し、**すべて1行ずつのコマンド**にした。作業場所を `$HOME/rpm` と `$HOME/depcheck_log` に固定。社内リポジトリを `/etc/yum.repos.d/internal-rhel7.repo`（`gpgcheck=0`）前提にして**署名検証の章を削除**（代わりに `localpkg_gpgcheck` も `0` である注意を追記）。初心者向けの用語解説、WinSCP のバイナリ転送、ハッシュ値の照合、TeraTerm でのサーバー取り違え防止を追加 |
| 2026-10-14 | 1.1 | **`yum-utils` が使えるかの判定と、パターンBノートへの分岐を追加。**誤りの修正：`Operation aborted` → **`Exiting on user command`**、`rpm -Kv` の失敗語、**`install` / `localinstall` が警告だけで RPM を計画から外すこと**の検出手順、`/tmp/yum_save_tx.*.yumtx`、`--assumeno` では `localpkg_gpgcheck` が働かないこと、`tsflags=test` が `yum history` に残らないこと、`repoquery --pkgnarrow` の man と実装の食い違いを反映 |

---

[← 全体の目次にもどる](../README.md)
