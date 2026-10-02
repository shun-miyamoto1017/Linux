# dnfコマンド④ オンライン環境での更新手順

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **対象サーバ自身がリポジトリに届く環境での、月次パッチ適用と脆弱性対応の通し手順。**記録 → 調べる → 決める → 下見 → 事前取得 → 当てる → 確かめる の 0〜6 を 1 本につなげたもの |

> `dnf` 本体の使い方は [dnfコマンド① 基本と主要サブコマンド](./dnfコマンド①_基本と主要サブコマンド.md)、
> リポジトリの設定は [dnfコマンド② リポジトリとキャッシュの管理](./dnfコマンド②_リポジトリとキャッシュの管理.md)、
> **調査コマンドそのもの**は [dnfコマンド③ 依存関係とセキュリティ更新の調べ方](./dnfコマンド③_依存関係とセキュリティ更新の調べ方.md) にあります。
> **対象サーバがリポジトリに届かない場合**は
> [dnfコマンド⑤ オフライン環境でのパッケージの集め方](./dnfコマンド⑤_オフライン環境でのパッケージの集め方.md) と
> [dnfコマンド⑥ オフライン環境での適用と切り戻し](./dnfコマンド⑥_オフライン環境での適用と切り戻し.md) へ。

---

## 目次

- [このノートが対象にしている環境](#このノートが対象にしている環境)
- [作業の全体像](#作業の全体像)
- [ステップ0 いまの状態を記録する](#ステップ0-いまの状態を記録する)
- [ステップ1 何が更新できるか調べる](#ステップ1-何が更新できるか調べる)
- [ステップ2 何を当てるか決める](#ステップ2-何を当てるか決める)
- [ステップ3 下見する](#ステップ3-下見する)
- [ステップ4 事前に取得しておく](#ステップ4-事前に取得しておく)
- [ステップ5 当てる](#ステップ5-当てる)
- [ステップ6 当たったことを確かめる](#ステップ6-当たったことを確かめる)
- [再起動が要るかを判断する](#再起動が要るかを判断する)
- [切り戻す](#切り戻す)
- [当てたくないものを除外する](#当てたくないものを除外する)
- [定期実行 dnf-automatic](#定期実行-dnf-automatic)
- [よくある失敗と対処](#よくある失敗と対処)
- [作業チェックリスト](#作業チェックリスト)
- [RHEL 7（yum）との対応](#rhel-7yumとの対応)
- [参考リンク](#参考リンク)

---

## このノートが対象にしている環境

**「対象サーバの `dnf` が、自分でリポジトリを見に行ける」**状態です。
見に行く先がインターネットでも社内リポジトリサーバでも、**手順の骨格は同じ**です。
ただし社内ミラーの場合は、**アドバイザリ情報（`updateinfo`）が入っているか**と
**旧版の rpm が残っているか**を別に確認する必要があります（どちらも後述）。

```text
  [ このノート ]  対象サーバ ──HTTP(S)──▶ リポジトリ（インターネット / 社内ミラー）
  [ ⑤⑥ の担当 ]  対象サーバ  ×  どこにも届かない（rpm を手運びする）
```

**2 コマンドで判定できます。**

```bash
$ dnf --refresh repolist -v                 # 実際に取りに行かせて通るか（-v が必須）
$ dnf check-update                          # ここまで通れば、このノートの手順でよい
```

> **`dnf repolist` は `--refresh` を付けてもリポジトリに接続しません。**
> 到達できないリポジトリが有効になっていても、**一覧が出て終了ステータスは `0`** になります（実測）。
> **`-v` を付けるか `check-update` を使ってください。**どちらも到達不能なら
> `Failed to download metadata for repo ...` で終了ステータス `1` になります。

| 結果 | 読み方 |
|:--|:--|
| **リポジトリが並び、`--refresh` も通る** | **このノートの手順**でそのまま進められる |
| **`Failed to download metadata` になる** | 設定かネットワークの問題。まず [② リポジトリとキャッシュの管理](./dnfコマンド②_リポジトリとキャッシュの管理.md) を見る |
| **そもそも届く経路が無い** | [⑤](./dnfコマンド⑤_オフライン環境でのパッケージの集め方.md) の手運び手順へ |

> **「社内リポジトリだからオフライン」ではありません。**
> 対象サーバから社内リポジトリに HTTP で届くなら、それは**オンライン**です。
> 手運びは「どこにも届かないとき」だけの最終手段です。

---

## 作業の全体像

**脆弱性対応も月次パッチも、骨格はこの 0〜6 の 7 段階です。**

```text
  0. 記録     いまの状態をファイルに残す        ← 切り戻しと報告書の元になる
     ↓
  1. 調べる   何が更新できるか / どれが脆弱性対応か
     ↓
  2. 決める   全部当てるのか、セキュリティだけか、特定 CVE だけか
     ↓
  3. 下見     --assumeno で「何が動くか」を先に確定させる
     ↓
  4. 事前取得  窓の前に rpm を落としておく ＋ 切り戻し用の旧版も確保する
     ↓
  5. 当てる
     ↓
  6. 確かめる  更新されたか / 再起動が要るか / サービスは生きているか / 記録を残す
```

**ステップ 0 と 6 を飛ばさないでください。**
当てること自体より、**「当てる前の状態」と「どの `history` ID で当てたか」**のほうが後で効きます。
（以降「窓」と書いているのは**メンテナンスウィンドウ**＝作業を許された停止時間帯のことです）

---

## ステップ0 いまの状態を記録する

```bash
$ WORK=/var/tmp/patch-$(date +%F)                          # 作業用フォルダのパスを変数に入れる
$ mkdir -p $WORK/rpms && cd $WORK                          # 作って移動する（sudo は不要）
$ rpm -qa | sort > before-rpm.txt                          # 導入済みパッケージの一覧
$ uname -r > before-kernel.txt                             # 稼働中のカーネル
$ dnf repolist > before-repolist.txt                       # 有効なリポジトリ
$ grep -H "^exclude" /etc/dnf/dnf.conf /etc/yum.repos.d/*.repo > before-exclude.txt   # 除外設定を記録する
$ dnf versionlock list > before-versionlock.txt || true    # 固定設定を記録する（未導入でも止めない）
$ systemctl list-units --type=service --state=running > before-services.txt   # 稼働中サービス
$ dnf history list | head -20 > before-history.txt          # 直近の履歴
```

> **`$(date +%F)` を 2 回書かないでください。**日付をまたいだ瞬間に別のフォルダになります。
> 変数に入れてから使うと、その事故が起きません。
> また **`sudo mkdir` で作るとフォルダが root 所有になり、
> 続く `> before-rpm.txt` が `Permission denied` になります。**

| ファイル | 後で何に使うか |
|:--|:--|
| `before-rpm.txt` | 更新後の一覧と `diff` して、**実際に何が変わったか**を出す |
| `before-kernel.txt` | 再起動後に `uname -r` と比べて、**新カーネルで上がったか**を確認する |
| `before-services.txt` | 更新後に**落ちたサービスが無いか**を突き合わせる |
| `before-repolist.txt` | **見に行ったリポジトリ**を後から示せる |
| `before-exclude.txt` / `before-versionlock.txt` | **除外や固定のせいで当たらなかった**のを後から説明できる |
| `before-history.txt` | 切り戻し時に**どの ID まで戻すか**の目印 |

> **`/var/tmp` は `systemd-tmpfiles` によって一定期間で削除される設定になっていることがあります。**
> 証跡と切り戻し用の rpm は、**作業記録に転記するか、別サーバへ退避してください。**

---

## ステップ1 何が更新できるか調べる

### 更新の有無を見る check-update

**以下の出力は自作の検証リポジトリでの実測です**（RHEL の実機ではありません。作り方は⑥の「手元で練習する」）。
`libfoo` / `libbar` は自分で `rpmbuild` した noarch パッケージで、
`libfoo` に Important、`libbar` に Critical のアドバイザリを付けてあります。

```bash
$ dnf --refresh check-update                # メタデータを取り直してから一覧する
```

```text
libbar.noarch                          1.1-1                           httplocal
libfoo.noarch                          2.0-1                           httplocal
```

> **`--refresh` を付けてください。**
> `metadata_expire` の既定は **48 時間**（`Repo-expire: 172800 second(s)`。実測）なので、
> **公開されたばかりの CVE のアドバイザリが、古いキャッシュには載っていません。**

```bash
$ echo $?                                   # 直前のコマンドの終了ステータスを見る
```

```text
100
```

| 終了ステータス | 意味 |
|:--|:--|
| **`0`** | **更新は無い** |
| **`100`** | **更新がある**（エラーではない） |
| **`1`** | **エラー**（dnf が処理したもの。リポジトリに届かない等） |
| **`3`** | **想定外のエラー** |
| **`200`** | **ロックの取得・解放に失敗**。ただし**既定では待つ**ので通常は出ない（下記） |

（`man 8 dnf` の Return values より）

> **`100` はエラーではありません。**スクリプトで `set -e` を使うと `100` で止まります。
> ただし **`|| true` で済ませると「リポジトリに届かない（`1`）」も成功扱いになり、
> 更新が無いのか調べられなかったのかが区別できません。**

```bash
$ dnf --refresh check-update; rc=$?                      # 終了ステータスを受け取る
$ case $rc in 0) echo なし;; 100) echo あり;; *) echo "失敗 rc=$rc"; exit 1;; esac   # 3つを区別する
```

### セキュリティ更新だけを見る

```bash
$ dnf updateinfo summary                    # アドバイザリの件数を深刻度ごとに数える
```

```text
Updates Information Summary: available
    2 Security notice(s)
        1 Critical Security notice(s)
        1 Important Security notice(s)
```

```bash
$ dnf updateinfo list --available           # 未適用のアドバイザリを一覧する
```

```text
RHSA-2026:0002 Critical/Sec.  libbar-1.1-1.noarch
RHSA-2026:0001 Important/Sec. libfoo-2.0-1.noarch
```

```bash
$ dnf updateinfo info --cve CVE-2026-11111  # CVE 番号から中身を読む
```

```text
  Update ID: RHSA-2026:0001
       Type: security
    Updated: 2026-09-01 00:00:00
       CVEs: CVE-2026-11111
Description: libfoo に任意コード実行の脆弱性があります。
   Severity: Important
```

> **アドバイザリ情報（`updateinfo`）はリポジトリ側に metadata が入っていないと出ません。**
> 自前でミラーした社内リポジトリでは、`reposync --download-metadata` を付け忘れると
> `updateinfo` が空になり、**`--security` を付けても何も選ばれなくなります**。
> 詳しくは [⑤ オフライン環境でのパッケージの集め方](./dnfコマンド⑤_オフライン環境でのパッケージの集め方.md) を参照してください。

**リポジトリに `updateinfo` が入っているかは、こう確認します。**

```bash
$ dnf updateinfo summary                    # 空なら updateinfo が無い可能性が高い
$ curl -s http://repo.example.local/rhel9/baseos/repodata/repomd.xml | grep updateinfo   # metadata の有無を直接見る
```

> **`dnf repolist -v` に `updateinfo` の有無を示す項目はありません。**（dnf 4.14 で確認）
> 上の 2 つで確かめてください。

---

## ステップ2 何を当てるか決める

**ここが脆弱性対応の判断どころです。**目的によって使うオプションが変わります。

> **`dnf upgrade` は下見（`--assumeno`）でも root 権限が必要です。**
> `upgrade` に `root_user = True` が指定されているためで（`dnf` のソースで確認）、非 root では
> `This command has to be run with superuser privileges` で止まります。
> 一方 **`check-update` / `updateinfo` / `repoquery` / `list` は一般ユーザーでも実行できます。**

| やりたいこと | コマンド |
|:--|:--|
| **全部最新にする**（月次パッチ） | `dnf upgrade` |
| **セキュリティ更新だけ** | `dnf upgrade --security` |
| **特定の CVE だけ** | `dnf upgrade --cve CVE-2026-11111` |
| **特定のアドバイザリだけ** | `dnf upgrade --advisory RHSA-2026:0001` |
| **深刻度で絞る** | `dnf upgrade --sec-severity Critical` |
| **セキュリティ修正を含む最小バージョンまで** | `dnf upgrade-minimal --security` |
| **特定パッケージだけ** | `dnf upgrade openssh-server` |

### 実測で違いを確かめる

検証環境のアドバイザリは 2 件です。
**`RHSA-2026:0001` Important（`libfoo` 1.0→2.0 / `CVE-2026-11111`）**と
**`RHSA-2026:0002` Critical（`libbar` 1.0→1.1 / `CVE-2026-22222`）**。

```bash
$ sudo dnf upgrade --security --assumeno                    # セキュリティ更新すべて（下見）
$ sudo dnf upgrade --cve CVE-2026-11111 --assumeno          # CVE を1つだけ指定（下見）
$ sudo dnf upgrade --advisory RHSA-2026:0002 --assumeno     # アドバイザリを指定（下見）
```

**選ばれたパッケージ（`Upgrading:` に出たもの）の実測結果です。**

| 指定 | 選ばれたもの |
|:--|:--|
| `--security` | **`libfoo` 2.0-1 と `libbar` 1.1-1**（2 件） |
| `--cve CVE-2026-11111` | **`libfoo` 2.0-1 のみ**（1 件） |
| `--advisory RHSA-2026:0002` | **`libbar` 1.1-1 のみ**（1 件） |

**「この CVE への対応です」と報告する必要がある場面では、`--cve` か `--advisory` で対象を絞ります。**
余計なパッケージが混ざらないので、影響範囲の説明が楽になります。

### 深刻度の指定には落とし穴がある

**`--sec-severity Important` は Critical を含みません。**
深刻度は「Important 以上」ではなく「**ちょうど Important**」の意味です。

```bash
$ sudo dnf upgrade --sec-severity Important --assumeno      # Important だけを指定する
$ sudo dnf upgrade --sec-severity Critical --assumeno       # Critical だけを指定する
$ sudo dnf upgrade --sec-severity Critical --sec-severity Important --assumeno   # 2回書くと両方が対象になる
```

**実測結果です**（`libfoo` が Important、`libbar` が Critical）。

| 指定 | 選ばれたもの |
|:--|:--|
| `--sec-severity Important` | **`libfoo` のみ**（Critical の `libbar` は**含まれない**） |
| `--sec-severity Critical` | **`libbar` のみ** |
| **2 回書く** | **`libfoo` と `libbar` の両方** |

> **`--sec-severity` は繰り返し指定すると OR になります。**
> 「Critical と Important を当てる」なら**2 回書く**のが正解です。
> **`Important` だけを指定して「重要なものは当てた」と報告しないでください。**
> 日本語の「重要」は Important の訳語になりがちですが、**Critical は含まれていません。**
> 指定できる値は **`Critical` / `Important` / `Moderate` / `Low`** の 4 つです（`dnf --help` より）。

### upgrade と upgrade-minimal

| コマンド | 挙動 |
|:--|:--|
| **`dnf upgrade --security`** | 対象パッケージを**リポジトリにある最新版**まで上げる |
| **`dnf upgrade-minimal --security`** | **アドバイザリを満たす最小のバージョン**まで上げる |

違いが出るのは、たとえば `libfoo` に 1.1（脆弱性修正）と 2.0（新機能入り）の両方がある場合です。
`upgrade` は 2.0 まで、`upgrade-minimal` は 1.1 で止まります。
（アドバイザリが 1.1 を指していて 2.0 も存在する状態で実測して確認しています）

> **バージョンを上げたくない本番では `upgrade-minimal` が効きます。**
> ただし**リポジトリに中間バージョンの rpm が残っていること**が前提です。
> 社内ミラーを `reposync --newest-only` で作っていると中間バージョンの rpm が無く、
> **ダウンロードに失敗するか、最新版が選ばれます**（詳細は⑤の方法4）。

---

## ステップ3 下見する

**`--assumeno` を付けると、トランザクションの中身だけを出して実行しません。**

```bash
$ sudo dnf upgrade --security --assumeno; echo "exit=$?"   # 何が動くかだけを確定させる
```

```text
Upgrading:
 libbar           noarch           1.1-1              httplocal           6.0 k
 libfoo           noarch           2.0-1              httplocal           6.0 k

Transaction Summary
================================================================================
Upgrade  2 Packages

Total download size: 12 k
Operation aborted.
exit=1
```

> **`--assumeno` の終了ステータスは `1` です。**（実測）
> 「中止した」扱いなので、**下見が成功しても `1`** が返ります。
> スクリプトで下見するときは、終了ステータスではなく**出力内容**を見てください。

### 下見で必ず見るところ

| 見出し | 意味 | 注意 |
|:--|:--|:--|
| **`Upgrading`** | バージョンが上がる | 想定どおりか |
| **`Installing`** | **名指しで新規に入る** | パッチ作業では通常出ない。**ただしカーネル更新はここに出る**（下記） |
| **`Installing dependencies`** | **依存として引きずられて新規に入る** | **想定外のものが出たら止める** |
| **`Removing`** | **消える** | **`--allowerasing` を付けていないのに出たら要確認** |
| **`Downgrading`** | 下がる | 通常のパッチ作業では出ないはず |
| **`Skipping packages with broken dependencies`** | **依存が壊れていて飛ばされた**（`best=False` か `--skip-broken` のとき） | **見落とすと「当てたつもりで当たっていない」**。`best=True` では飛ばさずエラーで止まる（下記） |
| **`Skipping packages with conflicts`** | **衝突して飛ばされた** | 同上 |

> **`Removing` と `Skipping` の 2 つは、必ず一覧を読んで確認してください。**
> ここを流すと、当日「入っていたはずのパッケージが消えている」事故になります。
>
> **`Skipping` が出るかどうかは `best` の設定で変わります。**
> `dnf` 本体の既定は `best=False`（`man 5 dnf.conf`）で、この場合は飛ばして先へ進みます。
> **RHEL は `/etc/dnf/dnf.conf` に `best=True` を書いている構成が多く、
> その場合は飛ばさずに `Problem: ...` でエラー停止します**
> （`--allowerasing` / `--skip-broken` / `--nobest` を試せ、というヒントが付きます）。
> `grep best /etc/dnf/dnf.conf` でどちらかを先に確認してください。
>
> **カーネル更新は `Upgrading` ではなく `Installing` / `Install` として出ます。**
> カーネルは `installonlypkgs`（上書きせず並存させるパッケージ）なので、
> `dnf upgrade` でも「新規インストール」として扱われます。
> 検証環境で自作パッケージを `installonlypkgs` に指定して `upgrade` したところ、
> **`Upgrading:` ではなく `Install  1 Package` になりました**（実測）。
>
> 同じ理由で、**`installonly_limit` を超えた旧カーネルが `Removing` に出るのも正常です。**
> **新カーネル以外の `Installing` と、旧カーネル以外の `Removing` を要確認としてください。**

---

## ステップ4 事前に取得しておく

**窓の中でやることを「当てるだけ」にするための下準備です。**
ここには**誤解されがちな落とし穴**があります。

### 窓の前に rpm を落としておく（--downloadonly）

```bash
$ sudo dnf upgrade --security -y --downloadonly   # 適用せずダウンロードだけする
```

```text
Total                                           1.2 MB/s |  12 kB     00:00
Complete!
The downloaded packages were saved in cache until the next successful transaction.
You can remove cached packages by executing 'dnf clean packages'.
```

**窓の中で当てると、ダウンロードが省かれます。**（実測）

```bash
$ sudo dnf upgrade --security -y            # 窓の中で当てる
```

```text
Downloading Packages:
[SKIPPED] libbar-1.1-1.noarch.rpm: Already downloaded
[SKIPPED] libfoo-2.0-1.noarch.rpm: Already downloaded
Complete!
```

`[SKIPPED] ... Already downloaded` が**キャッシュを使い回した証拠**です。

### --destdir を付けると、逆に使われず消える

**ここが落とし穴です。**`--downloadonly` に `--destdir` を足すと、

- **窓の中の `dnf upgrade` では使われません**（再ダウンロードになります）
- **トランザクションが成功した時点で、そのディレクトリの rpm は消えます**

検証環境での実測です。`--destdir` に落ちた 2 つの rpm は、
続く `dnf upgrade --security -y` は**再ダウンロードして適用し、成功後にディレクトリは空になりました。**

```bash
$ sudo dnf upgrade --security -y --downloadonly --destdir=$WORK/rpms   # destdir を指定して取得する
$ ls -1 $WORK/rpms                          # libbar-1.1-1 と libfoo-2.0-1 がある
$ sudo dnf upgrade --security -y            # 当てる（再ダウンロードが走る）
$ ls -1 $WORK/rpms                          # 成功後は何も出ない
```

**`man 8 dnf` にもそう書かれています。**

> Packages are removed after the next successful transaction. This applies also
> when used together with `--destdir` option as the directory is considered as a
> part of the DNF cache. To persist the packages, use the `download` command instead.

| やりたいこと | 使うもの |
|:--|:--|
| **窓の前に落としておき、窓の中で当てる** | **`--downloadonly`（`--destdir` は付けない）** |
| **rpm をファイルとして残す**（手運び・保管・切り戻し用） | **`dnf download --destdir=...`** |

### 切り戻し用に「いま入っている版」を確保する

**`--downloadonly` で落ちるのは新しい版です。切り戻しには使えません。**
戻すのに必要なのは**いま入っている古い版**なので、それを別に取っておきます。

```bash
$ rpm -q libfoo libbar                      # いま入っている版を確認する（libfoo-1.0-1 / libbar-1.0-1）
$ dnf download --destdir=$WORK/rollback libfoo-1.0-1 libbar-1.0-1   # 旧版をファイルとして確保する
$ ls -1 $WORK/rollback                      # 2つの rpm が置かれたことを確認する
```

> **この一手間が、切り戻しの成否を分けます。**
> 社内ミラーを `reposync --newest-only` で作っていると、
> **リポジトリから旧版が消えているため `dnf history undo` が失敗します**（後述）。
>
> **ただし `dnf download` もリポジトリから取ってきます。**
> ミラーを更新してしまって旧版が消えていると `No package ... available.` で失敗します。
> **旧版の確保は、ミラーを更新する前（＝旧版がまだ残っているうち）に行ってください。**
> 間に合わなかった場合は、**前回のパッチ作業で残した rpm** か
> `/var/cache/dnf` に残っているものを探すことになります。
>
> **窓の中でもう一度 `--assumeno` を打ってください。**事前取得から窓までの間に
> リポジトリが更新されると、**対象が変わっている**ことがあります。
> なおキャッシュ済みの状態で下見すると `Total download size:` ではなく
> **`Total size:`** と表示されます（実測）。

---

## ステップ5 当てる

**適用するときは、最初から `--comment` を付けてください。**（後述）

```bash
$ sudo dnf upgrade --security -y --comment "2026-09 月次 CVE-2026-11111 対応 INC-1234"   # メモ付きで適用する
```

```text
Running transaction check
Transaction check succeeded.
Running transaction test
Transaction test succeeded.
Running transaction
  Preparing        :                                                        1/1
  Upgrading        : libfoo-2.0-1.noarch                                    1/4
  Upgrading        : libbar-1.1-1.noarch                                    2/4
  Cleanup          : libfoo-1.0-1.noarch                                    3/4
  Cleanup          : libbar-1.0-1.noarch                                    4/4
  Verifying        : libbar-1.1-1.noarch                                    1/4
（Verifying は4件分続く）

Upgraded:
  libbar-1.1-1.noarch                    libfoo-2.0-1.noarch

Complete!
```

| 行 | 読み方 |
|:--|:--|
| **`Transaction test succeeded`** | **ファイルの衝突やディスク不足が無い**ことを確認できた。ここまでは rpmdb に書いていない |
| **`Upgrading`** | 新しい版を展開している |
| **`Cleanup`** | **古い版を取り除いている**（`Upgrading` と対の後半工程） |
| **`Verifying`** | **結果が rpmdb に反映されたか**の確認。ファイルの改ざん検査ではない（それは `rpm -V`） |

### --comment は history info に残る

```bash
$ dnf history info last                     # 直近のトランザクションを読む
```

```text
Transaction ID : 2
Return-Code    : Success
Command Line   : upgrade --security -y --comment 2026-09 月次 CVE-2026-11111 対応 INC-1234
Comment        : 2026-09 月次 CVE-2026-11111 対応 INC-1234
Packages Altered:
    Upgrade  libbar-1.1-1.noarch @httplocal
    Upgraded libbar-1.0-1.noarch @@System
```

（出力は抜粋です。実際には `Begin time` / `User` / `Releasever` などの行も出ます）

> **`Comment` 行として残ります。**（実測）
> 半年後に「この更新は何だったのか」を追うとき、チケット番号がここにあると追跡が楽になります。

---

## ステップ6 当たったことを確かめる

**確認は「当てた対象と同じ条件」で打ちます。**

```bash
$ dnf check-update --security                # セキュリティ更新が残っていないか
$ echo $?                                    # 終了ステータスを見る
```

```text
0
```

**`0` ＝ 対象の更新は残っていません。**

> **`--security` で当てたのに素の `dnf check-update` で確認しないでください。**
> 通常の更新が残っているので `100` のままになり、**当たったのか分からなくなります。**
> 逆に、`exclude` や `versionlock` で除外されているものは
> **そもそも `check-update` に出てきません**（後述）。
> **`0` になったこと単独を「対応完了」の根拠にしてはいけません。**
> 次の `updateinfo list --all` の `i` と組にして確認してください。

```bash
$ dnf updateinfo list --all                 # 適用済みも含めて一覧する
```

```text
i RHSA-2026:0002 Critical/Sec.  libbar-1.1-1.noarch
i RHSA-2026:0001 Important/Sec. libfoo-2.0-1.noarch
```

> **先頭の `i` が「適用済み」の印です。**（実測）報告書の根拠としてそのまま貼れます。

```bash
$ rpm -qa | sort > after-rpm.txt            # 更新後の一覧を取る
$ diff before-rpm.txt after-rpm.txt         # 何が変わったかを出す
$ systemctl list-units --type=service --state=running > after-services.txt   # 稼働中サービスを取る
$ diff before-services.txt after-services.txt   # 落ちたサービスが無いか見る
$ systemctl --failed                        # 失敗しているユニットを確認する
```

> **`diff` の結果は、そのまま作業報告の証跡に使えます。**

---

## 再起動が要るかを判断する

```bash
$ dnf needs-restarting -r                   # 再起動が必要かを判定する
```

```text
No core libraries or services have been updated since boot-up.
Reboot should not be necessary.
```

**終了ステータスは `0` ＝ 再起動不要、`1` ＝ 再起動が必要です。**

```bash
$ sudo dnf needs-restarting                 # 再起動が要るプロセスを一覧する
$ sudo dnf needs-restarting -s              # 再起動が要るサービス名を出す（これを systemctl restart する）
```

> **`needs-restarting` は `dnf-plugins-core`（RHEL 8 以降）に入っています。**
> RHEL 7 では `yum-utils` の `needs-restarting` コマンドです。
> **一般ユーザーで実行すると自分のプロセスしか見えない可能性があるため、`sudo` を付けてください。**

### カーネル更新のとき

**カーネルは `installonly` パッケージなので、`dnf upgrade` でも古い版を上書きしません。**
新しいカーネルが**別に追加インストール**され、古いカーネルは残ります。

```bash
$ rpm -q kernel                             # 入っているカーネルを全部出す
$ uname -r                                  # いま稼働しているカーネル
$ dnf config-manager --dump | grep -E "installonly_limit|installonlypkgs"   # 何本残す設定かを既定値込みで見る
```

`installonly_limit` の**既定は `3`** で、これを超えると古いものから消えます。

| `installonly_limit` の値 | 挙動 |
|:--|:--|
| **`0`** | **無制限**（古いカーネルが溜まり続け、`/boot` を食い潰す） |
| **`1`** | **明示的に許可されていない**（稼働中カーネルは削除されないため、カーネル更新が複雑になる） |
| **`2` 以上** | その本数まで保持する（**最小は `2`**、既定は `3`） |

（`man 5 dnf.conf` の `installonly_limit` より）

**古いカーネルが残るのは、新カーネルで起動できなかったときに戻れるようにするためです。**
ディスク節約のために本数を削りすぎると、**戻る先が無くなります。**
なお **`grep installonly_limit /etc/dnf/dnf.conf` は未記載なら何も出ません**（＝既定の `3`）。

---

## 切り戻す

### history undo でトランザクション単位で戻す

```bash
$ dnf history list                          # 履歴の ID を確認する
```

```text
ID     | Command line             | Date and time    | Action(s)      | Altered
-------------------------------------------------------------------------------
     2 | upgrade --security -y -- | 2026-09-30 03:02 | Upgrade        |    2
     1 | install libfoo-1.0 libba | 2026-09-30 03:02 | Install        |    4
```

```bash
$ sudo dnf history undo last --assumeno     # 戻したら何が動くか下見する
$ sudo dnf history undo last -y             # 実際に戻す
```

```text
Downgrading:
 libbar           noarch           1.0-1              httplocal           6.0 k
 libfoo           noarch           1.0-1              httplocal           6.0 k

Transaction Summary
================================================================================
Downgrade  2 Packages
```

**`upgrade` の逆なので、`Upgrade` は `Downgrade` として戻ります。**（実測）

| コマンド | 何をするか |
|:--|:--|
| **`dnf history undo <ID>`** | そのトランザクションの**逆**を実行する |
| **`dnf history redo <ID>`** | そのトランザクションを**もう一度**実行する |
| **`dnf history rollback <ID>`** | **指定した ID より後のトランザクションを全部** undo する（指定した ID 自体は残る） |
| **`dnf downgrade <パッケージ>`** | 1 つ前のバージョンに下げる |
| **`dnf downgrade <rpmファイル>`** | **手元に確保した rpm ファイルから戻す**（後述） |

> **`history undo` はパッケージを戻すだけです。**
> 置き換わった設定ファイル（`.rpmnew` / `.rpmsave`）やデータベースのスキーマ変更は**戻りません**。
> **設定やデータが絡む更新では、スナップショットやバックアップを別に用意してください。**

### undo が成立する条件

**`undo` は「古い版の rpm をリポジトリから取れること」が前提です。**
**手元のディレクトリに rpm を置いてあっても、`undo` はそれを見てくれません。**
ファイルから戻す場合は、次に書く `dnf downgrade <rpmファイル>` を使います。

**旧版が入手できないと、こうなります。**（リポジトリを無効にして実測）

```text
Error: The following problems occurred while running a transaction:
  Cannot find rpm nevra "libbar-1.0-1.noarch".
  Cannot find rpm nevra "libfoo-1.0-1.noarch".
```

**社内ミラーを `reposync --newest-only` で作っていると、これが起きます。**
だからステップ4で**旧版を `dnf download` でファイルとして確保しておきます。**

```bash
$ sudo dnf downgrade $WORK/rollback/libfoo-1.0-1.noarch.rpm $WORK/rollback/libbar-1.0-1.noarch.rpm -y   # 確保した rpm から戻す
$ dnf list --installed libfoo libbar        # 戻ったことを確認する
```

```text
libbar.noarch                        1.0-1                         @@commandline
libfoo.noarch                        1.0-1                         @@commandline
```

> **`@@commandline` が「コマンドラインで渡した rpm ファイルから入った」印です。**（実測）

### rollback は範囲に注意

**`rollback` は指定 ID より後の全トランザクションを巻き戻します。**
パッチ適用後に別の作業（設定変更用パッケージの追加など）をしていると**それも消えます**。
**1 回の作業を戻すだけなら `undo` を使ってください。**

---

## 当てたくないものを除外する

### その場かぎりで外す

```bash
$ sudo dnf upgrade --security --exclude=libbar -y   # libbar だけ対象から外す
```

**検証環境では対象が 2 件から 1 件（`libfoo` のみ）に減りました。**（実測）

### 恒久的に外す

```bash
$ grep -n "^exclude" /etc/dnf/dnf.conf /etc/yum.repos.d/*.repo   # いまの除外設定を確認する
```

**`/etc/dnf/dnf.conf` の `[main]` に書くと、すべての `dnf` 操作で除外されます。**
**`.repo` ファイル側に書けば、そのリポジトリだけで除外されます。**

```ini
[main]
exclude=kernel* nginx
```

> **`/etc/yum.repos.d/redhat.repo` は手で編集しないでください。**
> `subscription-manager` が自動生成するファイルで、冒頭に「書き換えても上書きされる」と
> 書かれています。Red Hat の CDN 由来のリポジトリには
> `subscription-manager repo-override` か `/etc/dnf/dnf.conf` 側の `exclude` を使い、
> 自作リポジトリは自分で作った別の `.repo` に書いてください。

> **除外したパッケージは `check-update` に「出てこなくなる」**点に注意してください。
> 検証環境では `dnf check-update --exclude=libfoo` で **`libfoo` の行が消えました**（実測）。
>
> つまり症状はこうなります。
> **`dnf check-update` は「更新なし」なのに、脆弱性スキャナは検出し続ける。**
> 「更新が出続ける」ではありません。**逆です。**
> パッチ作業の前に
> `grep exclude /etc/dnf/dnf.conf /etc/yum.repos.d/*.repo` と `dnf versionlock list` を
> 確認するのを癖にしてください。
>
> **一時的に除外を無視したいときは、外し方が 2 つに分かれます。**（どちらも実測）
>
> | 除外の種類 | 一時的に無視する方法 |
> |:--|:--|
> | **`exclude`**（`dnf.conf` / `.repo`） | **`--disableexcludes=all`** |
> | **`versionlock`** | **`--disableplugin=versionlock`**（`--disableexcludes=all` では**外れません**） |

### バージョンを固定する versionlock

```bash
$ sudo dnf install -y python3-dnf-plugin-versionlock   # プラグインを入れる（未導入なら）
$ sudo dnf versionlock add libfoo           # 現在のバージョンで固定する
```

```text
Adding versionlock on: libfoo-0:1.0-1.*
```

```bash
$ dnf versionlock list                      # 固定されているものを一覧する（libfoo-0:1.0-1.* が出る）
$ sudo dnf versionlock delete libfoo        # 固定を解除する
$ cat /etc/dnf/plugins/versionlock.list     # 固定の実体はこのファイル
```

**固定すると、`upgrade --security` の対象からも `check-update` の一覧からも
`libfoo` が消えます。**（どちらも実測）

| `exclude` と `versionlock` | 違い |
|:--|:--|
| **`exclude`** | **そのパッケージを見なかったことにする**。依存で必要になっても入らない |
| **`versionlock`** | **バージョンを指定の版に縛る**。そのバージョンなら操作できる |

**アプリが特定バージョンに依存しているミドルウェアには `versionlock`、
運用上そもそも触らせたくないものには `exclude`** が使い分けの目安です。
どちらも**脆弱性対応の妨げになる**ので、**一覧を作って定期的に見直してください**。
（`versionlock` の詳しい書式は [② リポジトリとキャッシュの管理](./dnfコマンド②_リポジトリとキャッシュの管理.md) にあります）

---

## 定期実行 dnf-automatic

**`dnf-automatic` は、systemd タイマーで更新の確認・取得・適用を自動実行する仕組みです。**

| ファイル / ユニット | 役割 |
|:--|:--|
| `/etc/dnf/automatic.conf` | 設定ファイル |
| `dnf-automatic.timer` | **`automatic.conf` の設定どおりに動く** |
| `dnf-automatic-notifyonly.timer` | **通知だけ**（取得も適用もしない） |
| `dnf-automatic-download.timer` | **取得まで**（適用しない） |
| `dnf-automatic-install.timer` | **適用まで** |

> **`notifyonly` / `download` / `install` の 3 つは、`automatic.conf` の
> `download_updates` と `apply_updates` より優先されます。**
> `dnf-automatic` はコマンドライン引数（`--installupdates` / `--no-downloadupdates` など）で
> 設定を上書きする作りになっており（`dnf/automatic/main.py` で確認）、
> 各 timer はその引数を渡して起動するためです。
> **`apply_updates = no` と書いてあっても、`install.timer` を有効にすれば適用されます。**
> **どの timer がどの引数を渡すかは `systemctl cat dnf-automatic-install.service` の
> `ExecStart` で実機確認してください**（検証環境に unit ファイルが無く、実測できていません）。

**`[commands]` セクションの主な設定です。**
「**コード上の既定**」は `dnf-4.14.0` の実装（`dnf/automatic/main.py`）、
「**同梱 conf の値**」は配布される `/etc/dnf/automatic.conf` に実際に書かれている値です。
**ファイルに書かれていれば、そちらが効きます。**

| キー | コード上の既定 | 同梱 conf の値 | 取れる値 |
|:--|:--|:--|:--|
| **`upgrade_type`** | `default` | `default` | `default`（全部） / `security`（セキュリティのみ） |
| **`download_updates`** | `no` | **`yes`** | `yes` / `no` |
| **`apply_updates`** | `no` | `no` | `yes` / `no` |
| **`random_sleep`** | `300`（秒） | **`0`** | 整数。**台数が多いときリポジトリへの集中を避ける** |
| **`network_online_timeout`** | `60`（秒） | `60` | ネットワークが繋がるまで待つ上限 |

> **既定値を頭の中の前提にしないでください。**
> `download_updates` はコード上の既定が `no` なのに、同梱 conf には `yes` と書かれています。
> **`/etc/dnf/automatic.conf` を実際に開いて確かめてください。**
> なお「同梱 conf の値」は検証環境（Ubuntu 上の dnf 4.14.0 パッケージ）で確認したものです。
> **RHEL では確認していないため、値が異なる可能性があります。**

**`apply_updates = yes` にすると、`download_updates` は自動的に `yes` になります。**（実装で明示的にそうなっています）

`[emitters]` の `emit_via` で通知先を選びます。取れる値は
**`stdio` / `email` / `motd` / `command` / `command_email`** の 5 つです（`main.py` の `build_emitters` で確認）。

**「セキュリティ更新があればメールで知らせるだけ」の設定例です。**

```ini
[commands]
upgrade_type = security
download_updates = no
apply_updates = no
random_sleep = 300

[emitters]
emit_via = email

[email]
email_from = root@example.com
email_to = ops@example.com
```

```bash
$ sudo dnf install -y dnf-automatic         # 導入する
$ sudo systemctl list-unit-files 'dnf-automatic*'   # 使えるユニット名を確認する
$ sudo systemctl enable --now dnf-automatic.timer   # conf どおりに動かす
$ systemctl list-timers 'dnf-*'             # 次回実行を確認する
$ sudo dnf-automatic /etc/dnf/automatic.conf        # 手動で1回動かして通知を確かめる
```

> **`automatic.conf` の設定どおりに動かしたいなら `dnf-automatic.timer` を使ってください。**
> **`random_sleep` は `--timer` 付きで起動されたときだけ効きます**（`main.py`）。

> **本番サーバで `apply_updates = yes`（や `install.timer`）にするのは慎重に判断してください。**
> 「勝手に上がって、勝手に依存が変わって、朝になったらアプリが動かない」が起こり得ます。
> **まず `notifyonly` で通知だけ受け、適用は人が窓の中で行う**のが安全です。
>
> なお **RHEL 10 の `dnf` が 4 系か 5 系かは、①に書いたとおり断定できていません。**
> 世代が違えば `dnf-automatic` の実装と設定項目も変わる可能性があるため、
> RHEL 10 で使う場合は **`dnf --version`、
> `systemctl list-unit-files 'dnf*automatic*'`、`/etc/dnf/automatic.conf`**
> の 3 つを実機で確認してから設定してください。

---

## よくある失敗と対処

| 症状 | 原因 | 対処 |
|:--|:--|:--|
| **`--security` を付けたのに `No security updates needed, but N updates available`** | リポジトリに `updateinfo` が無い | `dnf updateinfo summary` が空か確認。社内ミラーなら `reposync --download-metadata` で作り直す |
| **`check-update` の `100` でスクリプトが止まる** | `set -e` が `100` をエラーと見なす | 終了ステータスを `0` / `100` / その他で場合分けする（`\|\| true` は `1` も隠すので不可） |
| **古い情報のまま更新される** | メタデータキャッシュが古い（既定 48 時間） | `dnf --refresh upgrade` / `dnf clean metadata` |
| **`Problem: ...` でエラー停止する** | `best=True` で依存を満たせない | `--allowerasing` / `--skip-broken` / `--nobest` の**影響範囲を下見してから**選ぶ。安易に `--nobest` で逃げない |
| **`Skipping packages with broken dependencies`** | `best=False` で依存を満たせず飛ばされた | 飛ばされたパッケージ名を確認する。**当たっていないので放置しない** |
| **`check-update` は「更新なし」なのにスキャナは検出する** | `exclude` / `versionlock` で除外されている | `grep exclude /etc/dnf/dnf.conf /etc/yum.repos.d/*.repo` と `dnf versionlock list`。一時回避は `--disableexcludes=all` と `--disableplugin=versionlock`（用途が違う） |
| **`Error: GPG check FAILED`** | 鍵が未取り込み、または署名が無い | `rpm --import` で鍵を入れる。**`--nogpgcheck` で逃げない** |
| **更新したのに脆弱性スキャンで検出され続ける** | **再起動していない / サービス再起動していない** | `dnf needs-restarting -r` と `-s` で確認して再起動する |
| **`Cannot find rpm nevra "..."`（`history undo` 時）** | リポジトリから旧版が消えている | 事前に `dnf download` で確保した旧版から `dnf downgrade <rpmファイル>` |
| **`Waiting for process with pid N to finish.` で止まったように見える** | 別の `dnf` や PackageKit がロックを持っている | **既定は待つだけ**なので、そのまま待つ。`ps -ef \| grep -E "dnf\|packagekit"` で相手を確認する |
| **`RPMDB already locked by N`（終了ステータス `200`）** | 上記で `exit_on_lock` が有効になっている | 相手の処理が終わってから再実行する |

> **よくあるのが下から 3 つ目です。**
> rpm を入れ替えても、メモリに載っている古いライブラリは動き続けます。
> `needs-restarting` で確認して、**再起動またはサービス再起動まで行って初めて対応完了**です。

---

## 作業チェックリスト

**月次パッチ／脆弱性対応で、上から順に潰していける形にしてあります。**

### 事前（窓の前日まで）

1. 対象サーバからリポジトリに届くことを確認した（`dnf --refresh repolist -v`。`-v` 無しは接続しない）
2. `exclude` と `versionlock` の設定を確認した（`grep exclude ...` / `dnf versionlock list`）
3. `rpm -qa | sort > before-rpm.txt` を取った
4. `uname -r` と稼働中サービスを記録した
5. `dnf --refresh check-update` と `dnf updateinfo summary` で規模を把握した
6. 適用対象を決めた（全部 / `--security` / `--cve` / `--advisory` / `--sec-severity`）
7. `--assumeno` で下見し、`Removing`・`Skipping`・`Problem:` が無いことを確認した
8. `--downloadonly`（`--destdir` **なし**）で rpm をキャッシュに落とした
9. **いま入っている旧版を `dnf download --destdir=...` でファイルとして確保した**
10. 再起動の要否と、業務停止の調整を済ませた

### 当日（窓の中）

11. `dnf history list` で作業前の最新 ID を控えた
12. **窓の中でもう一度 `--assumeno` を打ち、事前の下見と対象が変わっていないことを確認した**
13. `--comment "<チケット番号>"` を付けて適用した
14. `Complete!` と `Upgraded:` の一覧を確認した
15. **当てたのと同じ条件**の `dnf check-update --security`（等）が `0` になったことを確認した
16. `dnf updateinfo list --all` で対象アドバイザリに `i` が付いたことを確認した
17. `dnf needs-restarting -r` で再起動要否を判定した
18. 必要なら再起動し、`uname -r` が新カーネルになったことを確認した

### 事後

19. `rpm -qa | sort > after-rpm.txt` を取り、`diff` を作業報告に添えた
20. `systemctl --failed` が空であることを確認した
21. 稼働中サービスを `diff` で突き合わせ、落ちたものが無いことを確認した
22. アプリケーションの疎通確認を実施した
23. `dnf history list` の ID と `Comment` を作業記録に残した
24. **確保した旧版の rpm を、問題なしと判断できるまで別の場所に退避した**

---

## RHEL 7（yum）との対応

**`yum-3` との対応表は
[⑥ オフライン環境での適用と切り戻し](./dnfコマンド⑥_オフライン環境での適用と切り戻し.md) の
「RHEL 7 での書き方」にまとめてあります。**このノートで使ったコマンドもそこに載っています。

このノート固有の注意だけ挙げます。

> **`--destdir` と `--downloaddir` は `dnf-4` ではどちらも同じオプションの別名です**
> （`dnf --help` に `--destdir DESTDIR, --downloaddir DESTDIR` と出ます。実測）。
> **RHEL 7 の `yum-3` 側は `--downloaddir` だけ**なので、
> `dnf-4` と `yum-3` の両方で動かすスクリプトは `--downloaddir` に寄せると通ります。
> ただし **`dnf-5` では `--downloaddir` が廃止されています**（①参照）ので、
> RHEL 10 系も含めるなら分岐が要ります。
>
> **`needs-restarting` は RHEL 7 では `yum-utils` のコマンド**で、`yum` のサブコマンドではありません。
> **`versionlock` は RHEL 7 では `yum-plugin-versionlock` が要ります。**
>
> RHEL 7 は **2024 年 6 月 30 日に Maintenance Support が終了**しています。
> **ELS 契約が無ければセキュリティ更新そのものが配信されません。**

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — Managing and monitoring security updates (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_and_monitoring_security_updates/index)
- [Red Hat — Automating software updates in RHEL 9](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/assembly_automating-software-updates-in-rhel-9_managing-software-with-the-dnf-tool)
- [DNF — dnf-automatic](https://dnf.readthedocs.io/en/latest/automatic.html)
- [dnf-plugins-core — needs-restarting / versionlock](https://dnf-plugins-core.readthedocs.io/en/latest/)
- [man 8 dnf](https://man7.org/linux/man-pages/man8/dnf.8.html)

---

[← 全体の目次にもどる](../README.md)
