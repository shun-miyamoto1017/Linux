# RHEL 7.9：対象サーバーでの適用前確認

| | |
|:--|:--|
| **学習の順番** | 実務 ★★★★★ |
| **Ping-t の範囲** | 範囲外（**業務の実作業から作ったノート**） |
| **業務での使いどころ** | **集めた RPM を、オフラインの本番サーバーへ「あてる前」に確認するところだけ**を切り出した手順。ハッシュ照合 → 下見 → トランザクションテスト（`tsflags=test`）→ 前後比較。**実際にあてる作業は含みません。** |

> **このフォルダは「解説」と「手順書」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) | **なぜこの手順になるのか**。`createrepo` と目次、`clean all`、`--assumeno`、**署名検証の落とし穴**、エラータ、yum と dnf の違い |
> | 手順書 | [手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) | `yum` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 8 以降 openssh の更新](./手順書_RHEL8以降_openssh更新.md) | `dnf` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) | `yum` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) | `dnf` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [社内リポジトリ接続機で不足依存RPMを集めて持ち帰る](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md) | **本編。**TeraTerm と WinSCP を使った実作業の通し手順。別システムへ RPM を送る → 足りない依存を下見する → 取得する → 持ち帰る |
> | 手順書 | [yum-utils が無い別システムで不足依存RPMを取得する](./手順書_RHEL7_yum-utilsが無い場合の依存RPM取得.md) | 本編の第8・9章の差し替え。`yum provides` → `yum --showduplicates list` → `yum install --downloadonly` |
> | **手順書** | **このノート（対象サーバーでの適用前確認）** | **本編の続き。**持ち帰った RPM を対象サーバーで確認する（ハッシュ照合 → 下見 → トランザクションテスト → 前後比較） |
> | 解説 | [下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) | **`yum install --assumeno` のログの読み方。**行の形ごとの意味、`Error:` の塊の読み方、計画の表と `Transaction Summary` の読み方、よくある読み違い |
> | 解説 | [依存チェックスクリプトの読み方](./依存チェックスクリプトの読み方.md) | `check_deps.sh` を 1 ブロックずつ解説。**元版にあった不具合と、実機で確かめた修正内容** |
>
> **`dnf` / `yum` そのもののコマンド解説**は [07_パッケージ管理](../07_パッケージ管理/dnf解説①_基本とインストール系コマンド.md) にあります。

> **公式ドキュメントの確認日: 2026-10-14。**引用はその時点の記載です。
> **コマンドの実在とメッセージの文字列は、Yum 3 系と RPM 4.11 系の公式 man・開発元ソースで確認**しています。
> **RHEL 7.9 の実機で取った出力ではありません。**出力例は「こういう形で出る」という説明用です。

---

## 目次

