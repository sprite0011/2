import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os

# ==========================================
# 1. セッション状態（データ保持）の初期化
# ==========================================

# --- 1. セッション状態の初期化（ファイルから読み込む） ---
SAVE_FILE = "save_data.csv"

if 'point_owners' not in st.session_state:
    if os.path.exists(SAVE_FILE):
        try:
            # 保存ファイルからデータを読み込む
            df_save = pd.read_csv(SAVE_FILE)
            # { "スポット名": "color" } の辞書形式に変換
            st.session_state.point_owners = dict(zip(df_save['spot'], df_save['team']))
        except:
            st.session_state.point_owners = {}
    else:
        st.session_state.point_owners = {}


if 'ward_owners' not in st.session_state:
    all_wards = [
        "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", 
        "江東区", "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", 
        "中野区", "杉並区", "豊島区", "北区", "荒川区", "板橋区", 
        "練馬区", "足立区", "葛飾区", "江戸川区"
    ]
    st.session_state.ward_owners = {name: "gray" for name in all_wards}

if 'selected_pin' not in st.session_state:
    st.session_state.selected_pin = None

if 'point_owners' not in st.session_state:
    st.session_state.point_owners = {}

# ==========================================
# 2. 関数定義（ロジックの部品作成）
# ==========================================

def load_geojson(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

@st.cache_data
def load_points():
    if os.path.exists("points.csv"):
        df = pd.read_csv("points.csv")
        df['ward'] = df['ward'].str.strip()
        df['name'] = df['name'].str.strip()
        return df
    return pd.DataFrame(columns=['ward', 'name', 'lat', 'lng'])

# --- 区の色を判定するコアロジック ---
def determine_ward_color(ward_name, df_points):
    ward_df = df_points[df_points['ward'] == ward_name]
    red_count = 0
    blue_count = 0
    
    for _, row in ward_df.iterrows():
        p_full_name = row['name']
        p_short_name = p_full_name.split(":")[-1].strip() if ":" in p_full_name else p_full_name
        
        owner = st.session_state.point_owners.get(p_short_name)
        if owner == "red":
            red_count += 1
        elif owner == "blue":
            blue_count += 1
            
    if red_count == 0 and blue_count == 0:
        return "gray"
    elif red_count > blue_count:
        return "red"
    elif blue_count > red_count:
        return "blue"
    else:
        return "purple" # 同数は紫

# --- 全区の色をリフレッシュする ---
def refresh_all_ward_colors(df_points):
    for ward in st.session_state.ward_owners.keys():
        new_color = determine_ward_color(ward, df_points)
        st.session_state.ward_owners[ward] = new_color

# ==========================================
# 3. メイン処理（UIと地図の構築）
# ==========================================

st.title("⚔️ 東京23区 陣取りバトル")

# サイドバー設定
st.sidebar.header("🕹️ 操作パネル")
my_team = st.sidebar.radio("あなたのチーム", ["red", "blue"])
st.sidebar.info("ピンをクリック → 下のボタンで制圧！")

# データの読み込み
df_points = load_points()

# 【重要】描画の「直前」に全区の所有状況を再計算する
refresh_all_ward_colors(df_points)

# 地図の土台作成
m = folium.Map(location=[35.6895, 139.75], zoom_start=11)

# A. 各区の面（GeoJSON）を描画
wards_data = [
    {"file": "chiyoda.geojson", "label": "千代田区"}, {"file": "chuo.geojson", "label": "中央区"},
    {"file": "minato.geojson", "label": "港区"}, {"file": "shinjuku.geojson", "label": "新宿区"},
    {"file": "bunkyo.geojson", "label": "文京区"}, {"file": "taito.geojson", "label": "台東区"},
    {"file": "sumida.geojson", "label": "墨田区"}, {"file": "koto.geojson", "label": "江東区"},
    {"file": "shinagawa.geojson", "label": "品川区"}, {"file": "meguro.geojson", "label": "目黒区"},
    {"file": "ota.geojson", "label": "大田区"}, {"file": "setagaya.geojson", "label": "世田谷区"},
    {"file": "shibuya.geojson", "label": "渋谷区"}, {"file": "nakano.geojson", "label": "中野区"},
    {"file": "suginami.geojson", "label": "杉並区"}, {"file": "toshima.geojson", "label": "豊島区"},
    {"file": "kita.geojson", "label": "北区"}, {"file": "arakawa.geojson", "label": "荒川区"},
    {"file": "itabashi.geojson", "label": "板橋区"}, {"file": "nerima.geojson", "label": "練馬区"},
    {"file": "adachi.geojson", "label": "足立区"}, {"file": "katsushika.geojson", "label": "葛飾区"},
    {"file": "edogawa.geojson", "label": "江戸川区"}
]

for w_info in wards_data:
    geojson_data = load_geojson(w_info["file"])
    if geojson_data:
        current_color = st.session_state.ward_owners.get(w_info["label"], "gray")
        folium.GeoJson(
            geojson_data,
            style_function=lambda x, color=current_color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.4,
            },
            tooltip=w_info["label"]
        ).add_to(m)

