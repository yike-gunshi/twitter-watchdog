const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------- Types ----------

export interface AppConfig {
  twitter_username: string;
  custom_accounts: string[];
  style: "concise" | "standard" | "advanced";
  custom_prompt: string;
  keywords: string[];
  min_engagement: number;
  telegram_bot_token: string;
  telegram_chat_id: string;
  hours_ago: number;
  [key: string]: unknown;
}

export interface Job {
  id: number;
  type: "scrape" | "analyze" | "report" | "pipeline";
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  created_at: string;
  started_at?: string;
  finished_at?: string;
  params?: Record<string, unknown>;
  log?: string;
  error?: string;
}

export interface DataFile {
  filename: string;
  path: string;
  modified_at?: number;
  size_bytes?: number;
  count?: number;
  // Aliases for backward compat
  created_at?: string;
  size?: number;
  tweet_count?: number;
}

export interface Report {
  id: number;
  type: "single" | "daily" | "weekly" | "monthly";
  title?: string;
  tweet_count: number;
  created_at: string;
  summary?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ---------- Helpers ----------

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

async function requestNoContent(path: string, options?: RequestInit): Promise<void> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${body}`);
  }
}

// ---------- Config ----------

export async function getConfig(): Promise<AppConfig> {
  return request<AppConfig>("/api/config");
}

export async function updateConfig(config: Partial<AppConfig>): Promise<AppConfig> {
  return request<AppConfig>("/api/config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

// ---------- Jobs ----------

export async function createJob(
  type: Job["type"],
  params?: Record<string, unknown>
): Promise<Job> {
  return request<Job>("/api/jobs", {
    method: "POST",
    body: JSON.stringify({ type, params }),
  });
}

export async function listJobs(
  page = 1,
  limit = 20
): Promise<PaginatedResponse<Job>> {
  return request<PaginatedResponse<Job>>(
    `/api/jobs?page=${page}&limit=${limit}`
  );
}

export async function getJob(id: number | string): Promise<Job> {
  return request<Job>(`/api/jobs/${id}`);
}

export async function cancelJob(id: number): Promise<Job> {
  return request<Job>(`/api/jobs/${id}/cancel`, { method: "POST" });
}

export async function deleteJob(id: number): Promise<void> {
  return requestNoContent(`/api/jobs/${id}`, { method: "DELETE" });
}

// ---------- Reports ----------

export async function listReports(
  type?: Report["type"],
  page = 1,
  limit = 20
): Promise<PaginatedResponse<Report>> {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  if (type) params.set("type", type);
  return request<PaginatedResponse<Report>>(`/api/reports?${params}`);
}

export async function getReport(id: number | string): Promise<Report> {
  return request<Report>(`/api/reports/${id}`);
}

export function getReportHtmlUrl(id: number | string): string {
  return `${BASE_URL}/api/reports/${id}/html`;
}

export async function deleteReport(id: number): Promise<void> {
  return requestNoContent(`/api/reports/${id}`, { method: "DELETE" });
}

// ---------- Data Files ----------

export async function listRawFiles(): Promise<DataFile[]> {
  const res = await request<{ files: DataFile[] }>("/api/data/raw-files");
  return res.files;
}

export async function listAnalysisFiles(): Promise<DataFile[]> {
  const res = await request<{ files: DataFile[] }>("/api/data/analysis-files");
  return res.files;
}

export interface RawTweet {
  id: string;
  text: string;
  url: string;
  created_at: string;
  like_count: number;
  retweet_count: number;
  reply_count: number;
  view_count: number;
  quote_count: number;
  lang: string;
  source_type: "following" | "trending";
  author: {
    username: string;
    name: string;
    avatar: string;
  };
  has_media: boolean;
  is_reply: boolean;
  is_ai_selected?: boolean;
}

export interface RawFileContent {
  metadata: {
    scraped_at: string;
    username: string;
    hours_ago: number;
    followings_count: number;
    total_tweets: number;
    api_calls: number;
  };
  tweets: RawTweet[];
  total: number;
  following_count: number;
  trending_count: number;
  page: number;
  page_size: number;
}

export interface AnalysisFileContent {
  metadata: {
    analyzed_at: string;
    source_files: string[];
    total_tweets: number;
    filtered_count: number;
    model: string;
  };
  ai_tweet_ids: string[];
  tweets: RawTweet[];
  total: number;
  following_count: number;
  trending_count: number;
  page: number;
  page_size: number;
}

export interface ReportContext {
  analysis_file: string | null;
  raw_file: string | null;
  analysis_metadata: {
    analyzed_at: string;
    total_tweets: number;
    filtered_count: number;
    model: string;
  };
  raw_metadata: {
    scraped_at: string;
    followings_count: number;
    total_tweets: number;
    api_calls: number;
  };
}

export async function getRawFileContent(
  filename: string,
  page = 1,
  pageSize = 20,
  source: "all" | "followings" | "trending" = "all"
): Promise<RawFileContent> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    source,
  });
  return request<RawFileContent>(
    `/api/data/raw-files/${encodeURIComponent(filename)}?${params}`
  );
}

export async function getAnalysisFileContent(
  filename: string,
  page = 1,
  pageSize = 20,
  source: "all" | "followings" | "trending" = "all"
): Promise<AnalysisFileContent> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    source,
  });
  return request<AnalysisFileContent>(
    `/api/data/analysis-files/${encodeURIComponent(filename)}?${params}`
  );
}

export async function getReportContext(id: number | string): Promise<ReportContext> {
  return request<ReportContext>(`/api/reports/${id}/context`);
}

export async function getRawFileContentWithAnalysis(
  filename: string,
  analysisFile: string,
  page = 1,
  pageSize = 20,
  source: "all" | "followings" | "trending" = "all"
): Promise<RawFileContent> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    source,
    analysis_file: analysisFile,
  });
  return request<RawFileContent>(
    `/api/data/raw-files/${encodeURIComponent(filename)}?${params}`
  );
}

// ---------- Telegram test ----------

export async function testTelegram(): Promise<{ ok: boolean; message?: string }> {
  return request<{ ok: boolean; message?: string }>("/api/config/test-telegram", {
    method: "POST",
  });
}
