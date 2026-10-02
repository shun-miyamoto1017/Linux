# dnfコマンド② リポジトリとキャッシュの管理

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **社内リポジトリを向かせる設定はここ。**「dnf が外に出ようとして固まる」「リポジトリが見つからない」の切り分けも、結局この設定ファイルを読むだけで終わる |

> `dnf` 本体の使い方は [dnfコマンド① 基本と主要サブコマンド](./dnfコマンド①_基本と主要サブコマンド.md)、
> 依存関係の調べ方は [dnfコマンド③ 依存関係とセキュリティ更新の調べ方](./dnfコマンド③_依存関係とセキュリティ更新の調べ方.md)、
> **リポジトリに届く環境での通しの更新手順**は [dnfコマンド④ オンライン環境での更新手順](./dnfコマンド④_オンライン環境での更新手順.md)、
> 実際の持ち込み作業は [dnfコマンド⑤ オフライン環境でのパッケージの集め方](./dnfコマンド⑤_オフライン環境でのパッケージの集め方.md) と
> [dnfコマンド⑥ オフライン環境での適用と切り戻し](./dnfコマンド⑥_オフライン環境での適用と切り戻し.md) にあります。

---

## 目次

- [リポジトリとは何か](#リポジトリとは何か)
- [設定ファイルの置き場所](#設定ファイルの置き場所)
- [dnf.conf の主な設定](#dnfconf-の主な設定)
- [repo ファイルの書式](#repo-ファイルの書式)
- [変数 releasever と basearch](#変数-releasever-と-basearch)
- [リポジトリの一覧と状態](#リポジトリの一覧と状態)
- [有効と無効を切り替える](#有効と無効を切り替える)
- [その場だけリポジトリを足す repofrompath](#その場だけリポジトリを足す-repofrompath)
- [GPG 署名の扱い](#gpg-署名の扱い)
- [プロキシの設定](#プロキシの設定)
- [キャッシュの管理](#キャッシュの管理)
- [バージョンを固定する versionlock](#バージョンを固定する-versionlock)
- [AppStream モジュール](#appstream-モジュール)
- [Satellite 配下のサーバ](#satellite-配下のサーバ)
- [切り分けの手順](#切り分けの手順)
- [参考リンク](#参考リンク)

---

## リポジトリとは何か

**パッケージ本体（`.rpm`）と、その依存情報をまとめたメタデータが置かれた場所**です。

```text
  リポジトリのディレクトリ
    ├─ appx-1.0-1.noarch.rpm          ← パッケージ本体
    ├─ libfoo-2.0-1.noarch.rpm
    └─ repodata/                       ← メタデータ（これが無いとリポジトリとして使えない）
         ├─ repomd.xml                 ← 目次にあたるファイル。dnf は最初にこれを読む
         ├─ ○○-primary.xml.gz         ← パッケージ名・バージョン・依存関係
         ├─ ○○-filelists.xml.gz       ← どのファイルが入っているか
         ├─ ○○-other.xml.gz           ← 変更履歴
         └─ ○○-updateinfo.xml.gz      ← アドバイザリ（セキュリティ情報）
```

**`dnf` は必ず `repodata/repomd.xml` を最初に取りに行きます。**
「リポジトリが見つからない」というエラーの大半は、この 1 ファイルに届いていないだけです。

```bash
$ curl -sI http://repo.example.local/rhel9/baseos/repodata/repomd.xml   # 届くか確かめる
```

> **`repodata/` が無いディレクトリはリポジトリではありません。**
> RPM を集めただけのディレクトリをリポジトリにするには `createrepo_c` が要ります（⑤）。

---

## 設定ファイルの置き場所

| パス | 役割 |
|:--|:--|
| **`/etc/dnf/dnf.conf`** | **dnf 全体の設定**。RHEL 8 以降はここ |
| `/etc/yum.conf` | **`/etc/dnf/dnf.conf` へのシンボリックリンク**（RHEL 8 以降） |
| **`/etc/yum.repos.d/*.repo`** | **リポジトリごとの設定**。ファイル名は自由、拡張子は `.repo` |
| `/etc/dnf/vars/` | 独自の変数を定義する |
| `/etc/dnf/plugins/` | プラグインの設定 |
| `/var/cache/dnf/` | **メタデータとパッケージのキャッシュ** |
| `/var/log/dnf.log` / `/var/log/dnf.rpm.log` | ログ |

```bash
$ ls -l /etc/yum.conf                 # dnf.conf へのリンクになっているか確かめる
$ ls /etc/yum.repos.d/                # どんなリポジトリ設定があるか
$ grep -r "^baseurl\|^mirrorlist\|^metalink" /etc/yum.repos.d/   # 実際の向き先を一覧する
```

---

## dnf.conf の主な設定

`/etc/dnf/dnf.conf` の `[main]` セクションに書きます。

| 設定 | 意味 | 業務での使いどころ |
|:--|:--|:--|
| **`gpgcheck`** | **GPG 署名を確認するか**（`1` で確認） | **本番は必ず `1`** |
| **`installonly_limit`** | **カーネルを何世代残すか**（既定 `3`） | 戻せる世代を確保する |
| **`clean_requirements_on_remove`** | **削除時に、不要になった依存も消すか** | 既定 `True` |
| **`best`** | 最新版にこだわるか | `False` にすると部分更新が通りやすくなる |
| **`skip_if_unavailable`** | **リポジトリに届かないとき、無視して続行するか** | **本番は `False` 推奨**。黙って古い情報で動かれると危険 |
| **`install_weak_deps`** | **推奨パッケージ（Recommends）を入れるか** | **最小構成にしたいなら `False`** |
| **`keepcache`** | **ダウンロードした rpm を残すか**（既定 `0`） | **`1` にすると `/var/cache/dnf` に残る**（⑤で使える） |
| **`exclude`** | **更新対象から外すパッケージ** | **カーネルを固定したいときなど** |
| **`proxy`** | プロキシの URL | 社内環境 |
| **`reposdir`** | repo ファイルを探す場所 | 既定は `/etc/yum.repos.d` |
| **`cachedir`** | キャッシュの場所 | |
| **`max_parallel_downloads`** | 並列ダウンロード数 | |
| `metadata_expire` | メタデータの有効期限 | |
| `tsflags` | rpm に渡すフラグ（`nodocs` など） | |

**一時的に上書きするには `--setopt`**を使います。設定ファイルを書き換えずに済みます。

```bash
$ sudo dnf install --setopt=install_weak_deps=False -y httpd   # 推奨パッケージを入れない
$ sudo dnf upgrade --setopt=keepcache=1 -y                     # 今回だけ rpm を残す
$ dnf repoquery --setopt=local.gpgcheck=0 libfoo               # リポジトリ別の設定も上書きできる
```

**`--setopt` はリポジトリ単位でも書けます。** `リポジトリID.設定名=値` の形です。

> **`exclude` は強力ですが、忘れると「なぜか更新されない」の原因になります。**
> 設定したら、手順書とサーバの台帳の両方に残してください。

---

## repo ファイルの書式

`/etc/yum.repos.d/内部.repo` の例です。

```ini
[internal-baseos]
name=Internal BaseOS for RHEL $releasever
baseurl=http://repo.example.local/rhel/$releasever/baseos/$basearch/os/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
sslverify=1
skip_if_unavailable=False
```

| 項目 | 意味 |
|:--|:--|
| **`[ID]`** | **リポジトリ ID**。`--enablerepo` などで指定する名前。**角括弧の中** |
| **`name`** | 人が読むための説明。`dnf repolist` に出る |
| **`baseurl`** | **リポジトリの URL**。`http://` `https://` `ftp://` **`file://`** が使える |
| **`mirrorlist`** / **`metalink`** | ミラー一覧の URL。**社内リポジトリでは普通使わない** |
| **`enabled`** | **`1` で有効、`0` で無効** |
| **`gpgcheck`** | **`1` で署名を確認する** |
| **`gpgkey`** | **公開鍵の場所**。`file://` でローカルのファイルも指定できる |
| **`priority`** | **優先度。数字が小さいほうが優先**（既定 `99`）。dnf-4 は本体の機能なので追加パッケージは不要 |
| **`module_hotfixes`** | モジュール由来でないパッケージを許すか |
| **`proxy`** | このリポジトリだけのプロキシ |
| **`sslverify`** | 証明書を検証するか |
| **`exclude`** / **`includepkgs`** | このリポジトリから除外する / このリポジトリからだけ使う |

**`baseurl` は複数行書けます。** 1 つ目が落ちたら次を試します。

```ini
baseurl=http://repo1.example.local/rhel9/baseos/
        http://repo2.example.local/rhel9/baseos/
```

**ローカルディレクトリをリポジトリにするなら `file://`** を使います。

```ini
[patch-20260929]
name=patch set 2026-09-29
baseurl=file:///var/tmp/patch-20260929
enabled=0
gpgcheck=1
```

> **`enabled=0` にしておいて、使うときだけ `--enablerepo` で呼び出す**のが安全です。
> 常時有効にしておくと、関係のない `dnf` 実行でもそのリポジトリを見に行きます。

---

## 変数 releasever と basearch

**repo ファイルの中の `$releasever` と `$basearch` は dnf が自動で置き換えます。**

| 変数 | 中身 | 確かめ方 |
|:--|:--|:--|
| **`$releasever`** | **OS のメジャーバージョン**（RHEL 9 なら `9`） | **`dnf config-manager --dump-variables`**（dnf-4） |
| **`$basearch`** | **アーキテクチャ**（`x86_64` / `aarch64`） | `uname -m` |
| `$arch` | より細かいアーキテクチャ | |

```bash
$ dnf config-manager --dump-variables   # 実際の展開値を見る（dnf-4。dnf-5 は dnf --dump-variables）
$ uname -m                              # アーキテクチャを見る
```

**`--releasever` で一時的に上書きできます。**
「RHEL 8 用の rpm を RHEL 9 のマシンで集めたい」ようなときに使います。

```bash
$ dnf --releasever=8 repoquery sudo   # releasever を 8 として問い合わせる
```

**`/etc/dnf/vars/` にファイルを置くと独自の変数を作れます。**
ファイル名が変数名、中身が値になります。

```bash
$ echo "tokyo" | sudo tee /etc/dnf/vars/site   # $site という変数が使えるようになる
```

---

## リポジトリの一覧と状態

```bash
$ dnf repolist                        # 有効なリポジトリの一覧
$ dnf repolist --all                  # 無効なものも含めて全部
$ dnf repolist --disabled             # 無効なものだけ
$ dnf repolist -v                     # 詳しく（URL、パッケージ数、更新時刻）
```

検証環境での `dnf repolist` の実測です。

```text
repo id                               repo name
local                                 local test repo
```

**`repo id` の列が `--enablerepo` などで指定する名前**です。`repo name` ではありません。ここを取り違えるとリポジトリが見つかりません。

---

## 有効と無効を切り替える

### そのコマンドの間だけ

```bash
$ sudo dnf install --enablerepo=patch-20260929 -y sudo   # このコマンドの間だけ有効にする
$ sudo dnf upgrade --disablerepo=epel -y                 # このコマンドの間だけ epel を止める
$ dnf repoquery --repo=internal-baseos sudo              # このリポジトリだけを使う
```

| 書き方 | 意味 |
|:--|:--|
| **`--enablerepo=ID`** | **無効なリポジトリを一時的に有効にする** |
| **`--disablerepo=ID`** | **有効なリポジトリを一時的に無効にする**。`'*'` で全部 |
| **`--repo=ID`** | **そのリポジトリ「だけ」を使う**。`--disablerepo` とは併用できない |

**カンマ区切りとグロブが使えます。**

```bash
$ dnf repoquery --disablerepo='*' --enablerepo='internal-*' sudo   # 社内リポジトリだけを見る
```

### 設定として永続化する

**`dnf config-manager`**（`dnf-plugins-core` が必要）を使います。

```bash
$ sudo dnf config-manager --set-enabled patch-20260929    # 有効にして設定ファイルに書く
$ sudo dnf config-manager --set-disabled epel             # 無効にして設定ファイルに書く
$ sudo dnf config-manager --add-repo http://repo.example.local/rhel9/baseos/   # repo を追加する
$ sudo dnf config-manager --setopt=epel.priority=10 --save                     # 設定値を書き換える
```

> **dnf-5 では `config-manager` がサブコマンド形式に変わりました。**
>
> | dnf-4 | dnf-5 |
> |:--|:--|
> | `--add-repo URL` | **`addrepo --from-repofile=URL`** など |
> | `--set-enabled ID` | **`enable ID`** |
> | `--set-disabled ID` | **`disable ID`** |
> | `--setopt=... --save` | **`setopt ...`** |
>
> また dnf-5 の `config-manager` は**既存の repo ファイルを書き換えず**、
> `99-config_manager.repo` という drop-in ファイルに書きます。

---

## その場だけリポジトリを足す repofrompath

**設定ファイルを一切作らずに、コマンドラインでリポジトリを追加できます。**
持ち込んだ RPM のディレクトリを使うときに便利です。

```bash
$ sudo dnf --repofrompath=patch,file:///var/tmp/patch --repo=patch -y upgrade sudo   # その場で足して使う（新規なら install）
```

**書式は `--repofrompath=ID,URLまたはパス`** です。ID と場所をカンマで区切ります。

検証環境での実測です。ローカルディレクトリをリポジトリ化して、そこからだけインストールしています。

```text
Installing:
Installing dependencies:
Install  4 Packages
Installed:
Complete!
```

> **`--repofrompath` で足したリポジトリは、既定で `gpgcheck` が有効**です。
> 署名が無い RPM を扱うときは `--setopt=ID.gpgcheck=0` を併記します（**本番では鍵を入れるほうが正解**）。

---

## GPG 署名の扱い

**パッケージが改ざんされていないかを確かめる仕組み**です。脆弱性対応で外から RPM を持ち込むときこそ重要になります。

```bash
$ rpm -qa gpg-pubkey                  # 取り込み済みの鍵を一覧する
$ rpm -qi gpg-pubkey-fd431d51-4ae0493b   # 鍵の詳細（発行者、期限）を見る
$ sudo rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release   # 鍵を取り込む
$ rpm -K /var/tmp/patch/sudo-1.9.5-1.el9.x86_64.rpm               # 個別の rpm の署名を確かめる
```

**`rpm -K` の読み方**

| 出力 | 意味 |
|:--|:--|
| **`digests signatures OK`** | **ハッシュも署名も正しい**。これが本来の姿 |
| **`digests OK`** | **ハッシュは正しいが、署名されていない** |
| **`digests SIGNATURES NOT OK`** | **署名はあるが、鍵を取り込んでいない**。`rpm -Kv` に `NOKEY` と出る。**鍵を `rpm --import` してからやり直す** |
| **`DIGESTS ... NOT OK`**（大文字） | **壊れている**。**入れてはいけない** |

検証環境での実測です。自作の鍵で署名した rpm を、**鍵を取り込んでいない状態**で確かめました。

```text
/tmp/signed.rpm: digests SIGNATURES NOT OK
```

```text
/tmp/signed.rpm:
    Header V4 RSA/SHA512 Signature, key ID 067daafd: NOKEY
    Header SHA256 digest: OK
    Payload SHA256 digest: OK
```

**署名していない rpm だとこうなります。**

```text
out3/appx-1.0-1.noarch.rpm: digests OK
```

**`digests OK` は「署名されていない」、`digests SIGNATURES NOT OK` は「鍵が無い」**と読み分けます。
**終了ステータスも違います**（`digests OK` は 0、`SIGNATURES NOT OK` は 1）。

> **`--nogpgcheck` は最後の手段**です。使ったなら作業記録に理由を残します。

---

## プロキシの設定

社内環境では、外部リポジトリへプロキシ経由で出ることがあります。

**全体に効かせる**（`/etc/dnf/dnf.conf` の `[main]`）

```ini
proxy=http://proxy.example.local:8080
proxy_username=svc_dnf
proxy_password=********
```

**リポジトリ単位で効かせる**（repo ファイル）

```ini
proxy=http://proxy.example.local:8080
```

**社内リポジトリだけプロキシを通さない**なら、そのリポジトリに `proxy=_none_` を書きます。

```ini
proxy=_none_
```

```bash
$ sudo dnf --setopt=proxy=http://proxy.example.local:8080 makecache   # 一時的に試す
```

> **環境変数 `http_proxy` / `https_proxy` も参照されます。**
> `sudo` 経由だと環境変数が落ちることがあるので、**設定ファイルに書くほうが確実**です。

---

## キャッシュの管理

**dnf はメタデータをキャッシュします。**「更新があるはずなのに出てこない」の大半はこれが原因です。

```bash
$ sudo dnf makecache                  # メタデータのキャッシュを作り直す
$ sudo dnf clean metadata             # メタデータのキャッシュだけ消す
$ sudo dnf clean packages             # ダウンロード済みの rpm を消す
$ sudo dnf clean all                  # キャッシュを全部消す
$ dnf --refresh check-update          # キャッシュを期限切れ扱いにして取り直す
$ dnf -C list --installed             # キャッシュだけで動く（ネットワークを見に行かない）
```

| コマンド | 効果 | 使いどころ |
|:--|:--|:--|
| **`--refresh`** | **今回だけキャッシュを取り直す** | **社内リポジトリを更新した直後** |
| **`-C`** / `--cacheonly` | **ネットワークを見に行かない** | **切断環境で余計な待ちを避ける** |
| **`clean all`** | 全部消す | おかしくなったときの初期化 |
| **`makecache`** | 先にキャッシュを作る | 作業前に通信の可否を確かめる |

**社内リポジトリに RPM を追加したのに dnf に見えないときの手順**

```bash
$ sudo dnf clean metadata             # ① 古いメタデータを捨てる
$ sudo dnf makecache                  # ② 取り直す
$ dnf repoquery --repo=internal-baseos sudo   # ③ 見えるようになったか確かめる
```

> **リポジトリ側で `createrepo_c` を再実行し忘れている**ケースも同じくらい多いです。
> `repodata/repomd.xml` の更新時刻を確認してください。

---

## バージョンを固定する versionlock

**「このパッケージだけは上げたくない」**を実現します。
アプリの動作保証があるミドルウェアや、カーネルでよく使います。

**提供パッケージは `python3-dnf-plugin-versionlock`**（`dnf-plugins-core` の一部）です。

```bash
$ sudo dnf install -y python3-dnf-plugin-versionlock   # プラグインを入れる
$ sudo dnf versionlock add httpd                        # 今のバージョンで固定する
$ dnf versionlock list                                  # 固定しているものを一覧する
$ sudo dnf versionlock delete httpd                     # 固定を外す
$ sudo dnf versionlock clear                            # 全部外す
```

**設定は `/etc/dnf/plugins/versionlock.conf` と `/etc/dnf/plugins/versionlock.list` に入ります。**

> **`exclude` との違い**
>
> | 方法 | 効果 |
> |:--|:--|
> | **`versionlock`** | **今のバージョンに固定する**。そのパッケージ自体は使える |
> | **`exclude`** | **そのパッケージを dnf から見えなくする**。依存で必要でも入らない |
>
> **固定を忘れたまま脆弱性対応の期日を迎える**のがいちばんありがちな事故です。
> `dnf versionlock list` は作業前の確認項目に入れてください。

---

## AppStream モジュール

**RHEL 8 / 9 では、同じソフトの複数バージョンが「モジュール」として提供されます。**
PHP 7.4 と 8.0、PostgreSQL 12 と 13 のような関係です。

```bash
$ dnf module list                     # モジュールの一覧
$ dnf module list php                 # php のストリーム一覧
$ dnf module info php:8.0             # そのストリームの詳細
$ sudo dnf module enable php:8.0      # ストリームを選ぶ
$ sudo dnf module install php:8.0/common   # プロファイルを指定して入れる
$ sudo dnf module reset php           # 選択を解除する
```

| 用語 | 意味 |
|:--|:--|
| **モジュール** | **ソフトのまとまり**（`php`、`postgresql` など） |
| **ストリーム** | **バージョンの系列**（`8.0`、`7.4`） |
| **プロファイル** | **用途別のパッケージの組み合わせ**（`common`、`devel`、`minimal`） |

**ストリームは 1 つしか有効にできません。**
切り替えるときは `reset` してから `enable` します。

> **RHEL 10 ではモジュール機能が無くなりました。**
> Red Hat の「Considerations in adopting RHEL 10」に
> 「モジュラリティをパッケージング技術とする Application Stream を提供する予定はなく、モジュラーコンテンツは配布されない」
> と明記されています。**RHEL 10 へ移行する手順書から `dnf module` を消す必要があります。**

---

## Satellite 配下のサーバ

**Red Hat Satellite や `subscription-manager` で管理されているサーバ**では、
リポジトリ設定の扱いが変わります。

| 項目 | 内容 |
|:--|:--|
| **リポジトリ設定の場所** | **`/etc/yum.repos.d/redhat.repo`** |
| **誰が作るか** | **`subscription-manager` が自動生成する**。ファイル冒頭に「This file is auto-generated. Changes made here will be over-written.」と書かれている |
| **直接編集** | **してはいけない**。上書きされる |

```bash
$ sudo subscription-manager repos --list            # 使えるリポジトリを一覧する
$ sudo subscription-manager repos --list-enabled    # 有効なものだけ
$ sudo subscription-manager repos --enable=rhel-9-for-x86_64-appstream-rpms   # 有効にする
$ sudo subscription-manager repos --disable='*'     # 全部無効にする
$ sudo subscription-manager release --show          # 固定しているマイナーバージョンを見る
$ sudo subscription-manager release --set=9.4       # マイナーバージョンを固定する
$ sudo subscription-manager release --unset         # 固定を解除する
```

**`subscription-manager release --set=` は `$releasever` を固定します。**
EUS（Extended Update Support）でマイナーバージョンを止めたい運用で使います。
固定すると、リポジトリ URL の `$releasever` がその値になります。

**`subscription-manager` の管理を止めたい**なら `/etc/rhsm/rhsm.conf` の `manage_repos=0` にします。
社内リポジトリだけを使う構成にするときに使う設定です。

> **Satellite の切断環境（disconnected）へのコンテンツ持ち込み**は、
> **Inter-Satellite Synchronization（ISS）** という仕組みが公式の方法です。
> 上流 Satellite で `hammer content-export`、下流で `hammer content-import` を実行します。
> **上流と下流で Satellite のメジャーバージョンが同じである必要があります。**
> 素の `dnf` だけで持ち込む方法は⑤にまとめています。

---

## 切り分けの手順

**「dnf が動かない」と言われたときに、上から順に見る**とだいたい片が付きます。

| 症状 | 見るところ | コマンド |
|:--|:--|:--|
| **リポジトリが見つからない** | **repo ID を間違えていないか** | `dnf repolist --all` |
| **メタデータが取れない** | **URL に届くか** | `curl -sI <baseurl>/repodata/repomd.xml` |
| **名前解決できない** | DNS | `getent hosts repo.example.local` |
| **プロキシで止まる** | proxy 設定 | `grep -r proxy /etc/dnf/ /etc/yum.repos.d/` |
| **証明書エラー** | `sslverify`、CA | `curl -v https://...` |
| **更新が出てこない** | **キャッシュが古い** | `dnf --refresh check-update` |
| **更新が出てこない（2）** | **`exclude` / `versionlock`** | `grep exclude /etc/dnf/dnf.conf` / `dnf versionlock list` |
| **リポジトリ側に無い** | **`createrepo_c` のかけ忘れ** | リポジトリサーバで `repodata/repomd.xml` の更新時刻を見る |
| **署名エラー** | **GPG 鍵が未取り込み** | `rpm -qa gpg-pubkey` |
| **Satellite 配下で有効にならない** | **`redhat.repo` とアクティベーションキー** | `subscription-manager repos --list-enabled` |

```bash
$ dnf repolist --all                  # ① リポジトリの ID と有効・無効を確かめる
$ dnf --refresh repolist -v           # ② 実際に取りに行かせて、URL とエラーを見る
$ sudo dnf clean metadata             # ③ キャッシュを捨ててやり直す
```

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — Considerations in adopting RHEL 10](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html-single/considerations_in_adopting_rhel_10/index)
- [Red Hat Satellite — Synchronizing content between servers (ISS)](https://docs.redhat.com/en/documentation/red_hat_satellite/6.17/html/managing_content/synchronizing_content_between_servers_content-management)
- [dnf-plugins-core — versionlock](https://dnf-plugins-core.readthedocs.io/en/latest/versionlock.html)
- [DNF5 — config-manager](https://dnf5.readthedocs.io/en/latest/dnf5_plugins/config-manager.8.html)
- [man 5 dnf.conf](https://man7.org/linux/man-pages/man5/dnf.conf.5.html)

---

[← 全体の目次にもどる](../README.md)
