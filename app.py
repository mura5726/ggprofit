import os
import pandas as pd
import altair as alt
import streamlit as st
import re
import dataclasses
import math

from currency_converter import CurrencyConverter
from datetime import datetime, timedelta

# 定数定義
# Buy-in 閾値
BUY_IN_FREEROLL_DSP = 'FREEROLL'
BUY_IN_FREEROLL_RANGE = '($0)'
BUY_IN_MICRO_DSP = 'Micro'
BUY_IN_MICRO_RANGE = '(~$4)'
BUY_IN_LOW_DSP = 'Low'
BUY_IN_LOW_RANGE = '($5~$15)'
BUY_IN_MEDIUM_DSP = 'Medium'
BUY_IN_MEDIUM_RANGE = '($16~$99)'
BUY_IN_HIGH_DSP = 'High'
BUY_IN_HIGH_RANGE = '($100~)'

# 順位閾値
RANK_PAR_FAIR = 'FAIR(15%~)'
RANK_PAR_GOOD = 'GOOD(10%~15%)'
RANK_PAR_VERY_GOOD = 'VERY GOOD(5%~10%)'
RANK_PAR_BEST = 'BEST(~5%)'

# 過去履歴情報
HISTORY_DISPLAY_MAX = 100
HISTORY_DAY_MAX = 180

@dataclasses.dataclass(frozen=True)
class Cols:
    """
    out.csvの列名を、定数として持っておく。
    """
    TOURNAMENT_ID: str = 'Tournament ID'
    TOURNAMENT_NAME: str = 'Tournament Name'
    TOURNAMENT_GAME_TYPE: str = 'Tournament GameType'
    BUY_IN: str = 'Buy-in'
    TOTAL_BUY_IN: str = 'Total Buy-in'
    PRIZE: str = 'Prize'
    START_TIME: str = 'Start Time'
    PLAYERS: str =  'Players'
    TOTAL_PRIZE_POOL: str = 'Total Prize Pool'
    RANK: str = 'Rank'
    ENTRY_COUNT: str = 'Entry Count'
    RANK_PARCENT: str = 'Rank Percent'
    "以下、算出カラム"
    BUY_IN_CATEGORY: str = 'Buy-in Category'
    DAY_OF_WEEK: str = 'Day Of Week'
    TIME_ZONE: str = 'Time Zone'
    RANK_PARCENT_CATEGORY: str = 'Rank Percent Category'
    PROFIT: str = 'Profit'
    CUMULATIVE_PROFIT: str = 'Cumulative Profit'
    RECORD_INDEX: str = 'Record Index'

def get_eur_usd_rate() -> float:
    """
    CurrencyConverter を利用した EUR-USD 為替を取得する関数。
    """
    res0 = CurrencyConverter()
    crate = res0.convert(1, 'EUR', 'USD')
    return round(crate, 2)

def get_cny_usd_rate() -> float:
    """
    CurrencyConverter を利用した CNY-USD 為替を取得する関数。
    """
    res0 = CurrencyConverter()
    crate = res0.convert(1, 'CNY', 'USD')
    return round(crate, 2)

def get_usd_jpy_rate() -> float:
    """
    CurrencyConverter を利用したUSD-JPY 為替を取得する関数。
    """
    res0 = CurrencyConverter()
    crate = res0.convert(1, 'USD', 'JPY')
    return round(crate, 2)

