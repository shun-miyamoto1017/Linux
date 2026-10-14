# dnf実践② オンライン環境での切り戻しと除外設定

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **窓の中で「戻す」判断をするときに開くノート。**`history undo` が成立する条件を知らないと、戻せると思っていたのに戻せない。`exclude` と `versionlock` は「設定したのに当たらない／設定を外し忘れて当たらない」の両方を起こすので、書式と確認方法を押さえておく |

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
> | 実践 | [dnf実践① オンライン環境での更新手順](./dnf実践①_オンライン環境での更新手順.md) | **リポジトリに届く**サーバの、月次パッチと脆弱性対応の通し手順 |
> | **実践** | **このノート（dnf実践②）** | `history undo` / `rollback`、`exclude`、`versionlock`、`dnf-automatic` |
> | 実践 | [dnf実践③ オフライン環境でのパッケージの集め方](./dnf実践③_オフライン環境でのパッケージの集め方.md) | **社内リポジトリに届く場合と完全分離の場合**で、必要な rpm を集める |
> | 実践 | [dnf実践④ オフライン環境での適用と切り戻し](./dnf実践④_オフライン環境での適用と切り戻し.md) | 集めた rpm を対象サーバに当てて、問題が出たら戻す |
>
> `rpm` コマンド単体の話は [RPMによるパッケージ管理](./RPMによるパッケージ管理.md) です。
> `yum` 時代の書き方との対応は [YUMとDNFによるパッケージ管理](./YUMとDNFによるパッケージ管理.md) にあります。


> **公式ドキュメントの確認日: 2026-10-13。**引用はその時点の記載です。
> URL は末尾の「参考リンク」にあります。**本番作業の前に、対象バージョンのドキュメントで裏を取ってください。**

---

## 目次

