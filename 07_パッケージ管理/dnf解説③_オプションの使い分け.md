# dnf解説③ オプションの使い分け

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **`--skip-broken` と `--nobest` を取り違えると、脆弱性対応で「当たっていないのに当たったと報告する」事故が起きる。**`check-update` の終了ステータス 100 を知らないと、`set -e` のスクリプトが更新があるだけで落ちる |

> **このフォルダの dnf ノートは「解説」と「実践」に分かれています。**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | 解説 | [dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) | **`dnf` と `yum` の関係**、**`install` / `localinstall` / `update` / `upgrade` の違い**、`distro-sync`、`reinstall`、`downgrade` |
> | 解説 | [dnf解説② 削除系と調査系コマンド](./dnf解説②_削除系と調査系コマンド.md) | **`remove` で何が一緒に消えるか**、`autoremove` / `mark` / `swap`、`list` / `info` / `provides`、`history` での切り戻し |
> | **解説** | **このノート（dnf解説③）** | **どのサブコマンドにも付くオプション**、`--nobest` と `--skip-broken` と `--allowerasing` の違い、終了ステータス |
> | 解説 | [dnf解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) | `.repo` の書式、`$releasever` / `$basearch`、GPG 鍵、プロキシ、キャッシュ、AppStream モジュール |
> | 解説 | [dnf解説⑤ 依存関係とセキュリティ更新の調べ方](./dnf解説⑤_依存関係とセキュリティ更新の調べ方.md) | `repoquery` の使い方、アドバイザリと CVE、`repoclosure`、`needs-restarting` |
> | 解説 | [dnf解説⑥ 環境の見極めとバージョン差分](./dnf解説⑥_環境の見極めとバージョン差分.md) | **ディストリごとの `yum` / `dnf` 対応**、dnf-4 と dnf-5 の差分、**RHEL 10 で変わったこと** |
> | 実践 | [dnf実践① オンライン環境での更新手順](./dnf実践①_オンライン環境での更新手順.md) | **リポジトリに届く**サーバの、月次パッチと脆弱性対応の通し手順 |
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

