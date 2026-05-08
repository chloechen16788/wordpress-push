import { useEffect } from "react";

import { apiBase } from "../services/api";

type StreamHandlers = {
  onBatchProgress?: (data: any) => void;
  onItemStatus?: (data: any) => void;
  onPlatformStatus?: (data: any) => void;
  onBatchDone?: (data: any) => void;
};

export function useStream(
  taskId: number | null,
  batchId: number | null,
  handlers: StreamHandlers,
) {
  useEffect(() => {
    if (!taskId || !batchId) return;
    const source = new EventSource(
      `${apiBase}/api/stream?task_id=${taskId}&batch_id=${batchId}`,
    );
    source.addEventListener("batch_progress", (event) => {
      handlers.onBatchProgress?.(JSON.parse((event as MessageEvent).data));
    });
    source.addEventListener("item_status", (event) => {
      handlers.onItemStatus?.(JSON.parse((event as MessageEvent).data));
    });
    source.addEventListener("platform_status", (event) => {
      handlers.onPlatformStatus?.(JSON.parse((event as MessageEvent).data));
    });
    source.addEventListener("batch_done", (event) => {
      handlers.onBatchDone?.(JSON.parse((event as MessageEvent).data));
    });
    return () => source.close();
  }, [taskId, batchId]);
}

