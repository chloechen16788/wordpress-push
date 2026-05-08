import type { BatchSummary, RecordItem, Task } from "../types";

const API_BASE = "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!resp.ok) {
    throw new Error(`API error ${resp.status}`);
  }
  return (await resp.json()) as T;
}

export const api = {
  listTasks: () => request<Task[]>("/api/tasks"),
  updateTask: (taskId: number, payload: Partial<Task>) =>
    request<Task>(`/api/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listBatches: (taskId: number) =>
    request<BatchSummary[]>(`/api/batches?task_id=${taskId}`),
  listRecords: (batchId: number, status?: string) =>
    request<RecordItem[]>(
      `/api/batches/${batchId}/records${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  runTest: (taskId: number, startTime: string, endTime: string) =>
    request<{ batch_id: number; batch_uuid: string; status: string }>(
      "/api/tasks/run-test",
      {
        method: "POST",
        body: JSON.stringify({
          task_id: taskId,
          start_time: startTime,
          end_time: endTime,
        }),
      },
    ),
  publishBatch: (taskId: number, batchId: number) =>
    request<{ message: string }>("/api/publish/batch", {
      method: "POST",
      body: JSON.stringify({ task_id: taskId, batch_id: batchId }),
    }),
  publishSelected: (taskId: number, batchId: number, publishItemIds: number[]) =>
    request<{ message: string }>("/api/publish/selected", {
      method: "POST",
      body: JSON.stringify({
        task_id: taskId,
        batch_id: batchId,
        publish_item_ids: publishItemIds,
      }),
    }),
  publishItem: (publishItemId: number) =>
    request<{ message: string }>("/api/publish/item", {
      method: "POST",
      body: JSON.stringify({ publish_item_id: publishItemId }),
    }),
  getSourceConfig: () => request<any>("/api/config/source"),
  updateSourceConfig: (payload: any) =>
    request<any>("/api/config/source", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  getLLMConfig: () => request<any>("/api/config/llm"),
  updateLLMConfig: (payload: any) =>
    request<any>("/api/config/llm", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  listPlatforms: () => request<any[]>("/api/config/platforms"),
  createPlatform: (payload: any) =>
    request<any>("/api/config/platforms", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updatePlatform: (id: number, payload: any) =>
    request<any>(`/api/config/platforms/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deletePlatform: (id: number) =>
    request<{ message: string }>(`/api/config/platforms/${id}`, {
      method: "DELETE",
    }),
};

export const apiBase = API_BASE;

