# RAIDの監視と保守

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★★☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — ファイルシステムの管理（業務起点で厚く追記したもの） |
| **業務での使いどころ** | **「壊れたことに気づけるか」「壊れる前に見つけられるか」。**組んだあとに何もしていない RAID は、再構築のときに初めて読めないブロックが見つかる。そこを防ぐための設定と、引き継いだディスクを調べて組み直す手順 |

> **このノートは RAID を組んだ「あと」の話**です。
> **`mdadm` での構築と障害ディスクの交換**は
> [ソフトウェアRAIDの管理_mdadm](./ソフトウェアRAIDの管理_mdadm.md)、
> **RAID レベルの仕組みと容量計算**は
> [RAIDの基礎とレベル](./RAIDの基礎とレベル.md)、
> **ディスク自体の健全性監視**は
> [ディスクの健全性監視_SMART](./ディスクの健全性監視_SMART.md) にあります。

> **このノートの検証状況**
> **作業環境のカーネルに md ドライバが無い**ため（`/proc/mdstat` が存在しない）、
> **実際にアレイを作って動かしての確認はできていません。**
> **オプションとヘルプの引用は mdadm 4.3 の `--help` を実機で確認**したもの、
> **それ以外は `man`、カーネル公式文書（`admin-guide/md` / `md/raid5-ppl` / `md/raid5-cache`）、
> Red Hat の公式ドキュメントからの引用**で、その都度出典を併記しています。
> **実機確認ができていない箇所はその旨を明記**しています。

---

## 目次

