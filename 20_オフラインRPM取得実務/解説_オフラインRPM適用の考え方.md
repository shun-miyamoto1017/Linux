# RHEL 7.9：オフラインRPM適用の考え方

| | |
|:--|:--|
| **学習の順番** | 実務 ★★★★★ |
| **Ping-t の範囲** | 範囲外（**業務の実作業から作ったノート**） |
| **業務での使いどころ** | **手順書の「なぜそうするのか」をまとめた解説。**とくに**なぜ足りないものの判定を対象サーバーでしかできないのか**、**なぜ下見をまとめて1回だけやるのか**、**どこで黙って取りこぼすのか**。手順を打つ前に一度読んでおくと、エラーが出たときに自分で切り分けられます。 |

> **このフォルダのノート一覧**
>
> | 種類 | ノート | 何が書いてあるか |
> |:--|:--|:--|
> | **解説** | **このノート（オフラインRPM適用の考え方）** | **なぜこの手順になるのか。**判定を対象サーバーでしかできない理由、NEVRA と版比較、下見の仕組み、落とし穴8件、`LANG=C` の有効範囲 |
> | 解説 | [下見ログの読み方](./解説_下見ログの読み方.md) | `yum install --assumeno` のログを1行ずつ読む。`Error:` の塊、計画の表、`Transaction Summary`、よくある読み違い |
> | 解説 | [ローカルリポジトリの仕組み](./ローカルリポジトリの仕組み.md) | `createrepo` と目次、`clean all`、**署名検証の落とし穴**、エラータ、yum と dnf の違い |
> | 解説 | [依存チェックスクリプトの読み方](./依存チェックスクリプトの読み方.md) | `check_deps.sh` を1ブロックずつ解説 |
> | 手順書 | [不足依存RPMの取得と適用（yum-utils あり）](./手順書_RHEL7_不足依存RPM取得と適用_yum-utilsあり.md) | 取得機に `yumdownloader` / `repoquery` が**ある**場合の通し手順（下見 → 取得 → テスト → 適用） |
> | 手順書 | [不足依存RPMの取得と適用（yum-utils なし）](./手順書_RHEL7_不足依存RPM取得と適用_yum-utilsなし.md) | 取得機に `yumdownloader` / `repoquery` が**ない**場合の通し手順（標準の `yum` だけ） |
> | 手順書 | [手順書 RHEL 7.9 openssh の更新](./手順書_RHEL7_openssh更新.md) | ローカルリポジトリから openssh を更新する通し手順 |
> | 手順書 | [手順書 RHEL 8 以降 openssh の更新](./手順書_RHEL8以降_openssh更新.md) | `dnf` 版の同じ手順 |
> | 手順書 | [手順書 RHEL 7.9 依存RPMの不足対応](./手順書_RHEL7_依存不足対応.md) | ローカルリポジトリを作って「確認 → 追加」を繰り返す方式 |
> | 手順書 | [手順書 RHEL 8 以降 依存RPMの不足対応](./手順書_RHEL8以降_依存不足対応.md) | `dnf` 版の同じ手順 |

> **公式ドキュメントの確認日: 2026-10-14。**
> **コマンドの実在とメッセージの文字列は、Yum 3 系・Yum Utils・RPM 4.11 系の公式 man と開発元ソースで確認**しています。
> **RHEL 7.9 の実機では未実行です。**出力例は説明用で、値は架空です。

---

## 目次

