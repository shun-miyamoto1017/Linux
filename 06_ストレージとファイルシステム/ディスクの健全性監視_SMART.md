# ディスクの健全性監視_SMART

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★☆☆ |
| **Ping-t の範囲** | Linux2 / ファイルシステムとストレージ管理(主題2.02) — ファイルシステムの管理 |
| **業務での使いどころ** | **壊れる前に気づく。**「ディスクが逝ってから交換」ではなく「予兆の段階で計画停止して交換」に持ち込めるかどうかで、障害の重さがまるごと変わる |

> **このノートはディスクという「装置」の健康診断**です。
> ファイルシステムの**整合性チェック**（`fsck`）は [fsckとファイルシステムの修復](./fsckとファイルシステムの修復.md)、
> どのプロセスが使っているかの調査は [開いているファイルの確認 lsof](../04_プロセスとリソース管理/開いているファイルの確認_lsof.md) にあります。
>
> **`fsck` と S.M.A.R.T は見ている対象が違います。**
> `fsck` は**ファイルシステムの中の辻褄**、S.M.A.R.T は**ディスク装置そのものの劣化**です。

---

## 目次

- [SMART とは何か](#smart-とは何か)
  - [何を見ているのか](#何を見ているのか)
  - [smartmontools という道具立て](#smartmontools-という道具立て)
- [smartctl で今の状態を見る](#smartctl-で今の状態を見る)
  - [まず健全性だけを見る](#まず健全性だけを見る)
  - [デバイスタイプを指定する](#デバイスタイプを指定する)
- [結果画面の見方](#結果画面の見方)
  - [情報セクション](#情報セクション)
  - [健全性の判定行](#健全性の判定行)
  - [属性テーブルの読み方](#属性テーブルの読み方)
  - [特に見るべき属性](#特に見るべき属性)
- [自己診断テストを実行する](#自己診断テストを実行する)
- [smartd で定期監視する](#smartd-で定期監視する)
- [よく使うオプション](#よく使うオプション)
- [参考リンク](#参考リンク)

---

## SMART とは何か

### 何を見ているのか

**S.M.A.R.T は、ハードディスクの問題を発見するための自己診断機能**です。
**多くのハードディスクや SSD が対応しています。**

**ディスク自身が、自分の状態をカウントして記録し続けている**のが要点です。
OS が測っているのではなく、**ドライブのファームウェアが記録した値を読み出している**だけです。

```text
  ディスク内部（ファームウェア）
     ├─ 読み取りエラーが何回起きたか
     ├─ 代替処理したセクタが何個あるか
     ├─ 電源が入っていた時間は通算何時間か
     └─ 温度は何度か
              │  ← ここまでは OS 関係なく勝手に記録されている
              ▼
  smartctl が読み出して人間に見せる
```

**監視できる項目の例**

| 項目 | 何が分かるか |
|:--|:--|
| **読み取りエラーの発生率** | 記録面が劣化してきていないか |
| **ディスクの電源 ON の積算時間** | どれだけ使い込まれているか |
| 代替処理済みセクタ数 | 不良セクタをどれだけ肩代わりしたか |
| 温度 | 冷却が効いているか |

**監視できないもの** … **CPU やメモリの使用状況は S.M.A.R.T の対象ではありません。**
そちらは [リソース監視 システム全体](../04_プロセスとリソース管理/リソース監視_システム全体.md) を参照してください。

---

### smartmontools という道具立て

**Linux には、S.M.A.R.T の情報を取得する `smartmontools` というソフトウェアがあります。**
**中身は 2 つ**です。

| 名前 | 種類 | 役割 |
|:--|:--|:--|
| **`smartctl`** | **コマンド** | **今この瞬間の S.M.A.R.T 情報を表示する**／テストを実行する |
| **`smartd`** | **デーモン** | **S.M.A.R.T の情報を定期的に監視し、問題発生時は管理者に通知する** |

```text
  smartctl … 人が「いま見る」ための道具（手動）
  smartd   … 機械が「ずっと見張る」ための道具（自動）
```

**障害予防に使えるのは `smartd` のほう**です。
`smartctl` を人が思い出したときに叩くだけでは、壊れる前に気づけません。

**インストール**

```bash
$ sudo dnf install smartmontools        # RHEL 系
$ sudo apt install smartmontools        # Debian 系
```

---

## smartctl で今の状態を見る

### まず健全性だけを見る

**`-H`（`--health`）は、総合判定の 1 行だけを返します。**
**調査の入口は必ずここ**です。

```bash
$ sudo smartctl -H /dev/sda             # 総合的な健全性の判定だけを見る
SMART overall-health self-assessment test result: PASSED
```

| 表示 | 意味 |
|:--|:--|
| **`PASSED`** | **ドライブ自身は「まだ大丈夫」と判断している** |
| **`FAILED!`** | **ドライブ自身が「もう危ない」と判断している。至急バックアップして交換する** |

**補足** … **`PASSED` でも安心とは限りません。**
総合判定は**しきい値を割ったかどうか**だけを見ているので、
**悪化の途中は `PASSED` のまま**です。**推移を見るには属性テーブル（後述）が要ります。**

### すべての情報を見る

**`-a`（`--all`）で、S.M.A.R.T の情報をまとめて表示します。**

```bash
$ sudo smartctl -a /dev/sda             # S.M.A.R.T 情報をすべて表示する
```

**`-x`（`--xall`）にすると、S.M.A.R.T 以外の情報も含めてさらに詳しく出ます。**

---

### デバイスタイプを指定する

**USB 接続の外付け HDD では、そのままだと情報を取れないことがあります。**
**USB 変換チップが ATA のコマンドをそのまま通してくれない**ためです。

**`-d`（`--device`）でデバイスタイプを指定します。**

```bash
$ sudo smartctl -a /dev/sdb -d sat      # USB接続のHDDをSATAデバイスとして扱う
```

| 指定 | 使う場面 |
|:--|:--|
| **`-d sat`** | **USB 接続の HDD / SSD**（SCSI-ATA Translation） |
| `-d ata` | 直結の ATA デバイス |
| `-d nvme` | NVMe SSD |
| `-d scsi` | SCSI / SAS デバイス |
| `-d auto` | 自動判定（既定） |

**まず `-d` 無しで試し、情報が取れなければ `-d sat` を付ける**——これが実務の順番です。

```bash
$ sudo smartctl --scan                  # 認識できるデバイスと推奨タイプを一覧する
/dev/sda -d scsi # /dev/sda, SCSI device
```

**`--scan` は「どのデバイスに、どの `-d` を付ければよいか」を教えてくれます。**

---

## 結果画面の見方

### 情報セクション

```text
=== START OF INFORMATION SECTION ===
Model Family:     Hitachi/HGST Travelstar 7K750
Device Model:     Hitachi HTS727564A9E364
Serial Number:    J33C0084JSZ4RB
Firmware Version: JFDOA110
User Capacity:    640,135,028,736 bytes [640 GB]
Sector Sizes:     512 bytes logical, 4096 bytes physical
Rotation Rate:    7200 rpm
Form Factor:      2.5 inches
SATA Version is:  SATA 2.6, 3.0 Gb/s
SMART support is: Available - device has SMART capability.
SMART support is: Enabled
```

| 行 | 何が分かるか | 実務でどう使うか |
|:--|:--|:--|
| **`Device Model`** | 型番 | **交換部品を手配するときの型番** |
| **`Serial Number`** | シリアル番号 | **どの物理ディスクか**の特定。ラックで抜き間違えないため |
| `Firmware Version` | ファームウェア版数 | 既知の不具合に当たっていないかの確認 |
| `User Capacity` | 容量 | 同容量の代替品を選ぶため |
| `Sector Sizes` | 論理／物理セクタサイズ | **物理 4096（4Kn / 512e）**ならアライメントに注意 |
| **`Rotation Rate`** | 回転数 | **`Solid State Device` と出れば SSD** |
| **`SMART support is: Available`** | **S.M.A.R.T をサポートしている** | 対応していないディスクもある |
| **`SMART support is: Enabled`** | **S.M.A.R.T が有効である** | **`Disabled` なら `smartctl -s on` で有効にする** |

**この 2 行はセットで読みます。**
**「対応しているか」と「有効になっているか」は別の話**で、
**対応していても無効なら値は更新されません。**

```bash
$ sudo smartctl -s on /dev/sda          # S.M.A.R.T を有効にする
```

---

### 健全性の判定行

```text
=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED
Warning: This result is based on an Attribute check.
```

| 行 | 意味 |
|:--|:--|
| **`self-assessment test result: PASSED`** | **総合判定。しきい値を割った属性が 1 つも無い** |
| `Warning: This result is based on an Attribute check.` | **属性値からの判定であって、実際にテストを走らせた結果ではない**という断り |
| **`SMART Status not supported: Incomplete response, ATA output registers missing`** | **USB 変換チップが ATA の応答を返しきれていない**。それでも属性からの判定は出るので、直後の `PASSED` / `FAILED!` は読める |

**USB 接続の HDD では `SMART Status not supported` が出ることがあります。**

```bash
$ sudo smartctl -H /dev/sdb -d sat      # USB接続のHDDの健全性を見る
SMART Status not supported: Incomplete response, ATA output registers missing
SMART overall-health self-assessment test result: PASSED
Warning: This result is based on an Attribute check.
```

**`not supported` の行が出ても、その下に判定が出ていれば読めています。**
**変換チップがドライブの「状態レジスタ」を素通ししてくれないだけ**で、
属性テーブルは取れているため、**`smartctl` が属性から総合判定を組み立てている**という状態です。

その下には**自己診断の設定状況**が並びます。

```text
Offline data collection status:  (0x00) Offline data collection activity
                                        was never started.
Self-test execution status:      (   0) The previous self-test routine completed
                                        without error or no self-test has ever
                                        been run.
Total time to complete Offline
data collection:                 (  45) seconds.
```

| 行 | 読み方 |
|:--|:--|
| **`Offline data collection status`** | **バックグラウンド収集の状況**。`was never started` は一度も走っていない |
| **`Self-test execution status`** | **前回の自己診断の結果**。`completed without error` なら異常なし |
| `Total time to complete Offline data collection` | **収集に何秒かかるか**。テスト計画の目安 |

---

### 属性テーブルの読み方

**`-A`（`--attributes`）で表示される、いちばん実用的な部分**です。

```text
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      WHEN_FAILED RAW_VALUE
  5 Reallocated_Sector_Ct   0x0033   100   100   005    Pre-fail  -           0
  9 Power_On_Hours          0x0032   091   091   000    Old_age   -           4213
197 Current_Pending_Sector  0x0012   100   100   000    Old_age   -           0
```

| 列 | 意味 |
|:--|:--|
| **`ID#`** | **属性番号**。メーカーをまたいで概ね共通 |
| `ATTRIBUTE_NAME` | 属性名 |
| **`VALUE`** | **現在値。100 や 200 から始まり、悪化すると下がる正規化された値** |
| **`WORST`** | **これまでで最も悪かったときの `VALUE`** |
| **`THRESH`** | **しきい値。`VALUE` がここを下回ると異常** |
| **`TYPE`** | **`Pre-fail`＝故障の予兆／`Old_age`＝経年劣化** |
| **`WHEN_FAILED`** | **しきい値を割ったのはいつか。`-` なら一度も割っていない** |
| **`RAW_VALUE`** | **生の実測値**（回数・時間・個数など） |

**読み方の要点は 3 つ**です。

| 要点 | 内容 |
|:--|:--|
| **`VALUE` は「大きいほど良い」** | 100 から下がっていく。**`RAW_VALUE` とは向きが逆** |
| **見るのは `RAW_VALUE` の推移** | **0 だったものが 1 になった瞬間**が予兆。`VALUE` はまだ 100 のまま |
| **`Pre-fail` を優先する** | `Old_age`（使用時間など）は上がって当たり前。**`Pre-fail` の悪化が危険信号** |

**`-f brief` を付けると、フラグの意味が記号で並んで読みやすくなります。**

```bash
$ sudo smartctl -A -f brief /dev/sda    # 属性を短い形式で表示する
```

---

### 特に見るべき属性

| ID | 属性名 | 意味 | 増えたらどうか |
|:--:|:--|:--|:--|
| **5** | **`Reallocated_Sector_Ct`** | **代替処理済みセクタ数**。不良セクタを予備領域で肩代わりした数 | **0 以外になったら交換を検討する** |
| 9 | `Power_On_Hours` | 電源 ON の積算時間 | 増えて当然。**寿命の目安** |
| 187 | `Reported_Uncorrect` | 訂正できなかったエラーの報告数 | **増えたら危険** |
| 188 | `Command_Timeout` | コマンドがタイムアウトした回数 | ケーブルや電源も疑う |
| **197** | **`Current_Pending_Sector`** | **読めなくて代替処理待ちのセクタ数** | **0 以外は明確な予兆** |
| **198** | **`Offline_Uncorrectable`** | **オフライン検査で訂正できなかったセクタ数** | **0 以外は明確な予兆** |
| 194 | `Temperature_Celsius` | 温度 | 高止まりなら冷却を疑う |
| 199 | `UDMA_CRC_Error_Count` | 転送エラー数 | **ディスクよりケーブル・コネクタを疑う** |

> **`5` / `197` / `198` が 0 から動いたら要注意**——これは実務でよく使われる目安です。
> **ただしメーカーによって属性の意味や正規化のしかたが異なる**ため、
> **同じ型番の別個体と比べる**のがいちばん確実です。
> 属性の詳細は smartmontools の公式ドキュメントを参照してください。

---

## 自己診断テストを実行する

**属性テーブルは「今までの記録」ですが、テストは「いま実際に読めるか試す」操作**です。

| テスト | 所要時間の目安 | 何をするか |
|:--|:--|:--|
| **`short`** | **数分** | 電気系統と一部の領域を簡易チェックする |
| **`long`**（`extended`） | **数時間** | **全面をスキャンする** |
| `conveyance` | 数分 | 輸送中に痛んでいないかを調べる |
| `select,M-N` | 範囲による | **指定した LBA 範囲だけ**を調べる |

```bash
$ sudo smartctl -t short /dev/sda       # 短い自己診断テストを開始する
$ sudo smartctl -l selftest /dev/sda    # テストの履歴と結果を見る
```

**テストはバックグラウンドで走ります。** 開始コマンドはすぐ戻ってくるので、
**しばらく置いてから `-l selftest` で結果を見ます。**

```text
Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
# 1  Short offline       Completed without error       00%      4213         -
```

| 列 | 読み方 |
|:--|:--|
| **`Status`** | **`Completed without error` なら正常**。`Completed: read failure` は読み取り失敗 |
| `Remaining` | 未完了時の残り割合 |
| **`LifeTime(hours)`** | **そのテストを何時間目に実行したか**。履歴の時系列が分かる |
| **`LBA_of_first_error`** | **最初にエラーが出た論理ブロック番号**。`-` ならエラー無し |

```bash
$ sudo smartctl -X /dev/sda             # 実行中のテストを中断する
```

**補足** … **`-C`（captive モード）を付けると、テスト中そのディスクは使えなくなります。**
**稼働中のサーバでは絶対に使いません。**

---

## smartd で定期監視する

**`smartd` は S.M.A.R.T の情報を定期的に監視して、問題発生時は管理者に通知するデーモン**です。
**障害予防に使えるのはこちら**です。

**設定ファイル**

| ディストリビューション | 場所 |
|:--|:--|
| Debian 系 | `/etc/smartd.conf` |
| RHEL 系 | `/etc/smartmontools/smartd.conf`（環境により `/etc/smartd.conf`） |

```bash
$ grep -v '^#' /etc/smartd.conf | grep -v '^$'   # 有効な設定行だけを見る
DEVICESCAN -d removable -n standby -m root -M exec /usr/share/smartmontools/smartd-runner
```

| 書き方 | 意味 |
|:--|:--|
| **`DEVICESCAN`** | **監視対象を自動で見つける**（既定。1 台ずつ書く必要がない） |
| `-d removable` | リムーバブルデバイスも対象にする |
| `-n standby` | **スリープ中のディスクは起こさない**（無駄に回さない） |
| **`-m root`** | **通知メールの宛先** |
| `-M exec スクリプト` | 通知時に実行するスクリプト |

**1 台ずつ細かく書く例**

```bash
$ sudo vi /etc/smartd.conf              # 監視対象と条件を書く
```

```text
/dev/sda -a -o on -S on -s (S/../.././02|L/../../6/03) -m admin@example.com
```

| 指定 | 意味 |
|:--|:--|
| `-a` | すべての属性を監視する |
| `-o on` | 自動オフライン検査を有効にする |
| `-S on` | 属性の自動保存を有効にする |
| **`-s (S/../.././02\|L/../../6/03)`** | **短いテストを毎日 2 時、長いテストを毎週土曜 3 時に実行する** |
| `-m` | 通知先メールアドレス |

**起動と自動起動**

```bash
$ sudo systemctl start smartd           # デーモンを起動する
$ sudo systemctl enable smartd          # 起動時に自動で立ち上げる
$ systemctl status smartd               # 動いているか確認する
```

ユニットの操作は [systemctl サービスの操作と確認](../05_起動プロセスとカーネル/systemctl_サービスの操作と確認.md) を参照してください。

---

## よく使うオプション

**`smartctl`**（`smartctl [オプション] デバイス`）

| オプション | 意味 |
|:--|:--|
| **`-a` / `--all`** | **S.M.A.R.T 情報をすべて表示する** |
| `-x` / `--xall` | S.M.A.R.T 以外も含めてすべて表示する |
| **`-H` / `--health`** | **総合的な健全性の判定だけを表示する** |
| **`-A` / `--attributes`** | **属性テーブルを表示する** |
| `-i` / `--info` | 型番・シリアルなどの識別情報だけを表示する |
| `-c` / `--capabilities` | ドライブが対応している機能を表示する |
| **`-d タイプ` / `--device=`** | **デバイスタイプを指定する**（`sat` / `ata` / `nvme` / `scsi` / `auto`） |
| **`-t テスト` / `--test=`** | **自己診断テストを開始する**（`short` / `long` / `conveyance` / `select,M-N`） |
| **`-l タイプ` / `--log=`** | **ログを表示する**（`error` / `selftest` / `selective`） |
| `-s on\|off` / `--smart=` | S.M.A.R.T 自体を有効・無効にする |
| `-f 形式` / `--format=` | 属性の表示形式（`old` / `brief` / `hex`） |
| `-X` / `--abort` | 実行中のテストを中断する |
| `--scan` | 認識できるデバイスと推奨タイプを一覧する |
| `-j` / `--json` | **JSON で出力する**（監視スクリプトに組み込みやすい） |

> **上の一覧は `smartctl 7.4` の `--help` の出力をもとにしています。**
> **バージョンによって増減する可能性があるため、実機では `--help` で確認してください。**

---

## 参考リンク

- [smartmontools（公式）](https://www.smartmontools.org/)
- [man 8 smartctl](https://man7.org/linux/man-pages/man8/smartctl.8.html)
- [man 8 smartd](https://man7.org/linux/man-pages/man8/smartd.8.html)
- [man 5 smartd.conf](https://man7.org/linux/man-pages/man5/smartd.conf.5.html)
- [smartmontools Wiki — Supported devices](https://www.smartmontools.org/wiki/Supported_RAID-Controllers)
- [Wikipedia — S.M.A.R.T.](https://en.wikipedia.org/wiki/S.M.A.R.T.)
- [AWS — EBS ボリュームのステータスチェック](https://docs.aws.amazon.com/ja_jp/ebs/latest/userguide/monitoring-volume-status.html)

---

[← このフォルダの目次にもどる](./00_このフォルダにあるもの.md) ｜ [全体の目次にもどる](../README.md)