def parse_file(filepath=None, lines=None):
    if filepath:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
    elif lines is None:
        print('Either filepath or lines must be provided.')
        return None

    try:
        line_parts = lines[0].split(', ', 1)
        tournament_id = line_parts[0].split('#')[1].strip()
        line_right_parts = line_parts[1].rsplit(', ', 1)
        tournament_name = line_right_parts[0] if len(line_right_parts) > 1 else 'Unknown'
        tournament_game_type = line_right_parts[1] if len(line_right_parts) > 1 else 'Unknown'
    except IndexError:
        print(f"Could not parse tournament ID or name in {filepath}")
        tournament_id = 'Unknown'
        tournament_name = 'Unknown'
        tournament_game_type = 'Unknown'

    try:
        buy_in_line = lines[1]
        buy_in_parts = re.findall(r'(\$|\€|\¥)([0-9,]+(\.[0-9]{1,2})?)', buy_in_line)
        buy_in = 0.0

        for part in buy_in_parts:

            currency, amount = part[0], part[1]
            amount = float(amount.replace(',', ''))
            if currency == '€':
                amount *= get_eur_usd_rate()
            elif currency == '¥':
                amount *= get_cny_usd_rate()
            buy_in += amount

    except IndexError:
        print(f"Could not parse Buy-in in {filepath}")
        buy_in = 0.0

    try:
        prize_line = lines[-3]
        if 'chips' in prize_line.lower():
            prize = 0.0
        else:
            prize_str = re.search(r'(\$|\€|\¥)([0-9,]+(\.[0-9]{1,2})?)', prize_line).group(2)
            prize = float(prize_str.replace(',', ''))
            if '€' in prize_line:
                prize *= get_eur_usd_rate()
            elif '¥' in prize_line:
                prize *= get_cny_usd_rate()
    except (IndexError, ValueError, AttributeError):
        print(f"Could not parse Prize in {filepath}")
        prize = 0.0

    try:
        players_line = lines[2]
        players = players_line.replace('Players', '')
        players = int(players)
    except IndexError:
        print(f"Could not parse players in {filepath}")
        players = 0

    try:
        total_prize_line = lines[3]
        total_prize = 0.0
        currency = '$'
        # 通貨判定
        if '€' in total_prize_line:
            currency = '€'
        elif '¥' in total_prize_line:
            currency = '¥'

        total_prize = float(total_prize_line.replace('Total Prize Pool: ', '').replace(currency, '').replace(',', ''))
        if currency == '€':
            total_prize *= get_eur_usd_rate()
        elif currency == '¥':
            total_prize *= get_cny_usd_rate()
    except IndexError:
        print(f"Could not parse total prize in {filepath}")
        total_prize = 0

    try:
        rank_line = lines[5]
        rank = rank_line.split(':')[0]
        rank = rank.strip(' ').strip('\n')
        # 順位補正
        rank = rank.replace('1st', '1')
        rank = rank.replace('2nd', '2')
        rank = rank.replace('3rd', '3')
        rank = rank.replace('th', '')

    except IndexError:
        print(f"Could not parse total prize in {filepath}")
        rank = 'Unknown'

    try:
        start_time_line = next((line for line in lines if 'Tournament started' in line), None)
        if start_time_line:
            start_time_match = re.search(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})", start_time_line)
            if start_time_match:
                start_time_str = start_time_match.group(1)
                start_time = pd.to_datetime(start_time_str)
            else:
                print(f"Could not parse Start Time in {filepath}")
                start_time = None
        else:
            print(f"Could not find Start Time line in {filepath}")
            start_time = None
    except (IndexError, ValueError, StopIteration, AttributeError):
        print(f"Could not parse Start Time in {filepath}")
        start_time = None

    try:
        patterns = [
            r"You made (\d+) re-entries",
            r"re-entered (\d+) times",
            r"You made (\d+)-entries"
        ]
        reentry_count = 1  # 初期値（初回のエントリーのみ）
        for pattern in patterns:
            reentry_line = next((line for line in lines if re.search(pattern, line)), None)
            if reentry_line:
                reentry_match = re.search(pattern, reentry_line)
                if reentry_match:
                    reentry_count = int(reentry_match.group(1)) + 1  # リエントリー回数 + 初回のエントリー
                    break
        # else:
        #     print(f"Could not parse re-entry count in {filepath}")

    except (IndexError, ValueError, StopIteration, AttributeError):
        print(f"Could not parse re-entry count in {filepath}")
        reentry_count = 1  # 初回のエントリーのみ

    # リエントリー回数に応じてバイイン金額を更新
    total_buy_in = buy_in * reentry_count

    rank_parcent = 0.0
    if int(prize) > 0:
        rank_parcent = int(rank) / int(players) * 100

    return tournament_id, tournament_name, tournament_game_type, buy_in, total_buy_in, \
            prize, start_time, reentry_count, players, total_prize, rank, rank_parcent

