import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymysql


def resolve_path(raw: str, cwd: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else cwd / path


def load_state(path: Path) -> Dict[str, Any]:
    """读取分页游标状态文件；不存在时返回初始状态。"""
    if not path.exists():
        return {
            "cursor_create_time": None,
            "cursor_story_id": None,
            "total_fetched": 0,
        }
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: Path, state: Dict[str, Any]) -> None:
    """持久化分页游标状态，用于断点续拉。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def append_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """将一批记录追加写入 JSONL。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def build_sql(
    has_start: bool,
    has_end: bool,
    has_cursor: bool,
) -> str:
    """按参数动态拼接 SQL 条件。

    说明：
    - transmission_id 长度=15：过滤目标稿件
    - transmission_id 包含 ZH：限制中文站点稿件
    - 排除 NOT_SEND_CN_MAINLAND：过滤不发中国大陆稿件
    - send_website_flag=1：仅取可发站点稿件
    - 时间窗：按 start/end 过滤
    - 游标：按 create_time + story_id 倒序翻页，避免重复/漏数
    """
    where_parts: List[str] = [
        "LENGTH(s.transmission_id) = 15",
        "s.transmission_id LIKE %s",
        "s.special_flag != %s",
        "s.send_website_flag = %s",
    ]
    if has_start:
        where_parts.append("s.create_time >= %s")
    if has_end:
        where_parts.append("s.create_time <= %s")
    if has_cursor:
        where_parts.append("(s.create_time < %s OR (s.create_time = %s AND s.story_id < %s))")

    where_sql = " AND ".join(where_parts)

    return f"""
SELECT
    s.story_id,
    s.story_number,
    s.transmission_id,
    s.headline,
    s.create_time,
    c.content_text,
    f.file_url
FROM media_stories s
LEFT JOIN media_story_content c ON s.story_id = c.story_id
LEFT JOIN (
    SELECT
        mf.obj_id,
        SUBSTRING_INDEX(
            GROUP_CONCAT(mf.file_url ORDER BY mf.file_id ASC SEPARATOR ','),
            ',',
            1
        ) AS file_url
    FROM media_files mf
    GROUP BY mf.obj_id
) f ON s.story_id = f.obj_id
WHERE {where_sql}
ORDER BY s.create_time DESC, s.story_id DESC
LIMIT %s
""".strip()


def fetch_batch(
    conn: pymysql.connections.Connection,
    start_time: Optional[str],
    end_time: Optional[str],
    cursor_create_time: Optional[str],
    cursor_story_id: Optional[int],
    batch_size: int,
) -> List[Dict[str, Any]]:
    """查询一页 AMP 稿件数据。"""
    has_cursor = bool(cursor_create_time and cursor_story_id is not None)
    sql = build_sql(
        has_start=bool(start_time),
        has_end=bool(end_time),
        has_cursor=has_cursor,
    )
    params: List[Any] = ["%ZH%", "NOT_SEND_CN_MAINLAND", 1]  # 与 build_sql 中 %s 的顺序保持一致
    if start_time:
        params.append(start_time)
    if end_time:
        params.append(end_time)
    if has_cursor:
        params.extend([cursor_create_time, cursor_create_time, cursor_story_id])
    params.append(batch_size)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将 SQL 原始字段映射为系统统一字段结构。"""
    out: List[Dict[str, Any]] = []
    for row in rows:
        create_time = row.get("create_time")
        if isinstance(create_time, datetime):
            create_time_str = create_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            create_time_str = str(create_time) if create_time is not None else None

        content_text = row.get("content_text") or ""
        out.append(
            {
                "story_id": row.get("story_id"),
                "story_number": row.get("story_number"),
                "nm_transmission_id": row.get("transmission_id"),
                "title": row.get("headline"),
                "content_text": content_text,
                "content_html": content_text,
                "image_url": row.get("file_url"),
                "create_time": create_time_str,
            }
        )
    return out


def parse_args() -> argparse.Namespace:
    """命令行参数定义。"""
    parser = argparse.ArgumentParser(description="Fetch AMP stories into JSONL.")
    parser.add_argument("--host", default=os.getenv("PRESS_AMP_HOST", "139.198.21.183"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PRESS_AMP_PORT", "3460")))
    parser.add_argument("--user", default=os.getenv("PRESS_AMP_USER", "prnqa"))
    parser.add_argument("--password", default=os.getenv("PRESS_AMP_PASSWORD", ""))
    parser.add_argument("--database", default=os.getenv("PRESS_AMP_DATABASE", "media"))
    parser.add_argument("--start-time", default=None, help="YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--end-time", default=None, help="YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-rows", type=int, default=0, help="0 means no max limit")
    parser.add_argument("--output", default="output/amp_stories.jsonl")
    parser.add_argument("--state", default="state/amp_fetch_state.json")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue from state cursor and append to output.",
    )
    parser.add_argument(
        "--reset-output",
        action="store_true",
        help="Remove existing output file before fetch.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI 入口：分页拉取 AMP 数据并保存 JSONL 与状态文件。"""
    args = parse_args()
    if not args.password:
        raise SystemExit("AMP password is required. Use --password or set PRESS_AMP_PASSWORD.")
    cwd = Path.cwd()
    output_path = resolve_path(args.output, cwd)
    state_path = resolve_path(args.state, cwd)

    # --resume 时从状态文件续跑；否则从头开始。
    state = load_state(state_path) if args.resume else {
        "cursor_create_time": None,
        "cursor_story_id": None,
        "total_fetched": 0,
    }

    if args.reset_output and output_path.exists():
        output_path.unlink()

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=8,
        read_timeout=20,
        write_timeout=20,
    )

    fetched_total = 0  # 本次运行累计抓取数（与状态文件中的历史累计区分）
    try:
        while True:
            rows = fetch_batch(
                conn=conn,
                start_time=args.start_time,
                end_time=args.end_time,
                cursor_create_time=state.get("cursor_create_time"),
                cursor_story_id=state.get("cursor_story_id"),
                batch_size=args.batch_size,
            )
            if not rows:
                break

            normalized = normalize_rows(rows)
            append_jsonl(output_path, normalized)

            # 使用最后一条记录更新游标，下一页继续按倒序往后翻。
            last = rows[-1]
            cursor_time = last.get("create_time")
            if isinstance(cursor_time, datetime):
                cursor_time_str = cursor_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                cursor_time_str = str(cursor_time) if cursor_time is not None else None

            state["cursor_create_time"] = cursor_time_str
            state["cursor_story_id"] = last.get("story_id")
            state["total_fetched"] = int(state.get("total_fetched", 0)) + len(rows)
            save_state(state_path, state)

            fetched_total += len(rows)
            print(
                f"Fetched {len(rows)} rows, total_in_this_run={fetched_total}, "
                f"cursor=({state['cursor_create_time']}, {state['cursor_story_id']})"
            )

            # 命中上限后提前结束，避免单次抓取过大。
            if args.max_rows > 0 and fetched_total >= args.max_rows:
                print(f"Reached max rows limit: {args.max_rows}")
                break
    finally:
        conn.close()

    print(
        f"Done. output={output_path}, fetched_in_this_run={fetched_total}, "
        f"state_total_fetched={state.get('total_fetched', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
