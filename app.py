import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from openai import OpenAI
import os

# --- 1. 核心設定 ---
st.set_page_config(
    page_title="RV 94 Line Fit", 
    page_icon="🍰", 
    layout="centered"
)

# --- 2. 94 Line 動態配色邏輯 ---
current_hour = datetime.now().hour
is_night = current_hour >= 17 or current_hour < 5

# 定義顏色
RV_CORAL = "#F6B6B7"
SEULGI_ORANGE = "#ff9f43"
WENDY_BLUE = "#273c75"

if is_night:
    current_theme = WENDY_BLUE
    greeting = "Good Evening, ReVeluv! 💙"
else:
    current_theme = SEULGI_ORANGE
    greeting = "Good Morning, ReVeluv! 💛"

# --- 3. CSS 美化 ---
st.markdown(f"""
    <style>
    /* 背景色 */
    .stApp {{ background-color: #FFF0F2; }}
    
    /* 標題變色 */
    h1 {{ color: {current_theme} !important; text-align: center; }}
    h3 {{ color: {current_theme} !important; }}

    /* 表格優化 (讓歷史紀錄清楚好讀) */
    .dataframe {{ font-size: 16px !important; }}
    
    /* 按鈕樣式 */
    .stButton>button {{
        background-color: {current_theme};
        color: white;
        border-radius: 20px;
        border: none;
        height: 50px;
        width: 100%;
        font-weight: bold;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 4. 資料庫處理 ---
DATA_FILE = 'rv_log.csv'

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["Date", "Morning_Weight", "Evening_Weight", "Exercise", "AI_Comment"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

df = load_data()

# --- 5. App 主畫面 ---
st.title(greeting)

# [A區] 輸入資料
with st.container():
    st.markdown("### 📝 紀錄區")
    
    # 日期選擇 (預設今天)
    col_date, col_none = st.columns([2, 1])
    with col_date:
        input_date = st.date_input("選擇日期", datetime.now())
    
    # 讀取該日期是否已有資料 (為了顯示預設值)
    current_data = df[df['Date'] == str(input_date)]
    default_mor = 0.0
    default_eve = 0.0
    default_ex = ""
    
    if not current_data.empty:
        default_mor = float(current_data.iloc[0]['Morning_Weight'])
        default_eve = float(current_data.iloc[0]['Evening_Weight'])
        default_ex = str(current_data.iloc[0]['Exercise'])
        if pd.isna(default_ex): default_ex = ""

    # 輸入區塊
    tab1, tab2 = st.tabs(["☀️ Seulgi (早)", "🌙 Wendy (晚)"])
    with tab1:
        w_morning = st.number_input("早晨體重 (kg)", value=default_mor, step=0.1, format="%.1f")
    with tab2:
        w_evening = st.number_input("晚間體重 (kg)", value=default_eve, step=0.1, format="%.1f")
        exercise_log = st.text_area("運動紀錄", value=default_ex, height=100)

    if st.button("💾 儲存紀錄"):
        new_entry = {
            "Date": str(input_date),
            "Morning_Weight": w_morning,
            "Evening_Weight": w_evening,
            "Exercise": exercise_log,
            "AI_Comment": ""
        }
        # 刪除舊的，存入新的
        df = df[df['Date'] != str(input_date)]
        df = pd.concat([pd.DataFrame([new_entry]), df], ignore_index=True)
        df = df.sort_values(by="Date")
        save_data(df)
        st.success("已更新！")
        # 強制重新整理以顯示最新數據
        st.rerun()

# [B區] 歷史紀錄列表 (這就是你要的功能！)
if not df.empty:
    st.divider()
    st.markdown("### 📅 歷史數據一覽 (History Log)")
    
    # 整理表格顯示格式
    display_df = df.copy()
    display_df['Date'] = pd.to_datetime(display_df['Date'])
    display_df = display_df.sort_values(by='Date', ascending=False) # 最新的日期在最上面
    
    # 增加星期幾欄位
    display_df['Weekday'] = display_df['Date'].dt.strftime('%a') # Mon, Tue...
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d') # 轉回字串好顯示

    # 重命名欄位讓它變漂亮
    display_df = display_df[['Date', 'Weekday', 'Morning_Weight', 'Evening_Weight', 'Exercise']]
    display_df.columns = ['日期', '星期', '早晨(Seulgi)', '晚間(Wendy)', '運動']

    # 顯示表格
    st.dataframe(
        display_df, 
        use_container_width=True,
        hide_index=True,  # 隱藏醜醜的 index 0,1,2
        column_config={
            "日期": st.column_config.TextColumn("📅 日期", width="medium"),
            "早晨(Seulgi)": st.column_config.NumberColumn("☀️ 早", format="%.1f kg"),
            "晚間(Wendy)": st.column_config.NumberColumn("🌙 晚", format="%.1f kg"),
        }
    )

# [C區] 趨勢圖表
if not df.empty:
    st.divider()
    st.markdown("### 📈 變化趨勢")
    chart_df = df.tail(14)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['Morning_Weight'], mode='lines+markers', name='早晨', line=dict(color=SEULGI_ORANGE)))
    fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['Evening_Weight'], mode='lines+markers', name='晚間', line=dict(color=WENDY_BLUE, dash='dot')))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0), legend=dict(orientation="h", y=1.2))
    st.plotly_chart(fig, use_container_width=True)

# [D區] AI 分析
st.divider()
if st.button("💬 召喚 94 Line"):
    if df.empty:
        st.error("請先輸入資料")
    elif "OPENAI_API_KEY" not in st.secrets:
        st.warning("⚠️ 請設定 API Key")
    else:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        latest = df.iloc[-1]
        speaker = "Wendy" if is_night else "Seulgi"
        
        prompt = f"""
        扮演 Red Velvet 的 Seulgi 和 Wendy。主講人: {speaker}。
        數據: 日期{latest['Date']}, 早{latest['Morning_Weight']}, 晚{latest['Evening_Weight']}, 運動{latest['Exercise']}。
        給1-100評分，並進行簡短對話建議。
        Seulgi: 呆萌暖心(#ff9f43)。Wendy: 嚴格High Tension(#273c75)。
        """
        try:
            with st.spinner("連線中..."):
                res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                st.markdown(f"<div style='background:white;padding:15px;border-radius:10px;border-left:5px solid {current_theme}'>{res.choices[0].message.content}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(str(e))
