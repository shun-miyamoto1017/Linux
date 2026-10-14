# RHEL 7.9：CVE対応RPM99個の保管・依存RPM取得・オフライン検証

| | |
|:--|:--|
| **学習の順番** | 実務 ★★★★★ |
| **Ping-t の範囲** | 範囲外（**業務の実作業から作ったノート**） |
| **業務での使いどころ** | **CVE対応で渡された大量のRPMを、オフラインの本番サーバーへ当てる前の「準備フェーズ」の通し手順。**保管元A・取得用システムB・対象サーバーCの3系統に分けて、原本の保管、追加依存RPMの取得、オフライン検証（ドライラン）までを扱う。**とくに「`localinstall` は読めないRPMや同版導入済みのRPMを警告だけで計画から外す」は、知らないとCVE対応の取りこぼしに気づけない** |

> **このフォルダは「解説」と「手順書」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) | **なぜこの手順になるのか**。`createrepo` と目次、`clean all`、`--assumeno`、**署名検証の落とし穴**、エラータ、yum と dnf の違い |
> | 手順書 | [手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) | `yum` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 8 以降 openssh の更新](./手順書_RHEL8以降_openssh更新.md) | `dnf` でローカルリポジトリから openssh を更新する通し手順（事前確認 → 適用 → 切り戻し） |
> | 手順書 | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) | `yum` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | 手順書 | [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) | `dnf` で「確認 → 不足RPMを追加」を繰り返して依存を閉じる。手動とスクリプトの両方 |
> | **手順書** | **このノート（RHEL 7.9 CVE対応RPM99個の保管・依存RPM取得・オフライン検証）** | 取得済み99個を原本として保管し、別システムで追加の依存RPMを取得して、対象サーバーでオフライン検証（ドライラン）まで持っていく通し手順。**`localinstall` が警告だけでRPMを計画から外すこと**の検出手順も含む |
> | 解説 | [依存チェックスクリプトの読み方](./依存チェックスクリプトの読み方.md) | `check_deps.sh` を 1 ブロックずつ解説。**元版にあった不具合と、実機で確かめた修正内容** |
>
> **`dnf` / `yum` そのもののコマンド解説**は [07_パッケージ管理](../07_パッケージ管理/dnf解説①_基本とインストール系コマンド.md) にあります。
> **RHEL 8 以降（`dnf`）で同じことをする場合**は [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) も併せて読んでください。

> **公式ドキュメントの確認日: 2026-10-14。**引用はその時点の記載です。

**結論：取得済み99個を原本として保管し、社内リポジトリへ接続できる別システムで追加RPMを取得します。最終的な依存関係の判定は、対象サーバー自身のインストール状態を使って行います。**

この手順の到達点は「オフライン更新に必要なRPMと検証記録がそろい、更新作業の審査に出せる状態」です。実際の更新・再起動は含みません。

> 本書の99個はユーザーから提示された件数です。RPM実物、CVE番号、RHSA番号、対象サーバーの情報は未提供のため、99個の内容やCVE修正状況は未検証です。以下の出力例はすべて説明用です。

## 目次

