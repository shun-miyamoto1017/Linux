# systemctl サービスの操作と確認

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / システムアーキテクチャ(主題101) — システムの起動 ／ Linux2 / システムの起動とLinuxカーネル(主題2.01) — システム起動のカスタマイズ |
| **業務での使いどころ** | **サービスが動いているかを確かめる、起動・停止する、起動失敗を切り分ける**。サーバに入って最初に打つコマンド |

> **このノートは「コマンドの打ち方」を扱います。**
> **出力の読み方**は [systemctl 結果画面の見方](./systemctl_結果画面の見方.md)、
> ユニットファイルの中身（`[Unit]` / `[Service]` / `[Install]` の書き方、`Type=` の意味）は
> [systemd 基本とユニットファイル](./systemd_基本とユニットファイル.md) にまとめています。

---

## 目次

- [systemctl の書式](#systemctl-の書式)
- [サブコマンド一覧](#サブコマンド一覧)
- [よく使うオプション](#よく使うオプション)
- [サービスを操作する](#サービスを操作する)
- [自動起動を設定する](#自動起動を設定する)
- [状態を1語で判定する](#状態を1語で判定する)
- [出力の読み方は別ノートにある](#出力の読み方は別ノートにある)
- [失敗したユニットを扱う](#失敗したユニットを扱う)
- [daemon-reload が必要なとき](#daemon-reload-が必要なとき)
- [ターゲットとシステム全体の操作](#ターゲットとシステム全体の操作)
- [journalctl と組み合わせる](#journalctl-と組み合わせる)
- [参考リンク](#参考リンク)

---

## systemctl の書式

```text
systemctl [オプション] サブコマンド [ユニット名...]
```

```text
$ systemctl status nginx.service --no-pager --full
  │        │      │              └────────┬────────┘
  │        │      └ 対象のユニット        └ オプション
  │        └ サブコマンド（何をするか）
  └ コマンド本体
```

**オプションは前でも後ろでも構いません。** `systemctl --no-pager status nginx` でも同じです。

**参照するだけなら一般ユーザで実行できます**（`status` / `show` / `cat` / `list-*`）。
**状態を変えるものは root 権限が必要**です（`start` / `stop` / `enable` / `mask` など）。

```bash
$ systemctl status nginx             # 参照なので sudo は不要
$ sudo systemctl restart nginx       # 変更なので sudo が要る
```

---

## サブコマンド一覧

**役割ごとに 4 つのグループに分けて覚えます。**

**① 動かす・止める（ユニットコマンド）**

| サブコマンド | 意味 |
|:--|:--|
| **`start`** | **ユニットを起動する** |
| **`stop`** | **ユニットを停止する** |
| **`restart`** | **停止してから起動する**（止まっていても起動する） |
| `try-restart` | **動いているときだけ**再起動する（止まっていれば何もしない） |
| **`reload`** | **プロセスを止めずに設定だけ読み直させる**（`ExecReload=` が要る） |
| `reload-or-restart` | reload に対応していれば reload、していなければ restart |
| `try-reload-or-restart` | 上と同じだが、動いているときだけ実行する |
| **`kill`** | **ユニットのプロセスにシグナルを送る**（`--signal=` で指定） |
| `freeze` / `thaw` | cgroup freezer でプロセスを一時停止／再開する |
| `isolate` | **指定したユニットとその依存だけを起動し、他はすべて停止する** |
| `set-property` | 実行中のユニットのプロパティを一時的に変更する |

**② 調べる（ユニットコマンド）**

| サブコマンド | 意味 |
|:--|:--|
| **`status`** | **ユニットの状態と直近のログをまとめて表示する** |
| **`show`** | **systemd が保持しているプロパティを機械可読な形で表示する** |
| **`cat`** | **ユニットファイルと drop-in の中身をまとめて表示する** |
| **`is-active`** | **稼働中かどうかだけを 1 語で返す** |
| **`is-failed`** | **failed 状態かどうかだけを 1 語で返す** |
| **`list-units`** | **メモリ上に読み込まれているユニットの一覧** |
| **`list-dependencies`** | **そのユニットが必要とする／欲するユニットのツリー** |
| `list-timers` / `list-sockets` / `list-paths` / `list-automounts` | それぞれ timer / socket / path / automount の一覧 |
| `help` | そのユニットの man ページを開く |
| `whoami` | 指定した PID がどのユニットに属するかを返す |
| **`reset-failed`** | **failed の記録と再起動回数カウンタを消す** |

**③ 自動起動を設定する（ユニットファイルコマンド）**

| サブコマンド | 意味 |
|:--|:--|
| **`enable`** | **OS 起動時に自動起動するようにする** |
| **`disable`** | **自動起動をやめる** |
| **`is-enabled`** | **自動起動の設定状態を 1 語で返す** |
| `reenable` | いったん disable してから enable し直す（シンボリックリンクを既定に戻す） |
| **`mask`** | **起動そのものを禁止する**（`/dev/null` へのリンクを作る） |
| **`unmask`** | mask を解除する |
| **`list-unit-files`** | **インストール済みユニットファイルと、その有効／無効の状態の一覧** |
| `preset` / `preset-all` | ディストリの既定ポリシーに従って enable / disable を設定し直す |
| `link` | 検索パスの外にあるユニットファイルをリンクして使えるようにする |
| `revert` | drop-in と `/etc` の変更を捨てて、パッケージ提供の内容に戻す |
| **`edit`** | **drop-in（または本体）を安全に編集する** |
| `add-wants` / `add-requires` | 指定ターゲットに `Wants=` / `Requires=` を追加する |

**④ システム全体を操作する**

| サブコマンド | 意味 |
|:--|:--|
| **`daemon-reload`** | **ユニットファイルを読み直す**（編集したら必須） |
| `daemon-reexec` | systemd 自身を再実行する（systemd の更新後など） |
| **`get-default`** / **`set-default`** | **既定で起動するターゲットの確認／変更** |
| **`rescue`** / **`emergency`** | **レスキュー／緊急モードへ移行する** |
| **`default`** | **標準のモード（`default.target`）へ移行する**。レスキューからの復帰に使う |
| `reboot` / `poweroff` / `halt` / `suspend` | 再起動・電源断・停止・サスペンド |

> **`default` と `get-default` は別物です。**
> **`default`** は「**いま標準のモードに移る**」という**動作**、**`get-default`** は「**既定のターゲット名を表示する**」という**確認**です。

---

## よく使うオプション

| オプション | 意味 |
|:--|:--|
| **`--no-pager`** | **`less` などのページャーを使わず、そのまま出力する**（スクリプトやログ採取で必須） |
| **`-l` / `--full`** | **長い名前や説明を「…」で省略せず、最後まで表示する** |
| **`-t 種類` / `--type=種類`** | **ユニットの種類で絞る**（`service` `timer` `socket` など。カンマ区切りで複数可） |
| **`--state=状態`** | **LOAD / ACTIVE / SUB の状態で絞る**（`failed` `inactive` `running` など） |
| **`-a` / `--all`** | **inactive なユニットも含めてすべて表示する** |
| **`--failed`** | **failed 状態のユニットだけを表示する** |
| **`-p 名前` / `--property=名前`** | **`show` で表示するプロパティを絞る**（カンマ区切りで複数可） |
| **`--value`** | **`show` でプロパティ名を省き、値だけを出す**（スクリプト向き） |
| **`-n 行数` / `--lines=行数`** | **`status` に出すログの行数を変える**（既定は 10 行） |
| **`-o 形式` / `--output=形式`** | `status` のログ表示形式（`short` `cat` `json` など） |
| **`--now`** | **`enable` / `disable` と同時に `start` / `stop` もする** |
| **`--user`** | **ユーザ単位の systemd を対象にする**（既定はシステム全体の `--system`） |
| **`-H ホスト` / `--host=`** | SSH 経由でリモートホストの systemd を操作する |
| **`-M 名前` / `--machine=`** | コンテナ内の systemd を操作する |
| **`-q` / `--quiet`** | 結果の表示を抑える（終了コードだけ欲しいとき） |
| `--no-legend` | 一覧の見出し行と末尾の要約を出さない |
| `--plain` | `list-dependencies` のツリー記号を出さず、平らな一覧にする |
| `--runtime` | 変更を `/run` に書き、**再起動すると消える一時的な設定**にする |

**`--no-pager` を付ける理由**

`systemctl status` や `list-units` は、出力が長いと自動的に `less` に渡されます。
**スクリプトやコピー用途では止まってしまう**ため、`--no-pager` を付けます。

```bash
$ systemctl status nginx --no-pager --full   # 省略なし・ページャーなしで全文を出す
$ systemctl list-units --type=service --no-pager | head -20   # パイプに流すときも必要
```

**環境変数でまとめて無効にすることもできます。**

```bash
$ export SYSTEMD_PAGER=cat           # このシェルではページャーを使わない
```

---

## サービスを操作する

```bash
$ sudo systemctl start nginx         # 起動する
$ sudo systemctl stop nginx          # 停止する
$ sudo systemctl restart nginx       # 停止してから起動する
$ sudo systemctl reload nginx        # プロセスは残したまま設定だけ読み直させる
$ sudo systemctl try-restart nginx   # 動いているときだけ再起動する
```

**`restart` と `reload` の違い**

| | **`restart`** | **`reload`** |
|:--|:--|:--|
| プロセス | **いったん終了して作り直す** | **そのまま維持する** |
| 接続中のクライアント | **切れる** | **切れない** |
| 反映されるもの | すべての設定 | **アプリが再読込に対応した設定だけ** |
| 前提 | なし | **ユニットに `ExecReload=` がある**こと |

**`reload` に対応していないサービス**（`ExecReload=` が無いユニット）**で実行するとエラーになります。**
配布パッケージの `nginx` には `ExecReload=` があるので、下は自作の `myapp.service` を例にしています。

```text
Failed to reload myapp.service: Job type reload is not applicable for unit myapp.service.
```

**どちらでもよいなら `reload-or-restart`** を使うと、対応状況を気にせず済みます。

```bash
$ sudo systemctl reload-or-restart nginx   # reload できるならreload、無理ならrestart
```

**`restart` と `try-restart` の違い**

```text
restart      … 止まっていても起動する      ← 「動かしたい」とき
try-restart  … 止まっていれば何もしない    ← 「動いているものだけ入れ替えたい」とき
```

設定変更を一斉に反映するスクリプトでは、**止めておいたサービスを勝手に起こさない `try-restart`** が安全です。

**`kill` でシグナルを送る**

```bash
$ sudo systemctl kill nginx                      # 既定は SIGTERM を送る
$ sudo systemctl kill --signal=SIGHUP nginx      # HUP を送る（設定再読込を促す）
$ sudo systemctl kill --signal=SIGKILL nginx     # 強制終了させる（最終手段）
$ sudo systemctl kill --kill-whom=main nginx     # メインプロセスだけに送る
```

**`kill` コマンドとの違い**は、PID を調べなくてよいことと、
**ユニットに属するプロセスすべて**（cgroup 単位）に送れることです。

---

## 自動起動を設定する

```bash
$ sudo systemctl enable nginx        # OS起動時に自動起動する設定にする
$ sudo systemctl disable nginx       # 自動起動をやめる
$ sudo systemctl enable --now nginx  # 自動起動を設定して、いますぐ起動もする
$ sudo systemctl disable --now nginx # 自動起動をやめて、いますぐ停止もする
```

**`enable` は「いま起動する」ことではありません。**

```text
enable  … 次回のOS起動から自動で立ち上がるようにする   ← 未来の話
start   … いますぐ起動する                             ← いまの話
```

**構築時は `enable --now` をひとつ覚えておく**と、片方の忘れを防げます。

**`enable` が実際にしていること**

`[Install]` セクションの `WantedBy=` を見て、**対象ごとにシンボリックリンクを作るだけ**です。
`WantedBy=` に複数のターゲットが書かれていれば、その数だけリンクができます（`Also=` があればそちらも）。

```bash
$ sudo systemctl enable nginx        # 自動起動を有効にする
Created symlink /etc/systemd/system/multi-user.target.wants/nginx.service → /usr/lib/systemd/system/nginx.service.
```

**`[Install]` セクションが無いユニットは enable できません**（`static` と表示されます）。

**`mask` は disable より強い**

```bash
$ sudo systemctl mask nginx          # 起動そのものを禁止する
$ sudo systemctl unmask nginx        # 禁止を解除する
```

| | **`disable`** | **`mask`** |
|:--|:--|:--|
| 自動起動 | **しない** | **しない** |
| 手動の `start` | **できる** | **できない**（エラーになる） |
| 他ユニットの依存による起動 | **される** | **されない** |
| 実体 | シンボリックリンクを消す | **`/dev/null` へのリンクを作る** |

```text
Failed to start nginx.service: Unit nginx.service is masked.
```

**「絶対に起動させたくない」ときだけ `mask`** を使います。
運用でよくあるのは、**同じポートを使う別サービスを確実に止めておく**ケースです。

---

## 状態を1語で判定する

**`status` は人が読むためのもの**で、スクリプトでは扱いにくい形です。
**判定だけが欲しいときは `is-*` 系**を使います。

| コマンド | 出力例 | 終了コード |
|:--|:--|:--|
| **`systemctl is-active nginx`** | `active` / `inactive` / `failed` / `activating` | **active なら 0** |
| **`systemctl is-enabled nginx`** | `enabled` / `disabled` / `static` / `masked` など | **enabled なら 0** |
| **`systemctl is-failed nginx`** | `failed` / `active` など | **failed なら 0** |

```bash
$ systemctl is-active nginx          # 稼働中かどうかだけを表示する
active

$ systemctl is-active nginx -q && echo "動いています"   # 表示を抑えて終了コードだけ使う
動いています

$ systemctl is-enabled nginx         # 自動起動の設定状態だけを表示する
enabled
```

**`is-enabled` が返す値**

| 値 | 意味 |
|:--|:--|
| **`enabled`** | **`.wants/` などのシンボリックリンクで有効になっている** |
| `enabled-runtime` | `/run` 配下で一時的に有効。**再起動すると消える** |
| **`disabled`** | **`[Install]` セクションはあるが、有効になっていない** |
| **`static`** | **`[Install]` セクションが無く、enable できない**（依存や手動 start で動く） |
| **`masked`** | **起動が禁止されている** |
| `masked-runtime` | 一時的に禁止されている |
| `indirect` | 直接は有効でないが、他ユニットの `Also=` 経由で有効になる |
| `alias` | 別のユニットへの別名 |
| `linked` | 検索パス外のファイルへリンクされている |
| `generated` | ジェネレータが動的に作った（`/etc/fstab` から作られる `.mount` など） |
| `transient` | API 経由で一時的に作られた |

**`static` は「止まっている」という意味ではありません。**
「**enable するための設定を持っていない**」だけで、依存関係や `start` で普通に動きます。

---

## 出力の読み方は別ノートにある

**`status` / `show` / `cat` / `list-units` / `list-unit-files` / `list-dependencies` の出力を
1 語ずつ読み解く解説は、[systemctl 結果画面の見方](./systemctl_結果画面の見方.md) に移しました。**

| 知りたいこと | 打つコマンド |
|:--|:--|
| **いま動いているか。落ちたなら直前のログは** | **`systemctl status <名前>`** |
| **設定値が実際にいくつで効いているか** | **`systemctl show <名前>`** |
| **どのファイルが読まれ、何が上書きされているか** | **`systemctl cat <名前>`** |
| **いま読み込まれているユニットの一覧** | **`systemctl list-units`** |
| **インストール済みで、自動起動が有効か** | **`systemctl list-unit-files`** |
| **止めたら何が巻き添えになるか** | **`systemctl list-dependencies <名前>`** |

> `loaded` と `active` の違い、`enabled` と `vendor preset` の違いなど、
> **取り違えやすい語の対比表**も同じノートにまとめてあります。

---

## 失敗したユニットを扱う

```bash
$ systemctl --failed --no-pager      # 失敗しているユニットを一覧する
  UNIT        LOAD   ACTIVE SUB    DESCRIPTION
● ssh.service loaded failed failed OpenBSD Secure Shell server

1 loaded units listed.
```

**サーバに入ったらまず打つコマンド**のひとつです。何も出なければ、systemd 視点では異常なしです。

**原因を追う順番**

```bash
$ systemctl status ssh --no-pager --full     # ① Process/Main PID の終了コードを見る
$ journalctl -u ssh -n 50 --no-pager         # ② 直近のログを50行見る
$ systemctl cat ssh --no-pager               # ③ 設定（ExecStart/User/WorkingDirectory）を確認する
$ systemctl show ssh -p Result -p ExecMainStatus -p NRestarts   # ④ 失敗理由と再起動回数を確認する
```

**`Result=` が示す失敗の種類**

| 値 | 意味 |
|:--|:--|
| **`exit-code`** | **プログラムが 0 以外の終了コードで終わった** |
| **`signal`** | **シグナルで強制終了された**（`SIGKILL` など） |
| **`timeout`** | **`TimeoutStartSec=` 以内に起動が完了しなかった** |
| `core-dump` | 異常終了してコアダンプした |
| `watchdog` | ウォッチドッグのタイムアウト |
| `start-limit-hit` | **短時間に再起動を繰り返し、上限に達した** |
| `success` | 失敗していない |

**`start-limit-hit` になったとき**

```text
Failed to start myapp.service: Unit myapp.service has a start request repeated too quickly.
```

`Restart=always` のサービスが起動と失敗を繰り返すと、systemd が**再起動を打ち切ります**。
**原因を直したうえで、カウンタを消してから起動**します。

```bash
$ sudo systemctl reset-failed myapp          # failedの記録と再起動カウンタをリセットする
$ sudo systemctl start myapp                 # あらためて起動する
```

**`reset-failed` は原因を直しません。** 記録を消すだけです。

```text
reset-failed        … failedの記録と回数カウンタを消す
設定・プログラムの修正 … 原因そのものを直す      ← 本質はこちら
```

---

## daemon-reload が必要なとき

**systemd はユニットファイルをメモリに読み込んで動いています。**
ファイルを書き換えても、**読み直させるまで反映されません。**

```bash
$ sudo vi /etc/systemd/system/myapp.service  # ユニットファイルを編集する
$ sudo systemctl daemon-reload               # 編集内容をsystemdに読み直させる
$ sudo systemctl restart myapp               # サービス自体を入れ替える
```

**忘れると、systemd が警告を出します。**

```text
Warning: The unit file, source configuration file or drop-ins of myapp.service changed on disk.
Run 'systemctl daemon-reload' to reload units.
```

| 操作 | `daemon-reload` |
|:--|:--|
| **ユニットファイルを編集した** | **必要** |
| **drop-in を追加・削除した** | **必要** |
| `systemctl edit` を使った | **不要**（自動で実行される） |
| アプリの設定ファイル（`nginx.conf` など）を変えた | 不要（`reload` / `restart` だけでよい） |

**3 つの「リロード」を混同しないこと**

| コマンド | 対象 |
|:--|:--|
| **`systemctl daemon-reload`** | **systemd が読むユニットファイル** |
| **`systemctl reload ユニット`** | **そのサービスのアプリ設定** |
| `systemctl daemon-reexec` | **systemd 本体を再実行**（systemd を更新したとき） |

---

## ターゲットとシステム全体の操作

```bash
$ systemctl get-default              # 既定で起動するターゲットを確認する
multi-user.target

$ sudo systemctl set-default multi-user.target   # 既定をCUIモードに変更する
$ sudo systemctl isolate rescue.target           # いますぐレスキューモードへ移行する
```

| ターゲット | 意味 | 旧ランレベル |
|:--|:--|:--|
| `poweroff.target` | 電源断 | 0 |
| **`rescue.target`** | **シングルユーザモード**（最小限＋root シェル） | 1 |
| **`multi-user.target`** | **CUI でのマルチユーザ**。**サーバの既定** | 3 |
| **`graphical.target`** | **GUI 付きマルチユーザ** | 5 |
| `reboot.target` | 再起動 | 6 |
| `emergency.target` | 緊急モード（ファイルシステムは読み取り専用） | — |

```bash
$ sudo systemctl reboot              # 再起動する
$ sudo systemctl poweroff            # 電源を切る
$ sudo systemctl suspend             # サスペンドする
```

**`isolate` は強い操作です。** 指定したターゲットに必要なもの以外を**すべて停止**します。
**リモート接続中に実行すると、SSH ごと切れることがあります。**

### システム全体の状態を切り替えるサブコマンド

**ユニット名を取らず、システムそのものの状態を変えるサブコマンド**です。

| サブコマンド | 説明 |
|:--|:--|
| **`poweroff`** | **電源 OFF** |
| **`emergency`** | **緊急モードに移行** |
| **`rescue`** | **レスキューモードに移行** |
| **`default`** | **標準のモードに移行** |
| **`reboot`** | **再起動** |
| `halt` | システムを停止する（電源は切らない） |
| `suspend` / `hibernate` | サスペンド／休止状態にする |

**補足**

- **これらは `systemctl isolate <対応するターゲット>` の短縮形**です。たとえば `systemctl rescue` は `systemctl isolate rescue.target` とほぼ同じ動きをします
- **`halt` と `poweroff` の違い** … `halt` は「CPU を止めるところまで」、`poweroff` は「**電源も切る**」です。現在のハードウェアでは `poweroff` を使うのが普通です

---

### レスキューモードから通常の運用に戻す

**メンテナンスが終わったあと、通常のモードへ戻す方法は 3 つあります。**

| やり方 | コマンド | どういうときに選ぶか |
|:--|:--|:--|
| **標準のモードへ移行する** | **`systemctl default`** | **再起動したくない**とき。いちばん速い |
| **systemd 経由で再起動する** | **`systemctl reboot`** | **確実にきれいな状態から**上げ直したいとき |
| **再起動する（従来のコマンド）** | **`reboot`** | 上と同じ。打ち慣れているほう |

```bash
# レスキューモードで作業を終えたあと
$ systemctl default                                  # 再起動せずに標準のモードへ戻す
$ systemctl reboot                                   # または、再起動して通常起動させる
$ reboot                                             # 上とほぼ同じ（systemctl reboot へ転送される）
```

> **SysVinit の時代も、シングルユーザモードからの復帰は「再起動して標準のランレベルで上げ直す」方法が使われていました。**
> systemd でも同じ考え方で、**レスキューモードから再起動すれば通常のモードで起動します。**

**間違えやすい書き方**

| 書き方 | なぜ違うか |
|:--|:--|
| **`systemctl multi-user.target`** | **サブコマンドがありません。** ターゲット名だけでは動作が決まらない。**`systemctl isolate multi-user.target`** と書く |
| **`shutdown -h now`** | **システムを停止する**コマンド。通常運用には戻らない（`-h` は halt の意味） |
| **`telinit`（引数なし）** | **ランレベルの引数が必要**です。レスキューからの復帰なら `telinit 3`、再起動なら `telinit 6` |

**補足**

- **`telinit` は systemd 環境でも使えます。** 互換のために残されていて、数字を対応するターゲットへ読み替えてくれます。ただし**新しく書くなら `systemctl` のほうが意図が明確**です
- **`systemctl default` が失敗するときは、まだ落ちているユニットが残っています。** `systemctl --failed` で確認してから、原因を直して再度実行してください

---

## journalctl と組み合わせる

**`systemctl status` に出るログは末尾 10 行だけ**です。本格的に追うときは `journalctl` を使います。

```bash
$ journalctl -u nginx --no-pager             # nginxのログをすべて表示する
$ journalctl -u nginx -n 50 --no-pager       # 直近50行だけ表示する
$ journalctl -u nginx -f                     # 新しいログを追いかけて表示する（Ctrl+Cで終了）
$ journalctl -u nginx --since "1 hour ago"   # 直近1時間のログに絞る
$ journalctl -u nginx -b                     # 今回の起動以降のログだけに絞る
$ journalctl -u nginx -p err                 # エラー以上の重要度に絞る
```

**再起動をまたいで調べるときは `-b` が効きます。**

```bash
$ journalctl --list-boots | tail -5          # 起動の履歴を確認する
$ journalctl -u nginx -b -1 --no-pager       # 1つ前の起動時のログを見る
```

**`systemctl restart` の直後に落ちるサービス**は、`status` のログ 10 行では足りません。
**`journalctl -u サービス名 -n 100` まで広げる**と、原因のメッセージが見つかることが多いです。

---

## 参考リンク

- [man 1 systemctl](https://man7.org/linux/man-pages/man1/systemctl.1.html)
- [man 5 systemd.unit](https://man7.org/linux/man-pages/man5/systemd.unit.5.html)
- [man 5 systemd.service](https://man7.org/linux/man-pages/man5/systemd.service.5.html)
- [man 1 journalctl](https://man7.org/linux/man-pages/man1/journalctl.1.html)
- [Managing system services with systemctl — Red Hat Enterprise Linux 10](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_systemd_unit_files_to_customize_and_optimize_your_system/managing-system-services-with-systemctl)
- [AWS — cloud-init によるインスタンスの初期化](https://docs.aws.amazon.com/ja_jp/AWSEC2/latest/UserGuide/user-data.html)

---

[← 全体の目次にもどる](../README.md)