def categorize_buyin(buyin: float) -> str:
    """
    バイインをカテゴリに振り分ける関数
    FREEROLL:$0
    Micro:$0より大きく、$5未満
    Low: $5以上、$15以下
    Medium: $15より大きく、$100未満
    High:$100以上
    """
    if buyin >= 100:
        return BUY_IN_HIGH_DSP
    elif 15 < buyin < 100:
        return BUY_IN_MEDIUM_DSP
    elif 5 <= buyin <= 15:
        return BUY_IN_LOW_DSP
    elif buyin == 0:
        return BUY_IN_FREEROLL_DSP
    else:
        return BUY_IN_MICRO_DSP

def categorize_rank_parcent(rank_parcent: float) -> str:
    """
    バイインをカテゴリに振り分ける関数
    FAIR:15%より大きい
    GOOD: 10%より大きく、15%以下
    VERY GOOD: 5%より大きく、10%以下
    BEST:5%以下
    """
    if rank_parcent == 0:
        return ''
    elif rank_parcent <= 5:
        return RANK_PAR_BEST
    elif 5 < rank_parcent <= 10:
        return RANK_PAR_VERY_GOOD
    elif 10 < rank_parcent <= 15:
        return RANK_PAR_GOOD
    else:
        return RANK_PAR_FAIR

def show_in_the_money_distribution(df: pd.DataFrame) -> None:
    """
    イン・ザ・マネー分配の棒グラフを表示する関数
    """
    # イン・ザ・マネー分配カテゴリの順序を定義
    rank_par_category_order = [RANK_PAR_FAIR, RANK_PAR_GOOD, RANK_PAR_VERY_GOOD, RANK_PAR_BEST]

    # イン・ザ・マネー分配
    IMT_df = df.copy()
    IMT_df = IMT_df[IMT_df[Cols.RANK_PARCENT_CATEGORY] != '']

    # イン・ザ・マネー分配カテゴリ列をCategorical型に変換してカスタム順序を指定
    IMT_df[Cols.RANK_PARCENT_CATEGORY] \
        = pd.Categorical(IMT_df[Cols.RANK_PARCENT_CATEGORY],
                        categories=rank_par_category_order, ordered=True)

    # イン・ザ・マネー分配カテゴリ列でデータフレームを並び替え
    IMT_df.sort_values(by=Cols.BUY_IN_CATEGORY, inplace=True)

    df_target = IMT_df.groupby(Cols.RANK_PARCENT_CATEGORY).count() / len(IMT_df) * 100

    st.subheader('イン・ザ・マネー分配')
    st.bar_chart(df_target['Tournament ID'])

def show_day_of_week(df: pd.DataFrame, non_zero_buyin_df: pd.DataFrame) -> None:
    """
    曜日別集計を表示する関数
    """
    # 曜日別のROIを計算
    daywise_roi = round((non_zero_buyin_df.groupby(Cols.DAY_OF_WEEK)[Cols.PROFIT].sum() / non_zero_buyin_df.groupby(Cols.DAY_OF_WEEK)[Cols.TOTAL_BUY_IN].sum()) * 100, 2)
    daywise_roi = daywise_roi.reset_index()
    daywise_roi = daywise_roi.rename(columns={0: 'ROI'})

    # 曜日別のAv ROIを計算
    daywise_av_roi = round(non_zero_buyin_df.groupby(Cols.DAY_OF_WEEK)['Av ROI'].mean(), 2)
    daywise_av_roi = daywise_av_roi.reset_index()
    daywise_av_roi = daywise_av_roi.rename(columns={0: 'Av ROI'})

    # 曜日の順序を定義
    day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    # 曜日別の参加数
    day_count = df.groupby(Cols.DAY_OF_WEEK).size().reset_index(name='Total Tournaments')

    # 曜日列をCategorical型に変換してカスタム順序を指定
    day_count[Cols.DAY_OF_WEEK] = pd.Categorical(day_count[Cols.DAY_OF_WEEK], categories=day_order, ordered=True)

    # 曜日列でデータフレームを並び替え
    day_count.sort_values(by=Cols.DAY_OF_WEEK, inplace=True)

    # データフレームをマージ
    day_of_week_df_ = pd.merge(day_count, daywise_roi, on=Cols.DAY_OF_WEEK)
    day_of_week_df = pd.merge(day_of_week_df_, daywise_av_roi, on=Cols.DAY_OF_WEEK)

    # インデックスを変更
    day_of_week_df.set_index(Cols.DAY_OF_WEEK, inplace=True)

    # 曜日別集計
    st.subheader('曜日別集計')
    st.dataframe(day_of_week_df)

