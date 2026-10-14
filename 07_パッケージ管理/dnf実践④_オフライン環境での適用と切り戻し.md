# dnf実践④ オフライン環境での適用と切り戻し

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **脆弱性対応で毎月走る作業の後半。**持ち込んだ rpm を本番へ当て、確認し、駄目なら戻す。**`sudo` と `openssh` は失敗すると入れなくなる**ので、当て方と戻し方をここで固めておく |

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
> | 実践 | [dnf実践② オンライン環境での切り戻しと除外設定](./dnf実践②_オンライン環境での切り戻しと除外設定.md) | `history undo` / `rollback`、`exclude`、`versionlock`、`dnf-automatic` |
> | 実践 | [dnf実践③ オフライン環境でのパッケージの集め方](./dnf実践③_オフライン環境でのパッケージの集め方.md) | **社内リポジトリに届く場合と完全分離の場合**で、必要な rpm を集める |
> | **実践** | **このノート（dnf実践④）** | 集めた rpm を対象サーバに当てて、問題が出たら戻す |
>
> `rpm` コマンド単体の話は [RPMによるパッケージ管理](./RPMによるパッケージ管理.md) です。
> `yum` 時代の書き方との対応は [YUMとDNFによるパッケージ管理](./YUMとDNFによるパッケージ管理.md) にあります。


> **公式ドキュメントの確認日: 2026-10-13。**引用はその時点の記載です。
> URL は末尾の「参考リンク」にあります。**本番作業の前に、対象バージョンのドキュメントで裏を取ってください。**

---

## 目次

