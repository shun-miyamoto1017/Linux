# ディスクの暗号化_dm-cryptとLUKS

| | |
|:--|:--|
| **学習の順番** | Phase3 専門 ★★★☆☆ |
| **Ping-t の範囲** | Linux3 / 暗号化(主題325) — 暗号化ファイルシステム |
| **業務での使いどころ** | **ディスクが盗まれても中身を守る。**ノート PC の紛失、退役サーバの廃棄、持ち出し USB ——「物理的に手に入っても読めない」を作れるかどうかは、セキュリティ要件でそのまま問われる |

> **このノートはブロックデバイス全体の暗号化**です。
> **マウントそのもの**は [マウントとアンマウント](./マウントとアンマウント.md)、
> **ファイルシステムの作成**は [ディスクを追加する手順](./ディスクを追加する手順.md) にあります。

---

## 目次

- [暗号化の対象は2通りある](#暗号化の対象は2通りある)
- [dm-crypt とデバイスマッパー](#dm-crypt-とデバイスマッパー)
- [cryptsetup の2つのモード](#cryptsetup-の2つのモード)
- [プレーンモードの手順](#プレーンモードの手順)
- [LUKS の手順](#luks-の手順)
  - [LUKS とは何か](#luks-とは何か)
  - [4つのステップ](#4つのステップ)
  - [使い終わったら閉じる](#使い終わったら閉じる)
  - [2回目以降のアクセス](#2回目以降のアクセス)
- [KeySlot は8つある](#keyslot-は8つある)
- [結果画面の見方](#結果画面の見方)
- [新しいアクション名と古いアクション名](#新しいアクション名と古いアクション名)
- [起動時に自動で開く](#起動時に自動で開く)
- [参考リンク](#参考リンク)

---

## 暗号化の対象は2通りある

**暗号化においては、さまざまな暗号化方式とともに、さまざまな暗号化対象が存在します。**
**ディスクやファイルの暗号化は、大きく分けて 2 通り**あります。

| 対象 | 何を暗号化するか | 代表的な仕組み |
|:--|:--|:--|
| **ブロックデバイス** | **パーティション、ファイルシステムを含むデバイス全体** | **dm-crypt / LUKS** |
| 個別のファイル | ファイル 1 つずつ | eCryptfs、EncFS |

**試験範囲は前者（ブロックデバイスの暗号化）**です。
**個別のファイルを暗号化する手法は、ここでは扱いません。**

```text
【ブロックデバイスの暗号化】
  デバイス全体が丸ごと暗号化される
    → 中のファイル名もディレクトリ構造も見えない
    → マウントするには鍵が要る

【個別ファイルの暗号化】
  ファイル 1 つずつ暗号化される
    → ファイル名やサイズは見えることがある
```

**ディスクを抜かれても読めない**のは前者です。
**要件が「紛失時の情報漏洩対策」なら、ブロックデバイスの暗号化を選びます。**

---

## dm-crypt とデバイスマッパー

**ブロックデバイスの暗号化を行う方法の一つとして、dm-crypt を使う方法があります。**

**`dm-crypt` の `dm` は device-mapper（デバイスマッパー）を表します。**
**device-mapper は、物理デバイスと論理デバイスをマッピングする機能**です。

**`dm-crypt` は device-mapper を利用して、
ブロックデバイス（物理デバイス）へのアクセス時に暗号化が行われるよう、暗号化マッピングを行います。**

```text
  アプリケーション
        │  普通に読み書きする
        ▼
  /dev/mapper/workusb        ← 論理デバイス（暗号化マッピング）
        │  ここで暗号化・復号が行われる
        ▼
  /dev/sdb                    ← 物理デバイス（中身は暗号文）
```

**device-mapper は論理デバイスを `/dev/mapper` ディレクトリ配下に作成し、
物理デバイスと論理デバイス間のマッピングを行います。**
**そのため、暗号化されたブロックデバイスへのアクセスは、
`/dev/mapper` ディレクトリ配下の暗号化マッピングを介して行います。**

**要点は 2 つ**です。

| 論点 | 内容 |
|:--|:--|
| **物理デバイスを直接マウントしない** | `/dev/sdb` をそのままマウントしても暗号文しか見えない |
| **`/dev/mapper/<名前>` をマウントする** | **こちらが「復号された姿」** |

**device-mapper は LVM でも使われている仕組み**です。
`/dev/mapper/vg_server1-lv_root` のような名前を見たことがあれば、それも同じ仕組みです。

---

## cryptsetup の2つのモード

**dm-crypt を利用するコマンドは `cryptsetup` です。**
**`cryptsetup` は、後述する LUKS に用いることもできます。**

```text
cryptsetup [オプション] アクション 引数
```

**同じコマンドで 2 つのモードを使い分けます。**

| モード | 何をするか | 特徴 |
|:--|:--|:--|
| **プレーンモード**（dm-crypt そのまま） | デバイスに暗号化マッピングを作る | **ヘッダを持たない**。パスフレーズが合っているかを確かめる術がない |
| **LUKS モード** | **LUKS ヘッダを作ってから**使う | **鍵を 8 個まで持てる**。他のシステムでも開ける |

**実務で使うのはほぼ LUKS** です。プレーンモードは**仕組みを理解するため**に押さえます。

---

## プレーンモードの手順

**アクション**

| アクション | 説明 |
|:--|:--|
| **`create 名前 デバイス名`** | **マッピング名とデバイスを指定して、暗号化マッピングを作成** |
| **`remove 名前`** | **指定した暗号化マッピングの削除** |
| **`status 名前`** | **指定した暗号化マッピングの状態表示** |

**暗号化ファイルシステムを作成するには 3 つの手順が必要です。**

```text
  ① ブロックデバイスへの暗号化マッピングを作成する
        暗号化マッピングは /dev/mapper 配下に、指定した名前で作成される
  ② 暗号化マッピングにファイルシステムを作成する
  ③ 暗号化ファイルシステムをマウントする
```

**例** … デバイス `/dev/sdb` を暗号化する。暗号化マッピング名は `workusb`、
ファイルシステムは `ext3` とし、`/mnt` にマウントする。

```bash
$ sudo cryptsetup create workusb /dev/sdb    # ① 暗号化マッピングを作る
Enter passphrase:                             #   （パスフレーズの入力）
$ sudo mkfs -t ext3 /dev/mapper/workusb       # ② マッピングにファイルシステムを作る
$ sudo mount -t ext3 /dev/mapper/workusb /mnt # ③ マウントする
```

**② と ③ で指定しているのが `/dev/sdb` ではなく `/dev/mapper/workusb`** である点が要点です。

**使い終わったら**

```bash
$ sudo umount /mnt                            # ① アンマウントする
$ sudo cryptsetup remove workusb              # ② 暗号化マッピングを削除する
```

**2回目以降のアクセス**

**暗号化ファイルシステムに再度アクセスするには、同じ名前の暗号化マッピングを作成し、
初回に作成したパスフレーズを入力します。**
**その後、暗号化マッピングをマウントすることで暗号化ファイルシステムにアクセスできます。**
**ファイルシステムを新たに作成する必要はありません。**

```bash
$ sudo cryptsetup create workusb /dev/sdb     # ① 同じ名前でマッピングを作り直す
Enter passphrase:                              #   （初回作成時のパスフレーズを入力）
$ sudo mount -t ext3 /dev/mapper/workusb /mnt  # ② マウントする
```

> **プレーンモードの怖いところ** … **ヘッダが無いので、パスフレーズが違っていてもエラーになりません。**
> **違う鍵でマッピングを作ると、ただのゴミデータとして見える**だけです。
> **`mkfs` をやり直してしまうと元のデータは失われます。** LUKS を使う理由がここにあります。

---

## LUKS の手順

### LUKS とは何か

**LUKS（Linux Unified Key Setup）は、Linux において標準的に使用される暗号化ファイルシステムの仕様**です。

| 特徴 | 内容 |
|:--|:--|
| **相互運用性** | **異なるシステム、ディストリビューション間において相互運用が可能** |
| **実装** | **Linux においては dm-crypt を用いて実装**されている |
| **操作コマンド** | **`cryptsetup` コマンド**でファイルシステムの暗号化や管理を行う |
| **鍵の数** | **KeySlot により、パーティションごとに 8 つの鍵を持てる** |

**プレーンモードとの決定的な違いは「ヘッダを持つ」こと**です。
**ヘッダに鍵の情報が書いてあるので、パスフレーズが正しいかどうかを判定できます。**

---

### 4つのステップ

**アクション**

| アクション | 説明 |
|:--|:--|
| **`luksFormat デバイス名`** | **指定したデバイスを LUKS（暗号化）パーティションとして初期化** |
| **`luksOpen デバイス名 名前`** | **デバイスと LUKS パーティション名を指定し、LUKS パーティションを開く** |
| **`luksClose 名前`** | **指定した LUKS パーティションを閉じる** |
| **`luksDump デバイス名`** | **指定したデバイスの暗号化の状態を表示** |

**LUKS を使用するには以下のような手順が必要です。**

```text
  ① デバイスを LUKS（暗号化）パーティションとして初期化
  ② LUKS パーティションを開く
       「開く」ことで /dev/mapper 配下に、引数で設定した名前でマッピングされる
  ③ 開いた LUKS パーティションにファイルシステムを作成する
  ④ 暗号化ファイルシステムをマウントする
```

**例** … デバイス `/dev/sdb` を LUKS で暗号化する。LUKS パーティションは `luksusb`
という名前で開き、ファイルシステムは `ext3` とする。また `/mnt` にマウントする。

```bash
$ sudo cryptsetup luksFormat /dev/sdb         # ① LUKS パーティションとして初期化する
WARNING!
========
This will overwrite data on /dev/sdb irrevocably.

Are you sure? (Type uppercase yes): YES
Enter LUKS passphrase:                         #   （パスフレーズの入力）
Verify passphrase:                             #   （確認のため同じパスフレーズを入力）
```

```bash
$ sudo cryptsetup luksOpen /dev/sdb luksusb   # ② LUKS パーティションを開く
Enter passphrase for /dev/sdb:                 #   （luksFormat 時に指定したパスフレーズ）
$ sudo mkfs -t ext3 /dev/mapper/luksusb        # ③ ファイルシステムを作る
$ sudo mount -t ext3 /dev/mapper/luksusb /mnt  # ④ マウントする
```

**`Are you sure? (Type uppercase yes)` は大文字で `YES` と打つ**必要があります。
**小文字の `yes` では進みません。** 誤操作を防ぐための作りです。

---

### 使い終わったら閉じる

**暗号化ファイルシステムの使用を終了した場合はアンマウントし、LUKS パーティションを閉じます。**

```bash
$ sudo umount /mnt                            # ① アンマウントする
$ sudo cryptsetup luksClose luksusb           # ② LUKS パーティションを閉じる
```

**順番が逆だと閉じられません。** マウント中のものは使用中だからです。

---

### 2回目以降のアクセス

**暗号化ファイルシステムに再度アクセスするには、同じ名前で LUKS パーティションを開き、
設定してあるパスフレーズを入力します。**
**その後、LUKS パーティションをマウントすることで暗号化ファイルシステムにアクセスできます。**
**ファイルシステムを新たに作成する必要はありません。**

```bash
$ sudo cryptsetup luksOpen /dev/sdb luksusb   # ① 同じ名前で開く
Enter passphrase for /dev/sdb:                 #   （設定済みパスフレーズのいずれかを入力）
$ sudo mount -t ext3 /dev/mapper/luksusb /mnt  # ② マウントする
```

**「設定済みパスフレーズのいずれか」**という言い方になるのは、
**LUKS は鍵を複数持てるから**です。次の節で見ます。

---

## KeySlot は8つある

**LUKS では、KeySlot といって、暗号化管理のための鍵をパーティションごとに 8 つ持つことができます。**
**これにより、万が一の場合の予備鍵や、少数であればユーザーの使い分けなどにも対応できます。**

```text
  KeySlot 0  ENABLED    ← 最初に設定したパスフレーズ
  KeySlot 1  DISABLED
  KeySlot 2  DISABLED
       …
  KeySlot 7  DISABLED
```

**KeySlot は 0 から始まり、7 まであります。標準（未指定）であれば、0 が使われます。**

**鍵を追加・削除する**

| アクション | 説明 |
|:--|:--|
| **`luksAddKey デバイス名`** | **鍵（パスフレーズ）を追加する** |
| **`luksKillSlot デバイス名 番号`** | **指定した KeySlot の鍵を無効にする** |
| `luksChangeKey デバイス名` | 鍵を変更する |
| `luksUUID デバイス名` | UUID を表示する |
| `isLuks デバイス名` | LUKS パーティションかどうかを判定する |

```bash
$ sudo cryptsetup luksAddKey /dev/sdb         # 予備の鍵を追加する
Enter any existing passphrase:                 #   （いま使える鍵のどれか）
Enter new passphrase for key slot:             #   （追加したい新しい鍵）
```

**運用上の意味**

| 使い方 | 内容 |
|:--|:--|
| **予備鍵** | **担当者が不在でも開けるように、管理者用の鍵を別スロットに入れておく** |
| **鍵の入れ替え** | **新しい鍵を追加 → 動作確認 → 古い鍵を `luksKillSlot`**。無停止で交換できる |
| 使い分け | 少人数なら、人ごとに別のスロットを割り当てる |

**鍵を 1 つしか持てないと、パスフレーズを失った時点でデータは永久に読めません。**
**LUKS が実務で選ばれる最大の理由がこれ**です。

> **`luksKillSlot` で最後の 1 つを消すと、二度と開けなくなります。**
> **必ず「新しい鍵で開けることを確認してから」古い鍵を消します。**

---

## 結果画面の見方

**`cryptsetup luksDump` はデバイスの暗号化の状態を表示します。**

```bash
$ sudo cryptsetup luksDump enc.img            # LUKS ヘッダの情報を表示する
LUKS header information for enc.img

Version:        1
Cipher name:    aes
Cipher mode:    xts-plain64
Hash spec:      sha256
Payload offset: 4096
MK bits:        512
UUID:           6c4aa457-4fde-451e-8ab3-e60dac096de5

Key Slot 0: ENABLED
        Iterations:             4064248
        Salt:                   87 47 6d 53 11 74 7d 9d 5b fd de cb 40 c2 55 97
        Key material offset:    8
        AF stripes:             4000
Key Slot 1: DISABLED
Key Slot 2: DISABLED
Key Slot 3: DISABLED
Key Slot 4: DISABLED
Key Slot 5: DISABLED
Key Slot 6: DISABLED
Key Slot 7: DISABLED
```

| 欄 | 意味 | どこを見るか |
|:--|:--|:--|
| **`Version`** | **LUKS のバージョン** | **`1` なら LUKS1、`2` なら LUKS2** |
| **`Cipher name`** | 暗号化アルゴリズム | 通常 `aes` |
| **`Cipher mode`** | 暗号利用モード | 通常 `xts-plain64` |
| `Hash spec` | ハッシュアルゴリズム | |
| `Payload offset` | 実データが始まる位置 | ヘッダの大きさを表す |
| **`MK bits`** | **マスターキーのビット長** | 256 / 512 |
| **`UUID`** | **このデバイスの UUID** | **`/etc/crypttab` にこれで書ける** |
| **`Key Slot N: ENABLED`** | **その番号の鍵が有効** | **いくつ有効かをここで確認する** |
| `Key Slot N: DISABLED` | その番号は未使用 | |

**上の出力は 0 番だけが ENABLED、1〜7 は DISABLED** です。
**鍵を 1 つだけ設定した状態**であることが読み取れます。

> **補足 … LUKS2 ではヘッダの形が変わります。**
> **`cryptsetup 2.7.0` では `luksFormat` の既定が LUKS2** で、
> `Version: 2` として `Data segments:` や `Keyslots:` という別の形式で表示されます。
> **試験で問われるのは上の LUKS1 の形式**なので、
> **同じ形を見たいときは `--type luks1` を付けて作成**します（実機で確認）。

```bash
$ sudo cryptsetup luksFormat --type luks1 /dev/sdb   # LUKS1 形式で初期化する
```

---

## 新しいアクション名と古いアクション名

**`cryptsetup` の新しいバージョンでは、アクション名が整理されています。**

| 新しい名前 | 古い名前（別名として残っている） |
|:--|:--|
| **`open`** | **`create`**（プレーンモード）／**`luksOpen`**（LUKS） |
| **`close`** | **`remove`**（プレーンモード）／**`luksClose`**（LUKS） |

```bash
$ sudo cryptsetup open --type luks /dev/sdb luksusb   # 新しい書き方
$ sudo cryptsetup luksOpen /dev/sdb luksusb            # 古い書き方（同じ意味）
```

> **`cryptsetup 2.7.0` の `--help` では、`create` / `luksOpen` / `remove` / `luksClose` は
> 「old action syntax aliases（古いアクション構文の別名）」として掲載されています**（実機で確認）。
> **どちらも動きますが、試験で問われるのは `luksFormat` / `luksOpen` / `luksClose` / `luksDump` のほう**です。
> **実務で新しく書くなら `open` / `close`** が推奨されます。

---

## 起動時に自動で開く

**毎回手でパスフレーズを入れるのは現実的ではないので、`/etc/crypttab` を使います。**

```text
名前        デバイス                                       鍵ファイル      オプション
luksdata    UUID=6c4aa457-4fde-451e-8ab3-e60dac096de5      none            luks
```

| 欄 | 意味 |
|:--|:--|
| **名前** | `/dev/mapper/` 配下に作られる名前 |
| **デバイス** | 暗号化されているデバイス（**UUID 指定が安全**） |
| **鍵ファイル** | **`none` なら起動時にパスフレーズを聞く**。ファイルを指定すれば自動で開く |
| オプション | `luks` / `discard` など |

**`/etc/crypttab` で開いたあと、`/etc/fstab` でマウントします。**

```text
/dev/mapper/luksdata  /data  ext4  defaults  0 2
```

**この 2 つがセット**です。`/etc/fstab` だけでは開けません。
`/etc/fstab` の書式は [fstabの書き方](./fstabの書き方.md) にあります。

> **鍵ファイルを使う場合の注意** … **鍵ファイルを暗号化したディスクの中に置いても意味がありません。**
> 別のディスクか、TPM などの安全な場所に置きます。

---

## 参考リンク

- [cryptsetup（公式リポジトリ）](https://gitlab.com/cryptsetup/cryptsetup)
- [man 8 cryptsetup](https://man7.org/linux/man-pages/man8/cryptsetup.8.html)
- [man 5 crypttab](https://man7.org/linux/man-pages/man5/crypttab.5.html)
- [LUKS1 On-Disk Format Specification](https://gitlab.com/cryptsetup/cryptsetup/-/wikis/LUKS-standard/on-disk-format.pdf)
- [dm-crypt — カーネルドキュメント](https://docs.kernel.org/admin-guide/device-mapper/dm-crypt.html)
- [AWS — Amazon EBS 暗号化](https://docs.aws.amazon.com/ja_jp/ebs/latest/userguide/ebs-encryption.html)

---

[← 全体の目次にもどる](../README.md)
