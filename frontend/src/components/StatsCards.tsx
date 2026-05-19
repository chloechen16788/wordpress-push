type Props = {
  batchId?: number;
  rawCount: number;
  rewrittenCount: number;
  publishedCount: number;
};

export function StatsCards({
  batchId,
  rawCount,
  rewrittenCount,
  publishedCount,
}: Props) {
  const cvr = rawCount > 0 ? `${((publishedCount / rawCount) * 100).toFixed(1)}%` : "0.0%";
  return (
    <div className="stats-grid">
      <div className="card">
        <div className="label">当前批次</div>
        <div className="value">#{batchId ?? "-"}</div>
      </div>
      <div className="card">
        <div className="label">待发布</div>
        <div className="value">{rewrittenCount}</div>
      </div>
      <div className="card">
        <div className="label">已发布</div>
        <div className="value">
          {publishedCount} <span className="sub">CVR {cvr}</span>
        </div>
      </div>
    </div>
  );
}

