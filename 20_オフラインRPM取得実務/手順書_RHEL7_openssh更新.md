# 手順書 RHEL 7.9 openssh の更新

| | |
|:--|:--|
| **学習の順番** | 実務 ★★★★☆ |
| **Ping-t の範囲** | 範囲外（**業務の実作業から作ったノート**） |
| **業務での使いどころ** | **オフラインの RHEL 7.9 で openssh を更新するときに、上から順に打つ手順書。**RHEL 7.9 は ELS 契約がないと修正 RPM が出てこないので、着手前に契約状況を確認する |

> **このフォルダは「解説」と「手順書」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) | **なぜこの手順になるのか**。`createrepo` と目次、`clean all`、`--assumeno`、**署名検証の落とし穴**、エラータ、yum と dnf の違い |
> | **手順書** | **このノート（手順書 RHEL 7.9 openssh の更新）** | `yum` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 8 以降 openssh の更新](./手順書_RHEL8以降_openssh更新.md) | `dnf` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) | `yum` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) | `dnf` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [社内リポジトリ接続機で不足依存RPMを集めて持ち帰る](./RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md) | **TeraTerm と WinSCP を使った実作業の通し手順。**別システムへ RPM を送る → 足りない依存を下見する → 取得する → 持ち帰る → 対象サーバーであてる前の確認 |
> | 手順書 | [yum-utils が無い別システムで不足依存RPMを取得する](./手順書_RHEL7_yum-utilsが無い場合の依存RPM取得.md) | **`yumdownloader` / `repoquery` が無いとき**の代わり。`yum provides` → `yum --showduplicates list` → `yum install --downloadonly` で調べて取得する |
> | 解説 | [下見ログの読み方](./手順書_RHEL7_下見ログの読み方.md) | **`yum install --assumeno` のログの読み方。**行の形ごとの意味、`Error:` の塊の読み方、計画の表と `Transaction Summary` の読み方、よくある読み違い |
> | 手順書 | [対象サーバーでの適用前確認](./手順書_RHEL7_対象サーバーでの適用前確認.md) | 持ち帰った RPM を対象サーバーで確認する（ハッシュ照合 → 下見 → トランザクションテスト → 前後比較）。**実際にあてる手順は含まない** |
> | 解説 | [依存チェックスクリプトの読み方](./依存チェックスクリプトの読み方.md) | `check_deps.sh` を 1 ブロックずつ解説。**元版にあった不具合と、実機で確かめた修正内容** |
>
> **`dnf` / `yum` そのもののコマンド解説**は [07_パッケージ管理](../07_パッケージ管理/dnf解説①_基本とインストール系コマンド.md) にあります。
> **オフラインで rpm を集める側の作業**（`download --resolve` / `reposync` など）は
> [dnf実践③ オフライン環境でのパッケージの集め方](../07_パッケージ管理/dnf実践③_オフライン環境でのパッケージの集め方.md) です。

> **公式ドキュメントの確認日: 2026-10-13。**引用はその時点の記載です。
> **コマンドの挙動は検証環境（rpm 4.18.2 / dnf 4.14.0 / createrepo_c 0.17.3）での実測**です。
> **RHEL の実機で取った出力ではありません。**本番作業の前に、対象バージョンで裏を取ってください。

---

## 目次