def show_time_zone(df: pd.DataFrame, non_zero_buyin_df: pd.DataFrame) -> None:
    """
    時間帯別集計を表示する関数
    """
    # 時間帯別のROIを計算
    timewise_roi = round((non_zero_buyin_df.groupby(Cols.TIME_ZONE)[Cols.PROFIT].sum() / non_zero_buyin_df.groupby(Cols.TIME_ZONE)[Cols.TOTAL_BUY_IN].sum()) * 100, 2)
    timewise_roi = timewise_roi.reset_index()
    timewise_roi = timewise_roi.rename(columns={0: 'ROI'})

    # 時間帯別のAv ROIを計算
    timewise_av_roi = round(non_zero_buyin_df.groupby(Cols.TIME_ZONE)['Av ROI'].mean(), 2)
    timewise_av_roi = timewise_av_roi.reset_index()
    timewise_av_roi = timewise_av_roi.rename(columns={0: 'Av ROI'})

    # 時間帯別の参加数
    time_zone_count = df.groupby(Cols.TIME_ZONE).size().reset_index(name='Total Tournaments')

    # データフレームをマージ
    time_zone_df_ = pd.merge(time_zone_count, timewise_roi, on=Cols.TIME_ZONE)
    time_zone_df = pd.merge(time_zone_df_, timewise_av_roi, on=Cols.TIME_ZONE)

    # インデックスを変更
    time_zone_df.set_index(Cols.TIME_ZONE, inplace=True)

    # 時間帯別集計
    st.subheader('時間帯別集計')
    st.dataframe(time_zone_df)

def show_tournament_history(df: pd.DataFrame, day_max: int, display_max: int) -> pd.DataFrame:
    """
    直近のトーナメント成績を表示する関数
    """
    # Tournament History
    # 現在の日付からday_max日前の日付を計算
    dt_6months_ago = datetime.now() - timedelta(days=day_max)
    # 直近のトーナメント成績をフィルタリング
    history_df = df[df[Cols.START_TIME] >= dt_6months_ago]
    # トーナメント開始時間の降順ソート
    history_df.sort_values(Cols.START_TIME, ascending=False, inplace=True)

    # 表示件数オーバしている場合
    if len(history_df) > display_max:
        # 表示件数を抽出
        history_df = history_df.iloc[0:display_max -1, :]

    # インデックスを変更
    history_df.set_index(Cols.TOURNAMENT_ID, inplace=True)

    st.subheader('Tournament History')
    st.dataframe(history_df)

    # Export df
    history_df.to_csv('history.csv')

    return history_df

