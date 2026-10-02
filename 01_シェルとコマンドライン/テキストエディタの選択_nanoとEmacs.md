# テキストエディタの選択 nanoとEmacs

| | |
|:--|:--|
| **学習の順番** | Phase1 コア ★★★☆☆ |
| **Ping-t の範囲** | Linux1 / GNUとUnixコマンド(主題103) — ファイルの基本的な編集 |
| **業務での使いどころ** | **`crontab -e` や `visudo` を開いたときに出てくるエディタ**。Ubuntu と RHEL 系でデフォルトが違うので、知らないと「いつもと画面が違う」で固まる。`EDITOR` を設定しておけば、どのサーバでも同じエディタが出る |

> **vi の操作**は 3 本に分かれています。
> [viエディタの基本とモード](./viエディタの基本とモード.md) /
> [viエディタの編集操作](./viエディタの編集操作.md) /
> [viエディタの検索置換と保存](./viエディタの検索置換と保存.md)。
> **環境変数の仕組み**は
> [シェル変数と環境変数](./シェル変数と環境変数.md) です。

---

## 目次

- [主なテキストエディタ](#主なテキストエディタ)
- [nano](#nano)
  - [nano の画面の見方](#nano-の画面の見方)
  - [nano のキー操作](#nano-のキー操作)
- [Emacs](#emacs)
- [デフォルトのエディタを決めるもの](#デフォルトのエディタを決めるもの)
  - [EDITOR と VISUAL](#editor-と-visual)
  - [設定を永続化する](#設定を永続化する)
- [どれを使うか](#どれを使うか)
- [参考リンク](#参考リンク)

---

## 主なテキストエディタ

**Linux で問われるのは 3 つ**です。

| エディタ | 特徴 | GUI |
|:--|:--|:-:|
| **`vi` / `vim`** | **踏み台やコンテナでも入っている可能性がいちばん高い**。モードの概念がある。`vim` は vi から派生した高機能版で、現在の Linux ではこちらが標準 | **あり**（gvim） |
| **`nano`** | **操作キーが画面下部に出る**ので初心者でも扱える。軽量 | **なし** |
| **`Emacs`** | 編集・コーディング・デバッグ・他プログラムの操作までこなす**開発環境**。独自に拡張してカスタマイズできる | **あり** |

**「軽くて分かりやすい」が nano、「なんでもできる」が Emacs、「まず入っている」が vi** です。

**`EDITOR` はエディタではありません。** **環境変数の名前**です（後述）。
試験では、エディタの選択肢に混ぜて出されます。

**補足 … `vi` と `vim` の関係**

多くのディストリビューションで **`vi` は `vim` へのリンクか、`vim` の最小構成**になっています。
**踏み台やコンテナの中では `vi` しか入っていないことがある**ので、
**最低限 vi が使えれば困らない**、というのが実務の落としどころです。

---

## nano

**GNU nano は、操作キーの一覧が常に画面に出ているエディタ**です。
**モードがない**ので、開いたらそのまま文字を打てます。

```text
nano [オプション] [ファイル名]
```

### nano の画面の見方

```text
  GNU nano 7.2                  newtest.txt

  （ここに本文を打つ）



                                  [ New File ]
^G Help      ^O Write Out ^W Where Is  ^K Cut       ^T Execute   ^C Location
^X Exit      ^R Read File ^\ Replace   ^U Paste     ^J Justify   ^/ Go To Line
```

**上と下に情報が出ます。**

| 場所 | 中身 |
|:--|:--|
| **最上行** | **バージョン / ファイル名**。変更があると `Modified` が付く |
| **下の 2 行** | **使えるキーの一覧**。**`^` は `Ctrl`** を表す |
| 本文の下 | **`[ New File ]`** … 新規ファイルであることの通知（実測） |

**注意 … バージョンによって画面に出る文字が違います。**

上の画面は **nano 7.2 の実測**です。
**古い環境（nano 2.x 系）では、同じキーに別の名前が付いています。**

| 機能 | **nano 7.2**（実測） | 古い版で見かける表記 |
|:--|:--|:--|
| ヘルプ | **`Help`** | `Get Help` |
| 保存 | **`Write Out`** | `WriteOut` |
| 切り取り | **`Cut`** | `Cut Text` |
| 貼り付け | **`Paste`** | `UnCut Text` |
| 位置表示 | **`Location`** | `Cur Pos` |
| 新規ファイルの通知 | **`[ New File ]`** | `New Buffer` |

**右の列はこの環境では確認できていません**（nano 2.x が手元に無いため）。
**どのバージョンで変わったかも特定していない**ので、目安として見てください。

**キー自体（`^O` で保存、`^X` で終了）は変わりません。**
**画面に出ている文字が違うだけ**なので、迷ったら画面下を読めば足ります。

### nano のキー操作

**すべて `Ctrl` との同時押し**です。画面下部の `^G` は `Ctrl+G` という意味です。

| キー | 意味 |
|:--|:--|
| **`Ctrl+O`** | **保存する**（Write Out。ファイル名を聞かれる） |
| **`Ctrl+X`** | **終了する**（Exit。変更があれば保存するか聞かれる） |
| **`Ctrl+W`** | **検索する**（Where Is） |
| **`Ctrl+K`** | **行を切り取る**（Cut） |
| **`Ctrl+U`** | **貼り付ける**（Paste） |
| `Ctrl+G` | ヘルプ（Help） |
| `Ctrl+R` | 別ファイルを読み込む（Read File） |
| `Ctrl+J` | 段落を整形する（Justify） |
| `Ctrl+C` | カーソル位置の情報を出す（Location） |
| `Ctrl+_` | 指定行へ移動する（Go To Line） |

**vi の `:wq` にあたるのが `Ctrl+O` → `Ctrl+X`** です。
**`Ctrl+X` だけでも、変更があれば保存するか聞かれる**ので、実質これ 1 つで足ります。

```text
   vi    …  :wq        で「保存して終了」
   nano  …  Ctrl+X     で「終了（保存するか聞かれる）」
```

**注意 … `Ctrl+S` では保存できません。**
端末では `Ctrl+S` が画面の停止（フロー制御）に割り当てられていることがあり、
**画面が固まったように見えます**。その場合は **`Ctrl+Q`** で戻ります。

---

## Emacs

**Emacs はエディタというより「編集を中心とした作業環境」**です。

| できること | 例 |
|:--|:--|
| **テキスト編集** | 当然できる |
| **コーディング支援** | 補完・シンタックスハイライト・コンパイル |
| **デバッグ** | デバッガとの連携 |
| **他プログラムの操作** | シェル・メール・バージョン管理 |
| **拡張** | **Emacs Lisp で自分用の機能を書ける** |

**キー操作も `Ctrl` と `Meta`（`Alt` または `Esc`）の組み合わせ**です。

| キー | 意味 |
|:--|:--|
| **`Ctrl+x` `Ctrl+s`** | **保存する** |
| **`Ctrl+x` `Ctrl+c`** | **終了する** |
| `Ctrl+g` | 操作を取り消す |
| `Ctrl+s` | 検索する |

**2 つのキーを続けて押す**のが Emacs の特徴です。

**試験では「高機能でカスタマイズできる開発環境」＝Emacs**、
**「画面下に操作キーが出る軽量エディタ」＝nano** と対比で覚えれば足ります。

---

## デフォルトのエディタを決めるもの

**`crontab -e` や `visudo` のように「編集が必要なコマンド」を実行すると、
エディタが勝手に立ち上がります。**

**何が立ち上がるかはディストリビューションで違います。**

| ディストリビューション | デフォルト |
|:--|:--|
| **CentOS / RHEL 系** | **`vim`** |
| **Ubuntu / Debian 系** | **`nano`** |

**「いつもの vi のつもりで打ったら、nano だった」**という事故がここで起きます。

### EDITOR と VISUAL

**環境変数 `EDITOR` に起動コマンドを設定すると、立ち上がるエディタを変えられます。**

```bash
$ export EDITOR=/usr/bin/vim          # デフォルトのエディタを vim にする
$ echo $EDITOR                        # 設定されたことを確認する
/usr/bin/vim
$ crontab -e                          # 以降、これで vim が起動する
```

**似た環境変数に `VISUAL` があります。**

| 変数 | もともとの意味 |
|:--|:--|
| **`EDITOR`** | **行単位の（画面を使わない）エディタ**。`ed` のような古い前提 |
| **`VISUAL`** | **画面を使うエディタ**。`vi` のようなもの |

**いまはどちらも「使いたいエディタ」を指す**ようになっていて、
**`VISUAL` を先に見て、無ければ `EDITOR` を見る**のが通例です。

**Debian / Ubuntu では `sensible-editor` がその判断をしています。**
中身を見れば優先順位がそのまま書かれています。

```bash
$ grep -n 'for candidate' /usr/bin/sensible-editor   # 探す順番を確かめる
41:for candidate in "$VISUAL" "$EDITOR" "$SENSIBLE_EDITOR" "$SELECTED_EDITOR"; do
54:for candidate in "$EDITOR" "$SELECTED_EDITOR"; do
58:for candidate in editor nano nano-tiny vi; do
```

**`VISUAL` → `EDITOR` → …** の順で探し、
**どれも無ければ `editor` → `nano` → `nano-tiny` → `vi`** と落ちていきます（実測）。

**この `editor` が Ubuntu で nano になる仕掛け**が alternatives です。

```bash
$ ls -l /usr/bin/editor               # editor の実体をたどる
lrwxrwxrwx 1 root root 24 Oct 10  2024 /usr/bin/editor -> /etc/alternatives/editor
$ ls -l /etc/alternatives/editor      # さらにたどると nano に行き着く
lrwxrwxrwx 1 root root 9 Oct 10  2024 /etc/alternatives/editor -> /bin/nano
```

**切り替えるには `update-alternatives --config editor`** を使います。

**確実に効かせたいときは、両方を同じ値にする**のが安全です。

```bash
$ export EDITOR=/usr/bin/vim          # 両方そろえておく
$ export VISUAL=/usr/bin/vim          # VISUAL も同じ値にしておく
```

**紛らわしい名前**

| 変数 | 正体 |
|:--|:--|
| **`PATH`** | **コマンドの検索パス**を設定する環境変数 |
| **`LD_LIBRARY_PATH`** | **共有ライブラリの検索パス**を設定する環境変数 |
| `EDIT` / `TEXT` | **存在しない**（試験の誤答） |

### 設定を永続化する

**`export` はそのシェルの中だけ**なので、ログインし直すと消えます。
**恒久的にしたいときは設定ファイルに書きます**
（[シェルの設定ファイル](./シェルの設定ファイル.md)）。

```bash
$ echo 'export EDITOR=/usr/bin/vim' >> ~/.bashrc   # 自分だけに効かせる
$ echo 'export VISUAL=/usr/bin/vim' >> ~/.bashrc   # VISUAL も書いておく
$ source ~/.bashrc                                 # いますぐ反映する
```

**全ユーザに効かせたいときは `/etc/profile.d/` にファイルを置きます。**

```bash
# /etc/profile.d/editor.sh
export EDITOR=/usr/bin/vim
export VISUAL=/usr/bin/vim
```

**`/etc/profile` 本体は直接編集しないでください。** OS の更新で上書きされます。

---

## どれを使うか

| 場面 | 選択 |
|:--|:--|
| **どのサーバでも使える最低限** | **`vi`**。これだけは必修 |
| **設定ファイルをさっと直したい（自分の端末）** | `nano` でもよい |
| **作業用サーバで腰を据えて開発する** | `vim` / `Emacs` |
| **手順書に書く** | **`vi`** で統一する（相手の環境に nano が無いことがある） |

**結論 … vi は避けて通れません。**
`nano` は楽ですが、**踏み台やコンテナ、レスキューモードには入っていないことが多い**です。
**「いざというときに使えるのは vi だけ」**という前提で覚えてください。

**補足 … エディタを使わずに直す手もあります**

短い修正なら `sed -i` のほうが速く、手順書にも書きやすいです
（[sedによる置換](../02_テキスト処理と正規表現/sedによる置換.md)）。

```bash
$ sed -i.bak 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config   # 1行だけ直す
```

**「人が開いて直す」より「コマンドで直す」ほうが、作業証跡も残ります。**

---

## 参考リンク

- [man 1 nano](https://man7.org/linux/man-pages/man1/nano.1.html)
- [man 1 emacs](https://man7.org/linux/man-pages/man1/emacs.1.html)
- [man 5 crontab](https://man7.org/linux/man-pages/man5/crontab.5.html)
- [GNU nano 公式](https://www.nano-editor.org/)

---

[← 全体の目次にもどる](../README.md)
