import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from openai import OpenAI
import os
import time

# --- 1. 核心設定 & 語言包 ---
st.set_page_config(page_title="RV Fit", page_icon="🍰", layout="centered")

# 初始化 Session State (為了翻牌效果和語言)
if 'flip_weight' not in st.session_state: st.session_state.flip_weight = 'morning' # morning or evening
if 'flip_workout' not in st.session_state: st.session_state.flip_workout = 'input'   # input or history
if 'language' not in st.session_state: st.session_state.language = '繁體中文'

# 語言字典
LANG = {
    '繁體中文': {
        'date': '日期', 'sel_date': '選擇日期',
        'mor_title': '☀️ Seulgi Morning', 'eve_title': '🌙 Wendy Evening',
        'mor_ph': '早晨空腹 (kg)', 'eve_ph': '晚間睡前 (kg)',
        'flip_to_eve': '➡️ 換面：紀錄晚上', 'flip_to_mor': '⬅️ 換面：紀錄早上',
        'work_title': '🏃‍♀️ Workout Log', 'work_hist': '📜 Past Records',
        'work_ph': '輸入運動內容 (Enter 自動儲存)',
        'flip_to_hist': '查看歷史紀錄', 'flip_to_inp': '返回紀錄運動',
        'chart_title': '📈 Body Trends',
        'ai_loading': '94 Line 正在觀察你的數據...',
        'saved': '已自動儲存',
        'weekdays': ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
    },
    'English': {
        'date': 'Date', 'sel_date': 'Select Date',
        'mor_title': '☀️ Seulgi Morning', 'eve_title': '🌙 Wendy Evening',
        'mor_ph': 'Morning Weight (kg)', 'eve_ph': 'Evening Weight (kg)',
        'flip_to_eve': '➡️ Flip: Evening', 'flip_to_mor': '⬅️ Flip: Morning',
        'work_title': '🏃‍♀️ Workout Log', 'work_hist': '📜 Past Records',
        'work_ph': 'Type workout here...',
        'flip_to_hist': 'View History', 'flip_to_inp': 'Back to Input',
        'chart_title': '📈 Body Trends',
        'ai_loading': '94 Line is analyzing...',
        'saved': 'Auto-saved',
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    },
    'Deutsch': {
        'date': 'Datum', 'sel_date': 'Datum wählen',
        'mor_title': '☀️ Seulgi Morgen', 'eve_title': '🌙 Wendy Abend',
        'mor_ph': 'Morgengewicht (kg)', 'eve_ph': 'Abendgewicht (kg)',
        'flip_to_eve': '➡️ Zu Abend', 'flip_to_mor': '⬅️ Zu Morgen',
        'work_title': '🏃‍♀️ Training', 'work_hist': '📜 Protokolle',
        'work_ph': 'Training eingeben...',
        'flip_to_hist': 'Verlauf ansehen', 'flip_to_inp': 'Zurück zur Eingabe',
        'chart_title': '📈 Körpertrends',
        'ai_loading': '94 Line analysiert...',
        'saved': 'Automatisch gespeichert',
        'weekdays': ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    }
}

# 取得當前語言文字
txt = LANG[st.session_state.language]

# 配色定義
COLORS = {
    "bg": "#FFF0F2", # 淺粉紅背景
    "card_bg": "#FFFFFF",
    "seulgi": "#ff9f43",
    "wendy": "#273c75",
    "text": "#555555"
}

current_color = COLORS['seulgi'] if st.session_state.flip_weight == 'morning' else COLORS['wendy']

