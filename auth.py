"""
Google Colab 認証セル用スクリプト

このファイルの内容を Google Colab の最初のセル（セル1）に貼り付けて実行してください。
認証が完了すると、後続のセルで gspread を使用できるようになります。
"""

from google.colab import auth
import gspread

# 認証実行
print("=" * 60)
print("Google 認証を開始します...")
print("=" * 60)

auth.authenticate_user()

print("\n✅ 認証が完了しました！")
print("次のセル（メイン処理）を実行してください。")
