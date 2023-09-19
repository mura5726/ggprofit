import os
import pandas as pd
import altair as alt
import streamlit as st
import re

def parse_file(filepath=None, lines=None):
    if filepath:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.splitlines()
    elif lines is None:
        print("Either filepath or lines must be provided.")
        return None

    try:
        line_parts = lines[0].split(", ", 1)
        tournament_id = line_parts[0].split("#")[1].strip()
        line_right_parts = line_parts[1].rsplit(", ", 1)
        tournament_name = line_right_parts[0] if len(line_right_parts) > 1 else "Unknown"
        tournament_game_type = line_right_parts[1] if len(line_right_parts) > 1 else "Unknown"
    except IndexError:
        print(f"Could not parse tournament ID or name in {filepath}")
        tournament_id = "Unknown"
        tournament_name = "Unknown"
        tournament_game_type = "Unknown"

    try:
        buy_in_line = lines[1]
        buy_in_parts = re.findall(r'(\$|\€|\¥)([0-9,]+(\.[0-9]{1,2})?)', buy_in_line)
        buy_in = 0.0
        for part in buy_in_parts:
            currency, amount = part[0], part[1]
            amount = float(amount.replace(',', ''))
            if currency == "€":
                amount *= 1.18
            elif currency == "¥":
                amount *= 0.15
            buy_in += amount
    except IndexError:
        print(f"Could not parse Buy-in in {filepath}")
        buy_in = 0.0

    try:
        earning_line = lines[-3]
        if "chips" in earning_line.lower():
            earning = 0.0
        else:
            earning_str = re.search(r'(\$|\€|\¥)([0-9,]+(\.[0-9]{1,2})?)', earning_line).group(2)
            earning = float(earning_str.replace(',', ''))
            if '€' in earning_line:
                earning *= 1.18
            elif '¥' in earning_line:
                earning *= 0.15
    except (IndexError, ValueError, AttributeError):
        print(f"Could not parse Earning in {filepath}")
        earning = 0.0

    try:
        players_line = lines[2]
        players = players_line.replace('Players', '')
        players = players.strip(' ').strip('\n')
        players = int(players)
    except IndexError:
        print(f"Could not parse players in {filepath}")
        players = 0

    try:
        total_prize_line = lines[3]
        total_prize = total_prize_line.replace('Total Prize Pool: $', '')
        total_prize = total_prize.strip(' ').strip('\n')
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
        else:
            print(f"Could not parse re-entry count in {filepath}")

    except (IndexError, ValueError, StopIteration, AttributeError):
        print(f"Could not parse re-entry count in {filepath}")
        reentry_count = 1  # 初回のエントリーのみ

    buy_in *= reentry_count  # リエントリー回数に応じてバイイン金額を更新

    return tournament_id, tournament_name, tournament_game_type, buy_in, earning, start_time, reentry_count, players, total_prize, rank

# Initialize DataFrame with dtype
# Tournament Name column added for demonstration. Please populate it correctly.
df = pd.DataFrame(columns=['Tournament ID', 'Tournament Name', 'Tournament GameType', 'Buy-in', 'Earning', 'Start Time', 'Players', 'Total Prize Pool' 'Rank', 'Entry Count'], dtype=object)

# Directory where the text files are stored (please adjust this path accordingly)
directory_path = "./tournaments/"

try:
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory_path, filename)
            parse_result = parse_file(filepath=filepath)

            if parse_result is not None:
                tournament_id, tournament_name, tournament_game_type, buy_in, earning, start_time, entry_count, players, total_prize, rank = parse_file(filepath=filepath)
                new_row = pd.DataFrame({
                    'Tournament ID': [tournament_id],
                    'Tournament Name': [tournament_name],
                    'Tournament GameType': [tournament_game_type],
                    'Buy-in': [buy_in], 'Earning': [earning],
                    'Start Time': [start_time],
                    'Players': [players],
                    'Total Prize Pool': [total_prize],
                    'Rank': [rank],
                    'Entry Count': [entry_count]}, dtype=object)
                df = pd.concat([df, new_row], ignore_index=True)

except Exception as e:
    print(f"An error occurred while reading files from {directory_path}: {e}")

# Convert columns to the correct dtype
df['Buy-in'] = df['Buy-in'].astype(float)
df['Earning'] = df['Earning'].astype(float)

# Calculate 'In The Money' ratio
itm_count = len(df[df['Earning'] > 0])
total_entries = df['Entry Count'].sum()
itm_ratio = (itm_count / total_entries) * 100 if total_entries > 0 else 0


# Sort df by Start Time
df['Start Time'] = pd.to_datetime(df['Start Time'])
df = df.sort_values('Start Time')

# Calculate Profit and Cumulative Profit
df['Profit'] = df['Earning'] - df['Buy-in']
df['Cumulative Profit'] = df['Profit'].cumsum()

# Add record index for plotting
df['Record Index'] = df.reset_index().index

# Export df
df.to_csv('out.csv')

# Streamlit display
st.title("Poker Tournament Profit Tracker")