- [このノートが引き受けている範囲](#このノートが引き受けている範囲)
- [切り戻す](#切り戻す)
  - [history undo でトランザクション単位で戻す](#history-undo-でトランザクション単位で戻す)
  - [undo が成立する条件](#undo-が成立する条件)
  - [rollback は範囲に注意](#rollback-は範囲に注意)
- [当てたくないものを除外する](#当てたくないものを除外する)
  - [その場かぎりで外す](#その場かぎりで外す)
  - [恒久的に外す](#恒久的に外す)
  - [バージョンを固定する versionlock](#バージョンを固定する-versionlock)
- [定期実行 dnf-automatic](#定期実行-dnf-automatic)
- [参考リンク](#参考リンク)

---

## このノートが引き受けている範囲

**[dnf実践① オンライン環境での更新手順](./dnf実践①_オンライン環境での更新手順.md) の「当てたあと」**を引き受けます。

```text
  実践①  記録 → 調べる → 決める → 下見 → 事前取得 → 当てる → 確かめる
                                                              │
  このノート ────────────────────────────────────────────────┘
            ├ 当てたものを戻す          history undo / rollback / downgrade
            ├ 当てたくないものを外す    exclude / --exclude
            ├ バージョンを固定する      versionlock
            └ 定期実行する              dnf-automatic
```

**窓の中で「戻す」判断をするときは、ここだけを開けば足りるように書いています。**

| やりたいこと | どこを読むか |
|:--|:--|
| **当てた更新を取り消したい** | [切り戻す](#切り戻す) |
| **1 パッケージだけ前の版に戻したい** | [切り戻す](#切り戻す)（`downgrade`） |
| **このパッケージだけ更新対象から外したい** | [当てたくないものを除外する](#当てたくないものを除外する) |
| **版を動かさないよう固定したい** | [バージョンを固定する versionlock](#バージョンを固定する-versionlock) |
| **毎月の適用を自動にしたい** | [定期実行 dnf-automatic](#定期実行-dnf-automatic) |

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
$ cat /etc/dnf/plugins/versionlock.conf     # 設定（locklist でファイルの場所を決める）
$ cat /etc/dnf/plugins/versionlock.list     # 固定の実体（上の locklist が指すファイル）
```

**固定すると、`upgrade --security` の対象からも `check-update` の一覧からも
`libfoo` が消えます。**（どちらも実測）

> **ただし `dnf list` と `dnf repoquery` には効きません。**
> `dnf-plugins-core` の公式ドキュメントに
> **「Note the versionlock plugin does not apply any excludes in non-transactional operations
> like repoquery, list, info, etc.」**と明記されています。
>
> | コマンド | 固定が反映されるか | 作業での意味 |
> |:--|:--|:--|
> | **`dnf check-update`** | **される** | **固定したものは「更新なし」に見える** |
> | **`dnf upgrade` / `install`** | **される** | 固定を超えて上げられない |
> | **`dnf list --showduplicates available`** | **されない** | **新しい版が一覧に出る**（でも上がらない） |
> | **`dnf repoquery` / `dnf info`** | されない | 同上 |
>
> **「一覧に出ているのに上がらない」ときの原因はこれです。**
> **作業前の確認は `dnf versionlock list` で行ってください。**`dnf list` では分かりません。

| `exclude` と `versionlock` | 違い |
|:--|:--|
| **`exclude`** | **そのパッケージを見なかったことにする**。依存で必要になっても入らない |
| **`versionlock`** | **バージョンを指定の版に縛る**。そのバージョンなら操作できる |

**一時的に固定を外して上げたいときは、プラグインを無効にします。**

```bash
$ sudo dnf --disableplugin=versionlock upgrade libfoo   # 固定を無視して上げる
```

**`--disableexcludes=all` では外れません。**`versionlock` は `exclude` とは別のしくみ（プラグイン）で止めているためです（実測）。

**アプリが特定バージョンに依存しているミドルウェアには `versionlock`、
運用上そもそも触らせたくないものには `exclude`** が使い分けの目安です。
どちらも**脆弱性対応の妨げになる**ので、**一覧を作って定期的に見直してください**。
（`versionlock` の詳しい書式は [解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) にあります）

---

## 定期実行 dnf-automatic

**`dnf-automatic` は、systemd タイマーで更新の確認・取得・適用を自動実行する仕組みです。**

設定ファイルは **`/etc/dnf/automatic.conf`** です
（公式：「If no configuration file is passed from the command line, `/etc/dnf/automatic.conf` is used.」）。

**タイマーユニットの一覧は Red Hat の公式ドキュメント（RHEL 9「dnf-automatic パッケージに含まれる systemd
タイマーユニットの概要」表 7.1）に表があります。**以下はその記載をそのまま引いたものです。

| ユニット | 公式の説明 | `automatic.conf` を上書きするか |
|:--|:--|:--|
| **`dnf-automatic.timer`** | **「更新のダウンロードおよび適用時のこのタイマーの動作は、`/etc/dnf/automatic.conf` 設定ファイルの設定により指定されます。」**／**「このタイマーはパッケージをダウンロードしますが、インストールはしません。」** | **「いいえ」** |
| **`dnf-automatic-notifyonly.timer`** | **「リポジトリーデータのみをダウンロードして、リポジトリーキャッシュを最新の状態に保ち、利用可能な更新を通知します。」**／**「このタイマーユニットでは、更新されたパッケージはダウンロードまたはインストールされません。」** | **「はい」** |
| **`dnf-automatic-download.timer`** | **「キャッシュにパッケージをダウンロードし、更新を利用できるようにします。」**／**「このタイマーユニットでは更新パッケージはインストールされません。インストールを実行するには、`dnf update` コマンドを実行する必要があります。」** | **「はい」** |
| **`dnf-automatic-install.timer`** | **「更新したパッケージをダウンロードしてインストールします。」** | **「はい」** |

> **`dnf-automatic.timer` の説明に「ダウンロードはするがインストールはしない」とある**ことに注目してください。
> これは **RHEL が配る `automatic.conf` が `download_updates = yes` / `apply_updates = no` である**ことを示しています
> （検証環境の同梱 conf も同じ値でした）。

> **`notifyonly` / `download` / `install` の 3 つは、`automatic.conf` の
> `download_updates` と `apply_updates` より優先されます。これは公式に明記されています。**
>
> | 出典 | 記載 |
> |:--|:--|
> | **DNF 公式 `dnf-automatic` ドキュメント** | **「The systemd timer unit `dnf-automatic.timer` will behave as the configuration file specifies.」**／**「Some other timer units are provided which override the configuration file with some standard behaviours:」**／`notifyonly` は**「Regardless of the configuration file settings」**／`download_updates` と `apply_updates` の両方に**「Note that the other timer units override this setting.」** |
> | **同梱の `/etc/dnf/automatic.conf` のコメント** | **「Whether updates should be downloaded when they are available, by dnf-automatic.timer. notifyonly.timer, download.timer and install.timer override this setting.」** |
>
> **`apply_updates = no` と書いてあっても、`install.timer` を有効にすれば適用されます。**
> しくみとしては、`dnf-automatic` がコマンドライン引数（`--installupdates` / `--no-downloadupdates` など）で
> 設定を上書きできる作りになっており（`dnf/automatic/main.py` で確認）、各 timer がその引数を渡して起動します。
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
| **`random_sleep`** | `300`（秒） | **`0`** | 整数（秒）。**台数が多いときリポジトリへの集中を避ける**。**DNF 公式ドキュメント（latest）は既定を `0` と記載**しており、`dnf-4.14.0` の実装（`300`）と食い違う。**自分の環境の値は conf を見るのが確実** |
| **`network_online_timeout`** | `60`（秒） | `60` | ネットワークが繋がるまで待つ上限 |

> **既定値を頭の中の前提にしないでください。**
> `download_updates` はコード上の既定が `no` なのに、同梱 conf には `yes` と書かれています。
> `random_sleep` は**コード（4.14.0）が `300`、公式ドキュメント（latest）が `0`、同梱 conf が `0`** と三者が揃っていません。
> **`/etc/dnf/automatic.conf` を実際に開いて確かめてください。**
> なお「同梱 conf の値」は検証環境（Ubuntu 上の dnf 4.14.0 パッケージ）で確認したものです。
> **RHEL では確認していないため、値が異なる可能性があります。**

**`apply_updates = yes` にすると、`download_updates` は自動的に `yes` になります。**（実装で明示的にそうなっています）

`[emitters]` の `emit_via` で通知先を選びます。取れる値は
**`stdio` / `email` / `motd` / `command` / `command_email`** の 5 つです（`main.py` の `build_emitters` で確認。
DNF 公式ドキュメントも同じ 5 つを挙げています）。
**既定値は公式ドキュメントでは `email` / `stdio` / `motd`、同梱 conf のコメントでは `email,stdio`** と記載が揺れています。
**`emit_via` を空にすると何も通知されません**（公式：「If emit_via is None or left blank, no messages will be sent.」）。
**通知を当てにする設定なら、必ず明示的に書いてください。**

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
> なお **RHEL 10 の `dnf` が 4 系か 5 系かは、解説①に書いたとおり断定できていません。**
> 世代が違えば `dnf-automatic` の実装と設定項目も変わる可能性があるため、
> RHEL 10 で使う場合は **`dnf --version`、
> `systemctl list-unit-files 'dnf*automatic*'`、`/etc/dnf/automatic.conf`**
> の 3 つを実機で確認してから設定してください。

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — 第7章 RHEL 9 でのソフトウェア更新の自動化](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/assembly_automating-software-updates-in-rhel-9_managing-software-with-the-dnf-tool)
- [Red Hat — 7.4. dnf-automatic パッケージに含まれる systemd タイマーユニットの概要](https://docs.redhat.com/ja/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/ref_overview-of-the-systemd-timer-units-included-in-the-dnf-automatic-package_assembly_automating-software-updates-in-rhel-9)（**タイマーユニットの表**の出典）
- [Red Hat — 7.2. DNF Automatic 設定ファイル](https://docs.redhat.com/ja/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/con_dnf-automatic-configuration-file_assembly_automating-software-updates-in-rhel-9)
- [Red Hat — 第6章 RHEL でのソフトウェア更新の自動化（RHEL 10）](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_software_with_the_dnf_tool/automating-software-updates-in-rhel)
- [DNF ドキュメント（dnf4）— dnf history](https://dnf.readthedocs.io/en/latest/command_ref.html#history-command-label)
- [DNF ドキュメント（dnf4）— dnf-automatic](https://dnf.readthedocs.io/en/latest/automatic.html)
- [dnf-plugins-core ドキュメント — versionlock](https://dnf-plugins-core.readthedocs.io/en/latest/versionlock.html)（**非トランザクション操作では効かない**の出典）
- [DNF ドキュメント（dnf4）— Command Reference](https://dnf.readthedocs.io/en/latest/command_ref.html)（**終了ステータスと `--disableexcludes`**の出典）

---

[← 全体の目次にもどる](../README.md)