def show_buy_in_breakdown(df: pd.DataFrame) -> None:
    """
    バイインの内訳を表示する関数
    """
    # グループ化してトーナメント数をカウント
    buyin_tournament_count_df = df.groupby(Cols.BUY_IN_CATEGORY).size().reset_index(name='Tournaments Count')

    # グループ化して合計獲得賞金を集計
    buyin_prize_df = df.groupby(Cols.BUY_IN_CATEGORY).agg({Cols.PRIZE: 'sum'}).reset_index()
    # 列名をリネーム
    buyin_prize_df.rename(columns={Cols.PRIZE: 'Total Prize'}, inplace=True)

    # インマネ数をカウント
    buyin_profit_df = df[df[Cols.PROFIT] > 0]
    buyin_ITM_df = buyin_profit_df.groupby(Cols.BUY_IN_CATEGORY).size().reset_index(name='ITM Count')

    # データフレームをマージ
    buyin_beakdown_ = pd.merge(buyin_ITM_df, buyin_tournament_count_df, on=Cols.BUY_IN_CATEGORY)
    buyin_beakdown = pd.merge(buyin_beakdown_, buyin_prize_df, on=Cols.BUY_IN_CATEGORY)

    # インマネ率を算出
    buyin_beakdown['IMT(%)'] = round(buyin_beakdown['ITM Count'] / buyin_beakdown['Tournaments Count'] * 100, 2)

    # バイインカテゴリの順序を定義
    buyin_category_order = [BUY_IN_FREEROLL_DSP, BUY_IN_MICRO_DSP, BUY_IN_LOW_DSP, BUY_IN_MEDIUM_DSP, BUY_IN_HIGH_DSP]

    loc_count = 10
    for category in buyin_category_order:
        if category not in buyin_beakdown.values:
            buyin_beakdown.loc[str(loc_count)] = [category, 0, 0, 0, 0]
            loc_count += 1

    # バイインカテゴリ列をCategorical型に変換してカスタム順序を指定
    buyin_beakdown[Cols.BUY_IN_CATEGORY] = pd.Categorical(buyin_beakdown[Cols.BUY_IN_CATEGORY], categories=buyin_category_order, ordered=True)

    # バイインカテゴリ列でデータフレームを並び替え
    buyin_beakdown.sort_values(by=Cols.BUY_IN_CATEGORY, inplace=True)

    # インデックスを変更
    buyin_beakdown.set_index(Cols.BUY_IN_CATEGORY, inplace=True)

    list_1 = []
    for i in range(len(buyin_category_order)):
        list_1.append(str(buyin_beakdown.iloc[i, 3]) + '% (' + str(buyin_beakdown.iloc[i, 0]) + ' / ' + str(buyin_beakdown.iloc[i, 1]) + ')')

    list_2 = []
    for i in range(len(buyin_category_order)):
        list_2.append('$' + str(round(buyin_beakdown.iloc[i, 2], 2)))

    df_tm = pd.DataFrame(columns=buyin_category_order)
    df_tm.loc['イン ザ マネー %'] = list_1
    df_tm.loc['合計賞金'] = list_2

    # バイインの内訳
    st.subheader('バイインの内訳')
    st.write(BUY_IN_FREEROLL_DSP + BUY_IN_FREEROLL_RANGE.replace('$', '\$').replace('~', '\~') + ' '
        + BUY_IN_MICRO_DSP + BUY_IN_MICRO_RANGE.replace('$', '\$').replace('~', '\~') + ' '
        + BUY_IN_LOW_DSP + BUY_IN_LOW_RANGE.replace('$', '\$').replace('~', '\~') + ' '
        + BUY_IN_MEDIUM_DSP + BUY_IN_MEDIUM_RANGE.replace('$', '\$').replace('~', '\~') + ' '
        + BUY_IN_HIGH_DSP + BUY_IN_HIGH_RANGE.replace('$', '\$').replace('~', '\~'))
    st.dataframe(df_tm)

# Initialize DataFrame with dtype
# Tournament Name column added for demonstration. Please populate it correctly.
df = pd.DataFrame(columns=[
    Cols.TOURNAMENT_ID,
    Cols.TOURNAMENT_NAME,
    Cols.TOURNAMENT_GAME_TYPE,
    Cols.BUY_IN,
    Cols.TOTAL_BUY_IN,
    Cols.PRIZE,
    Cols.START_TIME,
    Cols.PLAYERS,
    Cols.TOTAL_PRIZE_POOL,
    Cols.RANK,
    Cols.ENTRY_COUNT,
    Cols.RANK_PARCENT
    ], dtype=object)

# Directory where the text files are stored (please adjust this path accordingly)
directory_path = './tournaments/'

try:
    for filename in os.listdir(directory_path):
        if filename.endswith('.txt'):
            filepath = os.path.join(directory_path, filename)
            tournament_id, tournament_name, tournament_game_type, buy_in, total_buy_in, \
            prize, start_time, entry_count, players, total_prize, rank, rank_parcent = parse_file(filepath)
            new_row = pd.DataFrame({
                Cols.TOURNAMENT_ID: [tournament_id],
                Cols.TOURNAMENT_NAME: [tournament_name],
                Cols.TOURNAMENT_GAME_TYPE: [tournament_game_type],
                Cols.BUY_IN: [buy_in],
                Cols.TOTAL_BUY_IN: [total_buy_in],
                Cols.PRIZE: [prize],
                Cols.START_TIME: [start_time],
                Cols.PLAYERS: [players],
                Cols.TOTAL_PRIZE_POOL: [total_prize],
                Cols.RANK: [rank],
                Cols.ENTRY_COUNT: [entry_count],
                Cols.RANK_PARCENT: [rank_parcent]
                },  dtype=object)
            df = pd.concat([df, new_row], ignore_index=True)

