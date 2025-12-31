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
if 'language' not in st.session_state: st.session_state.language = '繁體中文'
if 'ai_msg' not in st.session_state: st.session_state.ai_msg = None
if 'trigger_ai' not in st.session_state: st.session_state.trigger_ai = False # 新增：控制是否自動觸發 AI

# 配色定義
COLORS = {
    "bg": "#FFF0F2",
    "card_bg": "#FFFFFF",
    "seulgi": "#ff9f43", 
    "wendy": "#273c75",  
    "text": "#555555"
}

current_color = COLORS['seulgi'] if st.session_state.flip_weight == 'morning' else COLORS['wendy']

# --- 2. CSS 美化 ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLORS['bg']}; }}
    header {{visibility: hidden;}}
    .stDeployButton {{display:none;}}
    
    /* 卡片樣式 */
    .css-card {{
        background-color: white;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-top: 5px solid {current_color};
        text-align: center;
    }}
    
    /* 標題按鈕化 */
    div[data-testid="stButton"] button {{
        width: 100%;
        border: none;
        background-color: transparent;
        color: {current_color};
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 24px;
        font-weight: 800;
        padding: 10px 0;
        transition: 0.3s;
    }}
    div[data-testid="stButton"] button:hover {{
        background-color: #f8f9fa;
        color: {current_color};
    }}

    /* 隱形輸入框 */
    div[data-baseweb="input"] {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid #eee !important;
    }}
    input {{
        text-align: center;
        font-size: 28px !important;
        font-weight: bold;
        color: #333 !important;
        background-color: transparent !important;
    }}
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {{ -webkit-appearance: none; margin: 0; }}

    /* 置中優化 */
    div[data-testid="stDateInput"] {{ text-align: center; margin: 0 auto; }}
    div[data-testid="stDateInput"] input {{ text-align: center; }}
    div[data-testid="stSelectbox"] {{ border: none; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. 資料處理 ---
DATA_FILE = 'rv_log.csv'

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["Date", "Morning_Weight", "Evening_Weight", "Exercise", "AI_Comment"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

df = load_data()

# 自動儲存 + 觸發 AI
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
    
    # 關鍵改動：資料一變動，就打開 AI 觸發開關
    st.session_state.trigger_ai = True
    st.toast("✅ Saved")

# --- 4. 介面佈局 ---

col_top1, col_top2 = st.columns([8, 2])
with col_top2:
    st.selectbox("Language", ['繁體中文', 'English', 'Deutsch'], label_visibility="collapsed", key='language')

st.markdown("<br>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    input_date = st.date_input("Date", datetime.now(), label_visibility="collapsed", key="input_date", on_change=auto_save)

# 載入數據
current_data = df[df['Date'] == str(input_date)]
d_mor = float(current_data.iloc[0]['Morning_Weight']) if not current_data.empty else 0.0
d_eve = float(current_data.iloc[0]['Evening_Weight']) if not current_data.empty else 0.0
d_ex = str(current_data.iloc[0]['Exercise']) if not current_data.empty and pd.notna(current_data.iloc[0]['Exercise']) else ""

# [Block 2] 體重卡片
with st.container():
    st.markdown(f'<div class="css-card">', unsafe_allow_html=True)
    if st.session_state.flip_weight == 'morning':
        if st.button("☀️ Seulgi Morning (點擊切換)", key="btn_mor"):
            st.session_state.flip_weight = 'evening'
            st.rerun()
        st.number_input("Input", value=d_mor, step=0.0, format="%.1f", key="val_morning", on_change=auto_save, label_visibility="collapsed")
        st.caption("輸入早晨空腹體重 (kg)")
    else:
        if st.button("🌙 Wendy Evening (點擊切換)", key="btn_eve"):
            st.session_state.flip_weight = 'morning'
            st.rerun()
        st.number_input("Input", value=d_eve, step=0.0, format="%.1f", key="val_evening", on_change=auto_save, label_visibility="collapsed")
        st.caption("輸入晚間睡前體重 (kg)")
    st.markdown('</div>', unsafe_allow_html=True)

# [Block 3] 運動卡片
with st.container():
    wo_color = "#6c5ce7"
    st.markdown(f'<div class="css-card" style="border-top: 5px solid {wo_color};">', unsafe_allow_html=True)
    if st.session_state.flip_workout == 'input':
        if st.button("🏃‍♀️ Workout Log (點擊看歷史)", key="btn_wo_inp"):
             st.session_state.flip_workout = 'history'
             st.rerun()
        st.text_area("Input", value=d_ex, height=80, key="val_exercise", on_change=auto_save, label_visibility="collapsed", placeholder="今天做了什麼運動？")
    else:
        if st.button("📜 Past Records (點擊輸入)", key="btn_wo_hist"):
             st.session_state.flip_workout = 'input'
             st.rerun()
        if not df.empty:
            hist = df[df['Exercise'].notna() & (df['Exercise']!="")].tail(3)
            for _, r in hist.iterrows():
                st.markdown(f"<div style='text-align:left; font-size:14px; color:#666; border-bottom:1px solid #eee; padding:5px;'><b>{r['Date']}</b>: {r['Exercise']}</div>", unsafe_allow_html=True)
        else:
            st.caption("暫無紀錄")
    st.markdown('</div>', unsafe_allow_html=True)

# [Block 4] AI 自動建議 (Auto-Proactive Block)
# 邏輯：有資料 且 (剛修改過資料 或 尚未有建議) -> 自動執行
has_data = d_mor > 0 or d_eve > 0 or d_ex != ""
should_trigger = st.session_state.trigger_ai or (has_data and st.session_state.ai_msg is None)

if has_data:
    with st.container():
        # 這裡設定一個獨特的顏色，代表 AI 的存在感
        ai_color = "#00b894" 
        st.markdown(f'<div class="css-card" style="border-top: 5px solid {ai_color};">', unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:{ai_color}; margin:0;'>💬 94 Line Feedback</h3>", unsafe_allow_html=True)
        
        # 顯示區域
        msg_placeholder = st.empty()

        # 如果需要觸發 AI
        if should_trigger and "OPENAI_API_KEY" in st.secrets:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            prompt = f"""
            User Data: Morning {d_mor}kg, Evening {d_eve}kg, Workout: {d_ex}.
            Roleplay: Red Velvet Seulgi (Warm/Cute) & Wendy (Strict/High Tension).
            Language: {st.session_state.language}.
            Give a SHORT, lively comment.
            """
            
            # 顯示「對方正在輸入...」的感覺
            with st.spinner("Seulgi & Wendy are typing..."):
                try:
                    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                    st.session_state.ai_msg = res.choices[0].message.content
                    # 執行完後，關閉觸發開關，避免無限迴圈
                    st.session_state.trigger_ai = False
                except Exception as e:
                    st.error("AI 休息中 (Connection Error)")
        
        # 顯示訊息
        if st.session_state.ai_msg:
            st.markdown(f"<div style='text-align:left; padding-top:10px; font-weight:500; color:#444;'>{st.session_state.ai_msg}</div>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# [Block 5] Body Trend
if not df.empty:
    st.markdown(f'<div class="css-card" style="border-top: 5px solid #e17055;">', unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:#e17055; margin:0;'>📈 Body Trends</h3>", unsafe_allow_html=True)
    chart_df = df.sort_values(by="Date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Morning_Weight'],
        mode='lines+markers', name='Seulgi (早)',
        line=dict(color=COLORS['seulgi'], width=3),
        hovertemplate='<b>%{x|%m-%d} Morning</b><br>Weight: %{y}kg<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Evening_Weight'],
        mode='lines+markers', name='Wendy (晚)',
        line=dict(color=COLORS['wendy'], width=3, dash='dot'),
        hovertemplate='<b>%{x|%m-%d} Evening</b><br>Weight: %{y}kg<extra></extra>'
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,0)',
        margin=dict(l=0, r=0, t=20, b=0), legend=dict(orientation="h", y=-0.2),
        hovermode="x unified", xaxis=dict(tickformat="%m-%d", showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#eee')
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
