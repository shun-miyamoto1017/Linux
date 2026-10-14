#!/usr/bin/env bash
# =============================================================================
# check_deps.sh  (version 3.0 / 2026-10-13)
#
#   オフラインの RHEL サーバで、ローカルリポジトリに置いた RPM の
#   「依存が足りているか」を 1 ラウンド分だけ確認する（ドライラン）。
#
#   1 ラウンドでやること:
#     ① 署名確認 → ② 目次更新 → ③ キャッシュ削除 → ④ ドライラン → ⑤ 判定
#
#   - RHEL 7（yum / createrepo）と RHEL 8 以降（dnf / createrepo_c）を自動判定
#   - システムには一切変更を加えない（--assumeno のドライランのみ）
#   - ラウンドごとに証跡を round01, round02 ... に保存
#
# 終了コード:
#   0 = 依存OK（このまま適用できる）
#   1 = 依存不足あり（missing_hint.tsv を見て RPM を追加する）
#   2 = その他のエラー（署名NG / createrepo 失敗 / 解析できないエラー）
#   3 = 更新対象なし
#
# 変更履歴:
#   1.0 初版
#   2.0 登録済みの鍵の記録・警告を追加
#   3.0 検証で見つかった不具合を修正
#       - [重大] 署名が「無い」RPM を素通りさせていた問題を修正
#       - 日本語が化けていた問題を修正（LC_ALL=C と column の組み合わせ）
#       - grep -P が使えない環境で、不足依存を取りこぼす問題を修正
#       - best の値をログに残す（これで判定文が変わるため）
#       - ヒント検索で、カッコ付きのバージョン記号を外して再検索するようにした
#       - multilib 判定が画面を汚していた問題を修正
# =============================================================================
set -uo pipefail

# dnf/yum のメッセージを英語に固定する。解析を安定させるため。
# 注意: ここで LC_ALL=C にすると column コマンドが日本語を化けさせるので、
#       画面に日本語を出すところだけ LC_ALL を戻す（下の print_table を参照）。
export LC_ALL=C
ORIG_LANG="${LANG:-C.UTF-8}"

REPO_DIR="${REPO_DIR:-/opt/localrepo}"
REPO_ID="${REPO_ID:-localrepo}"
LOG_DIR="${LOG_DIR:-/var/tmp/depcheck_$(date +%Y%m%d)}"
TARGET="${1:-}"

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
fail() { echo "[ERROR] $*" >&2; exit 2; }

# 表を出すときだけロケールを戻す（LC_ALL=C のままだと日本語が \xNN に化ける）
print_table() { LC_ALL="$ORIG_LANG" column -t -s $'\t' "$1"; }

# ---- 前提チェック ------------------------------------------------------------
[[ $EUID -eq 0 ]] || fail "root で実行してください"
[[ -d "$REPO_DIR" ]] || fail "REPO_DIR が存在しません: $REPO_DIR"
ls "$REPO_DIR"/*.rpm >/dev/null 2>&1 || fail "RPM がありません: $REPO_DIR"

# .repo ファイルは「リポジトリID と同じ名前」でなくてもよいので、中身で探す
if ! grep -rqs "^\[${REPO_ID}\]" /etc/yum.repos.d/; then
  fail "リポジトリID [${REPO_ID}] の .repo が /etc/yum.repos.d/ に見つかりません"
fi

# ---- OS 判定 -----------------------------------------------------------------
if command -v dnf >/dev/null 2>&1; then
  PKG=dnf; SUBCMD=upgrade; CREATEREPO=createrepo_c
else
  PKG=yum; SUBCMD=update;  CREATEREPO=createrepo
fi
command -v "$CREATEREPO" >/dev/null 2>&1 || fail "$CREATEREPO がインストールされていません"

# dnf 側の不足依存の抽出に grep -P を使う。使えない環境だと黙って取りこぼすので先に確認する。
if [[ $PKG == dnf ]]; then
  echo x | grep -qoP 'x' 2>/dev/null || fail "grep -P が使えません（この環境では不足依存を抽出できません）"
fi

# ---- ラウンド用ディレクトリ ---------------------------------------------------
mkdir -p "$LOG_DIR"
PREV_RDIR=$(ls -d "$LOG_DIR"/round[0-9]* 2>/dev/null | sort | tail -n1 || true)
ROUND_NO=$(( $(ls -d "$LOG_DIR"/round[0-9]* 2>/dev/null | wc -l) + 1 ))
RDIR="$LOG_DIR/round$(printf '%02d' "$ROUND_NO")"
mkdir -p "$RDIR"

log "===== Round $(printf '%02d' "$ROUND_NO") 開始 ($PKG / $(cat /etc/redhat-release 2>/dev/null || echo 'release 不明')) ====="
log "対象: ${TARGET:-（全パッケージ）}"

# best の値を残す。これが True か False かで、依存不足のときの画面が変わる。
BEST_VAL=$("$PKG" config-manager --dump 2>/dev/null | sed -n 's/^best *= *//p' | head -n1)
[[ -n "$BEST_VAL" ]] && log "best の設定値: $BEST_VAL（1=True なら依存不足で Error 停止、0=False なら Skip して Nothing to do）"

