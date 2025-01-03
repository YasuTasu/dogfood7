from flask import Flask, request,  jsonify,render_template, session , redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os
import json
from sqlalchemy import inspect

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = 'your_secret_key_here' 

db = SQLAlchemy(app)

# グローバル変数としてAAFCO基準値を定義
aafco_standards = {}

# 食材モデルの定義
class Ingredient(db.Model):
    __tablename__ = 'ingredient'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=True)  # カテゴリを追加
    food_code = db.Column(db.Integer, nullable=False, unique=True)  # 食品番号を追加
    name = db.Column(db.String(80), nullable=False)
    WATER = db.Column(db.Float, nullable=False)
    ENERC_KCAL = db.Column(db.Float, nullable=False)
    PROT = db.Column(db.Float, nullable=False)
    ARG = db.Column(db.Float, nullable=False)
    HIS = db.Column(db.Float, nullable=False)
    ILE = db.Column(db.Float, nullable=False)
    LEU = db.Column(db.Float, nullable=False)
    LYS = db.Column(db.Float, nullable=False)
    MET = db.Column(db.Float, nullable=False)
    CYS = db.Column(db.Float, nullable=False)
    PHE = db.Column(db.Float, nullable=False)
    TYR = db.Column(db.Float, nullable=False)
    THR = db.Column(db.Float, nullable=False)
    TRP = db.Column(db.Float, nullable=False)
    VAL = db.Column(db.Float, nullable=False)
    F18D2N6 = db.Column(db.Float, nullable=False)
    F18D3N3 = db.Column(db.Float, nullable=False)
    F20D5N3 = db.Column(db.Float, nullable=False)
    F22D6N3 = db.Column(db.Float, nullable=False)
    FAT = db.Column(db.Float, nullable=False)
    CA = db.Column(db.Float, nullable=False)
    P = db.Column(db.Float, nullable=False)
    K = db.Column(db.Float, nullable=False)
    NAT = db.Column(db.Float, nullable=False)
    MG = db.Column(db.Float, nullable=False)
    FE = db.Column(db.Float, nullable=False)
    CU = db.Column(db.Float, nullable=False)
    MN = db.Column(db.Float, nullable=False)
    ZN = db.Column(db.Float, nullable=False)
    YO = db.Column(db.Float, nullable=False)
    SE = db.Column(db.Float, nullable=False)
    RETOL = db.Column(db.Float, nullable=False)
    VITD = db.Column(db.Float, nullable=False)
    TOCPHA = db.Column(db.Float, nullable=False)
    THIA = db.Column(db.Float, nullable=False)
    RIBF = db.Column(db.Float, nullable=False)
    PANTAC = db.Column(db.Float, nullable=False)
    NIA = db.Column(db.Float, nullable=False)
    VITB6A = db.Column(db.Float, nullable=False)
    FOL = db.Column(db.Float, nullable=False)
    VITB12 = db.Column(db.Float, nullable=False)

    def to_dict(self):
        """Ingredientオブジェクトを辞書形式で返す"""
        return {col.name: getattr(self, col.name) for col in self.__table__.columns if col.name not in ['id', 'food_code', 'name']}

# AAFCO基準値をロードする関数
def load_aafco_standards():
    aafco_path = os.path.join(os.path.dirname(__file__), 'aafco_standards.xlsx')
    if not os.path.exists(aafco_path):
        print("AAFCO基準値のExcelファイルがありません")
        return {}

    # Excelファイルをロード
    df = pd.read_excel(aafco_path, engine='openpyxl')

    # NaN を None に変換
    df['maximum'] = df['maximum'].where(df['maximum'].notna(), None)

    # データを変換
    standards = {}
    for _, row in df.iterrows():
        nutrient = row["nutrient"]
        standard_type = row["standard"].lower().replace(" ", "_")  # 'Adult Dog' → 'adult_dog'

        # 基準タイプが辞書にない場合は初期化
        if standard_type not in standards:
            standards[standard_type] = {}

        # 栄養素の基準値を追加
        standards[standard_type][nutrient] = {
            "minimum": row["minimum"],
            "maximum": row.get("maximum", None)  # 最大値がない場合はNoneを設定
        }

    return standards

