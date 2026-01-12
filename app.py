# @title ⚡ Finding Tesla's Pulse (Final Perfected)
# Quiet install
!pip install -q gradio supabase vaderSentiment pandas plotly

import gradio as gr
from supabase import create_client, Client
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURATION ---
SUPABASE_URL = "https://bsyxnawhabaulqvvsfdd.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_v-PyxoRQ36mNeT0yiNMuMg_YfZ9J-P2".strip()
TABLE_NAME = "comments"
TEXT_COLUMN = "comment_text"
TIMESTAMP_COLUMN = "published_at"

# --- 2. DATA ENGINE ---
print("--- 🔄 INITIALIZING DASHBOARD ---")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    analyzer = SentimentIntensityAnalyzer()
    
    # Fetch Data
    response = supabase.table(TABLE_NAME).select("*").execute()
    
    if not response.data:
        print("⚠️ Database empty. Using dummy structure for UI safety.")
        global_df = pd.DataFrame(columns=[TEXT_COLUMN, TIMESTAMP_COLUMN, 'score', 'Month_Year'])
    else:
        global_df = pd.DataFrame(response.data)
        
        # Robust Date Parsing
        global_df[TIMESTAMP_COLUMN] = pd.to_datetime(global_df[TIMESTAMP_COLUMN], errors='coerce', utc=True)
        global_df = global_df.dropna(subset=[TIMESTAMP_COLUMN])
        
        # Scoring
        global_df['score'] = global_df[TEXT_COLUMN].apply(lambda x: analyzer.polarity_scores(str(x))['compound'])
        global_df['Month_Year'] = global_df[TIMESTAMP_COLUMN].dt.strftime('%B %Y')
        
        print(f"✅ Loaded {len(global_df)} comments.")

except Exception as e:
    print(f"❌ Error: {e}")
    global_df = pd.DataFrame()

# --- 3. HELPER FUNCTIONS ---
def get_month_options():
    if global_df.empty: return ["No Data"]
    unique_months = sorted(global_df['Month_Year'].unique(), key=lambda x: datetime.strptime(x, "%B %Y"), reverse=True)
    return ["All Time"] + unique_months

def get_top_5_months():
    if global_df.empty: return "<div style='color:#ccc;'>No Data</div>"
    try:
        monthly = global_df.groupby('Month_Year')['score'].mean().sort_values(ascending=False).head(5)
        html = "<ul class='insight-list'>"
        for month, score in monthly.items():
            color = "#17FF6C" if score > 0.05 else "#E82127" if score < -0.05 else "#ffffff"
            html += f"<li class='insight-item'><span style='color:#ccc;'>{month}</span> <b style='color:{color}; float:right;'>{score:.2f}</b></li>"
        html += "</ul>"
        return html
    except: return "Calculation Error"

top_5_cache = get_top_5_months()

# --- 4. CORE LOGIC ---
def update_dashboard(selected_month):
    if global_df.empty: 
        return "No Data", "No Data", None, "No Data", "No Data"

    # Filter
    if selected_month == "All Time":
        df = global_df.copy()
    else:
        df = global_df[global_df['Month_Year'] == selected_month].copy()
    
    if df.empty: return "No Data", "No Data", None, "No Data", "No Data"

    # --- A. KPI CARDS ---
    avg = df['score'].mean()
    count = len(df)
    color = "#17FF6C" if avg > 0.05 else "#E82127" if avg < -0.05 else "#dddddd"
    
    kpi_html = f"""
    <div style="display:flex; gap:15px; justify-content:center; align-items:stretch;">
        <div class="kpi-card" style="flex:1;">
            <div class="kpi-value">{count}</div>
            <div class="kpi-label">Total Comments</div>
        </div>
        <div class="kpi-card" style="flex:1;">
            <div class="kpi-value" style="color:{color}">{avg:.2f}</div>
            <div class="kpi-label">Net Sentiment</div>
        </div>
        <div class="kpi-card" style="flex:1.2; text-align:left; padding: 15px 20px;">
            <div class="kpi-label" style="margin-top:0; margin-bottom:10px; color:#E82127; font-weight:bold;">🏆 Top 5 Performing Months</div>
            {top_5_cache}
        </div>
    </div>"""

    # --- B. THE PLOT ---
    df_sorted = df.sort_values(TIMESTAMP_COLUMN)
    daily_df = df_sorted.set_index(TIMESTAMP_COLUMN).resample('D')['score'].mean().reset_index().dropna()
    daily_df['color'] = daily_df['score'].apply(lambda x: '#17FF6C' if x >= 0 else '#E82127')
    daily_df['rolling'] = daily_df['score'].rolling(window=7, min_periods=1).mean()

    fig = go.Figure()
    
    # Bars
    fig.add_trace(go.Bar(
        x=daily_df[TIMESTAMP_COLUMN],
        y=daily_df['score'],
        marker_color=daily_df['color'],
        name='Daily Sentiment',
        opacity=0.9
    ))
    
    # Line
    fig.add_trace(go.Scatter(
        x=daily_df[TIMESTAMP_COLUMN],
        y=daily_df['rolling'],
        mode='lines',
        line=dict(color='#FFEB3B', width=3),
        name='7-Day Trend'
    ))

    # Layout Updates: SOLID BACKGROUND + EXPLICIT LINES
    fig.update_layout(
        template="plotly_dark", # Force Dark Template defaults
        height=500,
        paper_bgcolor='#000000', # Solid Black (No Transparency)
        plot_bgcolor='#000000',  # Solid Black
        font=dict(color='#ffffff', family="Segoe UI"),
        showlegend=False,
        margin=dict(l=60, r=40, t=40, b=80),
        
        # X-AXIS: Explicitly draw the line
        xaxis=dict(
            title="DATE OF COMMENT",
            showgrid=False,
            showline=True,        # Draw the axis line
            linewidth=2,          # Make it visible
            linecolor='white',    # Make it white
            mirror=True,          # Draw it on top too
            tickformat='%b %Y',
            ticks='outside',
            tickfont=dict(size=12, color='white'),
            title_font=dict(size=14, color='white')
        ),
        
        # Y-AXIS: Explicitly draw the line
        yaxis=dict(
            title="SENTIMENT SCORE",
            showgrid=True,
            gridcolor='#333',
            showline=True,        # Draw the axis line
            linewidth=2,
            linecolor='white',
            range=[-1.1, 1.1],
            tickfont=dict(size=12, color='white'),
            title_font=dict(size=14, color='white')
        )
    )

    # --- C. DRILL DOWN LISTS ---
    df_reviews = df.sort_values('score', ascending=False)
    
    def render_list(rows, border_color):
        html = ""
        for _, r in rows.iterrows():
            date_str = r[TIMESTAMP_COLUMN].strftime('%d %b %Y')
            html += f"""
            <div class='review-card' style='border-left: 5px solid {border_color};'>
                <div class='review-date'>{date_str}</div>
                <div class='review-text'>"{r[TEXT_COLUMN]}"</div>
                <div class='review-score' style='color:{border_color}'>Sentiment Score: {r['score']:.4f}</div>
            </div>"""
        return html

    date_range_str = f"{df[TIMESTAMP_COLUMN].min().strftime('%b %d, %Y')} — {df[TIMESTAMP_COLUMN].max().strftime('%b %d, %Y')}"
    date_badge = f"<div class='date-badge'>📅 Data Range: {date_range_str}</div>"
    
    return date_badge, kpi_html, fig, render_list(df_reviews.head(2), "#17FF6C"), render_list(df_reviews.tail(2), "#E82127")

