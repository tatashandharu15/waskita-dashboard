import re
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class ParseError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


REQUIRED_COLUMNS = [
    "SOURCE",
    "DATE",
    "SENTIMENT",
    "TRACKED KEYWORD",
    "PERFORMANCE",
]

NUMERIC_COLUMNS = [
    "SOCIAL MEDIA INTERACTIONS",
    "REACH",
    "VISITS",
    "PERFORMANCE",
    "FOLLOWING",
    "LIKES",
    "SHARES",
    "COMMENTS",
    "VIEWS",
    "FAVOURITES",
]

STRING_CLEAN_COLUMNS = [
    "SOURCE",
    "TITLE",
    "TEXT",
    "TRACKED KEYWORD",
    "SENTIMENT",
    "EMOTION",
    "LANGUAGE",
    "COUNTRY",
    "AUTHOR NAME",
    "AUTHOR USERNAME",
]

ENGAGEMENT_METRIC_LABELS = {
    "SOCIAL MEDIA INTERACTIONS": "Social Interactions",
    "REACH": "Reach",
    "VISITS": "Visits",
    "PERFORMANCE": "Performance Score",
    "FOLLOWING": "Following",
    "LIKES": "Likes",
    "SHARES": "Shares",
    "COMMENTS": "Comments",
    "VIEWS": "Views",
    "FAVOURITES": "Favourites",
}