# 栄養素の合計を計算する関数
def calculate_totals(selected_list):
    nutrient_totals = {nutrient: 0 for nutrient in aafco_standards.keys()}
    for item in selected_list:
        food_code = item['food_code']
        grams = item['grams']
        nutrients = food_database.get(food_code, {})
        for nutrient, value in nutrients.items():
            nutrient_totals[nutrient] += value * (grams / 100)
    return nutrient_totals

# 不足栄養素に基づく提案食材を生成する関数
def suggest_ingredients_for_deficiencies(deficiencies, excesses):
    suggestions = {}
    for nutrient in deficiencies:
        # 過剰栄養素を含まない食材を選択
        ingredients = (
            Ingredient.query.filter(getattr(Ingredient, nutrient) > 0)
            .filter(~Ingredient.food_code.in_(
                [item.food_code for item in Ingredient.query if item.food_code in excesses]
            ))
            .order_by(getattr(Ingredient, nutrient).desc())
            .limit(5)
            .all()
        )
        suggestions[nutrient] = [
            {
                "food_code": ing.food_code,
                "name": ing.name,
                "value": getattr(ing, nutrient, 0)
            }
            for ing in ingredients
        ]
    return suggestions

# 初期データベースの処理
def process_excel():
    excel_path = os.path.join(os.path.dirname(__file__), 'ingredients.xlsx')
    if not os.path.exists(excel_path):
        print("Excelファイル(ingredients.xlsx)が存在しません")
        return

    # Excelファイルの読み込み
    df = pd.read_excel(excel_path, engine='openpyxl')

    # データクレンジング: Tr, N/A, Undefined を 0 に置き換える
    df = df.replace(['Tr', 'N/A', 'Undefined', None], 0)

    # テーブルが存在しない場合に作成
    inspector = inspect(db.engine)
    if not inspector.has_table('ingredient'):
        db.create_all()

    # 既存データがある場合はスキップ
    if Ingredient.query.count() > 0:
        print("既存のデータがあります。処理をスキップします。")
        return

    # データベースへの登録
    for index, row in df.iterrows():
        ingredient = Ingredient(
            category=row["食品群"],  # Excelからカテゴリを読み取る
            food_code=int(row["食品番号"]),
            name=row["食品名"],
            WATER=float(row["水分"]),
            ENERC_KCAL=float(row["エネルギー"]),
            PROT=float(row["タンパク質"]),
            ARG=float(row["アルギニン"]),
            HIS=float(row["ヒスチジン"]),
            ILE=float(row["イソロイシン"]),
            LEU=float(row["ロイシン"]),
            LYS=float(row["リジン"]),
            MET=float(row["メチオニン"]),
            CYS=float(row["シスチン"]),
            PHE=float(row["フェニルアラニン"]),
            TYR=float(row["チロシン"]),
            THR=float(row["スレオニン"]),
            TRP=float(row["トリプトファン"]),
            VAL=float(row["バリン"]),
            F18D2N6=float(row["リノール酸"]),
            F18D3N3=float(row["αリノレン酸"]),
            F20D5N3=float(row["エイコサペンタエン酸"]),
            F22D6N3=float(row["ドコサヘキサエン酸"]),
            FAT=float(row["脂肪"]),
            CA=float(row["カルシウム"]),
            P=float(row["リン"]),
            K=float(row["カリウム"]),
            NAT=float(row["ナトリウム"]),
            MG=float(row["マグネシウム"]),
            FE=float(row["鉄"]),
            CU=float(row["銅"]),
            MN=float(row["マンガン"]),
            ZN=float(row["亜鉛"]),
            YO=float(row["ヨウ素"]),
            SE=float(row["セレン"]),
            RETOL=float(row["ビタミンA"]),
            VITD=float(row["ビタミンD"]),
            TOCPHA=float(row["ビタミンE"]),
            THIA=float(row["ビタミンB1"]),
            RIBF=float(row["ビタミンB2"]),
            PANTAC=float(row["パントテン酸"]),
            NIA=float(row["ナイアシン"]),
            VITB6A=float(row["ビタミンB6"]),
            FOL=float(row["葉酸"]),
            VITB12=float(row["ビタミンB12"]),
        )
        try:
            db.session.add(ingredient)
            db.session.commit()
        except Exception as e:
            print(f"行 {index} でエラーが発生しました: {e}")
            db.session.rollback()

