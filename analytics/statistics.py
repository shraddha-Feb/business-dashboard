import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    db_url = os.getenv("DATABASE_URL")
    return create_engine(db_url)


def load_daily_sales(engine):
    query = "SELECT * FROM daily_sales ORDER BY order_date"
    df = pd.read_sql(query, engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def compute_moving_averages(df):
    df["ma_7"] = df["total_sales"].rolling(window=7, min_periods=1).mean()
    df["ma_30"] = df["total_sales"].rolling(window=30, min_periods=1).mean()
    return df


def compute_zscore_outliers(df, threshold=2.0):
    mean = df["total_sales"].mean()
    std = df["total_sales"].std()
    df["zscore"] = (df["total_sales"] - mean) / std
    df["is_outlier"] = df["zscore"].abs() > threshold
    return df


def compute_growth_rates(df):
    df["daily_growth_pct"] = df["total_sales"].pct_change() * 100
    df["growth_7d_pct"] = df["total_sales"].pct_change(periods=7) * 100
    return df


def forecast_sales(df, periods=30):
    df = df.reset_index(drop=True)
    x = np.arange(len(df))
    y = df["total_sales"].values

    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(df), len(df) + periods)
    future_dates = pd.date_range(
        start=df["order_date"].max() + pd.Timedelta(days=1),
        periods=periods
    )
    forecast_values = slope * future_x + intercept

    forecast_df = pd.DataFrame({
        "order_date": future_dates,
        "forecast_sales": forecast_values
    })
    return forecast_df, slope


def save_to_db(df, table_name, engine):
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Saved {len(df)} rows to '{table_name}'")


def main():
    engine = get_engine()

    df = load_daily_sales(engine)
    df = compute_moving_averages(df)
    df = compute_zscore_outliers(df)
    df = compute_growth_rates(df)

    forecast_df, slope = forecast_sales(df, periods=30)

    print(f"Trend slope: {slope:.2f} sales/day")
    print(f"Outlier days found: {df['is_outlier'].sum()}")

    save_to_db(df, "sales_statistics", engine)
    save_to_db(forecast_df, "sales_forecast", engine)


if __name__ == "__main__":
    main()