- [1. 全体像](#1-全体像)
- [2. なぜ判定を対象サーバーでしかできないのか](#2-なぜ判定を対象サーバーでしかできないのか)
  - [2.1 「足りない」は、そのサーバーの中身との比較](#21-足りないはそのサーバーの中身との比較)
  - [2.2 具体例：取得機で判定すると取りこぼす](#22-具体例取得機で判定すると取りこぼす)
  - [2.3 だからこうする](#23-だからこうする)
- [3. RPM・依存関係・リポジトリ](#3-rpm・依存関係・リポジトリ)
- [4. NEVRA と版の比較](#4-nevra-と版の比較)
  - [4.1 Epoch がいちばん強い](#41-epoch-がいちばん強い)
  - [4.2 Release の `el7_9` が大事](#42-release-の-el79-が大事)
  - [4.3 バージョン番号で脆弱性を判定しない](#43-バージョン番号で脆弱性を判定しない)
- [5. 下見（`install --assumeno`）が何をしているか](#5-下見install---assumenoが何をしているか)
  - [5.1 1個ずつ下見してはいけない理由](#51-1個ずつ下見してはいけない理由)
  - [5.2 下見では社内リポジトリを有効にしない](#52-下見では社内リポジトリを有効にしない)
- [6. 落とし穴の一覧](#6-落とし穴の一覧)
  - [6.1 渡した RPM が黙って計画から外れる](#61-渡した-rpm-が黙って計画から外れる)
  - [6.2 `Exiting on user command` は成功](#62-exiting-on-user-command-は成功)
  - [6.3 `--assumeno` が効かない構成がある](#63---assumeno-が効かない構成がある)
  - [6.4 `tsflags` の打ち間違いは致命的](#64-tsflags-の打ち間違いは致命的)
  - [6.5 `Excluding` は既定では出力されない](#65-excluding-は既定では出力されない)
  - [6.6 `--assumeno` で中止すると `/tmp` にファイルが残る](#66---assumeno-で中止すると-tmp-にファイルが残る)
  - [6.7 `tsflags=test` は履歴に残らない](#67-tsflags=test-は履歴に残らない)
  - [6.8 取得機にすでに入っている依存は落ちない](#68-取得機にすでに入っている依存は落ちない)
- [7. `export LANG=C` の有効範囲](#7-export-lang=c-の有効範囲)
  - [7.1 `exit` すれば元に戻る](#71-exit-すれば元に戻る)
  - [7.2 確認と戻し方](#72-確認と戻し方)
  - [7.3 `LC_ALL` と `sudo` に注意](#73-lcall-と-sudo-に注意)
- [8. 条件から提供元を探すコツ](#8-条件から提供元を探すコツ)
  - [8.1 条件はそのまま、クォートで囲んで渡す](#81-条件はそのままクォートで囲んで渡す)
  - [8.2 カッコは外さない。ワイルドカードにする](#82-カッコは外さないワイルドカードにする)
  - [8.3 よくある対応表（RHEL 7）](#83-よくある対応表rhel-7)
  - [8.4 選ぶときのコツ](#84-選ぶときのコツ)
- [9. よく出るメッセージ早見表](#9-よく出るメッセージ早見表)
- [10. やってはいけないこと](#10-やってはいけないこと)
- [11. 根拠と検証範囲](#11-根拠と検証範囲)
  - [11.1 参照した資料](#111-参照した資料)
  - [11.2 開発元ソースで確認した挙動](#112-開発元ソースで確認した挙動)
  - [11.3 未検証のまま残ること](#113-未検証のまま残ること)
- [変更履歴](#変更履歴)

---

## 1. 全体像

**やりたいこと**：オフラインの RHEL 7.9 に、CVE 対応の RPM を当てたい。
**困ること**：当てたい RPM は、たいてい**別の RPM を必要とします**（依存関係）。その足りない RPM を集めてこないといけません。

| 呼び名 | 役割 | なぜ必要か |
|:--|:--|:--|
| **対象サーバー（C）** | **判定と適用** | **足りないものを決められるのはここだけ**（第2章） |
| **取得機（B）** | **RPM を取ってくるだけ** | 対象サーバーは社内リポジトリにつながらないから |
| 手元の Windows | 運ぶ・保管する | 両者を直接つなげないことが多いから |

```text
手元 ──[RPMを送る]──▶ 対象サーバー C
                         │ 下見して「足りない条件」を出す  ← ★判定はここだけ
                         ▼
手元 ◀─[条件の一覧]──────┘
  │
  └──[条件の一覧]──▶ 取得機 B
                         │ 条件を提供する RPM を取ってくる
                         ▼
手元 ◀─[取得したRPM]─────┘
  │
  └──[取得したRPM]──▶ 対象サーバー C
                         │ 追加して再下見 → 閉じるまで繰り返す
                         │ トランザクションテスト → 適用
```

**手順書は2本あります。**

| 取得機の状態 | 使う手順書 |
|:--|:--|
| `yumdownloader` / `repoquery` が**ある** | [不足依存RPMの取得と適用（yum-utils あり）](./手順書_RHEL7_不足依存RPM取得と適用_yum-utilsあり.md) |
| **ない** | [不足依存RPMの取得と適用（yum-utils なし）](./手順書_RHEL7_不足依存RPM取得と適用_yum-utilsなし.md) |

---

## 2. なぜ判定を対象サーバーでしかできないのか

**これがこのノートでいちばん大事な話です。**

### 2.1 「足りない」は、そのサーバーの中身との比較

`yum` が「依存が足りない」と言うとき、比べている相手は**そのサーバーに入っているパッケージ（rpmdb）**です。

```text
当てたい RPM が要求する条件  ─比較─▶  そのサーバーに入っているもの＋同時に渡す RPM
                                       └─ ここが サーバーごとに違う
```

**取得機と対象サーバーは、入っているパッケージが違います。**
同じ RHEL 7.9 でも、入れたパッケージ・当ててきたパッチ・用途が違えば中身は別物です。

### 2.2 具体例：取得機で判定すると取りこぼす

`openssh-server` が `openssl-libs >= 1:1.0.2k-26` を要求しているとします。

| | 入っている版 | 条件を満たすか | 下見の結果 |
|:--|:--|:--|:--|
| **取得機（B）** | `1:1.0.2k-26` | ✅ 満たす | **「足りない」と出ない** |
| **対象サーバー（C）** | `1:1.0.2k-21` | ❌ 満たさない | **足りない** |

取得機で下見すると「足りないものは無い」と出ます。**`openssl-libs` は取得されません。**
対象サーバーへ持っていって初めて足りないと分かり、**往復が1回増えます。**

**これは `yum ... --downloadonly install *.rpm` で一括取得する場合も同じです。**
`--downloadonly` は**そのサーバーの計画に入ったものだけ**を落とすので、
**取得機にすでに入っている依存は落ちません。**

> **取得機の版が要求より「古い」場合は、更新として計画に入るので落ちます。**
> 取りこぼすのは **取得機がすでに条件を満たしているとき**だけです。
> だからこそ「たまたま動いた」ことがあり、**気づきにくい**落とし穴です。

### 2.3 だからこうする

- **足りないものを決めるのは、対象サーバーの下見だけ。**
- **取得機は「この条件を提供する RPM をください」と言われたものを取ってくるだけ。**
- 対象サーバーへ持ち帰ったら、**もう一度下見して閉じたことを確認する。**

> **取得機を対象サーバーの複製にできるなら、この問題はほぼ消えます。**
> 同じイメージ・同じ構成から作った検証機を取得機にするのが、いちばん確実です。
>
> `yum --installroot` に対象サーバーの rpmdb の写しを与えて取得機上で模擬する方法もありますが、
> releasever やリポジトリ設定も絡むため**設計と検証が別途必要**です。**未検証**なので手順書では採りません。

---

## 3. RPM・依存関係・リポジトリ

| 言葉 | 意味 |
|:--|:--|
| **RPM** | プログラム・設定ファイル・依存条件が1つにまとまった配布ファイル |
| **依存関係** | 「このプログラムを動かすには別の機能が必要」という条件 |
| **リポジトリ** | RPM 本体と**目次（`repodata/`）**を置いた場所 |
| **提供（Provides）** | その RPM が「与える」機能の名前 |
| **要求（Requires）** | その RPM が「欲しがる」機能の名前 |

```text
更新したいRPM
  ├─ libexample.so.1()(64bit) が必要
  │     └─ example-libs RPM がその機能を「提供」している
  └─ example-common = 1.2-3.el7 が必要
        └─ 同じバージョンの example-common RPM が必要
```

> **`libexample.so.1()(64bit)` は RPM のファイル名ではありません。RPM が「提供する機能の名前」です。**
> エラーの文字列をそのままファイル名だと思って探しても見つかりません。
> **「この機能を提供しているのはどの RPM か」を調べる**のが、手順書の第7章です。

**調べるコマンドの違い**

| コマンド | 調べる相手 |
|:--|:--|
| `rpm -qp ファイル` | **RPM ファイルそのもの**（まだ入れていないもの） |
| `rpm -q 名前` | **そのサーバーに入っているもの** |
| `rpm -q --whatprovides '条件'` | **そのサーバーで**その条件を提供しているもの |
| `repoquery --whatprovides '条件'` | **リポジトリの中で**その条件を提供しているもの |
| `yum provides '条件'` | 同上（`yum-utils` が無くても使える） |

---

## 4. NEVRA と版の比較

RPM を正確に指すときは **NEVRA**（Name・Epoch・Version・Release・Architecture）を使います。

**例：`openssl-libs-1:1.0.2k-26.el7_9.x86_64`**

| 部分 | 意味 |
|:--|:--|
| `openssl-libs` | **N**ame（名前） |
| `1` | **E**poch（エポック） |
| `1.0.2k` | **V**ersion（バージョン。上流のソフトのバージョン） |
| `26.el7_9` | **R**elease（リリース。Red Hat がパッケージを作り直した回数と対象OS） |
| `x86_64` | **A**rchitecture（アーキテクチャ） |

### 4.1 Epoch がいちばん強い

**比較は Epoch → Version → Release の順**で、**Epoch が違えば、それだけで勝負がつきます。**

| 比較 | 結果 |
|:--|:--|
| `1:1.0.2k-21` と `1:1.0.2k-26` | Epoch 同じ、Version 同じ → **Release で比較して 26 が新しい** |
| `0:2.0-1` と `1:1.0-1` | **Epoch が違うので 1: のほうが新しい**（Version は 1.0 < 2.0 でも関係ない） |

> **未設定の Epoch は通常 0 相当**で、**ファイル名には入りません。**
> `rpm -qp --qf '%{EPOCH}'` で `(none)` と出るのが「未設定」です。
> **ファイル名の文字の並びだけで「こっちが新しい」と判断してはいけません。**

### 4.2 Release の `el7_9` が大事

`26.el7_9` の **`el7_9`** は「RHEL 7.9 向け」という印です。
**`el8` や `el6` の RPM を対象サーバーに混ぜてはいけません。**
`rpm -E 'el%{rhel}'` で対象サーバーの記号を確認し、**一致するものだけ**を使います。

### 4.3 バージョン番号で脆弱性を判定しない

Red Hat は、上流の新しいバージョンに上げるのではなく、**修正だけを既存の版に取り込みます**（バックポート）。

> **だから「上流の 1.0.2u で直ったから 1.0.2k はダメ」とは言えません。**
> 判定は **RHSA（Red Hat のセキュリティ修正のお知らせ）に載っている NEVRA** と、
> **いま入っている NEVRA** を突き合わせて行います。
> 根拠：[Red Hat：Security Backporting Practice](https://access.redhat.com/security/updates/backporting)

---

## 5. 下見（`install --assumeno`）が何をしているか

手順書の下見はこの形です。

```bash
$ sudo yum --noplugins --disablerepo='*' --setopt=alwaysprompt=1 \
    install --assumeno ${RPM_DIR:?}/*.rpm \
    > $LOG_DIR/dryrun_01.txt 2>&1            # 全部まとめて1回だけ下見する
```

| 指定 | 何のため |
|:--|:--|
| `install` に**ファイルパス** | `yum` は**ファイル名を渡されるとローカルインストールとして扱う**（`yum.8` に明記）。`localinstall` は公式に「互換のため残しているだけ」とされている |
| **全部まとめて**渡す | 第5.1 のとおり |
| `--assumeno` | 確認に自動で「いいえ」と答える |
| `--setopt=alwaysprompt=1` | **確認を必ず出させる**（第6.3 の保険） |
| `--disablerepo='*'` | **リポジトリを使わない。**持ち込んだ RPM と、そのサーバーに入っているものだけで判定する |
| `--noplugins` | versionlock などプラグイン由来の制約を外す。**`yum.conf` の `exclude` は外れない** |
| `${RPM_DIR:?}` | 変数が空のときに `/*.rpm` へ化けるのを防ぐ |
| `sudo` | `yum install` は root でないと実行できない（`You need to be root to perform this command.`） |

### 5.1 1個ずつ下見してはいけない理由

**当てる RPM は、お互いの依存を満たし合っています。**

```text
まとめて渡した場合
  openssh-server ── 要求 ──▶ openssh-libs ──▶ 同じ一式の中にある → OK

1個ずつ渡した場合
  openssh-server ── 要求 ──▶ openssh-libs ──▶ 見えない → 「足りない」と出る（偽）
```

**98個を1個ずつ下見すると、98個ぶんのログに偽の不足が並びます。**
本当に足りないものがその中に埋もれて、見つけられません。**必ず `*.rpm` でまとめて渡します。**

### 5.2 下見では社内リポジトリを有効にしない

**社内リポジトリを有効にして下見すると、`yum` が足りない依存を勝手に補って計画を作ります。**
その結果 `Error: ... Requires:` は出ず、**`Exiting on user command` で正常終了します。**

> 根拠：`yum.8` の localinstall の項に
> *"If required the enabled repositories will be used to resolve dependencies"* とあります。

これを「依存がそろった」と読むと、**補われた RPM を持ち帰らないまま先へ進んでしまいます。**
**下見はリポジトリ無し。リポジトリを使うのは「取得」のときだけ**です。

---

## 6. 落とし穴の一覧

### 6.1 渡した RPM が黙って計画から外れる

**いちばん見落としやすい落とし穴です。**`yum` は次の場合、**警告を1行出すだけでその RPM を計画から外します。**

| ログに出る文字列 | 起きていること | 既定の出力レベルで出るか |
|:--|:--|:--|
| `Cannot open: ... Skipping.` | RPM ファイルを読めなかった（壊れ・権限） | 出る |
| `... does not update installed package.` | **同じ版か新しい版がすでに入っている** | 出る |
| `Cannot add package ... Not a compatible architecture:` | アーキテクチャが合わない | 出る |
| `Cannot install package ... It is obsoleted by installed package ...` | 入っているパッケージに置き換えられている | 出る |
| `Excluding ...` | `yum.conf` の `exclude` に該当した | **出ない**（6.5） |

**外された分を除いた残りで依存が閉じると、ログの最後は `Exiting on user command` になります。**
つまり**「依存OK」に見えるのに、CVE 対応 RPM の一部は何も確認されていない**状態が起こります。

**見つけ方**：`Examining` の数と `Marking` の数を比べます。

```bash
$ grep -c 'Examining ' $LOG_DIR/dryrun_01.txt        # 読み込まれた RPM の数
$ grep -c 'Marking '   $LOG_DIR/dryrun_01.txt        # 計画に入った RPM の数
```

**一致すれば外されたものは無し。**違えばその差が外された数です。

### 6.2 `Exiting on user command` は成功

**`--assumeno` で「いいえ」と答えた正常な中止**で、**終了コードは 1** になります。
終了コードだけ見て「失敗した」と思わないでください。

> **`Operation aborted.` は RHEL 8 以降の `dnf` の表示で、RHEL 7 の `yum` では出ません。**
> 文字で探すときは、版による大文字小文字の違いを避けて `grep -i 'exiting on user'` が確実です。

### 6.3 `--assumeno` が効かない構成がある

`yum` は「確認を出すかどうか」を先に判断します。**確認を出さないと決めた場合、`--assumeno` は働きません。**

| 設定 | 起きること |
|:--|:--|
| `assumeyes=1` | **確認を出さずに実行する。**`--assumeno` 以前の問題 |
| `alwaysprompt=0` | 計画が「指定したものだけ」の場合に**確認を出さない**ことがある |

**だから作業前に設定を見ます。**

```bash
$ grep -H -E '^[[:space:]]*(exclude|includepkgs|alwaysprompt|assumeyes|assumeno|skip_broken|localpkg_gpgcheck|tsflags)' \
    /etc/yum.conf /etc/yum.repos.d/*.repo    # 除外や自動応答の設定を確認する
```

**手順書では保険として `--setopt=alwaysprompt=1` を必ず付けています。**

### 6.4 `tsflags` の打ち間違いは致命的

トランザクションテストは `--setopt=tsflags=test` で実更新を防いでいます。
**ところが `yum` は、不正な `tsflags` を見つけても `Invalid tsflag in config file` を出すだけで処理を続けます。**

> **`test` を打ち間違えて `y` を入れると、本当に更新されます。**
> **確認画面で `y` を入れる前に、画面の上に `Invalid tsflag` が出ていないか必ず見てください。**

### 6.5 `Excluding` は既定では出力されない

`yum.conf` の `exclude` で外された RPM の `Excluding ...` は、**debug レベルで出力**されます。
**`debuglevel` の既定は 2 なので、画面にもログにも出ません。grep しても見つかりません。**

> **だから `exclude` は、設定ファイルのほうを先に確認します**（6.3 のコマンド）。
> `exclude` があった場合は、下見に **`-d 3`** を足して実行すると `Excluding` が表示されます。

### 6.6 `--assumeno` で中止すると `/tmp` にファイルが残る

**依存解決まで進めた回**は、`yum` が計画を自動保存して案内してきます。

```text
Your transaction was saved, rerun it with:
 yum load-transaction /tmp/yum_save_tx.2026-10-14.10-30.AbCdEf.yumtx
```

> **この案内に従って `yum load-transaction` を実行してはいけません。実更新になります。**
> `Error: ... Requires:` で終わった回は作られません（依存解決が成功した回だけ保存されます）。

### 6.7 `tsflags=test` は履歴に残らない

`tsflags` に `test` が入っていると、`yum` は**履歴の記録そのものを行いません。**
**`yum history` に出るのは、実際に適用したときだけ**です。テストの実施記録はログファイルで残します。

### 6.8 取得機にすでに入っている依存は落ちない

第2章のとおりです。`yumdownloader --resolve` も `yum --downloadonly` も、
**「そのサーバーの計画に入ったもの」しか落としません。**

---

## 7. `export LANG=C` の有効範囲

手順書では、メッセージを英語にそろえるために `export LANG=C` を使います。

### 7.1 `exit` すれば元に戻る

**`export` が効くのは、そのログインセッション（そのシェルと、そこから起動したコマンド）の中だけ**です。
**ディスク上のファイルは一切書き換えません。**接続を閉じればシェルごと消えます。

次にログインしたときに `ja_JP.UTF-8` に戻るのは、**ログインのたびにロケールの設定が読み直される**からです。

| 場所 | 役割 |
|:--|:--|
| `/etc/locale.conf` | **システム全体**のロケール設定 |
| `$HOME/.i18n` | **ユーザーごと**のロケール設定 |
| `/etc/profile.d/lang.sh` | 対話シェルの起動時に、上の2つを（この順で）読み込んで `LANG` を設定する |

> **ただし `LANG` がすでに設定されている場合、`lang.sh` はその値をそのまま残します。**
> SSH クライアント側がロケールを送ってくる構成だと、ログイン直後から別の値になっていることがあります。
> 根拠：[Red Hat：How to change system locale on RHEL7?](https://access.redhat.com/node/974273)

### 7.2 確認と戻し方

```bash
$ echo $LANG                                 # 今のシェルの LANG
$ locale                                     # LANG と LC_* の一覧
$ cat /etc/locale.conf                       # システム全体の設定（書き換えない）
$ ls -l $HOME/.i18n                          # 個人設定の有無（無ければ No such file）
$ localectl status                           # systemd が見ているロケール
```

| 日本語に戻す方法 | 内容 |
|:--|:--|
| **`exit` して入り直す** | いちばん確実。`lang.sh` が読み直される |
| `export LANG=ja_JP.UTF-8` | その場のシェルだけ戻す |
| もう1本ターミナルを開く | 日本語の窓と英語の窓を並べて使える |

> **`~/.bashrc` や `~/.bash_profile` に `export LANG=C` を書かないでください。**恒久的な変更になります。
> **`localectl set-locale` や `/etc/locale.conf` の書き換えはシステム全体の構成変更**です。承認なしに行わないでください。

### 7.3 `LC_ALL` と `sudo` に注意

**優先順位は `LC_ALL` > `LC_MESSAGES` などの個別の `LC_*` > `LANG`** です。
**`LC_ALL` が設定されていると `LANG=C` は効きません。**`locale` で確認し、効かないときは `export LC_ALL=C` を使います。

**`sudo` の先に引き継がれるかは環境によります。**手順書の `yum` は `sudo` 越しに動くので、ここが効かないと英語になりません。

```bash
$ sudo printenv LANG                         # sudo 先の LANG を確認する
```

> `C` 以外が表示されたら、`sudo -E yum ...` のように `-E` を付けるか、`sudo env LANG=C yum ...` のようにコマンドごとに指定します。

---

## 8. 条件から提供元を探すコツ

### 8.1 条件はそのまま、クォートで囲んで渡す

```bash
$ repoquery --disablerepo='*' --enablerepo=$REPO_ID --show-duplicates \
    --whatprovides 'openssl-libs >= 1:1.0.2k-26'   # 条件を提供する RPM を探す
```

> **`Requires:` というラベル自体は入れません。**右側の条件だけを渡します。
> **必ずクォートで囲みます。**囲まないと **`>=` の `>` がリダイレクトとして解釈され**、
> カレントディレクトリに `=` というファイルができ、版の条件が渡りません。
> **名前だけに削るのもいけません。**`openssl-libs` だけだと**版の条件を満たさないものまで出ます。**

### 8.2 カッコは外さない。ワイルドカードにする

**`libcrypto.so.10()(64bit)` は、カッコまで含めて1つの「提供する機能の名前」**です。
検索は完全一致なので、**カッコを外した `libcrypto.so.10` では一致しません。**

| 条件の形 | 見つからないときの対処 |
|:--|:--|
| `libcrypto.so.10()(64bit)` | **末尾を `*` にする** → `'libcrypto.so.10*'` |
| `libc.so.6(GLIBC_2.14)(64bit)` | **真ん中のカッコの中身だけ外す** → `'libc.so.6()(64bit)'`（末尾の `()(64bit)` は残す） |
| ファイルそのもの | **パスで探す** → `'*/libcrypto.so.10'` |

### 8.3 よくある対応表（RHEL 7）

| 条件の例 | 提供している RPM |
|:--|:--|
| `libcrypto.so.10()(64bit)` / `libssl.so.10()(64bit)` | `openssl-libs` |
| `libk5crypto.so.3()(64bit)` / `libkrb5.so.3()(64bit)` | `krb5-libs` |
| `libz.so.1()(64bit)` | `zlib` |
| `libselinux.so.1()(64bit)` | `libselinux` |
| `libc.so.6()(64bit)` / `libpthread.so.0()(64bit)` | `glibc` |
| `libgcc_s.so.1()(64bit)` | `libgcc` |
| `libstdc++.so.6()(64bit)` | `libstdc++` |
| `libcurl.so.4()(64bit)` | `libcurl` |
| `libxml2.so.2()(64bit)` | `libxml2` |

> **この表は目安です。**必ず検索で**実際のリポジトリの中身**を確認してください。

### 8.4 選ぶときのコツ

- **対象サーバーと同じ `el7`** が入っているもの
- 条件が `()(64bit)` 付きなら **`x86_64` 版**
- **要求を満たす版で、今回の CVE と同じ時期のもの**
- **同じエラータ（RHSA）の仲間はまとめて取る**（`openssl` と `openssl-libs` など）。
  **仲間どうしは同じ版を要求し合うことが多い**ので、まとめて取るとやり直しが減ります
- **`Protected multilib versions`** が出たら、**i686 版も同じ版で**取得する

---

## 9. よく出るメッセージ早見表

| 表示 | 意味 | 次にやること |
|:--|:--|:--|
| `Exiting on user command` | `--assumeno` による**正常な中止**（終了コード1） | 異常ではない。計画本文を読む |
| `Error: Package: ...` ＋ `Requires: xxx` | 依存が足りない | 条件を抜き出して取得機で検索する |
| `Installed: NEVRA (@リポジトリ)` | いまそのサーバーに入っている版 | `Requires:` と見比べて、なぜ足りないかを見る |
| `Available: NEVRA (リポジトリ名)` | リポジトリにはこの版がある | その版を取ってくれば解決する |
| `Not found` | 提供するものがどこにも無い | 取得元の同期内容・権利を確認 |
| `xxx = 1.2-3.el7` | **版が完全一致**する依存 | 関連 RPM を同じ版でそろえる |
| `Protected multilib versions` | x86_64 と i686 の版ずれ | **両アーキテクチャを同じ版で**取得する |
| `conflicts with file from package` | ファイルの所有・内容が競合 | 両 RPM の製品・版・提供元を確認 |
| `does not update installed package.` | 同版・旧版が入っていて更新にならない | **計画から外れている。**当てる必要があるか判断する |
| `Cannot open: ... Skipping.` | RPM を読めず計画から外された | ハッシュ・権限・破損を確認し、運び直す |
| `Not a compatible architecture` | アーキテクチャ違い | `x86_64` / `i686` / `noarch` を確認 |
| `It is obsoleted by installed package` | 入っているものに置き換えられている | 当てる必要があるか判断する |
| `Excluding ...` | `exclude` に該当（**既定では出ない**） | 設定ファイルを確認する（6.5） |
| `Skipped (dependency problems)` | `skip_broken` で飛ばされた | **0 件でなければ中断** |
| `No package ... available` | 指定版が見えない | リポジトリID・同期内容・版指定・権利を確認 |
| `Cannot find a valid baseurl` | 取得元・接続・認証の問題 | **依存不足と混同しない** |
| `Nothing to do` | やることが無い | 取り違え、`el7` 以外の混入、適用済みを確認 |
| `Existing lock` | 別の yum/rpm が動いている可能性 | 実行状況を確認。**ロックファイルを消さない** |
| **`Invalid tsflag in config file`** | **`tsflags` が効いていない** | **そのまま進めると実更新。**中止して打ち直す |
| `Transaction test succeeded` | テスト成功 | 適用へ |
| `exiting because "Download Only" specified` | ダウンロードだけして正常終了 | 落ちたファイルを確認する |
| **`Complete!`** | **適用が正常に終わった** | 適用後の確認へ |
| `Failed` | **失敗したものがある** | **完了にしない** |
| `This system is not registered ...` | サブスクリプション未登録の案内 | **無視してよい** |

**ログの構造と、1行ずつの読み方**は [下見ログの読み方](./解説_下見ログの読み方.md) にあります。

---

## 10. やってはいけないこと

| やってはいけないこと | 理由 |
|:--|:--|
| **取得機で「足りない」を判定する** | 入っているものが違う。**取りこぼす**（第2章） |
| **RPM を1個ずつ下見する** | 仲間どうしが満たし合う依存を「足りない」と誤判定する（5.1） |
| **下見で社内リポジトリを有効にする** | 足りない依存が勝手に補われ、**正常終了に見える**（5.2） |
| **`--setopt=tsflags=test` を省く／打ち間違える** | **本当に更新される。**`Invalid tsflag` を必ず確認（6.4） |
| **`yum load-transaction` を実行する** | `--assumeno` の案内に従うと**実更新になる**（6.6） |
| **`--downloadonly` に `--assumeno` を足す** | 中止扱いになって**何も落ちない** |
| **`-y` を付ける** | 計画を見ずに進めてしまう |
| **`--nodeps` / `--force` / `--ignorearch`**（`rpm` のオプション） | 依存関係やアーキテクチャの判定を無視してシステムを壊す |
| **`--skip-broken`** | 問題のあるパッケージを**黙って計画から外す。**CVE 対応の抜けが隠れる |
| **`--nogpgcheck`** | 検証を飛ばす。先へ進めるための道具にしない |
| **`rpm -Uvh *.rpm`** | yum の依存解決・運用設定と評価が違う。**カーネルの installonly 扱いも異なる** |
| **取得したものをまとめて `mv` する** | 対象サーバーに要らない依存まで当ててしまう |
| **ログのファイル名を使い回す** | 前回の証跡が消える |
| **転送モードを「テキスト」にする** | RPM とアーカイブが壊れる |
| **`~/.bashrc` に `export LANG=C` を書く** | 恒久的な変更になり、他の作業にも影響する（7.2） |
| **`localectl set-locale` を実行する** | システム全体の構成変更（7.2） |
| **ロックファイルを消す** | 別の処理が動いている可能性がある |
| **対象サーバーに `.repo` を作る／道具を入れる** | この手順では不要な構成変更 |

---

## 11. 根拠と検証範囲

### 11.1 参照した資料

| 資料 | 確認した内容 |
|:--|:--|
| [Red Hat：RHEL 7 System Administrator's Guide — Yum](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-yum) | RHEL 7 の Yum、ローカル RPM の扱い |
| [Yum開発元：yum(8)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.8) | **`install` にファイル名を渡すとローカルインストールになること**、**有効なリポジトリで依存が解決されること**、`localinstall` が互換目的であること、`--assumeno`、`--downloadonly` / `--downloaddir`、`provides`、`--showduplicates`、`reinstall`、`check`、`history`、`-d`（debuglevel） |
| [Yum開発元：yum.conf(5)](https://raw.githubusercontent.com/rpm-software-management/yum/master/docs/yum.conf.5) | `tsflags`（`test` を含む）、`alwaysprompt`（既定1）、`assumeno`、`assumeyes`、`exclude`、`skip_broken`、`localpkg_gpgcheck`（既定0）、`debuglevel`（既定2） |
| [Yum Utils開発元：yumdownloader(1)](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/yumdownloader.1) | `--destdir`、`--resolve` |
| [Yum Utils開発元：repoquery(1)](https://raw.githubusercontent.com/rpm-software-management/yum-utils/master/docs/repoquery.1) | `--whatprovides`、`--show-duplicates` |
| [RPM開発元：RPM 4.11系 rpm(8)](https://raw.githubusercontent.com/rpm-software-management/rpm/rpm-4.11.x/doc/rpm.8) | `-qp`、`-qa`、`--qf`、`-R`、`--provides`、`--last`、`-K` |
| [Red Hat：How to change system locale on RHEL7?](https://access.redhat.com/node/974273) | `/etc/locale.conf`、`$HOME/.i18n`、`/etc/profile.d/lang.sh`、**`LANG` が設定済みなら上書きしない**こと |
| [Red Hat：Identify packages that will require a system reboot after an update](https://access.redhat.com/node/27943) | RHEL 7 では `needs-restarting` が `yum-utils` に含まれ、`-r / --reboothint` があること |
| [Red Hat：Security Backporting Practice](https://access.redhat.com/security/updates/backporting) | バックポートと版番号での判断 |

### 11.2 開発元ソースで確認した挙動

**man に書かれていない、または man だけでは分からない挙動は、Yum 3 系と RPM 4.11 系のソースで確認しました。**

- `--assumeno` 時の表示が **`Exiting on user command`** で、**終了コードが 1** になること
- **`alwaysprompt=0` だと、確認を出さない計画で `--assumeno` が働かない**こと
- 不正な `tsflags` は **`Invalid tsflag in config file` を出すだけで処理が続く**こと
- `tsflags=test` のとき RPM 側の処理が書き込み前に戻り、**`yum history` に記録されない**こと
- `Cannot open: ... Skipping.` / `does not update installed package.` / `Not a compatible architecture` /
  `It is obsoleted by installed package` で **RPM が黙って計画から外れる**こと
- **`Excluding` は debug レベルで出力されるため、既定（`debuglevel=2`）では出ない**こと
- 計画表の見出しに **`Obsoleting` が無い**こと（置き換えは `Removing` と行中の `replacing`）
- 適用完了時の見出し（`Installed` / `Dependency Installed` / `Updated` / `Dependency Updated` /
  `Removed` / `Dependency Removed` / `Replaced` / `Failed` / `Skipped (dependency problems)`）と **`Complete!`**
- `--downloadonly` が**確認プロンプトを出さず**、`exiting because "Download Only" specified` で終わること
- `--downloadonly` の取得先指定（`--downloaddir`）が、`yumdownloader --destdir` と**同じ設定**であること
- **ローカルファイルはダウンロード対象から外れる**ため、`--downloadonly` で落ちるのは**リポジトリ由来のものだけ**であること
- `--assumeno` 中止時の `/tmp/yum_save_tx.*.yumtx` の自動保存が、**依存解決まで進んだ回だけ**であること
- `yum install` が root を要求すること（`You need to be root to perform this command.`）
- `rpm -Kv` の行末の語が `OK` / `BAD` / `NOKEY` / `NOTRUSTED` / `UNKNOWN` で、
  **`NOT OK` は `-v` なしの要約行の表記**であること

### 11.3 未検証のまま残ること

> **RHEL 7.9 の実機では未実行です。**出力例は説明用で、値（版・件数・サイズ）は架空です。
>
> - RHEL 7.9 同梱版（`yum-3.4.3-168` など）と開発元 master の挙動差
> - `Exiting on user command` の大文字小文字（版による可能性があるため `grep -i` を推奨）
> - `tee` 経由での確認画面の見え方
> - `needs-restarting` の終了コードの意味
> - `yum provides` に版付きの条件を渡したときの挙動（ソース上は解釈されるが実機未確認）
> - `subscription-manager` プラグインの副作用
> - WinSCP と TeraTerm の画面の文言（版や日本語化で変わります）
>
> **`access.redhat.com/solutions/` 配下の記事は、閲覧に Red Hat のサブスクリプションでのログインが必要**です。

---

## 変更履歴

| 日付 | 版 | 内容 |
|:--|:--|:--|
| 2026-10-14 | 1.0 | 初版。旧「RHEL7_CVE対応RPM99個_依存関係確認とオフライン更新準備.md」を**解説専用に作り直して改名**。手順は [yum-utils あり](./手順書_RHEL7_不足依存RPM取得と適用_yum-utilsあり.md) / [yum-utils なし](./手順書_RHEL7_不足依存RPM取得と適用_yum-utilsなし.md) の2本へ分離。**なぜ判定を対象サーバーでしかできないのか**、**1個ずつ下見してはいけない理由**、**下見でリポジトリを有効にしてはいけない理由**、落とし穴8件、`LANG=C` の有効範囲、条件から提供元を探すコツ、根拠と検証範囲を整理 |

---

[← 全体の目次にもどる](../README.md)