# nutrient_labels をグローバル変数として定義
nutrient_labels = {
    'WATER': ('水分', 'g'),
    'ENERC_KCAL': ('エネルギー', 'kcal'),
    'PROT': ('タンパク質', 'g'),
    'ARG': ('アルギニン', 'g'),
    'HIS': ('ヒスチジン', 'g'),
    'ILE': ('イソロイシン', 'g'),
    'LEU': ('ロイシン', 'g'),
    'LYS': ('リジン', 'g'),
    'MET': ('メチオニン', 'g'),
    'CYS': ('シスチン', 'g'),
    'PHE': ('フェニルアラニン', 'g'),
    'TYR': ('チロシン', 'g'),
    'THR': ('スレオニン', 'g'),
    'TRP': ('トリプトファン', 'g'),
    'VAL': ('バリン', 'g'),
    'F18D2N6': ('リノール酸', 'g'),
    'F18D3N3': ('αリノレン酸', 'g'),
    'F20D5N3': ('エイコサペンタエン酸', 'g'),
    'F22D6N3': ('ドコサヘキサエン酸', 'g'),
    'FAT': ('脂肪', 'g'),
    'CA': ('カルシウム', 'g'),
    'P': ('リン', 'g'),
    'K': ('カリウム', 'g'),
    'NAT': ('ナトリウム', 'g'),
    'MG': ('マグネシウム', 'g'),
    'FE': ('鉄', 'mg'),
    'CU': ('銅', 'mg'),
    'MN': ('マンガン', 'mg'),
    'ZN': ('亜鉛', 'mg'),
    'YO': ('ヨウ素', 'mg'),
    'SE': ('セレン', 'mg'),
    'RETOL': ('ビタミンA', 'μg'),
    'VITD': ('ビタミンD', 'μg'),
    'TOCPHA': ('ビタミンE', 'μg'),
    'THIA': ('ビタミンB1', 'mg'),
    'RIBF': ('ビタミンB2', 'mg'),
    'PANTAC': ('パントテン酸', 'mg'),
    'NIA': ('ナイアシン', 'mg'),
    'VITB6A': ('ビタミンB6', 'mg'),
    'FOL': ('葉酸', 'mg'),
    'VITB12': ('ビタミンB12', 'mg'),
}

# 共通ユーティリティ関数
def calculate_nutrients(selected_list):
    """
    栄養素の合計を計算する関数
    """
    nutrient_totals = {nutrient: 0 for nutrient in aafco_standards.keys()}
    for item in selected_list:
        ingredient = Ingredient.query.filter_by(food_code=item['food_code']).first()
        if ingredient:
            for nutrient in aafco_standards.keys():
                value = getattr(ingredient, nutrient, 0) or 0
                nutrient_totals[nutrient] += value * (item['grams'] / 100)
        else:
            print(f"Warning: Ingredient with food_code {item['food_code']} not found")
    return nutrient_totals

