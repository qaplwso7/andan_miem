import pandas as pd
import numpy as np

dau_df = pd.read_csv(r"C:\Users\nikita\Desktop\иад_миэм\dz_2\dau_forecast.csv")
navigation_df = pd.read_csv(r"C:\Users\nikita\Desktop\иад_миэм\dz_2\navigation_events.csv")
impressions_df = pd.read_csv(r"C:\Users\nikita\Desktop\иад_миэм\dz_2\product_impressions.csv")

navigation_df["timestamp"] = pd.to_datetime(navigation_df["timestamp"], format="%d.%m.%Y %H:%M:%S")
navigation_df["date"] = navigation_df["timestamp"].dt.date
impressions_df["timestamp"] = pd.to_datetime(impressions_df["timestamp"])
impressions_df["date"] = impressions_df["timestamp"].dt.date
dau_df["month"] = pd.to_datetime(dau_df["month"]).dt.to_period("M")

for df in [navigation_df, impressions_df]:
    df["section"] = df["section"].astype("string").str.lower().str.strip()
navigation_df["event_type"] = navigation_df["event_type"].astype("string").str.lower().str.strip()

impressions_df["row_number"] = (
    impressions_df["row_number"].astype("string").str.replace(",", ".", regex=False).astype(float)
)

def to_float(x):
    if pd.isna(x) or str(x).strip() == "—":
        return np.nan
    return float(str(x).replace("\xa0", "").replace(" ", "").replace(",", "."))

dau_df["avg_dau_plan"] = dau_df["avg_dau_plan"].apply(to_float)
dau_df["avg_dau_actual"] = dau_df["avg_dau_actual"].apply(to_float)

print("month dtype", dau_df["month"].dtype)
print(dau_df.tail(4).to_string())
print("actual na months", dau_df.loc[dau_df["avg_dau_actual"].isna(), "month"].astype(str).tolist())

dau_daily = (
    navigation_df[navigation_df["event_type"] == "app_open"]
    .groupby("date")["user_id"].nunique().rename("dau")
)

placement_banners = {
    "feed_cheese": (3, "right"),
    "feed_monterra": (6, "left"),
    "feed_mango": (12, "left"),
    "feed_ideas": (15, "right"),
}
feed_impressions = impressions_df[impressions_df["section"] == "feed"].copy()
reach_frames = {}
for banner, (row, column) in placement_banners.items():
    proxy_column = "left" if column == "right" else "right"
    sub_df = feed_impressions[
        (feed_impressions["row_number"] == row) & (feed_impressions["column"] == proxy_column)
    ]
    print(banner, "proxy", proxy_column, "rows", len(sub_df), "users", sub_df["user_id"].nunique())
    reach_frames[banner] = sub_df.groupby("date")["user_id"].nunique().rename(banner + "_reach")

feed_reach_daily = pd.concat(reach_frames.values(), axis=1).fillna(0)
search_reach_daily = (
    navigation_df[(navigation_df["event_type"] == "section_open") & (navigation_df["section"] == "search")]
    .groupby("date")["user_id"].nunique().rename("search_reach")
)
daily = pd.concat([dau_daily, search_reach_daily, feed_reach_daily], axis=1).fillna(0)
reach_columns = [c for c in daily.columns if c.endswith("_reach")]
print("days", len(daily), "share>1", ((daily[reach_columns].div(daily["dau"], axis=0)) > 1).any().to_dict())
for col in reach_columns:
    daily[col + "_share"] = daily[col] / daily["dau"]
average_shares = daily[[c for c in daily.columns if c.endswith("_share")]].mean()
ratio_of_means = daily[reach_columns].mean() / daily["dau"].mean()
print("mean of ratios\n", average_shares.round(4))
print("ratio of means\n", ratio_of_means.round(4))

forecast = dau_df[dau_df["month"].dt.strftime("%Y-%m").isin(["2026-10", "2026-11", "2026-12"])][
    ["month", "avg_dau_plan"]
].copy()
forecast["month_label"] = forecast["month"].dt.strftime("%Y-%m")
place_map = {
    "feed_cheese_reach_share": "Лента: Сырная шпаргалка",
    "feed_monterra_reach_share": "Лента: Monterra",
    "feed_mango_reach_share": "Лента: Манго",
    "feed_ideas_reach_share": "Лента: Идеи",
    "search_reach_share": "Поиск: большой баннер",
}
result = forecast[["month_label", "avg_dau_plan"]].copy()
for sc, name in place_map.items():
    result[name] = (result["avg_dau_plan"] * average_shares[sc]).round().astype(int)
print(result.to_string(index=False))

# users with impression but no app_open that day
imp_users = impressions_df.groupby("date")["user_id"].apply(set)
open_users = navigation_df[navigation_df["event_type"] == "app_open"].groupby("date")["user_id"].apply(set)
extra = 0
for d in imp_users.index:
    extra += len(imp_users[d] - open_users.get(d, set()))
print("impression users without app_open same day", extra)