- [この手順書の使い方](#この手順書の使い方)
  - [この手順書で使う値](#この手順書で使う値)
- [1 事前準備（作業日より前にやる）](#1-事前準備作業日より前にやる)
  - [1-1 createrepo が入っていない場合](#1-1-createrepo-が入っていない場合)
- [2 作業前確認](#2-作業前確認)
  - [2-1 OS バージョンを確認する](#2-1-os-バージョンを確認する)
  - [2-2 いまのバージョンを記録する（証跡）](#2-2-いまのバージョンを記録する証跡)
  - [2-3 sshd の状態と起動時刻を記録する](#2-3-sshd-の状態と起動時刻を記録する)
  - [2-4 設定ファイルをバックアップする](#2-4-設定ファイルをバックアップする)
- [3 RPM の配置と署名確認](#3-rpm-の配置と署名確認)
  - [3-1 RPM を置く](#3-1-rpm-を置く)
  - [3-2 公開鍵をインポートする](#3-2-公開鍵をインポートする)
  - [3-3 登録されている鍵を確認する](#3-3-登録されている鍵を確認する)
  - [3-4 壊れていないか・鍵が合っているかを確認する](#3-4-壊れていないか・鍵が合っているかを確認する)
  - [3-5 署名が「入っているか」を確認する（★ここを飛ばさない）](#3-5-署名が入っているかを確認する★ここを飛ばさない)
- [4 ローカルリポジトリの作成](#4-ローカルリポジトリの作成)
  - [4-1 目次を作る](#4-1-目次を作る)
  - [4-2 .repo ファイルを作る](#4-2-repo-ファイルを作る)
  - [4-3 キャッシュを消して認識を確認する](#4-3-キャッシュを消して認識を確認する)
- [5 事前確認（ドライラン）](#5-事前確認ドライラン)
- [6 適用](#6-適用)
- [7 適用後確認](#7-適用後確認)
  - [7-1 バージョンを確認する](#7-1-バージョンを確認する)
  - [7-2 設定ファイルの文法をチェックする](#7-2-設定ファイルの文法をチェックする)
  - [7-3 sshd の状態と起動時刻を確認する](#7-3-sshd-の状態と起動時刻を確認する)
  - [7-4 新規ログインを確認する（★いちばん大事）](#7-4-新規ログインを確認する★いちばん大事)
  - [7-5 変更されたファイルを確認する（任意）](#7-5-変更されたファイルを確認する任意)
- [8 後片付け](#8-後片付け)
- [9 切り戻し手順](#9-切り戻し手順)
  - [判断基準](#判断基準)
  - [9-1 旧バージョンの RPM をリポジトリに追加する](#9-1-旧バージョンの-rpm-をリポジトリに追加する)
  - [9-2 対象トランザクションを確認する](#9-2-対象トランザクションを確認する)
  - [9-3 取り消す（まず下見、その後に実行）](#9-3-取り消すまず下見その後に実行)
  - [9-4 戻ったことを確認する](#9-4-戻ったことを確認する)
  - [9-5 sshd が起動しないとき](#9-5-sshd-が起動しないとき)
- [10 連絡先・エスカレーション](#10-連絡先・エスカレーション)
- [11 証跡ファイル一覧](#11-証跡ファイル一覧)
- [12 openssh を更新するときの注意](#12-openssh-を更新するときの注意)
- [変更履歴](#変更履歴)

---

## この手順書の使い方

**オフラインの RHEL 7.9 サーバに、ローカルリポジトリ経由で openssh を更新する通し手順**です。
**上から順に打てば終わります。**各ステップに「期待値」を書いてあるので、合わなければそこで止まってください。

| 項目 | 内容 |
|:--|:--|
| **対象 OS** | **RHEL 7.9**（`yum` v3） |
| **対象パッケージ** | `openssh` / `openssh-server` / `openssh-clients`（＋必要な依存） |
| **所要時間の目安** | 30〜45 分／台 |
| **影響** | **sshd が再起動される場合あり**（既存セッションは通常維持される） |
| **切り戻し** | `yum history undo`（**旧バージョンの RPM を事前に用意しておく必要あり**） |
| **作業者** | （記入） |
| **確認者** | （記入） |

> **CVE 対応で複数の RPM をまとめて当てる場合**
> この手順書は openssh を例にしています。**集めた RPM をまとめて当てるなら、手順 5・6 のコマンドから
> `'openssh*'` を外して**リポジトリ全体を対象にしてください。
> **依存が足りないときは** [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) へ。

### この手順書で使う値

| 変数 | 値（例） | 意味 |
|:--|:--|:--|
| `REPO_DIR` | `/opt/localrepo` | ローカルリポジトリの置き場所 |
| `LOG_DIR` | `/var/tmp/patch_YYYYMMDD` | 証跡ログの保存先 |
| `REPO_ID` | `localrepo` | `.repo` ファイル内のリポジトリID |

---

## 1 事前準備（作業日より前にやる）

> **⚠️ RHEL 7.9 のサポート状況を先に確認してください**（Red Hat 公式。2026-10-13 時点）
>
> | 項目 | 公式の記載 |
> |:--|:--|
> | フェーズ移行 | **2024年6月30日**に Maintenance Phase から **Extended Life Phase** へ移行 |
> | ELS なしの場合 | **「No bug fixes, security fixes, hardware enablement, or root-cause analysis will be available during this phase.」** |
> | **ELS アドオンの期間** | **「from July 1, 2024 through May 31, 2029」** |
> | **ELS の対象** | **「ELS is only supported on the last minor release. In this case, RHEL 7.9.」** |
> | ELS が出す修正 | **「Software maintenance for certain Critical, Important, and Moderate CVEs with a CVSS score of 7 or higher」** |
>
> **つまり、CVE 対応の RPM をポータルから取得できるかは ELS 契約の有無で決まります。**
> **目的の RPM が見つからないときは、まず契約状況を確認してください。**

☐ Red Hat カスタマーポータルから**更新版の RPM を取得した**
　（`openssh` / `openssh-server` / `openssh-clients` を**同一バージョン**、**サーバと同じ `el7`** で）
☐ **切り戻し用に、いま入っているバージョンの RPM も取得した**
　→ これが無いと `history undo` できません。**ここを飛ばすと戻せなくなります**
☐ 対象サーバに `createrepo` が入っているか確認した（`rpm -q createrepo`）
☐ 検証環境で本手順を実施した
☐ **作業用とは別に SSH セッションをもう 1 本開ける状態**にしてある（コンソール接続手段もあると安心）

### 1-1 createrepo が入っていない場合

| やり方 | 内容 |
|:--|:--|
| **A. 対象サーバに入れる** | `createrepo` と依存 RPM（`deltarpm` / `python-deltarpm` / `libxml2-python` など）を取得して `yum install ./*.rpm` |
| **B. 別の端末で目次を作る**（推奨） | **同じメジャーバージョンの端末**で `createrepo` を実行し、**`repodata/` を含めたフォルダごと転送** |

**B のほうが確実です。**本番サーバに余計なパッケージを入れずに済みます。

> **依存 RPM の名前は RHEL 7 のマイナーバージョンで変わる可能性があります**（**検証環境では未確認**）。
> オンラインの RHEL 7 端末があれば `yum deplist createrepo` で確かめてください。

---

## 2 作業前確認

```bash
$ export LANG=C                                       # yum の出力を英語にする（RHEL 7 は日本語になる）
$ export REPO_DIR=/opt/localrepo                      # 以降の手順で使う変数を設定する
$ export LOG_DIR=/var/tmp/patch_$(date +%Y%m%d)       # 証跡の保存先
$ export REPO_ID=localrepo                            # リポジトリID
$ mkdir -p "$LOG_DIR"                                 # 保存先を作る
```

> **SSH を切って入り直したら、この 4 つの `export` をもう一度実行してください。**シェル変数は消えます。
> **`LANG=C` を入れているのは、RHEL 7 の `yum` が日本語環境だとエラーメッセージも日本語になるため**です。
> `grep` でエラーを探すときに英語のほうが扱いやすくなります。

### 2-1 OS バージョンを確認する

```bash
$ cat /etc/redhat-release             # ディストリとマイナーバージョン
$ rpm -E 'el%{rhel}'                  # el7 と表示される
```

**期待値**: **`Red Hat Enterprise Linux Server release 7.9 (Maipo)`** と、**`el7`**
**この `el7` が、持ち込む RPM のファイル名と一致している必要があります。**

### 2-2 いまのバージョンを記録する（証跡）

```bash
$ rpm -qa 'openssh*' | sort | tee "$LOG_DIR/01_before_rpm.txt"    # 作業前のパッケージ一覧
$ ssh -V 2>&1 | tee "$LOG_DIR/02_before_ssh_version.txt"          # ssh のバージョン（stderr に出る）
```

**期待値**: openssh / openssh-server / openssh-clients が**同じバージョン**で表示される
💡 `ssh -V` は**標準エラー出力**に出すので `2>&1` が必要です。

### 2-3 sshd の状態と起動時刻を記録する

```bash
$ systemctl status sshd --no-pager | tee "$LOG_DIR/03_before_sshd_status.txt"             # 状態
$ systemctl show sshd -p ActiveEnterTimestamp | tee -a "$LOG_DIR/03_before_sshd_status.txt" # 起動時刻
```

**期待値**: `Active: active (running)`
💡 **起動時刻を控えるのは、更新後に「再起動されたかどうか」を判断するため**です。

### 2-4 設定ファイルをバックアップする

```bash
$ cp -rp /etc/ssh /etc/ssh.bak_$(date +%Y%m%d)    # ディレクトリごとコピーする
$ ls -ld /etc/ssh.bak_*                           # できたか確認する
```

**期待値**: `/etc/ssh.bak_YYYYMMDD` ができている
💡 **RHEL 7 には `/etc/ssh/sshd_config.d/` はありません**が、
　ホスト鍵（`ssh_host_*_key`）も `/etc/ssh/` にあるので、**ディレクトリごと**コピーしておくほうが安全です。

**⚠️ チェックポイント1**: 現状が記録され、バックアップが取れている

---

## 3 RPM の配置と署名確認

### 3-1 RPM を置く

```bash
$ mkdir -p "$REPO_DIR"                # 置き場所を作る（RPM は scp / WinSCP でここへ転送）
$ ls -l "$REPO_DIR"/*.rpm             # 置かれたか確認する
```

**期待値**: 取得した RPM が一覧に出る。**ファイル名の **`el7`** が手順 2-1 の結果と一致している**

```bash
$ ls "$REPO_DIR"/*.rpm | grep -v "$(rpm -E 'el%{rhel}')"   # OS に合わない RPM を洗い出す
```

**期待値**: **何も表示されない**
💡 `noarch` のパッケージなどで表示されることもあります。**出てきたらファイル名を目で確認**してください。

### 3-2 公開鍵をインポートする

```bash
$ sudo rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release   # 従来の鍵
```

**期待値**: 何も表示されない（すでに登録済みでもエラーにはなりません）

> **RHEL 7 では post-quantum 署名の話は関係ありません。**
> Red Hat 公式によると、post-quantum 署名（RPMv6）に対応するのは **RHEL 9.7 以降と RHEL 10.1 以降**です。
> **RHEL 7 の RPM は従来の RSA 署名（RPMv4）だけ**なので、上の 1 本で足ります。
>
> ```bash
> $ ls /etc/pki/rpm-gpg/RPM-GPG-KEY-*redhat*     # 置かれている鍵ファイルを見る
> ```

### 3-3 登録されている鍵を確認する

```bash
$ rpm -q gpg-pubkey --qf '%{VERSION}\t%{SUMMARY}\n' | tee "$LOG_DIR/04_gpg_keys.txt"   # 登録済みの鍵
```

**期待値**: **持ち主がすべて `Red Hat, Inc.`**

参考（Red Hat 公式「Product Signing Keys」より。**RHEL 7 で見える鍵**）

| 鍵ID（8桁） | 鍵の名前 | 鍵ファイル |
|:--|:--|:--|
| **`fd431d51`** | **Red Hat, Inc. (release key 2)** ← ふだんの RPM はこれで署名されている | `RPM-GPG-KEY-redhat-release` |
| `2fa658e0` | Red Hat, Inc. (auxiliary key)（災害復旧用） | `RPM-GPG-KEY-redhat-release` |
| `37017186` | Red Hat, Inc. (release key)（2007年より前の旧製品用） | `RPM-GPG-KEY-redhat-legacy-release` |

**⚠️ Red Hat 以外の鍵（EPEL など）が出た場合**、次の 3-4 が OK でも「Red Hat 製」とは言い切れません。
手順 3-5 で 1 本ずつ Key ID を確認してください。

### 3-4 壊れていないか・鍵が合っているかを確認する

```bash
$ rpm -K "$REPO_DIR"/*.rpm > "$LOG_DIR/04_rpm_signature.txt" 2>&1   # 結果をファイルに保存する
$ grep -Ei 'NOT OK|MISSING KEYS' "$LOG_DIR/04_rpm_signature.txt"    # NG の行だけを探す
```

**期待値**: **何も表示されない**
❌ 何か表示された → **作業中止**。表示された RPM を取り直す

💡 **`NOT OK` も行の最後が「OK」で終わります。**だから「OK を数える」のではなく「**NG の行だけを探す**」書き方にしています。

### 3-5 署名が「入っているか」を確認する（★ここを飛ばさない）

```bash
$ for f in "$REPO_DIR"/*.rpm; do \
    printf '%-44s %s\n' "$(basename "$f")" \
      "$(rpm -qpi "$f" 2>/dev/null | sed -n 's/^Signature *: *//p')"; \
  done | tee "$LOG_DIR/04_rpm_signature_detail.txt"              # 1本ずつ署名を表示する
```

**期待値**: 全行に `RSA/SHA512, ..., Key ID xxxxxxxxxxxxxxxx` のような**署名情報が出ている**

```text
openssh-7.4p1-23.el7_9.x86_64.rpm            RSA/SHA256, Mon Sep 15 10:22:03 2026, Key ID 199e2f91fd431d51
openssh-clients-7.4p1-23.el7_9.x86_64.rpm    RSA/SHA256, Mon Sep 15 10:22:03 2026, Key ID 199e2f91fd431d51
openssh-server-7.4p1-23.el7_9.x86_64.rpm     RSA/SHA256, Mon Sep 15 10:22:03 2026, Key ID 199e2f91fd431d51
```

❌ **`(none)` と出た RPM があったら作業中止。**その RPM は**署名が入っていません。**
　Red Hat が出したものだと確認できないので、**カスタマーポータルから取り直してください。**

> **なぜ 3-4 だけでは足りないのか。**
> **署名が入っていない RPM に `rpm -K` を打つと `digests OK`（終了ステータス 0）が返ります。**
> 検証環境で実測しました。
>
> ```text
> /opt/localrepo/appx-1.0-1.noarch.rpm:    digests signatures OK     ← 署名あり
> /opt/localrepo/libbaz-1.1-1.noarch.rpm:  digests OK                ← 署名なし
> ```
>
> **`NOT OK` が出ないので、3-4 の確認では何も検出できません。**
> **「確認しなかった」が「問題なし」として出てくる**ので、3-5 を必ずやってください。
>
> **⚠️ 上の出力は rpm 4.18 での実測です。RHEL 7 の rpm は 4.11 なので、文字列が違います**
> （`rsa sha1 (md5) pgp md5 OK` のような形。**検証環境では未確認**）。
> **だからこそ、文字列に頼らず 3-5 の `Signature` 行で判断するほうが確実**です。

💡 Key ID の下 8 桁（この例なら `fd431d51`）が、手順 3-3 の一覧と対応します。

**⚠️ チェックポイント2**: すべての RPM が「壊れていない」かつ「署名が入っている」

---

## 4 ローカルリポジトリの作成

### 4-1 目次を作る

```bash
$ sudo createrepo "$REPO_DIR"       # 初回：目次をゼロから作る
$ ls "$REPO_DIR/repodata/"            # できたか確認する
```

**期待値**: `repomd.xml` などのファイルができている
💡 **2 回目以降（RPM を追加したとき）は `sudo createrepo --update "$REPO_DIR"`** を使います（差分だけで速い）。

### 4-2 .repo ファイルを作る

```bash
$ sudo tee /etc/yum.repos.d/${REPO_ID}.repo > /dev/null <<EOF   # .repo を作る
[${REPO_ID}]
name=Local Repo
baseurl=file://${REPO_DIR}
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
EOF
$ cat /etc/yum.repos.d/${REPO_ID}.repo    # 中身を確認する
```

**期待値**: **`baseurl=file:///opt/localrepo`**（**スラッシュ 3 つ**）になっている
💡 `file://` のあとに絶対パス `/opt/localrepo` が続くので 3 つになります。**2 つは間違いです。**

### 4-3 キャッシュを消して認識を確認する

```bash
$ sudo yum clean all                                                        # 古い目次を捨てる
$ yum --disablerepo='*' --enablerepo="$REPO_ID" repolist | tee "$LOG_DIR/05_repolist.txt"   # 認識されたか見る
```

**期待値**: `localrepo` の行が出て、**`status` 欄に置いた RPM の件数**が表示される

```text
repo id                        repo name                        status
localrepo                      Local Repo                            3

repolist: 3
```

💡 **`yum repolist` は `status` 列に件数を出します**（`dnf` の `Repo-pkgs` に相当）。
💡 `This system is not registered with an entitlement server` と出ても**無視してよい**です。

**⚠️ チェックポイント3**: ローカルリポジトリが認識され、件数が合っている

---

## 5 事前確認（ドライラン）

```bash
$ sudo yum --disablerepo='*' --enablerepo="$REPO_ID" update --assumeno 'openssh*' 2>&1 \
    | tee "$LOG_DIR/06_dryrun.txt"      # 何が起きるかだけ見る（システムは変更しない）
```

**期待値**

- **`Updating:` 欄に openssh / openssh-server / openssh-clients が目的のバージョンで表示される**
- **想定外のパッケージが含まれていない**
- **最後に `Exiting on user command` と表示される**（これが正常です）

```text
 Package              Arch      Version              Repository     Size
=========================================================================
Updating:
 openssh              x86_64    7.4p1-23.el7_9       localrepo     510 k
 openssh-clients      x86_64    7.4p1-23.el7_9       localrepo     655 k
 openssh-server       x86_64    7.4p1-23.el7_9       localrepo     459 k

Transaction Summary
=========================================================================
Upgrade  3 Packages

Exiting on user command
```

💡 **`dnf` では `Upgrading:` / `Operation aborted.` ですが、`yum` では `Updating:` / `Exiting on user command` です。**

💡 **上の画面は、こうなるはずという例**です（RHEL 実機では未実測）。

❌ **失敗したとき**

| 表示 | 意味 | 対処 |
|:--|:--|:--|
| `Error: Package: ...` ＋ `Requires: xxx` | 依存 RPM が足りない | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) へ |
| `No packages marked for update` | 更新対象が無い | `rpm -qa 'openssh*'` で現行版を確認。**RPM の取り違え・`el7` 以外の取り違え**を疑う |
| `Protected multilib versions` | **32bit版（i686）と 64bit版のバージョンがずれている** | **i686 版も同じバージョンで取得する** |
| `Cannot retrieve repository metadata (repomd.xml)` | 目次が無い／パス間違い | 手順 4-1 をやり直す。`baseurl` のスラッシュ 3 つを確認 |

💡 **RHEL 7 の `yum` に `best` という設定はありません。**
　（`best` は RHEL 8 以降の `dnf` の設定です。RHEL 8 以降の手順書を参照してください）

**⚠️ チェックポイント4**: 更新内容が想定どおりで、依存エラーがない
（確認者のチェック: ☐）

---

## 6 適用

> **実施前に、別の SSH セッションが開いていることを再確認してください。**

```bash
$ sudo yum --disablerepo='*' --enablerepo="$REPO_ID" update 'openssh*'    # 実際に適用する
```

- **表示内容が手順 5 とまったく同じ**であることを確認してから `y` を入力します
- **期待値**: 最後に `Complete!`

```bash
$ yum history info last | tee "$LOG_DIR/07_yum_history.txt"   # 適用結果を証跡として保存する
```

💡 **`Transaction ID` を控えておいてください。**切り戻しで使います。

> **RHEL 7 の `yum` に `--comment` オプションはありません**（RHEL 8 以降の `dnf` の機能です）。
> 変更管理の番号は、**証跡ログに残してください。**
>
> ```bash
> $ echo "CHG-123 / RHSA-2026:0001 対応 / $(date)" | tee "$LOG_DIR/00_work_info.txt"
> ```

---

## 7 適用後確認

### 7-1 バージョンを確認する

```bash
$ rpm -qa 'openssh*' | sort | tee "$LOG_DIR/08_after_rpm.txt"   # 作業後のパッケージ一覧
$ ssh -V 2>&1 | tee "$LOG_DIR/09_after_ssh_version.txt"         # ssh のバージョン
```

**期待値**: 3 パッケージとも**新バージョンにそろっている**

### 7-2 設定ファイルの文法をチェックする

```bash
$ sudo sshd -t && echo "sshd config OK"    # 文法エラーが無ければ何も出ない
```

**期待値**: `sshd config OK`
❌ エラーが出たら、**sshd を再起動する前に**設定を直してください（再起動すると入れなくなる可能性があります）。

### 7-3 sshd の状態と起動時刻を確認する

```bash
$ systemctl status sshd --no-pager | tee "$LOG_DIR/10_after_sshd_status.txt"               # 状態
$ systemctl show sshd -p ActiveEnterTimestamp | tee -a "$LOG_DIR/10_after_sshd_status.txt" # 起動時刻
```

**期待値**: `active (running)`

| 起動時刻が | 意味 | 次にやること |
|:--|:--|:--|
| **手順 2-3 より新しい** | 更新時に自動で再起動された | そのまま 7-4 へ |
| **変わっていない** | 古い sshd が動き続けている | **手動で再起動する**（下記） |

```bash
$ sudo systemctl restart sshd            # 新しい sshd を反映させる
$ systemctl status sshd --no-pager       # 起動したか確認する
```

### 7-4 新規ログインを確認する（★いちばん大事）

```bash
$ ssh <ユーザー名>@<対象サーバー>        # 別の端末から新しくログインしてみる
```

**期待値**: 問題なくログインできる
☐ **新規ログイン成功を確認してから、予備セッションを閉じる**

💡 **ここを飛ばして予備セッションを閉じると、入れなくなったときに復旧手段がなくなります。**

### 7-5 変更されたファイルを確認する（任意）

```bash
$ rpm -V openssh openssh-server openssh-clients    # パッケージと実ファイルの差分を見る
```

**期待値**: 何も表示されない
💡 設定ファイルを変更している場合は `c` 付きで表示されることがあり、**それは想定内**です。

**⚠️ チェックポイント5**: 新バージョンで sshd が正常稼働し、新規ログインできる

---

## 8 後片付け

```bash
$ sudo sed -i 's/^enabled=1/enabled=0/' /etc/yum.repos.d/${REPO_ID}.repo   # 次回まで無効にする
$ sudo yum clean all                                                       # キャッシュを消す
$ ls -l "$LOG_DIR"                                                         # 証跡の一覧を確認する
```

💡 **無効にしておく理由**: 有効のままだと、次に誰かが `yum upgrade` を打ったときに
　**このローカルリポジトリの古い RPM が候補に入ってしまう**ことがあります。

☐ 証跡ファイルを所定の場所へ保管した
☐ RPM の保管・削除は現場ルールに従った

---

## 9 切り戻し手順

### 判断基準

- **新規ログインできない**
- **sshd が起動しない／`sshd -t` でエラー**
- 業務で使う接続（踏み台・監視・ジョブ連携など）に影響が出た

### 9-1 旧バージョンの RPM をリポジトリに追加する

```bash
$ sudo cp <旧バージョンRPM> "$REPO_DIR"/          # 手順1で用意したもの
$ sudo createrepo --update "$REPO_DIR"          # 目次を更新する
$ sudo yum clean all                              # キャッシュを消す
```

💡 **旧バージョンの RPM が無いと戻せません。**手順 1 で用意していなければ、ここで取得が必要になります。

### 9-2 対象トランザクションを確認する

```bash
$ yum history list        # 履歴の一覧
```

**期待値**: 手順 6 で控えた Transaction ID が一覧にある

### 9-3 取り消す（まず下見、その後に実行）

```bash
$ sudo yum --disablerepo='*' --enablerepo="$REPO_ID" history undo <Transaction ID> --assumeno   # まず下見する
$ sudo yum --disablerepo='*' --enablerepo="$REPO_ID" history undo <Transaction ID>              # 問題なければ実行する
```

**期待値**: openssh 3 パッケージが旧バージョンに戻り、`Complete!`

### 9-4 戻ったことを確認する

```bash
$ rpm -qa 'openssh*' | sort              # バージョンを確認する
$ sudo sshd -t && echo "sshd config OK"  # 文法をチェックする
$ sudo systemctl restart sshd            # 再起動する
$ systemctl status sshd --no-pager       # 状態を確認する
```

**期待値**: 手順 2-2 と同じバージョン、`active (running)`、新規ログイン成功

### 9-5 sshd が起動しないとき

```bash
$ sudo cp -rp /etc/ssh.bak_YYYYMMDD/. /etc/ssh/     # バックアップから設定を戻す
$ sudo sshd -t && sudo systemctl restart sshd       # 文法を確認して再起動する
```

💡 **`/etc/ssh.bak_YYYYMMDD/.` の末尾のドット**は「中身を全部」という意味です。
　これが無いと `/etc/ssh/ssh.bak_YYYYMMDD/` という入れ子ができてしまいます。

---

## 10 連絡先・エスカレーション

| 役割 | 連絡先 | 対応時間 |
|:--|:--|:--|
| 作業責任者 | （記入） | （記入） |
| 確認者 | （記入） | （記入） |
| 顧客窓口 | （記入） | （記入） |

---

## 11 証跡ファイル一覧

| No | ファイル | 内容 |
|:--|:--|:--|
| 01 | `01_before_rpm.txt` | 作業前のパッケージ |
| 02 | `02_before_ssh_version.txt` | 作業前の `ssh -V` |
| 03 | `03_before_sshd_status.txt` | 作業前の sshd 状態と起動時刻 |
| 04 | `04_gpg_keys.txt` | 登録済みの鍵一覧 |
| 04 | `04_rpm_signature.txt` | RPM の壊れ・鍵チェック |
| 04 | `04_rpm_signature_detail.txt` | **1本ずつの署名の有無** |
| 05 | `05_repolist.txt` | リポジトリ認識確認 |
| 06 | `06_dryrun.txt` | ドライラン結果 |
| 07 | `07_yum_history.txt` | 適用トランザクション |
| 08 | `08_after_rpm.txt` | 作業後のパッケージ |
| 09 | `09_after_ssh_version.txt` | 作業後の `ssh -V` |
| 10 | `10_after_sshd_status.txt` | 作業後の sshd 状態と起動時刻 |

---

## 12 openssh を更新するときの注意

- **`openssh` / `openssh-server` / `openssh-clients` は同じバージョンでそろえて更新します**
- **openssh-server を更新すると、パッケージのスクリプトにより sshd が自動で再起動される場合があります。**
  既存の SSH セッションは通常そのまま残りますが、念のため
  - **作業用とは別にもう 1 本セッションを開いておく**
  - 更新後、**新規ログインできることを確認してから**既存セッションを閉じる
- **`sshd -t` で設定ファイルの文法チェックができます**（何も表示されなければ OK）
- **RHEL 7 には `/etc/ssh/sshd_config.d/` はありません**が、ホスト鍵も `/etc/ssh/` にあるので
  **バックアップはディレクトリごと**取っておくほうが安全です

---

## 変更履歴

| 日付 | 版 | 内容 |
|:--|:--|:--|
| 2026-10-13 | 1.0 | 業務の手順書をリポジトリの書式に合わせて再構成。**署名が入っているかの確認（手順 3-5）を追加**、`LANG=C` の理由、RHEL 7 で見える鍵ID一覧、`yum` と `dnf` で画面の文字が違う点、RHEL 7.9 の ELS を追記 |

---

[← 全体の目次にもどる](../README.md)