- [オプションはどこに書いても効く](#オプションはどこに書いても効く)
- [確認の仕方を変える -y と --assumeno](#確認の仕方を変える--y-と---assumeno)
- [対象のリポジトリを絞る](#対象のリポジトリを絞る)
- [対象のパッケージを外す --exclude](#対象のパッケージを外す---exclude)
- [依存が解決できないときの3つのオプション](#依存が解決できないときの3つのオプション)
  - [公式ドキュメントの定義](#公式ドキュメントの定義)
  - [まず結論](#まず結論)
  - [--nobest は「2番目の候補を使う」](#--nobest-は2番目の候補を使う)
  - [--skip-broken は「その要求を任意に落とす」](#--skip-broken-はその要求を任意に落とす)
  - [upgrade の --skip-broken は、そもそも no-op](#upgrade-の---skip-broken-はそもそも-no-op)
  - [--allowerasing は「邪魔なものを消してよい」](#--allowerasing-は邪魔なものを消してよい)
  - [エラーメッセージの読み方](#エラーメッセージの読み方)
- [ダウンロードだけする --downloadonly と --destdir](#ダウンロードだけする---downloadonly-と---destdir)
- [キャッシュの扱いを変える --refresh と -C](#キャッシュの扱いを変える---refresh-と--c)
- [設定を一時的に上書きする --setopt](#設定を一時的に上書きする---setopt)
- [環境を差し替える --installroot と --releasever](#環境を差し替える---installroot-と---releasever)
- [署名とプラグインに関わるもの](#署名とプラグインに関わるもの)
- [出力の量を変える](#出力の量を変える)
- [記録を残す --comment](#記録を残す---comment)
- [アドバイザリで絞る](#アドバイザリで絞る)
- [終了ステータス](#終了ステータス)
- [オプション早見表](#オプション早見表)
- [このノートの検証環境](#このノートの検証環境)
- [参考リンク](#参考リンク)

---

## オプションはどこに書いても効く

**dnf のグローバルオプションは、サブコマンドの前でも後ろでも、パッケージ名の後ろでも効きます。**
実測で確かめました。次の 3 つはどれも同じ動きをします。

```bash
$ sudo dnf -y install libbaz                            # サブコマンドの前
$ sudo dnf install libbaz -y                            # サブコマンドの後ろ
$ sudo dnf install libbaz --assumeyes                   # パッケージ名の後ろ
```

**ただし手順書には「`dnf` の直後」に書いてください。**
`dnf install httpd -y` と書くと、読んだ人が `-y` を見落とします。
**`sudo dnf -y install httpd` のほうが「確認なしで実行する」ことが一目で分かります。**

> 以下は **dnf-4.14.0 の `dnf --help`「General DNF options」の実測**から、
> 業務で使うものを目的別に整理したものです。網羅ではなく「使うもの」を厚く書いています。

---

## 確認の仕方を変える -y と --assumeno

| オプション | 効果 | 終了ステータス |
|:--|:--|:--|
| **`-y`** / `--assumeyes` | **すべて yes と答える** | 成功なら 0 |
| **`--assumeno`** | **すべて no と答える**。**変更内容の下見に最適** | **1**（実測） |
| （何も付けない） | `Is this ok [y/N]:` で止まる | `n` と答えると **1**（実測） |

**本番作業は「`--assumeno` で下見 → 一覧を読む → `-y` で実行」の 2 段**でやります。

```bash
$ sudo dnf upgrade --assumeno         # 何が変わるか一覧だけ見る（変更しない）
$ sudo dnf upgrade -y                 # 一覧に納得したら実行する
```

実測。`--assumeno` の最後は `Operation aborted.` で終わります。

```text
Total download size: 6.0 k
Installed size: 11
Operation aborted.
```

> **`-q` と併用しないでください。**`-q` を付けると一覧が出ず、`Operation aborted.` の 1 行だけになります（後述）。
>
> **`--assumeno` は終了ステータス 1 を返します。**
> `set -e` のスクリプトで下見だけさせたいときは `|| true` で受け止めてください。
> **`--downloadonly` と違い、rpm のダウンロードもしません**（解決結果の表示だけ）。

---

## 対象のリポジトリを絞る

| オプション | 効果 |
|:--|:--|
| **`--enablerepo=ID`** | **そのコマンドの間だけリポジトリを有効にする** |
| **`--disablerepo=ID`** | **そのコマンドの間だけリポジトリを無効にする**（`'*'` で全部） |
| **`--repo=ID`** / `--repoid=ID` | **そのリポジトリだけを使う** |
| **`--repofrompath=ID,パス`** | **設定ファイルを作らずに、その場でリポジトリを足す** |
| **`--disableexcludes=ID`** | **`exclude` を無効にする**。`ID` はリポジトリ ID。**`all`（全部）と `main`（`dnf.conf` の分だけ）も指定できる** |

```bash
$ sudo dnf --enablerepo=epel install htop         # ふだん無効の EPEL を一時的に有効にする
$ sudo dnf --disablerepo=epel upgrade            # EPEL を除いて更新する
$ sudo dnf --repo=rhel-9-baseos-rpms list available   # そのリポジトリだけを見る
```

**`--disablerepo='*' --repo=xxx` はエラーになります。**実測の表示です。

```text
Command line error: argument --repo/--repoid: not allowed with argument --disablerepo
```

**1 つのリポジトリだけを使いたいなら `--repo=xxx` だけ**を書きます。
`--repo` は内部で「ほかを全部無効にする」ところまでやってくれるので、`--disablerepo` は不要です。

> `--repofrompath` の書き方と使いどころは
> [dnf実践④ オフライン環境での適用と切り戻し](./dnf実践④_オフライン環境での適用と切り戻し.md) にあります。

---

## 対象のパッケージを外す --exclude

```bash
$ dnf check-update                               # 全部見る
$ dnf check-update --exclude='kernel*'           # kernel 系を除いて見る
$ sudo dnf upgrade -x 'postgresql*' -x 'httpd*'  # 複数回書ける（-x は --exclude の短縮形）
```

**`--exclude` で外したものは、一覧から消えます。**
検証環境の実測です。`libfoo` と `libbaz` の両方に更新がある状態で `libfoo` を外しました。

```text
（--exclude なし）
libbaz.noarch                          1.1-1                           httplocal
libfoo.noarch                          3.0-1                           httplocal

（--exclude='libfoo*' を付けた）
libbaz.noarch                          1.1-1                           httplocal
```

**ここが落とし穴です。**
「除外したので対象外」という表示は出ません。**黙って消えるだけ**です。
**「`check-update` に出ていないから更新不要」と判断すると、除外設定のせいで見落とします。**

```bash
$ grep -rn '^exclude' /etc/dnf/dnf.conf /etc/yum.repos.d/   # 設定ファイル側の exclude を確かめる
$ dnf check-update --disableexcludes=all                    # exclude を全部無視して見る
```

> **`--disableexcludes=all` と `=main` は、コマンドラインの `-x` も無効にします。**
> **理由は公式ドキュメントに書かれています。**「`--exclude` は `[main]` の `excludepkgs` 設定に追記する」
> （**「the --exclude option appends to the [main] excludepkgs configuration」**）ためで、
> `main` や `all` を指定するとその設定ごと無効になります。実測でも確認しました。
> `-x 'libfoo*' --disableexcludes=all` と書くと、`libfoo` が一覧に戻ってきます。
> **「設定ファイルの exclude だけを外す」つもりで `all` を使うと、自分で書いた `-x` も外れます。**
> リポジトリ設定の `excludepkgs` だけを外したいなら、**リポジトリ ID を書いてください**（`--disableexcludes=epel` など）。
> **`repo` という文字をそのまま書いても何も起きません**（`repo` は「リポジトリ ID を書く場所」というプレースホルダです）。
>
> **`--disableexcludes` は `versionlock` には効きません**（別のしくみで止めているため。実測で確認）。
> `versionlock` を一時的に無効にしたいときは `--disableplugin=versionlock` を使います。
>
> **さらに `versionlock` には公式に明記された落とし穴があります。**
> `dnf-plugins-core` の versionlock の項に
> **「the versionlock plugin does not apply any excludes in non-transactional operations like repoquery, list, info, etc.」**
> と書かれています。**つまり固定したパッケージは `dnf list` や `dnf repoquery` には普通に出てきます。**
> **「`list` に出たから固定できていない」と判断しないでください。**効いているかは `dnf versionlock list` で見ます。
>
> 詳しくは [dnf実践② オンライン環境での切り戻しと除外設定](./dnf実践②_オンライン環境での切り戻しと除外設定.md) に。

---

## 依存が解決できないときの3つのオプション

**ここが dnf でいちばん混乱するところ**です。
`--skip-broken` / `--nobest` / `--allowerasing` は**全部違う問題を解きます**。

### 公式ドキュメントの定義

**まず、公式の文面を押さえます。**（DNF Command Reference / dnf5 の Changes between DNF and DNF5）

| オプション | 公式の記載 |
|:--|:--|
| **`--skip-broken`** | **「Resolve depsolve problems by removing packages that are causing problems from the transaction.」**（＝問題を起こしているパッケージをトランザクションから**外して**解決する）。**`strict` を False にする別名**と書かれている |
| **`--nobest`** | **「Set best option to `False`, so that transactions are not limited to best candidates only.」**（＝`best` を False にして、最良候補だけに縛られないようにする） |
| **`--best`** | **「Specifically during dnf upgrade, which by default skips over updates that can not be installed for dependency reasons」**／**「When running into packages with broken dependencies, DNF will fail giving a reason」** |
| **`--allowerasing`** | **「Allow erasing of installed packages to resolve dependencies.」**（＝依存解決のために導入済みパッケージを消すことを許す） |

**ここから 2 つ読み取れます。**

1. **`--skip-broken` は「外して解決する」オプション**です。**「名指ししたものは外さない」とは書かれていません。**
2. **`upgrade` が依存の壊れた最新版で止まるのは `best` のせい**です（`--best` の説明にそう書いてある）。

**そして dnf-5 の公式ドキュメント「Changes between DNF and DNF5」に、決定的な記載があります。**
`upgrade` の項に、次の 3 点が書かれています（**逐語ではなく要点。原文は出典を参照**）。

| 記載されていること |
|:--|
| **`upgrade` から `--skip-broken` が削除された** |
| **dnf-4 の時点ですでに no-op（何もしない）で、yum 互換のために残していただけ** |
| **パッケージの選び方は `best` / `no-best` で決まる** |

**つまり `upgrade --skip-broken` は効かないのが仕様**です。
**自分の環境でも、前述のとおり実測で同じ結果になることを確認しました。**

### まず結論

| オプション | 解く問題 | 何をするか | 危ないところ |
|:--|:--|:--|:--|
| **`--nobest`** | **最新版の依存が壊れている** | **2 番目の候補（1 つ前の版）を使う** | **妥協した結果で `Complete!` 終了 0** |
| **`--skip-broken`** | **入れられないものが混ざっている** | **その要求を「任意」に落として外す** | **名指ししたものでも外す。何も入らず `Complete!` 終了 0** |
| **`--allowerasing`** | **導入済みのものが邪魔をしている** | **邪魔なものを消してよいことにする** | **何が消えるか選べない** |

**3 つに共通する、いちばん大事な注意から書きます。**

> **`--nobest` も `--skip-broken` も、目的を達成できなくても `Complete!` と出して終了ステータス 0 で終わります。**
> **脆弱性対応でこれを付けると、「当たっていないのに当たったと報告する」事故が起きます。**
> **付けたときは必ず `Skipped:` の行を読み、`rpm -q 名前` で入った版を確かめてください。**

### --nobest は「2番目の候補を使う」

検証環境で、**`libfoo-3.0` が存在しないパッケージを要求している**状態を作りました。
`libfoo-1.0` が入っていて、リポジトリには 1.0 / 2.0 / 3.0 があります。

```bash
$ sudo dnf upgrade libfoo             # best=True なので最新の 3.0 を狙って失敗する
```

```text
Error:
 Problem: cannot install the best update candidate for package libfoo-1.0-1.noarch
  - nothing provides libmissing >= 5.0 needed by libfoo-3.0-1.noarch
(try to add '--skip-broken' to skip uninstallable packages or '--nobest' to use not only best candidate packages)
```

```bash
$ sudo dnf --nobest upgrade libfoo    # 2番目の候補（2.0）で妥協する
```

```text
Upgrading:
 libfoo           noarch           2.0-1              httplocal           6.0 k
Skipping packages with broken dependencies:
 libfoo           noarch           3.0-1              httplocal           6.0 k

Transaction Summary
Upgrade  1 Package
Skip     1 Package

Upgraded:
  libfoo-2.0-1.noarch
Skipped:
  libfoo-3.0-1.noarch
```

**2.0 へ上がり、3.0 は Skipped になりました。**
**修正が 3.0 にしか入っていなければ、これは「当たっていない」ということです。**
`Skipped:` の行が、そのことを教えてくれる唯一の手がかりです。

### --skip-broken は「その要求を任意に落とす」

**`--skip-broken` は「入れられないなら、入れなくていい」と dnf に言うオプション**です。
内部では、要求を `strict=False`（任意）に落としています。

**名指ししたものも、容赦なく外されます。**実測です。
`libfoo` は未導入で、リポジトリの最新は依存が壊れた 3.0 です。

```bash
$ sudo dnf install libfoo --skip-broken   # 入れたいものを名指しして、--skip-broken を付けた
```

```text
 Problem: cannot install the best candidate for the job
  - nothing provides libmissing >= 5.0 needed by libfoo-3.0-1.noarch
Skipping packages with broken dependencies:
 libfoo           noarch           3.0-1              httplocal           6.0 k

Transaction Summary
Skip  1 Package

Nothing to do.
Complete!
```

```bash
$ sudo dnf install libfoo --skip-broken >/dev/null ; echo "exit=$?"   # 終了ステータスを見る
```

```text
exit=0
```

**`libfoo` は 1 つも入っていないのに、`Complete!` で終了ステータス 0 です。**
これが「`--skip-broken` を脆弱性対応で使ってはいけない」理由のすべてです。

**衝突（Conflicts）のときも同じ**です。`libbaz-1.1` が入っている状態で、衝突する `newbaz` を入れようとします。

```bash
$ sudo dnf install newbaz --skip-broken   # 衝突しているので、やはり黙って諦める
```

```text
Skipping packages with conflicts:
(add '--best --allowerasing' to command line to force their upgrade):
 libbaz           noarch           1.0-1              httplocal           6.0 k
 newbaz           noarch           1.0-1              httplocal           6.1 k

Transaction Summary
Skip  2 Packages

Nothing to do.
Complete!
```

**何も変わらず、終了ステータスは 0 です。**

### upgrade の --skip-broken は、そもそも no-op

**`upgrade` に `--skip-broken` を付けても、同じ状況では解決しません。**実測です。

```bash
$ sudo dnf --skip-broken upgrade libfoo   # 期待に反して失敗する
```

```text
Error:
 Problem: cannot install the best update candidate for package libfoo-1.0-1.noarch
  - nothing provides libmissing >= 5.0 needed by libfoo-3.0-1.noarch
(try to add '--nobest' to use not only best candidate packages)
```

**提案の文面が変わっているのが手がかり**です。
`--skip-broken` を付けた状態では、dnf は **`--nobest` だけ**を提案してきます。

**原因は 2 つあり、どちらも公式ドキュメントに書かれています。**

1. **`upgrade` に対する `--skip-broken` は dnf-4 の時点ですでに no-op**（yum 互換のために残しているだけ。dnf5 のドキュメントに明記）
2. **止めているのは `best=True`。**`--best` の説明に「`upgrade` は既定では依存の都合で入らない更新を飛ばすが、`--best` を付けると理由を示して失敗する」と書かれている

**つまり `--skip-broken` は何もせず、`best=True` の制約だけが残って失敗します。**
**`best` を下ろすと通ります。**実測です。

```bash
$ sudo dnf upgrade libfoo --skip-broken --setopt=best=False   # best を下ろすと通る
```

```text
Upgraded:
  libfoo-2.0-1.noarch
Skipped:
  libfoo-3.0-1.noarch
Complete!
```

**結果は `--nobest` を付けたときと同じ**です（`--skip-broken` は効いていないので、`best=False` だけが働いた）。
**つまり `upgrade` の「最新版の依存が壊れている」問題を解くのは、常に `--nobest`（＝ `best=False`）側**です。

> **dnf-5 では `upgrade` から `--skip-broken` が削除されました。**
> dnf-5 では `best` の既定値も `true` に変わっています。
> **dnf-5 に移った手順書で `upgrade --skip-broken` と書いてあったら、そこは `--nobest` に直す必要があります。**

| 状況 | `--skip-broken` | `--nobest` |
|:--|:--|:--|
| **`install` で、入れたいものの依存が壊れている** | **何も入らず終了 0** | **1 つ前の版が入る** |
| **`upgrade` で、最新版の依存が壊れている** | **エラーで止まる（効かない）** | **1 つ前の版まで上がる** |
| **`install` で、複数指定のうち一部が壊れている** | **壊れたものだけ外して、残りは入る** | 壊れたものは 1 つ前の版で入ろうとする |
| **衝突している** | **何も入らず終了 0** | **効かない**（`--allowerasing` が必要） |

**使いどころの整理。**

- **`--skip-broken` が妥当なのは「複数まとめて入れて、入らないものは後で個別に見る」とき**だけです
- **脆弱性対応では、どちらも付けずにエラーを読む**のが正解です。**止まってくれたほうが安全です**

### --allowerasing は「邪魔なものを消してよい」

検証環境で、**`newbaz` が `libbaz` と衝突する（Conflicts）**状態を作りました。
`libbaz` が入っている状態で `newbaz` を入れようとします。

```bash
$ sudo dnf install newbaz             # 衝突で止まる
```

```text
Error:
 Problem: problem with installed package libbaz-1.1-1.noarch
  - package newbaz-1.0-1.noarch conflicts with libbaz provided by libbaz-1.1-1.noarch
  - package newbaz-1.0-1.noarch conflicts with libbaz provided by libbaz-1.0-1.noarch
  - conflicting requests
(try to add '--allowerasing' to command line to replace conflicting packages or '--skip-broken'
 to skip uninstallable packages or '--nobest' to use not only best candidate packages)
```

```bash
$ sudo dnf --allowerasing install newbaz   # 邪魔な libbaz を消してよいことにする
```

```text
Installing:
Removing dependent packages:
  Installing       : newbaz-1.0-1.noarch                                    1/2
  Erasing          : libbaz-1.1-1.noarch                                    2/2

Installed:
  newbaz-1.0-1.noarch
Removed:
  libbaz-1.1-1.noarch
Complete!
```

**`--allowerasing` は「消してよい」と言うだけで、何を消すかは選べません。**
**必ず `--assumeno` を併用して、消えるものの一覧を先に読んでください。**

```bash
$ sudo dnf --allowerasing --assumeno install newbaz   # 消えるものを確認するだけ
```

> **このとき `-q` を付けないでください。** `-q` を付けると一覧が出ず、`Operation aborted.` の 1 行だけになります（後述）。

### エラーメッセージの読み方

**dnf のエラーは、最後の行で「使えそうなオプション」を並べてきます。**
ただし**これは候補の列挙で、効くものだけを示しているわけではありません。**
上で見たとおり、最初に並ぶ `--skip-broken` が効かない場面がいくつもあります。

**判断するのは `Problem:` の中身**です。

| `Problem:` の行 | 意味 | 効くもの |
|:--|:--|:--|
| **`cannot install the best update candidate for package X`**（upgrade） | **X の最新版の依存が壊れている** | **`--nobest`** |
| **`cannot install the best candidate for the job`**（install） | **入れたいものの最新版の依存が壊れている** | **`--nobest`**（`--skip-broken` だと何も入らない） |
| **`nothing provides X needed by Y`** | Y が要求する X がどこにも無い | **`--nobest`**（Y が最新版なら）／リポジトリ設定を見直す |
| **`package A conflicts with B`** | 導入済みと衝突している | **`--allowerasing`**（中身を読んでから） |
| **`conflicting requests`** | **上の conflicts に付随して出る行**。これ単独では原因を示さない | **その上の行を読む** |
| **`Error: Unable to find a match: 名前`** | **そんなパッケージは無い** | 名前を確かめる（`dnf search`） |
| **`Package 名前 available, but not installed.`** | **リポジトリにはあるが未導入** | `upgrade` ではなく **`install`** を使う |

---

## ダウンロードだけする --downloadonly と --destdir

| オプション | 公式の記載 |
|:--|:--|
| **`--downloadonly`** | **「Download the resolved package set without performing any rpm transaction (install/upgrade/erase).」**／**「Packages are removed after the next successful transaction.」** |
| **`--destdir=パス`**（`--downloaddir` は dnf-4 限定の別名） | **「Redirect downloaded packages to provided directory.」**／**「The option has to be used together with the --downloadonly command line option」**（または `download` / `modulesync` / `reposync` / `system-upgrade` と併用） |

**公式ドキュメントは「次のトランザクションが成功したあとに消える」と明記しています。**
**しかも「`--destdir` で指定したディレクトリは DNF のキャッシュの一部として扱われる」**ので、
**`--destdir` を付けても同じように消えます。**

**公式の推奨は「残したいなら `download` コマンドを使え」**です。

```bash
$ sudo dnf install --downloadonly httpd                     # キャッシュに落とすだけ
$ sudo dnf install --downloadonly --destdir=/var/tmp/rpms httpd   # 置き場所を指定する
```

**`--destdir` を付けるかどうかで、落とした rpm のその後が変わります。**
検証環境で実測した違いです。

| | 保存先 | 同じ指定で 2 回目 | 通常の `install` から再利用されるか | いつ消えるか |
|:--|:--|:--|:--|:--|
| **`--downloadonly` だけ** | キャッシュ（`/var/cache/dnf/...`） | 再利用される | **される** | **次に成功したトランザクションの後**（`keepcache=False` が既定） |
| **`--downloadonly --destdir=パス`** | 指定したパス | **再利用される**（`[SKIPPED] Already downloaded`） | **されない**（落とし直す） | **次に成功したトランザクションの後** |

実測で出たメッセージです。

```text
The downloaded packages were saved in cache until the next successful transaction.
You can remove cached packages by executing 'dnf clean packages'.
```

**ここが最大の落とし穴です。`keepcache` の既定値は `False` なので、
落としておいた rpm は「次に dnf のトランザクションが成功した時点」で消えます。**
**無関係なパッケージの `install` でも消えます。**実測しました。

```bash
$ sudo dnf install libbaz --downloadonly       # 落とす
$ find /var/cache/dnf -name '*.rpm'            # ある
$ sudo dnf install libfoo-1.0                  # 無関係なものを入れて成功させる
$ find /var/cache/dnf -name '*.rpm'            # 消えている
```

```text
libbaz-1.1-1.noarch.rpm
（libfoo を入れたあと）
（何も出ない）
```

**`--destdir` に落としたものも、同じタイミングで消えます。**

**だから「窓の前に落としておく」なら、次のどれかにしてください。**

| やり方 | 書き方 | 根拠 |
|:--|:--|:--|
| **`download` コマンドを使う**（公式の推奨） | `sudo dnf download --resolve --destdir=/var/tmp/dl httpd` | **公式の `--downloadonly` の項に「To keep the packages, use the `download` command」とある** |
| **キャッシュを残す設定にする** | `sudo dnf install --downloadonly --setopt=keepcache=1 httpd` | `keepcache` の既定は `False`（公式の Configuration Reference） |
| **落としたら、すぐ別の場所へ退避する** | `sudo dnf install --downloadonly --destdir=/var/tmp/dl httpd` のあと `cp -a /var/tmp/dl /var/tmp/keep` | 上の実測 |

> **`download` は `dnf-plugins-core` のコマンド**です。入っていなければ使えません。
> **`--downloadonly` との違いは「キャッシュとして扱われないので消えない」こと**です。

**`--destdir` は「別のサーバへ持っていく rpm を集める」用途**に使ってください（実践③）。
**その場合も、集めたらすぐ `tar` でまとめる**こと。間に別の `dnf` が走ると空になります。

---

## キャッシュの扱いを変える --refresh と -C

| オプション | 効果 | 使いどころ |
|:--|:--|:--|
| **`--refresh`** | **キャッシュを期限切れ扱いにして、メタデータを取り直す** | **「リポジトリに置いたのに出てこない」とき** |
| **`-C`** / `--cacheonly` | **キャッシュだけで動く。ネットワークを見に行かない**。公式の記載は**「Run entirely from system cache, don't update the cache and use it even in case it is expired.」**（**期限切れでも使う**） | リポジトリが落ちているとき、調査だけしたいとき |

> **公式ドキュメントは「一般ユーザが root のキャッシュ（システムキャッシュ）を読み取り専用で使える」**とも説明しています。
> 一般ユーザのキャッシュより新しいことが多いので、**メタデータの同期を待たずに調べられる**という趣旨です。

```bash
$ sudo dnf --refresh check-update     # メタデータを取り直してから調べる
$ dnf -C check-update                 # ネットワークを見ずにキャッシュだけで調べる
$ dnf -C list installed               # これは -C の有無に関係なく動く（下記）
```

**`-C` はキャッシュが無いと失敗します。**ただし**失敗するのはリポジトリを見るコマンドだけ**です。

| コマンド | キャッシュが無いとき |
|:--|:--|
| **`dnf -C check-update`** / `-C list available` / `-C install` | **`Error: Cache-only enabled but no cache for 'httplocal'`**（終了 1） |
| **`dnf -C list installed`** / `-C info 導入済み` / `rpm -q` | **動く**（リポジトリを見ないため） |

**「`dnf -C list installed` が動いたからキャッシュはある」とは言えません。**
キャッシュの有無を確かめたいなら `dnf -C check-update` を打ってください。

> `metadata_expire` の既定は 48 時間（実測で `Repo-expire : 172800 second(s)`）です。
> **社内リポジトリに rpm を追加した直後は、必ず `--refresh` を付けて確かめてください。**
> キャッシュの詳しい扱いは [dnf解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) に。

---

## 設定を一時的に上書きする --setopt

**`/etc/dnf/dnf.conf` を書き換えずに、そのコマンドだけ設定を変えます。**
書き方が 2 つあります。

| 書き方 | 対象 | 例 |
|:--|:--|:--|
| **`--setopt=キー=値`** | **全体（main セクション）** | `--setopt=best=False` |
| **`--setopt=リポジトリID.キー=値`** | **そのリポジトリだけ** | `--setopt=epel.enabled=0` |

```bash
$ sudo dnf install --setopt=install_weak_deps=False httpd   # 推奨パッケージを入れない
$ sudo dnf upgrade --setopt=best=False                      # 最新版にこだわらない
$ dnf --setopt=httplocal.enabled=0 check-update             # そのリポジトリだけ無効にする
```

リポジトリ単位の指定が効いたことの実測です（唯一のリポジトリを無効にしたのでエラーになる）。

```text
Error: There are no enabled repositories in "/home/claude/dnflab/repos.d".
```

**よく使うキー**（既定値はすべて **DNF 公式の Configuration Reference** の記載）

| キー | 既定値（公式の記載） | 効果 |
|:--|:--|:--|
| **`best`** | **「The default is `False`.」**（公式）。同じページに**「`best` and `skip_if_unavailable` can be overridden by your distribution's configuration」**とあり、**Rocky Linux 9 の公式ドキュメントに載っている `/etc/dnf/dnf.conf` は `best=True`**。**ただし「RHEL が配る設定が `True`」という Red Hat 公式の明記は確認できなかった**ので、`grep -nE '^best' /etc/dnf/dnf.conf` で確かめる。**dnf-5 では本体の既定が `true` に変更された** | 最新版にこだわるか |
| **`install_weak_deps`** | **「Default is `True`.」** | **推奨パッケージ（Recommends）を入れるか** |
| **`clean_requirements_on_remove`** | **「The default is True.」** | **削除時に不要な依存も消すか** |
| **`installonly_limit`** | **`3`** | **カーネルを何世代残すか**。公式に **「The minimal number of installonly packages is 2.」**／**「Value 0 means unlimited number of installonly packages.」**／**「Value 1 is explicitly not allowed since it complicates kernel upgrades」**と記載（実測でも `1` は `value 1 is not allowed` で拒否） |
| **`skip_if_unavailable`** | **「The default is `False`.」** | リポジトリに届かないとき、無視して進むか |
| **`obsoletes`** | **「Default is 'true'.」** | Obsoletes による置き換えを行うか |
| **`metadata_expire`** | **「The default corresponds to 48 hours.」** | メタデータの有効期間 |
| **`timeout`** / **`retries`** | **「Defaults to 30 seconds.」** / **「Default is 10.」** | 通信のタイムアウトと再試行回数 |
| **`keepcache`** | **「The default is `False`.」** | **ダウンロードした rpm を残すか**（前述の落とし穴） |

> **`--setopt=best=True` と `--best` は同じ**です。短い `--best` / `--nobest` で足ります。
> 実測で、`best` が既定（`False`）の環境に `--best` を付けると `install` が `Upgraded` に変わることを確認しました。

---

## 環境を差し替える --installroot と --releasever

| オプション | 効果 |
|:--|:--|
| **`--installroot=パス`** | **そのディレクトリを `/` とみなして動く**。rpmdb もその中を使う |
| **`--releasever=版`** | **`$releasever` の値を上書きする** |

```bash
$ sudo dnf --installroot=/mnt/sysroot --releasever=9 install httpd   # 別のルートに入れる
$ dnf --releasever=9.4 check-update                                 # 9.4 の台で何が出るか見る
```

**`--installroot` は「本番に触らずに依存解決を試す」ための道具**です。
対象サーバの `rpmdb` をコピーしてくれば、**手元で同じ依存解決を再現できます**（実践③）。

> **`--installroot` を使うときは `--releasever` も必ず指定**してください。
> **`dnf` は `$releasever` を「installroot の rpmdb の中で `system-release` を Provides するパッケージ」から求めます**
> （ソースで確認：`dnf/rpm/__init__.py` の `detect_releasever()` が `ts.dbMatch('provides', distroverpkg)` を引き、
> 候補は `dnf/const.py` の `DISTROVERPKG = ('system-release(releasever)', 'system-release', ...)`）。
> **`/etc/redhat-release` というファイルを置いても解決しません。**空のルートではそこに何も入っていないので失敗します。
>
> 失敗の仕方は「エラーで即座に止まる」ではなく、**警告が出たあと `$releasever` が未展開のまま URL に入って 404 になる**という形です。
>
> ```text
> Unable to detect release version (use '--releasever' to specify release version)
> error: Status code: 404 for http://repo.example.com/$releasever/repodata/repomd.xml
> Error: Failed to download metadata for repo 'xxx'
> ```
>
> **`$releasever` という文字列がそのまま URL に出ていたら、`--releasever` の付け忘れです。**
> （対象サーバの rpmdb をコピーして使う場合は、その中に `redhat-release` が入っているので検出できる**可能性があります**。未検証です。）

---

## 署名とプラグインに関わるもの

| オプション | 効果 | 注意 |
|:--|:--|:--|
| **`--nogpgcheck`** | GPG 署名を確認しない | **原則使わない。**使うなら理由を作業記録に残す |
| **`--noplugins`** | **プラグインを全部無効にする** | `versionlock` も無効になる |
| **`--disableplugin=名前`** | **そのプラグインだけ無効にする** | **`--disableplugin=versionlock` が実務でよく要る** |
| **`--enableplugin=名前`** | そのプラグインだけ有効にする | |
| `--nodocs` | **ドキュメントを入れない** | コンテナイメージを小さくするときに使う |
| `--forcearch=アーキ` | アーキテクチャを強制する | クロスアーキの rpm を扱うとき |

```bash
$ sudo dnf --disableplugin=versionlock upgrade httpd   # 固定を一時的に外して上げる
$ sudo dnf --noplugins list installed                  # プラグインの影響を切り分ける
```

---

## 出力の量を変える

| オプション | 効果 |
|:--|:--|
| **`-q`** / `--quiet` | **出力を大幅に減らす。トランザクションの確認用の表も出なくなる**（後述。**下見では付けない**） |
| **`-v`** / `--verbose` | **プラグイン一覧・バージョン・cachedir・メタデータの使用状況・依存解決の経過を出す**。切り分けに使う |
| `-d N` / `--debuglevel=N` | デバッグの詳しさ（0〜10） |
| `-e N` / `--errorlevel=N` | エラー表示の詳しさ |
| `--color=auto\|never\|always` | 色付けの制御。**既定の `auto` は、パイプやリダイレクトのときは色を付けない**ので、`\| tee` なら `never` は不要。**`script` などで端末ごと記録するときに `never`** |
| `-R N` / `--randomwait=N` | **最大 N 分のランダム待ち**。多数のサーバが同時にリポジトリを叩くのを散らす |
| `-4` / `-6` | **名前解決を IPv4 のみ / IPv6 のみにする** |

```bash
$ dnf -q list installed               # スクリプトで使うなら -q
$ dnf -v list installed | head -40    # 効いている設定を確かめたいときは -v
$ sudo dnf upgrade | tee /var/tmp/upgrade.log                  # パイプなら auto のままで色は付かない
```

**`-q` には落とし穴があります。トランザクションの確認用の表も消えます。**
同じ `--assumeno install` を、`-q` の有無で比べた実測です。

```bash
$ sudo dnf --assumeno install libbar       # -q なし
```

```text
Installing:
 libbar           noarch           1.1-1              httplocal           6.0 k
Installing dependencies:
 libbaz           noarch           1.1-1              httplocal           6.1 k

Transaction Summary
================================================================================
Install  2 Packages

Total download size: 12 k
Installed size: 8
Operation aborted.
```

```bash
$ sudo dnf -q --assumeno install libbar    # -q あり
```

```text
Operation aborted.
```

**読みたかった一覧が丸ごと消えます。**
**このノートが勧めている「`--assumeno` で下見する」とは併用しないでください。**

**`-v` が追加で出すのは、次のものです**（実測）。

```text
Loaded plugins: builddep, changelog, config-manager, ...     ← 有効なプラグイン
DNF version: 4.14.0                                          ← バージョン
cachedir: /var/cache/dnf                                     ← キャッシュの場所
User-Agent: constructed: 'libdnf (...)'                      ← リポジトリへ送る UA
repo: using cache for: httplocal                             ← キャッシュを使ったか
httplocal: using metadata from Tue Oct 13 01:36:57 2026.     ← いつのメタデータか
--> Starting dependency resolution                           ← 依存解決の経過
---> Package libbaz.noarch 1.1-1 will be installed
--> Finished dependency resolution
```

> **`-v` は「設定値の一覧」を出すわけではありません。**
> **効いている設定値を見たいなら `dnf config-manager --dump`** を使ってください。
> **`-v` が役に立つのは「キャッシュを使ったのか、取り直したのか」「どのプラグインが効いているか」を見たいとき**です。

---

## 記録を残す --comment

**`dnf history` に自由文のコメントを残せます。**変更管理の番号を書いておくと、あとで突き合わせられます。

```bash
$ sudo dnf -y --comment="CHG-123 / RHSA-2026:0001 対応" upgrade libbaz   # 理由を残して実行する
$ dnf history info last                                                  # 残ったか確認する
```

実測です。**`Comment` 欄に入り、`Command Line` 欄にもそのまま残ります。**

```text
Transaction ID : 2
Return-Code    : Success
Command Line   : ... -y --comment=CHG-123 / RHSA-2026:0001 対応 upgrade libbaz
Comment        : CHG-123 / RHSA-2026:0001 対応
```

> **`dnf history` の一覧（表形式）には Comment 列は出ません。**`history info` で見ます。

**スペースを含めるなら、必ずクォートで囲んでください。**囲まないと次のようになります（実測）。

```bash
$ sudo dnf -y upgrade libbaz --comment=CHG-123 / RHSA-2026:0001 対応   # クォートを忘れた
```

```text
Comment        : CHG-123
```

**`Comment` に入るのは最初の 1 語だけ**で、残り（`/` や `RHSA-2026:0001`）は**パッケージ名として解釈されます**
（`No match for argument: /` などが出ますが、`Complete!` で終わります）。
**`Command Line` 欄は切れずに全部残る**ので、そこを見れば何を打ったかは分かります。

**さらに悪いのは、サブコマンドより前に置いた場合**です。コマンド自体が失敗します。

```text
No such command: /. Please use /usr/bin/dnf --help
```

---

## アドバイザリで絞る

**脆弱性対応で毎回使うもの**です。詳しくは [dnf解説⑤ 依存関係とセキュリティ更新の調べ方](./dnf解説⑤_依存関係とセキュリティ更新の調べ方.md) にまとめています。

| オプション | 効果 |
|:--|:--|
| **`--security`** | **セキュリティ関連のものだけ** |
| **`--bugfix`** | バグ修正のものだけ |
| **`--enhancement`** | 機能追加のものだけ |
| **`--newpackage`** | 新規パッケージのものだけ |
| **`--advisory=ID`** | **指定したアドバイザリ**（`RHSA-2026:0001` など）**に必要なものだけ** |
| **`--cve=ID`** | **指定した CVE に必要なものだけ** |
| **`--sec-severity=重大度`** | `Critical` / `Important` / `Moderate` / `Low` で絞る。**1 つ書くとその重大度だけ**になる。複数欲しければ**複数回書く**（実測） |
| `--bz=ID` | 指定した Bugzilla に必要なものだけ |

---

## 終了ステータス

**スクリプトや監視で判定に使うもの**です。すべて検証環境での実測です。

**まず `dnf` 本体の終了ステータスは、公式コマンドリファレンスに一覧があります。**

| 終了ステータス | 公式の記載 |
|:--|:--|
| **`0`** | **「Operation was successful.」** |
| **`1`** | **「An error occurred, which was handled by dnf.」**（dnf が想定して扱ったエラー） |
| **`3`** | **「An unknown unhandled error occurred during operation.」**（想定外のエラー） |
| **`100`** | **「See check-update」**（`check-update` で更新がある） |
| **`200`** | **「There was a problem with acquiring or releasing of locks.」**（**ロックの取得・解放の問題**） |

**`200` を知っていると切り分けが速くなります。**
`Waiting for process with pid N to finish.` のまま終わったときや、
ほかの `dnf` / `PackageKit` / `dnf-automatic` と競合したときに出ます。

**実際のコマンドごとに整理すると、こうなります。**

| コマンド | 終了ステータス | 意味 | 根拠 |
|:--|:--|:--|:--|
| **`dnf check-update`** | **0** | **更新なし** | 公式＋実測 |
| | **100** | **更新あり** | 公式＋実測 |
| | **1** | **エラー**（リポジトリに届かない等） | 実測 |
| **`dnf install 存在しない名前`** | **1** | `Error: Unable to find a match` | 実測 |
| **`dnf upgrade 未導入の名前`** | **1** | `Error: No packages marked for upgrade.` | 実測 |
| **`dnf install 既に最新`** | **0** | `Nothing to do` でも成功扱い | 実測 |
| **`dnf --assumeno ...`** | **1** | **中止したので 1** | 実測 |
| **対話で `n` と答えた** | **1** | 同上 | 実測 |
| **`dnf install --skip-broken`（全部外された）** | **0** | **`Complete!` でも何も入っていない** | 実測（前述） |
| **`dnf needs-restarting -r`** | **0** | **再起動は不要** | **公式**（`dnf-plugins-core` の needs-restarting の項に「Only report whether a reboot is required (exit code 1) or not (exit code 0).」とある） |
| | **1** | **再起動が必要** | **公式**（同上。検証環境ではカーネル更新ができず再現未実施） |
| **`dnf repoclosure`** | **0** | **依存が閉じている** | プラグインのソースで確認 |
| | **1** | **足りない依存がある** | **足りないときに `dnf.exceptions.Error` を投げる**ため、上の表の `1` になる |

> **`repoclosure` の終了ステータスは公式ドキュメントに記載がありません。**
> `dnf-plugins-core` の `repoclosure.py` が未解決依存を見つけると
> `Repoclosure ended with unresolved dependencies (N) across M packages.` というメッセージで
> `dnf.exceptions.Error` を投げる（＝ dnf が扱うエラー → 終了 `1`）ことをソースで確認しました。

**ここが実務の罠です。**

```bash
$ dnf check-update > /dev/null ; echo "exit=$?"   # 更新があると 100 が返る
```

```text
exit=100
```

**`set -e` を書いたシェルスクリプトの中で `dnf check-update` を素で呼ぶと、更新があるだけでスクリプトが落ちます。**

```bash
$ dnf check-update || true             # 100 で落ちないようにする
```

**「更新の有無」で分岐したいなら、100 を明示的に判定します。**

```bash
#!/bin/bash
# 更新があるかどうかで処理を分ける。check-update は 0=なし / 100=あり / それ以外=エラー。
set -uo pipefail
dnf check-update > /var/tmp/check.txt
rc=$?
case "$rc" in
  0)   echo "更新なし" ;;
  100) echo "更新あり"; cat /var/tmp/check.txt ;;
  *)   echo "dnf でエラー（rc=$rc）" >&2; exit 1 ;;
esac
```

> **`set -e` は書かず、`rc` を自分で見る**のが確実です。
> `set -e` を書く場合は **`rc=0; dnf check-update || rc=$?`** の形にしてください。
> **`rc=0` の初期化を忘れると、`set -u` のもとで「更新なし（終了 0）」のときに `rc: unbound variable` で落ちます。**

---

## オプション早見表

| やりたいこと | 書くもの |
|:--|:--|
| **確認なしで実行する** | `-y` |
| **変更内容だけ見る** | `--assumeno` |
| **ふだん無効のリポジトリを使う** | `--enablerepo=ID` |
| **そのリポジトリだけ見る** | `--repo=ID`（`--disablerepo` は併用不可） |
| **特定のパッケージを外す** | `-x '名前*'` |
| **設定の exclude を無視する** | `--disableexcludes=all` |
| **versionlock を一時的に外す** | `--disableplugin=versionlock` |
| **最新版の依存が壊れている** | `--nobest` |
| **複数まとめて入れて、入らないものは後回しにする** | `--skip-broken`（**脆弱性対応では使わない**） |
| **衝突している導入済みを消してよい** | `--allowerasing`（`--assumeno` で先に確認） |
| **rpm を落とすだけ** | `--downloadonly`（**残したいなら `--setopt=keepcache=1`**） |
| **別サーバへ持っていく rpm を集める** | `--downloadonly --destdir=パス` |
| **メタデータを取り直す** | `--refresh` |
| **ネットワークを見ない** | `-C` |
| **推奨パッケージを入れない** | `--setopt=install_weak_deps=False` |
| **別のルートに入れる** | `--installroot=パス --releasever=版` |
| **端末ごとログに残す** | `script` ＋ `--color=never`（パイプなら既定で色は付かない） |
| **変更管理の番号を残す** | `--comment="..."` |
| **セキュリティ更新だけ** | `--security` |

---

## このノートの検証環境

**このノートに載せた出力は、`rpmbuild` で作った検証用パッケージを使った自前のリポジトリで実際に実行した結果**です。
**構成の詳細（dnf の版・リポジトリ ID・パッケージと依存関係・設定）は
[dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) の「このノートの検証環境」に
まとめてあります。**

**RHEL の実機で取った出力ではありません。**
コマンドの挙動・オプションの有無・エラーメッセージの文面・終了ステータスは実測ですが、
`httpd` や `openssh` を対象にした例の画面そのものは載せていません（実測できていないため）。

---

## 参考リンク

- [DNF ドキュメント（dnf4）— Command Reference](https://dnf.readthedocs.io/en/latest/command_ref.html)（**オプションの定義と終了ステータス**の出典）
- [DNF ドキュメント（dnf4）— Configuration Reference](https://dnf.readthedocs.io/en/latest/conf_ref.html)（**設定の既定値**の出典）
- [DNF5 ドキュメント — Changes between DNF and DNF5](https://dnf5.readthedocs.io/en/latest/changes_from_dnf4.7.html)（**`upgrade --skip-broken` が dnf-4 で no-op だったこと / `best` の既定変更**の出典）
- [dnf-plugins-core ドキュメント — needs-restarting](https://dnf-plugins-core.readthedocs.io/en/latest/needs_restarting.html)（**`-r` の終了ステータス**の出典）
- [dnf-plugins-core ドキュメント — repoclosure](https://dnf-plugins-core.readthedocs.io/en/latest/repoclosure.html)
- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)

---

[← 全体の目次にもどる](../README.md)