# B. 各ピンの描画
for _, row in df_points.iterrows():
    p_full_name = row['name']
    p_short_name = p_full_name.split(":")[-1].strip() if ":" in p_full_name else p_full_name
    
    # ピン個別の所有チームを取得
    team = st.session_state.point_owners.get(p_short_name)
    
    # チームに応じた色（未占領はblack）
    icon_color = "black" 
    if team == "red": icon_color = "red"
    elif team == "blue": icon_color = "blue"
    
    folium.Marker(
        location=[row['lat'], row['lng']],
        popup=p_full_name,
        icon=folium.Icon(color=icon_color, icon="info-sign")
    ).add_to(m)

# ==========================================
# 4. 地図の表示とクリックイベントの処理
# ==========================================

output = st_folium(m, width="100%", height=600, key="map")

# ピンをクリックした情報を取得
if output.get("last_object_clicked_popup"):
    st.session_state.selected_pin = output["last_object_clicked_popup"]

# --- チェックイン操作UI ---
if st.session_state.selected_pin:
    # 判定用に文字を分割
    raw_text = st.session_state.selected_pin.replace("：", ":")
    parts = raw_text.split(":")
    clicked_spot = parts[-1].strip()

    st.write("---")
    st.subheader(f"📍 選択中: {clicked_spot}")
    
    current_p_owner = st.session_state.point_owners.get(clicked_spot)
    
    if current_p_owner == my_team:
        st.info(f"ここはすでに {my_team} チームが制圧しています。")
    else:
        if st.button(f"🚩 {clicked_spot} にチェックイン！"):
            # 1. セッション状態を更新
            st.session_state.point_owners[clicked_spot] = my_team
            
            # 2. ファイルに保存する
            # 辞書をデータフレームに変換してCSV保存
            new_save_df = pd.DataFrame([
                {"spot": k, "team": v} for k, v in st.session_state.point_owners.items()
            ])
            new_save_df.to_csv(SAVE_FILE, index=False, encoding="utf-8")
            
            st.success(f"{clicked_spot} を制圧し、ファイルに保存しました！")
            st.session_state.selected_pin = None
            st.rerun()

    if st.button("キャンセル"):
        st.session_state.selected_pin = None
        st.rerun()

# --- 7. 管理者用データ初期化機能 ---
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ 管理者メニュー")
admin_password = st.sidebar.text_input("リセット用パスワード", type="password")

# パスワードが正しい場合のみボタンを表示（例として "reset123" と設定）
if admin_password == "987654321":
    if st.sidebar.button("⚠️ データを初期化する", help="すべてのチェックイン情報を削除します"):
        # 1. セッション状態を空にする
        st.session_state.point_owners = {}
        
        # 2. 保存用CSVファイルを初期化（ヘッダーのみにする）
        df_reset = pd.DataFrame(columns=['spot', 'team'])
        df_reset.to_csv(SAVE_FILE, index=False, encoding="utf-8")
        
        st.sidebar.success("データを初期化しました。")
        st.rerun() # 地図と色を即座にリセット

# --- 8. スコアボードの表示 ---
# 各チームが占領している区の数をカウント
ward_counts = list(st.session_state.ward_owners.values())
red_wards = ward_counts.count("red")
blue_wards = ward_counts.count("blue")
purple_wards = ward_counts.count("purple") # 同数の区

# メイン画面にスコアを表示
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🔴 赤チーム", f"{red_wards} 区")
with col2:
    st.metric("🔵 青チーム", f"{blue_wards} 区")
with col3:
    st.metric("🟣 競合中", f"{purple_wards} 区")

st.markdown("---")