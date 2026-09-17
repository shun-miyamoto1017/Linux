# systemd Serviceセクションと自作サービス

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ ／ Phase2 ★★★★☆（システム起動のカスタマイズ） |
| **Ping-t の範囲** | Linux1 / システムアーキテクチャ(主題101) — システムの起動 ／ Linux2 / システムの起動とLinuxカーネル(主題2.01) — システム起動のカスタマイズ |
| **業務での使いどころ** | **自作アプリやベンダ製ミドルウェアを、落ちても復旧する常駐サービスにする**。`Type=` の選び方を間違えると、起動したつもりで止まっている状態になる |

> **このノートは `[Service]` セクションの書き方に絞ったもの**です。
> ユニットの種類・置き場所・`[Unit]` / `[Install]` セクション・drop-in・ターゲットは
> [systemd 基本とユニットファイル](./systemd_基本とユニットファイル.md)、
> コマンドの打ち方は [systemctl サービスの操作と確認](./systemctl_サービスの操作と確認.md) にまとめています。

---

## 目次

- [Serviceセクション](#serviceセクション)
- [ExecStartの書き方](#execstartの書き方)
- [Typeと起動完了の判断](#typeと起動完了の判断)
- [Restartで自動復旧させる](#restartで自動復旧させる)
- [自作サービスを作る手順](#自作サービスを作る手順)
- [参考リンク](#参考リンク)

---

## Serviceセクション

`[Service]` には、**何をどう動かすか**を書きます。

### コマンドを指定する設定

| 設定 | 実行されるタイミング |
|:--|:--|
| **`ExecStart=`** | **サービスの本体**。起動時に実行する |
| **`ExecStartPre=`** | **`ExecStart=` の前**。設定チェックや前準備 |
| `ExecStartPost=` | `ExecStart=` の後。起動後の後処理 |
| **`ExecStop=`** | **`stop` したとき**。省略するとシグナルで終了させる |
| **`ExecReload=`** | **`reload` したとき**。**無いと `reload` はエラーになる** |
| `ExecStopPost=` | 停止処理の後（成功・失敗どちらでも実行される） |

```ini
[Service]
ExecStartPre=/usr/sbin/nginx -t
ExecStart=/usr/sbin/nginx
ExecReload=/bin/kill -s HUP $MAINPID
```

**`$MAINPID` は、systemd がメインプロセスの PID に置き換える特殊変数**です。

**`ExecStartPre=` で設定を検証する**のは実務でよく使う型です。
**設定が壊れているときに、サービスを落とさずに起動を止められます**。

**先頭に付けられる記号**

| 記号 | 意味 |
|:--|:--|
| **`-`** | **失敗しても無視して続行する**（`ExecStartPre=-/bin/rm -f /run/app.pid`） |
| `+` | 権限制限を無視して full privilege で実行する |
| `@` | 引数の 0 番目（プロセス名）を明示する |
| `!` | 一部の権限設定を無視する |

### 実行環境の設定

| 設定 | 意味 |
|:--|:--|
| **`User=`** / **`Group=`** | **実行するユーザー / グループ**。省略すると root |
| **`WorkingDirectory=`** | **実行時のカレントディレクトリ** |
| **`Environment=`** | **環境変数を直接指定する**（複数行可） |
| **`EnvironmentFile=`** | **環境変数をファイルから読む**（`-` を付けると無いとき無視） |
| `UMask=` | 作成するファイルのパーミッションマスク |
| `RuntimeDirectory=` | `/run/名前` を自動で作成・削除する |
| `StateDirectory=` | `/var/lib/名前` を自動で作成する |

```ini
[Service]
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
Environment=APP_ENV=production
Environment=LOG_LEVEL=info
EnvironmentFile=-/etc/myapp/env
```

**`EnvironmentFile=` のファイルはシェルスクリプトではありません。**

```text
OK   APP_ENV=production
NG   export APP_ENV=production      ← export は書かない
NG   APP_PORT=$BASE_PORT            ← 変数展開はされない
```

**`User=` に存在しないユーザーを書くと `217/USER` で失敗**します。自作時の頻出ミスです。

### ログの出力先

| 設定 | 意味 |
|:--|:--|
| **`StandardOutput=`** | 標準出力の行き先 |
| **`StandardError=`** | 標準エラー出力の行き先 |

| 値 | 意味 |
|:--|:--|
| **`journal`** | **journal に記録する**（多くの環境で既定） |
| `null` | 捨てる |
| `inherit` | 親から引き継ぐ |
| `file:/path` | 指定ファイルへ書く（上書き） |
| `append:/path` | 指定ファイルへ追記する |

```ini
[Service]
StandardOutput=journal
StandardError=journal
```

**既定で journal に入るので、アプリ側でログファイルを開かなくても `journalctl -u` で読めます。**

### 停止のしかた

| 設定 | 意味 |
|:--|:--|
| **`KillSignal=`** | 最初に送るシグナル（既定は `SIGTERM`） |
| **`TimeoutStopSec=`** | **停止を待つ秒数**。過ぎると `SIGKILL` を送る |
| **`KillMode=`** | どのプロセスにシグナルを送るか |

| `KillMode` の値 | 意味 |
|:--|:--|
| **`control-group`** | **cgroup 内の全プロセスに送る**（既定） |
| `mixed` | メインには `SIGTERM`、残りには `SIGKILL` |
| **`process`** | **メインプロセスにだけ送る**（子プロセスが残る可能性がある） |
| `none` | 何も送らない（非推奨） |

**`stop` しても子プロセスが残る**ときは、`KillMode=process` になっていないか確認します。

---

## ExecStartの書き方

### 実行の流れ

`ExecStart=` は、**サービスを起動するために systemd が実行するプログラム**です。

**よくある誤解**

```text
サービスが先に起動する
        ↓
ExecStart= のプログラムを追加で実行する    ← これは誤り
```

**正しい流れ**

```text
systemctl start myapp.service
        ↓
systemd が myapp.service を読み込む
        ↓
ExecStart= のプログラムを実行する
        ↓
プログラムが動き始める
        ↓
myapp.service が起動状態になる
```

**`ExecStart=` のプログラムを起動・管理する一連の処理そのものが、サービスユニットの起動**です。

### 絶対パスで書く

```bash
$ command -v python3                 # 実行ファイルの場所を確認する
/usr/bin/python3
```

**`ExecStart=` に `python3` とだけ書いても動きません。**
systemd は `PATH` を頼りにできないため、**絶対パスで指定します**。

```ini
ExecStart=/usr/bin/python3 /opt/myapp/app.py --port 8000
```

```text
/usr/bin/python3        … systemd が実行するプログラム
/opt/myapp/app.py       … python3 へ渡す引数
--port 8000             … app.py へ渡すオプションと値
```

### シェルを経由しない

**systemd は `ExecStart=` をシェルに渡しません。** そのため、**シェルの機能は解釈されません**。

| 記号 | 本来の意味 | `ExecStart=` に書くと |
|:--|:--|:--|
| **`>`** | リダイレクト | **ただの文字列として引数に渡る** |
| **`\|`** | パイプ | 同上 |
| **`&&`** | 条件付き実行 | 同上 |
| **`*`** | ワイルドカード | **展開されない** |
| `$VAR` | 変数展開 | **`Environment=` で定義したものだけ**展開される |

**期待どおりに動かない例**

```ini
[Service]
ExecStart=/usr/bin/echo hello > /tmp/hello.txt
```

この場合、`>` と `/tmp/hello.txt` は **`echo` に渡される文字列**になり、
画面（journal）に `hello > /tmp/hello.txt` と出力されるだけです。

**シェルが必要なら明示的に呼びます**

```ini
[Service]
ExecStart=/bin/sh -c '/usr/bin/echo hello > /tmp/hello.txt'
```

**ただし、複雑な処理はスクリプトに分けるほうが管理しやすくなります。**

```ini
[Service]
ExecStart=/usr/local/bin/start-myapp.sh
```

### 実際に何が実行されるか確認する

```bash
$ systemctl cat nginx --no-pager | grep '^ExecStart='   # 設定ファイル上の指定を抜き出す
$ systemctl show nginx -p ExecStart                      # systemdが解析した結果を確認する
```

| 記号・コマンド | 意味 |
|:--|:--|
| `\|` | 左の実行結果を右のコマンドへ渡す |
| `grep` | 条件に一致する行を抜き出す |
| `^` | 行の先頭を表す |
| `^ExecStart=` | 行の先頭が `ExecStart=` である行 |

---

## Typeと起動完了の判断

**`Type=` は、systemd がどの時点で「起動が完了した」と判断するか**を決めます。

```text
ExecStart=  … 何を実行するか
Type=       … いつ「起動完了」と判断するか
```

**なぜ重要か。** プログラムが実際に使えるようになるまでには段階があるからです。

```text
プロセスを作る
    ↓
実行ファイルを開始する
    ↓
設定ファイルを読み込む
    ↓
DBへ接続する
    ↓
ポートで受付を開始する    ← ここまで来て初めて「使える」
```

**systemd がどの段階で `active` にするかで、`After=` で後続を待たせる意味が変わります。**

### Type の一覧

| 値 | 起動完了と判断するタイミング | 使いどころ |
|:--|:--|:--|
| **`simple`** | **メインプロセスを fork した直後**（既定値） | 一般的な常駐プログラム |
| **`exec`** | **実行ファイルの起動に成功した直後** | `simple` より確実。パス誤りを検出できる |
| **`forking`** | **親プロセスが終了した時点** | **自分でデーモン化する古い形式のプログラム** |
| **`oneshot`** | **プロセスが終了した時点** | **1回きりの処理**（初期化スクリプトなど） |
| **`notify`** | **アプリが `READY=1` を送った時点** | **準備完了を正確に伝えたいプログラム** |
| `notify-reload` | `notify` と同じ。加えて reload 時に `SIGHUP` を送る | reload に対応したプログラム |
| `dbus` | **`BusName=` で指定した名前を取得した時点** | D-Bus サービス |
| `idle` | 他のジョブが片付くまで実行を遅らせる | 起動時のコンソール出力を整えたいとき |

### Type=simple

```ini
[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/myapp/app.py
```

**systemd がプロセスを作った時点で、もう `active` になります。**

```text
systemd がプロセスを生成する
        ↓
systemd が active にする       ← ここが早い
        ↓
実行ファイルを開始する
        ↓
アプリの初期化
        ↓
ポートで受付開始               ← 本当に使えるのはここから
```

**`active (running)` でもアプリが応答するとは限りません。**
これが「systemctl は正常なのに、繋がらない」の主な原因です。

### Type=exec

```ini
[Service]
Type=exec
ExecStart=/usr/bin/python3 /opt/myapp/app.py
```

**プログラムの起動には 2 段階あります。**

```text
fork … 新しいプロセスを作る
exec … そのプロセスで目的の実行ファイルを開始する
```

**`Type=exec` は `exec` の成功まで待ちます。** そのため、

```text
実行ファイルが存在しない（203/EXEC）
User= のユーザーが存在しない（217/USER）
```

といった**起動前の問題を、確実に失敗として検出できます**。
`simple` ではこれらが「起動成功のあとで落ちた」と扱われ、原因が分かりにくくなります。

**ただし、設定の読み込み完了・DB接続・ポート受付までは保証しません。**

### Type=forking

```ini
[Service]
Type=forking
PIDFile=/run/nginx.pid
ExecStart=/usr/sbin/nginx
```

**自分で子プロセスを作って、親が終了する（デーモン化する）タイプ**のプログラム用です。

```text
systemd が ExecStart= を実行する
        ↓
起動したプロセスが子を作る
        ↓
親プロセスが終了する            ← systemd はここで「起動完了」と判断する
        ↓
子プロセスがサービスとして残る
```

**`PIDFile=` を併記します。** 親が終了してしまうため、
**systemd はどれがメインプロセスか分からなくなる**からです。PID ファイルで教えます。

**多くのアプリには「フォアグラウンドで動くオプション」があります。**
その場合は `Type=simple`（または `exec`）＋フォアグラウンド実行のほうが、systemd と相性が良くなります。

### Type=oneshot

```ini
[Unit]
Description=Initial firewall configuration

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-firewall.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

**処理が終わってから次へ進む**タイプです。初期化処理に使います。

| 特徴 | 内容 |
|:--|:--|
| **完了の判断** | **プロセスが終了した時点** |
| **`ExecStart=` の複数指定** | **できる**（上から順に実行される） |
| `After=` との関係 | **処理が終わるまで後続を待たせられる** |

**`RemainAfterExit=` の効き方**

| 設定 | コマンド終了後の状態 |
|:--|:--|
| **`RemainAfterExit=no`**（既定） | **`inactive (dead)`** |
| **`RemainAfterExit=yes`** | **`active (exited)`** |

```text
inactive (dead)
        ↓ systemctl start
setup-firewall.sh を実行
        ↓
スクリプトが正常終了
        ↓ RemainAfterExit=yes
active (exited)          ← 「実行済み」という意味の active
```

**`exited` は失敗ではありません。** 「実行中のプロセスは無いが、役目は果たしている」状態です。
`RemainAfterExit=yes` にすると、**「この初期化は済んでいる」を systemd 上で表現**できます。

```bash
$ systemctl list-units --type=service --state=active --no-pager | grep exited   # exited のユニットを探す
```

### Type=notify

```ini
[Service]
Type=notify
ExecStart=/usr/local/bin/myapp
```

**アプリ自身が「準備できました」と systemd に伝える**方式です。

```text
systemd がアプリを起動
        ↓
アプリが初期化
        ↓
アプリが DB へ接続
        ↓
アプリがポートを開く
        ↓
アプリが READY=1 を送信      ← ここで初めて
        ↓
systemd が active にする
```

**アプリ側が `sd_notify()` に対応している必要があります。**

```text
Type=notify を設定する
        ＋
アプリが READY=1 を送る
        ↓
正しく機能する
```

**対応していないアプリに `Type=notify` だけ設定すると、通知を待ち続けてタイムアウト**します。

```text
Job for myapp.service failed because a timeout was exceeded.
```

### 確認と比較

```bash
$ systemctl show nginx -p Type --value   # systemdが認識しているTypeを表示する
forking
```

| Type | 起動完了の判断 | アプリが使える状態を保証するか |
|:--|:--|:--|
| `simple` | プロセスを fork した直後 | **保証しない** |
| `exec` | 実行ファイルの起動成功後 | **保証しない** |
| `forking` | 親プロセスの終了後 | 実装次第 |
| `oneshot` | プロセスの終了後 | **処理は完了している** |
| `notify` | `READY=1` の受信後 | **アプリが正しく通知していれば保証される** |

**迷ったときの選び方**

```text
フォアグラウンドで動く常駐プログラム  → simple（できれば exec）
自分でデーモン化する古いプログラム    → forking ＋ PIDFile=
1回だけ動かす初期化処理              → oneshot ＋ RemainAfterExit=yes
準備完了を正確に伝えられるプログラム  → notify
```

---

## Restartで自動復旧させる

```ini
[Service]
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3
```

| `Restart=` の値 | 再起動する条件 |
|:--|:--|
| **`no`**（既定） | **再起動しない** |
| **`on-failure`** | **0 以外の終了コード、シグナル、タイムアウト、ウォッチドッグ** |
| **`always`** | **正常終了でも異常終了でも、必ず再起動する** |
| `on-success` | 正常終了したときだけ |
| `on-abnormal` | シグナルやタイムアウトのときだけ（終了コードは対象外） |
| `on-abort` | 捕捉されないシグナルで終了したときだけ |
| `on-watchdog` | ウォッチドッグのタイムアウトのときだけ |

| 補助設定 | 意味 |
|:--|:--|
| **`RestartSec=`** | **再起動までの待ち時間**（既定 100ms）。**5〜10 秒にすると暴走しにくい** |
| **`StartLimitIntervalSec=`** | **回数を数える時間の窓**（既定 10 秒） |
| **`StartLimitBurst=`** | **その窓の中で許す起動回数**（既定 5 回） |

**上限を超えると systemd は再起動をあきらめます。**

```text
Failed to start myapp.service: Unit myapp.service has a start request repeated too quickly.
```

このときは**原因を直してから、カウンタを消して起動**します。

```bash
$ sudo systemctl reset-failed myapp  # failedの記録と再起動カウンタをリセットする
$ sudo systemctl start myapp         # あらためて起動する
```

**`always` と `on-failure` の使い分け**

```text
on-failure … 正常終了したときは、意図した停止とみなして再起動しない  ← 通常はこちら
always     … 何があっても動かし続けたい常駐プロセス
```

**`Restart=always` は「設定ミスで即死するサービス」も延々と再起動しようとします。**
`RestartSec=` を短いままにすると、ログが溢れて調査しづらくなります。

---

## 自作サービスを作る手順

**Python アプリを常駐サービスにする**流れを例にします。

### ① 実行できることを先に確かめる

```bash
$ sudo -u myapp /usr/bin/python3 /opt/myapp/app.py --port 8000   # サービスと同じユーザーで手動実行する
```

**ここで動かないものは、systemd に載せても動きません。**
**必ず `User=` に指定する予定のユーザーで試します**（権限の問題を先に潰すため）。

### ② ユニットファイルを作る

```bash
$ sudo vi /etc/systemd/system/myapp.service   # 管理者用のディレクトリに作成する
```

```ini
[Unit]
Description=My sample application
Documentation=https://example.com/docs
Wants=network-online.target
After=network-online.target

[Service]
Type=exec
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
EnvironmentFile=-/etc/myapp/env
ExecStart=/usr/bin/python3 /opt/myapp/app.py --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### ③ 読み込ませて起動する

```bash
$ sudo systemctl daemon-reload       # 新しいユニットファイルをsystemdに読み込ませる
$ sudo systemctl start myapp         # 起動してみる
$ systemctl status myapp --no-pager --full   # 状態と直近ログを確認する
```

### ④ 自動起動を設定する

```bash
$ sudo systemctl enable myapp        # 次回のOS起動から自動で立ち上がるようにする
$ systemctl is-enabled myapp         # 設定できたか確認する
enabled
```

### ⑤ 再起動して確かめる

```bash
$ sudo reboot                        # 実際に再起動して確認する
$ systemctl is-active myapp          # 起動後に自動で立ち上がったか確認する
active
```

**「手動では動くのに、再起動すると上がらない」**は `enable` 忘れが原因の定番です。
**⑤ まで実施して初めて完了**とみなします。

### 失敗したときに見るところ

```bash
$ systemctl status myapp --no-pager --full   # Process / Main PID の終了コードを見る
$ journalctl -u myapp -n 50 --no-pager       # ログを50行分見る
```

| 終了コード | 原因 |
|:--|:--|
| **`203/EXEC`** | **`ExecStart=` のパスが違う、実行権限が無い** |
| **`217/USER`** | **`User=` のユーザーが存在しない** |
| **`200/CHDIR`** | **`WorkingDirectory=` が存在しない** |
| `1/FAILURE` | プログラム自身がエラー終了した（ログを見る） |

---

## 参考リンク

- [man 5 systemd.service](https://man7.org/linux/man-pages/man5/systemd.service.5.html)
- [man 5 systemd.exec](https://man7.org/linux/man-pages/man5/systemd.exec.5.html)
- [man 5 systemd.kill](https://man7.org/linux/man-pages/man5/systemd.kill.5.html)
- [man 5 systemd.resource-control](https://man7.org/linux/man-pages/man5/systemd.resource-control.5.html)
- [man 3 sd_notify（`Type=notify` の通知）](https://man7.org/linux/man-pages/man3/sd_notify.3.html)
- [Working with systemd unit files — Red Hat Enterprise Linux 10](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_systemd_unit_files_to_customize_and_optimize_your_system/working-with-systemd-unit-files)
- [AWS — cloud-init によるインスタンスの初期化](https://docs.aws.amazon.com/ja_jp/AWSEC2/latest/UserGuide/user-data.html)

---

[← 全体の目次にもどる](../README.md)
