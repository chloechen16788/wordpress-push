import type { RecordItem } from "../../types";
import { RecordCard } from "./RecordCard";

type Props = {
  items: RecordItem[];
  selectedIds: number[];
  onToggleSelect: (publishItemId: number, checked: boolean) => void;
  onPublishOne: (publishItemId: number) => void;
};

export function RecordList({
  items,
  selectedIds,
  onToggleSelect,
  onPublishOne,
}: Props) {
  if (items.length === 0) {
    return <div className="empty">当前批次暂无记录</div>;
  }
  return (
    <div className="record-list">
      {items.map((item) => (
        <RecordCard
          key={item.source_record_id}
          item={item}
          selected={Boolean(item.publish_item_id && selectedIds.includes(item.publish_item_id))}
          onToggleSelect={(checked) => {
            if (!item.publish_item_id) return;
            onToggleSelect(item.publish_item_id, checked);
          }}
          onPublishOne={() => {
            if (!item.publish_item_id) return;
            onPublishOne(item.publish_item_id);
          }}
        />
      ))}
    </div>
  );
}

