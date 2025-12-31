import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from openai import OpenAI
import os

# --- 1. 核心設定 ---
st.set_page_config(page_title="RV Fit", page_icon="🍰", layout="centered")

# Session State
if 'flip_weight' not in st.session_state: st.session_state.flip_weight = 'morning'
if 'flip_workout' not in st.session_state: st.session_state.flip_workout = 'input'
if 'language' not in st.session_state: st.session_state.language = 'English'
if 'ai_msg' not in st.session_state: st.session_state.ai_msg = None
if 'trigger_ai' not in st.session_state: st.session_state.trigger_ai = False

# --- 2. 嚴格色票 ---
PALETTE = {
    "BG": "#E7E0D8",       # 燕麥米 (背景)
    "SEULGI": "#E27921",   # 髒橘
    "WENDY": "#C6D1D9",    # 冷灰藍 (按鈕/邊框)
    "WENDY_TXT": "#78909C",# Wendy 文字深色版 (為了可讀性)
    "CORAL": "#F67869",    # 珊瑚粉
    "TEXT": "#555555"      # 一般文字
}

# 主題色判斷
current_theme = PALETTE['SEULGI'] if st.session_state.flip_weight == 'morning' else PALETTE['WENDY_TXT']

# 語言包
LANG = {
    '繁體中文': {
        'mor': 'Seulgi Morning', 'eve': 'Wendy Evening',
        'work': 'Work Log', 'hist': 'History',
        'remind_s': "Seulgi's Remind", 'remind_w': "Wendy's Remind",
        'trend': 'Body Trend'
    },
    'English': {
        'mor': 'Seulgi Morning', 'eve': 'Wendy Evening',
        'work': 'Work Log', 'hist': 'History',
        'remind_s': "Seulgi's Remind", 'remind_w': "Wendy's Remind",
        'trend': 'Body Trend'
    },
    'Deutsch': {
        'mor': 'Seulgi Morgen', 'eve': 'Wendy Abend',
        'work': 'Training', 'hist': 'Verlauf',
        'remind_s': "Seulgi's Notiz", 'remind_w': "Wendy's Notiz",
        'trend': 'Körpertrend'
    }
}
txt = LANG[st.session_state.language]