# エンドポイントの定義
@app.route('/')
def index():
    # `index.html` に食材リストを表示
    ingredients = Ingredient.query.all()
    return render_template('index.html', ingredients=ingredients)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # セッションを完全にリセット
        session.clear()

        # JSON データの取得
        data = request.get_json()

        # 新しいデータをセッションに保存
        selected_list = data.get('selected_list', [])
        session['selected_list'] = selected_list

        # 食材コードリストの作成
        selected_food_codes = [int(item['food_code']) for item in selected_list]

        # データベースから選択された食材を取得
        selected_ingredients = Ingredient.query.filter(Ingredient.food_code.in_(selected_food_codes)).all()

        # 栄養素の合計を計算
        totals = {nutrient: 0 for nutrient in next(iter(aafco_standards.values())).keys()}
        total_grams = 0
        selected_list_tuples = []

        for item in selected_list:
            food_code = int(item['food_code'])
            grams = float(item['grams'])

            # 対応する食材を取得
            ingredient = next((ing for ing in selected_ingredients if ing.food_code == food_code), None)
            if ingredient:
                selected_list_tuples.append((food_code, grams, ingredient.name))
                total_grams += grams
                for nutrient in totals.keys():
                    nutrient_value = getattr(ingredient, nutrient.upper(), 0) or 0  # 大文字対応
                    totals[nutrient] += nutrient_value * (grams / 100)

        # 判定ロジック（成犬用と幼犬用の両方）
        adult_deficiencies = [
            nutrient for nutrient, total in totals.items()
            if total < aafco_standards.get('adult_dog', {}).get(nutrient, {}).get('minimum', 0)
        ]
        adult_excesses = [
            nutrient for nutrient, total in totals.items()
            if aafco_standards.get('adult_dog', {}).get(nutrient, {}).get('maximum') is not None
            and total > aafco_standards['adult_dog'][nutrient]['maximum']
        ]

        puppy_deficiencies = [
            nutrient for nutrient, total in totals.items()
            if total < aafco_standards.get('puppy', {}).get(nutrient, {}).get('minimum', 0)
        ]
        puppy_excesses = [
            nutrient for nutrient, total in totals.items()
            if aafco_standards.get('puppy', {}).get(nutrient, {}).get('maximum') is not None
            and total > aafco_standards['puppy'][nutrient]['maximum']
        ]

        # 提案食材は幼犬基準で計算
        puppy_suggestions = suggest_ingredients_for_deficiencies(puppy_deficiencies, puppy_excesses)

        # 提案食材をセッションに保存（不足項目のみ）
        simplified_suggestions = {
            nutrient: [{"food_code": item["food_code"], "name": item["name"]} for item in items]
            for nutrient, items in puppy_suggestions.items()
        }
        session['suggestions'] = simplified_suggestions  # 提案食材を保存

        # 結果をテンプレートに渡す
        return render_template(
            'calculate.html',
            totals=totals,
            selected_list=selected_list_tuples,
            total_grams=total_grams,
            deficiencies={'adult_dog': adult_deficiencies, 'puppy': puppy_deficiencies},
            excesses={'adult_dog': adult_excesses, 'puppy': puppy_excesses},
            suggestions=puppy_suggestions,
            nutrient_labels=nutrient_labels,
            aafco_standards=aafco_standards
        )
    except Exception as e:
        print(f"Unhandled Exception in /calculate: {e}")
        return jsonify({"error": str(e)}), 500

def suggest_best_ingredients(deficiencies):
    """
    不足している複数の栄養素を部分的にでも補える食材を提案する
    """
    best_suggestions = []

    # すべての食材を取得
    all_ingredients = Ingredient.query.all()

    for ingredient in all_ingredients:
        total_score = 0
        partial_score = 0
        covered_nutrients = []

        for nutrient in deficiencies:
            nutrient_value = getattr(ingredient, nutrient, 0) or 0
            standard_value = aafco_standards.get(nutrient, 0)

            if standard_value > 0 and nutrient_value > 0:
                partial_score = min(nutrient_value / standard_value, 1.0)  # カバー率を1.0で最大化
                total_score += partial_score
                covered_nutrients.append(nutrient)

        # スコアがゼロでない食材を提案候補に追加
        if total_score > 0:
            best_suggestions.append({
                "food_code": ingredient.food_code,
                "name": ingredient.name,
                "score": round(total_score, 2),
                "covered_nutrients": covered_nutrients
            })

    # スコア順に並べて上位5つを返す
    return sorted(best_suggestions, key=lambda x: x['score'], reverse=True)[:5]