# ---- 1. RPM 一覧と前ラウンドからの差分 ----------------------------------------
ls -1 "$REPO_DIR"/*.rpm | xargs -n1 basename | sort > "$RDIR/rpm_list.txt"
log "RPM 数: $(wc -l < "$RDIR/rpm_list.txt")"
if [[ -n "$PREV_RDIR" && -f "$PREV_RDIR/rpm_list.txt" ]]; then
  comm -13 "$PREV_RDIR/rpm_list.txt" "$RDIR/rpm_list.txt" > "$RDIR/added_since_prev.txt"
  log "前ラウンドから追加された RPM: $(wc -l < "$RDIR/added_since_prev.txt") 件"
fi

# ---- 2. 登録済みの鍵の確認 -----------------------------------------------------
#   rpm -K の OK は「登録済みの鍵のどれかで署名されている」という意味しかない。
#   Red Hat の鍵だけが登録されていれば、OK = Red Hat の正規品と判断できる。
if rpm -q gpg-pubkey --qf '%{VERSION}\t%{SUMMARY}\n' > "$RDIR/gpg_keys.txt" 2>&1; then
  if grep -v 'Red Hat, Inc.' "$RDIR/gpg_keys.txt" | grep -q .; then
    log "⚠️ Red Hat 以外の公開鍵も登録されています（$RDIR/gpg_keys.txt）"
    log "   → 署名OKでも Red Hat 製とは限りません。下の signature_detail.txt の Key ID を確認してください"
  fi
else
  log "⚠️ 公開鍵が1つも登録されていません"
  log "   → rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release を実行してください"
fi

# ---- 3. 署名確認 ---------------------------------------------------------------
#   【重要】rpm -K だけでは不十分。署名が「無い」RPM は digests OK（終了0）で素通りする。
#   そのため「壊れていないか（rpm -K）」と「署名が入っているか（Signature タグ）」を別々に見る。
rpm -K "$REPO_DIR"/*.rpm > "$RDIR/signature.txt" 2>&1
if grep -Eqi 'NOT OK|MISSING KEYS' "$RDIR/signature.txt"; then
  grep -Ei 'NOT OK|MISSING KEYS' "$RDIR/signature.txt"
  fail "壊れている、または鍵の合わない RPM があります（$RDIR/signature.txt）。再取得してください"
fi

# 署名そのものが入っているかを1本ずつ確認する
: > "$RDIR/signature_detail.txt"
: > "$RDIR/unsigned.txt"
for f in "$REPO_DIR"/*.rpm; do
  sig=$(rpm -qpi "$f" 2>/dev/null | sed -n 's/^Signature *: *//p')
  printf '%s\t%s\n' "$(basename "$f")" "${sig:-(取得失敗)}" >> "$RDIR/signature_detail.txt"
  case "$sig" in
    ""|"(none)") basename "$f" >> "$RDIR/unsigned.txt" ;;
  esac
done
if [[ -s "$RDIR/unsigned.txt" ]]; then
  log "❌ 署名が入っていない RPM があります（$(wc -l < "$RDIR/unsigned.txt") 件）"
  sed 's/^/   /' "$RDIR/unsigned.txt"
  fail "署名なしの RPM は出所を保証できません。Red Hat カスタマーポータルから取り直してください"
fi
log "署名確認: OK（全 $(wc -l < "$RDIR/signature_detail.txt") 件に署名あり・壊れなし）"

# ---- 4. 目次更新とキャッシュ削除 ------------------------------------------------
"$CREATEREPO" --update "$REPO_DIR" > "$RDIR/createrepo.log" 2>&1 \
  || fail "$CREATEREPO に失敗しました（$RDIR/createrepo.log）"
"$PKG" clean all > /dev/null 2>&1
log "repodata 更新とキャッシュ削除: OK"

# ---- 5. ドライラン -------------------------------------------------------------
"$PKG" --disablerepo='*' --enablerepo="$REPO_ID" "$SUBCMD" --assumeno ${TARGET:+"$TARGET"} \
  > "$RDIR/dryrun.txt" 2>&1
log "ドライラン完了（$RDIR/dryrun.txt）"

# ---- 6. 不足依存の抽出 ---------------------------------------------------------
if [[ $PKG == yum ]]; then
  # yum 3 の形:  Error: Package: openssh-server-... (localrepo)
  #                    Requires: openssl-libs >= 1:1.0.2k-26
  grep -E '^[[:space:]]+Requires:' "$RDIR/dryrun.txt" \
    | sed -E 's/^[[:space:]]+Requires:[[:space:]]*//' | sort -u > "$RDIR/missing.txt"
  grep -E 'Error: Package:|^[[:space:]]+Requires:' "$RDIR/dryrun.txt" > "$RDIR/missing_detail.txt" || true
