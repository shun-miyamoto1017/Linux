# systemd 基本とユニットファイル

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / システムアーキテクチャ(主題101) — システムの起動 ／ Linux2 / システムの起動とLinuxカーネル(主題2.01) — システム起動のカスタマイズ |
| **業務での使いどころ** | **サービスの設定を読み解く／自作アプリを常駐サービスにする**。「なぜこの順番で起動するのか」を説明できるようになる |

> **このノートはユニットファイルの土台**（種類・名前・置き場所・`[Unit]` / `[Install]`・drop-in・ターゲット）を扱います。
> **`[Service]` セクションの書き方と自作サービスの手順**は
> [systemd Serviceセクションと自作サービス](./systemd_Serviceセクションと自作サービス.md)、
> コマンドの打ち方は [systemctl サービスの操作と確認](./systemctl_サービスの操作と確認.md)、
> 出力の読み方は [systemctl 結果画面の見方](./systemctl_結果画面の見方.md) にまとめています。

---

## 目次

- [まずこれだけ](#まずこれだけ)
- [systemdとsystemctlとユニットの関係](#systemdとsystemctlとユニットの関係)
- [ユニットの種類](#ユニットの種類)
- [ユニット名の読み方](#ユニット名の読み方)
- [ユニットファイルの置き場所と優先順位](#ユニットファイルの置き場所と優先順位)
- [ユニットファイルの構造](#ユニットファイルの構造)
- [Unitセクション](#unitセクション)
- [依存関係と起動順序](#依存関係と起動順序)
- [Serviceセクションは別ノートにある](#serviceセクションは別ノートにある)
- [Installセクションとenableの正体](#installセクションとenableの正体)
- [drop-inで設定を上書きする](#drop-inで設定を上書きする)
- [テンプレートユニット](#テンプレートユニット)
- [ターゲット](#ターゲット)
- [つまずきポイント](#つまずきポイント)
- [クラウド実務メモ](#クラウド実務メモ)
- [参考リンク](#参考リンク)

---

## まずこれだけ

| 用語 | 一言でいうと |
|:--|:--|
| **systemd** | **サービスを管理する本体**。PID 1 で動くプログラム |
| **systemctl** | **systemd に操作を依頼するコマンド** |
| **ユニット** | **systemd が管理する 1 つの対象**（サービス、マウント、タイマーなど） |
| **ユニットファイル** | **その対象をどう扱うかを書いた設定ファイル**（`.service` など） |

**最小のユニットファイル**

```ini
[Unit]
Description=My sample application

[Service]
ExecStart=/usr/local/bin/myapp

[Install]
WantedBy=multi-user.target
```

| セクション | 役割 |
|:--|:--|
| **`[Unit]`** | **何なのか・他のユニットとどういう関係か** |
| **`[Service]`** | **どう動かすか**（service ユニット専用） |
| **`[Install]`** | **`enable` したときにどこへ結び付けるか** |

**3 つの設定だけは必ず押さえます**

```text
ExecStart=  … 何を実行するか
Type=       … いつ「起動完了」と判断するか
Restart=    … 落ちたときどうするか
```

---

## systemdとsystemctlとユニットの関係

### systemd

**systemd は、Linux の起動処理やサービスを管理するプログラム**です。
カーネルが最初に起動するプロセスとして、**PID 1** で動きます。

```text
Linuxカーネル
    ↓ 最初のプロセスとして起動する
systemd（PID 1）
    ↓ ユニットファイルの設定に従う
SSH・Webサーバ・DBなどを起動・管理する
```

```bash
$ ps -p 1 -o pid,comm,args           # PID 1 のプロセスを、PID・名前・コマンド全体で表示する
PID COMMAND         COMMAND
  1 systemd         /sbin/init
```

| 指定 | 意味 |
|:--|:--|
| `ps` | プロセスを表示する |
| `-p 1` | PID 1 だけに絞る |
| `-o` | 表示する列を指定する |
| `pid` / `comm` / `args` | PID / プログラム名 / 起動コマンド全体 |

**`/sbin/init` と表示されるのは、systemd への入り口（シンボリックリンク）だから**です。

```bash
$ readlink -f /sbin/init             # リンクをたどって実体のファイルを表示する
/usr/lib/systemd/systemd
```

**`readlink -f` はリンクを最後までたどって実体のパスを返すコマンド**です。

```bash
$ systemctl --version                # systemdのバージョンとビルド時の機能を表示する
systemd 255 (255.4-1ubuntu8.10)
+PAM +AUDIT +APPARMOR +SELINUX ...
```

先頭の `systemd 255` がバージョンです。
**`+` が付いている項目は「その機能を有効にしてビルドされている」**という意味です。

### systemctl

**systemctl は、systemd へ操作や確認を依頼するコマンド**です。
**systemctl 自身がサービスを起動するのではありません。**

```text
利用者
  ↓ systemctl で依頼する
systemd（PID 1）
  ↓ ユニットファイルを読んで実行する
サービスの起動・停止・状態管理
```

```bash
$ sudo systemctl start ssh.service   # ssh.service を起動するよう systemd へ依頼する
```

**この依頼は非同期です。** コマンドが戻ってきても、起動が完了しているとは限りません。
完了を待ちたいときは、状態を確認します（[systemctl ノート](./systemctl_サービスの操作と確認.md) 参照）。

### ユニット

**ユニットは、systemd が管理する 1 つの対象**です。
**プログラムそのものとユニットは別のもの**です。

```text
nginx
└─ 実際に動く Web サーバのプログラム

nginx.service
└─ nginx を systemd で管理するためのユニット（設定と状態のまとまり）
```

---

## ユニットの種類

**拡張子が種類を表します。** 実務で出会う順に並べています。

| 拡張子 | 何を管理するか | 例 |
|:--|:--|:--|
| **`.service`** | **サービス（常駐プログラム、単発処理）** | `nginx.service` |
| **`.target`** | **複数ユニットをまとめたグループ**。起動段階を表す | `multi-user.target` |
| **`.timer`** | **時刻やタイマーによる定期実行**（cron の systemd 版） | `logrotate.timer` |
| **`.socket`** | **ソケットで待ち受け、接続が来たらサービスを起動する** | `sshd.socket` |
| **`.mount`** | **ファイルシステムのマウント** | `home.mount` |
| **`.automount`** | **アクセスされたときに自動でマウントする** | `proc-sys-fs-binfmt_misc.automount` |
| `.swap` | スワップ領域 | `dev-sda3.swap` |
| `.path` | ファイルやディレクトリの変化を監視して起動する | `cups.path` |
| `.slice` | **プロセスを資源制限のグループに分ける** | `system.slice` |
| `.scope` | systemd の外で作られたプロセスの集まり | `session-1.scope` |
| `.device` | カーネルが認識したデバイス | `dev-sda.device` |

```bash
$ systemctl list-units --type=timer --no-pager      # timer ユニットの一覧を見る
$ systemctl list-units --type=mount --no-pager      # mount ユニットの一覧を見る
```

**`.mount` は `/etc/fstab` から自動生成されます。**
`fstab` に書いた行が、起動時に systemd によって `.mount` ユニットに変換されます
（`systemctl list-unit-files` では `generated` と表示されます）。

**変換しているのは `systemd-fstab-generator` です。**
ジェネレータと呼ばれる仕組みで、**起動のたびに `/etc/fstab` を読んでユニットを作り直します。**

| 拡張子 | 誰が作るか | 手で書くか |
|:--|:--|:--|
| **`.mount`** | **`systemd-fstab-generator` が `/etc/fstab` から生成** | **ふつうは書かない**。`/etc/fstab` を直す |
| **`.swap`** | 同じく **`systemd-fstab-generator`** が生成 | **ふつうは書かない** |
| **`.device`** | **`udev` がデバイスを認識したときに自動で作られる** | **書けない**（ファイルとして存在しない） |
| `.service` など | **パッケージまたは自分が置く** | 書く |

```bash
$ systemctl list-unit-files --type=mount --no-pager  # mount ユニットがどう登録されているか見る
$ systemctl cat home.mount                           # 生成された .mount の中身を見る（fstab の行が元になっている）
```

> **`/etc/fstab` を書き換えたあとに `systemctl daemon-reload` が要る**のは、この生成をやり直させるためです。

**`.timer` は cron の置き換え**

| | **cron** | **`.timer`** |
|:--|:--|:--|
| ログ | 自前でリダイレクト | **journal に自動で残る** |
| 実行結果の確認 | しにくい | **`systemctl status` で分かる** |
| 依存関係 | 書けない | **`After=` などが使える** |
| 起動時に取りこぼした分 | 実行されない | **`Persistent=true` で追いつける** |

---

## ユニット名の読み方

```text
myapp@web01.service
└─┬─┘ └─┬─┘ └──┬──┘
 名前  インスタンス  種類
```

| 部分 | 意味 |
|:--|:--|
| **名前** | ユニットの名前 |
| **`@` の後ろ** | **テンプレートユニットのインスタンス名**（後述） |
| **拡張子** | ユニットの種類 |

**`.service` は省略できます。** `systemctl status nginx` は `nginx.service` を指します。

**名前に使えない文字はエスケープされます**

マウントユニットのように、**パスがそのまま名前になる**ものがあります。

```bash
$ systemd-escape --path /var/log/myapp   # パスをユニット名の形に変換する
var-log-myapp

$ systemd-escape --path --unescape var-log-myapp   # 元のパスに戻す
/var/log/myapp
```

`/` は `-` に置き換わります。`/home` をマウントするユニットは `home.mount` になります。

---

## ユニットファイルの置き場所と優先順位

**同じ名前のファイルが複数の場所にある場合、優先度の高い 1 つだけが読まれます。**

| 優先度 | ディレクトリ | 用途 |
|:-:|:--|:--|
| **① 高** | **`/etc/systemd/system/`** | **管理者が作成・変更する設定**。ここが最優先 |
| ② | `/run/systemd/system/` | **実行中だけ有効な一時的な設定**。再起動で消える |
| ③ | `/usr/local/lib/systemd/system/` | 管理者が自分でインストールしたソフトの設定 |
| **④ 低** | **`/usr/lib/systemd/system/`** | **パッケージが提供する設定**。更新で上書きされる |

```text
/etc/systemd/system/      ← 人が書く場所（残る）
        ↑ 上書きする
/usr/lib/systemd/system/  ← パッケージが置く場所（更新で消える）
```

**`/usr/lib/systemd/system/` のファイルを直接編集してはいけません。**
パッケージを更新すると**書いた内容が消えます**。変更は `/etc` 配下か drop-in で行います。

**ディストリによっては `/lib/systemd/system/` と表示されます。**
最近の環境では `/lib` は `/usr/lib` へのシンボリックリンクなので、実体は同じです。

```bash
$ systemctl show nginx -p FragmentPath --value   # 実際に読み込まれたファイルの場所を表示する
/usr/lib/systemd/system/nginx.service

$ systemctl show nginx -p DropInPaths --value    # 適用されている drop-in の場所を表示する
/etc/systemd/system/nginx.service.d/override.conf
```

**ユーザー単位のユニット**もあります（`--user` で操作します）。

| ディレクトリ | 用途 |
|:--|:--|
| `~/.config/systemd/user/` | そのユーザーが作る設定 |
| `/etc/systemd/user/` | 管理者が全ユーザー向けに置く設定 |
| `/usr/lib/systemd/user/` | パッケージが提供するユーザー向け設定 |

### どのファイルが何を上書きしているか調べる

**優先度の高い場所に同名のファイルを置くと、低い場所のファイルは読まれなくなります。**
**「いま効いているのはどのファイルか」「何が隠れているか」をまとめて確かめるのが `systemd-delta`** です。

```bash
$ systemd-delta                                      # 上書き・拡張されているユニットを一覧する
[EXTENDED] /usr/lib/systemd/system/nginx.service → /etc/systemd/system/nginx.service.d/override.conf
[OVERRIDDEN] /etc/systemd/system/sshd.service → /usr/lib/systemd/system/sshd.service

--- /usr/lib/systemd/system/sshd.service    2026-06-10 09:00:00
+++ /etc/systemd/system/sshd.service        2026-09-01 14:22:10
@@ -8,7 +8,7 @@
-ExecStart=/usr/sbin/sshd -D $OPTIONS
+ExecStart=/usr/sbin/sshd -D -p 2222

2 overridden configuration files found.
```

| 先頭の印 | 意味 |
|:--|:--|
| **`[OVERRIDDEN]`** | **同名のファイルで丸ごと置き換えられている**（元のファイルは読まれない） |
| **`[EXTENDED]`** | **drop-in で一部だけ追加・変更されている**（元のファイルも読まれる） |
| `[MASKED]` | `/dev/null` へのリンクで、**起動そのものが禁止されている** |
| `[EQUIVALENT]` | 内容が同じ（差分なし） |
| `[REDIRECTED]` | 別のファイルへのシンボリックリンクになっている |
| `[UNCHANGED]` | 変更されていない |

**よく使うオプション**

| オプション | 意味 |
|:--|:--|
| **`--type=<種別>`** | **表示する種別を絞る**（`overridden` / `extended` / `masked` / `equivalent` / `redirected` / `unchanged`） |
| **`--diff=false`** | **差分の中身を出さず、一覧だけ表示する**（何が上書きされているかの確認だけしたいとき） |
| `--no-pager` | ページャーを使わずそのまま出力する |

```bash
$ systemd-delta --type=overridden --diff=false       # 丸ごと置き換えられたものだけ一覧する
$ systemd-delta /etc/systemd/system                  # 特定のディレクトリだけに絞る
```

**補足**

- **「設定を直したのに効かない」「昔の誰かが `/etc` に置いたファイルが残っている」ときの調査に効きます。** 対象のユニットが分かっているなら、`systemctl cat ユニット名` のほうが手早く読めます
- **`systemd-delta` は systemd 付属のコマンド**です。`systemctl` のサブコマンドではないので、単独のコマンドとして実行します

---

## ユニットファイルの構造

**INI 形式で書きます。** `[セクション名]` で区切り、`キー=値` を並べます。

```ini
[Unit]
Description=My sample application
Documentation=https://example.com/docs
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=myapp
WorkingDirectory=/opt/myapp
EnvironmentFile=/etc/myapp/env
ExecStart=/usr/bin/python3 /opt/myapp/app.py --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

| セクション | 使えるユニット | 役割 |
|:--|:--|:--|
| **`[Unit]`** | **すべて** | 説明、他ユニットとの関係、起動条件 |
| **`[Service]`** | **`.service` だけ** | 実行するプログラムと管理方法 |
| **`[Install]`** | **すべて** | `enable` / `disable` したときの動作 |
| `[Timer]` / `[Socket]` / `[Mount]` | それぞれの種類 | 種類ごとの固有設定 |

**書き方のルール**

| 決まり | 内容 |
|:--|:--|
| **大文字小文字** | **キーは区別する**（`ExecStart` を `execstart` と書くとエラー） |
| **空白** | `=` の前後に空白を入れない |
| **コメント** | 行頭の `#` または `;` |
| **行の継続** | 行末に `\` を置くと次の行へ続く |
| **値のクォート** | 空白を含む引数は `"` で囲む |
| **同じキーの重複** | **後に書いたほうが勝つ**（`ExecStart=` など一部は追記になる） |

**空の値で「リセット」する**

```ini
ExecStart=
ExecStart=/usr/local/bin/newapp
```

**`ExecStart=` を空にすると、それまでの指定がすべて消えます。**
drop-in で `ExecStart=` を差し替えるときは、**この 2 行を必ずセットで書きます**（後述）。

---

## Unitセクション

`[Unit]` には、**ユニットの説明と、他ユニットとの関係**を書きます。

### Description

```ini
Description=The nginx HTTP and reverse proxy server
```

**人が読むための説明**です。`systemctl status` の 1 行目や、`list-units` の DESCRIPTION 列に出ます。

```bash
$ systemctl status nginx --no-pager | head -1   # 1行目だけを表示して説明を確認する
● nginx.service - The nginx HTTP and reverse proxy server
```

```text
Description=The nginx HTTP and reverse proxy server
                          ↓
status の「-」より後ろに表示される
```

**起動処理には影響しません。** ただし**一覧で自分のサービスを見つけるための唯一の手がかり**なので、
自作するときは必ず書きます。

### Documentation

```ini
Documentation=man:nginx(8)
Documentation=https://nginx.org/en/docs/
```

**そのユニットに関する資料の場所**です。複数行書けます。

```text
man:nginx(8)
└─┬─┘ └─┬─┘└┬┘
 種類  名前  manのセクション番号
```

| セクション | 主な内容 |
|:--|:--|
| 1 | 一般ユーザー向けコマンド |
| 5 | **設定ファイルの書式** |
| 8 | **管理者向けコマンド・デーモン** |

```bash
$ man 8 nginx                        # セクション8のマニュアルを開く（qキーで閉じる）
$ systemctl help nginx               # Documentation= のmanページを直接開く
```

### 起動する条件

**条件を満たさないときに、起動を静かに飛ばす設定**です。

| 設定 | 意味 |
|:--|:--|
| **`ConditionPathExists=`** | **指定したパスが存在するときだけ起動する** |
| `ConditionPathIsDirectory=` | ディレクトリが存在するときだけ |
| `ConditionFileNotEmpty=` | ファイルが空でないときだけ |
| **`ConditionVirtualization=`** | **仮想環境の種類が一致するときだけ**（`kvm` `container` など） |
| `ConditionKernelVersion=` | カーネルバージョンが条件に合うときだけ |
| **`AssertPathExists=`** | 同じ判定だが、**満たさないと失敗として記録される** |

```ini
[Unit]
ConditionPathExists=/etc/myapp/enabled
```

**`Condition*=` と `Assert*=` の違いは、失敗として扱うかどうか**です。

| | **`Condition*=`** | **`Assert*=`** |
|:--|:--|:--|
| 条件を満たさないとき | **何もせず飛ばす**（`inactive` のまま） | **`failed` として記録する** |
| ログ | 静かに記録されるだけ | エラーとして出る |

```bash
$ systemctl show myapp -p ConditionResult --value   # 条件判定の結果を確認する
no
```

**`no` なら、条件に合わず起動が飛ばされた**ということです。
「エラーも出ないのに起動しない」ときは、まずここを疑います。

### 失敗したときに動かすユニット

```ini
[Unit]
OnFailure=notify-admin.service
```

**このユニットが `failed` になったときに起動するユニット**を指定します。
通知スクリプトを紐づけておくと、**失敗を検知して自動で連絡**できます。

---

## 依存関係と起動順序

**systemd で最も間違えやすいのがここです。**

```text
依存関係（Requires= / Wants=）  … 「一緒に起動するか」
起動順序（After= / Before=）    … 「どちらが先か」

この2つは まったく別の設定です。
```

**`Requires=` を書いても、順番は決まりません。** 同時に起動しようとします。
**順番が必要なら `After=` を必ず併記します。**

### 依存関係の設定

| 設定 | 強さ | 意味 |
|:--|:-:|:--|
| **`Wants=`** | **弱** | **一緒に起動しようとするが、相手が失敗しても自分は動く** |
| **`Requires=`** | **強** | **相手が起動しないと自分も起動しない** |
| `Requisite=` | 強 | **相手が「すでに起動済み」でなければ、即座に失敗する**（起動は試みない） |
| **`BindsTo=`** | **最強** | `Requires=` に加え、**相手が予期せず止まったら自分も止まる** |
| `PartOf=` | 片方向 | **相手を stop / restart したとき、自分も stop / restart される** |
| `Upholds=` | 継続 | 自分が動いている間、相手が止まっていたら**繰り返し起動し直す** |
| **`Conflicts=`** | 排他 | **相手が起動していたら停止させる**（同時に動かせないもの同士） |

```ini
[Unit]
Requires=postgresql.service
After=postgresql.service
```

**この 2 行がセットで「DB が起動してから、自分を起動する」**になります。

**`Wants=` と `Requires=` の使い分け**

```text
Wants=    … 無くても動く。落ちても巻き込まれない   ← 迷ったらこちら
Requires= … 無いと成立しない。相手の失敗で自分も失敗
```

**`Requires=` は「相手が失敗したら自分も止まる」**ため、**依存を厳しくしすぎると障害が連鎖**します。
公式ドキュメントでも、**`Wants=` の使用が推奨**されています。

### 起動順序の設定

| 設定 | 意味 |
|:--|:--|
| **`After=`** | **相手が起動してから、自分を起動する** |
| **`Before=`** | **自分が起動してから、相手を起動する** |

```text
After=network.target    … network.target の後に自分が起動する
Before=shutdown.target  … shutdown.target の前に自分が停止処理される
```

**停止時は順番が逆になります。** `After=` を書いたユニットは、**停止時には先に止まります**。

**`network.target` と `network-online.target` の違い**

| ターゲット | 意味 |
|:--|:--|
| **`network.target`** | **ネットワーク管理の仕組みが起動した**。IP が付いている保証は無い |
| **`network-online.target`** | **実際に通信できる状態になった** |

```ini
[Unit]
Wants=network-online.target
After=network-online.target
```

**外部の API や DB に接続するサービスは `network-online.target`** を使います。
**`network.target` だけだと、IP が付く前に起動して接続に失敗**することがあります。
なお `network-online.target` は、**`Wants=` も一緒に書かないと有効になりません**。

```bash
$ systemctl list-dependencies nginx --no-pager   # 依存しているユニットをツリーで確認する
$ systemctl show nginx -p After --value          # 起動順序の指定を確認する
```

---

## Serviceセクションは別ノートにある

**`[Service]` セクションの書き方**（`ExecStart=` / `Type=` / `Restart=` / `User=` / 環境変数の渡し方）と、
**自作アプリを常駐サービスにする手順**は、
[systemd Serviceセクションと自作サービス](./systemd_Serviceセクションと自作サービス.md) に移しました。

| 決めること | 迷ったらこれ |
|:--|:--|
| **`Type=`** | **`exec`**（前面で動き続けるアプリ）。古い環境なら `simple` |
| **`ExecStart=`** | **絶対パスで書く**（systemd は `PATH` を使わない） |
| **`User=`** | **専用ユーザーを作って指定する**（root で常駐させない） |
| **`Restart=`** | **`on-failure`**、`RestartSec=` は 5〜10 秒 |

---

## Installセクションとenableの正体

```ini
[Install]
WantedBy=multi-user.target
```

**`[Install]` は、`enable` したときに何をするかを書くセクション**です。
**systemd が起動時に読む設定ではありません。**

| 設定 | 意味 |
|:--|:--|
| **`WantedBy=`** | **enable すると、指定ターゲットの `.wants/` にリンクを作る**（弱い依存） |
| **`RequiredBy=`** | enable すると、`.requires/` にリンクを作る（強い依存） |
| **`Alias=`** | **別名を付ける**。その名前でも操作できるようになる |
| **`Also=`** | **一緒に enable / disable するユニット**（socket とセットのときなど） |
| `DefaultInstance=` | テンプレートユニットの既定インスタンス名 |

### enable が実際にしていること

```bash
$ sudo systemctl enable myapp        # 自動起動を有効にする
Created symlink /etc/systemd/system/multi-user.target.wants/myapp.service → /etc/systemd/system/myapp.service.
```

**シンボリックリンクを 1 本作っているだけ**です。

```text
[Install]
WantedBy=multi-user.target
        ↓ systemctl enable
/etc/systemd/system/multi-user.target.wants/myapp.service
        ↓ 起動時
multi-user.target が「このユニットも欲しい」と判断して起動する
```

```bash
$ ls -l /etc/systemd/system/multi-user.target.wants/ | head -5   # リンクの実体を確認する
```

**`[Install]` が無いユニットは enable できません。**

```text
The unit files have no installation config (WantedBy=, RequiredBy=, Also=, Alias=
settings in the [Install] section, and DefaultInstance= for template units).
```

このようなユニットは `is-enabled` で **`static`** と表示されます。
**`static` は「他のユニットから依存されて起動する」前提**のもので、異常ではありません。

### enabled と active は別

```text
enabled          … 次回のOS起動から自動で立ち上がる設定がある
active (running) … いま動いている
```

**この 2 つは独立しています。** 4 通りの組み合わせがすべて存在します。

| 組み合わせ | 意味 |
|:--|:--|
| `enabled` ＋ `active` | 正常に運用されている |
| **`enabled` ＋ `inactive`** | **設定はあるが、いまは止めている**（メンテ中など） |
| **`disabled` ＋ `active`** | **手で起動しただけ。再起動すると消える** ← 事故のもと |
| `disabled` ＋ `inactive` | 使っていない |

**構築後は必ず両方を確認します。**

```bash
$ systemctl is-enabled myapp && systemctl is-active myapp   # 自動起動と稼働状態を両方確認する
enabled
active
```

---

## drop-inで設定を上書きする

**パッケージが提供するユニットファイルを直接編集せず、差分だけを別ファイルに置く仕組み**です。

```text
/etc/systemd/system/nginx.service.d/override.conf
                    └────┬────┘ └┬┘  └────┬────┘
                     ユニット名   .d    任意の名前.conf
```

**読み込まれる順番**

```text
① /usr/lib/systemd/system/nginx.service         ← 本体
        ↓ 上書き
② /usr/lib/systemd/system/nginx.service.d/*.conf
        ↓ 上書き
③ /run/systemd/system/nginx.service.d/*.conf
        ↓ 上書き
④ /etc/systemd/system/nginx.service.d/*.conf    ← 最優先
```

**同じディレクトリ内の `.conf` は、ファイル名のアルファベット順**に読まれます。
`10-` `20-` のように**数字を頭に付けて順番を明示**するのが慣習です。

### 作り方

```bash
$ sudo systemctl edit nginx          # drop-in を作成・編集する（保存すると daemon-reload まで自動）
```

エディタが開くので、**変更したい項目だけ**を書きます。

```ini
[Service]
Restart=always
RestartSec=10
```

**セクション名（`[Service]`）は必ず書きます。** これが無いと反映されません。

```bash
$ systemctl cat nginx --no-pager     # 本体とdrop-inをまとめて確認する
$ systemctl show nginx -p DropInPaths --value   # 適用されているdrop-inの場所を確認する
```

### ExecStart を差し替えるときの注意

**`ExecStart=` は「追記」されるため、drop-in にそのまま書くとエラー**になります。

```text
Service has more than one ExecStart= setting, which is only allowed for Type=oneshot services.
```

**いったん空にしてから書き直します。**

```ini
[Service]
ExecStart=
ExecStart=/usr/local/bin/nginx-wrapper
```

**この「空行でリセット」は `Environment=` や `ExecStartPre=` でも同じ**です。

### 元に戻す

```bash
$ sudo systemctl revert nginx        # drop-in と /etc の変更を削除して既定に戻す
Removed "/etc/systemd/system/nginx.service.d/override.conf".
```

**drop-in の利点**

| | **本体を直接編集** | **drop-in** |
|:--|:--|:--|
| パッケージ更新 | **上書きされて消える** | **残る** |
| 変更点の把握 | 差分を追いにくい | **変えた項目だけが並ぶ** |
| 元に戻す | 手作業 | **`systemctl revert` 一発** |

---

## テンプレートユニット

**1 つのユニットファイルから、パラメータ違いの複数サービスを作る仕組み**です。

```text
myapp@.service          ← テンプレート（ファイル名に @ を付ける）
        ↓
myapp@web01.service     ← インスタンス（@ の後ろが引数になる）
myapp@web02.service
```

```ini
[Unit]
Description=My application for %i

[Service]
ExecStart=/usr/local/bin/myapp --name %i
EnvironmentFile=/etc/myapp/%i.env

[Install]
WantedBy=multi-user.target
```

| 記号 | 展開される内容 |
|:--|:--|
| **`%i`** | **`@` の後ろの文字列**（エスケープを解除した形） |
| `%I` | `%i` と同じだが、エスケープを解除しない |
| **`%n`** | **ユニット名の全体**（`myapp@web01.service`） |
| `%N` | 拡張子を除いたユニット名 |
| `%H` | ホスト名 |
| `%u` | 実行ユーザー名 |

```bash
$ sudo systemctl enable --now myapp@web01   # web01 用のインスタンスを有効化して起動する
$ sudo systemctl start myapp@web02          # web02 用も起動する
$ systemctl status 'myapp@*' --no-pager     # インスタンスをまとめて確認する
```

**実際の例**では、`getty@tty1.service`（仮想コンソール）や
`user@1000.service`（ユーザーセッション）が同じ仕組みで動いています。

---

## ターゲット

**ターゲットは、複数のユニットをまとめたグループ**です。
**旧来のランレベルに相当**しますが、より柔軟にまとめられます。

| ターゲット | 意味 | 旧ランレベル |
|:--|:--|:-:|
| `poweroff.target` | 電源を切る | 0 |
| **`rescue.target`** | **シングルユーザーモード**（最小限＋root シェル） | 1 |
| **`multi-user.target`** | **CUI のマルチユーザー**。**サーバの既定** | 3 |
| **`graphical.target`** | **GUI 付きマルチユーザー** | 5 |
| `reboot.target` | 再起動する | 6 |
| `emergency.target` | 緊急モード（ほぼ何も起動しない） | — |
| `basic.target` | 基本的な初期化が済んだ状態 | — |
| `network.target` | ネットワーク管理の仕組みが起動した | — |
| `network-online.target` | 実際に通信できる状態になった | — |

```bash
$ systemctl get-default              # 既定で起動するターゲットを確認する
multi-user.target

$ sudo systemctl set-default multi-user.target   # 既定をCUIに変更する
$ systemctl list-dependencies multi-user.target --no-pager   # そのターゲットに紐づくユニットを見る
```

**ターゲットも `.wants/` ディレクトリを持ちます。**

```bash
$ ls /etc/systemd/system/multi-user.target.wants/ | head -5   # enable済みのユニットを確認する
```

**`WantedBy=multi-user.target` と書いて `enable` すると、ここにリンクが作られます。**
つまり**「起動時に立ち上がるサービス一覧」はこのディレクトリを見れば分かります**。

---

## つまずきポイント

| 症状 | 原因 | 対処 |
|:--|:--|:--|
| **設定を変えたのに反映されない** | **`daemon-reload` をしていない** | `sudo systemctl daemon-reload` |
| **`/usr/lib` を編集したら更新で消えた** | パッケージが上書きするディレクトリ | **`systemctl edit`** で `/etc` 配下に置く |
| **drop-in を書いたのに効かない** | **`[Service]` などのセクション名が無い** | セクション名から書く |
| **drop-in で `ExecStart=` がエラー** | 追記扱いになり 2 つになる | **空の `ExecStart=` を先に書く** |
| **`Requires=` だけ書いて順番が狂う** | **依存と順序は別の設定** | **`After=` を必ず併記する** |
| **ネットワーク接続に失敗する** | `network.target` は IP 付与を保証しない | **`network-online.target`** を `Wants=` と `After=` で指定 |
| **`static` を停止中と思う** | `[Install]` を持たないという意味 | 稼働状態は `Active:` 行で見る |
| **手動 start だけで再起動後に消える** | `enable` していない | `enable --now` を使う |
| 条件付きで起動しない・ログも出ない | **`Condition*=` に弾かれている** | `systemctl show -p ConditionResult` を確認 |

> **`ExecStart=` / `Type=` / `Restart=` まわりのつまずき**は
> [systemd Serviceセクションと自作サービス](./systemd_Serviceセクションと自作サービス.md) の「つまずきポイント」にまとめています。

---

## クラウド実務メモ

**EC2 で自作アプリを常駐させるときの型**

```ini
[Unit]
Description=My API server
Wants=network-online.target
After=network-online.target

[Service]
Type=exec
User=appuser
WorkingDirectory=/opt/api
EnvironmentFile=/etc/api/env
ExecStart=/opt/api/venv/bin/python /opt/api/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`network-online.target` を入れる理由**は、
**起動直後は ENI に IP が付いておらず、外部接続が失敗する**ことがあるためです。

**cloud-init との順序**

EC2 の初期化処理も systemd ユニットとして動きます。

| ユニット | 役割 |
|:--|:--|
| `cloud-init-local.service` | ネットワーク設定前の処理 |
| `cloud-init.service` | ネットワーク設定後の処理 |
| `cloud-config.service` | `cloud-config` の適用 |
| **`cloud-final.service`** | **ユーザーデータのスクリプト実行** |

```ini
[Unit]
After=cloud-final.service
```

**ユーザーデータで配置したファイルを使うサービス**は、この順序指定が要ります。

**環境変数と機密情報**

```text
Environment=      … ユニットファイルに直書き。systemctl show で誰でも読める
EnvironmentFile=  … 別ファイル。パーミッションで保護できる      ← こちらを使う
```

```bash
$ sudo chmod 600 /etc/myapp/env      # 所有者だけが読めるようにする
$ sudo chown myapp:myapp /etc/myapp/env   # サービス実行ユーザーの所有にする
```

**本番の機密情報は Secrets Manager や Parameter Store から取得**し、
**`ExecStartPre=` で取り出して `EnvironmentFile=` に書く**構成がよく使われます。

**コンテナには systemd がありません**

```text
EC2 / 仮想マシン … PID 1 は systemd     → ユニットファイルで管理する
一般的なコンテナ … PID 1 はアプリ自身   → Dockerfile の CMD が ExecStart 相当
```

| systemd | コンテナでの対応 |
|:--|:--|
| `ExecStart=` | `CMD` / `ENTRYPOINT` |
| `Restart=always` | `restartPolicy: Always`（Kubernetes） |
| `EnvironmentFile=` | ConfigMap / Secret |
| `After=` | `initContainers` / 依存の設計 |

**考え方は共通なので、systemd を理解しておくとコンテナ側の設計も読みやすくなります。**

---

## 参考リンク

- [man 5 systemd.unit](https://man7.org/linux/man-pages/man5/systemd.unit.5.html)
- [man 5 systemd.service](https://man7.org/linux/man-pages/man5/systemd.service.5.html)
- [man 5 systemd.exec](https://man7.org/linux/man-pages/man5/systemd.exec.5.html)
- [man 5 systemd.kill](https://man7.org/linux/man-pages/man5/systemd.kill.5.html)
- [man 5 systemd.target](https://man7.org/linux/man-pages/man5/systemd.target.5.html)
- [man 1 systemd-escape](https://man7.org/linux/man-pages/man1/systemd-escape.1.html)
- [Working with systemd unit files — Red Hat Enterprise Linux 10](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_systemd_unit_files_to_customize_and_optimize_your_system/working-with-systemd-unit-files)
- [AWS — cloud-init によるインスタンスの初期化](https://docs.aws.amazon.com/ja_jp/AWSEC2/latest/UserGuide/user-data.html)

---

[← このフォルダの目次にもどる](./00_このフォルダにあるもの.md) ｜ [全体の目次にもどる](../README.md)
