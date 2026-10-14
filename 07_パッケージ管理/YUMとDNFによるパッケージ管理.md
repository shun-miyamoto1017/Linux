# YUMとDNFによるパッケージ管理

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理 |
| **業務での使いどころ** | **セキュリティパッチ適用そのもの**。`yum update` を打つ前に `yum check-update` で影響範囲を出せるかが、本番作業の分かれ目 |

> **このノートは Ping-t の出題範囲（`yum` を中心にした基本）**です。
> **RHEL 8 以降の実務で `dnf` を使うなら、このフォルダの dnf ノートのほうが詳しく書いてあります。**
>
> | 知りたいこと | 読むノート |
> |:--|:--|
> | **`install` / `localinstall` / `update` / `upgrade` の違い** | [dnf解説① 基本とインストール系コマンド](./dnf解説①_基本とインストール系コマンド.md) |
> | **`remove` で何が一緒に消えるか、`list` / `info` / `provides` / `history`** | [dnf解説② 削除系と調査系コマンド](./dnf解説②_削除系と調査系コマンド.md) |
> | **オプションと終了ステータス** | [dnf解説③ オプションの使い分け](./dnf解説③_オプションの使い分け.md) |
> | **`.repo` の書式、GPG、プロキシ、キャッシュ** | [dnf解説④ リポジトリとキャッシュの管理](./dnf解説④_リポジトリとキャッシュの管理.md) |
> | **依存関係とセキュリティ更新の調べ方** | [dnf解説⑤ 依存関係とセキュリティ更新の調べ方](./dnf解説⑤_依存関係とセキュリティ更新の調べ方.md) |
> | **実際の作業手順（オンライン／オフライン）** | [dnf実践① オンライン環境での更新手順](./dnf実践①_オンライン環境での更新手順.md) ほか |
>
> **パッケージファイルそのものを扱う下位ツール**は
> [RPMによるパッケージ管理](./RPMによるパッケージ管理.md) にまとめています。
> パッケージファイル名の読み方や `rpm -q` 系の調査コマンドはそちらです。

---

## 目次