# --- 5. UI & CSS ---
tesla_css = """
body, .gradio-container { background-color: #000000; color: #ffffff; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
.header-row { display: flex; align-items: center; justify-content: center; gap: 20px; padding: 20px 0; border-bottom: 1px solid #333; margin-bottom: 20px; }
.tesla-logo { height: 50px; width: auto; object-fit: contain; }
.contest-title { font-size: 2.2em; color: #fff; text-transform: uppercase; letter-spacing: 3px; margin: 0; font-weight: 600; line-height: 1; }
h3, h4, .section-header { color: #ffffff !important; opacity: 1 !important; }
.kpi-card { background: #151515; border: 1px solid #333; padding: 15px; text-align: center; border-radius: 6px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; justify-content: center; }
.kpi-value { font-size: 2.2em; font-weight: 700; color: #fff; margin-bottom: 5px; } 
.kpi-label { font-size: 0.85em; color: #ddd; text-transform: uppercase; letter-spacing: 1px; }
.insight-list { list-style: none; padding: 0; margin: 0; font-size: 0.9em; width: 100%; }
.insight-item { padding: 6px 0; border-bottom: 1px solid #333; display: flex; justify-content: space-between; }
.review-card { background: #1a1a1a; padding: 15px; margin-bottom: 15px; border-radius: 4px; }
.review-date { color: #888; font-size: 0.85em; margin-bottom: 5px; font-weight: bold; letter-spacing: 0.5px; }
.review-text { font-size: 1.1em; color: #fff; line-height: 1.5; font-style: italic; }
.review-score { font-size: 0.9em; margin-top: 8px; font-weight: bold; }
.date-badge { background: #222; padding: 8px 20px; border-radius: 20px; border: 1px solid #444; color: #eee; font-size: 1em; display: inline-block; margin-top: 10px; }
.legend-text { color: #ffffff; font-size: 0.95em; }
"""

with gr.Blocks(css=tesla_css, theme=gr.themes.Base()) as demo:
    gr.HTML("""
    <div class="header-row">
        <img src="https://upload.wikimedia.org/wikipedia/commons/e/e8/Tesla_logo.png" class="tesla-logo">
        <h1 class="contest-title">Finding Tesla's Pulse</h1>
    </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            opts = get_month_options()
            ms = gr.Dropdown(choices=opts, value=opts[0], label="TIMEFRAME SELECTOR", interactive=True)
            dr = gr.HTML()
        with gr.Column(scale=3):
            # FIXED: Explicit white color for "CHART KEY:"
            gr.HTML("""
            <div style="background:#222; padding:15px; border-left:4px solid #fff; margin-top:5px;">
                <span class="legend-text">
                <b style="color:#ffffff;">CHART KEY:</b> <b style="color:#17FF6C">Green Bars</b> = Net Positive. <b style="color:#E82127">Red Bars</b> = Net Negative. 
                <b style="color:#FFEB3B">Yellow Line</b> = 7-Day Trend.
                </span>
            </div>
            """)
            
    kpi_section = gr.HTML()
    
    gr.HTML("<h3 class='section-header'>SENTIMENT VELOCITY (DAILY PULSE)</h3>")
    chart = gr.Plot()
    
    gr.HTML("<h3 class='section-header'>POLARITY EXTREMES (READ COMMENTS)</h3>")
    with gr.Row():
        with gr.Column():
            gr.HTML("<h4 class='section-header'>▲ POSITIVE OUTLIERS</h4>")
            pos_col = gr.HTML()
        with gr.Column():
            gr.HTML("<h4 class='section-header'>▼ NEGATIVE OUTLIERS</h4>")
            neg_col = gr.HTML()
        
    ms.change(update_dashboard, ms, [dr, kpi_section, chart, pos_col, neg_col])
    if not global_df.empty:
        demo.load(update_dashboard, ms, [dr, kpi_section, chart, pos_col, neg_col])

demo.launch(debug=True, height=1200)
