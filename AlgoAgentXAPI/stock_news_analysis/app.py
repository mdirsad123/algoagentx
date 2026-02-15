"""
streamlit run stock_news_analysis/app.py
"""

import streamlit as st
import pandas as pd
import os
import sys
import yfinance as yf

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
import time
import subprocess
import threading
import schedule
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import seaborn as sns
import matplotlib.pyplot as plt
from analysis.read_latest_csv import load_latest_data_output_sentiment, load_latest_data_output_chart_ind, read_final_result_to_trade_execute, read_ml_signal_data
from analysis.data_save_csv import save_to_csv_final_result, update_trade_execution_status
from notification.watsapp_alert_Twilio import send_whatsapp_alert_trade_executed
from algo_trading.gtt_order_place import place_gtt_order_by_symbol_percent
from notification.send_alert_main import send_alert_msg
from investing_risk_management.risk_management import get_live_risk_config

# Set page config
st.set_page_config(
    page_title="Stock News Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

def run_screener():
    """Run the daily screener script"""
    try:
        venv_python = r"D:\Stock_market\NSE-Stock-Scanner\.venv\Scripts\python.exe"
        st.sidebar.info("Running analysis... Please wait.")
        subprocess.run([venv_python, "-m", "stock_news_analysis.main"], check=True)
        return True
    except Exception as e:
        st.error(f"Error running screener: {e}")
        return False

def schedule_screener():
    """Schedule the screener to run every 10 minutes"""
    while True:
        schedule.run_pending()
        time.sleep(1)

def create_sentiment_chart(df):
    """Create an interactive sentiment distribution chart"""
    if df is None or df.empty or 'overall_sentiment' not in df.columns:
        return go.Figure()

    sentiment_counts = df['overall_sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['Sentiment', 'Count']
    
    color_map = {
        'Very Positive': '#00ff00',
        'Positive': '#90EE90',
        'Neutral': '#FFD700',
        'Negative': '#FFB6C1',
        'Very Negative': '#FF0000',
        'No Text': '#D3D3D3'
    }
    
    fig = px.bar(
        sentiment_counts,
        x='Sentiment',
        y='Count',
        color='Sentiment',
        color_discrete_map=color_map,
        title="Sentiment Distribution"
    )
    
    fig.update_layout(
        xaxis_title="Sentiment",
        yaxis_title="Count",
        showlegend=False,
        height=400
    )
    return fig

def create_confidence_chart(df):
    """Create a confidence score distribution chart"""
    if df is None or 'confidence' not in df.columns or df['confidence'].isnull().all():
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Box(
        y=df['confidence'],
        name='Confidence Scores',
        boxpoints='all',
        jitter=0.3,
        pointpos=-1.8
    ))
    fig.update_layout(
        title="Confidence Score Distribution",
        yaxis_title="Confidence Score",
        height=400
    )
    return fig

def process_sentiment(df):
    """Use existing sentiment columns instead of recomputing"""
    if df is None or df.empty:
        return None

    df_processed = df.copy()
    
    # Use final_sentiment and confidence columns from existing data
    df_processed['overall_sentiment'] = df_processed.get('final_sentiment', 'No Text')
    df_processed['confidence'] = df_processed.get('confidence', 0)
    df_processed['Time'] = df_processed.get('Time', 0)

    # Optional: If you want to show all sentiment scores together
    df_processed['sentiment_metrics'] = df_processed.apply(lambda row: {
        'vader_score': row.get('vader_score'),
        'textblob_score': row.get('textblob_score'),
        'bert_sentiment': row.get('bert_sentiment'),
        'confidence': row.get('confidence')
    }, axis=1)

    return df_processed

def main():
    st.title("📈 Stock News Analysis Dashboard")
    
    # Sidebar controls
    st.sidebar.header("Controls")
    auto_refresh = st.sidebar.checkbox("Auto-refresh dashboard every 5 minutes", value=True)
    auto_screener = st.sidebar.checkbox("Run screener every 10 minutes", value=False)
    
    # Simple Trading Engine Control
    st.sidebar.header("⚙️ Trading Engine Control")
    trading_engine = st.sidebar.checkbox("Enable Trading Engine", value=False)
    
    if trading_engine:
        st.sidebar.success("🟢 Trading Engine is ON")
    else:
        st.sidebar.warning("🔴 Trading Engine is OFF")

    # 👉 Button to Run Full Analysis Pipeline
    # st.sidebar.markdown("---")
    st.sidebar.markdown("⚡ **Run Full Analysis Pipeline**")

    if st.sidebar.button("🚀 Run Analysis Now"):
        try:
            run_screener()
            st.sidebar.success("✅ Analysis completed!")
        except subprocess.CalledProcessError as e:
            st.sidebar.error(f"❌ Error running analysis: {e}")

    # Session state initialization
    if 'last_data' not in st.session_state:
        st.session_state.last_data = None
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None
    if 'scheduler_running' not in st.session_state:
        st.session_state.scheduler_running = False
    if 'next_run_time' not in st.session_state:
        st.session_state.next_run_time = None
    if 'last_screener_run' not in st.session_state:
        st.session_state.last_screener_run = None

    # Auto-refresh logic with unique key
    if auto_refresh:
        st_autorefresh(interval=5 * 60 * 1000, key="dashboard_refresh")  # 5 minutes

    # Screener scheduling logic
    if auto_screener:
        current_time = datetime.now()
        
        # Initialize next run time if not set
        if st.session_state.next_run_time is None:
            st.session_state.next_run_time = current_time + timedelta(minutes=10)
        
        # Check if it's time to run the screener
        if current_time >= st.session_state.next_run_time:
            try:
                if run_screener():
                    st.session_state.last_screener_run = current_time
                    st.session_state.next_run_time = current_time + timedelta(minutes=10)
                    st.sidebar.success("Screener completed successfully!")
            except Exception as e:
                st.sidebar.error(f"Error running screener: {e}")
        
        # Display countdown timer
        if st.session_state.next_run_time:
            time_left = st.session_state.next_run_time - current_time
            minutes, seconds = divmod(int(time_left.total_seconds()), 60)
            st.sidebar.markdown(f"⏳ **Next screener run in:** {minutes:02d}:{seconds:02d}")
        
        # Display last run time
        if st.session_state.last_screener_run:
            st.sidebar.markdown(f"🕒 **Last run:** {st.session_state.last_screener_run.strftime('%H:%M:%S')}")

    # Load and display data
    df_sentiment_data = load_latest_data_output_sentiment()
    df_chart_ind_data = load_latest_data_output_chart_ind()
    
    # Update last data and timestamp
    if df_sentiment_data is not None:
        st.session_state.last_data = df_sentiment_data
        st.session_state.last_update = datetime.now()

    # Display last update time
    if st.session_state.last_update:
        st.sidebar.markdown(f"📊 **Last data update:** {st.session_state.last_update.strftime('%H:%M:%S')}")

    # View selection
    view = st.sidebar.radio("Select View", ["Smart Trade Signals", "Sentiment", "Chart Patterns", "Technical Indicators", "Risk Management"])

    if view == "Sentiment":
        # show sentiment charts and tables
        total_announcements = len(df_sentiment_data) if df_sentiment_data is not None else 0
        st.subheader(f'Total {total_announcements} Latest Announcements')
        if df_sentiment_data is not None:
            df_processed = process_sentiment(df_sentiment_data)
            st.session_state.last_data = df_processed
            st.session_state.last_update = datetime.now()
            st.dataframe(
                df_processed[['Company', 'Headline', 'Time', 'overall_sentiment', 'confidence']],
                use_container_width=True
            )
        else:
            st.warning("No sentiment data available. Please run the screener first.")

        # sentiment statistics
        if st.session_state.last_data is not None:
            
            sentiment_counts = st.session_state.last_data['overall_sentiment'].value_counts()
            total = len(st.session_state.last_data)
            st.subheader("Sentiment Statistics")
            ordered_sentiments = ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
            # Filter only the sentiments that are present
            filtered_sentiments = [(s, sentiment_counts[s]) for s in ordered_sentiments if s in sentiment_counts]
            # Create columns dynamically
            cols = st.columns(len(filtered_sentiments))
            # Display metrics row-wise
            for col, (sentiment, count) in zip(cols, filtered_sentiments):
                percentage = (count / total) * 100
                col.metric(sentiment, f"{percentage:.1f}%", f"{count} announcements")

        # --- New Section: Sentiment-Based Tables ---

        st.header("📊 Sentiment-Based Stock Breakdown")

        # Define the sentiment categories in desired order
        categories = ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]

        for sentiment in categories:
            df_s = df_sentiment_data[df_sentiment_data['final_sentiment'] == sentiment]
            if not df_s.empty:
                df_s = df_s[['Company', 'Headline', 'Time', 'confidence']].copy()
                df_s = df_s.sort_values('confidence', ascending=False)
                df_s['confidence'] = df_s['confidence'].apply(lambda x: f"{x:.1%}")  # format as percentage

                st.subheader(
                    f"🟢 {sentiment}" if "Positive" in sentiment
                    else f"🔴 {sentiment}" if "Negative" in sentiment
                    else f"⚪ {sentiment}"
                )

                st.dataframe(
                    df_s,
                    use_container_width=True,
                    column_config={
                        "Company": st.column_config.Column(width="small"),
                        "Headline": st.column_config.Column(width="large"),
                        "Time": st.column_config.Column(width="medium"),
                        "confidence": st.column_config.Column(width="small")
                    }
                )
    # ------------------------------------------------------------------------------------------

        # Count of Sentiments Pie Chart
        color_map = {
            'Very Positive': '#00ff00',
            'Positive': '#90EE90',
            'Neutral': '#FFD700',
            'Negative': '#FFB6C1',
            'Very Negative': '#FF0000',
            'No Text': '#D3D3D3'
        }

        # Count sentiments
        sentiment_counts = df_sentiment_data['final_sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['Sentiment', 'Count']

        # Create pie chart with custom color map
        fig_pie = px.pie(
            sentiment_counts,
            values='Count',
            names='Sentiment',
            title='Sentiment Distribution',
            hole=0.4,
            color='Sentiment',
            color_discrete_map=color_map
        )

        # Display in Streamlit
        st.plotly_chart(fig_pie, use_container_width=True)

    # ------------------------------------------------------------------------------------------

        # Bar Chart: Top Companies by Positive News
        positive_df = df_sentiment_data[df_sentiment_data['final_sentiment'].isin(['Very Positive', 'Positive'])]
        top_companies = positive_df['Company'].value_counts().nlargest(10).reset_index()
        top_companies.columns = ['Company', 'Positive News Count']
        fig_bar = px.bar(top_companies, x='Company', y='Positive News Count',
                        title='Top Companies with Most Positive News')
        st.plotly_chart(fig_bar, use_container_width=True)
        
# ---------------------------------------------------------------------------------------------------------
    
    elif view == "Chart Patterns":
        if df_chart_ind_data is None:
            st.warning("No chart pattern data available. Please run the screener first.")
        else:
            # Preprocess data with empty check
            df_chart = df_chart_ind_data[['Company', 'Chart_Pattern']].dropna()
            if df_chart.empty:
                st.info("No chart pattern data available.")
            else:
                df_chart['Chart_Pattern'] = df_chart['Chart_Pattern'].astype(str)
                df_chart = df_chart.assign(Patterns=df_chart['Chart_Pattern'].str.split(', ')).explode('Patterns')
                st.dataframe(df_chart)

                # Pattern frequency analysis
                pattern_counts = df_chart['Patterns'].value_counts().reset_index()
                pattern_counts.columns = ['Chart Pattern', 'Frequency']
                st.bar_chart(pattern_counts.set_index('Chart Pattern'))

                # Pie chart of patterns
                fig = px.pie(pattern_counts, values='Frequency', names='Chart Pattern', title='Chart Pattern Distribution')
                st.plotly_chart(fig)

                # Filter by selected pattern
                selected_pattern = st.selectbox("Select a Chart Pattern", df_chart['Patterns'].unique())
                filtered_df = df_chart[df_chart['Patterns'] == selected_pattern]
                st.write(f"Companies with {selected_pattern} pattern:")
                st.dataframe(filtered_df)

                # Correlation with sentiment
                df_combo = df_chart_ind_data[['Chart_Pattern', 'final_sentiment']].dropna()
                if not df_combo.empty:
                    df_combo['Chart_Pattern'] = df_combo['Chart_Pattern'].astype(str)
                    df_combo = df_combo.assign(Patterns=df_combo['Chart_Pattern'].str.split(', ')).explode('Patterns')
                    pattern_sentiment = df_combo.groupby(['Patterns', 'final_sentiment']).size().unstack(fill_value=0)

                    if not pattern_sentiment.empty and pattern_sentiment.size > 0:
                        fig, ax = plt.subplots()
                        sns.heatmap(pattern_sentiment, annot=True, fmt='d', cmap='Blues', ax=ax)
                        st.pyplot(fig)
                    else:
                        st.info("No sentiment correlation data available for chart patterns.")
                else:
                    st.info("No data available for sentiment correlation analysis.")

                # Download button
                if not filtered_df.empty:
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Filtered Data", csv, "filtered_chart_pattern.csv", "text/csv")
                else:
                    st.info("No data available to download.")




# ---------------------------------------------------------------------------------------------------------

    elif view == "Technical Indicators":
        if df_chart_ind_data is None:
            st.warning("No technical indicator data available. Please run the screener first.")
        else:
            st.subheader("Technical Indicators Analysis")

            # Preprocess data
            df_ind = df_chart_ind_data[['Company', 'Fii_Dii_BUYING']].dropna()
            if df_ind.empty:
                st.info("No technical indicator data available.")
            else:
                # Fix string handling
                df_ind['Fii_Dii_BUYING'] = df_ind['Fii_Dii_BUYING'].astype(str)
                df_ind = df_ind.assign(Indicators=df_ind['Fii_Dii_BUYING'].str.split(', ')).explode('Indicators')

                # Show raw data
                st.dataframe(df_ind)

                # Indicator frequency analysis
                st.markdown("### 📊 Frequency of Technical Indicators")
                ind_counts = df_ind['Indicators'].value_counts().reset_index()
                ind_counts.columns = ['Technical Indicator', 'Frequency']
                st.bar_chart(ind_counts.set_index('Technical Indicator'))

                # Pie chart of indicators
                st.markdown("### 🥧 Indicator Distribution")
                fig = px.pie(ind_counts, values='Frequency', names='Technical Indicator', title='Technical Indicator Distribution')
                st.plotly_chart(fig)

                # Filter by selected indicator
                st.markdown("### 🔍 Filter by Technical Indicator")
                selected_ind = st.selectbox("Select an Indicator", df_ind['Indicators'].unique())
                filtered_ind_df = df_ind[df_ind['Indicators'] == selected_ind]
                st.write(f"Companies with `{selected_ind}` indicator:")
                st.dataframe(filtered_ind_df)

                # Correlation with final sentiment
                st.markdown("### 🔗 Correlation with Sentiment")
                df_ind_sent = df_chart_ind_data[['Fii_Dii_BUYING', 'final_sentiment']].dropna()
                df_ind_sent['Fii_Dii_BUYING'] = df_ind_sent['Fii_Dii_BUYING'].astype(str)
                df_ind_sent = df_ind_sent.assign(Indicators=df_ind_sent['Fii_Dii_BUYING'].str.split(', ')).explode('Indicators')
                ind_sentiment = df_ind_sent.groupby(['Indicators', 'final_sentiment']).size().unstack(fill_value=0)

                # Check if we have data for the heatmap
                if not ind_sentiment.empty and ind_sentiment.size > 0:
                    fig2, ax = plt.subplots()
                    sns.heatmap(ind_sentiment, annot=True, fmt='d', cmap='Greens', ax=ax)
                    st.pyplot(fig2)
                else:
                    st.info("No sentiment correlation data available to display heatmap.")

                # Download filtered data
                st.markdown("### 📥 Download Filtered Data")
                csv_ind = filtered_ind_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download as CSV", csv_ind, "filtered_technical_indicator.csv", "text/csv")


# ---------------------------------------------------------------------------------------------------------
    elif view == "Smart Trade Signals":
        if df_chart_ind_data is None:
            st.warning("No data available for trading signals. Please run the screener first.")
        else:
            st.subheader("📈 Smart Trade Signals – Automated Trading Strategy")

            df_combo = df_chart_ind_data.copy()

            # Ensure Ticker column is present in df_combo
            df_combo['Ticker'] = df_combo['Company'].astype(str).str.upper().str.strip() + ".NS"

            # Now perform the merge
            ml_signal_df = read_ml_signal_data()
            df_combo = df_combo.merge(ml_signal_df, how="left", on="Ticker")

            # Filter: only positive sentiments
            df_combo = df_combo[df_combo['final_sentiment'].isin(['Very Positive', 'Positive'])]

            if df_combo.empty:
                st.info("No positive sentiment data available for trading signals.")
            else:
                # Step 1: Sentiment Score
                sentiment_score_map = {'Very Positive': 3, 'Positive': 2}
                df_combo['Sentiment_Score'] = df_combo['final_sentiment'].map(sentiment_score_map)

                # Step 2: Chart Pattern Score (limited patterns)
                pattern_weights = {
                    'Resistance Breakout': 5,
                    'Volume Spike': 5
                }

                def calculate_pattern_score(patterns):
                    if pd.isna(patterns):
                        return 0
                    return sum(pattern_weights.get(p, 0) for p in patterns.split(', '))

                df_combo['Pattern_Score'] = df_combo['Chart_Pattern'].apply(calculate_pattern_score)

                # Step 3: ML Boost (scaled using ML_Confidence)
                df_combo['ML_Prediction'] = df_combo['ML_Prediction'].astype(str).str.upper().str.strip()

                def ml_boost(row):
                    if row.get("ML_Prediction", "").upper() == "STRONG BUY":
                        return float(row.get("ML_Confidence", 0.9)) * 10
                    return 0

                df_combo['ML_Boost'] = df_combo.apply(ml_boost, axis=1)

                # Step 4: Total Score (indicator removed)
                df_combo['Total_Score'] = (
                    df_combo['Sentiment_Score'] * 1.5 +
                    df_combo['Pattern_Score'] * 1.3 +
                    df_combo['ML_Boost']
                )

                # Step 5: Success Chance (%)
                max_possible_score = 27.5  # based on weighted max: 3*1.5 + 10*1.3 + 10 (ML_Boost)

                df_combo['Success_Chance (%)'] = (
                    (df_combo['Total_Score'] / max_possible_score) * 100
                ).clip(upper=100).round(2)  # 💡 clip caps the max at 100%

                # Step 6: Signal Logic
                def get_trading_signal(row):
                    score = row['Total_Score']
                    if score >= 15:
                        return "STRONG BUY"
                    elif score >= 10:
                        return "BUY"
                    elif score >= 6:
                        return "WATCH"
                    return "NO TRADE"

                df_combo['Trading_Signal'] = df_combo.apply(get_trading_signal, axis=1)

                # Fetch previously executed companies
                very_positive_trades_df = read_final_result_to_trade_execute()
                executed_companies = []
                if very_positive_trades_df is not None:
                    very_positive_trades_df['Company'] = very_positive_trades_df['Company'].astype(str).str.strip()
                    very_positive_trades_df['Trade_Execute_Or_Not'] = very_positive_trades_df['Trade_Execute_Or_Not'].astype(str).str.strip().str.lower()
                    executed_companies = very_positive_trades_df[very_positive_trades_df['Trade_Execute_Or_Not'] == 'yes']['Company'].tolist()

                # Only high-confidence, new signals
                save_df = df_combo[
                    (df_combo['Success_Chance (%)'] >= 50) &
                    (~df_combo['Company'].isin(executed_companies))
                ].sort_values('Success_Chance (%)', ascending=False)

                # Save signals to file
                if not save_df.empty:
                    final_df = pd.DataFrame({
                        "Company": save_df['Company'],
                        "Annoucement_Time": save_df['Time'],
                        "Final_Sentiment": save_df['final_sentiment'],
                        "Chart_Pattern": save_df['Chart_Pattern'],
                        "ML_Prediction": save_df['ML_Prediction'],
                        "ML_Confidence": save_df['ML_Confidence'],
                        "Success_Chance": save_df['Success_Chance (%)'],
                        "Fii_Dii_BUYING": save_df['Fii_Dii_BUYING'],
                        "Trade_Execute_Or_Not": "no"
                    })
                    save_to_csv_final_result(final_df)

                # UI Filters
                min_success_chance = st.slider(
                    "Minimum Success Chance (%)", 0, 100, 50
                )

                filtered_df = df_combo[df_combo['Success_Chance (%)'] >= min_success_chance]
                if filtered_df.empty:
                    st.warning("No trading signals match the current filters.")
                else:
                    st.success(f"Found {len(filtered_df)} trading signals with success chance >= {min_success_chance}%")

                display_columns = [
                    'Company', 'Time', 'final_sentiment', 'Chart_Pattern',
                    'ML_Prediction', 'ML_Confidence', 'Total_Score', 'Success_Chance (%)', 'Trading_Signal', 'Fii_Dii_BUYING'
                ]

                st.markdown("### 📊 Trading Signals")
                if not filtered_df.empty:
                    st.dataframe(
                        filtered_df[display_columns].sort_values(by='Success_Chance (%)', ascending=False),
                        use_container_width=True
                    )
                else:
                    st.info("No trading signals match the current filters.")

                # Extra strategy tables
                st.markdown("### 🔍 Additional Trading Strategies")

                st.markdown("#### High Confidence Signals (Success Chance > 70%)")
                high_confidence_df = df_combo[df_combo['Success_Chance (%)'] >= 70]
                if not high_confidence_df.empty:
                    st.dataframe(high_confidence_df[display_columns].sort_values(
                        by='Success_Chance (%)', ascending=False), use_container_width=True)
                else:
                    st.info("No high confidence signals found.")

                st.markdown("### 🛡️ Risk Management Summary for Signals")

                risk_summary = []
                budget = 100000  # or use st.sidebar.number_input
                risk_per_trade = 1000

                for _, row in filtered_df.iterrows():
                    symbol = f"{row['Company']}.NS"
                    risk_result = get_live_risk_config(
                        symbol=symbol,
                        budget=budget,
                        risk_per_trade=risk_per_trade,
                        stop_loss_manual=None,
                        entry_manual=None
                    )
                    if "error" not in risk_result:
                        risk_summary.append(risk_result)

                if risk_summary:
                    df_risk = pd.DataFrame(risk_summary)
                    st.dataframe(df_risk)
                    # Optional CSV download
                    csv = df_risk.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Risk Report", csv, "risk_signals.csv", "text/csv")
                else:
                    st.warning("No valid risk reports generated.")

#algo trading start here ------------------------------------------------------------------------------

                # Auto trading logic
                if trading_engine:
                    for index, row in very_positive_trades_df.iterrows():
                        try:
                            company_name = row['Company']
                            print(f"🔄 Before Processing trade for {company_name}...")

                            if update_trade_execution_status(company_name):
                                print(f"🔄 after Processing trade for {company_name}...")
                                # trade_response = "Entry: ₹697.0, Target (+10%): ₹766.7, Stop Loss (-3%): ₹676.09"
                                
                                # Simulate or place trade here
                                # trade_response = place_gtt_order_by_symbol_percent(
                                #     symbol=row['Company']
                                # )

                                cmp = yf.Ticker(f"{company_name}.NS").info["currentPrice"]
                                # send_whatsapp_alert_trade_executed(
                                #     stock=company_name,
                                #     confidence=row['Success_Chance'],
                                #     pattern=row['Chart_Pattern'],
                                #     price=f"₹{cmp:.2f}",
                                #     executed_msg=trade_response
                                # )
                                # # send trade signal to WhatsApp
                                send_alert_msg(row)

                            else:
                                print(f"⏭️ Skipping {company_name}, already executed")
                        except Exception as e:
                            st.error(f"❌ Error trading {row['Company']}: {e}")
#algo trading end here ------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------
    elif view == "Risk Management":
        st.subheader("📌 Manual Risk Management Calculator")

        symbol_input = st.text_input("Enter Stock Symbol (e.g., RELIANCE.NS)")
        budget = st.number_input("Total Budget", min_value=1000, value=100000)
        risk = st.number_input("Risk per Trade", min_value=100, value=1000)
        rrr = st.slider("Risk to Reward Ratio", 1.0, 5.0, value=2.0)
        
        if st.button("Calculate Risk Plan"):
            result = get_live_risk_config(
                symbol=symbol_input,
                budget=budget,
                risk_per_trade=risk,
                risk_to_reward_ratio=rrr,
                plot=False
            )
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("✅ Risk Management Plan")
                st.dataframe(pd.DataFrame([result]))

if __name__ == "__main__":
    main()