else
  # dnf の形:  - nothing provides libcrypto.so.3(OPENSSL_3.0.9)(64bit) needed by openssh-...
  {
    grep -oP 'nothing provides \K.+?(?= needed by)' "$RDIR/dryrun.txt"
    grep -oP 'requires \K.+?(?=, but none of the providers can be installed)' "$RDIR/dryrun.txt"
  } 2>/dev/null | sort -u > "$RDIR/missing.txt"
  grep -E 'Problem|nothing provides|none of the providers|Skipping packages with broken' \
    "$RDIR/dryrun.txt" > "$RDIR/missing_detail.txt" || true
fi

# ---- 7. 不足依存 → 取得するパッケージ名のヒント -----------------------------------
#   サーバに入っている「古い版」を手がかりに、取るべきパッケージ名を推測する。
#   libcrypto.so.3(OPENSSL_3.0.9)(64bit) のようにカッコ付きのバージョン記号が付くと
#   そのままでは当たらないので、記号を外して再検索する。
whatprovides_hint() {
  local cap="$1" name hint
  name=$(awk '{print $1}' <<< "$cap")              # "openssl-libs >= 1:3.0.7" → "openssl-libs"
  if hint=$(rpm -q --whatprovides "$name" --qf '%{NAME}.%{ARCH}\n' 2>/dev/null) \
       && [[ $hint != *"no package provides"* ]]; then
    sort -u <<< "$hint" | paste -sd, -; return
  fi
  # 例: libcrypto.so.3(OPENSSL_3.0.9)(64bit) → libcrypto.so.3()(64bit)
  local stripped
  stripped=$(sed -E 's/\(([A-Za-z0-9_.]+)\)\(/()(/' <<< "$name")
  if [[ $stripped != "$name" ]] \
     && hint=$(rpm -q --whatprovides "$stripped" --qf '%{NAME}.%{ARCH}\n' 2>/dev/null) \
     && [[ $hint != *"no package provides"* ]]; then
    echo "$(sort -u <<< "$hint" | paste -sd, -) (記号を外して特定)"; return
  fi
  echo "(server does not have it: needs lookup)"
}

: > "$RDIR/missing_hint.tsv"
if [[ -s "$RDIR/missing.txt" ]]; then
  printf 'missing_capability\thint_package\n' > "$RDIR/missing_hint.tsv"
  while IFS= read -r cap; do
    printf '%s\t%s\n' "$cap" "$(whatprovides_hint "$cap")" >> "$RDIR/missing_hint.tsv"
  done < "$RDIR/missing.txt"
fi

# ---- 8. 判定 -------------------------------------------------------------------
#   判定の順番には意味がある。
#   best=False のときは、依存不足でも最後に「Nothing to do.」と出る。
#   そのため「不足依存があるか」を先に見る。順番を入れ替えると誤判定する。
echo
if [[ -s "$RDIR/missing.txt" ]]; then
  log "結果: ❌ 依存不足あり（$(wc -l < "$RDIR/missing.txt") 件）"
  print_table "$RDIR/missing_hint.tsv"
  grep -qi 'multilib' "$RDIR/dryrun.txt" && log "⚠️ multilib（i686/x86_64 のバージョン不一致）の可能性あり"
  echo
  log "次にやること: missing_hint.tsv をもとに RPM を取得 → $REPO_DIR に置く → もう一度このスクリプトを実行"
  exit 1
fi

if grep -Eq 'No packages marked for update|Nothing to do' "$RDIR/dryrun.txt"; then
  log "結果: ⚠️ 更新対象なし（RPM の取り違え・el7/el8/el9 の取り違え・既に適用済みでないか確認）"
  exit 3
fi

if grep -Eq '^Error|^ *Problem|Protected multilib' "$RDIR/dryrun.txt"; then
  log "結果: ❌ 自動解析できないエラーがあります。dryrun.txt を確認してください"
  grep -E -A5 '^Error|^ *Problem|Protected multilib' "$RDIR/dryrun.txt" | head -n 30
  exit 2
fi

if grep -Eq 'Exiting on user command|Operation aborted' "$RDIR/dryrun.txt"; then
  log "結果: ✅ 依存OK（このまま適用できる）"
  grep -A8 'Transaction Summary' "$RDIR/dryrun.txt" | tee "$RDIR/summary.txt"

  # サーバに入っていないパッケージは、依存として必要にならない限り適用されない
  for f in "$REPO_DIR"/*.rpm; do
    rpm -qp --qf '%{NAME}.%{ARCH}\n' "$f" 2>/dev/null
  done | sort -u | while IFS= read -r na; do
    rpm -q "$na" >/dev/null 2>&1 || echo "$na"
  done > "$RDIR/not_installed.txt"
  if [[ -s "$RDIR/not_installed.txt" ]]; then
    log "参考: サーバ未導入のパッケージ $(wc -l < "$RDIR/not_installed.txt") 件（not_installed.txt）"
    log "      → 'Installing dependencies' に出ていなければ適用されません"
  fi
  exit 0
fi

log "結果: ❓ 想定外の出力です。dryrun.txt を確認してください"
tail -n 20 "$RDIR/dryrun.txt"
exit 2
