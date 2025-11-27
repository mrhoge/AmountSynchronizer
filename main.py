from google.colab import auth
import gspread
from google.auth import default
import re
from datetime import datetime

# 認証
auth.authenticate_user()
gc = gspread.oauth()

# スプレッドシート開く
sh = gc.open('あなたのスプレッドシート名')
input_sheet = sh.worksheet('入力シート')
summary_sheet = sh.worksheet('実績管理シート')  # 実際のシート名に変更

# ===== 1. 入力シートからデータ読込 =====
print("【ステップ1】入力シートからデータを読込中...")
input_data = input_sheet.get_all_values()

# テーブル内の「合計」行を除外し、キーと金額をマッピング
data_map = {}
for row_idx, row in enumerate(input_data[1:], start=2):  # ヘッダーをスキップ
    if len(row) < 2 or not row[0]:
        continue
    
    item_key = row[0].strip()
    
    # 「合計」行を除外
    if '合計' in item_key:
        print(f"  スキップ: '{item_key}' （合計行）")
        continue
    
    amount_str = row[1].strip().replace('円', '')
    
    # 金額を数値化
    try:
        amount = int(amount_str)
        data_map[item_key] = amount
    except ValueError:
        print(f"  警告: '{amount_str}' を数値に変換できません")

print(f"✓ 読み込んだデータ: {len(data_map)}件\n")

# ===== 2. 集計シートから B 列（詳細）を取得し、重複チェック =====
print("【ステップ2】集計シートの B 列から重複チェック中...")
summary_data = summary_sheet.get_all_values()

detail_row_map = {}  # B列の値 → 行番号のマッピング

for row_idx, row in enumerate(summary_data, start=1):
    if len(row) < 2:
        continue
    detail = row[1].strip() if row[1] else ""
    
    if detail and detail not in ['詳細', '']:  # ヘッダーを除外
        if detail in detail_row_map:
            # 重複検出
            print(f"❌ エラー: B列に重複が見つかりました")
            print(f"   詳細: '{detail}' が {detail_row_map[detail]} 行目と {row_idx} 行目に存在")
            print(f"→ 処理を中止します。B列の重複を修正してください。")
            exit()
        
        detail_row_map[detail] = row_idx

print(f"✓ B列の有効なエントリ: {len(detail_row_map)}件、重複なし\n")

# ===== 3. 入力データと集計シート間で照合チェック =====
print("【ステップ3】入力データと集計シートの照合チェック中...")
missing_keys = []
for key in data_map.keys():
    if key not in detail_row_map:
        missing_keys.append(key)

if missing_keys:
    print(f"⚠️  警告: 集計シートに見つからない詳細があります")
    for key in missing_keys:
        print(f"   '{key}' → {data_map[key]}円")
    print(f"→ これらは貼付されません。B列に追加するか、入力シートを修正してください。\n")

# ===== 4. 月の列番号を決定 =====
print("【ステップ4】入力月を決定中...")
input_month = input("貼付先の月を入力してください（例：2025/6）: ").strip()

try:
    year, month = map(int, input_month.split('/'))
    # 月の検証
    if not (1 <= month <= 12):
        raise ValueError
except:
    print("❌ 入力形式が正しくありません。例：2025/6")
    exit()

# E列が2025/6, F列が2025/07...というヘッダーを想定
header_row = summary_data[0]
target_col = None

for col_idx, header_cell in enumerate(header_row[4:], start=5):  # E列から開始
    if str(year) in header_cell and str(month).zfill(2) in header_cell:
        target_col = col_idx
        print(f"✓ 対象月: {year}/{month} → {header_cell} 列\n")
        break

if not target_col:
    print(f"❌ エラー: {year}/{month} の列が見つかりません")
    print(f"   ヘッダー行を確認してください")
    exit()

# ===== 5. 既存データのチェック =====
print("【ステップ5】既存データをチェック中...")
existing_data = []

for row_num, row in enumerate(summary_data, start=1):
    if row_num == 1:  # ヘッダーをスキップ
        continue
    
    if len(row) >= target_col:
        cell_value = row[target_col - 1].strip() if target_col - 1 < len(row) else ""
        
        # セルに値がある場合を検出
        if cell_value and cell_value not in ['0', '']:
            detail = row[1].strip() if len(row) > 1 else f"行{row_num}"
            existing_data.append((row_num, detail, cell_value))

if existing_data:
    print(f"⚠️  警告: 対象月（{year}/{month}）に既存データが見つかりました")
    print(f"   以下の行は既に値が入っています：\n")
    for row_num, detail, value in existing_data:
        print(f"   行{row_num}: '{detail}' = {value}")
    
    print(f"\n❌ 既存データがあるため、処理を中止します。")
    print(f"   既存データを確認・削除してから、もう一度実行してください。")
    exit()

print(f"✓ 既存データなし。処理を続行します。\n")

# ===== 6. スプレッドシートのバックアップコピー作成 =====
print("【ステップ6】スプレッドシートのバックアップを作成中...")
try:
    # 現在の日時を取得してバックアップ名を生成
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"{sh.title}_バックアップ_{timestamp}"

    # スプレッドシートをコピー
    backup_sh = sh.copy(title=backup_name)

    # バックアップを元のスプレッドシートと同じフォルダに移動
    # (デフォルトではルートフォルダに作成されるため)
    original_parents = sh.list_permissions()

    print(f"✓ バックアップ作成完了: '{backup_name}'")
    print(f"   バックアップID: {backup_sh.id}")
    print(f"   URL: {backup_sh.url}\n")

except Exception as e:
    print(f"⚠️  警告: バックアップの作成に失敗しました: {str(e)}")
    print(f"   処理を続行しますか? (y/n): ", end="")
    response = input().strip().lower()
    if response != 'y':
        print("❌ 処理を中止します。")
        exit()
    print()

# ===== 7. データを集計シートに貼付 =====
print("【ステップ7】金額を貼付中...")
updates = []

for key, amount in data_map.items():
    if key in detail_row_map:
        row_num = detail_row_map[key]
        summary_sheet.update_cell(row_num, target_col, amount)
        updates.append(f"行{row_num}: '{key}' → {amount}円")

print(f"✓ 貼付完了: {len(updates)}件")
for update in updates:
    print(f"  {update}")

print("\n✅ 全処理完了！")