- [1. 作業場所と全体の流れ](#1-作業場所と全体の流れ)
- [2. 最初に理解する仕組み](#2-最初に理解する仕組み)
- [3. 作業前の確認](#3-作業前の確認)
- [4. 対象サーバーの状態を記録する](#4-対象サーバーの状態を記録する)
- [5. 取得済み99個をアーカイブする](#5-取得済み99個をアーカイブする)
- [6. 別システムへ搬送して展開する](#6-別システムへ搬送して展開する)
- [7. 社内リポジトリで不足候補を調べる](#7-社内リポジトリで不足候補を調べる)
- [8. 追加の依存RPMを取得する](#8-追加の依存rpmを取得する)
- [9. 搬送用セットを作る](#9-搬送用セットを作る)
- [10. 対象サーバーでオフライン検証する](#10-対象サーバーでオフライン検証する)
- [11. エラーの読み方と対処](#11-エラーの読み方と対処)
- [12. 完了判定と実更新への引き継ぎ](#12-完了判定と実更新への引き継ぎ)
- [13. コマンドと記号の早見表](#13-コマンドと記号の早見表)
- [14. 確認問題](#14-確認問題)
- [15. 公式参照](#15-公式参照)

## 1. 作業場所と全体の流れ

| 呼び名 | 役割 | RPMのインストール |
|---|---|---|
| A：保管元 | 取得済み99個を保存しているLinux環境 | 行わない |
| B：取得用システム | 承認された社内RHELリポジトリへ接続できるRHEL 7.9環境 | 本手順では行わない |
| C：対象サーバー | 更新予定のRHEL 7.9。外部リポジトリに接続せず検証 | テストのみ |

AとCが同じサーバーでも構いません。AがWindowsの場合は、99個を承認済みのLinux作業領域へコピーしてから第5章を実施します。PowerShellに本書のBashコマンドを貼り付けないでください。

```text
C：現状・制約を記録 ──────────────────────────┐
                                                       ↓
A：99個を数える → 原本アーカイブ → B：社内リポジトリで調査
                                      ↓
                                 追加RPMを取得
                                      ↓
                              搬送用セットを作成
                                      ↓
C：整合性・署名 → 更新計画の確認 → トランザクションテスト
                                      ↓
             不足あり ── Bで取得し直す → Cで再検証
                                      ↓
             不足なし・計画一致 → 更新作業の審査へ
```

**BとCの導入済みパッケージは別物です。** Bで問題がなくても、Cには必要なライブラリがない場合があります。Cでの結果を最終判断に使います。

## 2. 最初に理解する仕組み

### RPM・依存関係・リポジトリ

RPMはプログラム、設定ファイル、依存条件などが入った配布ファイルです。依存関係とは「このプログラムを使うには、別の機能が必要」という条件です。

```text
更新するアプリRPM
  ├─ libexample.so.1()(64bit) が必要
  │     └─ example-libs RPMがその機能を提供
  └─ example-common = 1.2-3.el7 が必要
        └─ 同じバージョンのexample-common RPMが必要
```

この名前と版は架空です。`libexample.so.1()(64bit)`はRPMファイル名ではなく、RPMが提供する「機能名」です。依存エラーの文字列を、そのままRPMファイル名と考えないでください。

| 道具 | 主な仕事 | 本手順での使い方 |
|---|---|---|
| `rpm` | RPMファイルや導入済みパッケージを直接調べる | 一覧・依存条件・署名を確認 |
| `yum` | 複数パッケージを一つの更新計画として解決する | 計画表示とテスト |
| `repoquery` | リポジトリ内のパッケージ情報を調べる | 依存条件の提供元を検索 |
| `yumdownloader` | リポジトリからRPMを保存する | 追加RPMをダウンロード |

根拠：[Yum公式マニュアル](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.8)、[repoquery公式マニュアル](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/repoquery.1)。

### 99個という件数だけで判断しない

- 99個すべてが対象サーバーに必要とは限りません。
- 追加の依存RPMにより、最終的な件数は99個を超える場合があります。
- 同じパッケージの異なる版や、不要なアーキテクチャが混ざっている可能性があります。
- 依存解決に成功しても、目的のCVEが直るとは限りません。

識別には **NEVRA：Name・Epoch・Version・Release・Architecture** を使います。Epochは版比較で最優先される数値です。Epochが違えばVersion・Releaseの大小に関係なく、Epochの大きい方が新しいと判断されます。未設定は通常0相当ですが、ファイル名には含まれないことがあります。版の大小を文字列の並び順で判断しないでください。

### CVE修正とRHEL 7.9のサポート

Red Hatは修正を既存の版へ取り込む「バックポート」を行います。上流ソフトウェアのバージョン番号だけで脆弱・修正済みを判定せず、対象製品のRHSAとRPMのEpoch・Version・Releaseを照合します。[Red Hat：Security Backporting Practice](https://access.redhat.com/security/updates/backporting)

2026年10月14日時点のRed Hat公式FAQでは、RHEL 7の通常のメンテナンス終了後の修正提供は契約・対象範囲に依存し、RHEL 7 ELSは7.9を対象として2029年5月31日まで提供されると案内されています。すべてのCVE・すべてのパッケージが対象ではありません。社内ミラーに必要な修正版が同期されているかも確認します。[Red Hat：RHEL 7 End of Maintenance FAQ](https://access.redhat.com/articles/7005471)（閲覧にRed Hatのサブスクリプションでのログインが必要な場合があります）

## 3. 作業前の確認

### 管理者と合意しておく項目

| 項目 | 記録する内容 |
|---|---|
| 対象 | サーバー名、RHEL 7.9、製品種別、CPUアーキテクチャ |
| 修正範囲 | CVE番号、RHSA番号、対象パッケージ、承認済み修正版 |
| 取得元 | 社内リポジトリID、Content Viewやスナップショット、同期日、ELS対象 |
| 構成 | x86_64のみか、i686も導入されているか、カーネルを含むか |
| 制約 | `exclude`、versionlock、独自プラグイン、アプリの動作保証 |
| 作業許可 | ファイル搬送、作業領域作成、キャッシュ・ログ・`/tmp`への書き込み、テストの実施許可 |
| 復旧 | 実更新前のバックアップ、復元方法、停止時間、コンソール接続手段 |

**本書を読んだことは本番操作の承認にはなりません。** 対象サーバーへの書き込みやテストは社内の作業承認後に実施してください。テストでもログ・キャッシュ・ロック用ファイルが作られることがあります。さらに`--assumeno`で中止した場合は、`/tmp`にトランザクション保存ファイル（`yum_save_tx.*.yumtx`）も作られます。

### 共通の実行条件

- LinuxのBashで、一つのコードブロックずつ実行します。表示結果を確認してから進めます。
- 同じ章の変数は同じターミナルで引き継ぎます。再ログイン時はパスを再設定します。
- `sudo`付きの行には権限が必要です。それ以外は一般ユーザーの作業領域を使います。
- `mktemp -d`で毎回新しい作業場所を作り、既存ファイルへの上書きを避けます。
- `export LC_ALL=C`はメッセージを英語にそろえ、調査・比較をしやすくします。
- コマンドが失敗したら、そのブロックの続きも実施せず原因を確認します。
- 99個のRPMは通常のファイル名で、同一ディレクトリ直下にあることを前提とします。サブディレクトリや特殊な改行付きファイル名がある場合は先に整理方法を相談します。

### ツールの有無を調べる

実行場所：A・B・C。状態の照会だけです。

```bash
cat /etc/redhat-release
uname -m
rpm --version
rpm -q yum yum-utils
command -v tar sha256sum
```

Bでは追加で確認します。

```bash
command -v yumdownloader repoquery
yumdownloader --help
repoquery --help
```

`command -v`がパスを表示しないツールは利用できません。Bに`yum-utils`がなければ、管理者へ導入を依頼します。本書ではツール導入によるシステム変更は行いません。Cには`yumdownloader`や`repoquery`は不要です。

RHEL 8以降のDNF、Ubuntu/DebianのAPT、BusyBoxのツールにそのまま置き換えないでください。BもRHEL 7.9の同じアーキテクチャを基本とします。`--releasever=7.9`を指定しただけでは別OSをRHEL 7.9相当にはできません。社内リポジトリで使うreleaseverの値は管理者に確認します。

## 4. 対象サーバーの状態を記録する

実行場所：C。パッケージは変更せず、作業領域に記録を保存します。

```bash
export LC_ALL=C
EVIDENCE=$(mktemp -d /var/tmp/rhel7-cve-evidence.XXXXXX)
printf '%s\n' "$EVIDENCE"
cat /etc/redhat-release > "$EVIDENCE/os.txt"
uname -m > "$EVIDENCE/architecture.txt"
uname -r > "$EVIDENCE/running-kernel.txt"
rpm -q rpm yum yum-utils > "$EVIDENCE/tools.txt" 2>&1
cat "$EVIDENCE/tools.txt"
rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE}\n' \
  > "$EVIDENCE/gpg-pubkey.txt" 2>&1
cat "$EVIDENCE/gpg-pubkey.txt"
rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' \
  | sort > "$EVIDENCE/installed-before.tsv"
df -h / /var /boot > "$EVIDENCE/disk-space.txt"
df -i / /var /boot > "$EVIDENCE/inodes.txt"
```

`rpm -q`の結果はファイルへリダイレクトしているので、直後の`cat`で内容を確認します。`yum-utils`未導入なら`tools.txt`に`package yum-utils is not installed`が記録されます（`rpm -q`の終了コードも0以外になりますが、リダイレクトしているため画面では見えません）。これはCでは必ずしも問題ではありません。`rpm`と`yum`は必要です。

`gpg-pubkey.txt`には、このサーバーのRPMデータベースに登録済みの公開鍵が並びます。承認済みの鍵がここにないと、第10章の署名確認が`NOKEY`で止まります。鍵が見当たらない場合は、本書で勝手にインポートせず管理者へ確認します。

管理者が、`/etc/yum.conf`、`/etc/yum.repos.d/`、`/etc/yum/pluginconf.d/`を読み、`exclude`、versionlock、署名設定、独自処理を記録します。認証情報を含む設定ファイルをそのまま搬送しないでください。

作業開始時点の既存の依存不整合も確認します。

```bash
sudo yum --noplugins --disablerepo='*' check \
  > "$EVIDENCE/yum-check-before.log" 2>&1
CHECK_RC=$?
cat "$EVIDENCE/yum-check-before.log"
printf 'yum check exit code: %s\n' "$CHECK_RC"
```

0以外なら内容を管理者へ確認します。元から存在する不整合を、今回の99個が原因だと決めつけないでください。

`--noplugins`はversionlockなど**プラグイン由来**の制約を無効にします。一方で`/etc/yum.conf`の`exclude`はプラグインではないため、`--noplugins`を付けても有効なままです。つまり本書のオフラインテストは「プラグインによる制約を外した状態」での依存解決を見ています。実運用のロック・除外条件との一致は別途確認し、一致しなければ完了扱いにしません。

状態記録はバックアップではありません。`installed-before.tsv`からシステムを復元することはできません。

## 5. 取得済み99個をアーカイブする

### 5.1 元の場所を指定し、99個であることを確認する

実行場所：A。元のRPMは変更しません。

```bash
export LC_ALL=C
read -r -p '取得済みRPMを置いたディレクトリの絶対パス: ' RPM_SOURCE
find "$RPM_SOURCE" -maxdepth 1 -type f -name '*.rpm' -printf '%f\n' | sort
find "$RPM_SOURCE" -maxdepth 1 -type f -name '*.rpm' -printf '%f\n' | wc -l
```

最後が`99`であることを確認します。違う場合は中断します。RPMの数とCVEの数は対応しません。

### 5.2 原本用の作業コピーと一覧を作る

```bash
WORK=$(mktemp -d /var/tmp/rhel7-cve-source.XXXXXX)
mkdir -p "$WORK/rhel7-cve-initial/rpms" "$WORK/rhel7-cve-initial/records"
printf '保管作業場所: %s\n' "$WORK"
(
  set -e
  shopt -s nullglob
  ORIGINALS=("$RPM_SOURCE"/*.rpm)
  test "${#ORIGINALS[@]}" -eq 99 \
    || { printf 'NG: 99個ではなく%s個です\n' "${#ORIGINALS[@]}" >&2; exit 1; }
  cp -p -- "${ORIGINALS[@]}" "$WORK/rhel7-cve-initial/rpms/"
  cd "$WORK/rhel7-cve-initial"
  rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' \
    rpms/*.rpm > records/rpm-inventory.tsv
  sha256sum rpms/*.rpm > SHA256SUMS
  printf 'OK: %s個の原本をコピーし、一覧とハッシュを作成しました\n' "${#ORIGINALS[@]}"
)
```

`rpm -qp`は未導入のRPMファイルを読む指定です。インストールしません。一覧の列は名前・Epoch・Version・Release・Architectureです。`(none)`はEpoch未設定を表します。

`test`は成功しても失敗しても何も表示しないため、件数が違ったときに気づけるよう`|| { printf ... ; exit 1; }`を付けています。サブシェルが`NG:`を出して止まったら、RPMの置き場所と件数を確認してからやり直します。

同じ名前・アーキテクチャの複数バージョンがある場合は、更新対象としてどれを使うか確認します。原本99個は残し、除外が必要なら後の搬送用セットで理由を記録します。カーネルの複数版は別途判断が必要です。

### 5.3 署名・アーカイブ・ハッシュ値を確認する

```bash
rpm -Kv "$WORK"/rhel7-cve-initial/rpms/*.rpm \
  > "$WORK/rhel7-cve-initial/records/signatures.txt" 2>&1
SIGNATURE_RC=$?
cat "$WORK/rhel7-cve-initial/records/signatures.txt"
printf 'signature check exit code: %s\n' "$SIGNATURE_RC"
```

`rpm -Kv`は署名とダイジェストを1行ずつ表示し、各行の末尾に結果の語が付きます。

| 行末の語 | 意味 |
|---|---|
| `OK` | その署名またはダイジェストの検証に成功 |
| `BAD` | 検証に失敗。内容が改変された可能性 |
| `NOKEY` | 対応する公開鍵がRPMデータベースにない |
| `NOTRUSTED` | 鍵はあるが信頼されていない |
| `UNKNOWN` | 署名の種類を判別できない |

`NOT OK`は`-v`を付けない`rpm -K`の要約行の表記です。本書は`-Kv`を使うので、失敗時に現れる語は`BAD`・`NOKEY`・`NOTRUSTED`です。終了コードはこのいずれでも0以外になります。

**最も注意が必要なのは「署名そのものが入っていないRPM」です。** 署名ヘッダーがなければ検証する対象が存在せず、ダイジェストの`OK`だけが並び、終了コードも0になります。`rpm -Kv`が0で終わったことを「署名済み」の根拠にしないでください。署名の有無は次のように機械的に確認します。

```bash
for RPM_FILE in "$WORK"/rhel7-cve-initial/rpms/*.rpm; do
  RPM_SIG=$(rpm -qpi "$RPM_FILE" 2>/dev/null | sed -n 's/^Signature *: *//p')
  printf '%s\t%s\n' "${RPM_FILE##*/}" "${RPM_SIG:-(取得失敗)}"
done > "$WORK/rhel7-cve-initial/records/signature-detail.tsv"
awk -F'\t' '$2 == "(none)" || $2 == "(取得失敗)" { print $1 }' \
  "$WORK/rhel7-cve-initial/records/signature-detail.tsv"
```

`rpm -qpi`の`Signature`欄が`(none)`なら署名なしです。最後の`awk`が1行でも出力したら、署名なしか読み取り失敗なので先へ進めず、取得元を確認します。何も出力されなければ全RPMに署名ヘッダーがあります。

署名者と鍵が社内承認済みであることも確認します。Aに鍵がない場合は「未検証」と記録し、BおよびCで検証を完了させます。鍵のインポートを本書では行いません。

```bash
(
  set -e
  cd "$WORK"
  tar -czf rpm99-original.tar.gz rhel7-cve-initial
  sha256sum rpm99-original.tar.gz > rpm99-original.tar.gz.sha256
  tar -tzf rpm99-original.tar.gz > archive-members.txt
  sha256sum -c rpm99-original.tar.gz.sha256
)
```

正常例：`rpm99-original.tar.gz: OK`。`tar -czf`はファイルをまとめてgzip圧縮する操作です。元のRPMは削除されません。RPM自体が圧縮されているため、大幅に小さくなるとは限りません。

Bへ渡すものは、`rpm99-original.tar.gz`、`rpm99-original.tar.gz.sha256`、Cの承認済み状態記録、CVE/RHSA対応表です。ハッシュ値は承認された経路でも照合してください。アーカイブとハッシュの両方が改変されれば単純な照合だけでは検知できず、署名確認の代わりにはなりません。

根拠：[GNU tar](https://www.gnu.org/software/tar/manual/tar.html)、[GNU SHA-2 utilities](https://www.gnu.org/s/coreutils/manual/html_node/sha2-utilities.html)、[RPM 4.11公式マニュアル](https://raw.githubusercontent.com/rpm-software-management/rpm/rpm-4.11.x/doc/rpm.8)。

## 6. 別システムへ搬送して展開する

実行場所：B。社内承認済みのファイル転送・媒体を使います。転送先のホスト名や認証方式が未確認なので、特定の転送コマンドは固定しません。

```bash
export LC_ALL=C
read -r -p '受領したアーカイブとsha256ファイルの保存ディレクトリ: ' INBOX
(
  set -e
  cd "$INBOX"
  sha256sum -c rpm99-original.tar.gz.sha256
  tar -tzf rpm99-original.tar.gz
)
```

ハッシュの一致と、メンバーが`rhel7-cve-initial/`配下であることを確認します。絶対パス、`../`、想定外の内容があれば展開しません。

```bash
STAGE=$(mktemp -d /var/tmp/rhel7-cve-fetch.XXXXXX)
tar -xzf "$INBOX/rpm99-original.tar.gz" -C "$STAGE"
(
  set -e
  cd "$STAGE/rhel7-cve-initial"
  sha256sum -c SHA256SUMS
)
BUNDLE="$STAGE/rhel7-cve-bundle"
mkdir -p "$BUNDLE/rpms" "$BUNDLE/records" "$STAGE/candidates"
cp -p -- "$STAGE"/rhel7-cve-initial/rpms/*.rpm "$BUNDLE/rpms/"
cp -p -- "$STAGE/rhel7-cve-initial/records/rpm-inventory.tsv" \
  "$BUNDLE/records/original99-inventory.tsv"
printf 'Bの作業場所: %s\n' "$STAGE"
```

以後、原本は`rhel7-cve-initial`に残し、実際に搬送するRPMだけを`rhel7-cve-bundle/rpms`で管理します。不要なRPMがあれば管理者が理由を記録して搬送候補から外します。自動削除はしません。

## 7. 社内リポジトリで不足候補を調べる

### 7.1 使ってよいリポジトリを限定する

実行場所：B。既存設定は書き換えません。以下はメタデータ・キャッシュを取得することがあります。

```bash
export LC_ALL=C
yum repolist all
read -r -a APPROVED_REPOS -p '承認済み社内リポジトリIDを空白区切りで入力: '
test "${#APPROVED_REPOS[@]}" -gt 0 \
  || printf 'NG: リポジトリIDが1つも入力されていません\n' >&2
REPO_ARGS=(--disablerepo='*')
for REPO_ID in "${APPROVED_REPOS[@]}"; do
  case "$REPO_ID" in
    *'*'*|*'?'*) printf 'NG: ワイルドカードは使えません: %s\n' "$REPO_ID" >&2 ;;
    *)           REPO_ARGS+=("--enablerepo=$REPO_ID") ;;
  esac
done
printf '実際に使う引数:\n'
printf '  %s\n' "${REPO_ARGS[@]}"
yum "${REPO_ARGS[@]}" repolist -v > "$BUNDLE/records/repositories.txt" 2>&1
cat "$BUNDLE/records/repositories.txt"
```

リポジトリIDは表示名やURLとは別です。空入力・ワイルドカードは使わず、管理者が承認した実際のIDだけを指定します。`NG:`が表示されたら先へ進めず入力をやり直します（このブロックはサブシェルではないため、`exit`ではなく表示で知らせる作りにしています）。`printf '  %s\n' "${REPO_ARGS[@]}"`で、実際にYumへ渡す引数も毎回確認します。`repolist -v`には社内URLが含まれるため、ログは社内で取り扱います。

同じリポジトリIDが複数の`.repo`ファイルで定義されていると、どちらの設定が使われるか分かりにくくなります。`yum repolist all`の結果と`/etc/yum.repos.d/`の内容が1対1で対応しているかも管理者と確認します。

**認証情報がroot専用の環境では、一般ユーザーの`yum`/`repoquery`/`yumdownloader`が失敗する可能性があります**（クライアント証明書や鍵ファイルの権限によります。未検証）。その場合は本章以降も`sudo`付きで実行します。あわせて、一般ユーザーのYumは`/var/tmp/yum-<ユーザー名>-*`を、`sudo yum`は`/var/cache/yum`を使い、メタデータのキャッシュが別系統になります。第7章の計画と第8章の取得候補が別時点のメタデータにならないよう、`sudo`の有無はどちらかに統一してください。

対象と同じ製品・アーキテクチャ・承認されたコンテンツ世代で、必要な通常/Optional等/ELSのコンテンツがそろっていることを確認します。取得できないRPMをCentOSや別メジャーバージョンのRPMで代用しません。

### 7.2 99個を一つの更新計画として予備確認する

```bash
sudo yum "${REPO_ARGS[@]}" \
  --assumeno --setopt=alwaysprompt=1 --setopt=tsflags=test \
  --setopt=localpkg_gpgcheck=1 --setopt=skip_broken=0 \
  localinstall "$BUNDLE"/rpms/*.rpm \
  > "$BUNDLE/records/online-plan.log" 2>&1
ONLINE_RC=$?
cat "$BUNDLE/records/online-plan.log"
printf 'online plan exit code: %s\n' "$ONLINE_RC"
```

`--assumeno`で確認に「いいえ」と答え、`alwaysprompt=1`で確認を必須にします。さらに`tsflags=test`を指定します。パッケージの実更新はしません。プラグインはBの通常設定に従うため、独自プラグインの副作用は管理者が確認してください。

> `--setopt=localpkg_gpgcheck=1`は、この実行では実際には働きません。Yumはローカルファイルの署名検査を「確認画面でyesと答えた後」に行うため、`--assumeno`で中止するこの実行は署名検査まで到達しません。保険として付けていますが、署名の確認は`rpm -Kv`（第5・9・10章）と第10.4節のトランザクションテストで行います。

> `--assumeno`で中止すると、Yumは解決済みのトランザクションを`/tmp/yum_save_tx.<日付>.<時刻>.XXXXXX.yumtx`へ自動保存し、`Your transaction was saved, rerun it with: yum load-transaction ...`と案内します。**この案内に従って`yum load-transaction`を実行しないでください。実更新になります。**作成されたファイルは記録として残し、不要になったら承認後に削除します。

`Installing for dependencies`などに現れる追加候補を読みます。`--assumeno`による中止では`Exiting on user command`が表示され、終了コードは1になります。これは意図的な中止であり、依存解決の失敗ではありません。終了コードだけで依存解決失敗と断定せず、計画とエラー本文を確認します（`Operation aborted`はRHEL 8以降のDNFの表示で、Yum 3では出ません）。

### 7.3 渡したRPMが黙って外されていないか確認する

計画は「余計なものが入っていないか」だけでなく、**渡したRPMが計画から外れていないか**も読みます。Yumの`localinstall`は、次の場合に警告だけを出してそのRPMを計画から除外します。

| 警告に現れる文字列 | 起きていること |
|---|---|
| `Cannot open: ... Skipping.` | RPMファイルを読めなかった |
| `... does not update installed package.` | 同版または旧版が導入済みで更新にならない |
| `Not a compatible architecture` | アーキテクチャが合わない |
| `It is obsoleted by installed package` | 導入済みパッケージに置き換えられている |
| `Excluding ...` | `yum.conf`の`exclude`に該当した |

残ったRPMだけで依存解決が通れば、終了コードも計画表示も正常に見えます。そのままでは、CVE対応RPMの一部が未検証のまま「問題なし」として扱われます。次のコマンドで警告を機械的に拾います。

```bash
grep -n -E 'Cannot open|Skipping|does not update installed package|Not a compatible architecture|obsoleted by installed package|^Excluding ' \
  "$BUNDLE/records/online-plan.log" || printf '除外警告はありません\n'
```

1件でも出たら、そのRPMを計画に含めるのか、今回の対象外として台帳に記録するのかを管理者と決めます。なお`grep`は一致が無いと終了コード1を返すため、`|| printf`で「警告なし」を明示しています。

**ここで追加が0個でも、Cで追加不要とは限りません。** Bにすでに導入済みなら、Bの計画上は満たされているためです。候補がなければ第9・10章へ進み、Cの不足条件を持ち帰ります。

補助的に、各RPMが要求する条件を表示できます。

```bash
rpm -qpR "$BUNDLE"/rpms/*.rpm > "$BUNDLE/records/all-requires.txt"
```

この一覧は「要求条件の一覧」であり「Cに不足しているものの一覧」ではありません。Cに導入済みのRPM、同時に渡す別のRPMが条件を満たす場合があります。RPMを1個ずつテストすると、同時更新で解決する関係を不足と誤認するため、最終テストはまとめて実施します。

## 8. 追加の依存RPMを取得する

### 8.1 必要な機能を提供するRPMを探す

実行場所：B。第7章の`REPO_ARGS`を引き継ぎます。Cのエラーがある場合はその不足条件を優先します。

```bash
read -r -p '不足している依存条件をそのまま入力: ' REQUIREMENT
repoquery "${REPO_ARGS[@]}" --show-duplicates \
  --whatprovides "$REQUIREMENT"
```

例として`example-common = 1.2-3.el7`や`libexample.so.1()(64bit)`を入力します。`Requires:`という表示ラベル自体は含めません。名前だけに削って検索すると版の条件を見落とします。

`--whatprovides`は「この条件を提供するパッケージ」を調べます。検索対象はリポジトリ側で、Bに導入済みのパッケージは結果から除かれます。`--show-duplicates`は最新版だけに絞らず、同じ名前の複数の版を表示させる指定です。

> `--pkgnarrow`は指定しません。manページは既定値を`repository`と書いていますが、`repoquery`の実装側の既定値は`repos`で、しかも`--whatprovides`の経路ではこの値が参照されません。指定しても効果がなく誤解を招くだけなので、既定のまま使います。

結果が複数なら、Cに適合し、同時更新するパッケージとの版一致条件も満たすものを選びます。無関係な提供元を全部入れません。認証にプラグインが必要な社内環境では、管理者が`repoquery --plugins`の要否を確認します。

### 8.2 正確な版を指定してダウンロードする

```bash
read -r -p '採用する完全なNEVRA（repoqueryの結果）: ' PACKAGE_SPEC
CANDIDATE=$(mktemp -d "$STAGE/candidates/item.XXXXXX")
yumdownloader "${REPO_ARGS[@]}" --destdir="$CANDIDATE" "$PACKAGE_SPEC" \
  > "$CANDIDATE/download.log" 2>&1
DOWNLOAD_RC=$?
cat "$CANDIDATE/download.log"
printf 'download exit code: %s\n' "$DOWNLOAD_RC"
find "$CANDIDATE" -maxdepth 1 -type f -name '*.rpm' -printf '%f\n'
```

`--destdir`は保存先です。`yumdownloader`はRPMを保存し、Bにインストールしません。終了コードだけでなく、指定したRPMが実際に保存されたことを確認します。単にパッケージ名だけを指定すると意図した版と異なるものを取得する可能性があります。

```bash
rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' \
  "$CANDIDATE"/*.rpm
rpm -Kv "$CANDIDATE"/*.rpm
rpm -qp --provides "$CANDIDATE"/*.rpm
rpm -qpR "$CANDIDATE"/*.rpm
```

確認する順番は、指定した版・アーキテクチャか、署名が信頼できるか、必要な条件を提供するか、さらに何を必要とするか、です。

追加RPMは次の表で記録します。台帳は`$BUNDLE/records/dependency-decisions.tsv`などに保存します。

| 不足条件 | 要求しているRPM | 採用NEVRA | 取得リポジトリ/日付 | 追加理由・承認 |
|---|---|---|---|---|
| 実際のエラーから転記 | 実際のRPM名 | 正確な版 | 社内ID・取得日 | Cの不足解消など |

採用を確認したRPMだけ搬送用ディレクトリへコピーします。同名ファイルがあれば自動上書きしません。

```bash
(
  set -e
  shopt -s nullglob
  FILES=("$CANDIDATE"/*.rpm)
  test "${#FILES[@]}" -gt 0 \
    || { printf 'NG: 取得したRPMが1件もありません\n' >&2; exit 1; }
  for FILE in "${FILES[@]}"; do
    test ! -e "$BUNDLE/rpms/${FILE##*/}" \
      || { printf 'NG: 同名ファイルが既にあります: %s\n' "${FILE##*/}" >&2; exit 1; }
  done
  cp -p -- "${FILES[@]}" "$BUNDLE/rpms/"
  printf 'OK: %s件を搬送用ディレクトリへコピーしました\n' "${#FILES[@]}"
)
```

コピーを止めた場合は同一RPMの重複か、同名で内容が異なるかを確認します。異なる版はファイル名も異なるため、このチェックだけでは版の混在を防げません。最終一覧も必ず確認します。

### 8.3 自動依存取得を使う場合の注意

`yumdownloader --resolve`は依存解決と追加取得を行えます。ただしBの導入状態に影響されるため、**C向けに全依存RPMがそろう保証にはなりません**。使う場合も採用ディレクトリとは別の候補領域で実施し、取得物を確認します。[Red Hat：インストールせずにRPMを取得する方法](https://access.redhat.com/solutions/10154)（要ログイン）

DNFの`--alldeps`をRHEL 7の`yumdownloader`で使えると決めつけないでください。導入済み版の`--help`・manページで確認します。本書の主手順はそのオプションに依存しません。

`yum localinstall --downloadonly`もBの状態で計画を組むため、Cとの構成差を解消する手段にはなりません。空の`--installroot`で全依存を集める方式もCの構成再現とは異なり、追加の設計・検証が必要なので本書では使いません。

## 9. 搬送用セットを作る

実行場所：B。第8章で不足候補の採用が終わった時点で実施します。Cで不足が出た場合もここから作り直します。

最終的なディレクトリは次の形です。

```text
rhel7-cve-bundle/
├─ rpms/                     最初のRPM群＋承認済みの追加RPM
├─ records/
│  ├─ original99-inventory.tsv
│  ├─ final-inventory.tsv
│  ├─ final-filenames.txt     搬送するRPMのファイル名一覧（Cで差分照合に使う）
│  ├─ dependency-decisions.tsv
│  ├─ repositories.txt
│  ├─ online-plan.log
│  ├─ signatures.txt
│  ├─ signature-detail.tsv    各RPMの署名欄（未署名の検出用）
│  └─ cve-rhsa-mapping.tsv    別途作成するCVE/RHSA対応表
└─ SHA256SUMS
```

`cve-rhsa-mapping.tsv`には、CVE・RHSA URL・対象製品・更新前NEVRA・承認した修正後NEVRA・搬送ファイル名を記録します。対象CVE未指定のため本書では実データを作れません。

```bash
export LC_ALL=C
rpm -Kv "$BUNDLE"/rpms/*.rpm > "$BUNDLE/records/signatures.txt" 2>&1
SIGNATURE_RC=$?
cat "$BUNDLE/records/signatures.txt"
printf 'signature check exit code: %s\n' "$SIGNATURE_RC"
for RPM_FILE in "$BUNDLE"/rpms/*.rpm; do
  RPM_SIG=$(rpm -qpi "$RPM_FILE" 2>/dev/null | sed -n 's/^Signature *: *//p')
  printf '%s\t%s\n' "${RPM_FILE##*/}" "${RPM_SIG:-(取得失敗)}"
done > "$BUNDLE/records/signature-detail.tsv"
awk -F'\t' '$2 == "(none)" || $2 == "(取得失敗)" { print $1 }' \
  "$BUNDLE/records/signature-detail.tsv"
```

最後の`awk`が何も出力しないこと（＝署名ヘッダーのないRPMがないこと）と、署名と鍵の承認を確認してから続けます。
第8章で追加したRPMも、ここでまとめて再確認する点が大切です。`export LC_ALL=C`は、この後の`sort`の並びをCでの照合とそろえるために再指定しています。

```bash
(
  set -e
  cd "$BUNDLE"
  rpm -qp --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' \
    rpms/*.rpm > records/final-inventory.tsv
  find rpms -maxdepth 1 -type f -name '*.rpm' -printf '%f\n' \
    | sort > records/final-filenames.txt
  wc -l records/final-filenames.txt
  sha256sum rpms/*.rpm > SHA256SUMS
  sha256sum -c SHA256SUMS
)
```

原本からの除外・置換・追加を台帳で説明できることを確認します。初期99個の全部が採用対象として承認されている場合、最終件数は99＋追加の重複なし件数です。収集候補を無条件に全部混ぜないでください。

```bash
DELIVERY=$(mktemp -d "$STAGE/delivery.XXXXXX")
(
  set -e
  tar -czf "$DELIVERY/rhel7-cve-bundle.tar.gz" -C "$STAGE" rhel7-cve-bundle
  cd "$DELIVERY"
  sha256sum rhel7-cve-bundle.tar.gz > rhel7-cve-bundle.tar.gz.sha256
  sha256sum -c rhel7-cve-bundle.tar.gz.sha256
)
printf '搬送する2ファイルの保存場所: %s\n' "$DELIVERY"
```

作成したアーカイブと`.sha256`をCへ搬送します。更新のたびに別の`delivery.*`ができるので、どの版を渡したか記録します。Bの古い搬送物とCの新しいログを混同しないでください。

## 10. 対象サーバーでオフライン検証する

### 10.1 搬送物を照合し、新しい場所に展開する

実行場所：C。作業承認を得てから実施します。

```bash
export LC_ALL=C
read -r -p '搬送用アーカイブとsha256ファイルの保存ディレクトリ: ' RECEIVED
(
  set -e
  cd "$RECEIVED"
  sha256sum -c rhel7-cve-bundle.tar.gz.sha256
  tar -tzf rhel7-cve-bundle.tar.gz
)
```

ハッシュとメンバー名を確認してから展開します。

```bash
VERIFY_ROOT=$(mktemp -d /var/tmp/rhel7-cve-verify.XXXXXX)
tar -xzf "$RECEIVED/rhel7-cve-bundle.tar.gz" -C "$VERIFY_ROOT"
PAYLOAD="$VERIFY_ROOT/rhel7-cve-bundle"
LOGDIR="$VERIFY_ROOT/verification-logs"
mkdir -p "$LOGDIR"
(
  set -e
  cd "$PAYLOAD"
  sha256sum -c SHA256SUMS
  find rpms -maxdepth 1 -type f -name '*.rpm' -printf '%f\n' \
    | sort > "$LOGDIR/received-filenames.txt"
  diff -u records/final-filenames.txt "$LOGDIR/received-filenames.txt"
)
```

全RPMのハッシュが`OK`、ファイル一覧の差分がないことが条件です。ハッシュ一覧にない余計なRPMの混入もファイル一覧で確認します。

### 10.2 Cで署名と現在の導入状態を確認する

```bash
rpm -Kv "$PAYLOAD"/rpms/*.rpm > "$LOGDIR/signatures.txt" 2>&1
SIGNATURE_RC=$?
cat "$LOGDIR/signatures.txt"
printf 'signature check exit code: %s\n' "$SIGNATURE_RC"
rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' \
  | sort > "$LOGDIR/installed-before-test.tsv"
```

署名者を含めて検証できない場合は中断します。`--nogpgcheck`で先へ進めません。第4章以降にパッケージ構成が変わっていれば、その差分を確認し、最新状態を前提に検証し直します。

### 10.3 更新計画だけを表示する

以下は外部リポジトリをすべて無効にして、ローカルRPM群を同時に渡します。`createrepo`や恒久的な`.repo`作成は不要です。

```bash
sudo yum --noplugins --disablerepo='*' \
  --assumeno --setopt=alwaysprompt=1 --setopt=tsflags=test \
  --setopt=localpkg_gpgcheck=1 --setopt=skip_broken=0 \
  localinstall "$PAYLOAD"/rpms/*.rpm \
  > "$LOGDIR/offline-plan.log" 2>&1
PLAN_RC=$?
cat "$LOGDIR/offline-plan.log"
printf 'offline plan exit code: %s\n' "$PLAN_RC"
```

| 計画中の表示 | 読み方・確認事項 |
|---|---|
| `Installing` | 新規導入。追加理由が承認されているか |
| `Updating` | 既存パッケージの更新。意図した版か |
| `Removing` / 行中の `replacing` | 削除・置換。想定外なら中断 |
| カーネルの追加や旧版削除 | 起動・復旧用カーネルへの影響を個別確認 |
| `Requires:` / `Error:` | 依存不足・不整合。Bへ持ち帰る |
| `Nothing to do` | 対象なし・同版導入済み等。目的達成とは限らない |
| `Exiting on user command` | `--assumeno`による意図的な中止。終了コードは1。直前の計画を確認 |
| `Skipping` / `does not update installed package` | 渡したRPMが計画から外された。下の確認手順を実施 |

`Obsoleting`はYum 3の計画表の見出しではありません。置き換えは`Removing`と、各行に続く`replacing`で表示されます（`Obsoleting`は`yum history`側の状態名です）。

第7.3節と同じく、計画から黙って外されたRPMがないかを確認します。**Cでの判定が最終判断なので、この確認はCでも必ず実施します。**

```bash
grep -n -E 'Cannot open|Skipping|does not update installed package|Not a compatible architecture|obsoleted by installed package|^Excluding ' \
  "$LOGDIR/offline-plan.log" || printf '除外警告はありません\n'
```

さらに、搬送したRPMのパッケージ名が計画ログに現れているかを突き合わせます。

```bash
awk -F'\t' '{ print $1 }' "$PAYLOAD/records/final-inventory.tsv" \
  | sort -u > "$LOGDIR/expected-names.txt"
while read -r PKG_NAME; do
  grep -qF -- "$PKG_NAME" "$LOGDIR/offline-plan.log" \
    || printf '計画ログに現れないパッケージ名: %s\n' "$PKG_NAME"
done < "$LOGDIR/expected-names.txt"
```

`grep -qF`は部分一致の簡易確認です。あるパッケージ名が別のパッケージ名の一部になっている場合は見逃すため、上の警告検索と計画表の目視を必ず併用します。それでも「1つも現れない名前」を拾えるので、取り違えや取りこぼしの発見には役立ちます。

不足があれば、`offline-plan.log`の必要部分と最新の導入一覧をBへ渡し、第8章へ戻ります。追加RPMの依存条件もあるので、往復が複数回になることがあります。

### 10.4 トランザクションテストを実行する

実行条件：計画の内容、署名、運用上のロックや除外条件を管理者が確認済みであること。

> `--setopt=tsflags=test`が実更新を防ぐ重要な指定です。削除・省略しないでください。今回は`-y`を付けず、確認画面で計画を再確認します。署名鍵のインポートや想定外の変更を求められたら中止してください。

```bash
sudo yum --noplugins --disablerepo='*' \
  --setopt=tsflags=test --setopt=alwaysprompt=1 --setopt=assumeyes=0 \
  --setopt=assumeno=0 --setopt=localpkg_gpgcheck=1 --setopt=skip_broken=0 \
  localinstall "$PAYLOAD"/rpms/*.rpm 2>&1 | tee "$LOGDIR/offline-test.log"
TEST_PIPE_STATUS=("${PIPESTATUS[@]}")
printf 'yum exit code: %s; tee exit code: %s\n' \
  "${TEST_PIPE_STATUS[0]}" "${TEST_PIPE_STATUS[1]}"
```

`Is this ok [y/d/N]:`などの確認画面では、実行した行に`tsflags=test`があることと計画をもう一度確認し、テストを進める場合だけ`y`を入力します。`tee`は画面表示とログ保存を同時に行います。通常の`$?`だけでは最後の`tee`の成否しか分からないため、直後に`PIPESTATUS`を保存しています。

> `tee`を通すと標準出力がパイプになるため、`Is this ok [y/d/N]:`のプロンプトが画面に出ないまま入力待ちになる可能性があります（Yum 3はPython 2の`raw_input`でプロンプトを出しており、パイプ時にフラッシュされない可能性があるためです。実機未検証）。一覧表までは表示されるのにプロンプトだけ出ない場合も、入力自体は受け付けられています。`offline-plan.log`で計画を確認済みであれば`y`と改行を入力します。確実に表示させたい場合は`sudo env PYTHONUNBUFFERED=1 yum ...`を試すか、`tee`を使わず`script`コマンドでログを採る方法を管理者と検討します。事前にBで同じ形式を1回試しておくと安全です。

Yum 3では`Running transaction check`→`Running transaction test`→`Transaction test succeeded`の順に表示されます。`tsflags=test`を付けているため、この後に`Running transaction`と出ても実際のファイル更新は行われません。表示は版により異なり得ますが、`Transaction test succeeded`、`yum`の終了コード0、ログ保存の終了コード0を確認します。コード0だけでなく、対象の更新計画が実際に組まれたかも確認します。`Nothing to do`なら「今回の更新をテスト済み」とは記録しません。

**`tsflags=test`のテストは`yum history`に残りません。** Yumは`tsflags`に`test`が入っている場合、履歴の記録そのものを行いません。実施記録は本書のログファイル（`offline-plan.log`・`offline-test.log`）で残します。

テスト後にパッケージ一覧が変わっていないことを確認します。

```bash
rpm -qa --qf '%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n' \
  | sort > "$LOGDIR/installed-after-test.tsv"
diff -u "$LOGDIR/installed-before-test.tsv" "$LOGDIR/installed-after-test.tsv"
```

通常は差分なしです。差分があれば他の管理処理との同時実行なども含めて調査し、完了にしません。パッケージ一覧の一致は、ファイルシステムへの一切の書き込みがない証明ではありません。

根拠：[Yum設定の公式マニュアル（tsflags・署名・確認動作）](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.conf.5)。

### 10.5 テストで確認できないこと

| 確認できる範囲 | これだけでは確認できない範囲 |
|---|---|
| Cの現在のRPM情報に対する依存解決 | 更新後のアプリケーション動作 |
| 提示したRPM群の更新計画・競合など | インストールスクリプトの実行成功 |
| 署名やファイル整合性の別途確認 | サービスの正常再起動、OSの起動 |
| テスト時点の条件での可否 | 目的のCVEが確実に修正されたこと |

更新後の動作を保証するには、別途、対象を再現した検証環境での実更新とアプリケーション試験が必要です。本手順の結果を「本番更新成功」と報告しないでください。

## 11. エラーの読み方と対処

| 表示・状況 | 考えられる意味 | 次の行動 |
|---|---|---|
| `Requires: xxx` | 要求された機能・版を満たせない | 条件全文をBの`repoquery --whatprovides`で調査 |
| `xxx = 1.2-3.el7` | 版が完全一致する依存 | 関連RPMを同じ版でそろえる |
| `conflicts with file from package` | ファイルの所有・内容が競合 | 両RPMの製品・版・提供元を確認 |
| `Protected multilib versions` | x86_64とi686等の版不一致 | 必要な両アーキテクチャの版を確認 |
| `NOKEY` | 検証鍵がない | 承認済み鍵の確認手順を管理者へ依頼 |
| `No package ... available` | 指定版が見えない | ID・同期内容・版指定・権利を確認 |
| `Cannot find a valid baseurl`等 | 取得元・接続・認証の問題 | Bのリポジトリ接続を確認。依存不足と混同しない |
| 空き容量不足 | 展開・更新に必要な容量がない | `/var`、`/boot`、ルート等を調査 |
| ロック待ち | 別のyum/rpm処理が動いている可能性 | 管理者へ実行状況を確認。ロックを消さない |
| 同版導入済み・より新しい版がある | 初期99個とCの状態が合っていない | 最新の一覧とRHSAで採用対象を再判断 |
| `Exiting on user command` | `--assumeno`で確認を「いいえ」にした | 異常ではない。計画とエラー本文を読む |
| `does not update installed package` | 同版・旧版が導入済みで更新にならない | 第7.3・10.3節の確認手順で計画からの除外を確認 |
| `Cannot open: ... Skipping.` | RPMファイルを読めず計画から外された | ハッシュ・権限・破損を確認し、搬送をやり直す |

使用しない回避策：`--nodeps`、`--force`、`--skip-broken`、`--nogpgcheck`、`--ignorearch`。依存関係や検証を無視して進めると、CVE対応の抜けやシステム不整合を隠すおそれがあります。

`rpm -Uvh --test *.rpm`を主手順にしない理由は、yumの依存解決・運用設定と同じ評価ではなく、カーネルのinstallonly扱いなども異なるためです。特に`--test`を外した一括実行は、この手順の対象外です。

補足：更新だけが目的で新規導入を一切許したくない場合、`localinstall`の代わりに`localupdate`を使う方法もあります。導入済みでないパッケージには`Package ... not installed, cannot update it. Run yum install to install it instead.`の警告が出るため、意図しない新規導入を機械的に弾けます。ただし`yum`のmanページは`localupdate`を「互換のために残しているだけ」と記しており、カーネルはinstallonly扱いなので`localupdate`でも新しい版が追加されます。本書は新規導入の可否を計画表で人が確認する方式にしているため、主手順では`localinstall`を使います。

## 12. 完了判定と実更新への引き継ぎ

### オフライン更新準備の完了条件

- [ ] 元の99個、一覧、アーカイブ、ハッシュ値を保存した。
- [ ] 各CVE・RHSAと採用する修正後RPMの対応を確認した。
- [ ] 取得元の製品・アーキテクチャ・コンテンツ世代・ELSの条件を確認した。
- [ ] 原本からの追加・除外・置換理由を台帳に記録した。
- [ ] 搬送後の全RPMのハッシュ、ファイル一覧、署名を確認した。
- [ ] C上の計画で更新対象と版、新規導入、削除・置換に意図しないものがない。
- [ ] C上の計画ログに`Cannot open`・`Skipping`・`does not update installed package`・`Not a compatible architecture`・`obsoleted by installed package`・`Excluding`の警告がない（あれば台帳で処置を説明した）。
- [ ] 搬送したRPMのパッケージ名が計画ログに現れている（計画から黙って外されたRPMがない）。
- [ ] versionlock・exclude・独自プラグイン等、実運用条件との相違を解決した。
- [ ] C上で依存解決とトランザクションテストが成功した。
- [ ] テスト前後の導入済みパッケージ一覧が一致した。
- [ ] 最終アーカイブのハッシュ、サーバー、日時、実行者、ログを対応付けた。

### 実更新の前に別途必要な作業

バックアップと復元試験、停止・再起動計画、対象を再現した環境での実更新試験、アプリケーション確認項目、障害時の連絡先、変更承認をそろえます。カーネルを含む場合は起動先と復旧用カーネルを確認し、更新後には実際に動作しているカーネルも確認します。ユーザー空間のライブラリ更新でも関連プロセスの再起動が必要になる場合があります。

`yum history undo`は完全なバックアップ復元の代わりではありません。旧版RPMの入手可否やスクリプトによる変更などが関係するため、復旧方法を事前に検証します。

### 作業領域を片付ける時期

本手順はリポジトリ設定を書き換えず、主に新規作業領域へファイルを保存します。ターミナルを終了すると変数設定は失われます。成果物とログは社内の保管期間に従って保存し、削除は別途承認後に行います。`/var/tmp`は恒久保管場所ではないため、最終成果物は承認された保管先へコピーしてください。本書に一括削除コマンドは載せません。

## 13. コマンドと記号の早見表

### まず覚えるもの

| 書式 | 意味 |
|---|---|
| `tar -czf ファイル.tar.gz ディレクトリ` | `-c / --create`で作成、`-z / --gzip`で圧縮、`-f / --file`で保存ファイル指定 |
| `tar -tzf ファイル.tar.gz` | `-t / --list`で内容一覧。展開しない |
| `tar -xzf ファイル.tar.gz -C 展開先` | `-x / --extract`で展開、`-C / --directory`で展開場所指定 |
| `sha256sum ファイル` | 内容からハッシュ値を計算 |
| `sha256sum -c 一覧` | `-c / --check`で記録済みハッシュと照合 |
| `rpm -qa` | `-q / --query`と`-a / --all`で導入済み全パッケージを照会 |
| `rpm -qp RPMファイル` | `-p / --package`でファイルを照会 |
| `rpm -qpR RPMファイル` | `-R / --requires`で必要な機能・版を表示 |
| `rpm -Kv RPMファイル` | `-K / --checksig`と`-v / --verbose`で署名等を詳しく確認。失敗時の語は`BAD`・`NOKEY`・`NOTRUSTED` |
| `rpm -qpi RPMファイル` | `-i / --info`で概要を表示。`Signature`欄が`(none)`なら署名なし |
| `rpm --qf '書式'` | `--queryformat`の短い別名。表示する情報を指定 |
| `repoquery --whatprovides '条件'` | 条件を提供するRPM候補を検索 |
| `yumdownloader --destdir=保存先 完全な版指定` | 指定したRPMを保存 |
| `yum --disablerepo='*'` | その呼び出しで全リポジトリを無効化 |
| `yum --assumeno` | 確認を「いいえ」にする。計画確認に利用 |
| `yum --setopt=tsflags=test` | RPMトランザクションをテスト指定にする |

### コードに出てくるBashの記号

| 記号・命令 | 意味 |
|---|---|
| `read -r -p '質問' 変数` | 入力を変数に保存。`-r`はバックスラッシュを特別扱いしない |
| `"$WORK"` | 変数の値を使用。引用符は空白による分割を防ぐ |
| `$(コマンド)` | コマンドの出力を変数等に取り込む |
| `*.rpm` | 該当する複数ファイルに展開。採用済みディレクトリだけで使う |
| `> ファイル` | 標準出力を保存。同名ファイルは上書きする |
| `2>&1` | 標準エラー出力も標準出力と同じ場所へ送る |
| `コマンド1 \| コマンド2` | 1の標準出力を2の標準入力へ渡す |
| 行末の `\` | コマンドが次の行へ続く。直後に空白を置かない |
| `(...)` | サブシェル。この中の`cd`等が外に残らない |
| `set -e` | このサブシェル内で通常のコマンド失敗時に止める。パイプ途中の失敗をすべて検出するものではない |
| `shopt -s nullglob` | ワイルドカードに一致がなければ空の一覧にする |
| `ARRAY=(...)` / `"${ARRAY[@]}"` | 複数の引数を配列として保持し、個別の引数として渡す |
| `test` | 条件判定。`-eq`は数の一致、`-gt`は大小、`-e`は存在 |
| `${FILE##*/}` | パスからファイル名部分を取り出す |
| `cp -p --` | 時刻等を可能な範囲で保持してコピー。`--`はオプションの終わり |
| `find ... -maxdepth 1 -type f` | 指定場所の直下の通常ファイルだけを対象にする |
| `sort` / `wc -l` / `diff -u` | 並べ替え／行数確認／差分表示 |
| `grep -E '条件1\|条件2'` | 複数の文字列のどれかを含む行を探す |
| `grep -qF -- '文字列'` | 固定文字列で検索し、結果を表示せず有無だけを返す |
| `awk -F'\t' '条件 { print $1 }'` | タブ区切りの列を条件付きで取り出す |
| `コマンド \|\| { ...; exit 1; }` | 失敗したときだけ中身を実行する。`test`の無言の失敗を可視化する |

余裕があれば覚えるもの：`rpm -q --whatprovides '条件'`はそのサーバーに導入済みの提供元を調べます。リポジトリ検索の`repoquery --whatprovides`と検索対象が違います。`rpm -qp --scripts RPMファイル`では更新時のスクリプトを表示できますが、表示だけで実行成功を保証できません。

## 14. 確認問題

1. Bで依存不足が0件なら、Cでも不足しませんか？
2. SHA-256が一致すれば、承認されたRed Hatの修正版と断定できますか？
3. Cのトランザクションテスト成功で、更新後のアプリ動作まで確認できますか？
4. `rpm -Kv`が終了コード0で終われば、そのRPMは署名済みと言えますか？
5. 計画表に意図しない追加・削除がなく終了コードも0なら、完了にしてよいですか？

解答：

1. いいえ。BとCの導入状態が違うため、Cで確認します。
2. いいえ。ハッシュ一致、署名者の確認、CVE/RHSAとの対応確認は別の検証です。
3. いいえ。実更新・スクリプト実行・サービス再起動・アプリケーション試験は別途必要です。
4. いいえ。署名ヘッダーがないRPMはダイジェストだけで`OK`になり、終了コードも0になります。`rpm -qpi`の`Signature`欄で署名の有無を別に確認します（第5.3節）。
5. いいえ。`localinstall`は読めないRPMや同版導入済みのRPMを警告だけで計画から外すため、「渡したRPMが計画に入っているか」も確認しないと、CVE対応RPMの取りこぼしに気づけません（第7.3・10.3節）。

## 15. 公式参照

RHEL 7の手順なので、現行DNFだけでなくYum 3系とRPM 4.11系の公式資料を参照しています。開発元のmaster文書にはRHEL 7にない機能も含み得るため、実行前に導入済み版の`man yum`、`man yum.conf`、`man rpm`、`man yumdownloader`、`man repoquery`および`--help`でも確認してください。

下表の「開発元」は、Yum / Yum Utils / RPM の開発リポジトリにある文書（masterまたは4.11系ブランチ）です。RHEL 7同梱版との差異があり得るうえ、開発リポジトリの文書は移動・改名される場合があります。リンクが開けないときは、各プロジェクトのリポジトリ内を検索してください。また`access.redhat.com/solutions/`配下の記事は、閲覧にRed Hatのサブスクリプションでのログインが必要です。

| 資料 | 本書で確認した内容 |
|---|---|
| [Red Hat：RHEL 7 System Administrator’s Guide — Yum](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-yum) | RHEL 7のYum、ローカルRPMの扱い |
| [Red Hat：How to use dnf/yum to download a package without installing it](https://access.redhat.com/solutions/10154)（要ログイン） | yumdownloader、downloadonly、保存先、依存取得 |
| [Yum開発元：yum(8)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.8) | localinstall、確認中止、リポジトリ指定、プラグイン、版指定 |
| [Yum開発元：yum.conf(5)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.conf.5) | tsflags、localpkg_gpgcheck、alwaysprompt、multilib、installonly |
| [Yum Utils開発元：yumdownloader(1)](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/yumdownloader.1) | ダウンロードとresolve |
| [Yum Utils開発元：yumdownloaderの実装](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/yumdownloader.py) | 依存解決がYumの状態を使用すること |
| [Yum Utils開発元：repoquery(1)](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/repoquery.1) | 提供元検索、利用可能パッケージ、NEVRA |
| [RPM開発元：RPM 4.11系 rpm(8)](https://raw.githubusercontent.com/rpm-software-management/rpm/rpm-4.11.x/doc/rpm.8) | 照会、依存条件、署名、テストの範囲 |
| [GNU tar Manual](https://www.gnu.org/software/tar/manual/tar.html) | 作成・一覧・展開・圧縮 |
| [GNU Coreutils：SHA-2 utilities](https://www.gnu.org/s/coreutils/manual/html_node/sha2-utilities.html) | SHA-256による照合 |
| [Red Hat：Security Backporting Practice](https://access.redhat.com/security/updates/backporting) | バックポートと版番号の判断 |
| [Red Hat：RHEL 7 End of Maintenance FAQ](https://access.redhat.com/articles/7005471)（要ログインの場合あり） | RHEL 7.9とELSの対象・期間 |

### この文書の検証範囲

公式情報を参照して手順を構成し、26個のBashコードブロックに構文チェックを実施しました。目次のリンク先とコードブロックの対応も確認しています。ただし、実際の99個のRPM、社内リポジトリ、RHEL 7.9対象サーバーに対するコマンド実行は行っていません。各RPMの採用可否、必要な追加件数、CVE修正の網羅性、導入済みYumの個別挙動は現場で確認が必要です。

---

[← 全体の目次にもどる](../README.md)