# --- 3. CSS 極簡重構 (無卡牌、大字體、置中) ---
st.markdown(f"""
    <style>
    /* 字體引入 */
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/chenyuluoyan-thin@1.0.0/ChenYuluoyan-Thin.css');

    /* 全局背景 */
    .stApp {{ background-color: {PALETTE['BG']}; }}
    
    /* 隱藏預設元件 */
    header, .stDeployButton, footer {{ display: none !important; }}

    /* 通用字體設定 */
    body, div, button, input, textarea {{
        font-family: 'Cinzel', 'ChenYuluoyan-Thin', serif !important;
    }}

    /* === 按鈕 (Button) === */
    /* 讓按鈕看起來跟 Heading 一樣大 (28px) 且置中 */
    div.stButton > button:first-child {{
        border: none;
        background: transparent;
        color: {current_theme};
        font-size: 28px !important; /* 與 Remind 標題一致 */
        font-weight: 700;
        padding: 0;
        margin: 0 auto; /* 絕對置中 */
        display: block;
        width: 100%;
        text-align: center;
        box-shadow: none;
    }}
    div.stButton > button:hover {{
        color: {PALETTE['CORAL']};
        background: transparent;
    }}
    div.stButton > button:focus {{
        color: {PALETTE['CORAL']};
        box-shadow: none;
        background: transparent;
    }}

    /* === 標題文字 (Heading Text) === */
    /* 用於 AI Remind 和 Trend 的標題 */
    .heading-text {{ 
        font-size: 28px; 
        font-weight: 700; 
        text-align: center; 
        margin-bottom: 10px;
        display: block;
        width: 100%;
    }}

    /* === 輸入框 (Input) === */
    /* 巨大的數字輸入，完全透明背景 */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid transparent !important; /* 極致隱藏 */
    }}
    input {{
        text-align: center;
        font-size: 48px !important; /* 數字再大一點，成為視覺重心 */
        font-weight: 400;
        color: #444 !important;
        background-color: transparent !important;
        padding: 10px 0 !important;
    }}
    /* 移除數字箭頭 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {{ -webkit-appearance: none; margin: 0; }}

    /* Text Area (Work Log) */
    textarea {{
        background-color: transparent !important;
        border: none !important;
        font-size: 20px !important;
        color: #666 !important;
        text-align: center;
    }}

    /* 日期選擇器 */
    div[data-testid="stDateInput"] {{
        margin: 0 auto;
        width: 200px;
    }}
    div[data-testid="stDateInput"] input {{
        text-align: center;
        font-size: 18px !important;
        color: #888 !important;
    }}

    /* 語言選單 (隱藏於右上) */
    div[data-testid="stSelectbox"] div {{
        border: none;
        background: transparent;
        color: {PALETTE['BG']}; /* 幾乎隱形，滑鼠過去才看得到，或者保持淺灰 */
        font-size: 14px;
    }}
    /* 調整間距，讓 Blocks 之間有呼吸感 */
    .block-spacer {{
        margin-bottom: 40px;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 4. 資料庫 ---
DATA_FILE = 'rv_log.csv'

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["Date", "Morning_Weight", "Evening_Weight", "Exercise", "AI_Comment"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

df = load_data()

def auto_save():
    d = str(st.session_state.input_date)
    m = st.session_state.get('val_morning', 0.0)
    e = st.session_state.get('val_evening', 0.0)
    ex = st.session_state.get('val_exercise', "")
    global df
    new_entry = {"Date": d, "Morning_Weight": m, "Evening_Weight": e, "Exercise": ex, "AI_Comment": ""}
    df = df[df['Date'] != d]
    df = pd.concat([pd.DataFrame([new_entry]), df], ignore_index=True)
    df = df.sort_values(by="Date")
    save_data(df)
    st.session_state.trigger_ai = True

# --- 5. 介面佈局 ---

# [Header] Language
c_dummy, c_lang = st.columns([8, 2])
with c_lang:
    st.selectbox("Lang", ['English', '繁體中文', 'Deutsch'], key='language', label_visibility="collapsed")

# [Date] Date Input
st.markdown("<br>", unsafe_allow_html=True)
input_date = st.date_input("Date", datetime.now(), key="input_date", on_change=auto_save, label_visibility="collapsed")

# Load Current Data
current_data = df[df['Date'] == str(input_date)]
d_mor = float(current_data.iloc[0]['Morning_Weight']) if not current_data.empty else 0.0
d_eve = float(current_data.iloc[0]['Evening_Weight']) if not current_data.empty else 0.0
d_ex = str(current_data.iloc[0]['Exercise']) if not current_data.empty and pd.notna(current_data.iloc[0]['Exercise']) else ""

# === Block 1: Weight ===
st.markdown("<div class='block-spacer'></div>", unsafe_allow_html=True)
with st.container():
    # 標題按鈕化 (28px, Centered)
    if st.session_state.flip_weight == 'morning':
        if st.button(txt['mor'], key="btn_mor"):
            st.session_state.flip_weight = 'evening'
            st.rerun()
        # 輸入框
        st.number_input("M", value=d_mor, step=0.0, format="%.1f", key="val_morning", on_change=auto_save, label_visibility="collapsed")
    else:
        if st.button(txt['eve'], key="btn_eve"):
            st.session_state.flip_weight = 'morning'
            st.rerun()
        st.number_input("E", value=d_eve, step=0.0, format="%.1f", key="val_evening", on_change=auto_save, label_visibility="collapsed")

# === Block 2: Work Log ===
st.markdown("<div class='block-spacer'></div>", unsafe_allow_html=True)
with st.container():
    # 運動標題 (Button)
    if st.session_state.flip_workout == 'input':
        if st.button(txt['work'], key="btn_wo"):
            st.session_state.flip_workout = 'history'
            st.rerun()
        st.text_area("W", value=d_ex, height=60, key="val_exercise", on_change=auto_save, label_visibility="collapsed")
    else:
        if st.button(txt['hist'], key="btn_hist"):
            st.session_state.flip_workout = 'input'
            st.rerun()
        
        # 歷史列表 (純文字呈現)
        if not df.empty:
            hist = df[df['Exercise'].notna() & (df['Exercise']!="")].tail(3)
            for _, r in hist.iterrows():
                st.markdown(f"<div style='text-align:center; color:#666; font-size:18px; margin-top:5px;'>{r['Date']} | {r['Exercise']}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center; color:#ccc;'>-</div>", unsafe_allow_html=True)

# === Block 3: AI Remind ===
st.markdown("<div class='block-spacer'></div>", unsafe_allow_html=True)

# Logic check
has_data = d_mor > 0 or d_eve > 0 or d_ex != ""
should_trigger = st.session_state.trigger_ai or (has_data and st.session_state.ai_msg is None)

if has_data:
    is_seulgi_time = (st.session_state.flip_weight == 'morning')
    ai_title = txt['remind_s'] if is_seulgi_time else txt['remind_w']
    ai_color = PALETTE['SEULGI'] if is_seulgi_time else PALETTE['WENDY_TXT']
    
    # 這裡直接用 HTML 渲染標題，確保跟上面的 Button 大小完全一樣 (28px)
    st.markdown(f"<div class='heading-text' style='color:{ai_color};'>{ai_title}</div>", unsafe_allow_html=True)

    # AI Trigger
    if should_trigger and "OPENAI_API_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        persona = "Seulgi (Warm, Cute)" if is_seulgi_time else "Wendy (Strict, Energetic)"
        prompt = f"""
        User: {d_mor}kg (M), {d_eve}kg (E), Ex: {d_ex}.
        Role: {persona} from Red Velvet.
        Lang: {st.session_state.language}.
        Task: One short sentence feedback. No emojis.
        """
        # 隱形讀取
        try:
            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
            st.session_state.ai_msg = res.choices[0].message.content
            st.session_state.trigger_ai = False
        except:
            pass # 靜默失敗，不破壞介面

    if st.session_state.ai_msg:
        st.markdown(f"<div style='text-align:center; color:#555; font-size:20px; padding:0 20px;'>{st.session_state.ai_msg}</div>", unsafe_allow_html=True)

# === Block 4: Body Trend ===
if not df.empty:
    st.markdown("<div class='block-spacer'></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='heading-text' style='color:{PALETTE['CORAL']};'>{txt['trend']}</div>", unsafe_allow_html=True)
    
    chart_df = df.sort_values(by="Date")
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Morning_Weight'],
        mode='lines', name='M',
        line=dict(color=PALETTE['SEULGI'], width=3),
        connectgaps=True
    ))
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Evening_Weight'],
        mode='lines', name='E',
        line=dict(color=PALETTE['WENDY_TXT'], width=3),
        connectgaps=True
    ))

    fig.update_layout(
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=10, b=10),
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False), # 極簡，甚至隱藏X軸標籤，只看線條
        yaxis=dict(
            showgrid=True, 
            gridcolor='#dcdcdc', # 淡淡的格線
            zeroline=False,
            tickfont=dict(family='Cinzel', size=14, color='#888')
        )
    )
    st.plotly_chart(fig, use_container_width=True)
