# v0.2 保存と認証

## 保存戦略

### D1

用途:

- プロジェクト
- 話者設定
- プリセット
- 初期段階の SRT / EXO 本文

方針:

- 初期版は D1 のみで共有を成立させる
- SRT / EXO / preview 用メタデータは `payload_json` に含める
- まず共有と変換を優先し、資産分離は後段で行う

### R2

用途:

- 初期版では必須にしない
- 将来的なテンプレート EXO 原本
- 将来的な SRT 原本
- 将来的な生成キャッシュ

方針:

- 支払方法設定が必要なので、初期導入では使わない
- D1 に内包しづらいサイズや件数になった時点で導入する

## R2 key 設計

導入する場合の予約:

- `templates/team_xxx/asset_xxx.exo`
- `srts/project_xxx/speaker_xxx/asset_xxx.srt`

この設計は後段用であり、初期版では未使用でもよい。

## 認証

前提:

- 利用者は身内メンバーのみ

方針:

- すべての共有 API は認証前提にする
- 初期段階では細かい権限制御より、同一グループ内での共同編集を優先する

## 共有権限

- プロジェクト: 共有メンバー全員が閲覧・更新可能
- プリセット: 共有メンバー全員が閲覧・更新可能
- 音声そのものや、将来の大きい素材だけを必要なら別権限にする

## 初期運用方針

- まずは D1 のみで共有を成立させる
- `payload_json` に SRT / EXO / preview 用メタデータを含める
- R2 は必要性が出てから追加する


## Local V2 store durability boundary

`backend/v2_store.py` must not overwrite the only accepted `project.json` / `preset.json` in place.

Persistence contract:

1. Serialize JSON in memory before touching the target file.
2. Write a temporary file in the target directory.
3. Flush and `fsync` the temporary file contents.
4. Close the temporary file, then publish it with same-filesystem `os.replace`.
5. If any step before replace fails, remove the temporary file and preserve the previous accepted target unchanged.

This guarantees that readers do not observe a partially written target and that failures before replace do not destroy the previous accepted file. The implementation does not `fsync` the directory entry, so crash/power-loss durability of directory metadata immediately after replace is outside this guarantee.

If an existing store file cannot be decoded as UTF-8 JSON, the store must stop with bounded `ERR-STORAGE-CORRUPT` semantics and must not silently reinitialize or overwrite that file. Recovery from corrupted data is an explicit user/application action.
