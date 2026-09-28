import os
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


def get_engine():
    db_url = os.getenv("DATABASE_URL")
    return create_engine(db_url)


def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-3.6-flash")


def load_recent_stats(engine, days=30):
    query = f"""
        SELECT order_date, total_sales, total_orders, ma_7, ma_30,
               zscore, is_outlier, daily_growth_pct, growth_7d_pct
        FROM sales_statistics
        ORDER BY order_date DESC
        LIMIT {days}
    """
    df = pd.read_sql(query, engine)
    return df.sort_values("order_date")


def load_forecast(engine):
    query = "SELECT * FROM sales_forecast ORDER BY order_date"
    return pd.read_sql(query, engine)


def build_prompt(recent_df, forecast_df):
    latest = recent_df.iloc[-1]
    avg_sales_30d = recent_df["total_sales"].mean()
    outlier_days = recent_df[recent_df["is_outlier"] == True]
    forecast_start = forecast_df["forecast_sales"].iloc[0]
    forecast_end = forecast_df["forecast_sales"].iloc[-1]
    forecast_direction = "upward" if forecast_end > forecast_start else "downward"

    prompt = f"""
You are a senior business analyst preparing a written summary for a
dashboard. Based on the sales data below, write a detailed analysis
of 3 short paragraphs (8-10 sentences total). Use plain English,
no bullet points, no markdown, no headers.

Paragraph 1: Describe the current sales trend using the moving
averages and growth rate. State whether the business is accelerating,
steady, or slowing, and by how much.

Paragraph 2: Discuss the outlier days and what they suggest. Note
whether there were unusual spikes or drops, and what that could mean
operationally (demand surge, stockout, promotion effect, data anomaly).

Paragraph 3: Interpret the 30 day forecast and give a concrete
recommendation for what the business should focus on next.

Data:
Latest recorded date: {latest['order_date'].date()}
Latest day sales: {latest['total_sales']:.2f}
Average daily sales last 30 days: {avg_sales_30d:.2f}
7 day moving average: {latest['ma_7']:.2f}
30 day moving average: {latest['ma_30']:.2f}
7 day growth rate: {latest['growth_7d_pct']:.2f} percent
Number of outlier days in the last 30: {len(outlier_days)}
30 day forecast trend: {forecast_direction}, from {forecast_start:.2f} to {forecast_end:.2f}
"""
    return prompt.strip()


def generate_summary(model, prompt):
    response = model.generate_content(prompt)
    return response.text.strip()


def save_summary(summary_text, engine):
    df = pd.DataFrame([{
        "generated_at": datetime.now(timezone.utc),
        "summary": summary_text
    }])
    df.to_sql("business_summary", engine, if_exists="append", index=False)
    print("Summary saved to 'business_summary' table")


def main():
    engine = get_engine()
    model = get_gemini_model()

    recent_df = load_recent_stats(engine, days=30)
    forecast_df = load_forecast(engine)

    prompt = build_prompt(recent_df, forecast_df)
    summary = generate_summary(model, prompt)

    print("\n--- AI Business Summary ---")
    print(summary)
    print("----------------------------\n")

    save_summary(summary, engine)


if __name__ == "__main__":
    main()