except Exception as e:
    print(f"An error occurred while reading files from {directory_path}: {e}")

# Convert columns to the correct dtype
df[Cols.BUY_IN] = df[Cols.BUY_IN].astype(float)
df[Cols.TOTAL_BUY_IN] = df[Cols.TOTAL_BUY_IN].astype(float)
df[Cols.PRIZE] = df[Cols.PRIZE].astype(float)

# Calculate 'In The Money' ratio
itm_count = len(df[df[Cols.PRIZE] > 0])
total_entries = df[Cols.ENTRY_COUNT].sum()
itm_ratio = (itm_count / total_entries) * 100 if total_entries > 0 else 0

# Sort df by Start Time
df[Cols.START_TIME] = pd.to_datetime(df[Cols.START_TIME])
df.sort_values(Cols.START_TIME, inplace=True)

# バイインカテゴリ列を追加
df[Cols.BUY_IN_CATEGORY] = df[Cols.BUY_IN].apply(categorize_buyin)

# 曜日列を追加
df[Cols.DAY_OF_WEEK] = df[Cols.START_TIME].dt.strftime('%a')

# 時間帯列を追加
df[Cols.TIME_ZONE] = df[Cols.START_TIME].dt.strftime('%H')

# 順位カテゴリ列を追加
df[Cols.RANK_PARCENT_CATEGORY] = df[Cols.RANK_PARCENT].apply(categorize_rank_parcent)

# Calculate Profit and Cumulative Profit
df[Cols.PROFIT] = df[Cols.PRIZE] - df[Cols.TOTAL_BUY_IN]
df[Cols.CUMULATIVE_PROFIT] = df[Cols.PROFIT].cumsum()

# ROI
df['Av ROI'] = df[Cols.PROFIT] / df[Cols.TOTAL_BUY_IN] * 100

# Add record index for plotting
df[Cols.RECORD_INDEX] = df.reset_index().index

# Export df
df.to_csv('out.csv')

# Streamlit display
st.title('Poker Tournament Profit Tracker')

