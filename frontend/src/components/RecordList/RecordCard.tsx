import { useMemo, useState } from "react";

import type { RecordItem } from "../../types";

function statusClass(status: string): string {
  if (status === "published") return "tag tag-ok";
  if (status === "ready_to_publish") return "tag tag-pending";
  if (status === "publishing") return "tag tag-running";
  if (status === "noise") return "tag";
  return "tag tag-failed";
}

type Props = {
  item: RecordItem;
  selected: boolean;
  showPublishActions: boolean;
  onToggleSelect: (checked: boolean) => void;
  onPublishOne: () => void;
};

export function RecordCard({
  item,
  selected,
  showPublishActions,
  onToggleSelect,
  onPublishOne,
}: Props) {
  const [expandedOriginal, setExpandedOriginal] = useState(false);
  const [expandedEdited, setExpandedEdited] = useState(false);
  const titleCandidates = useMemo(
    () => [item.headline_1, item.headline_2, item.headline_3].filter(Boolean) as string[],
    [item.headline_1, item.headline_2, item.headline_3],
  );

  return (
    <article className="record-card">
      <header className="record-head">
        <div className="row">
          {showPublishActions ? (
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => onToggleSelect(e.target.checked)}
            />
          ) : null}
          <div>
          <div className="mono">ID: {item.original_id}</div>
          <div className="subtle">{new Date(item.fetched_at).toLocaleString()}</div>
          </div>
        </div>
        <div className={statusClass(item.publish_status)}>{item.publish_status}</div>
      </header>

      <section className="dual">
        <div className="pane">
          <h4>原始稿件</h4>
          <div className="title">{item.original_title}</div>
          {item.thumbnail_url ? <img className="thumb" src={item.thumbnail_url} alt="" /> : null}
          <p
            className={!expandedOriginal ? "clamp" : ""}
            onClick={() => setExpandedOriginal((v) => !v)}
          >
            {item.original_body}
          </p>
        </div>
        <div className="pane">
          <h4>AI 改写</h4>
          <div className="category-row">
            <span className="category-label">分类标签</span>
            <span className="category-chip">{item.industry_category || "未分类"}</span>
          </div>
          <div className="title">{item.headline_1 || item.original_title}</div>
          {titleCandidates.length > 0 ? (
            <ul className="headline-list">
              {titleCandidates.map((h, idx) => (
                <li key={idx}>{h}</li>
              ))}
            </ul>
          ) : null}
          <p
            className={!expandedEdited ? "clamp" : ""}
            onClick={() => setExpandedEdited((v) => !v)}
          >
            {item.edited_article || "当前为噪音或未生成改写内容"}
          </p>
        </div>
      </section>

      <footer className="record-foot">
        <span>判定理由：{item.adoption_reason || "-"}</span>
        <div className="platforms">
          {item.platform_statuses.map((ps) => (
            <a
              key={`${item.source_record_id}-${ps.platform_id}-${ps.wp_post_id ?? "noid"}`}
              className={statusClass(ps.status)}
              href={ps.preview_url || "#"}
              target="_blank"
              rel="noreferrer"
            >
              {ps.platform_name}:{ps.status}
            </a>
          ))}
          {showPublishActions && item.publish_item_id ? (
            <button className="btn-mini" onClick={onPublishOne}>
              单条发布
            </button>
          ) : null}
        </div>
      </footer>
    </article>
  );
}

