# dnf実践① オンライン環境での更新手順

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **対象サーバ自身がリポジトリに届く環境での、月次パッチ適用と脆弱性対応の通し手順。**記録 → 調べる → 決める → 下見 → 事前取得 → 当てる → 確かめる の 0〜6 を 1 本につなげたもの |

> **このフォルダの dnf ノートは「解説」と「実践」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) | **`dnf` と `yum` の関係**、**`install` / `localinstall` / `update` / `upgrade` の違い**、`distro-sync`、`reinstall`、`downgrade` |
> | 解説 | [dnf解説② 削除系と調査系コマンド](./dnf解説②_削除系と調査系コマンド.md) | **`remove` で何が一緒に消えるか**、`autoremove` / `mark` / `swap`、`list` / `info` / `provides`、`history` での切り戻し |
> | 解説 | [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) | **どのサブコマンドにも付くオプション**、`--nobest` と `--skip-broken` と `--allowerasing` の違い、終了ステータス |
> | 解説 | [dnf解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) | `.repo` の書式、`$releasever` / `$basearch`、GPG 鍵、プロキシ、キャッシュ、AppStream モジュール |
> | 解説 | [dnf解説⑤ 依存関係とセキュリティ更新の調べ方](./dnf解説⑤_依存関係とセキュリティ更新の調べ方.md) | `repoquery` の使い方、アドバイザリと CVE、`repoclosure`、`needs-restarting` |
> | 解説 | [dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md) | **ディストリごとの `yum` / `dnf` 対応**、dnf-4 と dnf-5 の差分、**RHEL 10 で変わったこと** |
> | **実践** | **このノート（dnf実践①）** | **リポジトリに届く**サーバの、月次パッチと脆弱性対応の通し手順 |
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