- [YUMツールとは](#yumツールとは)
- [依存関係という問題](#依存関係という問題)
- [yumコマンド](#yumコマンド)
  - [主なサブコマンド](#主なサブコマンド)
  - [よく使うオプション](#よく使うオプション)
- [一つずつ例文で確認する](#一つずつ例文で確認する)
  - [アップデートする](#アップデートする)
  - [インストール済みか調べる](#インストール済みか調べる)
  - [パッケージを探す](#パッケージを探す)
  - [パッケージグループを扱う](#パッケージグループを扱う)
- [結果画面の見方](#結果画面の見方)
- [設定ファイル](#設定ファイル)
  - [yum.conf の主な設定](#yumconf-の主な設定)
  - [リポジトリの設定](#リポジトリの設定)
- [DNFツール](#dnfツール)
- [Zypperツール](#zypperツール)
- [Debian系との対応](#debian系との対応)
- [実務での手順](#実務での手順)
- [参考リンク](#参考リンク)

---

## YUMツールとは

**YUM（Yellowdog Updater Modified）ツールは RPM ツールを拡張したツール群**です。

**インターネット上ないしはメディア上のパッケージ情報のデータベースを使い、
依存関係を調整しながらパッケージ管理を行うことができます。**

**この「パッケージ本体と依存関係の情報が置かれている場所」を リポジトリ と呼びます。**
以降に出てくる `repolist` や `/etc/yum.repos.d/` は、すべてこのリポジトリの設定です。

| | **RPM ツール（`rpm`）** | **YUM ツール（`yum`）** |
|:--|:--|:--|
| **依存関係** | **自分では解決しない** | **自動で解決する** |
| **取得元** | **手元の `.rpm` ファイルだけ** | **リポジトリ**（ネットワークやメディア） |
| 引数 | **パッケージファイル名** | **パッケージ名** |
| 設定ファイル | `/usr/lib/rpm/rpmrc` | **`/etc/yum.conf`** |
| 速度 | 速い（ローカルのみ） | 遅い（ネットワークを見に行く） |
| 調査向きか | **`rpm -q` 系が最速** | 情報は多いが重い |

**日常のインストールと更新は `yum`、調査は `rpm -q`** という使い分けになります。

---

## 依存関係という問題

**依存関係とは、あるパッケージが動作するために別のパッケージを必要とする関係のこと**をいいます。

```text
   httpd を入れたい
     │
     ├─ apr        が必要
     ├─ apr-util   が必要
     │    └─ openldap が必要
     └─ httpd-tools が必要
```

**`rpm -ivh httpd.rpm` だけを打つと、この依存が足りずにエラーになります。**

```text
error: Failed dependencies:
	libapr-1.so.0()(64bit) is needed by httpd-2.4.6-97.el7.x86_64
```

**`yum install httpd` なら、必要なものをリポジトリから集めてまとめて入れてくれます。**
これが YUM が存在する最大の理由です。

---

## yumコマンド

**`yum` コマンドは、インターネット上ないしはメディア上のパッケージ情報のデータベースを使い、
依存関係を調整しながら、パッケージのインストール・アンインストールなどを行えるコマンド**です。

```text
yum [-y] サブコマンド [パッケージ名]
```

### 主なサブコマンド

**`yum` コマンドの書式および主なサブコマンドは以下のとおり**です。

| サブコマンド | 説明 |
|:--|:--|
| **`install パッケージ名`** | **パッケージのインストール** |
| **`update [パッケージ名]`** | **パッケージのアップデート** |
| **`remove パッケージ名`** | **パッケージのアンインストール** |
| **`info [パッケージ名]`** | **パッケージの詳細情報の表示** |
| **`list [パッケージ名]`** | **パッケージの一覧表示（バージョンとインストール済かどうか）** |
| **`search キーワード`** | **指定したキーワードでパッケージの検索** |
| **`check-update [パッケージ名]`** | **アップデート可能なパッケージの表示** |
| **`grouplist`** | **パッケージグループの一覧表示** |
| **`groupinstall グループ`** | **パッケージグループのインストール** |

**そのほかによく使うもの**

| サブコマンド | 説明 |
|:--|:--|
| `provides ファイル名` | **そのファイルを提供するパッケージを探す**（`whatprovides` も同じ） |
| `deplist パッケージ名` | 依存関係を一覧する |
| `history` | 過去に実行した yum の操作履歴を見る |
| `history undo 番号` | 過去の操作を取り消す |
| `clean all` | キャッシュを削除する |
| `repolist` | 有効なリポジトリを一覧する |
| `reinstall パッケージ名` | 同じバージョンを入れ直す |
| `downgrade パッケージ名` | 古いバージョンに戻す |

**存在しないサブコマンドを問う問題がよく出ます。**

| 書き方 | 存在するか |
|:--|:--|
| **`yum update`** | **○** |
| **`yum groupinstall`** | **○**（パッケージ「グループ」のインストール） |
| `yum upgrade-all` | ✕ |
| `yum installgroup` | ✕（`groupinstall` の語順違い） |
| `yum upgrade-install` | ✕ |

**`yum upgrade` は存在します**が、`update` とは微妙に違います（後述）。

### よく使うオプション

| オプション | 意味 |
|:--|:--|
| **`-y`** | **すべての質問に `y`（yes）を自動的に選択する** |
| `-q` | 出力を抑える |
| `-v` | 詳細に表示する |
| **`--enablerepo=リポジトリ名`** | **通常は無効なリポジトリを一時的に有効にする** |
| **`--disablerepo=リポジトリ名`** | **リポジトリを一時的に無効にする** |
| **`--exclude=パッケージ名`** | **指定したパッケージを対象から除く** |
| `--downloadonly` | ダウンロードだけして、インストールしない（**yum 3 ではプラグイン由来**） |
| `--security` | セキュリティ更新だけを対象にする（**yum 3 ではプラグイン由来**。RHEL では要サブスクリプション） |
| `--assumeno` | すべての質問に `no` と答える（影響確認用） |

**`--exclude` は本番運用で重要**です。

```bash
$ sudo yum update --exclude=kernel*   # カーネルだけ除いて更新する（再起動を避けたいとき）
```

---

## 一つずつ例文で確認する

### アップデートする

**パッケージを指定せずに実行した場合は、アップデート可能な全てのパッケージをアップデートします。**

```bash
# yum update                          # アップデート可能な全パッケージを更新する
...（略）
python-kerberos       i686     1.1-6.2.el6      base      21 k
python-lxml           i686     2.2.3-1.1.el6    base     2.0 M
python-netaddr        noarch   0.7.5-4.el6      base     1.0 M
python-nss            i686     0.11-3.el6       base     166 k
xorg-x11-drv-xgi      i686     1.6.0-11.el6     base     123 k

Transaction Summary
================================================================================
Install      34 Package(s)
Upgrade     441 Package(s)

Total download size: 402 M
Is this ok [y/N]:
```

**最後の行では、表示されている内容でアップデートしてよいかどうかというメッセージが
表示されています**（`y` を入力するとアップデート、`N` を入力すると中止）。

**`[y/N]` の大文字が既定値**です。この場合、そのまま `Enter` を押すと**中止**されます。

**`yum` コマンドを実行する際、`-y` オプションを使用すると
すべての質問に `y`（yes）を自動的に選択します。**

```bash
# yum -y update                       # 確認なしで一括更新する（スクリプト用）
```

**本番では `-y` を安易に使わないでください。**
影響範囲を見ずに 441 個のパッケージを更新することになります。

**先に `check-update` で確認**するのが正しい手順です。

```bash
# yum check-update                    # 更新可能なパッケージだけを一覧する（何も変更しない）
```

**補足 … `update` と `upgrade` の違い**

| サブコマンド | 違い |
|:--|:--|
| **`yum update`** | 更新する。**廃止されたパッケージは残す** |
| **`yum upgrade`** | 更新する。**`--obsoletes` が有効**（廃止されたパッケージを置き換える） |

**`dnf` では両者が同じ動作**に統一されました。
`yum` の時代は `update` を使うのが通例です。

### インストール済みか調べる

**パッケージの詳細な情報は必要なく、入っているかどうかだけ知りたい場合は `list`** です。

```bash
# yum list php                        # php が入っているか確認する
Loaded plugins: fastestmirror, refresh-packagekit
Loading mirror speeds from cached hostfile
 * base: mirrors.bluehost.com
 * extras: mirrors.usc.edu
 * updates: mirrors.cat.pdx.edu
Installed Packages
php.i686              5.3.3-3.el6_1.3              installed
```

**`Installed Packages` という見出しの下に出ていれば、インストール済み**です。

**パッケージ名を省略すると、インストール済み、および利用できるパッケージが全て一覧表示されます。**

| 見出し | 意味 |
|:--|:--|
| **`Installed Packages`** | **インストール済み** |
| **`Available Packages`** | **リポジトリにあるが、まだ入っていない** |
| `Updated Packages` | 更新可能 |

**`info` との使い分け**

| サブコマンド | 出るもの |
|:--|:--|
| **`yum list php`** | **バージョンとインストール状態の1行** |
| **`yum info php`** | **説明文・ライセンス・サイズ・URL などの詳細** |

**「詳細な情報は必要ない」なら `list`** が正解です。

**なお `show` は存在しないサブコマンド**です（`apt show` と混同しやすい点です）。

### パッケージを探す

```bash
# yum search nginx                    # キーワードでパッケージを検索する
# yum provides */nginx.conf           # このファイルを提供するパッケージを探す
# yum provides /usr/sbin/httpd        # コマンドの実体がどのパッケージか調べる
```

**`provides` は「コマンドが無い」ときに効きます。**

```text
   -bash: dig: command not found
     ↓
   # yum provides */dig
     → bind-utils パッケージだと分かる
```

### パッケージグループを扱う

**パッケージグループとは、用途ごとにまとめられたパッケージの束**です。

```bash
# yum grouplist                       # パッケージグループの一覧を表示する
# yum groupinstall "Development Tools"   # 開発ツール一式をまとめて入れる
```

**`"Development Tools"` は空白を含むのでクォートが必要**です。

| コマンド | 意味 |
|:--|:--|
| **`yum grouplist`** | グループの一覧 |
| **`yum groupinstall グループ`** | **グループをインストール** |
| `yum groupinfo グループ` | グループに含まれるパッケージを見る |
| `yum groupremove グループ` | グループをアンインストール |

**`installgroup` という語順は存在しません。** 試験の誤答選択肢として頻出です。

---

## 結果画面の見方

**`yum update` の出力は 3 つのブロック**に分かれます。

```text
python-lxml           i686     2.2.3-1.1.el6    base     2.0 M
      │                 │           │            │        │
      │                 │           │            │        └─ ダウンロードサイズ
      │                 │           │            └────────── リポジトリ名
      │                 │           └─────────────────────── バージョン-リリース
      │                 └─────────────────────────────────── アーキテクチャ
      └───────────────────────────────────────────────────── パッケージ名
```

| ブロック | 内容 | 見るところ |
|:--|:--|:--|
| **① 対象一覧** | これから処理するパッケージ | **意図しないものが混ざっていないか** |
| **② Transaction Summary** | **件数の要約** | **`Install` と `Upgrade` の数** |
| **③ 確認プロンプト** | `Is this ok [y/N]:` | **ここで止まる** |

| Transaction Summary の行 | 意味 |
|:--|:--|
| **`Install`** | **新規にインストールされる**（依存で引きずられたもの） |
| **`Upgrade`** | **更新される**（すでに入っているもの） |
| `Remove` | 削除される |
| `Downgrade` | 古い版に戻される |

**`Install` の数に注目してください。**
「更新するだけ」のつもりが、**依存で新しいパッケージが 34 個入る**ことが分かります。
本番作業では、この数が想定どおりかを確認してから `y` を押します。

| `Loaded plugins:` の行 | 意味 |
|:--|:--|
| `fastestmirror` | 最も速いミラーを自動で選ぶプラグイン |
| `refresh-packagekit` | GUI のパッケージ管理と連携するプラグイン |
| `* base:` `* extras:` | **実際に使われているミラーサーバ** |

**ミラーが遅い／落ちているとここで止まります。**
更新が進まないときは、まずこの行を見てください。

---

## 設定ファイル

**YUM ツールの設定ファイルは `/etc/yum.conf`** です。

**`/etc/yum.conf` ファイルではキャッシュやログの保存先などの基本設定を行います。**

```bash
# cat /etc/yum.conf                   # YUM の基本設定ファイルを見る
[main]
cachedir=/var/cache/yum/$basearch/$releasever
keepcache=0
debuglevel=2
logfile=/var/log/yum.log
exactarch=1
obsoletes=1
gpgcheck=1
plugins=1
installonly_limit=5
bugtracker_url=http://bugs.centos.org/set_project.php?project_id=16&ref=http://bugs.centos.org/bug_report_page.php?category=yum
distroverpkg=centos-release
...（略）
```

### yum.conf の主な設定

| 設定項目 | 意味 |
|:--|:--|
| **`cachedir`** | **ダウンロードしたパッケージのキャッシュ先** |
| **`keepcache`** | **インストール後にキャッシュを残すか**（`0` で消す） |
| **`logfile`** | **ログの出力先**（`/var/log/yum.log`） |
| **`gpgcheck`** | **パッケージの署名を検証するか**（`1` で検証。**本番では必ず 1**） |
| `exactarch` | 更新時にアーキテクチャを厳密に一致させるか |
| `obsoletes` | 廃止されたパッケージを置き換えるか |
| `plugins` | プラグインを有効にするか |
| **`installonly_limit`** | **`installonlypkgs` のパッケージを同時に何世代保持するか**（既定はカーネル系） |
| `distroverpkg` | ディストリのバージョンを判定するパッケージ |

**`installonly_limit` は `/boot` が溢れる事故に直結**します。
カーネル更新を繰り返すと古いカーネルが溜まるため、この値で世代数を制御します。

**補足 … 対象は「カーネル」ではなく `installonlypkgs`**

`installonly_limit` が数えているのは **`installonlypkgs` に列挙されたパッケージ**で、
**既定でカーネル系（`kernel` など）がそこに入っている**ため、
結果としてカーネルの世代数を決めることになります。

**稼働中のカーネルも 1 世代として数えます。**
そのため `dnf` の既定値 `3` は「稼働中 1 ＋ 予備 2」という意味です
（値 `1` は稼働中カーネルの保護と衝突するため、明示的に禁止されています）。

### リポジトリの設定

**なお、パッケージの取得元（リポジトリ）は `/etc/yum.repos.d` ディレクトリ内のファイルで設定します。**

**`/etc/yum.conf` との役割分担がここです。**

| ファイル／ディレクトリ | 何を設定するか |
|:--|:--|
| **`/etc/yum.conf`** | **キャッシュ・ログ・署名検証などの基本設定** |
| **`/etc/yum.repos.d/`** | **パッケージの取得元（リポジトリ）** |

**リポジトリ情報を追加するには、`/etc/yum.repos.d` にリポジトリの情報を記述した
拡張子 `.repo` のファイルを配置します。**

```text
# /etc/yum.repos.d/example.repo の例
[example]
name=Example Repository
baseurl=https://repo.example.com/el9/x86_64/
enabled=1
gpgcheck=1
gpgkey=https://repo.example.com/RPM-GPG-KEY-example
```

| 項目 | 意味 |
|:--|:--|
| **`[example]`** | **リポジトリ ID**（`--enablerepo` で指定する名前） |
| `name` | 人間向けの説明 |
| **`baseurl`** | **取得元の URL** |
| **`enabled`** | **既定で有効か**（`0` なら `--enablerepo` で都度有効化） |
| **`gpgcheck`** | **署名を検証するか** |
| `gpgkey` | 署名検証に使う公開鍵の場所 |
| `mirrorlist` | `baseurl` の代わりにミラー一覧の URL を指定する |

**間違えやすいファイル名**

| 書き方 | 正しいか |
|:--|:--|
| **`/etc/yum.conf`** | **○ YUM の設定ファイル** |
| **`/etc/yum.repos.d`** | **○ リポジトリ設定の置き場（ディレクトリ）** |
| `/etc/yum/yum.conf` | ✕ RHEL / CentOS では使われない（上流 yum の既定パス。RHEL 系ビルドでは `/etc/yum.conf` に変更されている） |
| `/etc/yum/sources.list` | ✕ 存在しない |
| **`/etc/apt/sources.list`** | **Debian 系（APT）の設定ファイル**。YUM ではない |

**`sources.list` は Debian 系のもの**です。混同させる選択肢として頻出します。

---

## DNFツール

**DNF ツールは YUM の後継となるパッケージ管理ツール**です。
**Linux ディストリビューションの1つである Fedora では、
Fedora 22 からデフォルトのパッケージ管理ツールになっています。**

**`dnf` コマンドでは、`yum` コマンドとほぼ同じオプションが使用できます。**
**また、リポジトリも yum と同様に `/etc/yum.repos.d` ディレクトリを使用します。**

| | **YUM** | **DNF** |
|:--|:--|:--|
| 初登場 | Yellowdog Linux 由来 | Fedora 18（既定は Fedora 22 から） |
| 依存解決 | 独自実装 | **libsolv**（高速） |
| 設定ファイル | `/etc/yum.conf` | **`/etc/dnf/dnf.conf`** |
| **リポジトリ** | **`/etc/yum.repos.d/`** | **`/etc/yum.repos.d/`**（同じ） |
| コマンド体系 | — | **ほぼ同じ** |

**RHEL 8 以降では `yum` は `dnf` へのシンボリックリンク**になっています。
`yum install` と打っても実際には `dnf` が動きます。

**上の表は「YUM 時代」と「DNF 時代」の対比**です。
**RHEL 8 以降では `/etc/yum.conf` 自体も `/etc/dnf/dnf.conf` へのシンボリックリンク**なので、
**どちらを編集しても同じファイル**を書き換えていることになります。
「yum の設定と dnf の設定が別にある」わけではない点に注意してください。

```bash
$ ls -l /usr/bin/yum                  # RHEL 8 以降での yum の実体を確認する例
lrwxrwxrwx 1 root root 5 … /usr/bin/yum -> dnf-3
```

**`dnf` で変わった点**

| 変更 | 内容 |
|:--|:--|
| `dnf history` | 履歴の取り消しが確実になった |
| `dnf module` | **モジュール**（同じソフトの複数バージョンを切り替える仕組み） |
| `dnf mark` | 手動インストールか依存かの印を変更できる |
| `--setopt` | 設定を一時的に上書きできる |

---

## Zypperツール

**Zypper は openSUSE（SUSE Linux から改名）が採用しているコマンドラインのパッケージ管理ツール**です。
**`apt` コマンドや `yum` コマンドのように、`zypper` コマンドでリポジトリやパッケージの操作を行えます。**

| やること | `zypper` |
|:--|:--|
| インストール | `zypper install パッケージ名`（`zypper in`） |
| 更新 | `zypper update`（`zypper up`） |
| 削除 | `zypper remove パッケージ名`（`zypper rm`） |
| 検索 | `zypper search キーワード`（`zypper se`） |
| リポジトリ一覧 | `zypper repos`（`zypper lr`） |

**扱うパッケージ形式は RPM** です。SUSE 系も RPM 系である点に注意してください。

---

## Debian系との対応

**Debian 系 Linux では、`apt-get` がほぼ同等のコマンドにあたります。**

| やること | **RHEL 系（`yum` / `dnf`）** | **Debian 系（`apt`）** |
|:--|:--|:--|
| **インストール** | `yum install 名前` | `apt install 名前` |
| **更新（一括）** | **`yum update`** | **`apt update` → `apt upgrade`** |
| 削除 | `yum remove 名前` | `apt remove 名前` |
| 検索 | `yum search キーワード` | `apt search キーワード` |
| 情報表示 | `yum info 名前` | `apt show 名前` |
| ファイルの提供元 | `yum provides パス` | `apt-file search パス` |
| **設定ファイル** | **`/etc/yum.conf`** | **`/etc/apt/apt.conf`** |
| **リポジトリ** | **`/etc/yum.repos.d/`** | **`/etc/apt/sources.list`** |

**`update` の意味が正反対なので要注意**です。

```text
   RHEL 系:  yum update   →  パッケージを実際に更新する
   Debian 系: apt update   →  パッケージ「情報」を更新するだけ（本体は変わらない）
                apt upgrade →  こちらが実際の更新
```

**`apt update` のつもりで `yum update` を打つと、本番サーバが更新されます。**
系統をまたいで作業するときは、ここを最も注意してください。

---

## 実務での手順

**セキュリティパッチ適用の標準的な流れ**です。

```bash
# yum check-update                    # ① 更新対象を確認する（何も変更しない）
# yum check-update > /tmp/before.txt  # ② 証跡として残す
# yum update --exclude=kernel*        # ③ カーネルを除いて更新する（再起動を避けたい場合）
                                      #    Is this ok [y/N]: の内容を確認してから y
# yum history                         # ④ 実行した操作を確認する
# needs-restarting -r                 # ⑤ 再起動が必要か判定する（yum-utils）
```

**`yum history undo` で戻せます。**

```bash
# yum history                         # 操作履歴を確認する（ID 番号を控える）
# yum history undo 42                 # ID 42 の操作を取り消す
```

**完全に元に戻る保証はありません**が、
**`rpm` にはこの仕組みが無い**ので、YUM を使う実務上の利点になっています。

**補足 … 本番では `gpgcheck=1` を無効にしないでください**

署名検証に失敗すると、こういうエラーが出ます。

```text
Package xxx.rpm is not signed
```

**`--nogpgcheck` で回避できますが、改ざんされたパッケージを検出できなくなります。**
社内リポジトリなら、まず**リポジトリの GPG 鍵を正しく登録**してください。

**補足 … このノートの実行例について**

`yum` は RHEL 系のコマンドのため、本ノートの `yum` の実行例は
**Ping-t の解説に掲載されている実機出力を引用**しています
（サンドボックスは Ubuntu のため `yum` を実行して確認することができませんでした）。
**サブコマンドやオプションの意味は公式ドキュメントで確認済み**ですが、
**出力の細部は環境やバージョンによって異なる可能性があります。**

---

## 参考リンク

- [man 8 yum（yum 3 の man。man7 の `yum.8.html` は DNF へ転送されるので注意）](https://manpages.ubuntu.com/manpages/xenial/man8/yum.8.html)（**yum プロジェクトの man ページ本文。Red Hat の製品ドキュメントではありません**）
- [man 8 yum（同じ yum 3 の man の別ミラー）](https://dyn.manpages.debian.org/wheezy/yum/yum.8.en.html)
- [man 5 dnf.conf（man7 の `yum.conf.5.html` はこの内容）](https://man7.org/linux/man-pages/man5/yum.conf.5.html)
- [DNF 公式ドキュメント](https://dnf.readthedocs.io/en/latest/)
- [Red Hat: Managing software with the DNF tool](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [openSUSE Zypper ドキュメント](https://en.opensuse.org/SDB:Zypper_manual)

---

[← 全体の目次にもどる](../README.md)
