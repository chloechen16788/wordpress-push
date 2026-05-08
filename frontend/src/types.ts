export type BatchSummary = {
  id: number;
  task_id: number;
  batch_uuid: string;
  trigger_type: string;
  status: string;
  raw_count: number;
  rewritten_count: number;
  published_count: number;
  cvr: number;
  start_time: string | null;
  end_time: string | null;
  created_at: string;
};

export type PlatformStatus = {
  platform_id: number;
  platform_name: string;
  status: string;
  preview_url?: string | null;
  wp_post_id?: number | null;
  error_msg?: string | null;
};

export type RecordItem = {
  source_record_id: number;
  publish_item_id?: number | null;
  original_id: string;
  fetched_at: string;
  thumbnail_url?: string | null;
  original_title: string;
  original_body: string;
  is_adopted: string;
  adoption_reason: string;
  industry_category?: string | null;
  edited_article?: string | null;
  news_brief?: string | null;
  headline_1?: string | null;
  headline_2?: string | null;
  headline_3?: string | null;
  publish_status: string;
  platform_statuses: PlatformStatus[];
};

export type Task = {
  id: number;
  name: string;
  mode: "auto" | "manual";
  cron_expr?: string | null;
  publish_interval_hours?: number | null;
  is_test_space: boolean;
  status: string;
};

