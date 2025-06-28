#!/bin/bash

echo "********** 尝试关闭已有的Screen **********"
screen -S bot -X quit 2>/dev/null

echo "********** Git pull最新代码 **********"
git pull

echo "********** 启动Screen(bot),并运行bot **********"
screen -dmS bot python3 main.py

echo "********** 当前运行的Screen **********"
screen -ls

echo "********** 显示bot实时日志 **********"
tail -f bot.log
