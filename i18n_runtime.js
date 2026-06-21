;(function(){
"use strict";
var T={
"Always Ask":"常に確認",
"Always Allow":"常に許可",
"App Settings":"アプリ設定",
"System Prompt":"システムプロンプト",
"Cancel All Tasks":"すべてのタスクをキャンセル",
"Cancel Task":"タスクをキャンセル",
"Clear":"クリア",
"Conversation History":"会話履歴",
"Disable Task":"タスクを無効化",
"Enable Task":"タスクを有効化",
"Model":"モデル",
"Open Settings":"設定を開く",
"Project Settings":"プロジェクト設定",
"Skills are instructions that extend what Agent can do.":"スキルはエージェントの機能を拡張する指示（インストラクション）です。",
"Rules":"ルール",
"Skills":"スキル",
"Task Logs":"タスクログ",
"Agent Loading":"エージェント読み込み中...",
"Add Scheduled Task":"スケジュールタスクの追加",
"Background Task":"バックグラウンドタスク",
"Log in to use the agent":"エージェントを使用するにはログインしてください",
"No internet. Agent features may not work.":"インターネット接続がありません。エージェント機能が動作しない可能性があります。",
"Stop Task":"タスクを停止",
"Submit":"送信",
"Workspace Command Access":"コマンド実行権限",
"Workspace File Access":"ファイルアクセス権限",
"Workspace Web Access":"ウェブアクセス権限",
"New Conversation":"新しい会話",
"Delete Conversation":"会話を削除",
"Archive Conversation":"会話をアーカイブ",
"Confirm Undo":"元に戻す確認",
"Confirm Browser Interaction":"ブラウザ操作の確認",
"Confirm Window Reload":"ウィンドウ再読込の確認",
"Something went wrong":"エラーが発生しました",
"Good response":"良い回答",
"Bad response":"悪い回答",
"Provide Feedback":"フィードバックを送る",
"Provide feedback":"フィードバック",
"Send Feedback":"フィードバックを送信",
"Try Again":"再試行",
"Reload Window":"ウィンドウを再読込",
"Select Project":"プロジェクトを選択",
"Add Folder":"フォルダーを追加",
"Close Folder":"フォルダーを閉じる",
"Create Project":"プロジェクトを作成",
"Always Proceed":"常に続行",
"Learn more":"詳しく見る",
"Copied":"コピーしました",
"Loading...":"読み込み中...",
"Installing...":"インストール中...",
"Waiting for user input":"ユーザー入力を待機中",
"Background Tasks":"バックグラウンドタスク",
"Appearance":"外観",
"General":"一般",
"Permissions":"権限",
"Customizations":"カスタマイズ",
"Shortcuts":"ショートカット",
"Account":"アカウント",
"Sign In":"サインイン",
"Not Signed In":"未サインイン",
"Copy Path":"パスをコピー",
"Copy File Path":"ファイルパスをコピー",
"Copy File Name":"ファイル名をコピー",
"Code Search":"コード検索",
"Workspace Settings":"ワークスペース設定",
"Token Usage":"トークン使用量"
};
var L=localStorage.getItem("ag_lang")||"en";
function trNode(n){
if(n.nodeType===3){var s=n.textContent,t=s.trim();if(t&&T[t])n.textContent=s.replace(t,T[t])}
else if(n.nodeType===1){for(var i=0;i<n.childNodes.length;i++)trNode(n.childNodes[i]);
if(n.placeholder&&T[n.placeholder])n.placeholder=T[n.placeholder];
if(n.title&&T[n.title])n.title=T[n.title]}
}
function trAll(){
var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
while(w.nextNode()){var s=w.currentNode.textContent,t=s.trim();
if(t&&T[t])w.currentNode.textContent=s.replace(t,T[t])}
document.querySelectorAll("[placeholder]").forEach(function(e){if(T[e.placeholder])e.placeholder=T[e.placeholder]});
document.querySelectorAll("[title]").forEach(function(e){if(T[e.title])e.title=T[e.title]});
}
new MutationObserver(function(ms){if(L!=="ja")return;
ms.forEach(function(m){m.addedNodes.forEach(function(n){trNode(n)})})
}).observe(document.documentElement,{childList:true,subtree:true});
function init(){
if(L==="ja")setTimeout(trAll,200);
var d=document.createElement("div");
d.id="ag-i18n";
d.style.cssText="position:fixed;top:6px;right:52px;z-index:9999;display:flex;align-items:center;gap:4px";
d.innerHTML='<span style="color:#888;font-size:11px">\u{1F310}</span>'
+'<select id="ag-lang-sel" style="background:var(--bg-base,#1e1e2e);color:var(--text-normal,#cdd6f4);border:1px solid var(--border-color,#45475a);border-radius:4px;padding:1px 4px;font-size:11px;cursor:pointer;outline:none">'
+'<option value="en">English</option><option value="ja">日本語</option></select>';
document.body.appendChild(d);
var sel=document.getElementById("ag-lang-sel");
sel.value=L;
sel.onchange=function(){
if(sel.value==="en"){localStorage.setItem("ag_lang","en");location.reload()}
else{L="ja";localStorage.setItem("ag_lang","ja");trAll()}
};
}
if(document.body)init();else document.addEventListener("DOMContentLoaded",init);
})();/*ag_i18n_runtime*/