# File uploader
uploaded_files = st.file_uploader('Choose txt files', type=['txt'], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        # File content can be read here and parsed accordingly
        content = uploaded_file.read().decode()
        lines = content.splitlines()

        # File parsing (ここで先ほどのparse_file関数を使います)
        tournament_id, tournament_name, tournament_game_type, buy_in, total_buy_in,
        prize, start_time, entry_count, players, total_prize, rank, rank_parcent = parse_file(lines=lines)

        # Append data to existing dataframe
        new_row = pd.DataFrame({
            Cols.TOURNAMENT_ID: [tournament_id],
            Cols.TOURNAMENT_NAME: [tournament_name],
            Cols.TOURNAMENT_GAME_TYPE: [tournament_game_type],
            Cols.BUY_IN: [buy_in],
            Cols.TOTAL_BUY_IN: [total_buy_in],
            Cols.PRIZE: [prize],
            Cols.START_TIME: [start_time],
            Cols.PLAYERS: [players],
            Cols.TOTAL_PRIZE_POOL: [total_prize],
            Cols.RANK: [rank],
            Cols.ENTRY_COUNT: [entry_count],
            Cols.RANK_PARCENT: [rank_parcent]
        }, dtype=object)
        df = pd.concat([df, new_row], ignore_index=True)

    # Sort df by Start Time
    df[Cols.START_TIME] = pd.to_datetime(df[Cols.START_TIME])
    df.sort_values(Cols.START_TIME, inplace=True)

    # Calculate Profit and Cumulative Profit
    df[Cols.PROFIT] = df[Cols.PRIZE] - df[Cols.TOTAL_BUY_IN]
    df[Cols.CUMULATIVE_PROFIT] = df[Cols.PROFIT].cumsum()

    # ROI
    df['Av ROI'] = df[Cols.PROFIT] / df[Cols.TOTAL_BUY_IN] * 100

    # Add record index for plotting
    df[Cols.RECORD_INDEX] = df.reset_index().index

    # Export df
    df.to_csv('out.csv')

# Arrange Date and Buy-in filters in a row
col_01, col_02, col_03 = st.columns(3)
col_11, col_12 = st.columns(2)
col_31, col_32, col_33 = st.columns(3)

if df.empty:
    st.warning('No data to display.')
    st.image('howtouse.png', caption='How to use this app')
else:

    # Date range filter
    default_since = df[Cols.START_TIME].min().date()
    default_until = df[Cols.START_TIME].max().date()
    since = col_01.date_input('Since', min_value=df[Cols.START_TIME].min().date(), max_value=df[Cols.START_TIME].max().date(), value=default_since)
    until = col_02.date_input('Until', min_value=df[Cols.START_TIME].min().date(), max_value=df[Cols.START_TIME].max().date(), value=default_until)

    # Buy-in slider filter
    min_buyin = 0
    max_buyin = df[Cols.BUY_IN].max()
    selected_buyin_range = col_11.slider('Buy-in Range', int(min_buyin), int(math.ceil(max_buyin)), (int(min_buyin), int(math.ceil(max_buyin))))

    # Players slider filter
    min_players = 0
    max_players = df[Cols.PLAYERS].max()
    selected_players_range = col_03.slider('Players Range', int(min_players), int(max_players), (int(min_players), int(max_players)))

    # Tournament tag filter
    TAGS = [
        'JOPT',
        'WSOP',
        'GGMasters',
        'Zodiac',
        'Step to',
        'Mega to',
        'Last Chance to',
        'Global MILLION',
        'Turbo',
        'Hyper',
        'Bounty',
        'WSOPC',
        '#',
        'Seats',
        'Flip & Go',
        'Builder',
        'Freeroll',
        'school',
        'ThanksGG Flipout'
        ]
    selected_tournament_tags = col_31.multiselect('Tournament Tags', TAGS, default=[])

    # Buy-in tag filter
    Buy_IN_TAGS = [
        BUY_IN_FREEROLL_DSP,
        BUY_IN_MICRO_DSP,
        BUY_IN_LOW_DSP,
        BUY_IN_MEDIUM_DSP,
        BUY_IN_HIGH_DSP
        ]
    selected_buy_in_tags = col_12.multiselect('Buy-in Tags'
        + '  \n'
        + BUY_IN_FREEROLL_DSP + BUY_IN_FREEROLL_RANGE.replace('$', '\$').replace('~', '\~')
        + BUY_IN_MICRO_DSP + BUY_IN_MICRO_RANGE.replace('$', '\$').replace('~', '\~')
        + '\n'
        + BUY_IN_LOW_DSP + BUY_IN_LOW_RANGE.replace('$', '\$').replace('~', '\~')
        + BUY_IN_MEDIUM_DSP + BUY_IN_MEDIUM_RANGE.replace('$', '\$').replace('~', '\~')
        + BUY_IN_HIGH_DSP + BUY_IN_HIGH_RANGE.replace('$', '\$').replace('~', '\~'),
        Buy_IN_TAGS, default=[])

    # Select Game Type
    game_type_list= df.drop_duplicates(subset=Cols.TOURNAMENT_GAME_TYPE)[Cols.TOURNAMENT_GAME_TYPE].to_list()
    game_type_list.insert(0, '')
    selected_game_type = col_33.selectbox('Tournament GameType', options=game_type_list)

    # Apply filters
    filtered_df = df[(df[Cols.START_TIME].dt.date >= since) & (df[Cols.START_TIME].dt.date <= until)]
    filtered_df = filtered_df[(filtered_df[Cols.BUY_IN] >= selected_buyin_range[0]) & (filtered_df[Cols.BUY_IN] <= selected_buyin_range[1])]
    filtered_df = filtered_df[(filtered_df[Cols.PLAYERS] >= selected_players_range[0]) & (filtered_df[Cols.PLAYERS] <= selected_players_range[1])]
    filtered_df = filtered_df[filtered_df[Cols.TOURNAMENT_NAME].str.contains('|'.join(selected_tournament_tags))]
    filtered_df = filtered_df[filtered_df[Cols.BUY_IN_CATEGORY].str.contains('|'.join(selected_buy_in_tags))]
    if selected_game_type != '':
        filtered_df = filtered_df[filtered_df[Cols.TOURNAMENT_GAME_TYPE] == selected_game_type]

    # Recalculate Cumulative Profit
    filtered_df.sort_values(Cols.START_TIME, inplace=True)
    filtered_df[Cols.CUMULATIVE_PROFIT] = filtered_df[Cols.PROFIT].cumsum()

    # Choose X-axis
    x_axis_choice = col_32.selectbox('Choose X-axis', ['Start Time', 'Record Index'])

    # Reset index if Record Index is the chosen x-axis
    if x_axis_choice == 'Record Index':
        filtered_df[Cols.RECORD_INDEX] = filtered_df.reset_index().index

    # If filtered_df is empty, display a message
    if filtered_df.empty:
        st.warning('No data to display.')
        st.image('howtouse.png', caption='How to use this app')
    else:
        # Generate the chart with the filtered data
        chart = alt.Chart(filtered_df, width=600, height=400).mark_line().encode(
            x=alt.X(f'{x_axis_choice}:Q' if x_axis_choice == 'Record Index' else f'{x_axis_choice}:T', title=x_axis_choice),
            y=alt.Y('Cumulative Profit:Q', title='Cumulative Profit'),
            tooltip=[
                alt.Tooltip('Tournament ID:N', title='Tournament ID'),
                alt.Tooltip('Tournament Name:N', title='Tournament Name'),
                alt.Tooltip('Start Time:T', title='Start Time'),
                alt.Tooltip('Cumulative Profit:Q', title='Cumulative Profit')]
        ).properties(
            width=600,
            height=400
        ).interactive()

        st.write(chart)

        # バイインが0でない場合のみでフィルタリング
        non_zero_buyin_df = filtered_df[filtered_df[Cols.BUY_IN] != 0]

        # ROIが計算可能な場合のみ平均を計算
        if not non_zero_buyin_df.empty:
            avg_roi = ((non_zero_buyin_df[Cols.PROFIT] / non_zero_buyin_df[Cols.TOTAL_BUY_IN]) * 100).mean()
        else:
            avg_roi = 0  # または 'N/A', 何も計算できない場合

        # Additional stats below the graph
        st.write('### Statistics')
        st.write(f"Total Tournaments: {len(filtered_df)}")
        st.write(f"Total Prize: \${filtered_df[Cols.PRIZE].sum():.2f}（{filtered_df[Cols.PRIZE].sum() * get_usd_jpy_rate():,.0f}円）")
        st.write(f"Total Entries: {filtered_df[Cols.ENTRY_COUNT].sum()}")
        st.write(f"Average Profit: \${filtered_df[Cols.PROFIT].mean():.2f}（{filtered_df[Cols.PROFIT].mean() * get_usd_jpy_rate():,.0f}円）")
        st.write(f"Average Buy-in: \${filtered_df[Cols.BUY_IN].mean():.2f}（{filtered_df[Cols.BUY_IN].mean() * get_usd_jpy_rate():,.0f}円）")
        st.write(f"In The Money (%): {itm_ratio:.2f}%")
        st.write(f"Average ROI: {avg_roi:.2f}%")  # 修正された行
        st.write(f"Total Profit: \${filtered_df[Cols.PROFIT].sum():.2f}（{filtered_df[Cols.PROFIT].sum() * get_usd_jpy_rate():,.0f}円）")
        st.write(f"※exchange rate €1 = \${get_eur_usd_rate()}  1元 =  \${get_cny_usd_rate()} $1 = {get_usd_jpy_rate()}円")

        # イン・ザ・マネー分配
        show_in_the_money_distribution(filtered_df)

        # 曜日別
        show_day_of_week(filtered_df, non_zero_buyin_df)

        # 時間帯別
        show_time_zone(filtered_df, non_zero_buyin_df)

        # Tournament History
        history_df = show_tournament_history(filtered_df, HISTORY_DAY_MAX, HISTORY_DISPLAY_MAX)

        # バイインの内訳
        show_buy_in_breakdown(history_df)

# 画面の下部にTwitterリンクを追加
st.markdown(
    """
    ---

    Follow me on X: [kacchimu](https://twitter.com/kacchimu)
    """,
    unsafe_allow_html=True,
)
