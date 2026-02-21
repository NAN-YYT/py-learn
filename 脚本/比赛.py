import requests
import re
import os
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# =======================
# 基本配置
# =======================
NOWCODER_URL = "https://ac.nowcoder.com/acm/contest/vip-index"
CF_URL = "https://codeforces.com/contests"

CSV_FILE = "比赛.csv"
ICS_FILE = "比赛.ics"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Codeforces 防 403 头
CF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://codeforces.com/",
    "Connection": "keep-alive",
}


# =======================
# 牛客比赛
# =======================
def fetch_nowcoder_contests():
    resp = requests.get(NOWCODER_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    contests = []

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for block in soup.select("div.platform-item-main"):
        title = block.select_one("h4 a")
        time_li = block.select_one("li.match-time-icon")

        if not title or not time_li:
            continue

        name = title.get_text(strip=True)
        link = "https://ac.nowcoder.com" + title["href"]

        text = time_li.get_text(" ", strip=True)
        times = re.findall(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", text)
        duration_match = re.search(r"时长:([^)]+)\)", text)

        if len(times) < 2:
            continue

        start = datetime.strptime(times[0], "%Y-%m-%d %H:%M")
        end = datetime.strptime(times[1], "%Y-%m-%d %H:%M")

        if start < today_start:
            continue

        contests.append({
            "比赛名称": name,
            "平台": "牛客",
            "开始时间": start,
            "结束时间": end,
            "持续时间": duration_match.group(1) if duration_match else "",
            "比赛链接": link
        })

    return contests


# =======================
# Codeforces 比赛
# =======================
def fetch_codeforces_contests():
    try:
        resp = requests.get(CF_URL, headers=CF_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print("❌ Codeforces 抓取失败，已跳过：", e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    contests = []

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for tr in soup.select("tr[data-contestid]"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        name = tds[0].get_text(strip=True)
        contest_id = tr["data-contestid"]
        link = f"https://codeforces.com/contest/{contest_id}"

        time_span = tds[2].select_one("span.format-time")
        if not time_span:
            continue

        try:
            start = datetime.strptime(
                time_span.get_text(strip=True),
                "%b/%d/%Y %H:%M"
            )
        except ValueError:
            continue

        if start < today_start:
            continue

        duration = tds[3].get_text(strip=True)
        parts = duration.split(":")
        h, m = int(parts[0]), int(parts[1])

        end = start + timedelta(hours=h, minutes=m)

        contests.append({
            "比赛名称": name,
            "平台": "Codeforces",
            "开始时间": start,
            "结束时间": end,
            "持续时间": duration,
            "比赛链接": link
        })

    return contests


# =======================
# CSV 保存
# =======================
def save_to_csv(contests):
    if not contests:
        print("⚠️ 没有比赛数据")
        return

    df_new = pd.DataFrame(contests)

    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        df_old = pd.read_csv(CSV_FILE)
        df = pd.concat([df_old, df_new], ignore_index=True)
        df.drop_duplicates(subset=["比赛名称", "开始时间"], inplace=True)
    else:
        df = df_new

    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ CSV 已保存：{CSV_FILE}（{len(df)} 场比赛）")


# =======================
# ICS 生成（颜色区分）
# =======================
def generate_ics(contests):
    def fmt(dt):
        return dt.strftime("%Y%m%dT%H%M%S")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Contest Calendar//CN",
        "CALSCALE:GREGORIAN"
    ]

    for c in contests:
        uid = f"{hash(c['比赛名称'] + str(c['开始时间']))}@contest"

        if c["平台"] == "Codeforces":
            color = "#FF3B30"   # 红色
            category = "Codeforces"
        else:
            color = "#007AFF"   # 蓝色
            category = "NowCoder"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{fmt(datetime.now())}",
            f"DTSTART:{fmt(c['开始时间'])}",
            f"DTEND:{fmt(c['结束时间'])}",
            f"SUMMARY:{c['比赛名称']}（{c['平台']}）",
            f"CATEGORIES:{category}",
            f"COLOR:{color}",
            f"DESCRIPTION:持续时间：{c['持续时间']}\\n链接：{c['比赛链接']}",
            f"URL:{c['比赛链接']}",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📅 ICS 日历文件已生成：{ICS_FILE}")


# =======================
# 主函数
# =======================
def main():
    nowcoder = fetch_nowcoder_contests()
    codeforces = fetch_codeforces_contests()

    contests = nowcoder + codeforces

    print(
        f"🎯 牛客 {len(nowcoder)} 场，"
        f"Codeforces {len(codeforces)} 场，"
        f"总计 {len(contests)} 场"
    )

    save_to_csv(contests)
    generate_ics(contests)


if __name__ == "__main__":
    main()