- [壊れる前に気づく仕組み](#壊れる前に気づく仕組み)
  - [障害を通知させる mdmonitor](#障害を通知させる-mdmonitor)
  - [定期的に整合性をチェックする](#定期的に整合性をチェックする)
  - [write-intent bitmap で再同期を短くする](#write-intent-bitmap-で再同期を短くする)
  - [RAID5のライトホールとその対策](#raid5のライトホールとその対策)
- [組み直す Assembleモードと痕跡を消す](#組み直す-assembleモードと痕跡を消す)
  - [止めたアレイを起動し直す](#止めたアレイを起動し直す)
  - [中身を先に確かめる Examine](#中身を先に確かめる-examine)
  - [痕跡を消す zero-superblock](#痕跡を消す-zero-superblock)
- [参考リンク](#参考リンク)

---

## 壊れる前に気づく仕組み

**`-f` `-r` `-a` の 3 手は「壊れたあと」の話です。**
**実務でもっと大事なのは「壊れたことに気づく」と「壊れる前に見つける」**です。

### 障害を通知させる mdmonitor

**`mdadm --monitor`（Monitor モード）がアレイを定期的に見て、変化があれば通知します。**
**RHEL では `mdmonitor.service` として常駐します。**

```bash
$ systemctl status mdmonitor                        # 監視が動いているか確認する
$ sudo mdadm --monitor --scan --oneshot             # 手動で1回だけ縮退チェックする
$ sudo mdadm --monitor --scan --test --oneshot      # テスト通知を飛ばして経路を確かめる
```

> **`--test` だけを付けると監視し続けて戻ってきません。**
> **`--oneshot` を一緒に付けてください。**
>
> **メールが飛ぶイベントは限られています。**
> `man 8 mdadm` によると、メールの対象は
> **`Fail` / `FailSpare` / `DegradedArray` / `SparesMissing` / `TestMessage`** だけです。
> **`RebuildStarted` や `RebuildFinished` はメールになりません**（`PROGRAM` では受け取れます）。
>
> **メールを飛ばすには MTA（`sendmail` 互換のもの）が必要**です。
> **`MAILADDR` を書いただけでは届きません**（必要なパッケージは実機で確認してください）。

**`mdadm --monitor` は、デバイスを指定しなければ設定ファイルに載っているアレイを監視します**
（`--monitor --help`）。
**つまり `mdadm.conf` の `ARRAY` 行が無いと、監視する対象がありません。**
**`ARRAY` 行の作り方は
[ソフトウェアRAIDの管理_mdadm](./ソフトウェアRAIDの管理_mdadm.md) の「設定ファイル」**にあります。

**通知先も `mdadm.conf` に書きます。**

```text
MAILADDR ops@example.com
PROGRAM /usr/local/sbin/raid-alert.sh
```

| 設定行 | 何をするか |
|:--|:--|
| **`MAILADDR`** | **アラートの送信先メールアドレス** |
| **`PROGRAM`** | **イベント検知時に実行するプログラム**（Slack 通知などに使える） |

`man 5 mdadm.conf` の記述です。

> - "The mailaddr line gives an E-mail address that alerts should be sent to when mdadm is running in --monitor mode"
> - "The program line gives the name of a program to be run when mdadm --monitor detects potentially interesting events"

**`--monitor --help` で確認できる主なオプション**（mdadm 4.3）

```text
  --mail=       -m   : Address to mail alerts of failure to
  --program=    -p   : Program to run when an event is detected
  --syslog      -y   : Report alerts via syslog
  --delay=      -d   : seconds of delay between polling state. default=60
  --oneshot     -1   : Check for degraded arrays, then exit
  --test        -t   : Generate a TestMessage event against each array at startup
```

> **`--test` を一度流して、本当にメールが届くか確かめてください。**
> **通知経路を試していない監視は、動いているかどうか分かりません。**
>
> **ホットスペアをアレイ間で共有する `spare-group` も、この監視が動いていないと機能しません**
> （[RAIDの基礎とレベル](./RAIDの基礎とレベル.md) の「ホットスペア」）。

### 定期的に整合性をチェックする

**RAID は「読まないブロックが壊れていること」に気づけません。**
**再構築のときに初めて読めないことが分かる**——これが最悪のパターンです。
**だから定期的に全ブロックを読んで確かめます。**

**手動で走らせる**

```bash
$ echo check | sudo tee /sys/block/md0/md/sync_action    # ① まず検査だけする
$ cat /proc/mdstat                                        # ② 進捗を見る
$ cat /sys/block/md0/md/mismatch_cnt                      # ③ 不一致セクタ数を見る
$ echo idle | sudo tee /sys/block/md0/md/sync_action      #   途中で止めたいとき
$ echo repair | sudo tee /sys/block/md0/md/sync_action    # ④ 原因を確認した上で修復する
```

> **いきなり `repair` を打たないでください。**
> **`repair` は「どちらが正しいか」を判断せず、片方に合わせます**
> （RAID5 なら、データ側を正しいものとしてパリティを書き直します）。
> **まず `check` で `mismatch_cnt` を見て、原因を確認する**のが順番です。
>
> **`mismatch_cnt` はセクタ数**です。
> **RAID1 / RAID10 では 0 でなくても異常とは言い切れません**
> （未使用領域の内容が一致しないことがあるため、`raid-check` も警告にとどめます）。

**`sync_action` に書ける値**（カーネル公式ドキュメント `admin-guide/md` より）

| 値 | 意味 |
|:--|:--|
| **`idle`** | **"nothing is happening"**（何も動いていない） |
| **`resync`** | **"redundancy is being recalculated after unclean shutdown or creation"**（異常停止後や作成直後の冗長性再計算） |
| **`recover`** | **"a hot spare is being built to replace a failed/missing device"**（故障・欠損デバイスの置き換え） |
| **`check`** | **"A full check of redundancy was requested and is happening. This reads all blocks and checks them. A repair may also happen for some raid levels."**（**RAID レベルによっては修復も起きます**） |
| **`repair`** | **"A full check and repair is happening."**（検査と修復。write-intent bitmap による最適化はされない） |

> **`/proc/mdstat` の表示は `recovery`、`sync_action` の値は `recover`** です。
> **綴りが 1 文字違う**ので、スクリプトで判定するときは注意してください。
> （この対応関係自体はカーネル公式文書では明記されておらず、環境による差がある可能性があります）

**RHEL 8 は自動、RHEL 9 は自分で有効化する**

**`mdadm` パッケージが、定期チェックの仕組みを一緒に入れます。**
**ただし RHEL 8 と RHEL 9 で動かし方が変わり、RHEL 9 では自動では走りません。**

| バージョン | 定期チェックの動かし方 |
|:--|:--|
| **RHEL 8 以前** | **cron ジョブが自動で作られ、そのまま走る** |
| **RHEL 9 以降** | **systemd タイマー（`raid-check.timer`）。**自分で有効化する必要がある |

```bash
$ systemctl is-enabled raid-check.timer        # 有効になっているか確認する
$ sudo systemctl enable --now raid-check.timer  # 有効にする（RHEL 9）
```

```bash
$ systemctl list-unit-files 'raid-check*'     # タイマーがあるか確認する（RHEL 9系）
$ systemctl list-timers 'raid-check*'         # 次回実行を確認する
$ ls -l /etc/cron.d/raid-check                # RHEL 8系ならこちらを確認する
$ cat /etc/sysconfig/raid-check               # 動作の設定（check / repair の選択など）
$ sudo /usr/sbin/raid-check                   # 手動で走らせる
```

**`/usr/sbin/raid-check` は `/etc/sysconfig/raid-check` を読み、
`check` か `repair` を `sync_action` に書き込むスクリプト**です。
**実行後に `mismatch_cnt` が 0 でなければ警告します**
（RAID1 / RAID10 は仕組み上 0 以外になることがあるため除外されます）。

> **RHEL 9 では cron ジョブが作られません。**
> Red Hat のナレッジベースにも
> **"The raid-check is enabled by default in config, and the cron job was created
> automatically in RHEL 8 but not in RHEL 9"** とあります。
>
> **RHEL 8 から RHEL 9 へ移行した環境では、定期チェックが止まっている可能性が高い**です。
> **`systemctl is-enabled raid-check.timer` を確認してください。**
> （RHEL の再ビルド版では `disabled` が既定という報告があります。
> RHEL 実機での確認はこのノートではできていません）

### write-intent bitmap で再同期を短くする

**`--bitmap=internal` を付けると、書き込み中の領域を記録しておきます。**
**異常停止や一時的な切り離しのあと、記録された領域だけを再同期**します。

```bash
$ sudo mdadm -C /dev/md0 -l1 -n2 --bitmap=internal /dev/sdb1 /dev/sdc1   # 作成時に付ける
$ sudo mdadm --grow /dev/md0 --bitmap=internal     # 後から付ける
$ sudo mdadm --grow /dev/md0 --bitmap=none         # 外す
$ sudo mdadm -D /dev/md0                           # Consistency Policy 欄で確認する
```

**RHEL 9 の公式ドキュメントに
"Write-intent bitmaps, which drastically increase the speed of resync events"
（再同期の速度を劇的に上げる）とあります。**

```text
  bitmap なし   ケーブルが一瞬抜けただけ → 全領域を再同期（数時間）
  bitmap あり   同じ事象              → 書き込み中だった領域だけ（数秒〜数分）
```

| 注意点 | 内容 |
|:--|:--|
| **`repair` では使われない** | 全ブロックを読む操作なので、bitmap による短縮は効かない |
| **PPL と併用できない** | カーネル文書に "using write-intent bitmap and PPL together is not supported." |
| **わずかに書き込み性能が落ちる** | bitmap の更新が入るため |

### RAID5のライトホールとその対策

**異常停止すると、データは書けたがパリティは書けていない、という状態が起こりえます。**
**これがライトホール（write hole）**です。

**この状態だけでは、実害は見えません。**
**問題になるのは、そのあとディスクが 1 本壊れたとき**です。
**不整合なパリティから「復元」した結果、壊れたデータが読み出されます。**

```text
  異常停止    データは新しい、パリティは古い    ← まだ誰も気づかない
        ▼
  1本故障    そのパリティを使って復元する      ← 誤ったデータが出てくる
```

> カーネル文書 `md/raid5-cache.txt`:
> **"an unclean shutdown can cause data in some stripes to not be in consistent state,
> eg, data and parity don't match."**／**"This problem is called 'write hole'."**

**対策が 2 つあります。**

| 対策 | 指定 | 特徴 |
|:--|:--|:--|
| **PPL**（Partial Parity Log） | **`--consistency-policy=ppl`** | **RAID5 専用**。ログを各メンバーディスクのメタデータ領域に分散して持つので**専用デバイスが不要** |
| **ジャーナルデバイス** | **`--write-journal=/dev/nvme0n1`** | **RAID4/5/6 で使える**。専用デバイスが必要で、**SSD が推奨** |

```bash
$ sudo mdadm -C /dev/md0 -l5 -n3 --consistency-policy=ppl /dev/sd{b,c,d}1   # PPLを有効にする
$ sudo mdadm -D /dev/md0 | grep -i consistency      # 設定を確認する
```

`man 8 mdadm` の記述です。

> - "For RAID5 only, Partial Parity Log is used to close the write hole and eliminate resync."
> - "Specify journal device for the RAID-4/5/6 array."／"The journal device should be an SSD with a reasonable lifetime."

> **PPL には限界があります。**カーネル文書に
> **"It does not protect from losing in-flight data, only from silent data corruption."**
> （飛んでいる途中のデータは守らない。守るのは静かなデータ破損だけ）とあり、
> **アレイのディスク数は最大 64 本までという制約**もあります。

---

## 組み直す Assembleモードと痕跡を消す

**Create は「新しく作る」、Assemble は「既にあるものを組み直す」**です。
**ここを間違えて `-C` を打つと、データを消します。**

```text
  mdadm -C   新規作成      … スーパーブロックを書き直す
  mdadm -A   再構成        … 既存のスーパーブロックを読んで、元の構成で起動する
      ▲ ディスクを別マシンに移したときに使うのは -A
```

> **`-C` は、デバイスの順序・レベル・チャンクサイズ・メタデータ版のどれかがずれると
> データを壊します。**
> **条件が完全に一致していれば（`--assume-clean` も使って）復旧できる場合もありますが、
> それは最後の手段**です。
> **まず `-A` を試す**——これが順番です。

### 止めたアレイを起動し直す

```bash
$ sudo mdadm -S /dev/md0               # いったん停止する
$ sudo mdadm -A /dev/md0 /dev/sdb1 /dev/sdc1   # 構成デバイスを指定して組み直す
$ sudo mdadm -A --scan                 # mdadm.conf の定義を使って全アレイを組み直す
$ cat /proc/mdstat                     # 起動したか確認する
```

### 中身を先に確かめる Examine

**`-D`（detail）は動いているアレイを見ますが、
`-E`（examine）は構成デバイス側のスーパーブロックを直接読みます。**

| | 見る対象 | いつ使うか |
|:--|:--|:--|
| **`mdadm -D /dev/md0`** | **アレイ**（動いている必要がある） | 稼働中の状態を見る |
| **`mdadm -E /dev/sdb1`** | **デバイスのスーパーブロック** | **アレイが組めない / 正体が分からないディスクを調べる** |

```bash
$ sudo mdadm -E /dev/sdb1              # このディスクがどのアレイの何番目かを調べる
$ sudo mdadm -E --scan                 # 見つかったアレイの定義を出す
```

**これが効く場面**

```text
  ディスク4本を引き継いだが、どれがどのアレイの何番目か分からない
      → 各デバイスに -E をかけて、UUID と Device Role を突き合わせる
      → そのうえで -A で組み直す
```

> **分からないまま `-C` で作り直すのが最悪の手**です。
> **まず `-E` で読む**——これだけは覚えておいてください。

### 痕跡を消す zero-superblock

**一度 RAID に使ったディスクには、スーパーブロックが残ります。**
**残っていると、別の用途に使おうとしたときに勝手に RAID として認識されたり、
`mdadm -C` で確認を求められたりします。**

```bash
$ sudo mdadm -E /dev/sdb1              # ① まだ残っているか確認する
$ sudo mdadm --zero-superblock /dev/sdb1   # ② RAID の痕跡を消す
$ sudo mdadm -E /dev/sdb1              # ③ 消えたことを確認する
```

```text
  mdadm: No md superblock detected on /dev/sdb1.
```

**この表示が出れば、痕跡は消えています。**（実測）

> **`--zero-superblock` を打つ前に、そのディスクが本当に不要か必ず確認してください。**
> **消したら `-A` で組み直せなくなります。**
> **アレイを停止（`-S`）してから**実行します。

**片付けの正しい順番**

```text
  ① umount                     使用をやめる
  ② mdadm -S /dev/md0          アレイを停止する
  ③ mdadm --zero-superblock    各デバイスの痕跡を消す
  ④ mdadm.conf の ARRAY 行と fstab のエントリを消す
      ▲ fstab に残っていると、次の起動でマウントに失敗して緊急モードに落ちる
```

---

## 参考リンク

- [man 8 mdadm](https://man7.org/linux/man-pages/man8/mdadm.8.html)
- [man 5 mdadm.conf](https://man7.org/linux/man-pages/man5/mdadm.conf.5.html)
- [man 4 md](https://man7.org/linux/man-pages/man4/md.4.html)
- [Linux kernel — admin-guide/md](https://docs.kernel.org/admin-guide/md.html)
- [Linux kernel — RAID5 Partial Parity Log](https://www.kernel.org/doc/Documentation/driver-api/md/raid5-ppl.rst)
- [Linux kernel — RAID5 write-back cache](https://www.kernel.org/doc/Documentation/md/raid5-cache.txt)
- [Red Hat — Managing RAID (RHEL 9)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_storage_devices/managing-raid_managing-storage-devices)
- [Red Hat — Setting up email notifications to monitor a RAID (RHEL 9)](https://docs.redhat.com/ja/documentation/red_hat_enterprise_linux/9/html/managing_storage_devices/setting-up-email-notifications-to-monitor-a-raid_managing-raid)

---

[← 全体の目次にもどる](../README.md)
