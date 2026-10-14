# RHEL 7.9：不足依存RPMの取得と適用（yum-utils なし）

| | |
|:--|:--|
| **学習の順番** | 実務 ★★★★★ |
| **Ping-t の範囲** | 範囲外（**業務の実作業から作ったノート**） |
| **業務での使いどころ** | **用意した CVE 対応 RPM を、開発環境の RHEL 7.9 へ当てるまでの通し手順。**取得機に `yumdownloader` / `repoquery` が**ない**場合の手順です。標準の `yum` だけで行います。**判定は対象サーバーだけで行い、取得機は RPM を取ってくるだけ**に徹します。切り戻しは別ノートです。 |

> **このフォルダのノート一覧**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [オフラインRPM適用の考え方](./解説_オフラインRPM適用の考え方.md) | **なぜこの手順になるのか。**判定を対象サーバーでしかできない理由、NEVRA と版比較、下見の仕組み、落とし穴8件、`LANG=C` の有効範囲 |
> | 解説 | [下見ログの読み方](./解説_下見ログの読み方.md) | `yum install --assumeno` のログを1行ずつ読む。`Error:` の塊、計画の表、`Transaction Summary`、よくある読み違い |
> | 解説 | [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) | `createrepo` と目次、`clean all`、**署名検証の落とし穴**、エラータ、yum と dnf の違い |
> | 解説 | [依存チェックスクリプトの読み方](./依存チェックスクリプトの読み方.md) | `check_deps.sh` を1ブロックずつ解説 |
> | 手順書 | [不足依存RPMの取得と適用（yum-utils あり）](./手順書_RHEL7_不足依存RPM取得と適用_yum-utilsあり.md) | 取得機に `yumdownloader` / `repoquery` が**ある**場合の通し手順（下見 → 取得 → テスト → 適用） |
> | **手順書** | **このノート（不足依存RPMの取得と適用（yum-utils なし））** | 取得機に `yumdownloader` / `repoquery` が**ない**場合の通し手順（標準の `yum` だけ） |
> | 手順書 | [手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) | ローカルリポジトリから openssh を更新する通し手順 |
> | 手順書 | [手順書 RHEL 8 以降 openssh の更新](./手順書_RHEL8以降_openssh更新.md) | `dnf` 版の同じ手順 |
> | 手順書 | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) | ローカルリポジトリを作って「確認 → 追加」を繰り返す方式 |
> | 手順書 | [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) | `dnf` 版の同じ手順 |

> **公式ドキュメントの確認日: 2026-10-14。**
> **コマンドの実在とメッセージの文字列は、Yum 3 系・Yum Utils・RPM 4.11 系の公式 man と開発元ソースで確認**しています。
> **RHEL 7.9 の実機では未実行です。**出力例は「こういう形で出る」という説明用で、値（版・件数・サイズ）は架空です。
> 実行前に、対象サーバーの `man yum` と `yum --help` でも裏を取ってください。

> **コードブロックの先頭の `$ ` は入力しません。**プロンプトの印として書いてあるだけです。

---

## 目次