- [このノートが対象にしている環境](#このノートが対象にしている環境)
- [作業の全体像](#作業の全体像)
- [ステップ0 いまの状態を記録する](#ステップ0-いまの状態を記録する)
- [ステップ1 何が更新できるか調べる](#ステップ1-何が更新できるか調べる)
  - [更新の有無を見る check-update](#更新の有無を見る-check-update)
  - [セキュリティ更新だけを見る](#セキュリティ更新だけを見る)
- [ステップ2 何を当てるか決める](#ステップ2-何を当てるか決める)
  - [実測で違いを確かめる](#実測で違いを確かめる)
  - [深刻度の指定には落とし穴がある](#深刻度の指定には落とし穴がある)
  - [upgrade と upgrade-minimal](#upgrade-と-upgrade-minimal)
- [ステップ3 下見する](#ステップ3-下見する)
  - [下見で必ず見るところ](#下見で必ず見るところ)
- [ステップ4 事前に取得しておく](#ステップ4-事前に取得しておく)
  - [窓の前に rpm を落としておく（--downloadonly）](#窓の前に-rpm-を落としておく--downloadonly)
  - [--destdir を付けると、逆に使われず消える](#--destdir-を付けると逆に使われず消える)
  - [切り戻し用に「いま入っている版」を確保する](#切り戻し用にいま入っている版を確保する)
- [ステップ5 当てる](#ステップ5-当てる)
  - [--comment は history info に残る](#--comment-は-history-info-に残る)
- [ステップ6 当たったことを確かめる](#ステップ6-当たったことを確かめる)
- [再起動が要るかを判断する](#再起動が要るかを判断する)
  - [カーネル更新のとき](#カーネル更新のとき)
- [切り戻しと除外設定は実践②へ](#切り戻しと除外設定は実践②へ)
- [よくある失敗と対処](#よくある失敗と対処)
- [作業チェックリスト](#作業チェックリスト)
  - [事前（窓の前日まで）](#事前窓の前日まで)
  - [当日（窓の中）](#当日窓の中)
  - [事後](#事後)
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
  [ 実践③④の担当 ]  対象サーバ  ×  どこにも届かない（rpm を手運びする）
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
| **`Failed to download metadata` になる** | 設定かネットワークの問題。まず [解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) を見る |
| **そもそも届く経路が無い** | [実践③](./dnf実践③_オフライン環境でのパッケージの集め方.md) の手運び手順へ |

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

**以下の出力は自作の検証リポジトリでの実測です**（RHEL の実機ではありません。作り方は実践④の「手元で練習する」）。
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
> 詳しくは [実践③ オフライン環境でのパッケージの集め方](./dnf実践③_オフライン環境でのパッケージの集め方.md) を参照してください。

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
> **ダウンロードに失敗するか、最新版が選ばれます**（詳細は実践③の方法4）。

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
| **`Skipping packages with broken dependencies`** | **依存が壊れていて飛ばされた**（`best=False` / `--nobest` のとき、または `install` に `--skip-broken` を付けたとき） | **見落とすと「当てたつもりで当たっていない」**。`best=True` では飛ばさずエラーで止まる（下記） |
| **`Skipping packages with conflicts`** | **衝突して飛ばされた** | 同上 |

> **`Removing` と `Skipping` の 2 つは、必ず一覧を読んで確認してください。**
> ここを流すと、当日「入っていたはずのパッケージが消えている」事故になります。
>
> **`Skipping` が出るかどうかは `best` の設定で変わります。**
> **`dnf` 本体の既定は `best=False`**（公式の Configuration Reference に「The default is `False`.」）で、
> この場合は飛ばして先へ進みます。
> **RHEL は `/etc/dnf/dnf.conf` に `best=True` を書いている構成が多く、
> その場合は飛ばさずに `Problem: ...` でエラー停止します**
> （`--allowerasing` / `--skip-broken` / `--nobest` を試せ、というヒントが付きます）。
> `grep -nE '^best' /etc/dnf/dnf.conf` でどちらかを先に確認してください。
>
> **ヒントに出る `--skip-broken` は、`upgrade` では効きません。**
> `dnf5` の公式ドキュメントに
> **「`--skip-broken` was dropped from `upgrade`. It was already a no-op in DNF4,
> kept only for YUM compatibility.」**と書かれています。
> **`upgrade` で先へ進めたいなら `--nobest` 側です**（ただし「飛ばして終了 0」になるので、
> 当たったかどうかは `rpm -q` で必ず確かめてください。解説③）。
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

> **ただしこのキャッシュは、窓まで必ず残るわけではありません。**
> **`keepcache` の既定は `0`（残さない）なので、「次に成功した dnf のトランザクション」でキャッシュの rpm は消えます。**
> **その「次のトランザクション」は、落としたものと無関係な `dnf install` でもかまいません。**実測しました。
>
> ```bash
> $ sudo dnf install libbaz --downloadonly   # 落とす
> $ sudo find /var/cache/dnf -name '*.rpm'   # ある
> $ sudo dnf install -y libfoo               # 無関係なものを入れて成功させる
> $ sudo find /var/cache/dnf -name '*.rpm'   # 消えている
> ```
>
> **公式ドキュメントにも明記されています。**`--downloadonly` の説明は
> **「Packages are removed after the next successful transaction.」**で、
> `keepcache` の既定値は **「The default is `False`.」**です。
>
> **窓まで確実に残す方法は 2 つあります。**
>
> ```bash
> $ sudo dnf upgrade --security -y --downloadonly --setopt=keepcache=1   # 残す設定で落とす
> $ sudo dnf download --resolve --destdir=/var/tmp/patch httpd           # download コマンドで落とす（公式の推奨）
> ```
>
> **公式は `--downloadonly` の項で「To keep the packages, use the `download` command」**と案内しています。
> `download` は `dnf-plugins-core` のコマンドで、**落としたものはキャッシュとして扱われないので消えません。**
> **前日までに落としておく運用では、間に誰かが `dnf` を打つ可能性を考えて、どちらかを必ず使ってください。**

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

## 切り戻しと除外設定は実践②へ

**当てたあとの話**（`history undo` での切り戻し、当てたくないものの除外、`versionlock` での固定、
`dnf-automatic` による定期実行）は、分量が増えたので
[dnf実践② オンライン環境での切り戻しと除外設定](./dnf実践②_オンライン環境での切り戻しと除外設定.md)
に分けました。**窓の中で切り戻しが必要になったら、そちらを開いてください。**

---

## よくある失敗と対処

| 症状 | 原因 | 対処 |
|:--|:--|:--|
| **`--security` を付けたのに `No security updates needed, but N updates available`** | リポジトリに `updateinfo` が無い | `dnf updateinfo summary` が空か確認。社内ミラーなら `reposync --download-metadata` で作り直す |
| **`check-update` の `100` でスクリプトが止まる** | `set -e` が `100` をエラーと見なす | 終了ステータスを `0` / `100` / その他で場合分けする（`\|\| true` は `1` も隠すので不可） |
| **古い情報のまま更新される** | メタデータキャッシュが古い（既定 48 時間） | `dnf --refresh upgrade` / `dnf clean metadata` |
| **`Problem: ...` でエラー停止する** | `best=True` で依存を満たせない | **`upgrade` では `--skip-broken` は効かない**（公式に「dnf-4 では no-op」と明記）。`--allowerasing` / `--nobest` の**影響範囲を `--assumeno` で下見してから**選ぶ。安易に `--nobest` で逃げない |
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
[実践④ オフライン環境での適用と切り戻し](./dnf実践④_オフライン環境での適用と切り戻し.md) の
「RHEL 7 での書き方」にまとめてあります。**このノートで使ったコマンドもそこに載っています。

このノート固有の注意だけ挙げます。

> **`--destdir` と `--downloaddir` は `dnf-4` ではどちらも同じオプションの別名です**
> （`dnf --help` に `--destdir DESTDIR, --downloaddir DESTDIR` と出ます。実測）。
> **RHEL 7 の `yum-3` 側は `--downloaddir` だけ**なので、
> `dnf-4` と `yum-3` の両方で動かすスクリプトは `--downloaddir` に寄せると通ります。
> ただし **`dnf-5` では `--downloaddir` が廃止されています**（解説①参照）ので、
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
- [Red Hat — Managing and monitoring security updates (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/managing_and_monitoring_security_updates/index)
- [Red Hat — Managing and monitoring security updates（**RHEL 10 ではこの章に移動**）](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/risk_reduction_and_recovery_operations/managing-and-monitoring-security-updates)
- [Red Hat — Automating software updates in RHEL 9](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/assembly_automating-software-updates-in-rhel-9_managing-software-with-the-dnf-tool)
- [DNF — dnf-automatic](https://dnf.readthedocs.io/en/latest/automatic.html)
- [dnf-plugins-core — needs-restarting / versionlock](https://dnf-plugins-core.readthedocs.io/en/latest/)
- [man 8 dnf](https://man7.org/linux/man-pages/man8/dnf.8.html)

---

[← 全体の目次にもどる](../README.md)
