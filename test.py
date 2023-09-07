import pandas as pd
import re

def parse_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.splitlines()

    try:
        tournament_id = lines[0].split(", ")[0].split("#")[1].strip()
    except IndexError:
        print(f"Could not parse tournament ID in {filepath}")
        tournament_id = "Unknown"

    try:
        buy_in_parts = lines[1].split(": ")[1].split("+")
        buy_in = sum(float(part.replace('$', '')) for part in buy_in_parts)
    except IndexError:
        print(f"Could not parse Buy-in in {filepath}")
        buy_in = 0.0

    try:
        earning_line = lines[-3]
        earning_str = re.search(r'\$([0-9]+\.[0-9]{2})', earning_line).group(1)
        earning = float(earning_str)
    except (IndexError, ValueError):
        print(f"Could not parse Earning in {filepath}")
        earning = 0.0

    profit = earning - buy_in

    return pd.DataFrame([{
        'Tournament ID': tournament_id, 
        'Buy-in': buy_in, 
        'Earning': earning, 
        'Profit': profit
    }])


# テスト用のテキストファイルの場所（適切に変更してください）
filepath = 'tournaments/GG20230906 - Tournament #103083445 - T Builder 2.txt'

df = parse_file(filepath)
print(df)
