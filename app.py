import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from openai import OpenAI
import os

# --- 1. 核心設定 ---
st.set_page_config(page_title="RV Fit", page_icon="🍰", layout="centered")

# 初始化 Session State
if 'flip_weight' not in st.session_state: st.session_state.flip_weight = 'morning'
if 'flip_workout' not in st.session_state: st.session_state.flip_workout = 'input'
if 'language' not in st.session_state: st.session_state.language = 'English' # 預設英文較能呈現 Cinzel 之美
if 'ai_msg' not in st.session_state: st.session_state.ai_msg = None
if 'trigger_ai' not in st.session_state: st.session_state.trigger_ai = False

# --- 2. 嚴格色票與字體定義 ---
PALETTE = {
    "BG": "#E7E0D8",       # 燕麥米
    "CARD": "#F1F1F1",     # 極淺灰
    "SEULGI": "#E27921",   # 髒橘
    "WENDY": "#C6D1D9",    # 冷灰藍 (因太淺，文字會自動加深，邊框用此色)
    "WENDY_TXT": "#78909C",# 為了可讀性，Wendy文字稍微加深一點的同色系
    "CORAL": "#F67869",    # 珊瑚粉 (修正無效色碼)
    "YELLOW": "#FFE497",
    "APRICOT": "#F5CD9D"
}

# 根據狀態決定當前主色
current_theme = PALETTE['SEULGI'] if st.session_state.flip_weight == 'morning' else PALETTE['WENDY_TXT']
border_color = PALETTE['SEULGI'] if st.session_state.flip_weight == 'morning' else PALETTE['WENDY']

# 語言包 (極簡化)
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

