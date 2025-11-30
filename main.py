import gspread
from google.auth import default
import re
from datetime import datetime

def search_spreadsheets(gc, keyword):
    """
    Google Driveでスプレッドシートを検索

    Args:
        gc: gspreadクライアント
        keyword: 検索キーワード

    Returns:
        list: マッチしたスプレッドシートのリスト
    """
    print(f"\n検索中: '{keyword}' を含むスプレッドシート...\n")

    try:
        # すべてのスプレッドシートを取得
        all_files = gc.list_spreadsheet_files()

        # キーワードでフィルタリング
        matched_files = [
            f for f in all_files
            if keyword.lower() in f['name'].lower()
        ]

        return matched_files
    except Exception as e:
        print(f"❌ エラー: スプレッドシートの検索に失敗しました: {str(e)}")
        return []


def select_spreadsheet(gc):
    """
    ユーザーにスプレッドシートを選択させる

    Args:
        gc: gspreadクライアント

    Returns:
        Spreadsheet: 選択されたスプレッドシートオブジェクト
    """
    while True:
        # キーワード入力
        keyword = input("処理対象のスプレッドシート名（の一部）を入力してください: ").strip()

        if not keyword:
            print("⚠️  キーワードを入力してください。\n")
            continue

        # スプレッドシートを検索
        matched_files = search_spreadsheets(gc, keyword)

        if not matched_files:
            print(f"⚠️  '{keyword}' に一致するスプレッドシートが見つかりませんでした。")
            print(f"   別のキーワードで検索しますか? (y/n): ", end="")
            retry = input().strip().lower()
            if retry != 'y':
                print("❌ 処理を中止します。")
                exit()
            print()
            continue

        # 候補を表示
        print(f"✓ {len(matched_files)}件のスプレッドシートが見つかりました:\n")
        for idx, file in enumerate(matched_files, start=1):
            print(f"  [{idx}] {file['name']}")
            print(f"      ID: {file['id']}")

        print()

        # ユーザーに選択を求める
        while True:
            try:
                selection = input(f"使用するスプレッドシートの番号を入力してください (1-{len(matched_files)}), または 'r' で再検索: ").strip()

                if selection.lower() == 'r':
                    print()
                    break

                selected_idx = int(selection) - 1

                if 0 <= selected_idx < len(matched_files):
                    selected_file = matched_files[selected_idx]
                    print(f"\n✓ 選択: {selected_file['name']}\n")

                    # スプレッドシートを開く
                    try:
                        sh = gc.open_by_key(selected_file['id'])
                        return sh
                    except Exception as e:
                        print(f"❌ エラー: スプレッドシートを開けませんでした: {str(e)}")
                        exit()
                else:
                    print(f"⚠️  1から{len(matched_files)}の間の数字を入力してください。\n")
            except ValueError:
                print("⚠️  有効な数字を入力してください。\n")


def check_spreadsheet_owner(sh, creds):
    """
    スプレッドシートの所有者をチェック

    Args:
        sh: スプレッドシートオブジェクト
        creds: 認証情報

    Returns:
        bool: 所有者確認が成功したかどうか
    """
    print("【ステップ0】スプレッドシート所有者を確認中...")

    # 現在のユーザーのメールアドレスを取得
    try:
        current_user_email = creds.id_token.get('email') if hasattr(creds, 'id_token') else None
        if not current_user_email:
            # OAuth2の場合は別の方法で取得
            from google.oauth2.credentials import Credentials
            if isinstance(creds, Credentials):
                import requests
                response = requests.get('https://www.googleapis.com/oauth2/v1/userinfo',
                                      headers={'Authorization': f'Bearer {creds.token}'})
                if response.status_code == 200:
                    current_user_email = response.json().get('email')

        print(f"  現在のユーザー: {current_user_email}")
    except Exception as e:
        print(f"⚠️  警告: 現在のユーザー情報を取得できませんでした: {str(e)}")
        current_user_email = None

    # スプレッドシートの所有者を確認
    try:
        permissions = sh.list_permissions()
        owner_email = None

        for permission in permissions:
            if permission.get('role') == 'owner':
                owner_email = permission.get('emailAddress')
                break

        print(f"  スプレッドシート所有者: {owner_email}")

        # 所有者チェック
        if current_user_email and owner_email:
            if current_user_email.lower() != owner_email.lower():
                print(f"\n❌ エラー: このスプレッドシートはあなたが所有していません")
                print(f"   あなたのアカウント: {current_user_email}")
                print(f"   スプレッドシート所有者: {owner_email}")
                print(f"\n⚠️  セキュリティ上の理由から、自分が所有するスプレッドシートのみ処理できます。")
                print(f"   このスプレッドシートは共有ファイルです。処理を中止します。")
                return False
            else:
                print(f"✓ 所有者確認完了: あなたが所有するスプレッドシートです\n")
                return True
        else:
            print(f"⚠️  警告: 所有者情報を完全に確認できませんでした")
            print(f"   処理を続行しますか? (y/n): ", end="")
            response = input().strip().lower()
            if response != 'y':
                print("❌ 処理を中止します。")
                return False
            print()
            return True

    except Exception as e:
        print(f"⚠️  警告: 所有者チェックに失敗しました: {str(e)}")
        print(f"   処理を続行しますか? (y/n): ", end="")
        response = input().strip().lower()
        if response != 'y':
            print("❌ 処理を中止します。")
            return False
        print()
        return True


def main():
    """
    メイン処理
    """
    print("=" * 60)
    print("Google スプレッドシート自動化ツール")
    print("=" * 60)
    print()

    # 認証情報を取得（別セルで認証済みを想定）
    creds, _ = default()
    gc = gspread.oauth()

    # スプレッドシートを検索・選択
    sh = select_spreadsheet(gc)

    # 所有者チェック
    if not check_spreadsheet_owner(sh, creds):
        exit()

    # シートを取得
    try:
        input_sheet = sh.worksheet('入力シート')
        summary_sheet = sh.worksheet('実績管理シート')
    except Exception as e:
        print(f"❌ エラー: シートが見つかりません: {str(e)}")
        print(f"   '入力シート' と '実績管理シート' が存在することを確認してください。")
        exit()

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

    print("\n" + "=" * 60)
    print("✅ 全処理完了！")
    print("=" * 60)


if __name__ == "__main__":
    main()
