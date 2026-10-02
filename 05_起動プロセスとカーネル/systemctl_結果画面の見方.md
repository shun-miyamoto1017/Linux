# systemctl 結果画面の見方

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★★★ |
| **Ping-t の範囲** | Linux1 / システムアーキテクチャ(主題101) — システムの起動 ／ Linux2 / システムの起動とLinuxカーネル(主題2.01) — システム起動のカスタマイズ |
| **業務での使いどころ** | **`systemctl` の出力に並んだ語を、ひとつ残らず読み切るための逆引き**。「`activating (start-post)` って何？」「`vendor preset` と `enabled` の違いは？」で開く |

> **このノートは「出力の読み方」だけを集めたもの**です。
> コマンドの打ち方・サブコマンド一覧・オプションは [systemctl サービスの操作と確認](./systemctl_サービスの操作と確認.md)、
> ユニットファイルの書き方は [systemd 基本とユニットファイル](./systemd_基本とユニットファイル.md) にまとめています。

---

## 目次

- [systemctl status の結果画面の見方](#systemctl-status-の結果画面の見方)
- [systemctl show の結果画面の見方](#systemctl-show-の結果画面の見方)
- [systemctl cat の結果画面の見方](#systemctl-cat-の結果画面の見方)
- [systemctl list-units の結果画面の見方](#systemctl-list-units-の結果画面の見方)
- [systemctl list-unit-files の結果画面の見方](#systemctl-list-unit-files-の結果画面の見方)
- [systemctl list-dependencies の結果画面の見方](#systemctl-list-dependencies-の結果画面の見方)
- [出力の読み違いでよくあるもの](#出力の読み違いでよくあるもの)
- [参考リンク](#参考リンク)

---

## systemctl status の結果画面の見方

```bash
$ systemctl status nginx --no-pager --full   # 状態と直近ログを省略なしで表示する
● nginx.service - The nginx HTTP and reverse proxy server
     Loaded: loaded (/usr/lib/systemd/system/nginx.service; enabled; preset: disabled)
     Active: active (running) since Fri 2026-09-05 08:30:00 JST; 2h 5min ago
       Docs: man:nginx(8)
    Process: 1230 ExecStartPre=/usr/bin/rm -f /run/nginx.pid (code=exited, status=0/SUCCESS)
   Main PID: 1234 (nginx)
      Tasks: 3 (limit: 4653)
     Memory: 8.5M
        CPU: 120ms
     CGroup: /system.slice/nginx.service
             ├─1234 "nginx: master process /usr/sbin/nginx"
             └─1235 "nginx: worker process"

Sep 05 08:30:00 web01 systemd[1]: Starting The nginx HTTP and reverse proxy server...
Sep 05 08:30:00 web01 systemd[1]: Started The nginx HTTP and reverse proxy server.
```

**画面は「上のヘッダ」と「下のログ」に分かれます。**

**1行目 … ユニット名と説明**

```text
● nginx.service - The nginx HTTP and reverse proxy server
│ └────┬────┘   └──────────────┬──────────────┘
│   ユニット名          Description= の内容
└ 状態を表す印
```

**先頭の印は状態を表します**（端末が色に対応していれば色も付きます）。

| 印 | 状態 |
|:--|:--|
| **`●`（白/緑）** | **active。動いている** |
| **`×` または `●`（赤）** | **failed。失敗している** |
| `○` | inactive。止まっている |
| `↻` | activating / reloading。切り替え中 |

**Loaded 行 … 設定を読み込めたか**

```text
Loaded: loaded (/usr/lib/systemd/system/nginx.service; enabled; preset: disabled)
        └──┬─┘ └──────────────┬──────────────┘  └──┬──┘  └───────┬───────┘
      読み込み状態      ユニットファイルの場所    自動起動   ディストリの既定値
```

| 値 | 意味 |
|:--|:--|
| **`loaded`** | **ユニットファイルを正常に読み込めた** |
| **`not-found`** | **ユニットファイルが見つからない**（名前の打ち間違い、未インストール） |
| **`bad-setting`** | ユニットファイルの書式に誤りがある |
| **`error`** | 読み込み時にエラーが起きた（権限など） |
| **`masked`** | 起動が禁止されている |

**`loaded` は「動いている」ではありません。** 設定を読めただけです。

**Active 行 … いまどの状態か**

```text
Active: active (running) since Fri 2026-09-05 08:30:00 JST; 2h 5min ago
        └──┬─┘ └──┬──┘       └──────────┬──────────┘  └───┬──┘
     ActiveState  SubState        その状態になった日時    経過時間
```

**`ActiveState`（大まかな状態）**

| 値 | 意味 |
|:--|:--|
| **`active`** | **有効。動いている** |
| **`inactive`** | **止まっている**（正常停止も含む） |
| **`failed`** | **失敗が記録されている** |
| `activating` | 起動処理の途中 |
| `deactivating` | 停止処理の途中 |
| `reloading` | 設定を再読込中 |

**`SubState`（詳しい状態。ユニットの種類ごとに値が違う）**

| 値 | 意味 |
|:--|:--|
| **`running`** | **メインプロセスが実行中** |
| **`exited`** | **プロセスは終了したが、ユニットは有効なまま**（`RemainAfterExit=yes`） |
| **`dead`** | **実行中のプロセスが無い** |
| `start-pre` / `start` / `start-post` | 起動処理の各段階 |
| `auto-restart` | `Restart=` により再起動待ち |
| `failed` | 失敗して止まっている |

**Docs 行 … 参照すべきドキュメント**

`[Unit]` の `Documentation=` の内容です。`man:nginx(8)` とあれば `man 8 nginx` で読めます。

**Process 行 … 補助コマンドの実行結果**

`ExecStartPre=` / `ExecStartPost=` / `ExecStop=` の結果が並びます。
**起動に失敗したときは、この行に原因が出ていることが多い**ので必ず見ます。

```text
Process: 1230 ExecStartPre=/usr/sbin/nginx -t (code=exited, status=1/FAILURE)
              └───────┬───────┘              └────┬────┘  └────┬────┘
            実行されたコマンド              終了のしかた    終了コード
```

**Main PID 行 … 主役のプロセス**

```text
Main PID: 1234 (nginx)
```

失敗しているときは、ここに終了理由が入ります。

```text
Main PID: 1234 (code=exited, status=203/EXEC)
```

| `status=` の例 | 意味 |
|:--|:--|
| **`0/SUCCESS`** | **正常終了** |
| **`1/FAILURE`** | **プログラムが終了コード 1 で失敗した** |
| **`203/EXEC`** | **実行ファイルを起動できなかった**（パス間違い、実行権限なし） |
| **`200/CHDIR`** | `WorkingDirectory=` に移動できなかった |
| **`217/USER`** | **`User=` に指定したユーザが存在しない** |
| `226/NAMESPACE` | サンドボックス設定の適用に失敗した |

**`203/EXEC` と `217/USER` は自作サービスの二大失敗**です。まずここを疑います。

**Tasks / Memory / CPU 行 … 使っている資源**

```text
Tasks: 3 (limit: 4653)     ← いまのプロセス+スレッド数と、上限
Memory: 8.5M               ← このユニットが使っているメモリ
CPU: 120ms                 ← 起動してから積み上がった CPU 時間
```

**`Tasks` が `limit` に張り付いていると、新しいプロセスを作れずエラーになります。**

**CGroup 行 … このユニットに属するプロセスの木**

```text
CGroup: /system.slice/nginx.service
        ├─1234 "nginx: master process /usr/sbin/nginx"
        └─1235 "nginx: worker process"
```

**`ps` で追わなくても、そのサービスの子プロセスまで一目で分かります。**
`systemctl stop` や `kill` は、**この木に含まれるプロセスすべて**が対象になります。

**最下部 … 直近のログ**

`journalctl -u ユニット名` の末尾 10 行が表示されます。行数は `-n` で変えられます。

```bash
$ systemctl status nginx -n 50 --no-pager   # 直近50行のログまで見る
$ systemctl status nginx -n 0               # ログを出さずヘッダだけ見る
```

**引数なしで実行するとシステム全体の状態**が出ます。

```bash
$ systemctl status --no-pager | head -20    # システム全体のユニットツリーを見る
```

---

## systemctl show の結果画面の見方

**`show` は、systemd がメモリ上で保持している設定値と状態を、`キー=値` の形で表示します。**

```bash
$ systemctl show nginx --no-pager | head -5   # 全プロパティを表示する（数百行になる）
Type=forking
Restart=no
NotifyAccess=none
RestartUSec=100ms
TimeoutStartUSec=1min 30s
```

**必要なものだけ取り出す**

```bash
$ systemctl show nginx -p Type               # Type だけを表示する
Type=forking

$ systemctl show nginx -p Type --value       # 値だけを表示する（スクリプト向き）
forking

$ systemctl show nginx -p ActiveState -p SubState -p MainPID   # 複数まとめて表示する
ActiveState=active
SubState=running
MainPID=1234
```

**調査でよく使うプロパティ**

| プロパティ | 意味 |
|:--|:--|
| **`FragmentPath`** | **読み込んだメインユニットファイルの場所** |
| **`DropInPaths`** | **適用されている drop-in ファイルの場所** |
| **`UnitFileState`** | **`is-enabled` と同じ値**（enabled / disabled / static …） |
| **`ActiveState`** / **`SubState`** | 大まかな状態 / 詳しい状態 |
| **`Type`** | 起動完了の判断方法 |
| **`ExecStart`** | 実行されるコマンド（解析済みの形） |
| **`MainPID`** | メインプロセスの PID |
| **`Result`** | **失敗の理由**（`exit-code` / `timeout` / `signal` / `success`） |
| **`ExecMainCode`** / **`ExecMainStatus`** | **終了のしかた / 終了コード** |
| **`NRestarts`** | これまでに再起動した回数 |
| `ActiveEnterTimestamp` | active になった日時 |
| `ConditionResult` | `Condition*=` の判定結果（`no` なら条件で起動がスキップされた） |

```bash
$ systemctl show nginx -p FragmentPath -p DropInPaths -p UnitFileState   # 設定の出どころを確認する
FragmentPath=/usr/lib/systemd/system/nginx.service
DropInPaths=/etc/systemd/system/nginx.service.d/override.conf
UnitFileState=enabled
```

**`status` と `show` と `cat` の使い分け**

| | **`status`** | **`show`** | **`cat`** |
|:--|:--|:--|:--|
| 何が出るか | **人向けの要約＋ログ** | **systemd が持つ全プロパティ** | **設定ファイルの生の中身** |
| 既定値 | 出ない | **出る**（書いていない項目も既定値が見える） | **出ない**（書いてあることだけ） |
| 向いている用途 | **障害の一次確認** | **スクリプト・厳密な確認** | **どのファイルにどう書かれているか** |

**「設定したはずの値が効いていない」ときは `cat` と `show` を突き合わせます。**
**`cat` に書いてあるのに `show` の値が違う**なら、**他の drop-in が後から上書きしている**と分かります。

---

## systemctl cat の結果画面の見方

**`cat` は、メインユニットファイルと drop-in を、systemd が読む順番どおりに並べて表示します。**

```bash
$ systemctl cat nginx --no-pager     # ユニットファイルとdrop-inをまとめて表示する
# /usr/lib/systemd/system/nginx.service
[Unit]
Description=The nginx HTTP and reverse proxy server
After=network.target

[Service]
Type=forking
ExecStart=/usr/sbin/nginx

# /etc/systemd/system/nginx.service.d/override.conf
[Service]
Restart=always
```

**先頭が `#` で始まる行はファイルの区切りです。**

```text
# /usr/lib/systemd/system/nginx.service      ← ここから下が本体の内容
# /etc/systemd/system/nginx.service.d/...    ← ここから下が drop-in の内容
```

**この `#` 行は設定項目ではありません。** `systemctl cat` が付けている案内です。

**通常の `cat` との違い**

```bash
$ cat /usr/lib/systemd/system/nginx.service  # 指定した1ファイルだけを表示する
```

| | **`systemctl cat`** | **通常の `cat`** |
|:--|:--|:--|
| 表示範囲 | **本体 ＋ すべての drop-in** | **指定した 1 ファイルだけ** |
| ファイルの場所 | **自動で探す** | 自分でパスを調べる必要がある |
| 見落とし | **しにくい** | **drop-in を見落とす** |

**設定調査は必ず `systemctl cat` から始めます。**
`/usr/lib/...` の本体だけを読んで「`Restart=` は設定されていない」と判断すると、
`/etc/systemd/system/*.d/override.conf` にある設定を見落とします。

**安全に編集する `systemctl edit`**

```bash
$ sudo systemctl edit nginx          # drop-in（override.conf）を作って編集する
$ sudo systemctl edit --full nginx   # 本体を /etc 配下にコピーして丸ごと編集する
$ sudo systemctl revert nginx        # 編集を取り消してパッケージ提供の状態に戻す
```

**`/usr/lib/systemd/system/` のファイルを直接編集してはいけません。**
**パッケージを更新すると上書きされて消えます。** `systemctl edit` なら `/etc` 配下に置かれるため残ります。
`edit` は保存後に **`daemon-reload` まで自動で実行**してくれます。

---

## systemctl list-units の結果画面の見方

**`list-units` は、いま systemd がメモリに読み込んでいるユニットの一覧です。**

```bash
$ systemctl list-units --type=service --no-pager   # serviceユニットの一覧を表示する
  UNIT              LOAD   ACTIVE SUB     DESCRIPTION
  cron.service      loaded active running Regular background program processing daemon
  nginx.service     loaded active running The nginx HTTP and reverse proxy server
● ssh.service       loaded failed failed  OpenBSD Secure Shell server

Legend: LOAD   → Reflects whether the unit definition was properly loaded.
        ACTIVE → The high-level unit activation state, i.e. generalization of SUB.
        SUB    → The low-level unit activation state, values depend on unit type.

3 loaded units listed.
```

| 列 | 意味 | 見るポイント |
|:--|:--|:--|
| **`UNIT`** | **ユニット名** | 先頭の `●` は**異常があるユニットの目印** |
| **`LOAD`** | **設定を読み込めたか** | **`not-found` は名前間違いか未インストール** |
| **`ACTIVE`** | **大まかな状態** | `active` / `inactive` / `failed` |
| **`SUB`** | **詳しい状態** | `running` / `exited` / `dead` |
| **`DESCRIPTION`** | **`Description=` の内容** | 何のサービスか |

**既定では inactive なユニットは出ません。**

```bash
$ systemctl list-units --type=service --all --no-pager      # 停止中のものも含めて全部出す
$ systemctl list-units --type=service --state=failed        # 失敗しているものだけ
$ systemctl list-units --type=service --state=running       # 動いているものだけ
$ systemctl list-units --type=timer --no-pager              # timer ユニットの一覧
```

**`list-units` と `list-unit-files` の違い**

```text
list-units       … いまメモリに読み込まれているもの      ← 「動いている世界」
list-unit-files  … ディスクに存在するユニットファイル    ← 「インストールされている世界」
```

**インストールされているのに一度も使われていないユニットは、`list-units` には出ません。**

---

## systemctl list-unit-files の結果画面の見方

```bash
$ systemctl list-unit-files --type=service --no-pager   # インストール済みのserviceユニットを一覧する
UNIT FILE                  STATE    PRESET
cron.service               enabled  enabled
nginx.service              disabled disabled
systemd-journald.service   static   -
firewalld.service          masked   enabled

4 unit files listed.
```

| 列 | 意味 |
|:--|:--|
| **`UNIT FILE`** | **ユニットファイル名** |
| **`STATE`** | **現在の有効／無効の状態**（`is-enabled` と同じ値） |
| **`PRESET`** | **ディストリが定めた既定値**。`preset` を実行するとこの値に戻る |

**`STATE` と `PRESET` がずれている行が「管理者が意図的に変えたところ」**です。
サーバの棚卸しでは、ここを見ると**手で変更された設定**が浮かび上がります。

```bash
$ systemctl list-unit-files --state=enabled --no-pager      # 自動起動が有効なものだけ一覧する
$ systemctl list-unit-files --state=masked --no-pager       # 禁止されているものだけ一覧する
$ systemctl list-unit-files 'ssh*' --no-pager               # 名前で絞り込む
```

---

## systemctl list-dependencies の結果画面の見方

```bash
$ systemctl list-dependencies nginx --no-pager   # nginxが必要とする・欲するユニットをツリー表示する
nginx.service
● ├─system.slice
● ├─sysinit.target
● │ ├─systemd-journald.service
● │ └─systemd-tmpfiles-setup.service
● └─network.target
```

| 記号 | 意味 |
|:--|:--|
| **`●`（緑）** | **そのユニットは active** |
| **`○`** | **inactive** |
| **`×`（赤）** | **failed** |
| `├─` / `└─` | ツリーの枝 |

**既定では `Requires=` と `Wants=` をたどります。** 起動順序（`After=` / `Before=`）は含まれません。

```bash
$ systemctl list-dependencies nginx --reverse      # 「nginxに依存している側」を逆向きにたどる
$ systemctl list-dependencies nginx --all          # 展開を省略せず、すべて展開する
$ systemctl list-dependencies nginx --plain        # ツリー記号なしの平らな一覧にする
$ systemctl list-dependencies multi-user.target    # ターゲットに紐づくユニットを見る
```

**`--reverse` が役に立つ場面**

「このサービスを止めたら、何が巻き添えで止まるのか」を事前に確認できます。
**メンテナンス前の影響範囲確認**に使います。

---

## 出力の読み違いでよくあるもの

**同じような語が並ぶので、意味を取り違えやすいところをまとめます。**

| 見た目 | 正しい意味 | 取り違えやすい相手 |
|:--|:--|:--|
| **`loaded`** | **ユニットファイルを読み込めている**（＝定義が見つかった） | **動いているという意味ではない**。稼働の有無は `active` 側を見る |
| **`active (exited)`** | **処理は正常に終わり、ユニットとしては生きている扱い** | `inactive (dead)` と違い、**異常ではない**（`Type=oneshot` の正常形） |
| **`enabled`** | **次回起動時に自動で上がる設定** | **いま動いているかとは無関係**。`active` と混同しない |
| **`vendor preset: enabled`** | **ディストリが決めた既定値** | **いまの設定ではない**。いまの設定は行頭の `enabled` / `disabled` |
| **`static`** | **`[Install]` が無く、`enable` できない**（他から必要とされて起動する） | `disabled` と違い、**有効化し忘れではない** |
| **`masked`** | **`/dev/null` へのリンクで、起動そのものが禁止されている** | `disabled` より強い。`start` しても起動しない |
| **`inactive (dead)`** | **止まっている**（正常に止めた場合も含む） | `failed` と違い、**異常とは限らない** |
| **`failed`** | **異常終了した記録が残っている** | 直すまで残る。`systemctl reset-failed` で消える |

**補足**

- **`status` の 1 行目の色は判断材料になりません。** 端末の設定で出ないことがあります。**語そのもの**を読んでください
- **迷ったら 1 語で返させるのが確実です。** `systemctl is-active <名前>` / `is-enabled <名前>` / `is-failed <名前>` なら、解釈の余地がありません（[systemctl サービスの操作と確認](./systemctl_サービスの操作と確認.md) の「状態を1語で判定する」）

---

## 参考リンク

- [man 1 systemctl](https://man7.org/linux/man-pages/man1/systemctl.1.html)
- [man 5 systemd.unit](https://man7.org/linux/man-pages/man5/systemd.unit.5.html)
- [man 5 systemd.service](https://man7.org/linux/man-pages/man5/systemd.service.5.html)
- [man 5 systemd.directives（ディレクティブの逆引き索引）](https://man7.org/linux/man-pages/man7/systemd.directives.7.html)
- [man 1 journalctl](https://man7.org/linux/man-pages/man1/journalctl.1.html)
- [Managing system services with systemctl — Red Hat Enterprise Linux 10](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_systemd_unit_files_to_customize_and_optimize_your_system/managing-system-services-with-systemctl)

---

[← 全体の目次にもどる](../README.md)