- [対象サーバで適用する](#対象サーバで適用する)
  - [方法A rpm ファイルを直接指定する](#方法a-rpm-ファイルを直接指定する)
  - [方法B ローカルリポジトリにして入れる](#方法b-ローカルリポジトリにして入れる)
  - [方法C 事前テストしてから入れる](#方法c-事前テストしてから入れる)
  - [適用後の確認](#適用後の確認)
- [戻し方](#戻し方)
- [実例 sudo と openssh を当てる](#実例-sudo-と-openssh-を当てる)
  - [ステップ1 対象サーバで現状を確定する](#ステップ1-対象サーバで現状を確定する)
  - [ステップ2 何を上げればいいか決める](#ステップ2-何を上げればいいか決める)
  - [ステップ3 必要な rpm を集める](#ステップ3-必要な-rpm-を集める)
  - [ステップ4 依存が閉じているか確かめる](#ステップ4-依存が閉じているか確かめる)
  - [ステップ5 転送して検証する](#ステップ5-転送して検証する)
  - [ステップ6 当てる](#ステップ6-当てる)
  - [ステップ7 確認して記録する](#ステップ7-確認して記録する)
- [作業チェックリスト](#作業チェックリスト)
  - [事前](#事前)
  - [取得](#取得)
  - [転送](#転送)
  - [適用](#適用)
- [RHEL 7 での書き方](#rhel-7-での書き方)
- [手元で練習する](#手元で練習する)
- [参考リンク](#参考リンク)

---

## 対象サーバで適用する

**適用の方法は A と B の 2 通り**です。**安全なのは B**（必要な分だけが選ばれる）。
**C は適用ではなく、当てる前に依存だけ確かめる手順**です。

### 方法A rpm ファイルを直接指定する

```bash
$ sudo dnf install --setopt=localpkg_gpgcheck=1 /var/tmp/patch/*.rpm   # ディレクトリの rpm を全部入れる
$ sudo dnf upgrade --setopt=localpkg_gpgcheck=1 /var/tmp/patch/*.rpm   # 更新として当てる
```

検証環境での実測です。

```text
Installing:
Install  4 Packages
Installed:
Complete!
```

**`dnf` がインストール順を決めてくれる**ので、`rpm -Uvh` のように順番で悩む必要がありません。

> **注意が 2 つあります。**
>
> **① ファイル指定では GPG 署名が確認されません。**
> `/etc/dnf/dnf.conf` に `gpgcheck=1` と書いてあっても、**ローカルファイルには `localpkg_gpgcheck` のほうが効き、既定は `False`** です（`man 5 dnf.conf`）。
> **`--setopt=localpkg_gpgcheck=1` を明示**してください。
>
> **② `*.rpm` で全部指定すると、要らない更新まで巻き込みます。**
> 方法2（`--alldeps`）で集めたディレクトリには、対象サーバに入っているものより新しい依存まで入っています。
> **必要な分だけ当てたいなら、次の方法B でパッケージ名を指定**してください。

> **`dnf` は、依存が足りているかどうかに関係なく、起動時に有効なすべてのリポジトリのメタデータを読みに行きます。**
> 切断環境で外向きのリポジトリが有効なままだと、
> **依存がそろっていても `Failed to download metadata` で止まるか、タイムアウトまで固まります。**
>
> ```bash
> $ sudo dnf --disablerepo='*' install /var/tmp/patch/*.rpm   # 外を見に行かせない
> ```

### 方法B ローカルリポジトリにして入れる

**こちらが本命**です。**必要なものだけ**が選ばれます。

```bash
$ createrepo_c /var/tmp/patch                # ① リポジトリ化する
$ sudo dnf --repofrompath=patch,file:///var/tmp/patch --repo=patch -y upgrade sudo   # ② そこからだけ更新する
```

検証環境での実測です。

```text
Installing:
Installing dependencies:
Install  4 Packages
Installed:
Complete!
```

**`--repofrompath` を使えば `/etc/yum.repos.d/` に何も置かずに済みます。**
作業後にゴミが残りません。

> **更新は `install` ではなく `upgrade` と書いてください。**
> `dnf.conf` が `best=False` の環境だと、導入済みパッケージに対する `install` は
> **`Package ... is already installed. Nothing to do.` で終わり、何も当たりません**（実測）。
> `upgrade` なら `best` の設定に関係なく更新されます。**新規に入れるときだけ `install`** です。

> **`--repo` と `--disablerepo` は併用できません**（実測でエラーを確認）。
> **`--repo=patch` だけ**を書けば、そのリポジトリだけが使われます。

### 方法C 事前テストしてから入れる

```bash
$ sudo rpm -Uvh --test /var/tmp/patch/*.rpm   # 依存が足りるかだけ試す（何も変更しない）
```

足りないときの実測です。

```text
error: Failed dependencies:
	libbar is needed by appx-1.0-1.noarch
	libfoo >= 1.0 is needed by appx-1.0-1.noarch
```

**何も出なければ依存は足りています。**
本番で当てる直前の最終確認として、これを挟むのが安全です。

### 適用後の確認

```bash
$ rpm -q sudo openssh-server          # 版が上がったか確認する
$ dnf history                         # トランザクション ID を控える
$ sudo dnf needs-restarting -s        # 再起動が要るサービスを出す
$ sudo dnf needs-restarting -r ; echo "exit=$?"   # OS 再起動の要否を判定する
$ rpm -qa --qf '%{NAME} %{EPOCH}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | sort > /tmp/after.txt   # 作業後の状態を控える
$ diff /tmp/before.txt /tmp/after.txt   # 何が変わったかを出す
```

---

## 戻し方

**当てた直後に問題が出たとき**の手段を、作業前に用意しておきます。

```bash
$ dnf history                         # ① 当てたトランザクションの ID を確認する
$ dnf history info 12                 # ② 中身を確認する
$ sudo dnf history undo 12            # ③ そのトランザクションだけ取り消す
```

**`undo` が成功するには、戻す先の rpm が手に入る必要があります。**

| 状況 | 戻せるか |
|:--|:--|
| **前の版が社内リポジトリにある** | **戻せる** |
| **前の版をどこにも残していない** | **戻せない** |
| **旧版の rpm を自分で確保してある** | **戻せる**（`dnf downgrade /var/tmp/rollback/*.rpm`）。**`keepcache=1` で残るのは「新しく落とした版」で、入れ替わる前の旧版ではありません** |

> **これが「社内リポジトリで `--newest-only` を使うと戻せなくなる」という話につながります。**
>
> **確実なのは、当てる前に元の rpm を自分で確保しておくこと**です。
>
> ```bash
> $ dnf download --destdir=/var/tmp/rollback sudo-$(rpm -q --qf '%{VERSION}-%{RELEASE}' sudo)   # 今の版を確保する
> ```
>
> 切断環境では、**社内リポジトリから旧版を先に落としておく**運用にしてください。

**`undo` も効かないときは、確保しておいた旧版 rpm を `dnf downgrade` で戻します。**

```bash
$ sudo dnf downgrade /var/tmp/rollback/*.rpm   # 旧版 rpm を指定して戻す
```

**`dnf downgrade` なら依存も解決され、`dnf history` にも残ります。**
`openssh` のように兄弟パッケージ（`openssh` / `openssh-server` / `openssh-clients`）がある場合は、**まとめて指定**してください。片方だけ戻すと版が食い違います。

```bash
$ sudo rpm -Uvh --oldpackage /var/tmp/rollback/sudo-1.9.5p2-7.el9.x86_64.rpm   # 最後の手段（履歴に残らない）
```

---

## 実例 sudo と openssh を当てる

**「CVE-2026-XXXXX 対応で `sudo` と `openssh` を上げてください」と来たとき**の流れです。

> **以下のコマンド列は、上で実測した挙動をそのまま `sudo` / `openssh` に当てはめたものです。**
> **画面出力は RHEL の実機で取っていないため載せていません。**
> 出力の読み方は、このノートの検証環境の実測例と同じです。

### ステップ1 対象サーバで現状を確定する

```bash
$ rpm -q sudo openssh openssh-server openssh-clients   # いま入っている版を控える
$ rpm -qa --qf '%{NAME} %{EPOCH}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | sort > /tmp/before.txt   # 全体の控え
$ cat /etc/redhat-release ; uname -m ; dnf --version   # OS 版・アーキ・dnf 版を控える
$ dnf versionlock list 2>/dev/null     # 固定されているものが無いか確認する
```

**`openssh` は 1 パッケージではありません。** `openssh` / `openssh-server` / `openssh-clients` に分かれています。
**サーバに入っているものだけ**を対象にします。

### ステップ2 何を上げればいいか決める

> **パターンB では、この節のコマンドを対象サーバで打てません**（リポジトリに届かないため）。
> **作業用マシンで、方法3 の `fakeroot`（対象サーバの rpmdb を展開したもの）を使い、
> 各コマンドに `--installroot=/var/tmp/fakeroot --releasever=9` を付けて実行**してください。
> パターンA なら対象サーバでそのまま打てます。

```bash
$ dnf --refresh updateinfo list --cve CVE-2026-XXXXX   # 対応するアドバイザリと対象パッケージを出す
$ dnf updateinfo info --cve CVE-2026-XXXXX             # 重大度と説明を読む
$ dnf repoquery --upgrades --qf '%{name}-%{evr}.%{arch}\n' | grep -E '^(sudo|openssh)'   # 上がる先の版を確認する
```

### ステップ3 必要な rpm を集める

**パターンA（対象サーバが社内リポジトリに届く）**

```bash
$ sudo dnf upgrade --downloadonly --destdir=/var/tmp/patch-20260929 --cve CVE-2026-XXXXX   # 必要な分だけ落とす
```

**パターンB（届かない。作業用マシンで集める）**

```bash
$ dnf --releasever=9 --forcearch=x86_64 download --resolve --alldeps \
      --destdir=/var/tmp/patch-20260929 sudo openssh openssh-server openssh-clients   # 依存を全部落とす
```

**転送量を絞りたいなら方法3**（対象サーバの rpmdb を持ってきて `--installroot` で解決）を使います。

### ステップ4 依存が閉じているか確かめる

```bash
$ createrepo_c /var/tmp/patch-20260929   # リポジトリ化する
$ dnf --refresh repoclosure --repofrompath=chk,file:///var/tmp/patch-20260929 --repo=chk ; echo "exit=$?"   # 閉じているか判定する
```

**`exit=0` なら、集めた rpm の中だけで依存が閉じています。**
`exit=1` なら足りない依存が表示されるので、それを追加で集めます。

> **この判定は方法2（`--alldeps`）で集めた場合のものです。**
> **方法1 や方法3 で作った最小セットは、対象サーバの導入済みパッケージを前提にしているので、単独では閉じません**（`exit=1` が正常）。
> その場合は、対象サーバ上で `rpm -Uvh --test` と `dnf ... --assumeno` を使って確認してください。

### ステップ5 転送して検証する

```bash
$ cd /var/tmp/patch-20260929 && sha256sum *.rpm > SHA256SUMS   # ハッシュを取る
$ tar czf /tmp/patch-20260929.tar.gz -C /var/tmp patch-20260929   # まとめる
```

```bash
$ tar xzf /tmp/patch-20260929.tar.gz -C /var/tmp        # 対象サーバで展開する
$ cd /var/tmp/patch-20260929 && sha256sum -c SHA256SUMS # ハッシュを照合する
$ rpm -K *.rpm                                          # 署名を確認する
```

### ステップ6 当てる

```bash
$ sudo rpm -Uvh --test /var/tmp/patch-20260929/*.rpm    # ① 依存が足りるか試す（変更なし）
$ sudo dnf --repofrompath=patch,file:///var/tmp/patch-20260929 --repo=patch --assumeno upgrade sudo openssh-server   # ② 下見する
$ sudo dnf --repofrompath=patch,file:///var/tmp/patch-20260929 --repo=patch -y upgrade sudo openssh-server           # ③ 当てる
```

### ステップ7 確認して記録する

```bash
$ rpm -q sudo openssh-server          # 版が上がったか確認する
$ sudo sshd -t                        # sshd の設定に文法誤りが無いか確かめる
$ sudo dnf needs-restarting -s        # 再起動が要るサービスを出す
$ sudo systemctl restart sshd         # sshd を再起動する（別セッションを開いたまま）
$ sudo systemctl status sshd          # 起動したか確認する
$ ss -tlnp | grep ':22'               # 22 番で待ち受けているか確認する
$ dnf history                         # トランザクション ID を控える
```

> **`sshd` を再起動する前に、必ず別の SSH セッションを開いたままにしてください。**
> 設定に誤りがあっても、開いているセッションから戻せます。
> **`sudo sshd -t` は更新の前と後の両方で打ってください。**何も出なければ設定は正しいということです。
> `openssh-server` の rpm は更新時に `sshd` を自動で再起動することがあるため、
> **後だけに打つと間に合わないことがあります**（そのサーバの挙動は `rpm -q --scripts openssh-server` の `postun` で確認できます）。
>
> **`sudo` を上げるときの注意**もあります。
> `sudo` が壊れると**権限昇格ができなくなります**。
> 作業前に **root で直接入れる手段**（コンソール、別の踏み台）を確保しておいてください。

---

## 作業チェックリスト

**そのまま手順書に貼れる形**にしてあります。

### 事前

| # | 項目 | コマンド |
|:-:|:--|:--|
| 1 | OS 版・アーキ・dnf 版を控えた | `cat /etc/redhat-release ; uname -m ; dnf --version` |
| 2 | 導入済みパッケージの控えを取った | `rpm -qa --qf ... \| sort > /tmp/before.txt` |
| 3 | **対象サーバがリポジトリに届くか確かめた** | `dnf --refresh repolist -v` |
| 4 | 対象の CVE とアドバイザリを特定した | `dnf updateinfo list --cve ...` |
| 5 | **何が上がるか下見した** | `dnf upgrade --cve ... --assumeno` |
| 6 | **消えるものが無いか確認した** | 下見の `Removing:` が空であること |
| 7 | versionlock / exclude を確認した | `dnf versionlock list` / `grep exclude /etc/dnf/dnf.conf` |
| 8 | **戻すための旧版 rpm を確保した** | `dnf download --destdir=/var/tmp/rollback ...` |
| 9 | **スナップショットまたはバックアップを取った** | 仮想基盤側で実施。`dnf history undo` では戻せない設定ファイルの差し替えに備える |
| 10 | **カーネル更新が含まれるか確認した** | 下見に `kernel-core` などが出るか。`df -h /boot` で空きを確認し、適用後は再起動して `uname -r` で確認する |

### 取得

| # | 項目 | コマンド |
|:-:|:--|:--|
| 11 | **どの方法で集めるか決めた** | 方法1〜4のいずれか |
| 12 | **`--resolve` 単体を使っていない**（使うなら `--alldeps`） | — |
| 13 | `--releasever` と `--forcearch` を対象に合わせた | — |
| 14 | **依存が閉じているか確かめた**（方法2 のとき） | `dnf --refresh repoclosure ... ; echo $?` が 0。方法1・3 の最小セットは閉じなくて正常 |

### 転送

| # | 項目 | コマンド |
|:-:|:--|:--|
| 15 | ハッシュを取った | `sha256sum *.rpm > SHA256SUMS` |
| 16 | **転送先でハッシュを照合した** | `sha256sum -c SHA256SUMS` |
| 17 | **GPG 署名を確認した** | `rpm -K *.rpm` |

### 適用

| # | 項目 | コマンド |
|:-:|:--|:--|
| 18 | **依存の事前テストをした** | `rpm -Uvh --test *.rpm` |
| 19 | **外部リポジトリを見に行かせない指定を入れた** | `--repo=patch` または `--disablerepo='*'` |
| 20 | 当てた | `dnf --repofrompath=... --repo=patch -y upgrade ...` |
| 21 | **版が上がったことを確認した** | `rpm -q ...` |
| 22 | **設定の文法チェックをした**（sshd など） | `sshd -t` |
| 23 | 再起動の要否を判定した | `dnf needs-restarting -r ; echo $?` |
| 24 | **トランザクション ID を控えた** | `dnf history` |
| 25 | 作業後の控えを取り、差分を確認した | `diff /tmp/before.txt /tmp/after.txt` |

---

## RHEL 7 での書き方

**RHEL 7 は yum-3 なので、コマンドが違います。**

| やりたいこと | RHEL 8 / 9（dnf-4） | RHEL 7（yum-3） |
|:--|:--|:--|
| **入れずに落とす** | `dnf install --downloadonly --destdir=DIR PKG` | **`yum install --downloadonly --downloaddir=DIR PKG`** |
| **依存ごと落とす** | `dnf download --resolve --alldeps PKG` | **`yumdownloader --resolve --destdir=DIR PKG`**<br>または **`repotrack -p DIR PKG`** |
| **必要なパッケージ** | `dnf-plugins-core` | **`yum-utils`** |
| **セキュリティ一覧** | `dnf updateinfo list --security` | **`yum updateinfo list --security`** |
| **セキュリティ適用** | `dnf upgrade --security` | **`yum update --security`** |
| **最小適用** | `dnf upgrade-minimal --security` | **`yum update-minimal --security`** |
| **CVE 指定** | `dnf upgrade --cve CVE-...` | **`yum update --cve CVE-...`** |
| **リポジトリ設定** | `dnf config-manager` | **`yum-config-manager`** |
| **リポジトリ複製** | `dnf reposync` | **`reposync`**（`yum-utils`） |
| **履歴と取り消し** | `dnf history undo N` | **`yum history undo N`** |

```bash
$ sudo yum install -y yum-utils       # RHEL 7 でまず入れるもの
$ yumdownloader --resolve --destdir=/var/tmp/patch sudo   # 依存も含めて落とす
$ repotrack -p /var/tmp/patch sudo                        # 依存を再帰的に全部落とす
```

> **`yumdownloader --resolve` にも `dnf download --resolve` と同じ落とし穴があります。**
> 実行したマシンに入っている依存は落ちてきません。
> **RHEL 7 で「全部欲しい」なら `repotrack`** を使ってください。`repotrack` は導入状態を見ずに再帰的に集めます。
>
> **`repotrack` は RHEL 8 以降では標準で見当たりません。**
> Red Hat のナレッジに「Unable to find repotrack command in RHEL 8 and later releases」という記事があります
> （本文は購読者向けのため未確認）。
> **RHEL 8 以降では `dnf download --resolve --alldeps` が代替**です（DNF 公式ドキュメントに対応が記載されています）。

> **セキュリティプラグインについて**
> RHEL 7 以降は `yum` に組み込み済みで、`yum-plugin-security` を別途入れる必要はありません。
> RHEL 6 では `yum-plugin-security` が必要でした。

---

## 手元で練習する

**本番に触らずに、ここまでの挙動を全部再現できます。**
小さな noarch パッケージを数個作って、ローカルディレクトリをリポジトリにするだけです。

```bash
$ mkdir -p ~/lab/{SPECS,RPMS,SOURCES,BUILD,BUILDROOT} ~/lab/repo   # 作業ディレクトリを作る
```

**spec ファイルの例**（`libbar` が `libbaz` に依存する形）

```text
Name: libbar
Version: 1.0
Release: 1
Summary: test package libbar
License: MIT
BuildArch: noarch
Requires: libbaz
%description
test package libbar
%install
mkdir -p %{buildroot}/usr/share/libbar
echo libbar-1.0 > %{buildroot}/usr/share/libbar/VERSION
%files
/usr/share/libbar
```

```bash
$ rpmbuild --define "_topdir $HOME/lab" -bb ~/lab/SPECS/libbar-1.0.spec   # rpm を作る
$ cp ~/lab/RPMS/noarch/*.rpm ~/lab/repo/                                  # 1か所に集める
$ createrepo_c ~/lab/repo                                                 # リポジトリにする
```

**リポジトリ設定を書いて、空のルートに対して試します。**

```bash
$ mkdir -p ~/lab/repos.d ~/lab/root   # 設定置き場と仮想ルートを作る
$ printf '[local]\nname=local\nbaseurl=file://%s/lab/repo\nenabled=1\ngpgcheck=0\n' "$HOME" > ~/lab/repos.d/local.repo   # repo 設定を書く
$ printf '[main]\ngpgcheck=0\nreposdir=%s/lab/repos.d\ncachedir=%s/lab/cache\n' "$HOME" "$HOME" > ~/lab/dnf.conf   # dnf 設定を書く
$ dnf -c ~/lab/dnf.conf --installroot=$HOME/lab/root --releasever=9 repolist   # 見えるか確認する
```

**この要領で `libbaz`（依存なし）、`libfoo`（Version 1.0 と 2.0 の 2 つ）、
`appx`（`Requires: libfoo >= 1.0` と `Requires: libbar`）の spec も作り、同じ `~/lab/repo` に集めて
`createrepo_c` をかけ直せば、本文のコマンドをそのまま試せます。**

```bash
$ sudo dnf install -y rpm-build createrepo_c   # 先に必要なツールを入れる
```

```bash
$ dnf -c ~/lab/dnf.conf --installroot=$HOME/lab/root --releasever=9 -y install libbar   # 依存ごと入る
$ dnf -c ~/lab/dnf.conf --installroot=$HOME/lab/root --releasever=9 download --resolve --destdir=/tmp/o1 appx   # 落とし穴を再現する
$ dnf -c ~/lab/dnf.conf --installroot=$HOME/lab/root --releasever=9 download --resolve --alldeps --destdir=/tmp/o2 appx   # 違いを見る
```

> **`--installroot` を使うので、実行しているマシン本体には一切影響しません。**
> 依存解決の挙動を体で覚えるのに、これがいちばん安全で速いやり方です。

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — Is it possible to limit yum so that it lists or installs only security updates?](https://access.redhat.com/solutions/10021)
- [Red Hat Satellite — Synchronizing content between servers (ISS)](https://docs.redhat.com/en/documentation/red_hat_satellite/6.17/html/managing_content/synchronizing_content_between_servers_content-management)
- [man 8 rpm](https://man7.org/linux/man-pages/man8/rpm.8.html)
- [man 8 dnf](https://man7.org/linux/man-pages/man8/dnf.8.html)

---

[← 全体の目次にもどる](../README.md)
