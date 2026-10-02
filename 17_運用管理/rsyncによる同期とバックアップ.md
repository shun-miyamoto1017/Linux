# rsyncによる同期とバックアップ

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★★ |
| **Ping-t の範囲** | Linux2 / システムの保守(主題206) — バックアップ操作 |
| **業務での使いどころ** | **差分だけ送るので、日次の同期がとにかく速い**。サーバ移設のデータ移行、ログの退避、静的コンテンツの配布、EC2 から EFS への流し込み。`aws s3 sync` の考え方も rsync とほぼ同じなので、ここを押さえるとクラウド側も迷わない |

> **方式（フル・差分・増分）の設計**は [バックアップの方式と設計](./バックアップの方式と設計.md)、
> **アーカイブ形式そのもの**は [圧縮とアーカイブ](../01_シェルとコマンドライン/圧縮とアーカイブ.md) にまとめています。

---

## 目次

- [rsyncとは](#rsyncとは)
- [書式](#書式)
- [末尾のスラッシュが最大の事故ポイント](#末尾のスラッシュが最大の事故ポイント)
- [よく使うオプション](#よく使うオプション)
  - [アーカイブモード](#アーカイブモード)
  - [詳細表示](#詳細表示)
  - [圧縮転送](#圧縮転送)
  - [転送元にないものを消す](#転送元にないものを消す)
  - [まず試す](#まず試す)
- [リモートホストとやりとりする](#リモートホストとやりとりする)
  - [書式はコロンで区切る](#書式はコロンで区切る)
  - [既定の転送方式は ssh](#既定の転送方式は-ssh)
  - [rsync デーモンに繋ぐ場合](#rsync-デーモンに繋ぐ場合)
- [cp や scp との使い分け](#cp-や-scp-との使い分け)
- [実務での書き方](#実務での書き方)
- [参考リンク](#参考リンク)

---

## rsyncとは

**`rsync` は、2か所の内容をそろえる（同期する）コマンド**です。
単純なコピーとの決定的な違いは、**すでに同じものは送らない**ことです。

```text
   cp / scp … 毎回すべてを転送する
   rsync    … サイズとタイムスタンプを比べ、違うものだけ転送する
              さらにファイル内部も差分（ブロック単位）で送れる
```

100GB のディレクトリで 1MB だけ変わったとき、**実際に流れるのは 1MB 前後**です。
夜間の同期ジョブが rsync だらけになるのはこのためです。

---

## 書式

```text
rsync [オプション] 転送元 転送先
```

`cp` と同じ並びです。**左が元、右が先**。

```bash
$ rsync -av src/ dst/                       # src の中身を dst にそろえる
```

```text
sending incremental file list
a.txt
sub/
sub/b.txt

sent 245 bytes  received 66 bytes  622.00 bytes/sec
total size is 12  speedup is 0.04
```

`speedup` は「実際に送ったバイト数に対して、何倍の量を同期できたか」です。
2回目以降は差分しか流れないので、この数字が跳ね上がります。

---

## 末尾のスラッシュが最大の事故ポイント

**転送元の末尾にスラッシュを付けるかどうかで、結果が変わります。**

```bash
$ rsync -a src/ d1/                         # 末尾スラッシュあり
$ rsync -a src  d2/                         # 末尾スラッシュなし
```

```text
[ src/ の場合 … 中身だけが入る ]
d1
d1/a.txt
d1/sub
d1/sub/b.txt

[ src の場合 … src ディレクトリごと入る ]
d2
d2/src
d2/src/a.txt
d2/src/sub
d2/src/sub/b.txt
```

**覚え方**

```text
   src/   … 「src の中身を」  → dst の直下に展開される
   src    … 「src そのものを」 → dst/src ができる
```

**転送先の末尾スラッシュは結果に影響しません。**
気にするのは**転送元だけ**です。

この違いは `--delete` と組み合わせたときに致命的になります。
`src` のつもりで `src/` と書いて `--delete` を付けると、**転送先の中身が丸ごと入れ替わります。**

---

## よく使うオプション

| オプション | 意味 |
|:--|:--|
| `-a` | アーカイブモード。属性を保ったまま再帰コピー |
| `-v` | 詳細表示。転送したファイル名と合計を出す |
| `-z` | 転送データを圧縮する |
| `-n` | 実際には転送せず、何が起きるかだけ表示する |
| `--delete` | 転送元にないものを転送先から削除する |
| `-e` | リモートシェルを指定する |
| `-r` | 再帰的にコピーする（`-a` に含まれる） |
| `-P` | 進捗表示＋中断したファイルの再開 |
| `--exclude` | 除外するパターンを指定する |

### アーカイブモード

**`-a` は「属性を保ったまま丸ごと」**という意味の、いちばん使うオプションです。

```bash
$ rsync --help | grep -- '--archive'        # -a の実体を確認する
```

```text
--archive, -a            archive mode is -rlptgoD (no -A,-X,-U,-N,-H)
```

つまり `-a` は次の 7 つをまとめたものです。

| 内訳 | 意味 |
|:--|:--|
| `-r` | 再帰的に |
| `-l` | シンボリックリンクはリンクのままコピー |
| `-p` | パーミッションを保持 |
| `-t` | タイムスタンプを保持 |
| `-g` | グループを保持 |
| `-o` | 所有者を保持（root で実行した場合） |
| `-D` | デバイスファイルと特殊ファイルを保持 |

**実測で確かめます。**

```bash
$ chmod 0640 src/a.txt                      # 元のパーミッションを変えておく
$ chown tu:tu src/sub/b.txt                 # 元の所有者も変えておく
$ rsync -av src/ dst/                       # -a で同期する
$ ls -l src/a.txt dst/a.txt                 # パーミッションを比べる
$ ls -l src/sub/b.txt dst/sub/b.txt         # 所有者を比べる
```

```text
-rw-r----- 1 root root 6 Sep 23 14:51 dst/a.txt
-rw-r----- 1 root root 6 Sep 23 14:51 src/a.txt
-rw-r--r-- 1 tu tu 6 Sep 23 14:51 dst/sub/b.txt
-rw-r--r-- 1 tu tu 6 Sep 23 14:51 src/sub/b.txt
```

パーミッションも所有者も、そのまま引き継がれています。

**注意** … `-a` に**ACL（`-A`）と拡張属性（`-X`）は含まれません。**
SELinux のラベルや POSIX ACL を保ちたい場合は `-aAX` と明示します。

### 詳細表示

`-v` は転送したファイル名と合計バイト数を出します。
**ジョブのログに残すなら必須**です。何も出さずに終わったジョブは、成功したのか対象が無かったのか区別できません。

### 圧縮転送

`-z` は**ネットワークに流す前にデータを圧縮**します。転送量が減ります。

実測です。5MiB のファイル（中身はゼロ）を転送して、送信バイト数を比べました。

```bash
$ rsync -a  --stats src/big.txt dz/         # 圧縮なしで転送する
$ rsync -az --stats src/big.txt dz/         # 圧縮ありで転送する
```

```text
[-z なし]
Total bytes sent: 5,244,256
Total bytes received: 35

[-z あり]
Total bytes sent: 274
Total bytes received: 35
```

**5,244,256 バイト → 274 バイト。** ただしこれは中身がすべてゼロの極端な例です。
実データではここまでは縮みません。

**`-z` を付けるべきかの判断**

```text
  帯域が細い / 遠距離 / テキスト・ログが中心   → -z を付ける（効く）
  LAN 内 / すでに圧縮済み（jpg, gz, mp4）      → -z は無駄（CPU だけ食う）
```

### 転送元にないものを消す

`--delete` を付けると、**転送元に存在しないファイルが転送先から削除**されます。
これを付けて初めて「同期」になります。付けないと転送先にゴミが溜まり続けます。

```bash
$ echo "ゴミ" > d1/garbage.txt              # 転送先にだけあるファイルを作る
$ rsync -av --delete src/ d1/               # --delete 付きで同期する
```

```text
sending incremental file list
deleting garbage.txt
./

sent 139 bytes  received 42 bytes  362.00 bytes/sec
total size is 12  speedup is 0.07
```

> 2行目の `./` は、転送元と転送先のディレクトリ自体の更新時刻がずれているときだけ出ます。
> 出ないことがあっても異常ではありません。

**`--delete` は転送先を壊しうるオプションです。**
転送元のパスを打ち間違えた状態で実行すると、転送先が空になります。
**必ず次の `-n` と組み合わせて、一度目視してから外してください。**

### まず試す

`-n`（`--dry-run`）は**実際には何もせず、何が起きるかだけ**を表示します。

```bash
$ echo "new" > src/c.txt                    # 新しいファイルを追加する
$ rsync -avn --delete src/ d1/              # dry-run で確認する
$ ls d1/                                    # 実際には作られていないことを確認する
```

```text
sending incremental file list
./
c.txt

sent 174 bytes  received 30 bytes  408.00 bytes/sec
total size is 16  speedup is 0.08 (DRY RUN)

a.txt
sub
```

末尾に **`(DRY RUN)`** と出ます。`c.txt` は「送る予定」として表示されただけで、`d1/` には作られていません。

---

## リモートホストとやりとりする

### 書式はコロンで区切る

```text
[ユーザ名@][ホスト名]:ディレクトリ
```

```bash
$ rsync -av /data/ hoge@ping-t:/backup      # ローカル → リモート
$ rsync -av hoge@ping-t:/backup/ /data      # リモート → ローカル
```

**順番は `ユーザ名@ホスト名:パス`** です。ホスト名とパスの区切りは**コロン**。
コロンを忘れると、`ping-t/backup` という名前の**ローカルディレクトリ**と解釈されます。

**転送元と転送先の両方をリモートにはできません。**（片方はローカルである必要があります）

### 既定の転送方式は ssh

`-e` でリモートシェルを指定できますが、**`rsync` は指定しなければ ssh を使います。**
実測で確かめます。この検証環境には ssh が入っていません。

```bash
$ rsync -av src/ tu@ping-t.example:/backup  # -e を付けずに実行する
```

```text
rsync: [sender] Failed to exec ssh: No such file or directory (2)
rsync error: error in IPC code (code 14) at pipe.c(85) [sender=3.2.7]
rsync: connection unexpectedly closed (0 bytes received so far) [sender]
rsync error: error in IPC code (code 14) at io.c(232) [sender=3.2.7]
（終了ステータス 14）
```

**`-e` を何も付けていないのに `ssh` を exec しようとして失敗しています。**
これが「既定は ssh」の証拠です。したがって次の2つは同じ意味です。

```bash
$ rsync -av src/ user@host:/backup          # -e 省略（既定で ssh）
$ rsync -av -e ssh src/ user@host:/backup   # -e ssh を明示
```

**`-e` を明示するのは、ssh 以外を使いたいときか、ssh にオプションを渡したいとき**です。

```bash
$ rsync -av -e "ssh -p 2222 -i ~/.ssh/backup_key" src/ user@host:/backup   # ポートと鍵を指定する
```

> **実測できていないこと** … この環境には ssh も sshd も無いため、
> **ssh 経由の**転送成功例は確認していません。上記は `-e` の解決に失敗した時点の挙動です。
> （次に述べる rsync デーモン経由は実測しています）

### rsync デーモンに繋ぐ場合

コロンを**2つ**書くと、ssh ではなく **rsync デーモン（tcp/873）** への接続になります。

```bash
$ rsync -av src/ user@host::module/         # コロン2つ → rsyncd のモジュール名を指定
$ rsync -av src/ rsync://user@host/module/  # 同じ意味の URL 形式
```

| 書き方 | 使う経路 | 認証 |
|:--|:--|:--|
| `host:/path` | **ssh** | ssh の認証 |
| `host::module` | **rsync デーモン** | rsyncd.conf の secrets ファイル |

**コロン1つと2つで経路が変わる**点は、試験でも実務でも引っかかりやすいところです。

**実測で確かめます。** ssh の無いこの環境でも、デーモン経由なら転送できます。

```bash
$ rsync --daemon --config=./rsyncd.conf --port=8730   # rsync デーモンを起動する
$ RSYNC_PASSWORD=pw rsync -av --port=8730 src/ user@127.0.0.1::module/   # デーモンへ転送する
```

```text
sending incremental file list
./
a.txt
c.txt
sub/
sub/b.txt

sent 322 bytes  received 88 bytes  820.00 bytes/sec
```

**ssh がまったく無くても成功しました。** デーモンを止めると、エラーの種類が変わります。

```bash
$ rsync -av src/ user@127.0.0.1::module/    # デーモンを止めた状態で実行する
```

```text
rsync: [sender] failed to connect to 127.0.0.1 (127.0.0.1): Connection refused (111)
rsync error: error in socket IO (code 10) at clientserver.c(141) [sender=3.2.7]
```

```text
   コロン1つ  →  Failed to exec ssh / error in IPC code (code 14)   … ssh を起動しようとした
   コロン2つ  →  Connection refused / error in socket IO (code 10)  … TCP に直接つなごうとした
```

**エラーメッセージを見れば、どちらの経路を使ったかが分かります。**

---

## cp や scp との使い分け

| | `cp` | `scp` | `rsync` |
|:--|:--|:--|:--|
| 対象 | ローカルのみ | ローカル ⇔ リモート | 両方 |
| 差分転送 | しない | しない | **する** |
| 中断からの再開 | — | できない | **できる（`-P`）** |
| 属性の保持 | `-p` で可 | `-p` で時刻とモードのみ | **`-a` で一式** |
| 転送先の余計なものを消す | — | — | **`--delete`** |
| 2回目以降の速さ | 変わらない | 変わらない | **圧倒的に速い** |

```text
  1回きりの単発コピー          → cp / scp で十分
  毎日繰り返す / 巨大 / 遠い   → rsync 一択
```

> OpenSSH 9 以降、`scp` は内部的に SFTP プロトコルを使うようになりました。
> 挙動が変わった影響もあり、**リモートコピーは rsync か sftp を使うのが現在の推奨**です。

---

## 実務での書き方

**日次のバックアップジョブの型**

```bash
$ rsync -az --delete --exclude='*.tmp' \
    -e "ssh -i /root/.ssh/backup_key" \
    /var/www/ backup@bk01:/backup/www/       # 除外つきで別ホストへ同期する
```

| オプション | 書いた理由 |
|:--|:--|
| `-a` | 所有者とパーミッションを保つ。Web コンテンツは権限が崩れると事故になる |
| `-z` | 拠点間の回線なので圧縮が効く |
| `--delete` | 削除も反映しないと「同期」にならない |
| `--exclude` | 一時ファイルまで送ると無駄が多い |
| `-e` で鍵を明示 | cron から動かすとき、実行ユーザの既定鍵に依存しないようにする |
| `-v` を入れていない | cron のメールが毎日ファイル一覧で埋まるため。ログに残すなら `--stats` だけ付ける |

**事故を防ぐ運用ルール**

```text
  1. --delete を含む変更は、必ず -n を付けて一度実行して出力を読む
  2. 転送元のパスは変数にせず、ベタ書きするか厳密に検証する
  3. 転送先が空だった場合に abort する（バックアップ先の未マウントを検知する）
```

3番目は実際によくある事故です。**バックアップ先の NFS が外れていると、
マウントポイントの空ディレクトリに同期してしまい、`--delete` がバックアップを全消しします。**

```bash
$ mountpoint -q /backup || exit 1            # マウントされていなければ中止する
$ rsync -az --delete /var/www/ /backup/www/  # マウント確認が通ってから実行する
```

---

## 参考リンク

- [man 1 rsync](https://man7.org/linux/man-pages/man1/rsync.1.html)
- [rsync 公式](https://rsync.samba.org/)
- [man 5 rsyncd.conf](https://man7.org/linux/man-pages/man5/rsyncd.conf.5.html)

---

[← 全体の目次にもどる](../README.md)