- [この手順書でやること](#この手順書でやること)
- [1.【手元】RPM を1つにまとめる](#1【手元】rpm-を1つにまとめる)
- [2.【C】ログインして作業場所を用意する](#2【c】ログインして作業場所を用意する)
- [3.【C】現在の状態を記録する](#3【c】現在の状態を記録する)
- [4.【手元→C】RPM を送って展開する](#4【手元→c】rpm-を送って展開する)
- [5.【C】下見する](#5【c】下見する)
- [6.【C】足りない条件の一覧を作って持ち出す](#6【c】足りない条件の一覧を作って持ち出す)
- [7.【B】足りない RPM を取得する（標準の yum だけ）](#7【b】足りない-rpm-を取得する標準の-yum-だけ)
  - [7.1 取得機にログインして作業場所を用意する](#71-取得機にログインして作業場所を用意する)
  - [7.2 社内リポジトリを確認する](#72-社内リポジトリを確認する)
  - [7.3 条件からパッケージ名と版を決める](#73-条件からパッケージ名と版を決める)
  - [7.4 取得する](#74-取得する)
  - [7.5 取得したものを確認してまとめる](#75-取得したものを確認してまとめる)
- [8.【B→手元→C】取得した RPM を持ち帰って追加する](#8【b→手元→c】取得した-rpm-を持ち帰って追加する)
  - [8.1 取得機から手元へ、手元から対象サーバーへ運ぶ](#81-取得機から手元へ手元から対象サーバーへ運ぶ)
  - [8.2【C】照合して展開し、採用するものだけ移す](#82【c】照合して展開し採用するものだけ移す)
  - [8.3【C】もう一度下見する](#83【c】もう一度下見する)
- [9.【C】トランザクションテストをする](#9【c】トランザクションテストをする)
- [10.【C】適用する](#10【c】適用する)
- [11.【C】適用後の確認](#11【c】適用後の確認)
- [付録A よく出るメッセージ](#付録a-よく出るメッセージ)
- [付録B 記録表](#付録b-記録表)
  - [ラウンド記録](#ラウンド記録)
  - [採用・不採用の台帳](#採用・不採用の台帳)
  - [作られるファイル](#作られるファイル)
  - [完了条件](#完了条件)
- [付録C やってはいけないこと](#付録c-やってはいけないこと)
- [付録D 根拠と検証範囲](#付録d-根拠と検証範囲)
- [変更履歴](#変更履歴)

---

## この手順書でやること

**用意した RPM を、開発環境の対象サーバーへ当てます。**

| 呼び名 | 何をする場所 | 接続方法 |
|:--|:--|:--|
| **対象サーバー（C）** | **判定と適用。**開発環境の RHEL 7.9。**ここの結果だけが正解** | TeraTerm／WinSCP |
| **取得機（B）** | 社内リポジトリにつながる RHEL 7.9。**RPM を取ってくるだけ** | TeraTerm／WinSCP |
| 手元の Windows | 運ぶ・保管する | — |

```text
手元     ① RPM を tar.gz にまとめる
  │ WinSCP
  ▼
C        ② 作業場所を用意する
         ③ 現在の状態を記録する
         ④ 展開する
    ┌──▶ ⑤ 下見する ← ★ 足りないものを決めるのはここだけ
    │       ├─ 足りない条件あり ─────┐
    │       └─ 無し ───────────────┐ │
    │                               │ │
    │    ⑥ 条件の一覧を作る          │ │
    │ WinSCP（手元経由）             │ │
    │  ▼                            │ │
    │ B  ⑦ 条件を提供する RPM を取得  │ │
    │ WinSCP（手元経由）             │ │
    │  ▼                            │ │
    └─ C ⑧ 追加する ────────────────┘ │
                                      ▼
C        ⑨ トランザクションテスト（tsflags=test）
         ⑩ 適用する
         ⑪ 適用後の確認
```

> **足りないものを決めるのは、対象サーバー（C）だけです。**
> 「足りない」の判定は**そのサーバーに入っているパッケージとの比較**なので、
> 入っているものが違う取得機（B）で判定すると**取りこぼします。**
> 例：`openssl-libs >= 1:1.0.2k-26` が要るとき、**B にその版が入っていると B では不足に出ず、取得もされません。**
> C には古い版しか無ければ、そのまま進めて**最後に足りないことが分かります。**
> 理由の詳しい説明は [オフラインRPM適用の考え方](./解説_オフラインRPM適用の考え方.md) にあります。

**始める前にそろえておくもの**

- [ ] 対象サーバー（C）と取得機（B）が**同じ RHEL 7.9・同じアーキテクチャ**であること
- [ ] C は**開発環境**であること（この手順書は実際にパッケージを更新します）
- [ ] 当てる RPM 一式と、対応する **CVE / RHSA の一覧**
- [ ] 社内リポジトリのリポジトリID（既定の例では `internal-rhel7`）
- [ ] C のバックアップ（スナップショット等）と、戻し方の確認
- [ ] 作業の承認、停止してよい時間帯、連絡先

---

## 1.【手元】RPM を1つにまとめる

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

**期待値**：`rpm.tar.gz` ができてサイズが 0 ではない。**`Hash` 欄の値をメモしておく**（転送後の照合に使います）

> **`tar` が使えないと言われたら**、7-Zip などで `tar.gz` を作ってください（tar にしてから gzip にする2段階です）。
> **`.zip` は避けたほうが安全**です。展開に `unzip` が必要で、RHEL 7 に入っていないことがあります。
> **RPM は圧縮済みなので小さくはなりません。**1ファイルにまとめて**転送の抜けを防ぐ**ためにやっています。

---

## 2.【C】ログインして作業場所を用意する

**TeraTerm の操作**

1. TeraTerm を起動して「新しい接続」
2. **ホスト**に**対象サーバー**の IP かホスト名
3. **サービス**は **SSH**、**SSHバージョン**は **SSH2** を選んで「OK」
4. ユーザー名とパスワード（または鍵）を入れて「OK」

```bash
$ export LANG=C                              # この接続だけメッセージを英語にそろえる
$ hostname                                   # 今いるサーバー名
$ cat /etc/redhat-release                    # OS の版
$ rpm -E 'el%{rhel}'                         # メジャーバージョンの記号
$ uname -m                                   # CPU アーキテクチャ
```

**期待値**

| コマンド | 期待する表示 |
|:--|:--|
| `hostname` | **対象サーバー**の名前（取得機ではないこと） |
| `cat /etc/redhat-release` | `Red Hat Enterprise Linux Server release 7.9 (Maipo)` |
| `rpm -E 'el%{rhel}'` | **`el7`** |
| `uname -m` | 取得機と同じ（通常 `x86_64`） |

> **いちばん多い事故が「サーバーを間違える」ことです。`hostname` を必ず見てから**先に進んでください。

**作業場所を2つ作ります。**

```bash
$ export RPM_DIR=$HOME/rpm                   # RPM を置く場所
$ export LOG_DIR=$HOME/depcheck_log          # ログを置く場所
$ mkdir -p $RPM_DIR                          # RPM 置き場を作る
$ mkdir -p $LOG_DIR                          # ログ置き場を作る
$ echo "RPM_DIR=$RPM_DIR LOG_DIR=$LOG_DIR"   # 値が入っているか確認する
$ ls -ld $RPM_DIR $LOG_DIR                   # 2つできたか確認する
```

**期待値**：`/home/ユーザー名/rpm` と `/home/ユーザー名/depcheck_log` が表示される（空が1つでもあれば `export` からやり直す）

> **この手順書で作るファイルは、この2か所にしか置きません。**
>
> | 置き場所 | 中身 |
> |:--|:--|
> | **`$RPM_DIR`（`$HOME/depcheck_log` ではないほう）** | **当てる RPM だけ。**ログは置かない |
> | **`$LOG_DIR`（`$HOME/depcheck_log`）** | **ログと記録だけ。**RPM は置かない |
>
> **ログを読み書きするときは、いつも `$LOG_DIR/ファイル名` とフルパスで書きます。**
> `cd $LOG_DIR` してファイル名だけで書くと、**どこに出ているのか分からなくなる**ので、この手順書では `cd` しません。

> **SSH を切って入り直したら、`export` を全部もう一度実行してください**（値はその接続の中だけで有効です）。
> **`LANG=C`** は、RHEL 7 の日本語環境だと **yum のメッセージが日本語になる**ためです。英語のほうが調べやすく `grep` もしやすい。
> `exit` すれば元に戻ります（仕組みは [オフラインRPM適用の考え方](./解説_オフラインRPM適用の考え方.md) に）。

**最後に、道具がそろっているか確認します。**

```bash
$ rpm -q yum rpm                             # yum と rpm が入っているか
$ which tar sha256sum                        # まとめる・ハッシュを取る道具
```

**期待値**：`yum` と `rpm` と `tar` と `sha256sum` が表示される

> **このノートは `yum-utils` を使わない前提**なので、対象サーバーにも取得機にも `yum-utils` は要りません。


---

## 3.【C】現在の状態を記録する

**当てる前の状態を残します。後で「何が変わったか」を見るのに使います。**

```bash
$ rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' | sort \
    > $LOG_DIR/installed-before.tsv          # 導入済みパッケージの一覧
$ wc -l $LOG_DIR/installed-before.tsv        # 何パッケージ入っているか
$ uname -r > $LOG_DIR/running-kernel.txt     # 動いているカーネル
$ cat $LOG_DIR/running-kernel.txt            # 内容を確認する
$ df -h / /var /boot > $LOG_DIR/disk-space.txt   # 空き容量
$ cat $LOG_DIR/disk-space.txt                # 内容を確認する
```

**期待値**：`installed-before.tsv` の行数が 0 ではない。`/var` と `/boot` に十分な空きがある

> **この記録はバックアップではありません。**`installed-before.tsv` からシステムを復元することはできません。
> **バックアップ（スナップショット等）は、この手順書を始める前に取っておいてください。**

**yum の設定と、もともとの不整合も見ておきます。**

```bash
$ grep -H -E '^[[:space:]]*(exclude|includepkgs|alwaysprompt|assumeyes|assumeno|skip_broken|localpkg_gpgcheck|tsflags)' \
    /etc/yum.conf /etc/yum.repos.d/*.repo    # 除外や自動応答の設定を確認する
$ sudo yum --noplugins --disablerepo='*' check \
    > $LOG_DIR/yum-check-before.log 2>&1     # 既存の依存不整合を調べる
$ echo "check exit code: $?"                 # 終了コードを見る
$ cat $LOG_DIR/yum-check-before.log          # 結果を見る
```

**期待値**：`exclude` と `includepkgs` が無い。`assumeyes=1` と `alwaysprompt=0` が無い。`check` の終了コードが 0

❌ **`assumeyes=1` または `alwaysprompt=0` があった** → **`--assumeno` が効かない構成**です。
　このまま下見すると**意図せず適用される可能性**があります。**先へ進めず管理者に報告**してください。
❌ **`check` が 0 以外** → **もともと不整合があります。**内容を管理者に確認してください。
　**今回の RPM が原因だと決めつけないでください。**

---

## 4.【手元→C】RPM を送って展開する

**WinSCP の操作**

1. WinSCP を起動して、**対象サーバー**への接続（サイト）を作る
2. **ファイルプロトコル**を **SFTP**、**ホスト名**に対象サーバーの IP かホスト名
3. ユーザー名とパスワード（または鍵）を入れて「ログイン」
4. 画面が左右に分かれる。**左が手元の Windows、右が対象サーバー**
5. **右側のパス欄に `/home/ユーザー名` を入れて移動**する（**`/rpm` は付けません**）
6. 左側で `C:\work\rpm.tar.gz` を選び、**右へドラッグする**

> **送り先は `$HOME` です。`$RPM_DIR` ではありません。**
> アーカイブの中身が `rpm/` というフォルダなので、**`$HOME` で展開すると `$HOME/rpm/`（＝`$RPM_DIR`）ができます。**
> `$RPM_DIR` に送って展開すると `$HOME/rpm/rpm/` という余計な入れ子ができます。

> **転送モードは「バイナリ」にしてください。**既定は「自動」で拡張子から判定します。
> **「テキスト」で転送されると改行コードが書き換えられて壊れます。**
> 画面の項目名は WinSCP の版や日本語化の有無で変わるので、**実際の画面の表記に読み替えてください。**

**届いたことを確認します。**

```bash
$ ls -l $HOME/rpm.tar.gz                     # 届いたファイルを見る
$ sha256sum $HOME/rpm.tar.gz                 # ハッシュ値を計算する
```

**期待値**：サイズが手元の `dir` と同じで、**ハッシュ値が第1章でメモした値と一致する**

❌ **ハッシュ値が違う** → 転送中に壊れています。**転送モードがバイナリか確認して送り直してください。**

**中身を見てから展開します。ここで止まれるようにブロックを分けています。**

```bash
$ cd $HOME                                   # ホームへ移動する
$ tar -tzf rpm.tar.gz                        # 中身を一覧する（まだ展開しない）
$ tar -tzf rpm.tar.gz | wc -l                # 中身の数（rpm/ の行も1行入る）
```

**期待値**：すべての行が **`rpm/` で始まっている**こと

❌ **絶対パス（先頭が `/`）や `../` がある** → **展開しないでください。**想定外の場所にファイルが置かれます。

```bash
$ cd $HOME                                   # ホームへ移動する
$ tar -xzf rpm.tar.gz                        # 展開する（$HOME/rpm/ ができる）
$ ls $RPM_DIR/*.rpm | wc -l                  # RPM の数を数える
$ ls $RPM_DIR | grep -v '\.rpm$'             # RPM 以外が混ざっていないか
$ rm -f $HOME/rpm.tar.gz                     # 送ってきたアーカイブを消す
```

**期待値**：RPM の数が**手元で用意した数と一致**し、`grep` が**何も表示しない**

❌ **`$HOME/rpm/rpm` ができた** → アーカイブを `$RPM_DIR` に送ってしまっています。手順 5 の送り先を確認してください。

**RPM の中身を一覧にして記録します。**

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
> **RPM の数と CVE の数は対応しません。**1つの CVE 対応に複数の RPM が必要なこともあります。

---
## 5.【C】下見する

**ここで「何が足りないか」を決めます。この判定は対象サーバーでしかできません。**

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/dryrun_01.txt 2>&1            # 全部まとめて1回だけ下見する
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 20 $LOG_DIR/dryrun_01.txt          # ログの最後を見る
```

> **RPM が何個あっても、下見は1回だけです。1個ずつやってはいけません。**
> 持ち込んだ RPM は**お互いの依存を満たし合っています。**
> たとえば `openssh-server` が要求する `openssh-libs` が同じ一式の中にあれば、まとめて渡せば問題ありません。
> ところが**1個ずつ下見すると仲間が見えないので「足りない」と出ます。**
> **偽の不足がログに並び、本当に足りないものが埋もれます。**

**なぜこの形なのか**

| 指定 | 理由 |
|:--|:--|
| `install` に**ファイルパス**を渡す | `yum` は**ファイル名を渡されるとローカルインストールとして扱う**（`yum.8` に明記）。`localinstall` は公式に「互換のため残しているだけ」とされているので `install` を使う |
| **全部まとめて**渡す | 上のとおり。1個ずつは誤判定のもと |
| `--assumeno` | 確認に自動で「いいえ」と答える。**この実行では絶対に適用されない** |
| `--setopt=alwaysprompt=1` | **確認を必ず出させる。**`alwaysprompt=0` の環境では確認が出ない計画で `--assumeno` が働かないため（保険） |
| `--disablerepo='*'` | **リポジトリを一切使わない。**持ち込んだ RPM と、**このサーバーに入っているもの**だけで判定する |
| `--noplugins` | versionlock などプラグイン由来の制約を外す。**`yum.conf` の `exclude` は外れない** |
| `${RPM_DIR:?}` | 変数が空のときに `/*.rpm` へ化けるのを防ぐ。**未設定ならその場でエラーになる** |
| `> $LOG_DIR/... 2>&1` | 出力が長く画面では読めない。`2>&1` で**エラー出力も同じファイルへ**送る |
| `sudo` | `yum install` は **root でないと実行できない**（`You need to be root to perform this command.`） |

**結果の読み方**

| ログの最後に出ている文 | 意味 | 次にやること |
|:--|:--|:--|
| **`Error: Package: ...` ＋ `Requires: xxx`** | **足りない依存がある**（よくある） | **第6章へ**（条件の一覧を作る） |
| **`Exiting on user command`** | **足りない依存は無い** | **第9章へ**（トランザクションテスト） |
| **`Protected multilib versions`** | 32bit 版と 64bit 版の版ずれ | **i686 版も同じ版で取得する**。条件を第6章の一覧に手で足す |
| **`Nothing to do`** | やることが無い | RPM の取り違え、`el7` 以外の混入、すでに同じ版が入っている |

> **`Exiting on user command` は「成功」です。**`--assumeno` で「いいえ」と答えた正常な中止で、**終了コードは 1** になります。
> 終了コードだけ見て「失敗した」と思わないでください。
> **`Operation aborted.` は RHEL 8 以降の `dnf` の表示で、RHEL 7 の `yum` では出ません。**
> 文字で探すときは、版による大文字小文字の違いを避けて `grep -i 'exiting on user'` が確実です。
> `This system is not registered with an entitlement server.` は**無視してよい**です。

**計画から黙って外された RPM がないかを必ず確認します。**

```bash
$ grep -c 'Examining ' $LOG_DIR/dryrun_01.txt        # 読み込まれた RPM の数
$ grep -c 'Marking '   $LOG_DIR/dryrun_01.txt        # 計画に入った RPM の数
$ grep -n -E 'Cannot open|Skipping|does not update installed package|Not a compatible architecture|obsoleted by installed package' \
    $LOG_DIR/dryrun_01.txt                           # 外された理由を探す
$ grep -n 'Skipped (dependency problems)' $LOG_DIR/dryrun_01.txt   # skip_broken による除外
```

**期待値**：`Examining` と `Marking` の数が**一致**し、下2つの `grep` が**何も表示しない**こと

❌ **数が合わない／警告が出た** → **その RPM は計画に入っていません。**
　**残りだけで依存が閉じると `Exiting on user command` になるので、「問題なし」に見えてしまいます。**
　文字列ごとの意味は [下見ログの読み方](./解説_下見ログの読み方.md) にあります。次のどちらかを決めてください。

- **すでに同じ版が入っているだけ**（`does not update installed package.`）なら、**当てる必要が無い**ので台帳に理由を書いて外す
- **ファイルが壊れている・アーキテクチャ違い**なら、**取り直す**

> **`Excluding ...` は既定の出力レベルでは出力されないので、`grep` では見つかりません。**
> 第3章で `exclude` が無いことを確認済みなら問題ありません。
> `exclude` があった場合は、上の下見に **`-d 3`** を足して実行すると `Excluding` が表示されます。

---

## 6.【C】足りない条件の一覧を作って持ち出す

**取得機へ持っていくのは「条件の一覧」だけです。RPM は運びません。**

```bash
$ grep 'Requires:' $LOG_DIR/dryrun_01.txt | sed 's/.*Requires: *//' | sort -u \
    > $LOG_DIR/requires_01.txt               # 足りない条件だけを抜き出す
$ cat $LOG_DIR/requires_01.txt               # 内容を確認する
$ wc -l $LOG_DIR/requires_01.txt             # 条件の数
$ grep -A6 'Error: Package:' $LOG_DIR/dryrun_01.txt \
    > $LOG_DIR/errors_01.txt                 # 要求元・導入済み・候補もセットで残す
$ cat $LOG_DIR/errors_01.txt                 # 内容を確認する
```

**`requires_01.txt` の表示例**（説明用です）

```text
libcrypto.so.10()(64bit)
openssl-libs >= 1:1.0.2k-26
```

**`errors_01.txt` の表示例**（説明用です）

```text
Error: Package: openssh-server-7.4p1-23.el7_9.x86_64 (/openssh-server-7.4p1-23.el7_9.x86_64)
           Requires: openssl-libs >= 1:1.0.2k-26
           Installed: openssl-libs-1:1.0.2k-21.el7_9.x86_64 (@anaconda)
               openssl-libs = 1:1.0.2k-21.el7_9
```

| 行 | 読み方 |
|:--|:--|
| `Error: Package: NEVRA (出どころ)` | **この RPM が困っている。**カッコが `/` で始まればあなたが渡したファイル |
| `Requires: 条件` | **足りないもの。**これを取得機で検索します |
| `Installed: NEVRA (@リポジトリ)` | **いまこのサーバーに入っている版。**`@` 付きは「導入済み」の印 |
| （字下げ行） | その版が実際に提供している内容。`Requires:` と見比べると、なぜ足りないかが分かる |
| `Available:` | リポジトリにこの版がある、という情報（リポジトリ無しの下見では通常出ません） |

ログの読み方の詳細は [下見ログの読み方](./解説_下見ログの読み方.md) にまとめてあります。

**WinSCP で手元に持ち出します。**

1. WinSCP で**対象サーバー**に接続する
2. **右側のパス欄に `/home/ユーザー名/depcheck_log` を入れて移動**する
3. `requires_01.txt`、`errors_01.txt`、`dryrun_01.txt` を選び、**左（手元の Windows）へドラッグする**

> **`dryrun_01.txt` は長いので、手元のエディタで開いて [下見ログの読み方](./解説_下見ログの読み方.md) を見ながら読みます。**
> 取得機へ持っていくのは `requires_01.txt` だけで足ります。

> **`requires_01.txt` が、次の章で取得機に渡す「買い物リスト」です。**
> ❌ `requires_01.txt` が**空**だった場合は、足りない条件がありません。**第9章へ進んでください。**

---
## 7.【B】足りない RPM を取得する（標準の yum だけ）

**取得機にログインして、`requires_01.txt` に並んだ条件を1件ずつ調べて取得します。`yumdownloader` と `repoquery` は使わず、標準の `yum` だけで行います。**

| yum-utils が要るもの | ここで使う代わり | 差がある点 |
|:--|:--|:--|
| `repoquery --whatprovides '条件'` | **`yum provides '条件'`** | man には名前とファイルglobだけと書いてあるが、実装は `名前 演算子 版` も解釈する（ソースで確認・実機未検証）。**うまくいかないときは名前だけで検索して 7.4 で版を選ぶ** |
| `repoquery --show-duplicates` | **`yum --showduplicates list all 名前`** | `info` / `list` / `search` に効く |
| `yumdownloader --destdir DIR` | **`yum install --downloadonly --downloaddir=DIR`** | **取得機にすでに入っている版は落ちない**（7.5 参照） |

### 7.1 取得機にログインして作業場所を用意する

```bash
$ export LANG=C                              # この接続だけメッセージを英語にそろえる
$ hostname                                   # 今いるサーバー名（取得機であること）
$ cat /etc/redhat-release                    # OS の版（対象サーバーと同じ 7.9 か）
$ uname -m                                   # アーキテクチャ（対象サーバーと同じか）
$ export REPO_ID=internal-rhel7              # 社内リポジトリのID（7.2 で確認する）
$ export DL_DIR=$HOME/rpm_dl                 # 取得した RPM を置く場所
$ export LOG_DIR=$HOME/depcheck_log          # ログを置く場所
$ mkdir -p $DL_DIR                           # 取得先を作る
$ mkdir -p $LOG_DIR                          # ログ置き場を作る
$ echo "DL_DIR=$DL_DIR LOG_DIR=$LOG_DIR"     # 値が入っているか確認する
$ yum --help | grep -c downloadonly          # --downloadonly が使えるか確認する
```

**期待値**：ホスト名が表示され、OS とアーキテクチャが対象サーバーと一致。最後が **1以上**

❌ **最後が `0`** → その `yum` に `--downloadonly` がありません（古い版では `yum-plugin-downloadonly` が要ります）。管理者に相談してください。

### 7.2 社内リポジトリを確認する

```bash
$ cat /etc/yum.repos.d/internal-rhel7.repo          # 設定の中身を見る
$ grep '^\[' /etc/yum.repos.d/internal-rhel7.repo   # リポジトリIDを取り出す
$ yum --disablerepo='*' --enablerepo=$REPO_ID repolist -v \
    > $LOG_DIR/repolist.txt 2>&1                    # 詳しい情報をログに保存する
$ grep -E 'Repo-id|Repo-name|Repo-baseurl|Repo-pkgs' $LOG_DIR/repolist.txt   # 要点だけ見る
```

**期待値**：`grep '^\['` が `[internal-rhel7]` のような1行。`Repo-pkgs` が 0 ではない

❌ **ID が違った** → `export REPO_ID=実際のID` で入れ直してください。**`[ ]` の中がIDで、ファイル名とは別物**です。
❌ **`Cannot find a valid baseurl`** → **リポジトリへの接続・認証の問題**です。依存不足とは別の話なので混同しないでください。

### 7.3 条件からパッケージ名と版を決める

```bash
$ yum --disablerepo='*' --enablerepo=$REPO_ID provides 'libcrypto.so.10()(64bit)' \
    > $LOG_DIR/provides_01.txt 2>&1          # 機能を提供するパッケージを探す
$ cat $LOG_DIR/provides_01.txt               # 結果を見る
```

**1件ごとに「NEVRA : 概要」の行と `Repo` の行が出ます**
（例：`1:openssl-libs-1.0.2k-26.el7_9.x86_64 : A general purpose cryptography library`）。
ここで知りたいのは**パッケージ名**（この例なら `openssl-libs`）です。**先頭の `1:` は Epoch** で、0 のときは省略されます。

**見つからないときは、ワイルドカードにします。**

```bash
$ yum --disablerepo='*' --enablerepo=$REPO_ID provides 'libcrypto.so.10*'   # 末尾を * にして探す
$ yum --disablerepo='*' --enablerepo=$REPO_ID provides '*/libcrypto.so.10'  # ファイルパスとして探す
$ yum --disablerepo='*' --enablerepo=$REPO_ID provides 'libc.so.6()(64bit)' # 真ん中のカッコの中身だけ外す
```

> **`libcrypto.so.10()(64bit)` は、カッコまで含めて1つの「提供する機能の名前」**です。検索は完全一致なので、
> **カッコを外した `libcrypto.so.10` では一致しません。**見つからないときは `*` を付けます。
> ただし **`libc.so.6(GLIBC_2.14)(64bit)` のように真ん中のカッコに版が入っている形は別**で、
> **版の部分だけ外した `libc.so.6()(64bit)`** で見つかります（**末尾の `()(64bit)` は残す**）。

**どの RPM が提供しているかの目安**は [オフラインRPM適用の考え方](./解説_オフラインRPM適用の考え方.md) の対応表にあります。
**ただし目安なので、必ず上の検索で実際のリポジトリの中身を確認してください。**

**次に、その名前で版の候補を並べて選びます。**

```bash
$ yum --disablerepo='*' --enablerepo=$REPO_ID --showduplicates list all openssl-libs \
    > $LOG_DIR/versions_01.txt 2>&1          # 利用できる版を全部並べる
$ cat $LOG_DIR/versions_01.txt               # 結果を見る
```

**表示例**（説明用です）：`Available Packages` の下に
`openssl-libs.x86_64      1:1.0.2k-26.el7_9      internal-rhel7` のような行が並びます。
**左から、パッケージ名.アーキテクチャ／Epoch:Version-Release／リポジトリID** です。
ここから、**`requires_01.txt` の条件を満たし、対象サーバーと同じ `el7`** のものを選びます。

> **`list all` にする理由**：`list available` は**取得機にすでに入っている版を除いて**表示するため、
> **「必要な版が、取得機に入っているせいで候補から消えている」**状況に気づけません。
> **`--showduplicates` が無いと最新版しか出ません。**条件が「ちょうどこの版」のときに取り違えます。

### 7.4 取得する

```bash
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID \
    --downloadonly --downloaddir=$DL_DIR \
    install 'openssl-libs-1:1.0.2k-26.el7_9' \
    > $LOG_DIR/download_01.txt 2>&1          # インストールせずにダウンロードだけする
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 10 $LOG_DIR/download_01.txt        # 結果を見る
$ ls -lt $DL_DIR | head -n 5                 # 落ちたファイルを見る
```

**期待値**：ログの最後に **`exiting because "Download Only" specified`** が出て、`$DL_DIR` に RPM が増えている

> **`--downloadonly` は確認プロンプトを出しません**（Yum が `-y` と同じ扱いにするため）。
> **`--assumeno` を足してはいけません。**中止になって何も落ちません。
> **依存もまとめて落ちる**ので、対象サーバーに要らないものが混ざります。第8章で選別します。

❌ **`Nothing to do` / `Package ... already installed and latest version`**
　→ **その版が取得機にすでに入っています。**何も落ちません。次のコマンドで取り直してください。

```bash
$ rpm -q openssl-libs                        # 取得機に入っている版を見る
$ sudo yum --disablerepo='*' --enablerepo=$REPO_ID \
    --downloadonly --downloaddir=$DL_DIR reinstall openssl-libs \
    > $LOG_DIR/download_reinstall_01.txt 2>&1   # 導入済みと同じ版をダウンロードする
$ echo "exit code: $?"                       # 終了コードを見る
$ ls -lt $DL_DIR | head -n 5                 # 落ちたファイルを見る
```

> **`reinstall` で取れるのは「いま取得機に入っているのと同じ版」だけ**です（`yum.8`：
> *"Will reinstall the identically versioned package as is currently installed"*）。
> **必要な版がそれと違うなら取れません。**その場合は **`yum-utils` の導入を依頼**するか、
> **社内リポジトリから直接ファイルを受け取る**ことを管理者と相談してください。
> **カーネルなどの installonly パッケージには `reinstall` を使えません**（`yum.8` に明記）。

**`requires_01.txt` の行を上から順に、全部処理します。**

❌ **どの検索でも見つからない条件があった**
　→ **社内リポジトリにその RPM がありません。**取得元の同期内容・コンテンツ世代・ELS の権利を管理者に確認してください。

### 7.5 取得したものを確認してまとめる

```bash
$ ls $DL_DIR/*.rpm | wc -l                   # 取得した件数
$ rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' $DL_DIR/*.rpm \
    > $LOG_DIR/downloaded-inventory.tsv      # 取得したものの NEVRA 一覧
$ cat $LOG_DIR/downloaded-inventory.tsv      # 内容を確認する
$ ls $DL_DIR | grep -v '\.rpm$'              # RPM 以外が混ざっていないか
$ cd $HOME                                   # ホームへ移動する
$ tar -czf add_01.tar.gz -C $HOME rpm_dl     # 取得分をまとめる
$ sha256sum $HOME/add_01.tar.gz > $HOME/add_01.tar.gz.sha256   # ハッシュ値を残す
$ cat $HOME/add_01.tar.gz.sha256             # ハッシュ値を表示してメモする
$ tar -tzf $HOME/add_01.tar.gz | head -n 5   # 中身の先頭を確認する
```

**期待値**：すべて `el7` で、アーキテクチャが対象サーバーに合っていること。`grep` が**何も表示しない**こと
（依存でまとめて落ちたものが混ざっています。第8章で、実際に必要なものだけを採用します）

---
## 8.【B→手元→C】取得した RPM を持ち帰って追加する

### 8.1 取得機から手元へ、手元から対象サーバーへ運ぶ

1. WinSCP で**取得機**に接続し、**右側のパス欄に `/home/ユーザー名`** を入れて移動する
2. `add_01.tar.gz` と `add_01.tar.gz.sha256` を**左（手元）へドラッグ**する
3. WinSCP で**対象サーバー**に接続し、**右側のパス欄に `/home/ユーザー名`** を入れて移動する
4. 手元の `add_01.tar.gz` と `add_01.tar.gz.sha256` を**右へドラッグ**する

> **転送モードはどちらも「バイナリ」**です。

### 8.2【C】照合して展開し、採用するものだけ移す

```bash
$ cd $HOME                                   # ホームへ移動する
$ sha256sum -c $HOME/add_01.tar.gz.sha256    # ハッシュ値を照合する
$ tar -tzf $HOME/add_01.tar.gz | head -n 5   # 中身の先頭を確認する
$ tar -xzf $HOME/add_01.tar.gz               # 展開する（$HOME/rpm_dl/ ができる）
$ ls $HOME/rpm_dl/*.rpm | wc -l              # 届いた件数
$ rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' $HOME/rpm_dl/*.rpm   # NEVRA を確認する
```

**期待値**：`add_01.tar.gz: OK` と表示され、取得機での件数と一致すること

❌ **`FAILED`** → 転送で壊れています。**先へ進めず、運び直してください。**

**採用するものだけを `$RPM_DIR` へ移します。**

```bash
$ mv -i $HOME/rpm_dl/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm ${RPM_DIR:?}/   # 1件ずつ移す
$ ls $RPM_DIR/*.rpm | wc -l                  # 当てる RPM の件数
$ ls $HOME/rpm_dl                            # 採用しなかったものを確認する
```

> **`mv -i` にしているのは、同じ名前のファイルを黙って上書きしないためです。**
> **「上書きしますか」と聞かれたら `n` で止めて**、自分が用意した RPM と同じ名前でないか確認してください。
> **`mv $HOME/rpm_dl/*.rpm $RPM_DIR/` とまとめて移さないでください。**
> 依存でまとめて落ちた、対象サーバーには要らないものまで混ざります。
> **採用しなかったものは `$HOME/rpm_dl` に残したままにします。**「何が落ちてきて何を採用しなかったか」が証跡になります。

**採用の理由を、付録Bの台帳に書きます。**

### 8.3【C】もう一度下見する

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/dryrun_02.txt 2>&1            # 2回目の下見（番号を変える）
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 20 $LOG_DIR/dryrun_02.txt          # ログの最後を見る
$ grep -c 'Examining ' $LOG_DIR/dryrun_02.txt   # 読み込まれた RPM の数
$ grep -c 'Marking '   $LOG_DIR/dryrun_02.txt   # 計画に入った RPM の数
```

| 結果 | 次にやること |
|:--|:--|
| **`Exiting on user command`** で終わり、`Examining` と `Marking` が一致 | **第9章へ** |
| **`Error: ... Requires:`** がまだ残る | **第6章に戻る**（`requires_02.txt` を作り、第7章で取得し直す） |

> **ログのファイル名の番号（`_01`, `_02`, `_03` …）を必ず変えてください。**
> 同じ名前にすると**前回の記録が上書きされて消えます。**
> **「何回目で何が足りなかったか」が作業の証跡になります。**

> **追加した RPM が、さらに別の RPM を要求することがあります。**往復が数回になるのは普通です。

---

## 9.【C】トランザクションテストをする

**実行条件**：第8.3 の下見が `Exiting on user command` で終わっていること。

> **`--setopt=tsflags=test` が、この章で実際の更新を防ぐ唯一の指定です。削除・省略しないでください。**
> **`-y` は付けません。**確認画面で計画をもう一度見ます。

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=tsflags=test \
    install ${RPM_DIR:?}/*.rpm \
    2>&1 | tee $LOG_DIR/test.txt             # ファイルを書き換えないテストをする
$ echo "yum の終了コード: ${PIPESTATUS[0]}"    # パイプの1番目（yum）の終了コードを見る
```

**確認画面（`Is this ok [y/d/N]:`）が出たら、`y` を入れる前に次の3つを必ず見てください。**

| 確認すること | 理由 |
|:--|:--|
| 画面の上のほうに **`Invalid tsflag in config file`** が出ていないこと | **出ていたら `tsflags=test` が効いていません。**`y` を入れると**本当に更新されます** |
| 自分が打った行に `--setopt=tsflags=test` が入っていること | 打ち間違いの確認 |
| 計画の内容が第8.3 の下見で見たものと同じであること | 想定外の追加・削除がないか |

❌ 1つでも違ったら、**`N`（または Enter）で中止**してください。

**計画の読み方**

| 計画に出る表示 | 読み方・確認すること |
|:--|:--|
| `Installing` | **新規導入。**入れてよいものか |
| `Updating` | 既存パッケージの更新。**意図した版か** |
| `Installing for dependencies` / `Updating for dependencies` | **依存の都合で足されたもの。**`$RPM_DIR` の中にあるはず |
| `Removing` と行中の `replacing` | 削除・置換。**想定外なら中断** |
| **`Removing for dependencies`** | **依存の都合で何かが消える計画。**サービス停止につながるので**中断して確認** |
| カーネルの追加・旧版削除 | **起動と復旧用カーネルへの影響**を確認 |

> **`Obsoleting` は Yum 3 の計画表の見出しではありません。**
> 置き換えは **`Removing` と、各行に続く `replacing`** で表示されます（`Obsoleting` は `yum history` 側の状態名です）。

**結果を確認します。**

```bash
$ grep -n 'Invalid tsflag' $LOG_DIR/test.txt   # 念のためログでも確認する
$ tail -n 30 $LOG_DIR/test.txt                 # 結果を見る
```

**期待値**：`Invalid tsflag` が**出ていない**こと。ログの中に次の3つが順に出ていること

```text
Running transaction check
Running transaction test
Transaction test succeeded
```

> **`Transaction test succeeded` の後に `Running transaction` と出ても、ファイルは更新されません。**
> `tsflags=test` が付いていると、RPM 側の処理が実際の書き込みを行う前に戻ります（スクリプトも実行されません）。
> **このテストは `yum history` に記録されません。**`tsflags` に `test` が入っていると Yum は履歴の記録自体を行いません。

**テストの前後でパッケージ一覧が変わっていないことを確認します。**

```bash
$ rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' | sort \
    > $LOG_DIR/installed-after-test.tsv      # テスト後の一覧を取る
$ diff -u $LOG_DIR/installed-before.tsv $LOG_DIR/installed-after-test.tsv   # 前後を比べる
$ echo "diff の終了コード: $?"                 # 差分があれば 1 になる
```

**期待値**：**差分なし**（終了コードが 0）

❌ **差分があった** → **適用へ進まないでください。**ほかの管理処理が同時に動いていないかも含めて調査します。

---

## 10.【C】適用する

> **ここから実際にパッケージが更新されます。**
> **第9章のテストが `Transaction test succeeded` で通っていること**、**バックアップがあること**、
> **停止してよい時間帯であること**を確認してから実行してください。

```bash
$ sudo yum --noplugins --disablerepo='*' install ${RPM_DIR:?}/*.rpm \
    2>&1 | tee $LOG_DIR/apply.txt            # 実際に適用する
$ echo "yum の終了コード: ${PIPESTATUS[0]}"    # パイプの1番目（yum）の終了コードを見る
```

**確認画面が出たら、計画が第9章で見たものと同じであることを確認して `y` を入力します。**

> **`--setopt=tsflags=test` が無いことを確認してください。**この章では付けません。
> **`-y` も付けません。**計画を目で見てから進めます。
> **`tee` を使っているのは、画面を見ながらログも残すためです。**
> `> ファイル` だと確認画面が見えません。なお `tee` 経由だとプロンプトの文字が出ないまま入力待ちになることがあります
> （Python 2 の入力処理の都合。**実機未検証**）。その場合も入力は受け付けられているので、`y` または `N` と改行を入力してください。

**期待値**：ログに次の流れが出て、**最後が `Complete!`**、`yum の終了コード` が **0**

```text
Running transaction check
Running transaction test
Transaction test succeeded
Running transaction
  Updating   : openssl-libs-1:1.0.2k-26.el7_9.x86_64                       1/4
  Installing : openssh-7.4p1-23.el7_9.x86_64                               2/4
  Verifying  : openssh-7.4p1-23.el7_9.x86_64                               3/4
  Verifying  : openssl-libs-1:1.0.2k-26.el7_9.x86_64                       4/4

Installed:
  openssh.x86_64 0:7.4p1-23.el7_9

Updated:
  openssl-libs.x86_64 1:1.0.2k-26.el7_9

Complete!
```

**最後のまとめに出る見出し**

| 見出し | 意味 |
|:--|:--|
| `Installed` | 新しく入ったもの（自分で指定したもの） |
| `Dependency Installed` | **依存の都合で入ったもの** |
| `Updated` / `Dependency Updated` | 更新されたもの／依存の都合で更新されたもの |
| `Removed` / `Dependency Removed` | 消えたもの／依存の都合で消えたもの |
| `Replaced` | 置き換えられたもの |
| **`Failed`** | **失敗したもの。1件でもあれば完了にしない** |
| **`Skipped (dependency problems)`** | **依存の問題で飛ばされたもの。1件でもあれば完了にしない** |

❌ **`Complete!` が出ない／終了コードが 0 以外**
　→ ログの `Error:` を読み、**第11章の確認をしてから**管理者に報告してください。
　**途中で止まった場合も `rpm -qa` は第11章の手順で必ず取ってください。**

---

## 11.【C】適用後の確認

**何が変わったかを記録します。**

```bash
$ rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' | sort \
    > $LOG_DIR/installed-after.tsv           # 適用後の一覧を取る
$ diff -u $LOG_DIR/installed-before.tsv $LOG_DIR/installed-after.tsv \
    > $LOG_DIR/installed-diff.txt            # 前後の差分をファイルに残す
$ cat $LOG_DIR/installed-diff.txt            # 差分を見る
$ wc -l $LOG_DIR/installed-diff.txt          # 差分の行数
```

**期待値**：`+` の行が**当てた RPM の NEVRA** になっていて、`-` の行が**その前の版**になっていること

**依存が壊れていないかを確認します。**

```bash
$ sudo yum --noplugins --disablerepo='*' check \
    > $LOG_DIR/yum-check-after.log 2>&1      # 適用後の依存不整合を調べる
$ echo "check exit code: $?"                 # 終了コードを見る
$ cat $LOG_DIR/yum-check-after.log           # 結果を見る
$ diff $LOG_DIR/yum-check-before.log $LOG_DIR/yum-check-after.log   # 作業前と比べる
```

**期待値**：終了コードが 0。作業前と差分なし

❌ **0 以外になった／作業前に無かった不整合が出た** → **完了にしないでください。**内容を控えて管理者に報告します。

**履歴に残っていることを確認します。**

```bash
$ sudo yum history list > $LOG_DIR/history.txt 2>&1   # 履歴の一覧
$ head -n 10 $LOG_DIR/history.txt            # 先頭（いちばん新しいもの）を見る
```

**期待値**：いちばん上の行が、**今回の適用**（日時とパッケージ数が合っている）

> **この ID を控えておいてください。**切り戻すときに使います（切り戻しは別ノートです）。
> **第9章のテストは履歴に残りません。**ここに出るのは第10章の適用だけです。

**再起動やサービス再起動が必要かを調べます。**

```bash
$ uname -r                                   # 動いているカーネル
$ rpm -q --last kernel | head -n 3           # 入っているカーネル（新しい順）
$ grep -A20 -E '^(Installed|Updated|Dependency Installed|Dependency Updated):' \
    $LOG_DIR/apply.txt                       # 何が入った・更新されたかを見る
```

**判定のしかた**

| 見るところ | 再起動・再起動が要るか |
|:--|:--|
| `uname -r` と `rpm -q --last kernel` の先頭が**違う** | **サーバーの再起動が必要**（新しいカーネルが入っている） |
| 更新されたものに `glibc` / `openssl-libs` / `systemd` などの共有ライブラリがある | **そのライブラリを使っているサービスの再起動が必要**。どれが該当するかは管理者と確認 |
| 更新されたものがサービス本体（`openssh-server` など） | **そのサービスの再起動が必要** |

> **`yum-utils` の `needs-restarting` が使えれば一発で分かりますが、このノートは使わない前提**なので、
> **更新されたものの一覧から人が判断**します。判断に迷ったら、開発環境なので**サーバーごと再起動する**のがいちばん確実です。

```bash
$ systemctl status sshd                      # 例：sshd の状態と起動時刻を見る
```

> **`Active: active (running) since ...` の時刻が更新より前なら、まだ古いプロセスが動いています。**
> 再起動が必要なサービスは `sudo systemctl restart サービス名` で再起動し、**もう一度 `systemctl status` で確認**します。

**CVE が直ったかは別の確認です。**

```bash
$ rpm -q openssh openssh-server              # 例：当てたパッケージの版を確認する
```

> **依存が閉じて適用が成功したことと、目的の CVE が直ったことは別です。**
> **RHSA に載っている修正後の NEVRA と、いま入っている NEVRA を突き合わせて**確認してください。
> Red Hat は修正を既存の版へ取り込む「バックポート」を行うため、**上流のバージョン番号では判定できません**
> （[Red Hat：Security Backporting Practice](https://access.redhat.com/security/updates/backporting)）。

**ログを手元へ持ち出して保管します。**

```bash
$ cd $HOME                                   # ホームへ移動する
$ tar -czf depcheck_log.tar.gz -C $HOME depcheck_log   # ログ一式をまとめる
$ ls -l $HOME/depcheck_log.tar.gz            # サイズを確認する
```

WinSCP で `depcheck_log.tar.gz` を手元へ持ち出し、社内の保管先へ入れます。

> **`$RPM_DIR`・`$HOME/rpm_dl`・`$LOG_DIR` は、保管が終わるまで消さないでください。**
> **削除は社内の承認後**です。ホームは自動では消えないので、作業完了後に自分で片付けます。

---

## 付録A よく出るメッセージ

**メッセージの意味と対処は [下見ログの読み方](./解説_下見ログの読み方.md) と
[オフラインRPM適用の考え方](./解説_オフラインRPM適用の考え方.md) にまとめてあります。**
この手順書の中では、各ステップの直後に ❌ で分岐を書いてあります。

**とくに取り違えやすい3つ**

| 表示 | 意味 |
|:--|:--|
| `Exiting on user command` | **`--assumeno` による正常な中止。**終了コードは 1 だが失敗ではない |
| `Invalid tsflag in config file` | **`tsflags` の指定が効いていない。**そのまま `y` を入れると実更新になる |
| `does not update installed package.` | **その RPM は計画から外れている。**同版・旧版がすでに入っている |

---

## 付録B 記録表

### ラウンド記録

| 回 | 下見ログ | 当てるRPM数 | 結果 | 足りなかった条件 | 追加したNEVRA | 実施日時 | 実施者 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 01 | `dryrun_01.txt` | | | | | | |
| 02 | `dryrun_02.txt` | | | | | | |

### 採用・不採用の台帳

| 取得した NEVRA | 採用 / 不採用 | 理由 | 取得日 |
|:--|:--|:--|:--|
| | | | |

### 作られるファイル

| 場所 | ファイル | 内容 |
|:--|:--|:--|
| C `$HOME/rpm` | `*.rpm` | **当てる RPM だけ** |
| C `$HOME/rpm_dl` | `*.rpm` | 取得したが採用しなかったもの（証跡） |
| C `$HOME/depcheck_log` | `installed-before.tsv` / `installed-after.tsv` / `installed-diff.txt` | 適用前後の導入済み一覧と差分 |
| C `$HOME/depcheck_log` | `dryrun_01.txt` / `requires_01.txt` / `errors_01.txt` … | 各回の下見と、そこから作った一覧 |
| C `$HOME/depcheck_log` | `test.txt` / `apply.txt` / `history.txt` | テスト・適用・履歴 |
| C `$HOME/depcheck_log` | `yum-check-before.log` / `yum-check-after.log` | 依存不整合の確認 |
| B `$HOME/depcheck_log` | `repolist.txt` | 社内リポジトリの詳細（**社内URLを含む。社外に出さない**） |

### 完了条件

- [ ] 作業前に `yum check` が 0 で終わり、`exclude` / `assumeyes=1` / `alwaysprompt=0` が無いことを確認した
- [ ] 下見で `Examining` と `Marking` の数が一致した（黙って外された RPM が無い）
- [ ] 最後の下見が `Exiting on user command` で終わった
- [ ] 計画に意図しない新規導入・削除・置換がない（**`Removing for dependencies` が無い**）
- [ ] `Invalid tsflag` が出ずに `Transaction test succeeded` になった
- [ ] テスト前後の導入済み一覧に差分がなかった
- [ ] 適用が `Complete!`・終了コード 0 で終わり、`Failed` と `Skipped (dependency problems)` が 0 件だった
- [ ] 適用後の `yum check` が 0 で、作業前と差分がない
- [ ] `yum history list` の先頭が今回の適用で、ID を控えた
- [ ] 再起動・サービス再起動の要否を判断し、必要なら実施して確認した
- [ ] 各 CVE・RHSA と、いま入っている NEVRA の対応を確認した
- [ ] 採用・不採用の理由を台帳に記録した
- [ ] ログ一式を保管し、サーバー名・日時・実施者を対応付けた

---

## 付録C やってはいけないこと

| やってはいけないこと | 理由 |
|:--|:--|
| **取得機（B）で「足りない」を判定する** | B と対象サーバーで入っているものが違う。**取りこぼす** |
| **RPM を1個ずつ下見する** | 仲間どうしが満たし合う依存を「足りない」と誤判定する |
| **第9章で `--setopt=tsflags=test` を省く／打ち間違える** | **本当に更新される。**`Invalid tsflag` が出ていないか必ず確認する |
| **`yum load-transaction` を実行する** | `--assumeno` の案内に従うと**実更新になる** |
| **`-y` を付ける** | 計画を見ずに進めてしまう |
| **`--nodeps` / `--force` / `--ignorearch` / `--skip-broken` / `--nogpgcheck`** | 依存・アーキテクチャ・検証の判定を飛ばす。**CVE 対応の抜けが隠れる** |
| **`mv $HOME/rpm_dl/*.rpm $RPM_DIR/`** | 対象サーバーに要らない依存まで当ててしまう |
| **ログのファイル名を使い回す** | 前回の証跡が消える |
| **転送モードを「テキスト」にする** | RPM とアーカイブが壊れる |

ほかの禁止事項は [オフラインRPM適用の考え方](./解説_オフラインRPM適用の考え方.md) にまとめてあります。

---

## 付録D 根拠と検証範囲

**このノートのコマンド・オプション・メッセージの文字列は、Yum 3 系・Yum Utils・RPM 4.11 系の公式 man と
開発元ソースで確認しています。**参照した資料の一覧と、確認した項目の詳細は
[オフラインRPM適用の考え方](./解説_オフラインRPM適用の考え方.md) の「根拠と検証範囲」にまとめてあります。

> **RHEL 7.9 の実機では未実行です。**出力例は説明用で、値（版・件数・サイズ）は架空です。
> **`tee` 経由での確認画面の見え方**、**`needs-restarting` の終了コードの意味**、
> **WinSCP と TeraTerm の画面の文言**（版や日本語化で変わります）は**未検証**です。
> 実行前に `man yum` と `yum --help` で裏を取ってください。

---

## 変更履歴

| 日付 | 版 | 内容 |
|:--|:--|:--|
| 2026-10-14 | 1.0 | 初版。**判定を対象サーバーだけで行い、取得機は RPM を取ってくるだけ**という役割分担に組み直して新設。下見は**まとめて1回**（1個ずつは誤判定）、`--setopt=alwaysprompt=1` の保険、`${RPM_DIR:?}` による変数未設定の防止、`Examining` と `Marking` の数で**黙って外された RPM** を見つける方法、**`Invalid tsflag` の確認**（打ち間違えると実更新になる）、ログは `$LOG_DIR/` のフルパスで統一（`cd` しない）、適用と適用後の確認まで記載 |

---

[← 全体の目次にもどる](../README.md)
