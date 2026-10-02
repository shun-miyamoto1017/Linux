# dnfコマンド⑤ オフライン環境でのパッケージの集め方

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / Linuxのインストールとパッケージ管理(主題102) — RPMとYUMパッケージ管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **脆弱性対応で毎月走る作業の前半。**インターネットに出られない本番サーバへ届ける rpm を、過不足なく集める。ここを勘でやると「持っていった rpm では依存が足りず、本番で止まる」が起きる |

> `dnf` 本体の使い方は [dnfコマンド① 基本と主要サブコマンド](./dnfコマンド①_基本と主要サブコマンド.md)、
> リポジトリの設定は [dnfコマンド② リポジトリとキャッシュの管理](./dnfコマンド②_リポジトリとキャッシュの管理.md)、
> **何を当てるかを決める調査**は [dnfコマンド③ 依存関係とセキュリティ更新の調べ方](./dnfコマンド③_依存関係とセキュリティ更新の調べ方.md) です。
> **集めたものを実際に当てる手順**は
> [dnfコマンド⑥ オフライン環境での適用と切り戻し](./dnfコマンド⑥_オフライン環境での適用と切り戻し.md) にあります。
> **`sudo` と `openssh` を当てる通しの実例**と**作業チェックリスト**も⑥にまとめてあります。
> **対象サーバがリポジトリに届くなら、手運びは不要です。**その場合は [dnfコマンド④ オンライン環境での更新手順](./dnfコマンド④_オンライン環境での更新手順.md) へ。

---

## 目次

