"""
Google Colab 認証セル用スクリプト

このファイルの内容を Google Colab の最初のセル（セル1）に貼り付けて実行してください。
認証が完了すると、後続のセルで gspread を使用できるようになります。
"""

# ユーザー認証情報を取得します
from google.colab import auth
from google.auth import default
import gspread

# 認証実行
print("=" * 60)
print("Google 認証を開始します...")
print("=" * 60)

## セッション用認証取得・変数格納
auth.authenticate_user()
creds, _ = default()

## gspreadクライアントの生成
gc = gspread.authorize(creds)

print("\n✅ 認証が完了しました！")
print("次のセル（メイン処理）を実行してください。")