# File uploader
uploaded_files = st.file_uploader("Choose txt files", type=["txt"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        # File content can be read here and parsed accordingly
        content = uploaded_file.read().decode()
        lines = content.splitlines()

        # File parsing (ここで先ほどのparse_file関数を使います)
        tournament_id, tournament_name, tournament_game_type, buy_in, earning, start_time, entry_count, players, total_prize, rank = parse_file(lines=lines)

        # Append data to existing dataframe
        new_row = pd.DataFrame({
            'Tournament ID': [tournament_id],
            'Tournament Name': [tournament_name],
            'Tournament GameType': [tournament_game_type],
            'Buy-in': [buy_in],
            'Earning': [earning],
            'Start Time': [start_time],
            'Players': [players],
            'Total Prize Pool': [total_prize],
            'Rank': [rank],
            'Entry Count': [entry_count]
        }, dtype=object)
        df = pd.concat([df, new_row], ignore_index=True)

    # Sort df by Start Time
    df['Start Time'] = pd.to_datetime(df['Start Time'])
    df = df.sort_values('Start Time')

    # Calculate Profit and Cumulative Profit
    df['Profit'] = df['Earning'] - df['Buy-in']
    df['Cumulative Profit'] = df['Profit'].cumsum()

    # Add record index for plotting
    df['Record Index'] = df.reset_index().index

    # Export df
    df.to_csv('out.csv')

# Arrange Date and Buy-in filters in a row
col1, col2, col3, col7 = st.columns(4)
col4, col5, col6 = st.columns(3)

if df.empty:
    st.write("No data to display.")
    st.image('howtouse.png', caption='How to use this app')
else:

    # Date range filter
    default_since = df['Start Time'].min().date()
    default_until = df['Start Time'].max().date()
    since = col1.date_input("Since", min_value=df['Start Time'].min().date(), max_value=df['Start Time'].max().date(), value=default_since)
    until = col2.date_input("Until", min_value=df['Start Time'].min().date(), max_value=df['Start Time'].max().date(), value=default_until)

    # Buy-in slider filter
    min_buyin = 0
    max_buyin = df['Buy-in'].max()
    selected_buyin_range = col3.slider("Buy-in Range", int(min_buyin), int(max_buyin), (int(min_buyin), int(max_buyin)))

    # Players slider filter
    min_players = 0
    max_players = df['Players'].max()
    selected_players_range = col7.slider('Players Range', int(min_players), int(max_players), (int(min_players), int(max_players)))

    # Tournament tag filter
    TAGS = ["JOPT", "WSOP", "GGMasters", "Zodiac", "Step to", "Mega to", 
    "Last Chance to", "Global MILLION", "Turbo", "Hyper", "Bounty",
    "WSOPC", "#", "Seats", "Flip & Go"]
    selected_tags = col4.multiselect("Tournament Tags", TAGS, default=[])

    # Select Game Type
    game_type_list= df.drop_duplicates(subset='Tournament GameType')['Tournament GameType'].to_list()
    game_type_list.insert(0, '')
    selected_game_type = col6.selectbox('Tournament GameType', options=game_type_list)

    # Apply filters
    filtered_df = df[(df['Start Time'].dt.date >= since) & (df['Start Time'].dt.date <= until)]
    filtered_df = filtered_df[(filtered_df['Buy-in'] >= selected_buyin_range[0]) & (filtered_df['Buy-in'] <= selected_buyin_range[1])]
    filtered_df = filtered_df[filtered_df['Tournament Name'].str.contains('|'.join(selected_tags))]
    if selected_game_type != '':
        filtered_df = filtered_df[filtered_df['Tournament GameType'] == selected_game_type]

    # Recalculate Cumulative Profit
    filtered_df = filtered_df.sort_values('Start Time')
    filtered_df['Cumulative Profit'] = filtered_df['Profit'].cumsum()


    # Choose X-axis
    x_axis_choice = col5.selectbox("Choose X-axis", ["Start Time", "Record Index"])

    # Reset index if Record Index is the chosen x-axis
    if x_axis_choice == 'Record Index':
        filtered_df['Record Index'] = filtered_df.reset_index().index

    # If filtered_df is empty, display a message
    if filtered_df.empty:
        st.write("No data to display.")
        st.image('howtouse.png', caption='How to use this app')
    else:
        # Generate the chart with the filtered data
        chart = alt.Chart(filtered_df, width=600, height=400).mark_line().encode(
            x=alt.X(f'{x_axis_choice}:Q' if x_axis_choice == "Record Index" else f'{x_axis_choice}:T', title=x_axis_choice),
            y=alt.Y('Cumulative Profit:Q', title='Cumulative Profit'),
            tooltip=[alt.Tooltip('Tournament ID:N', title='Tournament ID'),
                     alt.Tooltip('Tournament Name:N', title='Tournament Name'),
                     alt.Tooltip('Start Time:T', title='Start Time'),
                     alt.Tooltip('Cumulative Profit:Q', title='Cumulative Profit')]
        ).properties(
            width=600,
            height=400
        ).interactive()

        st.write(chart)

        # バイインが0でない場合のみでフィルタリング
        non_zero_buyin_df = filtered_df[filtered_df['Buy-in'] != 0]

        # ROIが計算可能な場合のみ平均を計算
        if not non_zero_buyin_df.empty:
            avg_roi = ((non_zero_buyin_df['Profit'] / non_zero_buyin_df['Buy-in']) * 100).mean()
        else:
            avg_roi = 0  # または 'N/A', 何も計算できない場合

        # Additional stats below the graph
        st.write("### Statistics")
        st.write(f"Total Tournaments: {len(filtered_df)}")
        st.write(f"Total Entries: {filtered_df['Entry Count'].sum()}")
        st.write(f"Average Profit: {filtered_df['Profit'].mean():.2f}")
        st.write(f"Average Buy-in: {filtered_df['Buy-in'].mean():.2f}")
        st.write(f"In The Money (%): {itm_ratio:.2f}%")
        st.write(f"Average ROI: {avg_roi:.2f}%")  # 修正された行
        st.write(f"Total Profit: {filtered_df['Profit'].sum():.2f}")

# 画面の下部にTwitterリンクを追加
st.markdown(
    """
    ---

    Follow me on X: [kacchimu](https://twitter.com/kacchimu)
    """,
    unsafe_allow_html=True,
)