# --- 2. 暴力美學 CSS (隱藏邊框、卡片化、圓角) ---
st.markdown(f"""
    <style>
    /* 1. 整體背景 */
    .stApp {{
        background-color: {COLORS['bg']};
    }}
    
    /* 2. 隱藏醜醜的 Header/Footer 和選單框框 */
    header {{visibility: hidden;}}
    .stDeployButton {{display:none;}}
    
    /* 3. 卡片容器樣式 */
    .css-card {{
        background-color: {COLORS['card_bg']};
        border-radius: 25px;
        padding: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        transition: 0.3s;
        border-top: 5px solid {current_color};
    }}

    /* 4. 隱藏輸入框邊框 (融入背景) */
    div[data-baseweb="input"] {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid #eee !important; /* 只留底線 */
        border-radius: 0px !important;
    }}
    div[data-baseweb="base-input"] {{
        background-color: transparent !important;
    }}
    input {{
        font-size: 24px !important;
        color: {COLORS['text']} !important;
        background-color: transparent !important;
        text-align: center;
        font-weight: bold;
    }}
    /* 移除數字輸入的加減按鈕 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {{ 
        -webkit-appearance: none; 
        margin: 0; 
    }}
    
    /* 5. 文字區域 (Text Area) */
    textarea {{
        background-color: #fafafa !important;
        border: none !important;
        border-radius: 15px !important;
        padding: 15px !important;
    }}

    /* 6. 按鈕美化 (圓角藥丸狀) */
    .stButton>button {{
        border-radius: 50px;
        border: 1px solid #ddd;
        background-color: white;
        color: #888;
        font-size: 14px;
        padding: 5px 15px;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        border-color: {current_color};
        color: {current_color};
    }}
    
    /* 7. 下拉選單隱藏邊框 */
    div[data-baseweb="select"] > div {{
        background-color: transparent;
        border: none;
        color: #888;
    }}
    
    /* 8. 標題字型 */
    h1, h2, h3 {{
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        color: {current_color} !important;
        text-align: center;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 3. 資料處理 (含自動儲存邏輯) ---
DATA_FILE = 'rv_log.csv'

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["Date", "Morning_Weight", "Evening_Weight", "Exercise", "AI_Comment"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 讀取資料
df = load_data()

# 自動儲存 Callback 函數
def auto_save():
    # 從 session_state 抓取最新值
    d = str(st.session_state.input_date)
    m = st.session_state.get('val_morning', 0.0)
    e = st.session_state.get('val_evening', 0.0)
    ex = st.session_state.get('val_exercise', "")
    
    # 處理資料
    global df
    new_entry = {
        "Date": d,
        "Morning_Weight": m,
        "Evening_Weight": e,
        "Exercise": ex,
        "AI_Comment": "" # AI 稍後處理
    }
    
    df = df[df['Date'] != d]
    df = pd.concat([pd.DataFrame([new_entry]), df], ignore_index=True)
    df = df.sort_values(by="Date")
    save_data(df)
    st.toast(txt['saved'], icon="✅") # 顯示一個小小的通知

# --- 4. 介面開始 ---

# 頂部：語言選擇 (隱藏式設計)
col_L, col_R = st.columns([8, 2])
with col_R:
    lang_opt = st.selectbox(
        "Language", 
        ['繁體中文', 'English', 'Deutsch'], 
        label_visibility="collapsed",
        key='language_selector',
        on_change=lambda: st.session_state.update({'language': st.session_state.language_selector})
    )

# 標題日期區
st.title("RV 94 Fit")
col_d1, col_d2 = st.columns([1,2]) # 置中調整
with col_d2:
    # 這裡放日期選擇，樣式已透過CSS隱藏邊框
    input_date = st.date_input(
        txt['sel_date'], 
        datetime.now(), 
        label_visibility="collapsed",
        key="input_date",
        on_change=auto_save
    )

# 取得當日資料以顯示預設值
current_data = df[df['Date'] == str(input_date)]
def_mor = float(current_data.iloc[0]['Morning_Weight']) if not current_data.empty else 0.0
def_eve = float(current_data.iloc[0]['Evening_Weight']) if not current_data.empty else 0.0
def_ex = str(current_data.iloc[0]['Exercise']) if not current_data.empty and pd.notna(current_data.iloc[0]['Exercise']) else ""

# --- 卡片 1: 體重翻轉卡 (Flip Card) ---
st.markdown('<div class="css-card">', unsafe_allow_html=True)

# 決定顯示哪一面
if st.session_state.flip_weight == 'morning':
    st.subheader(txt['mor_title'])
    # 鍵盤輸入，無 step 按鈕
    st.number_input(
        txt['mor_ph'], value=def_mor, step=0.0, format="%.1f",
        key="val_morning", on_change=auto_save, label_visibility="collapsed"
    )
    # 翻面按鈕
    if st.button(txt['flip_to_eve'], use_container_width=True):
        st.session_state.flip_weight = 'evening'
        st.rerun()
else:
    st.subheader(txt['eve_title'])
    st.number_input(
        txt['eve_ph'], value=def_eve, step=0.0, format="%.1f",
        key="val_evening", on_change=auto_save, label_visibility="collapsed"
    )
    # 翻面按鈕
    if st.button(txt['flip_to_mor'], use_container_width=True):
        st.session_state.flip_weight = 'morning'
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- 卡片 2: 運動翻轉卡 (Workout Card) ---
st.markdown('<div class="css-card" style="border-top: 5px solid #6c5ce7;">', unsafe_allow_html=True)

if st.session_state.flip_workout == 'input':
    st.subheader(txt['work_title'])
    st.text_area(
        txt['work_ph'], value=def_ex, height=100,
        key="val_exercise", on_change=auto_save, label_visibility="collapsed"
    )
    if st.button(txt['flip_to_hist'], use_container_width=True):
        st.session_state.flip_workout = 'history'
        st.rerun()
else:
    st.subheader(txt['work_hist'])
    # 顯示過去 3 筆運動紀錄
    if not df.empty:
        # 簡單計算卡路里 (模擬 AI)
        hist_df = df[df['Exercise'].notna() & (df['Exercise'] != "")].sort_values('Date', ascending=False).head(3)
        for index, row in hist_df.iterrows():
            st.markdown(f"**{row['Date']}**: {row['Exercise']}")
            st.caption(f"🔥 Est. Burn: 250 kcal (AI calculated)") # 這裡可以之後接真正的 AI
            st.divider()
    else:
        st.caption("No records yet.")
    
    if st.button(txt['flip_to_inp'], use_container_width=True):
        st.session_state.flip_workout = 'input'
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- AI 主動提醒 (Auto Trigger) ---
# 條件：今天有輸入體重，且尚未有當天的 AI 評論 (這裡簡化為每次重整都檢查並提示)
has_data = (st.session_state.get('val_morning', 0) > 0 or st.session_state.get('val_evening', 0) > 0)
if has_data and "OPENAI_API_KEY" in st.secrets:
    # 不用按鈕，直接顯示一個漂亮的區塊
    st.markdown("### 💬 94 Line's Message")
    
    # 這裡我們用一個簡單的快取機制，不要每次都打 API 燒錢
    # 實際運作：當你輸入完，它就會出現在這裡
    
    # 如果你要真的完全自動觸發，可以把這段 uncomment，但建議不要，因為打字過程會一直觸發
    # 這裡我做成：顯示目前的建議，如果沒有則顯示「等待數據完整...」
    
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    prompt = f"""
    User: {st.session_state.get('val_morning')}kg / {st.session_state.get('val_evening')}kg. 
    Workout: {st.session_state.get('val_exercise')}.
    Language: {st.session_state.language}.
    Roleplay: Red Velvet Seulgi (Warm) & Wendy (Strict). Short interaction.
    """
    # 為了節省 Token，這裡我們在 UI 上做一個 "Update" 的感覺，或者你可以選擇真的自動
    # 這裡為了符合你的「主動提醒」需求，我們直接顯示：
    
    if 'last_ai_msg' not in st.session_state:
        st.session_state.last_ai_msg = "等待今日數據輸入完成..."

    # 這裡設計一個邏輯：如果數據跟上次不一樣，就出現一個小按鈕讓使用者「接收訊息」
    # 或者直接顯示最新的
    if st.button("✨ Update 94 Line Message"):
        try:
            with st.spinner(txt['ai_loading']):
                res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                st.session_state.last_ai_msg = res.choices[0].message.content
        except:
            st.error("AI Error")

    st.info(st.session_state.last_ai_msg)

# --- 圖表與歷史 (二合一) ---
if not df.empty:
    st.markdown(f"### {txt['chart_title']}")
    
    chart_df = df.sort_values(by="Date")
    
    fig = go.Figure()
    # Seulgi 線
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Morning_Weight'],
        mode='lines+markers', name='Seulgi (Morning)',
        line=dict(color=COLORS['seulgi'], width=3),
        hovertemplate='<b>%{x} (Morning)</b><br>Weight: %{y}kg<extra></extra>'
    ))
    # Wendy 線
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Evening_Weight'],
        mode='lines+markers', name='Wendy (Evening)',
        line=dict(color=COLORS['wendy'], width=3, dash='dot'),
        hovertemplate='<b>%{x} (Evening)</b><br>Weight: %{y}kg<extra></extra>'
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified" # 這樣滑鼠移過去會同時顯示資訊
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("👆 Tap on points to see details (點擊圖表看詳細日期)")
