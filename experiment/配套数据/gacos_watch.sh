#!/bin/bash
# GACOS 自动轮询 v2：指数退避间隔（30s→1m→2m→5m→10m→30m→保持30m）
cd /d/work/data/配套数据
INTERVALS=(30 60 120 300 600 1800)
while [ $(ls GACOS/*.ztd 2>/dev/null | wc -l) -lt 77 ]; do
  PYTHONIOENCODING=utf-8 python gacos_email.py >> gacos_watch.log 2>&1
  n=$(ls GACOS/*.ztd 2>/dev/null | wc -l)
  echo "--- $(date '+%H:%M:%S') 当前 ztd: $n/77 ---" >> gacos_watch.log
  # 指数退避：用已轮询次数选间隔
  idx=$(( ${#INTERVALS[@]} - 1 ))
  for i in $(seq 0 $((${#INTERVALS[@]}-1))); do
    if [ $n -lt $(( 20*(i+1) )) ]; then idx=$i; break; fi
  done
  sleep ${INTERVALS[$idx]}
done
echo "=== $(date '+%H:%M:%S') GACOS 全部 77 个 ztd 收齐！===" >> gacos_watch.log
