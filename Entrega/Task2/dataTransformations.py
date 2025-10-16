import pandas as pd
import re

NULL_LIKE = {"", "\\N", "None", "null", None, "NaN"}

def convert_to_none(val):
    if val is None:
        return None
    
    if isinstance(val, str):
        val = val.strip()
        if val.lower() in NULL_LIKE:
            return None
        return val
    
    if pd.isna(val):
        return None
    return val


def normalize_ref(string):
    if string is None:
        return None
    
    string = str(string).strip().lower()
    string = re.sub(r'\s+', '_', string)  # Replace multiple spaces with single space
    string = re.sub(r'[^a-z0-9_]+', '', string)  # Remove non-alphanumeric characters except underscore
    string = re.sub(r'_+', '_', string)  # Replace multiple underscores with single underscore
    string = string.strip('_')  # Remove leading/trailing underscores

    return string or None


def splitDate(date, part):
    dates = pd.to_datetime(date, errors="coerce", dayfirst=False)
    if part.lower() == "year":
        return dates.dt.year
    elif part.lower() == "month":
        return dates.dt.month
    elif part.lower() == "day":
        return dates.dt.day
    elif part.lower() == "dayoftheweek":
        return dates.dt.weekday + 1


def getDayOfWeek(value):
    weekdays_num2str = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }
    weekdays_str2num = {v: k for k, v in weekdays_num2str.items()}

    if isinstance(value, pd.Series):
        if pd.api.types.is_numeric_dtype(value):
            return value.map(weekdays_num2str)
        else:
            return value.map(weekdays_str2num)

    if isinstance(value, int):
        return weekdays_num2str.get(value, None)
    elif isinstance(value, str):
        return weekdays_str2num.get(value, None)
    else:
        return None


def parse_duration(value):
    def to_seconds(t):
        if pd.isna(t):
            return None
        s = str(t).strip()
        if s in ("", "\\N", "None"):
            return None
        parts = s.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        elif len(parts) == 1:
            return float(parts[0])
        else:
            return None

    if isinstance(value, pd.Series):
        return value.apply(to_seconds)
    else:
        return to_seconds(value)


def parse_hour(value):
    def to_hour(v):
        if pd.isna(v):
            return None
        s = str(v).strip()
        if s in ("", "\\N", "None"):
            return None
        try:
            t = pd.to_datetime(s, errors="coerce")
            if pd.isna(t):
                parts = s.split(":")
                return int(parts[0]) if parts and parts[0].isdigit() else None
            return t.hour
        except Exception:
            return None

    if isinstance(value, pd.Series):
        return value.apply(to_hour)
    else:
        return to_hour(value)

def applyTransform(rules, df, col):

    if isinstance(rules, dict):
        mapping = rules.get("value", col)
        transforms = rules
    else:
        mapping = rules
        transforms = {}

    if mapping in df.columns:
        series = df[mapping].copy()
    elif col in df.columns:
        series = df[col].copy()
    else:
        raise KeyError(f"Neither '{mapping}' nor '{col}' found in dataframe columns: {list(df.columns)}")

    series = series.apply(convert_to_none)

    if transforms.get("int", False):
        series = pd.to_numeric(series, errors="coerce").astype("Int64")
    if transforms.get("float", False):
        series = pd.to_numeric(series, errors="coerce").astype("float64")
        if "decimals" in transforms:
            decimals = transforms["decimals"]
            if isinstance(decimals, int) and decimals >= 0:
                series = series.round(decimals)

    if transforms.get("normalize_ref", False):
        series = series.apply(normalize_ref)

    if transforms.get("date", False):
        series = splitDate(series, col)
    if transforms.get("day", False):
        series = getDayOfWeek(series)
    if transforms.get("hour", False):
        series = parse_hour(series)
    if transforms.get("duration_sec", False):
        series = parse_duration(series)

    series = series.astype(object).where(pd.notna(series), None)

    return series
