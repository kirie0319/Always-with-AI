import csv
from bs4 import BeautifulSoup

# ファイルパス
html_path = "templates/financial/components/lifeplan_simulation.html"
csv_path = "AI-FP.xlsx - LPS（現在)(開発用）.csv"

# CSVデータを辞書に格納
csv_data = {}
with open(csv_path, encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        if not row or not row[0].strip():
            continue  # 空行やラベルなしはスキップ
        label = row[0].strip()
        values = [v.strip() for v in row[1:]]
        csv_data[label] = values

# HTMLを読み込み
with open(html_path, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# tbody内のすべてのtrを取得
for tbody in soup.find_all("tbody"):
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        label = tds[0].get_text(strip=True).replace("　", "")  # 全角スペース除去
        if label in csv_data:
            # 1列目以外をCSVデータで上書き
            for i in range(1, 67):
                value = csv_data[label][i-1] if i-1 < len(csv_data[label]) else ""
                if i < len(tds):
                    tds[i].string = value
                else:
                    new_td = soup.new_tag("td", attrs={"class": "financial-data-cell"})
                    new_td.string = value
                    tr.append(new_td)
            # 67個より多い場合は余分を削除
            for td in tds[67:]:
                td.decompose()
        else:
            # 67個に揃えるだけ
            td_count = len(tds)
            if td_count < 67:
                for _ in range(67 - td_count):
                    new_td = soup.new_tag("td", attrs={"class": "financial-data-cell"})
                    tr.append(new_td)
            elif td_count > 67:
                for td in tds[67:]:
                    td.decompose()

# 上書き保存
with open(html_path, "w", encoding="utf-8") as f:
    f.write(str(soup))

print("CSVデータをHTMLに反映し、全てのtrのtd数を67個に揃えました。")