# --- 3. CSS 視覺重構 (字體 + 階層 + 顏色) ---
st.markdown(f"""
    <style>
    /* 引入字體：Cinzel (英德) + 辰宇落雁體 (中) */
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/chenyuluoyan-thin@1.0.0/ChenYuluoyan-Thin.css');

    /* 全局設定 */
    .stApp {{ background-color: {PALETTE['BG']}; }}
    header, .stDeployButton, footer {{ display: none !important; }}

    /* 字體管理 */
    body, button, input, textarea, div {{
        font-family: 'Cinzel', 'ChenYuluoyan-Thin', serif !important;
    }}

    /* 階層大小控制 (4px 級距) */
    .title-text {{ font-size: 32px; font-weight: 700; color: {PALETTE['CORAL']}; text-align: center; }}
    .heading-text {{ font-size: 28px; font-weight: 700; text-align: center; }}
    .sub-text {{ font-size: 24px; font-weight: 400; text-align: center; color: #888; }}
    .body-text {{ font-size: 20px; font-weight: 400; }}

    /* 卡片區塊 Block */
    .css-block {{
        background-color: {PALETTE['CARD']};
        border-radius: 12px; /* 稍微圓角就好，不要太圓 */
        padding: 24px 16px;
        margin-bottom: 24px;
        border-left: 6px solid {border_color}; /* 改用左側邊條，更像雜誌排版 */
        box-shadow: none; /* 扁平化 */
    }}

    /* 按鈕 (標題化) - 絕對置中 */
    div[data-testid="stButton"] button {{
        width: 100%;
        border: none;
        background: transparent;
        color: {current_theme};
        font-size: 28px; /* Heading Size */
        font-family: 'Cinzel', 'ChenYuluoyan-Thin', serif !important;
        font-weight: 700;
        padding: 0;
        margin: 0;
        display: flex;
        justify-content: center; /* 內容置中 */
    }}
    div[data-testid="stButton"] {{
        display: flex;
        justify-content: center; /* 容器置中 */
    }}
    div[data-testid="stButton"] button:hover {{
        color: {PALETTE['CORAL']};
        background: transparent;
    }}
    div[data-testid="stButton"] button:focus {{
        box-shadow: none;
        color: {PALETTE['CORAL']};
    }}

    /* 輸入框極簡化 (無框、大字) */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {{
        background-color: transparent !important;
        border: none !important;
    }}
    input {{
        text-align: center;
        font-size: 32px !important; /* Title Size for numbers */
        color: #555 !important;
        font-family: 'Cinzel', serif !important;
    }}
    /* 移除數字加減箭頭 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {{ -webkit-appearance: none; margin: 0; }}

    /* Date Input 置中與美化 */
    div[data-testid="stDateInput"] {{
        margin: 0 auto;
        width: 150px;
    }}
    div[data-testid="stDateInput"] div {{
        border: none;
        background-color: transparent;
        color: #666;
    }}
    input[type="text"] {{
        font-size: 20px !important; /* Body Size */
        text-align: center;
    }}

    /* Text Area (Work Log) */
    textarea {{
        background-color: transparent !important;
        border: none !important;
        font-size: 20px !important; /* Body Size */
        color: #666 !important;
        text-align: center;
        padding: 0 !important;
    }}
    
    /* 隱藏 Label */
    label {{ display: none !important; }}

    /* 語言選單隱藏邊框 */
    div[data-testid="stSelectbox"] div {{
        border: none;
        background: transparent;
        color: #999;
        font-size: 16px;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 4. 資料處理 ---
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

# [Header] 語言選擇 (隱藏於右上)
c_ph, c_lang = st.columns([8, 2])
with c_lang:
    st.selectbox("Lang", ['English', '繁體中文', 'Deutsch'], key='language', label_visibility="collapsed")

# [Date] 日期選擇 (置中)
st.markdown("<br>", unsafe_allow_html=True)
input_date = st.date_input("Date", datetime.now(), key="input_date", on_change=auto_save)

# 讀取數據
current_data = df[df['Date'] == str(input_date)]
d_mor = float(current_data.iloc[0]['Morning_Weight']) if not current_data.empty else 0.0
d_eve = float(current_data.iloc[0]['Evening_Weight']) if not current_data.empty else 0.0
d_ex = str(current_data.iloc[0]['Exercise']) if not current_data.empty and pd.notna(current_data.iloc[0]['Exercise']) else ""

# === Block 1: 體重 (Weight) ===
with st.container():
    st.markdown(f'<div class="css-block">', unsafe_allow_html=True)
    
    # 標題切換按鈕 (Heading Size)
    if st.session_state.flip_weight == 'morning':
        # Seulgi Morning (Emoji 只有這裡有)
        if st.button(f"☀️ {txt['mor']}", key="btn_mor"):
            st.session_state.flip_weight = 'evening'
            st.rerun()
        # 輸入框 (Title Size, No labels)
        st.number_input("M", value=d_mor, step=0.0, format="%.1f", key="val_morning", on_change=auto_save)
    else:
        # Wendy Evening
        if st.button(f"🌙 {txt['eve']}", key="btn_eve"):
            st.session_state.flip_weight = 'morning'
            st.rerun()
        st.number_input("E", value=d_eve, step=0.0, format="%.1f", key="val_evening", on_change=auto_save)

    st.markdown('</div>', unsafe_allow_html=True)

# === Block 2: 運動 (Work Log) ===
with st.container():
    st.markdown(f'<div class="css-block" style="border-color: {PALETTE["APRICOT"]};">', unsafe_allow_html=True)
    
    if st.session_state.flip_workout == 'input':
        if st.button(txt['work'], key="btn_wo_title"):
            st.session_state.flip_workout = 'history'
            st.rerun()
        # Text Area (Body Size)
        st.text_area("W", value=d_ex, height=60, key="val_exercise", on_change=auto_save)
    else:
        if st.button(txt['hist'], key="btn_hist_title"):
            st.session_state.flip_workout = 'input'
            st.rerun()
        # 歷史列表
        if not df.empty:
            hist = df[df['Exercise'].notna() & (df['Exercise']!="")].tail(3)
            for _, r in hist.iterrows():
                st.markdown(f"<div class='body-text' style='text-align:center; color:#666; margin-top:8px;'>{r['Date']} | {r['Exercise']}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='body-text' style='text-align:center;'>-</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# === Block 3: AI Remind (Feedback) ===
# 觸發條件
has_data = d_mor > 0 or d_eve > 0 or d_ex != ""
should_trigger = st.session_state.trigger_ai or (has_data and st.session_state.ai_msg is None)

if has_data:
    # 決定是 Seulgi 還是 Wendy
    is_seulgi_time = (st.session_state.flip_weight == 'morning')
    ai_title = txt['remind_s'] if is_seulgi_time else txt['remind_w']
    ai_color = PALETTE['SEULGI'] if is_seulgi_time else PALETTE['WENDY_TXT']
    
    with st.container():
        st.markdown(f'<div class="css-block" style="border-color: {PALETTE["YELLOW"]};">', unsafe_allow_html=True)
        st.markdown(f"<div class='heading-text' style='color:{ai_color};'>{ai_title}</div>", unsafe_allow_html=True)
        
        # AI Logic
        if should_trigger and "OPENAI_API_KEY" in st.secrets:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            persona = "Seulgi (Warm, Cute, Soft)" if is_seulgi_time else "Wendy (Strict, Energetic, High Tension)"
            prompt = f"""
            User: {d_mor}kg (M), {d_eve}kg (E), Ex: {d_ex}.
            Role: {persona} from Red Velvet.
            Lang: {st.session_state.language}.
            Task: One short sentence feedback. No emojis.
            """
            with st.spinner("..."):
                try:
                    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                    st.session_state.ai_msg = res.choices[0].message.content
                    st.session_state.trigger_ai = False
                except:
                    pass
        
        if st.session_state.ai_msg:
            st.markdown(f"<div class='body-text' style='text-align:center; margin-top:10px; color:#555;'>{st.session_state.ai_msg}</div>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# === Block 4: Trend (Chart) ===
if not df.empty:
    with st.container():
        st.markdown(f'<div class="css-block" style="border-color: {PALETTE["CORAL"]};">', unsafe_allow_html=True)
        st.markdown(f"<div class='heading-text' style='color:{PALETTE['CORAL']};'>{txt['trend']}</div>", unsafe_allow_html=True)
        
        chart_df = df.sort_values(by="Date")
        fig = go.Figure()
        
        # Seulgi Line
        fig.add_trace(go.Scatter(
            x=chart_df['Date'], y=chart_df['Morning_Weight'],
            mode='lines', name='M',
            line=dict(color=PALETTE['SEULGI'], width=2),
            connectgaps=True
        ))
        # Wendy Line
        fig.add_trace(go.Scatter(
            x=chart_df['Date'], y=chart_df['Evening_Weight'],
            mode='lines', name='E',
            line=dict(color=PALETTE['WENDY_TXT'], width=2),
            connectgaps=True
        ))

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=False,
            font=dict(family="Cinzel", size=14, color="#888"),
            xaxis=dict(showgrid=False),
            yaxis=dict(
                showgrid=True, 
                gridcolor='#eee',
                zeroline=False,
                tickmode='auto' # 自動顯示體重數值
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
