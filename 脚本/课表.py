import re
from datetime import datetime, timedelta

# =======================
# ① 学期第一周第一天（周一）
# =======================
SEMESTER_START_DATE = "2026-03-02"  # YYYY-MM-DD

# =======================
# ② 节次时间表
# =======================
PERIOD_TIME = {
    1: ("08:30", "09:15"),
    2: ("09:25", "10:10"),
    3: ("10:20", "11:05"),
    4: ("11:15", "12:00"),
    5: ("14:10", "14:55"),
    6: ("15:05", "15:50"),
    7: ("16:00", "16:45"),
    8: ("16:55", "17:40"),
    9: ("19:00", "19:45"),
    10: ("19:55", "20:40"),
    11: ("20:50", "21:35"),
}

# =======================
# ③ 原始课表文本（当前格式）
# =======================
RAW_TEXT = """
学科前沿讲座	信息与管理科学学院	1-4	讲授	司彦飞	周一(3-4节)	许昌C409
机器学习	信息与管理科学学院	1-12	讲授	尚旭鹏	周三(1-2节)	许昌C403
机器学习 信息与管理科学学院	1-12	实验	尚旭鹏	周三(3-4节)	A406
大数据开发技术（Ⅱ） 信息与管理科学学院	1-12	讲授	段博文	周二(1-2节)	许昌B402
大数据开发技术（Ⅱ） 信息与管理科学学院	1-16	实验	段博文	周二(3-4节)	A404
大数据开发技术（Ⅱ） 信息与管理科学学院	13-16	实验	段博文	周二(1-2节)	A404
大数据项目管理与案例分析 信息与管理科学学院	9-16	讲授	赵博文	周三(5-6节)	许昌C404
大数据项目管理与案例分析选 信息与管理科学学院	9-16	实验	赵博文	周三(7-8节)	A406
形势与政策Ⅵ 马克思主义学院	14-15	讲授	刘琳	周四(7-8节)	许昌C405
"""

# =======================
# 工具函数
# =======================
def parse_weeks(text):
    nums = list(map(int, re.findall(r"\d+", text)))
    if len(nums) != 2:
        return []
    return list(range(nums[0], nums[1] + 1))


def weekday_to_index(text):
    mapping = {
        "周一": 0,
        "周二": 1,
        "周三": 2,
        "周四": 3,
        "周五": 4,
        "周六": 5,
        "周日": 6,
    }
    for k, v in mapping.items():
        if k in text:
            return v
    return None


# =======================
# 核心解析（✔ 完全匹配当前格式）
# =======================
def parse_courses(text):
    semester_start = datetime.strptime(SEMESTER_START_DATE, "%Y-%m-%d")
    events = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 提取字段
        week_match = re.search(r"\d+-\d+", line)
        time_match = re.search(r"周[一二三四五六日]\(\d+-\d+节\)", line)

        if not week_match or not time_match:
            continue

        week_text = week_match.group()
        time_text = time_match.group()

        # 课程名 = 周次前的内容（去掉学院名）
        course = line[:week_match.start()].strip().split()[0]

        # 教师 = “讲授 / 实验” 后面的名字
        teacher_match = re.search(r"(讲授|实验)\s*([\u4e00-\u9fa5]+)", line)
        teacher = teacher_match.group(2) if teacher_match else ""

        # 地点 = 最后一个字段
        location = line.split()[-1]

        weekday_index = weekday_to_index(time_text)
        periods = list(map(int, re.findall(r"\d+", time_text)))

        if weekday_index is None or not periods:
            continue

        start_p, end_p = periods[0], periods[-1]
        start_time, _ = PERIOD_TIME[start_p]
        _, end_time = PERIOD_TIME[end_p]

        for w in parse_weeks(week_text):
            date = semester_start + timedelta(days=(w - 1) * 7 + weekday_index)

            events.append({
                "course": course,
                "date": date,
                "start": start_time,
                "end": end_time,
                "teacher": teacher,
                "location": location,
            })

    return events


# =======================
# 生成 ICS
# =======================
def generate_ics(events, filename="课表.ics"):
    def fmt(dt):
        return dt.strftime("%Y%m%dT%H%M%S")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Course Calendar//CN",
        "CALSCALE:GREGORIAN",
    ]

    for e in events:
        start_dt = datetime.strptime(
            f"{e['date'].strftime('%Y-%m-%d')} {e['start']}",
            "%Y-%m-%d %H:%M",
        )
        end_dt = datetime.strptime(
            f"{e['date'].strftime('%Y-%m-%d')} {e['end']}",
            "%Y-%m-%d %H:%M",
        )

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{hash(str(e))}@course",
            f"DTSTAMP:{fmt(datetime.now())}",
            f"DTSTART:{fmt(start_dt)}",
            f"DTEND:{fmt(end_dt)}",
            f"SUMMARY:{e['course']}",
            f"DESCRIPTION:教师：{e['teacher']}\\n地点：{e['location']}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =======================
# 生成 CSV（中文列名）
# =======================
def generate_csv(events, filename="课表.csv"):
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    lines = ["课程名称,日期,星期,开始时间,结束时间,教师,地点"]

    for e in events:
        lines.append(
            f"{e['course']},"
            f"{e['date'].strftime('%Y-%m-%d')},"
            f"{weekday_map[e['date'].weekday()]},"
            f"{e['start']},"
            f"{e['end']},"
            f"{e['teacher']},"
            f"{e['location']}"
        )

    with open(filename, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


# =======================
# 主入口
# =======================
if __name__ == "__main__":
    events = parse_courses(RAW_TEXT)
    print(f"生成课程事件数：{len(events)}")

    generate_ics(events)
    print("✅ 已生成 courses.ics")

    generate_csv(events)
    print("✅ 已生成 courses.csv")