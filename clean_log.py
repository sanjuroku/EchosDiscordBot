from datetime import datetime, timedelta
import re

log_path = "/root/bot-env/EchosDiscordBot/bot.log" 
cutoff_date = datetime.now() - timedelta(days=3)

# 定义低等级日志（需要清理的等级）
low_levels = {"DEBUG", "INFO"}

# 正则匹配
log_line_pattern = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2},\d{3} \[(?P<level>[A-Z]+)\]"
)

retained_lines = []
with open(log_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

i = 0
while i < len(lines):
    line = lines[i]
    match = log_line_pattern.match(line)

    if match:
        # 是一个段落的开始
        log_date = datetime.strptime(match.group("date"), "%Y-%m-%d")
        level = match.group("level")

        # 收集整段
        paragraph = [line]
        i += 1
        while i < len(lines) and not log_line_pattern.match(lines[i]):
            paragraph.append(lines[i])
            i += 1

        # 决定是否保留整段
        if log_date >= cutoff_date:
            retained_lines.extend(paragraph)  # 保留近三天的全部段落
        elif level not in low_levels:
            retained_lines.extend(paragraph)  # 保留旧但重要的（WARNING+）
        # 否则跳过整段（老的 INFO/DEBUG + 附属输出）

    else:
        # 没有起始时间戳的“悬浮行”保留
        retained_lines.append(line)
        i += 1

# 写回精简后的日志
with open(log_path, "w", encoding="utf-8") as f:
    f.writelines(retained_lines)

print(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] bot.log 清理完成：保留了近 3 天和 WARNING 以上等级日志")
