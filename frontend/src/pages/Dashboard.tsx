import { useEffect, useMemo, useState } from "react";

import { BatchSelector } from "../components/BatchSelector";
import { ConfigPanel } from "../components/ConfigPanel";
import { PublishControls } from "../components/PublishControls";
import { RecordList } from "../components/RecordList";
import { StatsCards } from "../components/StatsCards";
import { useStream } from "../hooks/useStream";
import { api } from "../services/api";
import type { BatchSummary, RecordItem, Task } from "../types";

export function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [mode, setMode] = useState<"auto" | "manual">("manual");
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [activeBatchId, setActiveBatchId] = useState<number | null>(null);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [publishing, setPublishing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [runningTest, setRunningTest] = useState(false);
  const [tab, setTab] = useState<"pending" | "published">("pending");
  const [selectedItemIds, setSelectedItemIds] = useState<number[]>([]);
  const [publishIntervalHours, setPublishIntervalHours] = useState<number | null>(null);
  const [sourceConfig, setSourceConfig] = useState({
    amp_host: "",
    amp_port: 3460,
    amp_user: "",
    amp_password: "",
    amp_database: "media",
  });
  const [llmConfig, setLLMConfig] = useState({
    provider: "mock",
    model: "gpt-4.1-mini",
    system_prompt: "",
  });
  const [platforms, setPlatforms] = useState<any[]>([]);

  const activeBatch = useMemo(
    () => batches.find((b) => b.id === activeBatchId) ?? null,
    [batches, activeBatchId],
  );
  const currentTask = useMemo(
    () => tasks.find((t) => t.id === activeTaskId) ?? null,
    [tasks, activeTaskId],
  );

  useEffect(() => {
    const t = tasks.find((x) => x.id === activeTaskId);
    if (t) {
      setMode(t.mode);
      setPublishIntervalHours(t.publish_interval_hours ?? null);
    }
  }, [activeTaskId, tasks]);

  useEffect(() => {
    api.listTasks().then((rows) => {
      setTasks(rows);
      if (rows.length > 0) {
        setActiveTaskId(rows[0].id);
        setMode(rows[0].mode);
        setPublishIntervalHours(rows[0].publish_interval_hours ?? null);
      }
    });
    Promise.all([api.getSourceConfig(), api.getLLMConfig(), api.listPlatforms()])
      .then(([source, llm, ps]) => {
        setSourceConfig((prev) => ({
          ...prev,
          amp_host: source.amp_host,
          amp_port: source.amp_port,
          amp_user: source.amp_user,
          amp_database: source.amp_database,
        }));
        setLLMConfig({
          provider: llm.provider,
          model: llm.model,
          system_prompt: llm.system_prompt,
        });
        setPlatforms(ps);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!activeTaskId) return;
    api.listBatches(activeTaskId).then((rows) => {
      setBatches(rows);
      if (rows.length > 0) setActiveBatchId(rows[0].id);
    });
  }, [activeTaskId]);

  useEffect(() => {
    if (!activeBatchId) return;
    const status = tab === "published" ? "published" : undefined;
    api.listRecords(activeBatchId, status).then((rows) => {
      if (tab === "pending") {
        setRecords(rows.filter((x) => x.publish_status !== "published"));
      } else {
        setRecords(rows);
      }
      setSelectedItemIds([]);
    });
  }, [activeBatchId, tab]);

  useStream(activeTaskId, activeBatchId, {
    onBatchProgress: (data) => {
      setPublishing(true);
      setProgress(data.percent ?? 0);
    },
    onBatchDone: () => {
      setPublishing(false);
      setProgress(100);
      if (activeTaskId) {
        api.listBatches(activeTaskId).then(setBatches);
      }
      if (activeBatchId) {
        const status = tab === "published" ? "published" : undefined;
        api.listRecords(activeBatchId, status).then((rows) => {
          if (tab === "pending") {
            setRecords(rows.filter((x) => x.publish_status !== "published"));
          } else {
            setRecords(rows);
          }
        });
      }
    },
  });

  return (
    <div className="layout">
      <ConfigPanel
        mode={mode}
        onModeChange={setMode}
        publishIntervalHours={publishIntervalHours}
        onPublishIntervalChange={setPublishIntervalHours}
        sourceConfig={sourceConfig}
        onSourceChange={setSourceConfig}
        llmConfig={llmConfig}
        onLLMChange={setLLMConfig}
        platforms={platforms}
        onPlatformsUpdated={setPlatforms}
        onSaveAll={async () => {
          if (!activeTaskId) return;
          await api.updateTask(activeTaskId, {
            mode,
            publish_interval_hours: publishIntervalHours,
          });
          await api.updateSourceConfig(sourceConfig);
          await api.updateLLMConfig(llmConfig);
          const updatedTasks = await api.listTasks();
          setTasks(updatedTasks);
          alert("配置已保存");
        }}
        runningTest={runningTest}
        onRunTest={async (start, end) => {
          if (!activeTaskId) return;
          try {
            setRunningTest(true);
            const out = await api.runTest(activeTaskId, start, end);
            await api.listBatches(activeTaskId).then((rows) => {
              setBatches(rows);
              setActiveBatchId(out.batch_id);
            });
            await api.listRecords(out.batch_id).then(setRecords);
            setTab("pending");
            alert(`采集与改写完成，生成批次 #${out.batch_id}`);
          } finally {
            setRunningTest(false);
          }
        }}
      />

      <main className="main">
        <header className="toolbar">
          <h2>发稿任务：{currentTask?.name ?? "自动新闻转写分发系统"}</h2>
          <div className="row">
            <BatchSelector
              batches={batches}
              currentBatchId={activeBatchId}
              onChange={setActiveBatchId}
            />
            <PublishControls
              mode={mode}
              loading={publishing}
              progress={progress}
              onBatchPublish={async () => {
                if (!activeTaskId || !activeBatchId) return;
                const readySelectedIds = records
                  .filter(
                    (r) =>
                      r.publish_item_id &&
                      selectedItemIds.includes(r.publish_item_id) &&
                      r.publish_status === "ready_to_publish",
                  )
                  .map((r) => r.publish_item_id!) as number[];
                if (readySelectedIds.length === 0) {
                  alert("请先勾选要发布的条目");
                  return;
                }
                setPublishing(true);
                setProgress(0);
                await api.publishSelected(activeTaskId, activeBatchId, readySelectedIds);
                alert(`已触发批量发布，共 ${readySelectedIds.length} 条`);
              }}
            />
          </div>
        </header>
        <StatsCards
          batchId={activeBatchId ?? undefined}
          rawCount={activeBatch?.raw_count ?? 0}
          rewrittenCount={activeBatch?.rewritten_count ?? 0}
          publishedCount={activeBatch?.published_count ?? 0}
        />
        <div className="tabbar">
          <button
            className={`tab-btn ${tab === "pending" ? "active" : ""}`}
            onClick={() => setTab("pending")}
          >
            本批次待审结果
          </button>
          <button
            className={`tab-btn ${tab === "published" ? "active" : ""}`}
            onClick={() => setTab("published")}
          >
            已发布历史
          </button>
          <label className="check-all">
            <input
              type="checkbox"
              checked={
                records.filter((r) => r.publish_item_id && r.publish_status === "ready_to_publish")
                  .length > 0 &&
                records
                  .filter((r) => r.publish_item_id && r.publish_status === "ready_to_publish")
                  .every((r) => selectedItemIds.includes(r.publish_item_id!))
              }
              onChange={(e) => {
                const readyIds = records
                  .filter((r) => r.publish_item_id && r.publish_status === "ready_to_publish")
                  .map((r) => r.publish_item_id!) as number[];
                if (e.target.checked) setSelectedItemIds(readyIds);
                else setSelectedItemIds([]);
              }}
            />
            全选本页
          </label>
        </div>
        <RecordList
          items={records}
          selectedIds={selectedItemIds}
          onToggleSelect={(publishItemId, checked) => {
            setSelectedItemIds((prev) =>
              checked ? [...new Set([...prev, publishItemId])] : prev.filter((x) => x !== publishItemId),
            );
          }}
          onPublishOne={async (publishItemId) => {
            await api.publishItem(publishItemId);
            setPublishing(true);
            setProgress(0);
          }}
        />
      </main>
    </div>
  );
}

