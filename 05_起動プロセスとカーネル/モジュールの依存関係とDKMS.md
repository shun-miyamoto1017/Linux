# モジュールの依存関係とDKMS

| | |
|:--|:--|
| **学習の順番** | Phase2 ★★★★☆（Linuxカーネルの構成要素 ／ カーネル実行時における管理とトラブルシューティング） |
| **Ping-t の範囲** | Linux2 / システムの起動とLinuxカーネル(主題2.01) — Linuxカーネルの構成要素、カーネル実行時における管理とトラブルシューティング |
| **業務での使いどころ** | **「モジュールが見つからない」「カーネル更新後にドライバが消えた」**の原因はここ。GPU や独自ストレージのドライバを扱うなら必須 |

> **このノートは「依存関係のしくみ」**です。
> モジュールの**読み込み・取り外し・情報の確認**（`lsmod` / `modprobe` / `insmod` / `rmmod`）は
> [カーネルモジュールの管理](./カーネルモジュールの管理.md) にまとめています。

---

## 目次

- [modules dep 依存関係のファイル](#modules-dep-依存関係のファイル)
- [depmod 依存関係を作り直す](#depmod-依存関係を作り直す)
- [DKMS カーネル更新に追随する仕組み](#dkms-カーネル更新に追随する仕組み)
- [結果画面の見方](#結果画面の見方)
- [参考リンク](#参考リンク)

---

## modules dep 依存関係のファイル

### なぜ依存関係があるのか

モジュールは、**別のモジュールが提供する機能を使う**ことがあります。
たとえば「iSCSI のモジュール」は「SCSI 共通処理のモジュール」がないと動きません。

**先に土台のモジュールを読み込まないと、上に載るモジュールは読み込めません。**
その前後関係を書いたのが **`modules.dep`** です。

| ファイル | 中身 | 誰が使うか |
|:--|:--|:--|
| **`modules.dep`** | 依存関係の**テキスト版**（人が読める） | 人が目で確認する |
| **`modules.dep.bin`** | 同じ内容を**プログラムが処理しやすい形式**に変換したもの | **`modprobe`** が実際に読む |

> **`modules.dep` は「モジュールの起動順」や「カーネルイメージの中身」ではありません。**
> あくまで**依存関係だけ**が書かれた、`/lib/modules/(バージョン)/` の下にあるファイルです。

---

### 書式

**1 行が 1 モジュール**で、こう書かれています。

```text
モジュール名: 依存しているモジュール 依存しているモジュール …
   ↑          ↑
コロンの左     コロンの右（スペース区切り、無いこともある）
```

| 見る場所 | 分かること |
|:--|:--|
| **コロン（`:`）の左** | **そのモジュール自身**のパス |
| **コロン（`:`）の右** | **そのモジュールが依存しているモジュール**（スペース区切り） |
| **コロンの右が空** | **何にも依存していない**（単独で読み込める） |

---

### 例文で読んでみる

```text
kernel/net/A.ko:
kernel/net/B.ko: kernel/net/A.ko kernel/net/C.ko
kernel/net/C.ko: kernel/net/A.ko
kernel/net/D.ko: kernel/net/A.ko kernel/net/C.ko
```

この 4 行から、次のことが読み取れます。

| 行 | 読み取れること |
|:--|:--|
| `A.ko:` | **A は他のモジュールに依存していない**（コロンの右が空） |
| `B.ko: A.ko C.ko` | B は **A と C** に依存している |
| `C.ko: A.ko` | **C は A だけ**に依存している |
| `D.ko: A.ko C.ko` | D は A と C に依存している |

**「D を読み込みたい」ときに何が起きるか**

```text
  modprobe D
      │
      ├─ modules.dep を見る → D は A と C が必要だと分かる
      ├─ C も見る           → C は A が必要だと分かる
      │
      ▼  足りないものを順に読み込む
   A → C → D の順に読み込まれる
```

> **ここが `modprobe` の便利なところです。**
> 自分で A と C を先に読み込む必要はなく、**`modprobe D` と打つだけで全部そろえてくれます。**

**例文**

```bash
$ grep "^kernel/fs/xfs/xfs.ko" /lib/modules/$(uname -r)/modules.dep   # xfs が何に依存するか調べる
kernel/fs/xfs/xfs.ko: kernel/lib/libcrc32c.ko

$ modprobe --show-depends xfs                        # 読み込まれる順番を実行せずに確認する
insmod /lib/modules/6.1.0-18-amd64/kernel/lib/libcrc32c.ko
insmod /lib/modules/6.1.0-18-amd64/kernel/fs/xfs/xfs.ko
```

**補足**

- `grep "^..."` … `^` は「行の先頭」を表す記号。**コロンの左側（自分自身）で探したい**ので付けています
- `modules.dep` を**手で書き換えてはいけません**。`depmod` が生成するファイルなので、次の生成で上書きされます

---

### 消えると困るのは modprobe だけ

**`modules.dep` と `modules.dep.bin` を誤って削除してしまったら、何が使えなくなるか。**
ここは依存関係の理解を試す問題としてよく出ます。

| コマンド | 使えるか | 理由 |
|:--|:--:|:--|
| **`modprobe`** | **使えない** | **このファイルを読んで依存関係を解決している**ので、無いと致命的なエラーになる |
| `insmod` | **使える** | ファイルのパスを直接指定するだけ。依存関係を見ない |
| `rmmod` | **使える** | 同じく依存関係を見ない |
| `lsmod` | **使える** | `/proc/modules` を読むだけ |
| `depmod` | **使える** | **このファイルを作る側**。むしろこれで復旧する |

**復旧のしかた**

```bash
$ sudo depmod                                        # modules.dep を作り直す
$ ls -l /lib/modules/$(uname -r)/modules.dep         # 復旧したか確認する
$ sudo modprobe xfs                                  # modprobe が使えるようになったか試す
```

> **覚え方**
>
> ```text
>   depmod    が  modules.dep  を  作る
>   modprobe  が  modules.dep  を  使う
>
>   → 作る側は無事、使う側が困る
> ```

---

## depmod 依存関係を作り直す

### 意味

**`depmod`** は、`/lib/modules/(バージョン)/` の中のモジュールを全部調べて、
**`modules.dep` などの一覧ファイルを作り直す**コマンドです。

**いつ実行するか**

| 場面 | 理由 |
|:--|:--|
| **`make modules_install` のあと** | 自動で実行されるので、通常は意識しなくてよい |
| **`.ko` を手でコピーしたあと** | 一覧に載らないと `modprobe` から見つけられない |
| **`modprobe` が「モジュールが見つからない」と言うとき** | 一覧が古い可能性がある |

**例文**

```bash
$ sudo depmod                                        # 動いているカーネルの一覧を作り直す
$ sudo depmod -a                                     # 全モジュールを調べ直す（既定の動作）
$ sudo depmod 6.1.0-17-amd64                         # 別のカーネルバージョンを対象にする
$ sudo depmod -n | head                              # 書き込まずに結果だけ表示して確認する
```

### よく使うオプション

| オプション | 意味 | 使いどころ |
|:--|:--|:--|
| **`-a`** / `--all` | **すべてのモジュール**を調べる | 既定の動作。明示したいとき |
| **`-A`** / `--quick` | 前回より**新しいモジュールがあるときだけ**処理する | 起動スクリプトの中で使われる |
| **`-n`** / `--dry-run` | 書き込まず、**結果を画面に出すだけ** | 変更前の確認 |
| **`-v`** / `--verbose` | 処理した内容を詳しく表示する | 調査用 |
| **`-b 基準ディレクトリ`** | モジュールを探す**基準のディレクトリを変える** | 別環境のルートに対して作るとき |
| **`-F System.map`** | カーネルのシンボル表を渡す | 未解決シンボルを検出したいとき |
| **`-e`** / `--errsyms` | **解決できないシンボルを報告する**（`-F` と併用） | ビルド不整合の調査 |
| **`バージョン`**（引数） | 対象のカーネルバージョン | 省略すると `uname -r` |

**補足**

- `depmod` は **`modules.dep` 以外にも** `modules.alias` / `modules.symbols` / `modules.devname` などをまとめて作り直します
- **書き込み先は `/lib/modules/(バージョン)/`** なので、`root` 権限が必要です

---

## DKMS カーネル更新に追随する仕組み

### 何が問題なのか

モジュールは、**そのカーネルのバージョン専用にビルド**されています。
配置先が `/lib/modules/(バージョン)/` とバージョンごとに分かれているのは、そのためです。

すると、こうなります。

```text
  カーネル 6.1.0-17 で使っていた独自ドライバ
        │
        │  カーネルを 6.1.0-18 に更新
        ▼
  /lib/modules/6.1.0-18/ には、その独自ドライバが存在しない
        │
        ▼
  再起動したら、そのデバイスが動かなくなる
```

ディストリが配るモジュールはカーネルと一緒に更新されるので問題ありません。
困るのは、**自分で入れたサードパーティ製のドライバ**（GPU・仮想化・独自ストレージなど）です。

---

### DKMS とは

**DKMS**（**D**ynamic **K**ernel **M**odule **S**upport）は、
**カーネルを更新したときに、モジュールを自動でビルドし直して配置する仕組み**です。

| | |
|:--|:--|
| **正式名称** | **Dynamic Kernel Module Support** |
| **やること** | カーネル更新時に、カーネルとは独立して**自動でモジュールをコンパイルし、インストールする** |
| **必要なもの** | **カーネルヘッダ**（`kernel-devel` / `linux-headers-$(uname -r)`）とコンパイラ |
| **現状** | **多くのディストリが標準でパッケージに含んでいる** |

```text
  カーネル更新のパッケージが入る
        │
        ▼
  DKMS が反応して、登録されている全モジュールを
  新しいカーネル向けにビルドし直す
        │
        ▼
  /lib/modules/(新しいバージョン)/ に配置される
        │
        ▼
  再起動しても、そのデバイスは動き続ける
```

> **名前を問う問題が出ます。**
> **Dynamic Kernel Module Support** が正解で、
> 「Dynamic Auto Module Support」「Auto Kernel Module System」「Dynamic Kernel Module System」といった**似た名前の仕組みは存在しません。**

---

### 設定ファイル

| ファイル | 役割 |
|:--|:--|
| **`dkms.conf`** | **各モジュールごと**の設定。ソースと一緒に `/usr/src/(名前)-(バージョン)/` に置く |
| **`/etc/dkms/framework.conf`** | **DKMS 全体**の設定（署名まわりなど） |

**`dkms.conf` のおもな項目**

| 項目 | 意味 |
|:--|:--|
| **`PACKAGE_NAME`** | モジュールの名前 |
| **`PACKAGE_VERSION`** | バージョン |
| **`BUILT_MODULE_NAME`** | ビルドしてできる `.ko` の名前 |
| **`DEST_MODULE_LOCATION`** | `/lib/modules/…` のどこに置くか |
| **`MAKE`** | ビルドに使うコマンド |
| **`AUTOINSTALL`** | **`yes` にすると、カーネル更新時に自動でビルドし直す** |

**例文**

```bash
$ cat /usr/src/mymod-1.0/dkms.conf                   # モジュールごとの設定を見る
PACKAGE_NAME="mymod"
PACKAGE_VERSION="1.0"
BUILT_MODULE_NAME[0]="mymod"
DEST_MODULE_LOCATION[0]="/kernel/drivers/misc"
AUTOINSTALL="yes"
```

---

### 手作業で操作する

自動任せにせず、`dkms` コマンドで自分で扱うこともできます。

| サブコマンド | やること |
|:--|:--|
| **`dkms add`** | ソースを DKMS に**登録する** |
| **`dkms build`** | 登録したモジュールを**ビルドする** |
| **`dkms install`** | ビルド済みのモジュールを**配置する** |
| **`dkms remove`** | **取り除く** |
| **`dkms status`** | **登録されているモジュールの状態を表示する** |
| **`dkms autoinstall`** | 登録済みのものを**まとめてビルドし直す** |
| **`dkms uninstall`** | 配置だけを取り消す（登録は残す） |

**例文**

```bash
$ dkms status                                        # 登録されているモジュールの状態を見る
$ sudo dkms add -m mymod -v 1.0                      # /usr/src/mymod-1.0 を登録する
$ sudo dkms build -m mymod -v 1.0                    # 現在のカーネル向けにビルドする
$ sudo dkms install -m mymod -v 1.0                  # /lib/modules 配下へ配置する
$ sudo dkms remove -m mymod -v 1.0 --all             # 全カーネル分をまとめて取り除く
$ sudo dkms autoinstall                              # 登録済みを現在のカーネル向けに作り直す
```

**よく使うオプション**

| オプション | 意味 |
|:--|:--|
| **`-m 名前`** | 対象のモジュール名 |
| **`-v バージョン`** | 対象のバージョン |
| **`-k バージョン`** | **対象のカーネルバージョン**（省略すると `uname -r`） |
| **`--all`** | **すべてのカーネル**に対して処理する |
| **`--force`** | すでに処理済みでもやり直す |

**補足**

- **カーネルヘッダが入っていないとビルドに失敗します。**更新時にヘッダも一緒に入る構成にしておくのが安全です

```bash
$ sudo apt install linux-headers-$(uname -r)         # Debian系：カーネルヘッダを入れる
$ sudo dnf install kernel-devel-$(uname -r)          # RHEL系：カーネルヘッダを入れる
```

---

## 結果画面の見方

### dkms status の見方

```bash
$ dkms status                                        # DKMSで管理しているモジュールの状態を見る
flashcache, 3.1.3+git20150701, 4.4.0-34-generic, x86_64: installed
iscsitarget, 1.4.20.3+svn502, 4.4.0-31-generic, x86_64: installed
iscsitarget, 1.4.20.3+svn502, 4.4.0-34-generic, x86_64: installed
virtualbox, 5.0.32, 4.4.0-34-generic, x86_64: installed
```

**1 行がカンマ区切りで 4 つの情報を持っています。**

| 位置 | 内容 | どこを見るか |
|:--|:--|:--|
| **1 番目** | **モジュール名** | どのドライバか |
| **2 番目** | **モジュールのバージョン** | 入っている版 |
| **3 番目** | **対象のカーネルバージョン** | **今の `uname -r` の行があるか**を確認する |
| **4 番目** | **アーキテクチャ**（`x86_64` など） | 通常は 1 種類 |
| **コロンの右** | **状態** | 下の表を参照 |

| 状態 | 意味 | 対処 |
|:--|:--|:--|
| **`installed`** | ビルドされ、**配置済み**。正常 | — |
| **`built`** | ビルドは済んだが、**まだ配置されていない** | `dkms install` を実行する |
| **`added`** | **登録されただけ**。まだビルドしていない | `dkms build` → `dkms install` |
| **`broken`** | ビルドに失敗している | カーネルヘッダの有無と、ビルドログを確認する |

**読み方の例**

```text
  iscsitarget, 1.4.20.3+svn502, 4.4.0-31-generic, x86_64: installed
  iscsitarget, 1.4.20.3+svn502, 4.4.0-34-generic, x86_64: installed
                                 ↑ 同じモジュールが 2 つのカーネル向けに入っている
                                    → カーネルを更新しても、どちらでも動く
```

**確認のしかた**

```bash
$ dkms status | grep $(uname -r)                     # 今のカーネル向けが入っているか確認する
$ ls /var/lib/dkms/                                  # DKMSが管理しているモジュールの一覧
```

---

### modules dep の見方

```bash
$ grep "^kernel/fs/xfs" /lib/modules/$(uname -r)/modules.dep   # xfs の行だけ取り出す
kernel/fs/xfs/xfs.ko: kernel/lib/libcrc32c.ko
```

| 見る場所 | 意味 | 何が分かるか |
|:--|:--|:--|
| **コロンの左** | そのモジュール自身のパス（`/lib/modules/(バージョン)/` からの相対） | 実体がどこにあるか |
| **コロンの右** | **依存しているモジュール**（スペース区切り） | **先に読み込まれるもの** |
| **コロンの右が空** | 依存なし | 単独で読み込める |

---

## 参考リンク

- [man 5 modules.dep](https://man7.org/linux/man-pages/man5/modules.dep.5.html)
- [man 8 depmod](https://man7.org/linux/man-pages/man8/depmod.8.html)
- [man 8 modprobe](https://man7.org/linux/man-pages/man8/modprobe.8.html)
- [DKMS（dell/dkms）](https://github.com/dell/dkms)
- [Linux kernel documentation — Kernel module signing facility](https://www.kernel.org/doc/html/latest/admin-guide/module-signing.html)

---

[← このフォルダの目次にもどる](./00_このフォルダにあるもの.md) ｜ [全体の目次にもどる](../README.md)