- [この手順書でやること](#この手順書でやること)
- [1. 送って展開し、現状を記録する](#1-送って展開し現状を記録する)
- [2. 下見する](#2-下見する)
- [3. トランザクションテストをする](#3-トランザクションテストをする)
- [4. ここで確認できないこと](#4-ここで確認できないこと)
  - [完了条件](#完了条件)
- [やってはいけないこと](#やってはいけないこと)
- [公式参照](#公式参照)
  - [この文書の検証範囲](#この文書の検証範囲)
- [変更履歴](#変更履歴)

---

## この手順書でやること

**[本編](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md) で集めて持ち帰った RPM を、対象サーバー（オフラインの本番機）で確認します。**

```text
本編 第11章  WinSCP で持ち帰る
      │
      └─[社内で承認された方法で渡す]──▶ 対象サーバー
                                            │ 1. ハッシュ照合 → 展開 → 現状の記録
                                            │ 2. 下見（install --assumeno）
                                            │ 3. トランザクションテスト（tsflags=test）
                                            │ 4. 前後のパッケージ一覧を比較
                                            ▼
                                     更新作業の審査へ（実更新は別の作業）
```

> **このノートに「実際にあてる手順」は含みません。**
> **`--assumeno` と `--setopt=tsflags=test` しか使いません。**パッケージは1つも更新されません。

> **別システムでの結果は参考値です。最終判断はここでの結果を使います。**
> 入っているパッケージが違うので、**別システムで「足りないものなし」でも、対象サーバーでは足りないことがあります。**

**作業承認を得てから実施してください。**テストでもログ・キャッシュ・ロック用ファイル、
`/tmp` のトランザクション保存ファイルが作られます。

> **コードブロックの先頭の `$ ` は入力しません。**プロンプトの印として書いてあるだけです。

---

## 1. 送って展開し、現状を記録する

社内で承認された方法で、本編で作った `rpm_final.tar.gz` と `rpm_final.tar.gz.sha256` を渡します。

```bash
$ export LANG=C                              # この接続だけメッセージを英語にそろえる
$ export RPM_DIR=$HOME/rpm                   # RPM 置き場
$ export LOG_DIR=$HOME/depcheck_log          # ログ置き場
$ mkdir -p $LOG_DIR                          # ログ置き場を作る
$ echo "RPM_DIR=$RPM_DIR LOG_DIR=$LOG_DIR"   # 値が入っているか確認する
```

> **`export LANG=C` はこの接続の中だけで有効**で、`exit` すれば元の `ja_JP.UTF-8` に戻ります。
> 仕組みと、戻らないときの確認方法は
> [本編の「LANG=C は exit したら元に戻るのか」](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md#langc-は-exit-したら元に戻るのか) にあります。

**まず中身を確認します。ここで止まれるように、展開とはブロックを分けています。**

```bash
$ cd $HOME                                   # ホームへ移動する
$ sha256sum -c rpm_final.tar.gz.sha256       # ハッシュ値を照合する
$ tar -tzf rpm_final.tar.gz | head -n 5      # 中身の先頭を確認する
$ tar -tzf rpm_final.tar.gz | wc -l          # 中身の数（rpm/ の行も1行入る）
```

**期待値**：`rpm_final.tar.gz: OK` と表示され、すべての行が **`rpm/` で始まっている**こと

❌ `FAILED` / `NG` → **転送で壊れています。**先へ進めず、渡し直してください。
❌ 絶対パス（先頭が `/`）や `../` がある → **展開しないでください。**想定外の場所にファイルが置かれます。

**確認できたら展開します。**

```bash
$ cd $HOME                                   # ホームへ移動する
$ tar -xzf rpm_final.tar.gz                  # 展開する（$HOME/rpm/ ができる）
$ ls $RPM_DIR/*.rpm | wc -l                  # RPM の数を数える
$ ls $RPM_DIR | grep -v '\.rpm$'             # RPM 以外が混ざっていないか
```

**期待値**：RPM の数が**別システムでの最終件数と一致**し、最後の `grep` が**何も表示しない**

**作業前の状態を記録します。**

```bash
$ cat /etc/redhat-release > $LOG_DIR/os.txt  # OS の版を記録する
$ uname -r > $LOG_DIR/running-kernel.txt     # 動いているカーネルを記録する
$ rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' | sort \
    > $LOG_DIR/installed-before.tsv          # 導入済み一覧を記録する
$ wc -l $LOG_DIR/installed-before.tsv        # 何パッケージ入っているか
$ df -h / /var /boot > $LOG_DIR/disk-space.txt   # 空き容量を記録する
$ cat $LOG_DIR/disk-space.txt                # 空き容量を確認する
```

> **この記録はバックアップではありません。**`installed-before.tsv` からシステムを復元することはできません。
> **バックアップと復元試験は、実更新の前に別途必要**です。

**設定と、もともとの不整合も見ておきます。**

```bash
$ grep -H -E '^[[:space:]]*(exclude|includepkgs|alwaysprompt|assumeyes|assumeno|skip_broken|localpkg_gpgcheck|tsflags)' \
    /etc/yum.conf /etc/yum.repos.d/*.repo    # 除外や自動応答の設定を確認する
$ rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE}\n'   # 登録済みの公開鍵
$ sudo yum --noplugins --disablerepo='*' check \
    > $LOG_DIR/yum-check-before.log 2>&1     # 既存の依存不整合を調べる
$ echo "check exit code: $?"                 # 終了コードを見る
$ cat $LOG_DIR/yum-check-before.log          # 結果を見る
```

**期待値**：`exclude` と `includepkgs` が無い。`assumeyes=1` と `alwaysprompt=0` が無い。`check` の終了コードが 0

❌ `assumeyes=1` / `alwaysprompt=0` があった → **`--assumeno` が効かない構成**です。**先へ進めず管理者に報告**してください。
❌ `check` が 0 以外 → **もともと不整合があります。**管理者に確認してください。**今回の RPM が原因だと決めつけないでください。**

---

## 2. 下見する

**外部リポジトリを一切使わず、持ち込んだ RPM だけで依存が閉じるかを見ます。**

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/offline-dryrun.txt 2>&1       # 外部リポジトリ無しで下見する
$ echo "exit code: $?"                       # 終了コードを見る
$ tail -n 30 $LOG_DIR/offline-dryrun.txt     # 結果を見る
```

| 指定 | 理由 |
|:--|:--|
| `--disablerepo='*'` | **外部リポジトリを一切使わない。**持ち込んだ RPM だけで閉じるかを見る |
| `--noplugins` | versionlock などプラグイン由来の制約を外す。**`yum.conf` の `exclude` は外れない** |
| `--assumeno` | 確認に自動で「いいえ」と答える。**実更新を絶対にしない** |
| `--setopt=alwaysprompt=1` | **確認を必ず出させる**（`alwaysprompt=0` の環境で `--assumeno` が働かない事故を防ぐ保険） |
| `${RPM_DIR:?}` | 変数が空のときに `/*.rpm` へ化けるのを防ぐ。**未設定ならその場でエラーになる** |
| `sudo` | `yum install` は **root でないと実行できない**（`You need to be root to perform this command.`） |

**計画の読み方**

| 計画に出る表示 | 読み方・確認すること |
|:--|:--|
| `Installing` | **新規導入。**追加して良いものか承認を確認する |
| `Updating` | 既存パッケージの更新。**意図した版か** |
| `Installing for dependencies` / `Updating for dependencies` | **依存の都合で足されたもの。**持ち込んだ RPM に含まれているか確認する |
| `Removing` と行中の `replacing` | 削除・置換。**想定外なら中断** |
| **`Removing for dependencies`** | **依存の都合で何かが消える計画。**サービス停止につながるので**中断して管理者に確認** |
| カーネルの追加・旧版削除 | **起動と復旧用カーネルへの影響**を個別に確認 |
| `Requires:` / `Error:` | **依存不足。**本編の第7〜9章に戻って別システムで取り直す |
| `Nothing to do` | 対象なし。**目的達成とは限らない** |
| `Exiting on user command` | `--assumeno` による正常な中止。**終了コードは1**。異常ではない |

> **`Obsoleting` は Yum 3 の計画表の見出しではありません。**
> 置き換えは **`Removing` と、各行に続く `replacing`** で表示されます。
> （`Obsoleting` は `yum history` 側の状態名です。）

**黙って計画から外された RPM がないかを確認します。**

```bash
$ grep -n -E 'Cannot open|Skipping|does not update installed package|Not a compatible architecture|obsoleted by installed package' \
    $LOG_DIR/offline-dryrun.txt              # 計画から外された RPM の警告を探す
$ grep -n 'Skipped (dependency problems)' $LOG_DIR/offline-dryrun.txt   # skip_broken による除外
```

**期待値**：**どちらも何も表示されない**

❌ 表示された → **その RPM は計画に入っていません。**本編の第7章の表を見て、持ち帰るか取り直すかを管理者と決めてください。

> **`Excluding ...` は既定の出力レベル（`debuglevel=2`）では出ません。**
> Yum のソース上、この行は debug レベルで出力されます。**grep しても引っかからない**ので、
> 第1章で `exclude` の設定が無いことを確認しておくことが、この確認の代わりになります。
> `exclude` があった場合は、上の下見に `-d 3` を足して実行し、`Excluding` が出ないか確認します。

> **「渡したのに計画に出てこない RPM」が、いちばん危険な見落としです。**
> 気になるパッケージは `grep -o 'openssh[^ ]*' $LOG_DIR/offline-dryrun.txt | sort -u` のように**名前で探して**確かめてください。

---

## 3. トランザクションテストをする

**実行条件**：計画の内容と、versionlock・exclude などの運用条件を管理者が確認済みであること。

> **`--setopt=tsflags=test` が実更新を防ぐ重要な指定です。削除・省略しないでください。**
> **`-y` は付けません。**確認画面で計画をもう一度見ます。

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=tsflags=test \
    install ${RPM_DIR:?}/*.rpm \
    2>&1 | tee $LOG_DIR/offline-test.txt     # ファイルを書き換えないテストをする
```

**確認画面（`Is this ok [y/d/N]:`）が出たら、`y` を入れる前に次の3つを必ず見てください。**

| 確認すること | 理由 |
|:--|:--|
| 画面の上のほうに **`Invalid tsflag in config file`** が出ていないこと | **出ていたら `tsflags=test` が効いていません。**`y` を入れると**本当に更新されます** |
| 自分が打った行に `--setopt=tsflags=test` が入っていること | 打ち間違いの確認 |
| 計画の内容が第2章で見たものと同じであること | 想定外の追加・削除がないか |

❌ 1つでも違ったら、**`N`（または Enter）で中止**してください。

```bash
$ grep -n 'Invalid tsflag' $LOG_DIR/offline-test.txt   # 念のためログでも確認する
$ tail -n 30 $LOG_DIR/offline-test.txt                 # 結果を見る
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
> **実施記録はこのログファイルで残してください。**

> **`tee` を使っているのは、確認画面を見ながらログも残すためです。**
> `> ファイル` だと確認画面が見えません。なお `tee` 経由だとプロンプトの文字が出ないまま入力待ちになることがあります
> （Python 2 の入力処理の都合。**実機未検証**）。その場合も入力は受け付けられているので、
> 計画を確認したうえで `y` または `N` と改行を入力してください。

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

**`/tmp` に残るファイルも確認しておきます。**

```bash
$ ls -l /tmp/yum_save_tx.*.yumtx             # 自動保存されたファイルを確認する
```

> **`yum load-transaction` を実行してはいけません。実更新になります。**消さずに残し、承認後に片付けます。

---

## 4. ここで確認できないこと

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

### 完了条件

- [ ] `sha256sum -c` が `OK` で、RPM の数が別システムでの最終件数と一致した
- [ ] `exclude` / `assumeyes=1` / `alwaysprompt=0` が無いことを確認した
- [ ] 作業前の `yum check` が 0 で終わった（0 以外なら管理者と合意した）
- [ ] 計画に意図しない新規導入・削除・置換がない（**`Removing for dependencies` が無い**）
- [ ] 計画から外された RPM の警告が出ていない
- [ ] 持ち込んだ RPM が計画に現れている
- [ ] `Invalid tsflag` が出ていない
- [ ] `Transaction test succeeded` になった
- [ ] テスト前後の導入済み一覧に差分がない
- [ ] ログ一式を保管し、サーバー名・日時・実施者を対応付けた

---

## やってはいけないこと

| やってはいけないこと | 理由 |
|:--|:--|
| **`--setopt=tsflags=test` を省く／打ち間違える** | **本当に更新されます。**`Invalid tsflag` が出ていないか必ず確認する |
| **`yum load-transaction` を実行する** | `--assumeno` の案内に従うと**実更新になる** |
| **`-y` を付ける** | 確認画面で計画を見られなくなる |
| **`--nodeps` / `--force` / `--ignorearch`**（`rpm` のオプション） | 依存関係やアーキテクチャの判定を無視してシステムを壊す |
| **`--skip-broken`** | 問題のあるパッケージを**黙って計画から外す。**CVE 対応の抜けが隠れる |
| **`--nogpgcheck`** | 検証を飛ばす。先へ進めるための道具にしない |
| **`rpm -Uvh *.rpm`（`--test` 無し）** | yum の依存解決・運用設定と評価が違う。**カーネルの installonly 扱いも異なる** |
| **`.repo` を作る／`yum install` で何かを入れる** | 本番機の恒久的な構成変更。この手順では不要 |
| **ロックファイルを消す** | 別の処理が動いている可能性がある。管理者に確認する |

---

## 公式参照

| 資料 | 本書で確認した内容 |
|:--|:--|
| [Red Hat：RHEL 7 System Administrator's Guide — Yum](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-yum) | RHEL 7 の Yum、ローカル RPM の扱い |
| [Yum開発元：yum(8)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.8) | `install` にファイル名を渡すとローカルインストールになること、`--assumeno`、`check`、リポジトリ指定 |
| [Yum開発元：yum.conf(5)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.conf.5) | `tsflags`（`test` を含む）、`alwaysprompt`、`assumeno`、`exclude`、`localpkg_gpgcheck` |
| [RPM開発元：RPM 4.11系 rpm(8)](https://raw.githubusercontent.com/rpm-software-management/rpm/rpm-4.11.x/doc/rpm.8) | `-qa`、`--qf`、`--test` |

### この文書の検証範囲

**公式 man と開発元ソースで確認した事項**：`--assumeno` 時の `Exiting on user command` と終了コード1／
`alwaysprompt=0` だと `--assumeno` が働かない計画があり得ること／
不正な `tsflags` は **`Invalid tsflag in config file` を出すだけで処理が続く**こと／
`tsflags=test` のとき RPM 側の処理が書き込み前に戻り、**`yum history` にも記録されない**こと／
`Cannot open: ... Skipping.`・`does not update installed package.`・`Not a compatible architecture`・
`It is obsoleted by installed package` が既定の出力レベルで出るのに対し、**`Excluding` は debug レベルで出ない**こと／
計画表の見出しに `Obsoleting` が無いこと／`yum install` が root を要求すること。

**RHEL 7.9 の実機では未実行**です。**出力例は説明用**で、実機の出力ではありません。
`tee` 経由での確認画面の見え方は未検証です。

---

## 変更履歴

| 日付 | 版 | 内容 |
|:--|:--|:--|
| 2026-10-14 | 1.0 | 初版。[本編](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md) の第12章を、分量が増えたため別ノートに切り出して新設。**`Invalid tsflag` の確認**（打ち間違えると実更新になる）、`--setopt=alwaysprompt=1` の保険、`${RPM_DIR:?}` による変数未設定の防止、**`Excluding` は既定の出力レベルでは出ない**ことと設定側の事前確認、`Removing for dependencies` の危険性、`Skipped (dependency problems)` の確認を追加 |

---

[← 全体の目次にもどる](../README.md)
