# ユーザへの通知 wallとwriteとtalk

| | |
|:--|:--|
| **学習の順番** | Phase3 専門 ★★★☆☆ |
| **Ping-t の範囲** | Linux2 / システムの保守(主題206) — ユーザへのシステム関連事項の通知 |
| **業務での使いどころ** | **メンテナンス前の予告**。ログイン中の作業者に「17時に再起動します」を確実に届ける。踏み台サーバに複数人がぶら下がっている環境では、Slack より確実に目に入る |

> **ログイン時に自動で見せるメッセージ**は [ログインメッセージ issueとmotd](./ログインメッセージ_issueとmotd.md) にまとめています。

---

## 目次

- [四つのコマンドの役割分担](#四つのコマンドの役割分担)
- [wall 全員に一斉通知](#wall-全員に一斉通知)
  - [実際の出力](#実際の出力)
  - [日本語が化ける](#日本語が化ける)
  - [バナーを消す](#バナーを消す)
- [write 特定のユーザに送る](#write-特定のユーザに送る)
  - [相手を指定する](#相手を指定する)
  - [届かないとき](#届かないとき)
- [mesg 受信するかどうかを決める](#mesg-受信するかどうかを決める)
  - [正体はttyのパーミッション](#正体はttyのパーミッション)
  - [mesg-n が write を止めることの実測](#mesg-n-が-write-を止めることの実測)
- [talk 双方向で会話する](#talk-双方向で会話する)
- [shutdown による予告](#shutdown-による予告)
- [systemctl rescue の通知](#systemctl-rescue-の通知)
- [使い分けの早見表](#使い分けの早見表)
- [参考リンク](#参考リンク)

---

## 四つのコマンドの役割分担

```text
             送る相手            方向        用途
  wall  …  ログイン中の全員   一方向   メンテ予告・緊急連絡
  write …  指定した1人        一方向   個別の連絡
  talk  …  指定した1人        双方向   会話（画面を上下に分割）
  mesg  …  自分の端末         —        受信するかどうかの設定
```

**`wall` と `write` は一方向、`talk` だけが双方向**です。
`mesg` は送る側ではなく**受け取る側の設定**という点で毛色が違います。

---

## wall 全員に一斉通知

**`wall` は WriteALL の略**で、**ログイン中の全ユーザの端末**にメッセージを表示します。

```text
wall [オプション] [メッセージ]
```

メッセージは引数でも標準入力でも渡せます。

```bash
$ wall "17時にサーバを再起動します"          # 引数で渡す
$ echo "17時にサーバを再起動します" | wall    # パイプで渡す
$ wall /etc/maintenance.txt                  # ファイルの内容を流す
```

### 実際の出力

検証用に端末を1本作って受信側にし、実際に `wall` を撃ちました。

```bash
$ echo "The server will reboot at 17:00" | wall   # ASCII のメッセージを一斉送信する
```

**受け取った端末に出たもの**

```text
Broadcast message from root@vm (somewhere) (Wed Sep 23 14:54:35 2026):         

The server will reboot at 17:00                                                
```

**`Broadcast message from ユーザ@ホスト (端末) (日時):`** というバナーが自動で付きます。
誰がいつ送ったかが必ず残るので、受け取った側は無視しにくくなります。

行末に大量の空白が付いているのは仕様です。man にはこうあります。

```text
The command will wrap lines that are longer than 79 characters.
Short lines are whitespace padded to have 79 characters.
```

**79 文字で折り返し、短い行は 79 文字まで空白で埋める**ため、端末の行が上書きされて読みやすくなります。

### 日本語が化ける

**ここが実務で最も刺さる落とし穴です。**
同じことを日本語でやると、こうなりました。

```bash
$ wall "引数で渡した場合"                     # 日本語のメッセージを一斉送信する
```

```text
Broadcast message from root@vm (somewhere) (Wed Sep 23 14:54:36 2026):         

\345\274\225\346\225\260\343\201\247\346\270\241\343\201\227\343\201\237\345\240 
\264\345\220\210
```

**読めません。**
`wall`（util-linux 2.39.3）は**制御文字を防ぐために非 ASCII バイトを8進エスケープ**します。
その結果、UTF-8 の日本語はすべて `\NNN` 形式になります。

```text
   検証環境: wall from util-linux 2.39.3（Ubuntu 24.04）
   → 日本語のメンテ予告は wall で送ってはいけない
   → ASCII（英数字）で書くこと
```

```bash
$ wall "Maintenance 17:00-18:00 JST. Please logout."   # 英語なら正しく表示される
```

> **注意** … この挙動は util-linux の版によって異なる可能性があります。
> 手元の環境で一度テストしてから運用に入れてください。

### バナーを消す

`-n`（`--nobanner`）でバナーを抑止できます。**root のみが使えます。**

```bash
$ wall -n "Reboot in 5 minutes"             # バナーなしで送る
```

```text
Reboot in 5 minutes
```

```bash
$ su tu -c 'wall -n "test"'                 # 一般ユーザで -n を使ってみる
```

```text
wall: --nobanner is available only for root
```

| オプション | 意味 |
|:--|:--|
| `-n` / `--nobanner` | バナーを出さない。**root のみ**（実測） |
| `-t 秒` / `--timeout` | 端末への書き込みを諦めるまでの秒数。**既定 300 秒**（man の記載） |
| `-g グループ` / `--group` | **指定グループのメンバーにだけ**送る。グループ名でも GID でも可 |

**`-g` は覚えておくと便利**です。全員に撃つ必要がないときに使えます。

```bash
$ wall -g developers "Build server restarts at 15:00"   # developers グループにだけ送る
```

---

## write 特定のユーザに送る

**`write` は指定した1人の端末に**メッセージを送ります。

```text
write ユーザ名 [端末]
```

実行すると入力待ちになり、**Enter を押すたびに1行ずつ送信**されます。
**`Ctrl+D` で終了**します。

### 相手を指定する

```bash
$ echo -e "こんにちは\nテストです" | write root pts/4   # root の pts/4 に送る
```

**受け取った端末に出たもの**

```text
Message from root@vm on <no tty> at 14:54 ...
\343\201\223\343\202\223\343\201\253\343\201\241\343\201\257
\343\203\206\343\202\271\343\203\210\343\201\247\343\201\231
EOF
```

**`write` も同じく非 ASCII を8進エスケープします。** 日本語は使えません。
終了すると末尾に **`EOF`** が出ます。

**同じユーザが複数の端末でログインしている場合**は、端末名まで指定します。

```bash
$ who                                       # 誰がどの端末にいるか確認する
$ write tanaka pts/2                        # 端末を指定して送る
```

### 届かないとき

```bash
$ echo x | write root pts/99                # 存在しない端末を指定する
$ echo x | write nobody                     # ログインしていないユーザに送る
```

```text
write: root is not logged in on pts/99
write: nobody is not logged in
```

**`write` は utmp（ログイン中の記録）を見て相手を探します。**
`who` に出ないユーザには送れません。

---

## mesg 受信するかどうかを決める

**`mesg` は「自分の端末が `write` や `talk` を受け取るかどうか」**を切り替えるコマンドです。

```text
mesg [y|n]
```

| 書き方 | 意味 |
|:--|:--|
| `mesg` | 現在の設定を表示する |
| `mesg y` | 受信を**許可**する |
| `mesg n` | 受信を**拒否**する |

### 正体はttyのパーミッション

**`mesg` の実体は、自分の tty デバイスの書き込み権ビット**です。実測で確かめます。

```bash
$ tty                                       # 自分の端末を確認する
$ mesg                                      # 現在の設定を表示する
$ ls -l $(tty)                              # tty デバイスのモードを見る
```

```text
/dev/pts/5
is n
crw------- 1 root root 136, 5 Sep 23 14:54 /dev/pts/5
```

`mesg y` にすると、モードが変わります。

```bash
$ mesg y                                    # 受信を許可する
$ ls -l $(tty)                              # モードの変化を見る
$ mesg                                      # 設定を確認する
```

```text
crw--w--w- 1 root root 136, 5 Sep 23 14:54 /dev/pts/5
is y
```

```bash
$ mesg n                                    # 受信を拒否する
$ ls -l $(tty)                              # モードの変化を見る
```

```text
crw------- 1 root root 136, 5 Sep 23 14:54 /dev/pts/5
```

```text
   mesg y  →  crw--w--w-   （0622 … グループとその他の書き込み権が付く）
   mesg n  →  crw-------   （0600 … 書き込み権が外れる）
```

**`mesg y` が立てるのは、グループとその他の両方の書き込みビット**です。
`ls -l` の `-w-` が2つ並んでいるのはそのためです。

**`write` は setgid tty の実行ファイル**なので、実際に効くのは**グループ `tty` のビット**です。
そのビットが落ちていれば書けない、という単純な仕組みです。

**終了ステータスにも意味があります。**

| 状態 | 表示 | 終了ステータス |
|:--|:--|:--|
| 許可 | `is y` | **0** |
| 拒否 | `is n` | **1** |

スクリプトから判定するときに使えます。

```bash
$ mesg && echo "受信できる状態"              # 終了ステータスで分岐する
```

### mesg n が write を止めることの実測

一般ユーザ `tu` から root の端末に `write` を撃ち、モードを変えて挙動を比べました。

```bash
$ chmod 620 /dev/pts/4                      # mesg y 相当にする
$ su tu -c 'echo "from tu" | write-sgid root pts/4'   # 一般ユーザから送る
```

```text
Message from tu@vm on <no tty> at 14:55 ...
from tu
EOF
```

```bash
$ chmod 600 /dev/pts/4                      # mesg n 相当にする
$ su tu -c 'echo "from tu again" | write-sgid root pts/4'   # もう一度送る
```

```text
write-sgid: root has messages disabled on pts/4
```

**`has messages disabled` で弾かれました。**

> **検証環境について** … この Ubuntu イメージの `/usr/bin/write` には setgid tty が付いておらず
> （`-rwxr-xr-x`）、そのままでは一般ユーザから送信できませんでした。
> 上の実測は、`write` を複製して `chmod 2755` と `chgrp tty` を施したもの（`write-sgid`）で行っています。
> また検証用に自作した pty はグループが `root` だったため、`chgrp tty` も必要でした
> （`write: effective gid does not match group of /dev/pts/4` で弾かれます）。
> 通常の環境では `/usr/bin/write` が `-rwxr-sr-x root tty` で配布され、
> devpts が `gid=5(tty)` でマウントされるので、これらの追加操作は要りません。

**root は `mesg n` を無視して送信できます。** 緊急通知が確実に届くようにするためです。

---

## talk 双方向で会話する

**`talk` は指定した相手と画面を上下に分割して会話**するコマンドです。

```text
talk ユーザ名[@ホスト名] [端末]
```

```text
   ┌──────────────────────────┐
   │  一方が打った内容        │
   ├──────────────────────────┤
   │  もう一方が打った内容    │
   └──────────────────────────┘
```

> 上下どちらが自分の入力になるかは、実際に会話を成立させられていないため**確認していません。**

**流れ**

```text
  1. こちらが talk 相手 を実行する
  2. 相手の端末に「talk リクエストが来ている」という案内が出る
  3. 相手も talk こちら を実行すると接続が確立する
  4. Ctrl+C で終了する
```

**`talk` は talk デーモンを経由します。**
実測すると、デーモンが動いていない環境では次のようになりました。

```bash
$ talk root pts/4                           # 相手に talk を申し込む
```

```text
[No connection yet]
[ Error on read from talk daemon: Connection refused ]
```

画面が上下に分割され、`[No connection yet]` の表示のあと、
**talk デーモンに接続できずエラー**になっています。

デーモンは `inetd` / `xinetd` 経由で起動されるのが一般的です。

```bash
$ grep -E '^(talk|ntalk)' /etc/services     # 使用するポートを確認する
```

```text
talk		517/udp
ntalk		518/udp
```

**UDP の 517 / 518 番**を使います。ファイアウォールがあると通りません。

> **実測できていないこと** … この環境では `in.talkd` を起動していないため、
> 実際に会話が成立する様子は確認していません。上記は接続失敗時の出力です。

**`talk` は現在ほとんど使われません。**
標準では入っていないことが多く、UDP のポートを開ける必要もあるためです。
試験対策として「双方向なのは talk だけ」という区別を押さえておけば十分です。

```bash
$ talk root pts/4 < /dev/null                # 標準入力がパイプだと動かない
```

```text
Standard input must be a tty, not a pipe or a file
```

**`talk` は対話型なので、スクリプトからは使えません。**

---

## shutdown による予告

**`shutdown` も通知機能を持っています。**
引数にメッセージを書くと、`wall` と同じ形でログイン中の全員に流れます。

```bash
$ shutdown -h +10 "Maintenance. Please save your work."   # 10分後に停止する予告を出す
```

**`-k` を付けると、実際には停止せず通知だけ**を行います。

```bash
$ shutdown --help | grep -- '-k'            # -k の説明を確認する
```

```text
  -k             Don't halt/power-off/reboot, just send warnings
```

| オプション | 意味 |
|:--|:--|
| `-h` | 停止する（`--poweroff` と同等。`--halt` が指定されていればそちら） |
| `-r` | 再起動する |
| `-H` | halt する |
| `-P` | 電源を切る |
| **`-k`** | **停止せず警告だけ送る** |
| `-c` | 予約された shutdown を取り消す |
| `--no-wall` | 停止前の wall メッセージを出さない |

```text
   shutdown -k +10 "メッセージ"   →  通知だけ（wall とほぼ同じ）
   shutdown -h +10 "メッセージ"   →  通知 + 10分後に本当に落ちる
```

**`-k` は「予行演習」として使えます。**
通知の文面と届き方を確認してから、本番の `-h` を撃つ、という手順が安全です。

---

## systemctl rescue の通知

systemd 環境でレスキューモードへ移行するコマンドは **`systemctl rescue`** です。

```bash
$ systemctl rescue                          # レスキューモードへ移行する
$ systemctl isolate rescue.target           # ほぼ同じ動作
```

**「この2つは通知の有無が違う」と教わりますが、systemd の版によって記述が変わっています。**

古い systemd の man（Ubuntu 14.04 同梱のものなど）には、はっきりこう書かれています。

```text
Enter rescue mode. This is mostly equivalent to isolate rescue.target
but also prints a wall message to all users.
```

**「mostly equivalent（ほぼ同じ）だが、全ユーザに wall メッセージを出す」** — これが試験で問われる形です。

| コマンド | ログイン中ユーザへの警告 |
|:--|:--|
| `systemctl rescue` | **送る**（古い systemd の man の記述） |
| `systemctl isolate rescue.target` | 送らない |

**ところが systemd 255（Ubuntu 24.04）の man では、この記述が消えています。** 実測しました。

```bash
$ zcat /usr/share/man/man1/systemctl.1.gz | grep -A3 'Enter rescue mode'   # 現在の man を確認する
```

```text
Enter rescue mode\&. This is equivalent to
\fBsystemctl isolate rescue\&.target\fR\&. This operation is blocking by default, use
\fB\-\-no\-block\fR
to request asynchronous behavior\&.
```

**`mostly` が取れ、wall への言及も無くなりました。**
`--no-wall` の説明も、対象が halt / power-off / reboot に限定されています。

```bash
$ systemctl --help | grep no-wall           # --no-wall の対象を確認する
```

```text
     --no-wall           Don't send wall message before halt/power-off/reboot
```

```text
   試験対策    … 「systemctl rescue は wall を送る」で覚える（教材の前提）
   手元の運用  … man を必ず確認する。systemd 255 では保証されていない
```

> **実測できていないこと** … この検証環境ではコンテナ内のため systemd が PID 1 で動いておらず、
> `systemctl rescue` の**実行**は確認していません。上記は man と `--help` の実測です。

> レスキューモードそのものは
> [SysVinitの起動スクリプトとランレベル](../05_起動プロセスとカーネル/SysVinitの起動スクリプトとランレベル.md) と
> [systemctl サービスの操作と確認](../05_起動プロセスとカーネル/systemctl_サービスの操作と確認.md) を参照してください。

---

## 使い分けの早見表

| やりたいこと | 使うもの |
|:--|:--|
| ログイン中の全員に予告する | `wall` |
| 特定のグループだけに予告する | `wall -g グループ` |
| 特定の1人に連絡する | `write ユーザ [端末]` |
| 相手と会話する | `talk ユーザ` |
| 自分宛のメッセージを拒否する | `mesg n` |
| 停止せずに停止予告だけ流す | `shutdown -k 時刻 "メッセージ"` |
| これからログインする人に見せる | `/etc/issue`（ログイン前）／`/etc/motd`（ログイン後） |

**通知が「いつ」届くかで選ぶ**と迷いません。

```text
   今すでにログインしている人へ   → wall / write / shutdown -k
   これからログインする人へ       → /etc/issue / /etc/motd
```

**日本語を使う場合の注意をもう一度。**
`wall` と `write` は非 ASCII を8進エスケープするため、**日本語のメッセージは読めません。**
メンテナンス予告は英数字で書くか、`/etc/motd` 側に日本語を置いてください。

---

## 参考リンク

- [man 1 wall](https://man7.org/linux/man-pages/man1/wall.1.html)
- [man 1 write](https://man7.org/linux/man-pages/man1/write.1.html)
- [man 1 mesg](https://man7.org/linux/man-pages/man1/mesg.1.html)
- [man 1 talk](https://man7.org/linux/man-pages/man1/talk.1.html)
- [man 8 shutdown（systemd）](https://man7.org/linux/man-pages/man8/shutdown.8.html)
- [man 1 systemctl](https://man7.org/linux/man-pages/man1/systemctl.1.html)

---

[← 全体の目次にもどる](../README.md)