- [2つのパターンを最初に切り分ける](#2つのパターンを最初に切り分ける)
- [パターンA 対象サーバが社内リポジトリに届く](#パターンa-対象サーバが社内リポジトリに届く)
- [パターンB 対象サーバがどこにも届かない](#パターンb-対象サーバがどこにも届かない)
- [いちばん多い失敗 resolve の落とし穴](#いちばん多い失敗-resolve-の落とし穴)
- [必要な rpm を集める4つの方法](#必要な-rpm-を集める4つの方法)
- [方法1 対象サーバ上で解決してダウンロードだけする](#方法1-対象サーバ上で解決してダウンロードだけする)
- [方法2 alldeps で依存を全部持っていく](#方法2-alldeps-で依存を全部持っていく)
- [方法3 installroot で対象機の状態を再現する](#方法3-installroot-で対象機の状態を再現する)
- [方法4 リポジトリをまるごと複製する reposync](#方法4-リポジトリをまるごと複製する-reposync)
- [集めた rpm をリポジトリにする createrepo_c](#集めた-rpm-をリポジトリにする-createrepoc)
- [転送と検証](#転送と検証)
- [参考リンク](#参考リンク)

---

## 2つのパターンを最初に切り分ける

**やることが根本から変わるので、ここを最初に確定させます。**

```text
  [ パターンA ]  対象サーバ ──HTTP──▶ 社内リポジトリサーバ ──(定期同期)──▶ インターネット
                  dnf が自分でリポジトリを見に行ける

  [ パターンB ]  対象サーバ  ×  どこにも届かない
                  別のマシンで rpm を集め、ファイル転送やメディアで持ち込む
```

**判定のしかた**

```bash
$ dnf repolist                        # 有効なリポジトリが出るか
$ dnf --refresh repolist -v           # 実際に取りに行かせて、届くか確かめる
$ curl -sI http://repo.example.local/rhel9/baseos/repodata/repomd.xml   # URL に届くか
```

| 結果 | どちらか |
|:--|:--|
| **リポジトリ一覧が出て、`--refresh` も通る** | **パターンA**。ここから先は普通の `dnf` 作業 |
| **`Failed to download metadata` になる** | **パターンB**。rpm を持ち込む |

> **パターンAなのにBだと思い込んで手運びしている現場**が実際にあります。
> まず `dnf --refresh repolist -v` を 1 回打ってください。**届くなら作業量が 10 分の 1 になります。**

---

## パターンA 対象サーバが社内リポジトリに届く

**この場合、特別なことはほとんど要りません。**
ただし本番では **「落とす」と「当てる」を分ける**のが定石です。ダウンロードで失敗しても本番が変わらないからです。

```bash
$ sudo dnf --refresh check-update --security       # ① 対象があるか確かめる
$ sudo dnf upgrade --security --assumeno           # ② 何が上がるか下見する
$ sudo dnf upgrade --security --downloadonly --destdir=/var/tmp/patch-20260929   # ③ 落とすだけ
$ ls -l /var/tmp/patch-20260929                    # ④ 落ちたものを確認する
$ sudo dnf upgrade --security -y                   # ⑤ 当てる（③の --destdir 分は使われず再取得される。下記参照）
$ sudo dnf needs-restarting -r ; echo "exit=$?"    # ⑥ 再起動の要否を確認する
```

**`--downloadonly` の時点では本番は 1 バイトも変わりません。**
ここでエラーが出たら、当てる前に社内リポジトリ側を直せます。

> **`--downloadonly --destdir` で落としたものは、`dnf` の次の成功トランザクションで消される可能性があります。**
> `man 8 dnf` の `--downloadonly` の項に
> 「Packages are removed after the next successful transaction. This applies also when used together with `--destdir` option as the directory is considered as a part of the DNF cache. To persist the packages, use the download command instead.」
> と明記されています。**持ち込み用に確実に残したいなら `dnf download --destdir=...` を使ってください。**
> また **⑤ では `--destdir` に落とした分は使われず、再ダウンロードが走ります。**
> 通信を切ってから当てたいなら、落とした rpm をローカルリポジトリにして当てます（後述の方法B）。

**CVE 指定で当てるとき**

```bash
$ sudo dnf --refresh updateinfo list --cve CVE-2026-11111   # 対象を特定する
$ sudo dnf upgrade --cve CVE-2026-11111 --assumeno          # 下見する
$ sudo dnf upgrade --cve CVE-2026-11111 -y                  # 当てる
```

---

## パターンB 対象サーバがどこにも届かない

**作業は 5 段階**になります。

```text
  ① 対象サーバで「いま何が入っているか」を確定する        ← ここが全て
        ↓
  ② リポジトリに届くマシンで、必要な rpm を集める
        ↓
  ③ 集めた rpm で依存が閉じているか確かめる
        ↓
  ④ 転送して、ハッシュと署名を検証する
        ↓
  ⑤ 対象サーバで当てて、記録を残す
```

**②で何を集めるかは、①の結果に完全に依存します。**
次の節がこのノートでいちばん大事な部分です。

---

## いちばん多い失敗 resolve の落とし穴

**`dnf download --resolve` は「実行したマシンに入っていない依存」しかダウンロードしません。**

これを知らずに、リポジトリに届く「作業用サーバ」で `--resolve` を打つと、
**作業用サーバに既に入っているパッケージが結果から抜け落ちます。**
対象サーバにそれが入っていなければ、持ち込んだ rpm では依存が足りません。

**検証環境で実際に確かめました。**

構成は次のとおりです。

```text
  appx  ── 依存 ──▶ libfoo (>= 1.0)
        └─ 依存 ──▶ libbar ── 依存 ──▶ libbaz

  実行したマシンには libbar と libbaz が「すでに入っている」状態
```

```bash
$ dnf download --resolve --destdir=out2 appx   # 導入済みを除いてダウンロードする
$ ls out2                                      # 落ちてきたものを見る
```

```text
appx-1.0-1.noarch.rpm
libfoo-2.0-1.noarch.rpm
```

**`libbar` と `libbaz` が落ちてきていません。**
実行したマシンに入っているからです。この 2 個を持たずに対象サーバへ行くと、そこで止まります。

```bash
$ dnf download --resolve --alldeps --destdir=out3 appx   # 導入済みも含めて全部ダウンロードする
$ ls out3                                                # 落ちてきたものを見る
```

```text
appx-1.0-1.noarch.rpm
libbar-1.0-1.noarch.rpm
libbaz-1.0-1.noarch.rpm
libfoo-2.0-1.noarch.rpm
```

**`--alldeps` を付けると 4 個すべて落ちてきます。**

`dnf --help` の記述は次のとおりです（dnf-4.14.0 の実測）。

```text
  --resolve             resolve and download needed dependencies
  --alldeps             when running with --resolve, download all dependencies
                        (do not exclude already installed ones)
```

> **覚え方**
>
> | 書き方 | 基準 | 結果 |
> |:--|:--|:--|
> | **`--resolve`** | **コマンドを打ったマシンの導入状態** | **そのマシンに足りないものだけ** |
> | **`--resolve --alldeps`** | **導入状態を無視** | **依存の全体** |
>
> **対象サーバと作業用サーバの導入状態が同じだと確信できないなら、`--resolve` 単体は使わない。**
> これがオフライン作業の第一原則です。

---

## 必要な rpm を集める4つの方法

**どれを選ぶかは「どこで依存解決できるか」で決まります。**

| 方法 | どこで解決するか | 集まる量 | 正確さ | 使いどころ |
|:--|:--|:--|:--|:--|
| **方法1 `--downloadonly`** | **対象サーバ自身** | **最小** | **いちばん正確** | **対象サーバがリポジトリに届くなら第一候補** |
| **方法2 `--alldeps`** | 別マシン（状態を無視） | 多い | **安全側** | **対象サーバが届かないときの基本** |
| **方法3 `--installroot`** | 別マシン（状態を再現） | 最小 | 正確だが手間 | 台数が多い、転送量を絞りたい |
| **方法4 `reposync`** | 解決しない（丸ごと） | **非常に多い** | 取りこぼし無し | **社内リポジトリそのものを作る** |

---

## 方法1 対象サーバ上で解決してダウンロードだけする

**対象サーバがリポジトリに届くなら、これがいちばん正確**です。
**そのサーバの実際の導入状態**に基づいて、**本当に足りないものだけ**が落ちてきます。

```bash
$ sudo dnf install --downloadonly --destdir=/var/tmp/patch sudo   # 入れずに、必要な rpm だけ落とす
$ ls -l /var/tmp/patch                                            # 落ちたものを確認する
```

検証環境で、`libbar` と `libbaz` が入っている状態で `appx` を対象にした実測です。

```text
Installing:
Installing dependencies:
Install  2 Packages
Total size: 12 k
```

```text
appx-1.0-1.noarch.rpm
libfoo-2.0-1.noarch.rpm
```

**2 個だけ**です。既に入っている `libbar` / `libbaz` は不要なので落ちてきません。**これがそのサーバにとっての正解**です。

**更新の場合も同じです。**

```bash
$ sudo dnf upgrade --downloadonly --destdir=/var/tmp/patch --security   # セキュリティ更新分だけ落とす
$ sudo dnf upgrade --downloadonly --destdir=/var/tmp/patch libfoo       # 特定パッケージだけ落とす
```

検証環境で `libfoo-1.0` が入っている状態の実測です。

```text
Upgrading:
Upgrade  1 Package
Total size: 6.0 k
```

```text
libfoo-2.0-1.noarch.rpm
```

> **「落としたあと、ネットワークを切ってから当てる」**運用にするなら、
> 落とした rpm を `createrepo_c` でローカルリポジトリにして、方法B で当てます。
> **落としたあとに素の `dnf upgrade` を打つと、再ダウンロードが走ります。**
> 変更を伴う作業を、通信が確実にある時間帯から切り離せるのが利点です。

---

## 方法2 alldeps で依存を全部持っていく

**対象サーバがリポジトリに届かないときの基本**です。
リポジトリに届く別マシンで、**導入状態を無視して依存を全部**集めます。

```bash
$ dnf download --resolve --alldeps --destdir=/var/tmp/patch sudo openssh-server   # 依存を全部落とす
$ ls -l /var/tmp/patch                                                            # 落ちたものを確認する
```

**「上げる」目的なら、対象のバージョンを明示**します。

```bash
$ dnf download --resolve --alldeps --destdir=/var/tmp/patch sudo-1.9.5p2-10.el9_3   # 版を指定して落とす
```

**アドバイザリや CVE で落とすときは、先に対象パッケージを特定してから版を明示します。**

> **`dnf download` は `--advisory` / `--cve` / `--security` を受け付けますが、無視します。**
> 存在しない CVE を指定しても、そのパッケージの最新版がそのまま落ちてきました（実測）。
> **絞り込みが効いていると思い込むと、当てたつもりで当たっていない**という事故になります。
> パッケージ名を省いて `--advisory` だけ書くと `error: the following arguments are required: packages` で止まります。

```bash
$ dnf updateinfo list --advisory RHSA-2026:0001   # ① 対象パッケージ（名前-版-リリース.アーキ）を確認する
$ dnf download --resolve --alldeps --destdir=/var/tmp/patch libfoo-2.0-1.noarch   # ② 確認した版を明示して落とす
```

**`--releasever` と `--forcearch` で、作業用マシンと対象サーバの違いを吸収します。**

```bash
$ dnf --releasever=9 --forcearch=x86_64 download --resolve --alldeps --destdir=/var/tmp/patch sudo   # 対象に合わせる
```

| オプション | 合わせるもの |
|:--|:--|
| **`--releasever=9`** | **OS のメジャーバージョン**（RHEL 9 向けを取る） |
| **`--forcearch=x86_64`** | **アーキテクチャ** |
| **`--repo=ID`** | **どのリポジトリから取るか** |

> **欠点は量です。**
> `sudo` のような基礎パッケージだと、`glibc` まで芋づる式に付いてきて数百 MB になることがあります。
> **転送量が問題になるなら方法1か方法3**にしてください。

**先に何が落ちてくるか確かめる**

```bash
$ dnf download --resolve --alldeps --url sudo   # ダウンロードせず URL だけ出す
```

`--url` は**実際には落とさず、取得先の URL を並べるだけ**です。件数と容量の見積もりに使えます。

---

## 方法3 installroot で対象機の状態を再現する

**対象サーバの rpmdb（導入済み情報）を作業用マシンに持ってきて、そこで依存解決**します。
**方法1と同じ正確さを、届かないサーバに対して実現**できます。

```bash
$ sudo tar czf /tmp/rpmdb.tar.gz -C / var/lib/rpm   # ① 対象サーバで rpmdb を固める
```

```bash
$ sudo mkdir -p /var/tmp/fakeroot                          # ② 作業用マシンに展開先を作る
$ sudo tar xzf /tmp/rpmdb.tar.gz -C /var/tmp/fakeroot      # ③ rpmdb を展開する
$ sudo mkdir -p /var/tmp/fakeroot/etc/yum.repos.d          # ④ リポジトリ設定を置く場所を作る
$ sudo cp /etc/yum.repos.d/internal.repo /var/tmp/fakeroot/etc/yum.repos.d/   # ⑤ リポジトリ設定を置く
```

```bash
$ sudo dnf --installroot=/var/tmp/fakeroot --releasever=9 upgrade --downloadonly --destdir=/var/tmp/patch sudo   # ⑥ 対象機の状態で解決する（更新なので upgrade）
```

**`--installroot` を付けると、dnf はそのディレクトリを `/` とみなして動きます。**
導入済み判定も、そのディレクトリの `var/lib/rpm` を見ます。

> **注意点が 3 つあります。**
>
> | 注意 | 内容 |
> |:--|:--|
> | **`--releasever` が必須になりやすい** | `--installroot` の中に `redhat-release` が無いと `Unable to detect release version` になる |
> | **rpmdb のバージョン差** | 作業用マシンの `rpm` が対象サーバより**古い**と、rpmdb を読めないことがある。**同じ OS バージョンのマシンを使う** |
> | **モジュール状態** | RHEL 8 / 9 の AppStream モジュールの有効化状態は `/etc/dnf/modules.d/` にある。厳密にやるならこれも持ってくる |

**検証環境では、この `--installroot` を使って「何も入っていないサーバ」と「一部入っているサーバ」の
両方の依存解決を再現しました。** このノートの実測値はすべてその方式で取っています。

---

## 方法4 リポジトリをまるごと複製する reposync

**社内リポジトリサーバ自体を作る/更新する**ときに使います。
個別のパッチ作業ではなく、**基盤側の仕事**です。

```bash
$ sudo dnf reposync --repo=rhel-9-for-x86_64-baseos-rpms --download-metadata --newest-only -p /srv/repo   # 複製する
```

| オプション | 効果 |
|:--|:--|
| **`--repo=ID`** | **複製するリポジトリ** |
| **`--download-metadata`** | **メタデータも一緒に落とす**。**これが無いとアドバイザリ情報が欠ける** |
| **`--newest-only`** / `-n` | **最新版だけ**。容量が大幅に減る |
| **`-p パス`** / `--download-path` | 保存先 |
| **`--delete`** | 上流から消えたものをローカルでも消す |
| **`-g`** / `--gpgcheck` | **署名が不正なものをダウンロード後に削除する** |
| **`--norepopath`** | 保存先にリポジトリ名のディレクトリを作らない |
| **`-u`** / `--urls` | **落とさずに URL を並べるだけ**（見積もり用） |

検証環境での実測です。

```text
(1/4): appx-1.0-1.noarch.rpm                    4.6 MB/s | 6.0 kB     00:00
(2/4): libbar-1.0-1.noarch.rpm                  3.3 MB/s | 6.0 kB     00:00
(3/4): libbaz-1.0-1.noarch.rpm                  2.6 MB/s | 6.0 kB     00:00
(4/4): libfoo-2.0-1.noarch.rpm                  5.9 MB/s | 6.0 kB     00:00
```

**保存先の構造**（実測）

```text
mirror/local/appx-1.0-1.noarch.rpm
mirror/local/libbar-1.0-1.noarch.rpm
mirror/local/libbaz-1.0-1.noarch.rpm
mirror/local/libfoo-2.0-1.noarch.rpm
mirror/local/repodata/○○-primary.xml.gz
mirror/local/repodata/○○-updateinfo.xml.gz        ← --download-metadata を付けたので付いてくる
mirror/local/repodata/repomd.xml
```

> **`--download-metadata` を付け忘れると `updateinfo.xml` が落ちてきません。**
> すると社内リポジトリでは **`dnf upgrade --security` も `--cve` も効かなくなります**。
> 「社内リポジトリだとセキュリティ絞り込みができない」という相談の原因はほぼこれです。
>
> **`--newest-only` にも副作用があります。** 最新版しか置かないと、**`dnf downgrade` で戻せなくなります。**
> さらに **`--download-metadata` と併用すると、メタデータには旧版が載ったまま、rpm だけが無い状態**になります。
> 実測では、最新版だけを落としたミラーに対して `repoquery` が旧版まで返しました。
> この状態で旧版を指定して `install` や `downgrade` を打つと、**ファイルが無いので失敗します。**
> 戻せることを重視するなら、**`--newest-only` を付けずに世代を残す設計**にしてください。

> **dnf-5 では `--downloadcomps` が廃止され、`--download-metadata` に統合**されました。

---

## 集めた rpm をリポジトリにする createrepo_c

**RPM を集めただけのディレクトリは、まだリポジトリではありません。**
`createrepo_c` で `repodata/` を作ると、`dnf` から普通のリポジトリとして扱えます。

```bash
$ sudo dnf install -y createrepo_c    # 無ければ入れる
$ createrepo_c /var/tmp/patch         # repodata/ を作る
$ ls /var/tmp/patch/repodata          # できたメタデータを確認する
```

検証環境での実測です。

```text
Directory walk started
Directory walk done - 4 packages
Temporary output repo path: closure/.repodata/
Preparing sqlite DBs
Pool started (with 5 workers)
Pool finished
```

**rpm を追加したら作り直します。**

```bash
$ createrepo_c --update /var/tmp/patch   # 差分だけ更新する（速い）
```

**リポジトリにする利点**

| 利点 | 内容 |
|:--|:--|
| **依存解決が効く** | `dnf install パッケージ名` で、必要なものだけが選ばれる |
| **`repoclosure` で検査できる** | 足りない依存を機械的に見つけられる |
| **順序を気にしなくていい** | `rpm -Uvh` と違い、インストール順を dnf が決めてくれる |

---

## 転送と検証

**持ち込む前後で、中身が変わっていないことを確かめます。**

```bash
$ cd /var/tmp/patch && sha256sum *.rpm > SHA256SUMS   # ① 転送元でハッシュを取る
$ tar czf /tmp/patch-20260929.tar.gz -C /var/tmp patch   # ② まとめる
```

```bash
$ tar xzf /tmp/patch-20260929.tar.gz -C /var/tmp   # ③ 転送先で展開する
$ cd /var/tmp/patch && sha256sum -c SHA256SUMS     # ④ ハッシュを突き合わせる
```

検証環境での実測です。

```text
appx-1.0-1.noarch.rpm: OK
libbar-1.0-1.noarch.rpm: OK
libbaz-1.0-1.noarch.rpm: OK
libfoo-2.0-1.noarch.rpm: OK
```

**次に GPG 署名を確かめます。**

```bash
$ rpm -K /var/tmp/patch/*.rpm         # 署名とハッシュを確認する
```

| 出力 | 判定 |
|:--|:--|
| **`digests signatures OK`** | **正しい。これが本来の姿** |
| **`digests OK`** | **署名されていない**。出どころを確認する |
| **`digests SIGNATURES NOT OK`** | **署名はあるが鍵が未取り込み**。`rpm -Kv` で `NOKEY` と出る。**鍵を取り込んでやり直す** |
| **`DIGESTS ... NOT OK`**（大文字） | **壊れている。入れてはいけない** |

**鍵が未取り込みなら先に入れます。**

```bash
$ rpm -qa gpg-pubkey                  # 取り込み済みの鍵を確認する
$ sudo rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release   # 鍵を取り込む
```

> **`--nogpgcheck` で逃げないでください。**
> 脆弱性対応のために持ち込む rpm こそ、**改ざんされていないことの確認が要ります。**

---

## 参考リンク

- [Red Hat — Managing software with the DNF tool (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index)
- [Red Hat — How to use dnf/yum to download a package without installing it](https://access.redhat.com/solutions/10154)
- [DNF — Changes in DNF CLI compared to YUM](https://dnf.readthedocs.io/en/latest/cli_vs_yum.html)
- [DNF5 — download コマンド](https://dnf5.readthedocs.io/en/latest/commands/download.8.html)
- [dnf-plugins-core — reposync / repoclosure / download](https://dnf-plugins-core.readthedocs.io/en/latest/)
- [createrepo_c](https://github.com/rpm-software-management/createrepo_c)
- [man 8 dnf](https://man7.org/linux/man-pages/man8/dnf.8.html)

---

[← 全体の目次にもどる](../README.md)
