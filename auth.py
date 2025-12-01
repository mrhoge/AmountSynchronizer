"""
Google Colab 認証セル用スクリプト

このファイルの内容を Google Colab の最初のセル（セル1）に貼り付けて実行します。
認証が完了すると、後続のセルで gspread を使用できるようになります。

Copyright (C) 2023-2025 mrhoge

This file is part of AmountSynchronizer.

InvoiceRenamer is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed WITHOUT ANY WARRANTY; for more details see
the LICENSE file in the distribution root.
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