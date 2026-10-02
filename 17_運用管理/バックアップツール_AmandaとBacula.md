# バックアップツール AmandaとBacula

| | |
|:--|:--|
| **学習の順番** | Phase2 設計構築 ★★★☆☆ |
| **Ping-t の範囲** | Linux2 / システムの保守(主題206) — バックアップ操作 |
| **業務での使いどころ** | **サーバが10台を超えたあたりから、`tar` と `cron` では回らなくなる**。スケジュール・世代管理・どのテープに何が入っているかのカタログを持つツールが要る。AWS Backup / Veeam を評価するときの比較軸もここで身につく |

> **方式の設計**は [バックアップの方式と設計](./バックアップの方式と設計.md)、
> **メディアの特性**は [バックアップメディアとテープ操作](./バックアップメディアとテープ操作.md) にまとめています。

---

## 目次

- [自前のスクリプトでは足りなくなる理由](#自前のスクリプトでは足りなくなる理由)
- [四つのOSSバックアップシステム](#四つのossバックアップシステム)
- [Amanda](#amanda)
- [Bacula](#bacula)
- [Bareos](#bareos)
- [BackupPC](#backuppc)
- [四つの比較](#四つの比較)
- [バックアップシステムではないもの](#バックアップシステムではないもの)
- [選び方の目安](#選び方の目安)
- [参考リンク](#参考リンク)

---

## 自前のスクリプトでは足りなくなる理由

1台なら `tar` と `cron` で十分です。台数が増えると、次の問題が一気に噴き出します。

```text
  ✗ どのサーバのバックアップが失敗したのか、朝まで誰も気づかない
  ✗ 「3週間前の /etc/nginx/nginx.conf」がどのテープに入っているか分からない
  ✗ 全台が同時に走ってネットワークとバックアップ先が飽和する
  ✗ 世代が溜まり続けて、古いものを消す仕組みが無い
  ✗ テープを入れ替える手順が属人化する
```

**バックアップシステムが提供するのは、この5つの解決策**です。

| 機能 | 何を解決するか |
|:--|:--|
| **スケジューラ** | 台数を分散して走らせる |
| **カタログ**（インデックス DB） | どのファイルがどのメディアのどこにあるか |
| **保持ポリシー** | 世代が溜まり続けるのを防ぐ |
| **通知** | 失敗をその場で知らせる |
| **メディア管理** | テープのラベル、プール、ローテーション |

---

## 四つのOSSバックアップシステム

**ネットワーク越しに複数クライアントをまとめてバックアップできる**代表的な OSS は次の4つです。

```text
  Amanda    … 標準ツール（dump / tar）をそのまま使う。素朴で堅い
  Bacula    … 3つのデーモンからなる本格派。エンタープライズ向け
  Bareos    … Bacula から派生。Web UI が標準で付く
  BackupPC  … クライアントに何も入れない。ディスク前提でファイルを重複排除
```

---

## Amanda

**AMANDA** = **A**dvanced **M**aryland **A**utomatic **N**etwork **D**isk **A**rchiver。
メリーランド大学で開発された、最も歴史の長いネットワークバックアップシステムです。

**最大の特徴は「独自形式を使わない」こと**です。

公式リポジトリの README には次のようにあります。

> Built on top of standard backup software: Unix dump/restore, GNU Tar and other archival tools.

> Open file and tape formats. If necessary, you can use standard tools like mt and GNU Tar to recover data.

```text
   バックアップ  … Amanda が dump / GNU tar を呼んで取る
   保存形式      … dump 形式・tar 形式そのもの
   復元          … Amanda が無くても mt と tar だけで取り出せる  ← ここが強い
```

**これはベンダロックインの回避**という意味で非常に重要な性質です。
災害時に「バックアップは無事だが、それを読むソフトが動くサーバが無い」という事態を避けられます。

| 項目 | 内容 |
|:--|:--|
| 構成 | 1台のサーバが複数クライアントを並列にバックアップ |
| 保存形式 | **dump / GNU tar の標準形式** |
| 対応メディア | LTO / DAT / DLT などのテープ、ディスク、仮想テープ、DVD-RW、**Amazon S3** |
| ライセンス | オープンソース |

---

## Bacula

**「バックアップ（backup）」と「ドラキュラ（Dracula）」をかけた名前**です。
「データを取り戻しに来る」という意味を込めています。

**3つのデーモンとカタログ**という構成が特徴です。

```text
   ┌───────────────┐          ┌────────────┐
   │   Director    │─────────▶│  Catalog   │
   │  中央の司令塔  │          │  索引の DB  │
   └───┬───────┬───┘          └────────────┘
       │       │
       ▼       ▼
   ┌────────────┐  データ  ┌───────────────┐
   │File Daemon │────────▶│Storage Daemon │
   │（各クライアント）│          │（メディアに書く）  │
   └────────────┘          └───────────────┘
```

**Catalog を保守するのは Director**です。File Daemon は Catalog に直接つなぎません。

| コンポーネント | 役割 |
|:--|:--|
| **Director** | 中央の制御プログラム。他のすべてのデーモンを統制し、スケジュールを管理する |
| **File Daemon** | バックアップ対象のクライアントに入れる。ファイルを集めて送る |
| **Storage Daemon** | データを受け取ってメディアに書く |
| **Catalog** | ファイルの索引とボリュームの情報を保持する DB |
| **Console** | 管理者が Director と対話するための入口 |

**コンソールが2系統ある**のが Ping-t でもよく問われるところです。

| コンソール | 形態 |
|:--|:--|
| **bconsole** | **CUI**。シェル上で動くテキストインターフェース。起動すると `*` のプロンプトが出る |
| **bat** | **GUI**。Bacula Administration Tool。Qt で作られている |

公式ドキュメントにはこうあります。

> After launching the Console program (bconsole), it will prompt you for the next command with an asterisk (*).

**Console は Director とネットワーク越しに通信する**ため、
Console と Director は同じマシンで動いている必要はありません。

---

## Bareos

**B**ackup **A**rchiving **RE**covery **O**pen **S**ourced。
**Bacula 5.2 からのフォーク**です。

公式ドキュメントの記述です。

> Bareos is a fork of the open source project Bacula version 5.2.

分岐は **2010 年**、開発者 Marco van Wieringen が「取り込まれなかった、あるいは放置されたコミュニティの貢献」を
集めはじめたことがきっかけとされています。

**構成は Bacula とほぼ同じ**（Director / Storage Daemon / File Daemon / Catalog / Console）です。

| Bacula との違い | 内容 |
|:--|:--|
| **Web UI** | **Bareos WebUI** が公式に提供される |
| カタログ DB | PostgreSQL 対応 |
| ライセンス | 全機能がオープンソースで提供される |

```text
   Bacula  … bconsole（CUI）と bat（Qt の GUI）
   Bareos  … bconsole（CUI）と WebUI（ブラウザ）
```

**設定ファイルの書式や用語はほぼ共通**なので、片方を覚えればもう片方も読めます。

---

## BackupPC

**思想がまったく違います。** BackupPC は**ディスク前提**で、**クライアントに何も入れません。**

公式ドキュメントの一文です。

> No client-side software is needed.

**既存の標準プロトコルをそのまま使う**からです。

| 対象 OS | 使う経路 |
|:--|:--|
| Windows | SMB、または Cygwin 経由の rsync |
| Linux / UNIX / macOS | **rsync**、`tar`（ssh / rsh / nfs 経由）、FTP |

公式は **rsync を推奨**しています。効率的に転送でき、増分でほとんどの変更を検出できるためです。

**もうひとつの目玉が重複排除（プーリング）**です。

> A clever pooling scheme minimizes disk storage and disk I/O. Identical files across multiple backups of the same or different PC are stored only once, resulting in substantial savings in disk storage and disk writes.

```text
   100台の PC に同じ /usr/bin/python3 がある
        ↓  普通に取ると 100 個ぶんの容量
        ↓  BackupPC は「同じ内容のファイル」を1つだけ保存
   ディスクも I/O も劇的に減る
```

管理は **http/cgi の Web インターフェース**で行います。
管理者は状態確認・設定編集・ホストの追加削除ができ、
一般ユーザも**自分でバックアップの開始／中止、ファイルの閲覧と復元**ができます。

**テープは基本的に扱いません。**（ディスクに取ったものを別途テープへ流すことはある）

---

## 四つの比較

| | Amanda | Bacula | Bareos | BackupPC |
|:--|:--|:--|:--|:--|
| クライアントに導入 | 必要 | 必要（File Daemon） | 必要（File Daemon） | **不要** |
| 保存形式 | **dump / tar の標準形式** | 独自形式 | 独自形式 | 独自プール |
| ツールなしで復元 | **できる** | 難しい | 難しい | 難しい |
| テープ | **得意** | **得意** | **得意** | 基本は非対応 |
| 重複排除 | — | — | — | **あり** |
| CUI 管理 | 各種コマンド | **bconsole** | **bconsole** | — |
| GUI 管理 | — | **bat**（Qt） | **WebUI**（ブラウザ） | **Web（cgi）** |
| 由来 | メリーランド大学 | 独自 | **Bacula 5.2 のフォーク** | 独自 |

---

## バックアップシステムではないもの

Ping-t では**紛らわしい選択肢**として次が混ざります。どれもバックアップシステムではありません。

| 名前 | 正体 |
|:--|:--|
| **RAID** | 複数の HDD による**冗長化技術**。機器故障に備えるもので、誤削除からは守れない |
| **LVM** | 物理デバイスを論理ボリュームとして扱う**ボリューム管理技術**。スナップショットは取れるが、同じディスク上なので単体ではバックアップにならない |
| **Ansible** | **構成管理ツール**。サーバの状態を宣言的に揃えるもの |
| **Puppet / Chef** | 同じく構成管理ツール |

```text
   RAID    … 壊れても止まらない          （可用性）
   LVM     … 容量を柔軟に扱える          （管理性）
   Ansible … 同じ構成を再現できる        （再現性）
   バックアップ … 失われたデータを取り戻せる （復旧性）
```

> ただし **Ansible は「設定の再現」という意味でバックアップを補完します。**
> データは Bacula で、構成は Ansible で、という組み合わせは実務でよく取ります。

---

## 選び方の目安

```text
   テープを使う / 長期保管 / 復元の独立性を重視
        → Amanda（標準形式なのでツールが無くても戻せる）

   数十〜数百台 / 細かいポリシー / 商用サポートも視野
        → Bacula または Bareos（Web UI が要るなら Bareos）

   PC・ノートが中心 / ディスクに取る / 容量を節約したい
        → BackupPC（エージェント不要・重複排除）

   数台まで / 要件が単純
        → tar + rsync + cron で十分。無理にツールを入れない
```

**最後にひとつ。**
どのツールを選んでも、**リストア訓練をしなければ意味がありません。**
カタログ DB 自体のバックアップを取り忘れて、
「テープはあるが何が入っているか分からない」という事故が実際に起きます。
**カタログも必ずバックアップ対象に含めてください。**

---

## 参考リンク

- [Amanda 公式リポジトリ（zmanda/amanda）](https://github.com/zmanda/amanda)
- [Bacula Console and Operators Guide](https://www.bacula.org/9.2.x-manuals/en/console/Bacula_Console.html)
- [What is Bacula?（デーモン構成）](https://www.bacula.org/5.2.x-manuals/en/main/main/What_is_Bacula.html)
- [What is Bareos? — Bareos Documentation](https://docs.bareos.org/IntroductionAndTutorial/WhatIsBareos.html)
- [BackupPC Documentation](https://backuppc.github.io/backuppc/BackupPC.html)
- [bat(1) — Bacula Administration Tool Console](https://manpages.debian.org/testing/bacula-console-qt/bat.1.en.html)

---

[← 全体の目次にもどる](../README.md)