def calculate_nutrients(selected_list):
    nutrient_totals = {nutrient: 0 for nutrient in aafco_standards.keys()}
    for item in selected_list:
        ingredient = Ingredient.query.filter_by(food_code=item['food_code']).first()
        if ingredient:
            for nutrient in aafco_standards.keys():
                value = getattr(ingredient, nutrient, 0) or 0
                nutrient_totals[nutrient] += value * (item['grams'] / 100)
        else:
            print(f"Warning: Ingredient with food_code {item['food_code']} not found")
    return nutrient_totals


@app.route('/adjust', methods=['GET', 'POST'])
def adjust():
    if request.method == 'GET':
        try:
            # セッションからデータを取得
            selected_list = session.get('selected_list', [])
            suggestions = session.get('suggestions', {})  # 提案食材もセッションから取得

            # デバッグログ
            print("GET /adjust:")
            print(f"selected_list: {selected_list}")
            print(f"suggestions: {suggestions}")

            # 選択されたリストを整形
            selected_food_codes = [item['food_code'] for item in selected_list]
            ingredients = Ingredient.query.filter(Ingredient.food_code.in_(selected_food_codes)).all()
            
            # 初期選択された食材のリストを作成
            selected_list = [
                {
                    'food_code': ing.food_code,
                    'grams': next((item['grams'] for item in selected_list if str(item['food_code']) == str(ing.food_code)), 100),
                    'name': ing.name
                }
                for ing in ingredients
            ]

            # 初期の栄養素合計値を計算
            nutrient_totals = {nutrient: 0 for nutrient in nutrient_labels.keys()}
            for item in selected_list:
                food_code = item['food_code']
                grams = item['grams']
                ingredient = next((ing for ing in ingredients if ing.food_code == food_code), None)
                if ingredient:
                    for nutrient in nutrient_totals.keys():
                        nutrient_value = getattr(ingredient, nutrient.upper(), 0) or 0
                        nutrient_totals[nutrient] += nutrient_value * (grams / 100)

            # 判定ロジック（成犬用と幼犬用の両方）
            adult_deficiencies = [
                nutrient for nutrient, total in nutrient_totals.items()
                if total < aafco_standards.get('adult_dog', {}).get(nutrient, {}).get('minimum', 0)
            ]
            adult_excesses = [
                nutrient for nutrient, total in nutrient_totals.items()
                if aafco_standards.get('adult_dog', {}).get(nutrient, {}).get('maximum') is not None
                and total > aafco_standards['adult_dog'][nutrient]['maximum']
            ]

            puppy_deficiencies = [
                nutrient for nutrient, total in nutrient_totals.items()
                if total < aafco_standards.get('puppy', {}).get(nutrient, {}).get('minimum', 0)
            ]
            puppy_excesses = [
                nutrient for nutrient, total in nutrient_totals.items()
                if aafco_standards.get('puppy', {}).get(nutrient, {}).get('maximum') is not None
                and total > aafco_standards['puppy'][nutrient]['maximum']
            ]

            # 提案食材を計算
            puppy_suggestions = suggest_ingredients_for_deficiencies(puppy_deficiencies, [])


            # テンプレート用データ
            response_data = {
                "nutrient_totals": nutrient_totals,
                "selected_ingredients": selected_list,
                "deficiencies": {
                    "adult_dog": adult_deficiencies,
                    "puppy": puppy_deficiencies
                },
                "excesses": {
                    "adult_dog": adult_excesses,
                    "puppy": puppy_excesses
                },
                "suggestions": puppy_suggestions,
                "total_grams": sum(item['grams'] for item in selected_list),
                "nutrient_labels": nutrient_labels,
                "aafco_standards": aafco_standards,
            }

            print("Response data prepared for adjust:", response_data)
            return render_template('adjust.html', data=response_data)

        except Exception as e:
            print(f"Error in GET /adjust: {e}")
            return render_template('adjust.html', data={})

    if request.method == 'POST':
        try:
            data = request.json
            print("Received POST data at /adjust:", data)
            session['selected_list'] = data.get('selected_ingredients', [])
            return jsonify({"message": "Data updated successfully"})
        except Exception as e:
            print(f"Error in POST /adjust: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/calculate-nutrients', methods=['POST'])
def calculate_nutrients_endpoint():
    try:
        data = request.json
        selected_ingredients = data.get('selected_ingredients', [])

        # 栄養素合計の初期化
        nutrient_totals = {nutrient: 0 for nutrient in aafco_standards["adult_dog"].keys()}

        # 各食材の栄養素を合計
        for item in selected_ingredients:
            food_code = item.get('food_code')
            grams = item.get('grams', 0)

            # 食材データを取得 (仮: データベースやリストから)
            ingredient = Ingredient.query.filter_by(food_code=food_code).first()
            if not ingredient:
                continue

            for nutrient in nutrient_totals.keys():
                value_per_100g = getattr(ingredient, nutrient, 0) or 0
                nutrient_totals[nutrient] += value_per_100g * (grams / 100)

        # 判定結果を基準ごとに作成
        results = {}
        for standard_type, standards in aafco_standards.items():
            results[standard_type] = {}
            for nutrient, values in standards.items():
                total = nutrient_totals.get(nutrient, 0)
                minimum = values["minimum"]
                maximum = values["maximum"]

                if total < minimum:
                    results[standard_type][nutrient] = "不足"
                elif maximum is not None and total > maximum:
                    results[standard_type][nutrient] = "過剰"
                else:
                    results[standard_type][nutrient] = "適合"

        return jsonify({
            "nutrient_totals": nutrient_totals,
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/recalculate', methods=['POST'])
def recalculate():
    try:
        data = request.json
        selected_list = data.get('selected_ingredients', [])

        # データ形式を検証
        if not all(isinstance(item, dict) and 'food_code' in item and 'grams' in item for item in selected_list):
            raise ValueError("Invalid data format for selected_ingredients")

        # 栄養素の合計を計算
        nutrient_totals = calculate_totals(selected_list)

        # 不足栄養素の判定
        deficiencies = [
            nutrient for nutrient, total in nutrient_totals.items()
            if total < aafco_standards.get(nutrient, 0)
        ]

        # 提案食材の再生成
        suggestions = suggest_ingredients_for_deficiencies(deficiencies)

        return jsonify({
            "nutrient_totals": nutrient_totals,
            "deficiencies": deficiencies,
            "suggestions": suggestions
        })

    except Exception as e:
        print(f"Error in POST /recalculate: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ingredients', methods=['GET'])
def get_ingredients():
    """
    全食材リストを取得するエンドポイント。
    """
    try:
        ingredients = Ingredient.query.all()
        results = [{"food_code": ing.food_code, "name": ing.name} for ing in ingredients]
        return jsonify({"ingredients": results})
    except Exception as e:
        print(f"全食材リスト取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/search-ingredients', methods=['GET'])
def search_ingredients():
    """
    食材検索エンドポイント。
    クエリ文字列を使用して、食材名を部分一致で検索します。
    """
    query = request.args.get('query', '').strip().lower()
    if not query:
        return jsonify({"ingredients": []})

    ingredients = Ingredient.query.filter(Ingredient.name.ilike(f"%{query}%")).all()
    results = [{"food_code": ing.food_code, "name": ing.name} for ing in ingredients]
    return jsonify({"ingredients": results})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        process_excel()  # データベース初期化
        aafco_standards = load_aafco_standards()

    # アプリケーションの起動
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


