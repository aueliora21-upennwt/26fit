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

# 配色定義
COLORS = {
    "bg": "#FFF0F2",
    "card_bg": "#FFFFFF",
    "seulgi": "#ff9f43", # Orange
    "wendy": "#273c75",  # Blue
    "text": "#555555"
}

# 根據目前翻面狀態決定主色
current_color = COLORS['seulgi'] if st.session_state.flip_weight == 'morning' else COLORS['wendy']

# --- 2. CSS 魔法 (視覺整形手術) ---
st.markdown(f"""
    <style>
    /* 全局背景 */
    .stApp {{ background-color: {COLORS['bg']}; }}
    
    /* 隱藏預設 Header/Footer */
    header {{visibility: hidden;}}
    .stDeployButton {{display:none;}}
    
    /* === 核心卡片樣式 === */
    .css-card {{
        background-color: white;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-top: 5px solid {current_color};
        text-align: center;
    }}
    
    /* 讓按鈕看起來像標題 (Clickable Header) */
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
        background-color: #f8f9fa; /* 輕微反灰提示可點擊 */
        color: {current_color};
    }}
    div[data-testid="stButton"] button:focus {{
        box-shadow: none;
        color: {current_color};
    }}

    /* 輸入框完全隱形化 (融入卡片) */
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
    /* 移除數字加減按鈕 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {{ -webkit-appearance: none; margin: 0; }}

    /* 日期選擇器置中優化 */
    div[data-testid="stDateInput"] {{
        text-align: center;
        margin: 0 auto;
    }}
    div[data-testid="stDateInput"] input {{
        text-align: center;
    }}
    
    /* 語言選單隱藏 */
    div[data-testid="stSelectbox"] {{
        border: none;
    }}
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

# 自動儲存
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
    st.toast("✅ 自動儲存完成 (Saved)")

# --- 4. 介面佈局 ---

# [Top] 語言選擇 (右上角小小的)
col_top1, col_top2 = st.columns([8, 2])
with col_top2:
    st.selectbox("Language", ['繁體中文', 'English', 'Deutsch'], label_visibility="collapsed", key='language')

# [Block 1] 日期選擇 (絕對置中)
st.markdown("<br>", unsafe_allow_html=True) # 一點間距
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    # 這裡放日期，CSS 會讓它置中
    input_date = st.date_input("Date", datetime.now(), label_visibility="collapsed", key="input_date", on_change=auto_save)

# 抓取今日資料
current_data = df[df['Date'] == str(input_date)]
d_mor = float(current_data.iloc[0]['Morning_Weight']) if not current_data.empty else 0.0
d_eve = float(current_data.iloc[0]['Evening_Weight']) if not current_data.empty else 0.0
d_ex = str(current_data.iloc[0]['Exercise']) if not current_data.empty and pd.notna(current_data.iloc[0]['Exercise']) else ""

# [Block 2] 體重卡片 (Weight Card)
# 這裡用 container 來模擬一張卡片
with st.container():
    st.markdown(f'<div class="css-card">', unsafe_allow_html=True)
    
    if st.session_state.flip_weight == 'morning':
        # 標題就是按鈕
        if st.button("☀️ Seulgi Morning (點擊切換)", key="btn_mor"):
            st.session_state.flip_weight = 'evening'
            st.rerun()
        
        # 輸入框 (在卡片內)
        st.number_input("Input", value=d_mor, step=0.0, format="%.1f", key="val_morning", on_change=auto_save, label_visibility="collapsed")
        st.caption("輸入早晨空腹體重 (kg)")

    else:
        # 標題就是按鈕
        if st.button("🌙 Wendy Evening (點擊切換)", key="btn_eve"):
            st.session_state.flip_weight = 'morning'
            st.rerun()
            
        # 輸入框 (在卡片內)
        st.number_input("Input", value=d_eve, step=0.0, format="%.1f", key="val_evening", on_change=auto_save, label_visibility="collapsed")
        st.caption("輸入晚間睡前體重 (kg)")
        
    st.markdown('</div>', unsafe_allow_html=True)

# [Block 3] 運動卡片 (Workout Card)
with st.container():
    # 運動卡片邊框顏色固定為紫色或跟隨主題
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
             
        # 顯示歷史運動 (卡片背面)
        if not df.empty:
            hist = df[df['Exercise'].notna() & (df['Exercise']!="")].tail(3)
            for _, r in hist.iterrows():
                st.markdown(f"<div style='text-align:left; font-size:14px; color:#666; border-bottom:1px solid #eee; padding:5px;'><b>{r['Date']}</b>: {r['Exercise']}</div>", unsafe_allow_html=True)
        else:
            st.caption("暫無紀錄")

    st.markdown('</div>', unsafe_allow_html=True)

# [Block 4] AI 建議 (AI Block)
# 只有當有資料時才顯示
if d_mor > 0 or d_eve > 0 or d_ex != "":
    with st.container():
        st.markdown(f'<div class="css-card" style="border-top: 5px solid #00b894;">', unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#00b894; margin:0;'>💬 94 Line Coach</h3>", unsafe_allow_html=True)
        
        if st.session_state.ai_msg:
             st.markdown(f"<div style='text-align:left; padding-top:10px;'>{st.session_state.ai_msg}</div>", unsafe_allow_html=True)
             if st.button("🔄 Refresh Advice"):
                 st.session_state.ai_msg = None # Clear and rerun
                 st.rerun()
        else:
            st.caption("根據今日數據生成建議...")
            if st.button("✨ 取得建議 (Get Advice)"):
                if "OPENAI_API_KEY" in st.secrets:
                    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt = f"""
                    User Data: Morning {d_mor}kg, Evening {d_eve}kg, Workout: {d_ex}.
                    Roleplay: Red Velvet Seulgi (Warm/Cute) & Wendy (Strict/High Tension).
                    Language: {st.session_state.language}.
                    Provide a short, engaging feedback.
                    """
                    with st.spinner("Calling Seulgi & Wendy..."):
                        try:
                            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                            st.session_state.ai_msg = res.choices[0].message.content
                            st.rerun()
                        except:
                            st.error("Connection Error")
                else:
                    st.warning("No API Key")
        
        st.markdown('</div>', unsafe_allow_html=True)

# [Block 5] Body Trend (圖表二合一)
if not df.empty:
    st.markdown(f'<div class="css-card" style="border-top: 5px solid #e17055;">', unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:#e17055; margin:0;'>📈 Body Trends</h3>", unsafe_allow_html=True)
    
    chart_df = df.sort_values(by="Date")
    fig = go.Figure()
    
    # Seulgi Line
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Morning_Weight'],
        mode='lines+markers', name='Seulgi (早)',
        line=dict(color=COLORS['seulgi'], width=3),
        hovertemplate='<b>%{x|%m-%d} Morning</b><br>Weight: %{y}kg<extra></extra>' # 關鍵：自定義顯示格式
    ))
    
    # Wendy Line
    fig.add_trace(go.Scatter(
        x=chart_df['Date'], y=chart_df['Evening_Weight'],
        mode='lines+markers', name='Wendy (晚)',
        line=dict(color=COLORS['wendy'], width=3, dash='dot'),
        hovertemplate='<b>%{x|%m-%d} Evening</b><br>Weight: %{y}kg<extra></extra>'
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0)',
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", y=-0.2), # Legend 移到下面比較乾淨
        hovermode="x unified",
        xaxis=dict(
            tickformat="%m-%d", # X軸只顯示 月-日
            showgrid=False
        ),
        yaxis=dict(showgrid=True, gridcolor='#eee')
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
