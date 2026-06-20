# Antigravity 2.0 (スタンドアロン版) 日本語化パッチの作成計画

このプランでは、開発ツールである「Antigravity 2.0」スタンドアロン版（トレイ常駐型クライアント）の日本語化パッチスクリプト `apply_ja_patch_standalone.py` を作成し、適用する手順を定義します。

## 対象コンポーネントと仕組み

スタンドアロン版のAntigravity 2.0は、以下の2重構造で構築されています。双方を適切に日本語化します。

1. **Electronシェル (`resources/app.asar`)**
   - 役割: トレイアイコン、アプリ起動時のセットアップウィザード、ウィンドウ外殻。
   - 手法: `npx asar` コマンドでアーカイブを展開し、`dist/ideInstall/wizardHtml.js` 内のウェルカムテキスト等を日本語化した後、再度 `app.asar` に再パッケージします。

2. **Language Server (`resources/bin/language_server.exe`)**
   - 役割: メインエージェントUI（チャット、アプリ設定、ワークスペース設定）をHTTPSサーバーで配信。
   - 手法: Web資産（React bundle等）がGoバイナリ内のZIPアーカイブ（オフセット `107141712`、サイズ `2,884,187` バイト）として埋め込まれています。
     - ZIPを展開し、UIリソース（`main.js`）内の表示テキストを日本語化します。
     - 再度ZIPアーカイブを作成し、ZIPのコメント領域を使ってサイズを元のサイズと1バイトの狂いもなく同一に揃えます（**バイト長一致パッチ**）。
     - これをバイナリの元の位置に書き戻すことで、バイナリの破損を完全に防ぎつつWebUIを日本語化します。

---

## ユーザーレビューが必要な項目

> [!IMPORTANT]
> - 本パッチは、インストール済みの実バイナリ (`language_server.exe`) および ASARアーカイブを直接書き換えるため、Antigravity 2.0本体のアップデートが行われると変更が上書きされます。その場合は、作成するスクリプトを再度実行することで再適用が可能です。
> - 万が一動作に問題が生じた場合に備え、パッチ適用前に自動でバックアップファイル（`.bak`）を作成し、`--rollback` オプションで即時に元の状態へ復元できるように設計します。

---

## 提案される変更点

### [Workspace Root]

#### [NEW] [apply_ja_patch_standalone.py](file:///c:/Dev/AG_language/apply_ja_patch_standalone.py)
新規作成する日本語化パッチスクリプト。以下の機能を持ちます：
- `app.asar` および `language_server.exe` の自動バックアップ。
- `app.asar` の自動展開、`wizardHtml.js` 等のテキスト翻訳、および再パッケージ。
- `language_server.exe` からのZIP抽出、`main.js` 内の文字列置換、サイズ微調整（ダミーコメント追加によるバイト長合わせ）、バイナリへの書き戻し。
- `--rollback` オプションによる完全復元。

---

## 翻訳辞書案（一部抜粋）

### セットアップウィザード
- `"Welcome to the new Antigravity!"` -> `"新しい Antigravity へようこそ！"`
- `"Antigravity has been redesigned to put agents first..."` -> `"Antigravityはエージェントを第一に考えるように再設計されました。もしエディタ版を引き続き使用したい場合は、個別アプリ「Antigravity IDE」をダウンロードできます。"`
- `"Download the Antigravity IDE"` -> `"Antigravity IDE をダウンロードする"`
- `"Explore the new Antigravity"` -> `"新しい Antigravity を使ってみる"`

### エージェントWeb UI (`main.js` 用)
- `"AGENT"` -> `"エージェント"`
- `"App Settings"` -> `"アプリ設定"`
- `"Workspace Settings"` -> `"ワークスペース設定"`
- `"Always Ask"` -> `"常に確認"`
- `"Token Usage"` -> `"トークン使用量"`
- `"System Prompt"` -> `"システムプロンプト"`

---

## 検証プラン

### 手動検証
1. アプリ（Antigravity）を一度完全に終了します。
2. `apply_ja_patch_standalone.py` を実行し、パッチを適用します。
3. アプリを起動し、トレイメニュー、セットアップウィザード、およびブラウザで表示されるエージェントUIが日本語になっているか確認します。
4. `apply_ja_patch_standalone.py --rollback` を実行し、元の英語表記に戻ることを確認します。
