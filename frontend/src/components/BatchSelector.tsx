import type { BatchSummary } from "../types";

type Props = {
  batches: BatchSummary[];
  currentBatchId: number | null;
  onChange: (batchId: number) => void;
};

export function BatchSelector({ batches, currentBatchId, onChange }: Props) {
  return (
    <select
      className="input"
      value={currentBatchId ?? ""}
      onChange={(e) => onChange(Number(e.target.value))}
    >
      {batches.map((batch) => (
        <option key={batch.id} value={batch.id}>
          #{batch.batch_uuid} ({batch.status})
        </option>
      ))}
    </select>
  );
}

