#!/bin/bash
# 自动提取 Git 提交记录并按作者统计贡献，用于人员权重说明填写

echo "### 近期提交统计 (前 50 条)"
git log -n 50 --pretty=format:"%h - %an, %ar : %s"

echo -e "\n### 作者贡献度排名 (按提交数)"
git shortlog -sn --all --since="2 weeks ago"