def _to_numeric_safe(series: pd.Series) -> pd.Series:
    s = series.copy()
    if s.dtype == object:
        s = s.astype(str).str.strip()
        s = s.replace({"": np.nan, " ": np.nan, "nan": np.nan, "NaN": np.nan})
        if s.dtype == object:
            s = s.str.replace(",", "", regex=False)
            s = s.str.replace("%", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _clean_string_series(series: pd.Series) -> pd.Series:
    s = series.copy()
    s = s.fillna("")
    if s.dtype == object:
        s = s.astype(str).str.strip()
        s = s.replace({"": "Unknown", " ": "Unknown", "nan": "Unknown", "NaN": "Unknown"})
    return s


def _pct(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total * 100, 2)


STOPWORDS = set("""
yang dan di dengan dari untuk pada tidak ini itu ada saya anda kita mereka
juga dalam akan atau lebih sudah bisa harus sangat baru saja tidak ada
karena menjadi seperti oleh telah dapat hanya masih serta banyak setelah
sebagai tetapi selain antara sebelum beberapa kemudian tersebut daripada
sesuai hingga sehingga walaupun maupun kalau daripada apakah yaitu
bahwa lalu bukan pernah melakukan semua setiap atas bawah hanya sebab
akibat yaitu demi karena meskipun per nih bro kak pak bu gan mas
sama lagi lah si mah dong deh tuh bang uh yah ah apa siapa bagaimana
kapan mana dimana pun ya tidaklah sangatlah
the of and to in a is that for it with as on be this by are at an
be not or and which has have had was were will would can could should
you he she they them his her its our their my your no we us i so if
do does did out up down than then too very just also now here there
when what where who why how all any both each few more most other some
such than into about through before after above below between under
again further then once here there when where why how all any both
each few more most other some such no nor only own same so than too
very just because but and or if while although though
""".lower().split())

_EMOJI_RE_PATTERNS = [
    "[\\U0001F600-\\U0001F64F]",
    "[\\U0001F300-\\U0001F5FF]",
    "[\\U0001F680-\\U0001F6FF]",
    "[\\U0001F1E0-\\U0001F1FF]",
    "[\\U0001F900-\\U0001F9FF]",
    "[\\U0001FA70-\\U0001FAFF]",
    "[\\U00002702-\\U000027B0]",
    "[\\U0001F700-\\U0001F77F]",
    "[\\U00002600-\\U000027BF]",
    "[\\U0001FC00-\\U0001FFFD]",
]
EMOJI_RE = re.compile("|".join(_EMOJI_RE_PATTERNS))


def _extract_top_words(series_text: pd.Series, top_n: int = 120) -> List[Dict[str, Any]]:
    c: Counter = Counter()
    for t in series_text.fillna("").astype(str):
        s = t.lower()
        s = re.sub(r"https?://\S+", " ", s)
        s = re.sub(r"#\S+|@\S+", " ", s)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        for tok in s.split():
            tok = tok.strip()
            if len(tok) < 3:
                continue
            if tok in STOPWORDS:
                continue
            if tok.isdigit():
                continue
            c[tok] += 1
    items = c.most_common(top_n)
    if not items:
        return []
    max_cnt = items[0][1] if items else 1
    out = []
    for w, cnt in items:
        out.append({
            "word": w,
            "count": int(cnt),
            "weight": round((cnt / max_cnt) * 100, 2),
        })
    return out


def _extract_emoji_frequency(series_text: pd.Series, top_n: int = 100) -> List[Dict[str, Any]]:
    c: Counter = Counter()
    for t in series_text.fillna("").astype(str):
        matches = EMOJI_RE.findall(t)
        for m in matches:
            c[m] += 1
    items = c.most_common(top_n)
    if not items:
        return []
    max_cnt = items[0][1]
    out = []
    for e, cnt in items:
        out.append({
            "emoji": e,
            "count": int(cnt),
            "weight": round((cnt / max_cnt) * 100, 2),
        })
    return out


def _build_all_mentions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    cols = [
        ("SOURCE", "source"),
        ("AUTHOR NAME", "author_name"),
        ("AUTHOR USERNAME", "author_username"),
        ("DATE", "date"),
        ("TITLE", "title"),
        ("TEXT", "text"),
        ("URL", "url"),
        ("SENTIMENT", "sentiment"),
        ("EMOTION", "emotion"),
        ("TRACKED KEYWORD", "keyword"),
        ("LANGUAGE", "language"),
        ("COUNTRY", "country"),
        ("REACH_NUM", "reach"),
        ("LIKES_NUM", "likes"),
        ("SHARES_NUM", "shares"),
        ("COMMENTS_NUM", "comments"),
        ("VIEWS_NUM", "views"),
        ("PERFORMANCE_NUM", "performance"),
    ]
    arr = []
    total = int(len(df))
    for i in range(total):
        row = df.iloc[i]
        obj: Dict[str, Any] = {}
        for src, dst in cols:
            val = row[src] if src in df.columns else ""
            if isinstance(val, (np.integer,)):
                val = int(val)
            elif isinstance(val, (np.floating,)):
                if np.isnan(val):
                    val = 0
                else:
                    val = round(float(val), 2)
            elif pd.isna(val) if isinstance(val, float) else False:
                val = "" if dst in ("source","author_name","author_username","date","title","text","sentiment","emotion","keyword","language","country","url") else 0
            if dst in ("reach","likes","shares","comments","views","performance") and val == "":
                val = 0
            if dst == "date" and isinstance(val, (pd.Timestamp, datetime)):
                try:
                    val = val.isoformat()
                except Exception:
                    val = str(val)
            if dst == "url" and val:
                s = str(val).strip()
                if not (s.startswith("http://") or s.startswith("https://")):
                    s = "https://" + s
                val = s
            obj[dst] = "" if val is None else val
        text_full = ""
        if "TEXT" in df.columns:
            text_full = str(obj.get("text") or "")
        if "TITLE" in df.columns and str(obj.get("title") or ""):
            text_full = str(obj.get("title") or "") + " - " + text_full
        obj["text_preview"] = text_full[:300] if len(text_full) > 300 else text_full
        obj["id"] = int(i + 1)
        arr.append(obj)
    return arr


def _top_n_distribution(
    series: pd.Series, total: int, n: int = 12, label: str = "name"
) -> List[Dict[str, Any]]:
    counts = series.value_counts().head(n)
    return [
        {label: str(idx), "count": int(cnt), "percentage": _pct(int(cnt), total)}
        for idx, cnt in counts.items()
    ]


def _iso_date(dt: Optional[pd.Timestamp]) -> Optional[str]:
    if pd.isna(dt) or dt is None:
        return None
    try:
        return dt.isoformat(timespec="minutes")
    except Exception:
        return None


def _extract_hashtags(text_series: pd.Series, top_n: int = 50) -> List[Dict[str, Any]]:
    texts = text_series.fillna("").astype(str)
    all_tags: List[str] = []
    pattern = re.compile(r"#(\w+)")
    for t in texts:
        found = pattern.findall(t.lower())
        all_tags.extend(found)
    total = max(len(texts), 1)
    counter = Counter(all_tags)
    return [
        {"tag": f"#{tag}", "count": cnt, "percentage": _pct(cnt, total)}
        for tag, cnt in counter.most_common(top_n)
    ]


def _detect_mode_date(dates: pd.Series) -> Optional[pd.Timestamp]:
    valid = dates.dropna()
    if len(valid) == 0:
        return None
    try:
        d = valid.dt.date
        mode_vals = d.mode()
        if len(mode_vals) > 0:
            return pd.Timestamp(mode_vals.iloc[0])
        return pd.Timestamp(valid.dt.date.value_counts().index[0])
    except Exception:
        return None


def _hourly_trend(
    dates: pd.Series, focus_date: Optional[pd.Timestamp]
) -> tuple[List[Dict[str, Any]], int, int]:
    result: List[Dict[str, Any]] = []
    for h in range(24):
        result.append({"hour": h, "count": 0})
    valid = dates.dropna()
    if len(valid) == 0:
        return result, -1, 0
    if focus_date is not None:
        focus_d = focus_date.date()
        mask = valid.dt.date == focus_d
        filtered = valid[mask]
    else:
        filtered = valid
    if len(filtered) == 0:
        filtered = valid
    counts = filtered.dt.hour.value_counts()
    for h, cnt in counts.items():
        if 0 <= h < 24:
            result[int(h)]["count"] = int(cnt)
    peak_hour = -1
    peak_count = 0
    for entry in result:
        if entry["count"] > peak_count:
            peak_count = entry["count"]
            peak_hour = entry["hour"]
    return result, peak_hour, peak_count


def _performance_distribution(
    df: pd.DataFrame, total: int
) -> Dict[str, Any]:
    perf = df["PERFORMANCE_NUM"]
    scores: List[int] = [0] * 11
    valid_perf = perf.dropna()
    for val in valid_perf:
        try:
            iv = int(round(float(val)))
            if 1 <= iv <= 10:
                scores[iv] += 1
        except Exception:
            pass
    scores_list = []
    for s in range(1, 11):
        scores_list.append(
            {"score": s, "count": scores[s], "percentage": _pct(scores[s], total)}
        )
    mean_v = 0.0
    median_v = 0.0
    std_v = 0.0
    if len(valid_perf) > 0:
        mean_v = round(float(valid_perf.mean()), 2)
        median_v = round(float(valid_perf.median()), 2)
        std_v = round(float(valid_perf.std(ddof=0) if len(valid_perf) > 1 else 0.0), 2)
    top_performers_per_source: List[Dict[str, Any]] = []
    if "SOURCE" in df.columns:
        by_src = df.groupby("SOURCE")
        for src, grp in by_src:
            src_total = len(grp)
            if src_total == 0:
                continue
            count_10 = int((grp["PERFORMANCE_NUM"].dropna().astype(float).round() == 10).sum())
            top_performers_per_source.append(
                {
                    "source": str(src),
                    "count_10": count_10,
                    "pct_10_from_source": _pct(count_10, src_total),
                    "source_total": src_total,
                }
            )
    top_performers_per_source.sort(key=lambda r: r["count_10"], reverse=True)
    return {
        "scores": scores_list,
        "mean": mean_v,
        "median": median_v,
        "std": std_v,
        "top_performers_per_source": top_performers_per_source,
    }


def _engagement_metrics(df: pd.DataFrame) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for col in [
        "SOCIAL MEDIA INTERACTIONS",
        "REACH",
        "VISITS",
        "LIKES",
        "SHARES",
        "COMMENTS",
        "VIEWS",
        "FOLLOWING",
    ]:
        num_col = f"{col}_NUM"
        if num_col not in df.columns:
            continue
        series = df[num_col].dropna()
        n_valid = int(len(series))
        total = 0.0
        avg = 0.0
        mx = 0.0
        if n_valid > 0:
            total = float(series.sum())
            avg = float(series.mean())
            mx = float(series.max())
        out.append(
            {
                "metric": ENGAGEMENT_METRIC_LABELS.get(col, col),
                "metric_key": col,
                "total": round(total),
                "total_display": round(total),
                "avg": round(avg, 1),
                "max": round(mx),
                "n_valid": n_valid,
            }
        )
    return out


def _keyword_sentiment_crosstab(
    df: pd.DataFrame, total: int
) -> List[Dict[str, Any]]:
    if "TRACKED KEYWORD" not in df.columns or "SENTIMENT" not in df.columns:
        return []
    kw_counts = df["TRACKED KEYWORD"].value_counts()
    result = []
    for kw, cnt in kw_counts.items():
        grp = df[df["TRACKED KEYWORD"] == kw]
        s_counts = grp["SENTIMENT"].value_counts().to_dict()
        pos = int(s_counts.get("positive", 0))
        neu = int(s_counts.get("neutral", 0))
        neg = int(s_counts.get("negative", 0))
        tot = pos + neu + neg
        result.append(
            {
                "name": str(kw),
                "count": int(cnt),
                "percentage": _pct(int(cnt), total),
                "sentiment_pct": {
                    "positive": _pct(pos, tot),
                    "neutral": _pct(neu, tot),
                    "negative": _pct(neg, tot),
                },
                "sentiment_counts": {
                    "positive": pos,
                    "neutral": neu,
                    "negative": neg,
                },
            }
        )
    return result


def _sentiment_per_source(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if "SOURCE" not in df.columns or "SENTIMENT" not in df.columns:
        return []
    result = []
    for src, grp in df.groupby("SOURCE"):
        tot = len(grp)
        if tot == 0:
            continue
        s_counts = grp["SENTIMENT"].value_counts().to_dict()
        pos = int(s_counts.get("positive", 0))
        neu = int(s_counts.get("neutral", 0))
        neg = int(s_counts.get("negative", 0))
        result.append(
            {
                "source": str(src),
                "total": tot,
                "pos_pct": _pct(pos, tot),
                "neu_pct": _pct(neu, tot),
                "neg_pct": _pct(neg, tot),
                "pos_count": pos,
                "neu_count": neu,
                "neg_count": neg,
            }
        )
    result.sort(key=lambda r: r["total"], reverse=True)
    return result


def _top_authors(df: pd.DataFrame, top_n: int = 15) -> List[Dict[str, Any]]:
    name_col = "AUTHOR NAME" if "AUTHOR NAME" in df.columns else None
    user_col = "AUTHOR USERNAME" if "AUTHOR USERNAME" in df.columns else None
    if not name_col:
        return []
    mask = (df[name_col].fillna("").astype(str).str.strip() != "") & (
        df[name_col].fillna("").astype(str).str.strip() != "Unknown"
    )
    filtered = df[mask]
    if len(filtered) == 0:
        return []
    group_cols = [name_col]
    if user_col:
        group_cols.append(user_col)
    grouped = filtered.groupby(group_cols, dropna=False).size().reset_index(name="count")
    grouped = grouped.sort_values("count", ascending=False).head(top_n)
    result = []
    for _, row in grouped.iterrows():
        name = str(row[name_col]) if pd.notna(row[name_col]) else ""
        username = ""
        if user_col:
            username = str(row[user_col]) if pd.notna(row[user_col]) and str(row[user_col]) != "Unknown" else ""
        result.append(
            {
                "author_name": name,
                "author_username": username,
                "count": int(row["count"]),
            }
        )
    return result


def _demographics(df: pd.DataFrame) -> Dict[str, Any]:
    male_col = "WEBSITE TRAFFIC DEMOGRAPHICS MALE"
    female_col = "WEBSITE TRAFFIC DEMOGRAPHICS FEMALE"
    if male_col not in df.columns or female_col not in df.columns:
        return {"male_avg_pct": 0, "female_avg_pct": 0, "n_samples": 0}
    m_raw = df[male_col].astype(str).str.strip().str.replace("%", "", regex=False)
    f_raw = df[female_col].astype(str).str.strip().str.replace("%", "", regex=False)
    m_num = pd.to_numeric(m_raw.replace({"": np.nan, "Unknown": np.nan, "nan": np.nan}), errors="coerce")
    f_num = pd.to_numeric(f_raw.replace({"": np.nan, "Unknown": np.nan, "nan": np.nan}), errors="coerce")
    mask = m_num.notna() & f_num.notna()
    m_valid = m_num[mask]
    f_valid = f_num[mask]
    n = int(len(m_valid))
    if n == 0:
        return {"male_avg_pct": 0, "female_avg_pct": 0, "n_samples": 0}
    return {
        "male_avg_pct": round(float(m_valid.mean()), 2),
        "female_avg_pct": round(float(f_valid.mean()), 2),
        "n_samples": n,
    }


def _negative_samples(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Any]]:
    if "SENTIMENT" not in df.columns:
        return []
    neg = df[df["SENTIMENT"] == "negative"].head(n)
    out = []
    text_col = "TEXT" if "TEXT" in df.columns else "TITLE"
    src_col = "SOURCE"
    emo_col = "EMOTION"
    kw_col = "TRACKED KEYWORD"
    for _, row in neg.iterrows():
        text = str(row.get(text_col, "")) if pd.notna(row.get(text_col, "")) else ""
        preview = text[:220] + ("..." if len(text) > 220 else "")
        src = str(row.get(src_col, "Unknown"))
        emo = str(row.get(emo_col, "Unknown")) if pd.notna(row.get(emo_col, None)) else "Unknown"
        kw = str(row.get(kw_col, "Unknown")) if pd.notna(row.get(kw_col, None)) else "Unknown"
        out.append(
            {
                "source": src,
                "text_preview": preview,
                "emotion": emo,
                "tracked_keyword": kw,
            }
        )
    return out


def parse_excel_file(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        raise ParseError(f"File not found: {file_path}")
    try:
        df = pd.read_excel(file_path, sheet_name=0)
    except Exception as e:
        raise ParseError(f"Failed to read Excel: {type(e).__name__}")

    df.columns = [str(c).strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ParseError(f"Missing required columns: [{', '.join(missing)}]")

    total = int(len(df))
    columns_count = int(df.shape[1])

    for col in STRING_CLEAN_COLUMNS:
        if col in df.columns:
            df[col] = _clean_string_series(df[col])

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[f"{col}_NUM"] = _to_numeric_safe(df[col])
        else:
            df[f"{col}_NUM"] = pd.Series([np.nan] * total)

    if "DATE_NUM" not in df.columns and "DATE" in df.columns:
        raw = df["DATE"].astype(str).str.strip()
        raw = raw.replace({"": np.nan, " ": np.nan, "Unknown": np.nan, "nan": np.nan})
        df["DATE_NUM"] = pd.to_datetime(raw, errors="coerce", utc=False)

    valid_dates = df["DATE_NUM"].dropna()
    min_date = _iso_date(valid_dates.min()) if len(valid_dates) > 0 else None
    max_date = _iso_date(valid_dates.max()) if len(valid_dates) > 0 else None
    date_range_hours = 0
    if min_date and max_date:
        try:
            d1 = pd.Timestamp(min_date)
            d2 = pd.Timestamp(max_date)
            date_range_hours = max(0, int(math.ceil((d2 - d1).total_seconds() / 3600.0)))
        except Exception:
            date_range_hours = 0

    source_dist = _top_n_distribution(df["SOURCE"], total, n=20, label="name")

    if "SENTIMENT" in df.columns:
        s_counts = df["SENTIMENT"].value_counts().to_dict()
        pos = int(s_counts.get("positive", 0))
        neu = int(s_counts.get("neutral", 0))
        neg = int(s_counts.get("negative", 0))
        tot_sent = pos + neu + neg
        sentiment_dist = {
            "positive": {"count": pos, "percentage": _pct(pos, tot_sent)},
            "neutral": {"count": neu, "percentage": _pct(neu, tot_sent)},
            "negative": {"count": neg, "percentage": _pct(neg, tot_sent)},
        }
        pct_positive = _pct(pos, tot_sent)
        pct_neutral = _pct(neu, tot_sent)
        pct_negative = _pct(neg, tot_sent)
        composite = round((pos - neg) / tot_sent, 3) if tot_sent > 0 else 0.0
    else:
        sentiment_dist = {"positive": {"count": 0, "percentage": 0}, "neutral": {"count": 0, "percentage": 0}, "negative": {"count": 0, "percentage": 0}}
        pct_positive = pct_neutral = pct_negative = 0
        composite = 0.0

    emotion_dist = _top_n_distribution(
        df["EMOTION"] if "EMOTION" in df.columns else pd.Series(["Unknown"] * total),
        total,
        n=15,
        label="name",
    )

    focus_date = _detect_mode_date(df["DATE_NUM"])
    hourly, peak_hour, peak_count = _hourly_trend(df["DATE_NUM"], focus_date)
    focus_date_str = _iso_date(focus_date) if focus_date else None

    texts_combined = df.get("TITLE", pd.Series(dtype=str)).fillna("").astype(str) + " " + df.get("TEXT", pd.Series(dtype=str)).fillna("").astype(str)
    top_hashtags = _extract_hashtags(texts_combined, top_n=40)
    if len(top_hashtags) == 0 and "TAGS" in df.columns:
        top_hashtags = _extract_hashtags(df["TAGS"].fillna(""), top_n=40)

    performance = _performance_distribution(df, total)

    engagement = _engagement_metrics(df)

    reach_sum = 0.0
    reach_valid = 0
    for e in engagement:
        if e["metric_key"] == "REACH":
            reach_sum = e["total"]
            reach_valid = e["n_valid"]
            break
    avg_reach = reach_sum / reach_valid if reach_valid > 0 else 0.0

    keyword_dist = _keyword_sentiment_crosstab(df, total)

    lang_dist = _top_n_distribution(
        df["LANGUAGE"] if "LANGUAGE" in df.columns else pd.Series(["Unknown"] * total),
        total, n=15, label="lang"
    )
    country_dist = _top_n_distribution(
        df["COUNTRY"] if "COUNTRY" in df.columns else pd.Series(["Unknown"] * total),
        total, n=15, label="country"
    )

    top_authors = _top_authors(df, top_n=15)

    demo = _demographics(df)

    sent_per_source = _sentiment_per_source(df)

    neg_sample = _negative_samples(df, n=5)

    top_words = _extract_top_words(texts_combined, top_n=150)
    emoji_frequency = _extract_emoji_frequency(texts_combined, top_n=120)
    all_mentions = _build_all_mentions(df)

    overview = {
        "total_mentions": total,
        "total_reach_valid": reach_valid,
        "total_reach_sum": round(reach_sum),
        "avg_reach": round(avg_reach),
        "pct_positive": pct_positive,
        "pct_neutral": pct_neutral,
        "pct_negative": pct_negative,
        "sentiment_composite": composite,
    }

    metadata = {
        "rows_count": total,
        "columns_count": columns_count,
        "min_date": min_date,
        "max_date": max_date,
        "focus_date": focus_date_str,
        "date_range_hours": date_range_hours,
        "upload_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    return {
        "metadata": metadata,
        "overview_kpi": overview,
        "source_distribution": source_dist,
        "keyword_distribution": keyword_dist,
        "sentiment_distribution": sentiment_dist,
        "emotion_distribution": emotion_dist,
        "hourly_trend": {
            "items": hourly,
            "peak_hour": peak_hour,
            "peak_count": peak_count,
            "focus_date": focus_date_str,
        },
        "top_hashtags": top_hashtags[:20],
        "top_hashtags_full": top_hashtags,
        "performance_distribution": performance,
        "engagement": engagement,
        "language_distribution": lang_dist,
        "country_distribution": country_dist,
        "top_authors": top_authors,
        "demographics": demo,
        "sentiment_per_source": sent_per_source,
        "negative_sample": neg_sample,
        "columns_present": list(df.columns),
        "top_words": top_words,
        "emoji_frequency": emoji_frequency,
        "all_mentions": all_mentions,
    }
