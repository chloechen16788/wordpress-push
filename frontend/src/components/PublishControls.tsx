type Props = {
  mode: "auto" | "manual";
  loading: boolean;
  progress: number;
  onBatchPublish: () => void;
};

export function PublishControls({ mode, loading, progress, onBatchPublish }: Props) {
  if (mode !== "manual") return null;
  return (
    <button
      className="btn btn-primary"
      onClick={() => {
        if (confirm("确认批量发布当前批次 ready_to_publish 条目吗？")) {
          void onBatchPublish();
        }
      }}
      disabled={loading}
    >
      {loading ? `发布中 ${progress}%` : "批量发布"}
    </button>
  );
}

