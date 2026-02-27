#!/usr/bin/env python
"""
scripts/batch_ingest.py
批量入库往年文档 CLI 脚本

用法示例：
  python scripts/batch_ingest.py --dir ./往年作业 --term 春季 --year 2024
  python scripts/batch_ingest.py --file ./需求规格说明书.pdf --project_id projA --term 夏季
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.ingest import ingest_file, ingest_directory
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="批量入库往年 PDF/DOCX 文档")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dir", help="批量入库目录路径")
    group.add_argument("--file", help="入库单个文件路径")

    parser.add_argument("--project_id", default=None, help="项目 ID（可选，自动推断）")
    parser.add_argument("--term", default=None, help="春季 / 夏季（可选）")
    parser.add_argument("--year", type=int, default=None, help="年份（可选）")
    parser.add_argument("--report", default=None, help="输出报告 JSON 路径（可选）")

    args = parser.parse_args()
    kwargs = {
        "project_id": args.project_id,
        "term": args.term,
        "year": args.year,
    }

    if args.file:
        report = ingest_file(args.file, **kwargs)
        reports = [report]
    else:
        reports = ingest_directory(args.dir, **kwargs)

    # 汇总统计
    total_chunks = sum(r.get("chunks_inserted", 0) for r in reports)
    total_review = sum(r.get("needs_review_count", 0) for r in reports)
    logger.info(f"全部完成：{len(reports)} 个文件，{total_chunks} 个 chunks，{total_review} 个待人工复核")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        logger.info(f"报告已写入：{args.report}")
    else:
        print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
