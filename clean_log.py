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
keep = False  # 标记当前行是否在保留段中（用于多行情况）

with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        match = log_line_pattern.match(line)
        if match:
            log_date = datetime.strptime(match.group("date"), "%Y-%m-%d")
            level = match.group("level")

            if log_date >= cutoff_date:
                retained_lines.append(line)  # 保留近三天的所有日志
                keep = True  # 开启保留段（近三天）
            elif level not in low_levels:
                retained_lines.append(line)  # 保留高等级日志（WARNING以上）
                keep = True  # 保留高等级
            else:
                keep = False  # 不保留
        else:
            if keep:
                # 属于上面那行的延续（如异常堆栈、print输出），继续保留
                retained_lines.append(line)
            # 否则：孤立的旧内容，忽略

# 写回精简后的日志
with open(log_path, "w", encoding="utf-8") as f:
    f.writelines(retained_lines)

print("✅ bot.log 清理完成：保留了近 3 天和 WARNING 以上等级日志")
