import { useState } from "react";

import { api } from "../../services/api";

function toDatetimeLocalValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function getLast24HoursRange(): { start: string; end: string } {
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  return { start: toDatetimeLocalValue(start), end: toDatetimeLocalValue(end) };
}

type SourceConfig = {
  amp_host: string;
  amp_port: number;
  amp_user: string;
  amp_password: string;
  amp_database: string;
};

type LLMConfig = {
  provider: string;
  model: string;
  system_prompt: string;
};

type PlatformItem = {
  id: number;
  name: string;
  site_url: string;
  auth_type: string;
  username: string;
  is_active: boolean;
};

type Props = {
  mode: "auto" | "manual";
  onModeChange: (mode: "auto" | "manual") => void;
  publishIntervalHours: number | null;
  onPublishIntervalChange: (value: number | null) => void;
  onRunTest: (start: string, end: string) => void;
  sourceConfig: SourceConfig;
  onSourceChange: (value: SourceConfig) => void;
  llmConfig: LLMConfig;
  onLLMChange: (value: LLMConfig) => void;
  platforms: PlatformItem[];
  onPlatformsUpdated: (rows: PlatformItem[]) => void;
  onSaveAll: () => void;
  runningTest: boolean;
  showSourceConfig: boolean;
};

export function ConfigPanel({
  mode,
  onModeChange,
  publishIntervalHours,
  onPublishIntervalChange,
  onRunTest,
  sourceConfig,
  onSourceChange,
  llmConfig,
  onLLMChange,
  platforms,
  onPlatformsUpdated,
  onSaveAll,
  runningTest,
  showSourceConfig,
}: Props) {
  const defaultRange = getLast24HoursRange();
  const [startTime, setStartTime] = useState(defaultRange.start);
  const [endTime, setEndTime] = useState(defaultRange.end);
  const [addingPlatform, setAddingPlatform] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSiteUrl, setNewSiteUrl] = useState("");
  const [newAuthType, setNewAuthType] = useState<"rest_app_password" | "cookie_nonce">(
    "rest_app_password",
  );
  const [newUsername, setNewUsername] = useState("");
  const [newSecret, setNewSecret] = useState("");
  const [platformBusy, setPlatformBusy] = useState(false);

  async function refreshPlatforms() {
    const rows = await api.listPlatforms();
    onPlatformsUpdated(rows);
  }

  async function handleAddPlatform() {
    if (!newName.trim() || !newSiteUrl.trim() || !newUsername.trim() || !newSecret.trim()) {
      alert("请填写平台名称、站点链接、用户名与密钥/密码");
      return;
    }
    setPlatformBusy(true);
    try {
      await api.createPlatform({
        name: newName.trim(),
        site_url: newSiteUrl.trim(),
        auth_type: newAuthType,
        username: newUsername.trim(),
        secret: newSecret,
        is_active: true,
      });
      setNewName("");
      setNewSiteUrl("");
      setNewUsername("");
      setNewSecret("");
      setAddingPlatform(false);
      await refreshPlatforms();
      alert("已添加发布平台");
    } catch {
      alert("添加失败，请检查网络与后端日志");
    } finally {
      setPlatformBusy(false);
    }
  }

  async function handleDeletePlatform(id: number) {
    if (!confirm("确定删除该平台配置？")) return;
    setPlatformBusy(true);
    try {
      await api.deletePlatform(id);
      await refreshPlatforms();
    } catch {
      alert("删除失败（若已有发布记录则不允许删除）");
    } finally {
      setPlatformBusy(false);
    }
  }

  const authLabel = (t: string) =>
    t === "cookie_nonce" ? "浏览器登录" : "REST 应用密码";

  return (
    <aside className="left-panel oc-card panel">
      <h3 className="panel-title">执行策略配置</h3>
      {runningTest ? (
        <div className="running-banner" role="status" aria-live="polite">
          <span className="spinner" />
          <span>任务执行中，请稍候（正在采集并调用改写模型）...</span>
        </div>
      ) : null}

      <div className="field">
        <label className="label-title">发布模式</label>
        <div className="grid-two">
          <label className={`mode-option ${mode === "auto" ? "active" : ""}`}>
            <input
              type="radio"
              checked={mode === "auto"}
              onChange={() => onModeChange("auto")}
            />
            自动发布
          </label>
          <label className={`mode-option ${mode === "manual" ? "active" : ""}`}>
            <input
              type="radio"
              checked={mode === "manual"}
              onChange={() => onModeChange("manual")}
            />
            手动发布
          </label>
        </div>
      </div>

      {mode === "auto" && (
        <div className="field">
          <label className="label-title">定时拉取与发布间隔</label>
          <p className="field-hint">仅在「自动发布」下生效；按所选间隔重复拉取 AMP 最近时间窗并触发 WP 发布。</p>
          <select
            className="oc-input"
            value={publishIntervalHours ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "") onPublishIntervalChange(null);
              else onPublishIntervalChange(Number(v));
            }}
          >
            <option value="">关闭定时</option>
            <option value={1}>每 1 小时</option>
            <option value={3}>每 3 小时</option>
            <option value={12}>每 12 小时</option>
            <option value={24}>每 24 小时</option>
          </select>
        </div>
      )}

      <div className="field">
        <label className="label-title">新闻精编提示词 (Prompt)</label>
        <textarea
          className="oc-input"
          rows={8}
          value={llmConfig.system_prompt}
          onChange={(e) => onLLMChange({ ...llmConfig, system_prompt: e.target.value })}
          placeholder="输入改写 Prompt..."
        />
      </div>

      {showSourceConfig ? (
        <div className="field">
          <label className="label-title">数据源与分发目标</label>
        <div className="grid-two">
          <input
            className="oc-input"
            value={sourceConfig.amp_host}
            onChange={(e) => onSourceChange({ ...sourceConfig, amp_host: e.target.value })}
            placeholder="AMP Host"
          />
          <input
            className="oc-input"
            value={sourceConfig.amp_port}
            onChange={(e) =>
              onSourceChange({
                ...sourceConfig,
                amp_port: Number(e.target.value) || sourceConfig.amp_port,
              })
            }
            placeholder="Port"
          />
        </div>
        <div className="grid-two">
          <input
            className="oc-input"
            value={sourceConfig.amp_user}
            onChange={(e) => onSourceChange({ ...sourceConfig, amp_user: e.target.value })}
            placeholder="AMP Username"
          />
          <input
            className="oc-input"
            value={sourceConfig.amp_password}
            onChange={(e) => onSourceChange({ ...sourceConfig, amp_password: e.target.value })}
            placeholder="AMP Password"
            type="password"
          />
        </div>
        <input
          className="oc-input"
          value={sourceConfig.amp_database}
          onChange={(e) => onSourceChange({ ...sourceConfig, amp_database: e.target.value })}
          placeholder="AMP Database"
        />
        </div>
      ) : null}

      <div className="field">
        <div className="platform-section">
          <div className="platform-section-head">
            <span className="label-title inline">WordPress 发布目标</span>
            <button
              type="button"
              className="btn-link"
              disabled={platformBusy}
              onClick={() => setAddingPlatform(!addingPlatform)}
            >
              {addingPlatform ? "收起" : "+ 添加"}
            </button>
          </div>

          {addingPlatform && (
            <div className="platform-add-card">
              <input
                className="oc-input"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="显示名称"
              />
              <input
                className="oc-input"
                value={newSiteUrl}
                onChange={(e) => setNewSiteUrl(e.target.value)}
                placeholder="站点链接（含 https://）"
              />
              <div className="grid-two auth-toggle">
                <label className={newAuthType === "rest_app_password" ? "active" : ""}>
                  <input
                    type="radio"
                    name="wp-auth"
                    checked={newAuthType === "rest_app_password"}
                    onChange={() => setNewAuthType("rest_app_password")}
                  />
                  REST（应用密码）
                </label>
                <label className={newAuthType === "cookie_nonce" ? "active" : ""}>
                  <input
                    type="radio"
                    name="wp-auth"
                    checked={newAuthType === "cookie_nonce"}
                    onChange={() => setNewAuthType("cookie_nonce")}
                  />
                  浏览器登录
                </label>
              </div>
              {newAuthType === "rest_app_password" ? (
                <>
                  <input
                    className="oc-input"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="WP 用户名（REST Basic 鉴权必填）"
                  />
                  <input
                    className="oc-input"
                    type="password"
                    value={newSecret}
                    onChange={(e) => setNewSecret(e.target.value)}
                    placeholder="Application Password（应用密码）"
                  />
                </>
              ) : (
                <>
                  <input
                    className="oc-input"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="登录用户名"
                  />
                  <input
                    className="oc-input"
                    type="password"
                    value={newSecret}
                    onChange={(e) => setNewSecret(e.target.value)}
                    placeholder="登录密码"
                  />
                </>
              )}
              <button
                type="button"
                className="btn-brand full thin"
                disabled={platformBusy}
                onClick={() => void handleAddPlatform()}
              >
                保存平台
              </button>
            </div>
          )}

          <div className="platform-list">
            {platforms.length === 0 && !addingPlatform && (
              <div className="platform-empty">暂无平台，点击「添加」配置 REST 或浏览器登录。</div>
            )}
            {platforms.map((p) => (
              <div key={p.id} className="platform-item">
                <div className="platform-meta">
                  <span className="platform-name">{p.name}</span>
                  <span className="platform-auth">{authLabel(p.auth_type)}</span>
                </div>
                <div className="platform-actions">
                  <span className="platform-url" title={p.site_url}>
                    {p.site_url}
                  </span>
                  <button
                    type="button"
                    className="btn-danger-text"
                    disabled={platformBusy}
                    onClick={() => void handleDeletePlatform(p.id)}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <button className="btn-brand full" onClick={onSaveAll}>
        保存配置并更新任务
      </button>

      <div className="field test-box">
        <label className="label-title">单次拉取测试</label>
        <div className="test-time-grid">
          <div>
            <label className="time-label">开始时间</label>
            <input
              className="oc-input time-input"
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </div>
          <div>
            <label className="time-label">结束时间</label>
            <input
              className="oc-input time-input"
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </div>
        </div>
        <button
          className="btn-test"
          disabled={runningTest}
          onClick={() => {
            const start = startTime;
            const end = endTime;
            if (!start || !end) {
              alert("请先选择开始和结束时间");
              return;
            }
            onRunTest(new Date(start).toISOString(), new Date(end).toISOString());
          }}
        >
          {runningTest ? (
            <span className="btn-loading">
              <span className="spinner spinner-sm" />
              <span>采集中，请稍候...</span>
            </span>
          ) : (
            "开始采集与改写"
          )}
        </button>
      </div>
    </aside>
  );
}
