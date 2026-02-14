"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  Play,
  Search,
  Brain,
  FileText,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Ban,
  Trash2,
  StopCircle,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Terminal,
  Save,
  Plus,
  X,
  Send,
  AlertCircle,
  RefreshCw,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TimeRangeSelector } from "@/components/time-range-selector";
import { StyleSelector, type StyleValue } from "@/components/style-selector";
import { PromptEditor } from "@/components/prompt-editor";
import {
  createJob,
  listJobs,
  getJob,
  cancelJob,
  deleteJob,
  getConfig,
  updateConfig,
  testTelegram,
  listRawFiles,
  listAnalysisFiles,
  type Job,
  type AppConfig,
  type DataFile,
} from "@/lib/api";

// ---- Status Config ----

const statusConfig: Record<
  Job["status"],
  { label: string; className: string; dot: string; icon: React.ReactNode }
> = {
  pending: {
    label: "等待中",
    className: "bg-muted text-muted-foreground",
    dot: "bg-muted-foreground",
    icon: <Clock className="h-3 w-3" />,
  },
  running: {
    label: "运行中",
    className: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    dot: "bg-blue-500 animate-pulse",
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
  },
  completed: {
    label: "已完成",
    className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    dot: "bg-emerald-500",
    icon: <CheckCircle2 className="h-3 w-3" />,
  },
  failed: {
    label: "失败",
    className: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
    dot: "bg-red-500",
    icon: <XCircle className="h-3 w-3" />,
  },
  cancelled: {
    label: "已取消",
    className: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
    dot: "bg-orange-500",
    icon: <Ban className="h-3 w-3" />,
  },
};

const jobTypeLabels: Record<Job["type"], string> = {
  scrape: "数据采集",
  analyze: "智能分析",
  report: "生成报告",
  pipeline: "完整流水线",
};

function formatTime(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

function duration(start?: string, end?: string) {
  if (!start) return "";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const diff = Math.floor((e - s) / 1000);
  if (diff < 60) return `${diff}s`;
  const min = Math.floor(diff / 60);
  const sec = diff % 60;
  return `${min}m${sec}s`;
}

// ---- Scrape Dialog ----
function ScrapeDialog({
  open,
  onOpenChange,
  config,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  config: AppConfig | null;
  onSubmit: (params: Record<string, unknown>) => void;
}) {
  const [hoursAgo, setHoursAgo] = useState(8);
  const [maxTweets, setMaxTweets] = useState(50);
  const [minViews, setMinViews] = useState(1000);

  useEffect(() => {
    if (open && config) {
      setHoursAgo(config.hours_ago || 8);
      setMaxTweets(50);
      setMinViews(config.min_engagement || 1000);
    }
  }, [open, config]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>采集数据</DialogTitle>
          <DialogDescription>配置数据采集参数后执行</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <TimeRangeSelector value={hoursAgo} onChange={setHoursAgo} id="scrape-hours" />
          <div className="grid gap-2">
            <Label htmlFor="scrape-max">热门推文最大数量</Label>
            <Input id="scrape-max" type="number" min={1} max={500} value={maxTweets} onChange={(e) => setMaxTweets(Number(e.target.value))} className="w-32" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="scrape-views">最低浏览量</Label>
            <Input id="scrape-views" type="number" min={0} value={minViews} onChange={(e) => setMinViews(Number(e.target.value))} className="w-32" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={() => onSubmit({ hours_ago: hoursAgo, max_tweets: maxTweets, min_views: minViews })}>
            执行
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---- Analyze Dialog ----
function AnalyzeDialog({
  open,
  onOpenChange,
  config,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  config: AppConfig | null;
  onSubmit: (params: Record<string, unknown>) => void;
}) {
  const [hoursAgo, setHoursAgo] = useState(8);
  const [source, setSource] = useState("");
  const [style, setStyle] = useState<StyleValue>("standard");
  const [customPrompt, setCustomPrompt] = useState("");
  const [rawFiles, setRawFiles] = useState<DataFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);

  useEffect(() => {
    if (open && config) {
      setHoursAgo(config.hours_ago || 8);
      setStyle(config.style || "standard");
      setCustomPrompt(config.custom_prompt || "");
      setSource("");
      setFilesLoading(true);
      listRawFiles().then(setRawFiles).catch(() => setRawFiles([])).finally(() => setFilesLoading(false));
    }
  }, [open, config]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>智能分析</DialogTitle>
          <DialogDescription>配置 AI 分析参数后执行</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="analyze-source">数据源</Label>
            <select id="analyze-source" value={source} onChange={(e) => setSource(e.target.value)} className="flex h-9 w-full rounded-lg border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
              <option value="">最新采集数据</option>
              {filesLoading && <option disabled>加载中...</option>}
              {rawFiles.map((f) => (
                <option key={f.path} value={f.path}>
                  {f.filename}{(f.count ?? f.tweet_count) ? ` (${f.count ?? f.tweet_count} 条)` : ""}
                </option>
              ))}
            </select>
          </div>
          <TimeRangeSelector value={hoursAgo} onChange={setHoursAgo} label="时间范围" id="analyze-hours" />
          <StyleSelector value={style} onChange={setStyle} />
          <PromptEditor value={customPrompt} onChange={setCustomPrompt} id="analyze-prompt" />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={() => {
            const params: Record<string, unknown> = { hours_ago: hoursAgo, style };
            if (source) params.source = source;
            if (customPrompt.trim()) params.custom_prompt = customPrompt.trim();
            onSubmit(params);
          }}>
            执行
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---- Report Dialog ----
function ReportDialog({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSubmit: (params: Record<string, unknown>) => void;
}) {
  const [reportType, setReportType] = useState<"single" | "daily" | "weekly" | "monthly">("single");
  const [source, setSource] = useState("");
  const [reportDate, setReportDate] = useState("");
  const [analysisFiles, setAnalysisFiles] = useState<DataFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setReportType("single");
      setSource("");
      setReportDate(new Date().toISOString().slice(0, 10));
      setFilesLoading(true);
      listAnalysisFiles().then(setAnalysisFiles).catch(() => setAnalysisFiles([])).finally(() => setFilesLoading(false));
    }
  }, [open]);

  const reportTypeOptions = [
    { value: "single", label: "单次" },
    { value: "daily", label: "日报" },
    { value: "weekly", label: "周报" },
    { value: "monthly", label: "月报" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>生成报告</DialogTitle>
          <DialogDescription>选择报告类型与数据源</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>报告类型</Label>
            <div className="grid grid-cols-4 gap-1.5">
              {reportTypeOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setReportType(opt.value as typeof reportType)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                    reportType === opt.value
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          {reportType === "single" && (
            <div className="grid gap-2">
              <Label htmlFor="report-source">数据源（分析文件）</Label>
              <select id="report-source" value={source} onChange={(e) => setSource(e.target.value)} className="flex h-9 w-full rounded-lg border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
                <option value="">最新分析数据</option>
                {filesLoading && <option disabled>加载中...</option>}
                {analysisFiles.map((f) => (
                  <option key={f.path} value={f.path}>{f.filename}{(f.count ?? f.tweet_count) ? ` (${f.count ?? f.tweet_count} 条)` : ""}</option>
                ))}
              </select>
            </div>
          )}
          {reportType === "daily" && (
            <div className="grid gap-2">
              <Label htmlFor="report-date">日期</Label>
              <Input id="report-date" type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} />
            </div>
          )}
          {reportType === "weekly" && (
            <div className="grid gap-2">
              <Label htmlFor="report-week">选择日期（将自动取该周）</Label>
              <Input id="report-week" type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} />
              <p className="text-xs text-muted-foreground">选择一周内任意一天</p>
            </div>
          )}
          {reportType === "monthly" && (
            <div className="grid gap-2">
              <Label htmlFor="report-month">月份</Label>
              <Input id="report-month" type="month" value={reportDate.slice(0, 7)} onChange={(e) => setReportDate(e.target.value + "-01")} />
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={() => {
            const params: Record<string, unknown> = { report_type: reportType };
            if (reportType === "single") { if (source) params.source = source; }
            else if (reportType === "daily") { params.report_date = reportDate; }
            else if (reportType === "weekly") { params.report_date = reportDate; }
            else if (reportType === "monthly") { params.report_date = reportDate.slice(0, 7); }
            onSubmit(params);
          }}>
            执行
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---- Pipeline Dialog ----
function PipelineDialog({
  open,
  onOpenChange,
  config,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  config: AppConfig | null;
  onSubmit: (params: Record<string, unknown>) => void;
}) {
  const [hoursAgo, setHoursAgo] = useState(8);
  const [style, setStyle] = useState<StyleValue>("standard");
  const [customPrompt, setCustomPrompt] = useState("");

  useEffect(() => {
    if (open && config) {
      setHoursAgo(config.hours_ago || 8);
      setStyle(config.style || "standard");
      setCustomPrompt(config.custom_prompt || "");
    }
  }, [open, config]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>完整流水线</DialogTitle>
          <DialogDescription>依次执行采集、分析、报告</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <TimeRangeSelector value={hoursAgo} onChange={setHoursAgo} id="pipeline-hours" />
          <StyleSelector value={style} onChange={setStyle} />
          <PromptEditor value={customPrompt} onChange={setCustomPrompt} id="pipeline-prompt" />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={() => {
            const params: Record<string, unknown> = { hours_ago: hoursAgo, style };
            if (customPrompt.trim()) params.custom_prompt = customPrompt.trim();
            onSubmit(params);
          }}>
            执行
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---- Main Workbench Page ----
export default function WorkbenchPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [runningAction, setRunningAction] = useState<string | null>(null);

  const [scrapeOpen, setScrapeOpen] = useState(false);
  const [analyzeOpen, setAnalyzeOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [pipelineOpen, setPipelineOpen] = useState(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobPage, setJobPage] = useState(1);
  const [jobTotal, setJobTotal] = useState(0);
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);
  const [expandedJob, setExpandedJob] = useState<Job | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const [confirmAction, setConfirmAction] = useState<{
    type: "cancel" | "delete";
    jobId: number;
    jobLabel: string;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const [newAccount, setNewAccount] = useState("");
  const [newKeyword, setNewKeyword] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string } | null>(null);

  const [sourceOpen, setSourceOpen] = useState(true);
  const [styleOpen, setStyleOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [telegramOpen, setTelegramOpen] = useState(false);

  useEffect(() => {
    getConfig()
      .then(setConfig)
      .catch(() =>
        setConfig({
          twitter_username: "",
          custom_accounts: [],
          style: "standard",
          custom_prompt: "",
          keywords: [],
          min_engagement: 0,
          telegram_bot_token: "",
          telegram_chat_id: "",
          hours_ago: 8,
        })
      )
      .finally(() => setConfigLoading(false));
  }, []);

  const fetchJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const res = await listJobs(jobPage, 10);
      setJobs(res.items);
      setJobTotal(res.total);
    } catch {
      setJobs([]);
    } finally {
      setJobsLoading(false);
    }
  }, [jobPage]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (!expandedJobId) {
      setExpandedJob(null);
      return;
    }
    const poll = async () => {
      try {
        const job = await getJob(expandedJobId);
        setExpandedJob(job);
        if (job.status !== "running" && job.status !== "pending") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // ignore
      }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [expandedJobId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [expandedJob?.log]);

  useEffect(() => {
    const hasRunning = jobs.some((j) => j.status === "running" || j.status === "pending");
    if (!hasRunning) return;
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [jobs, fetchJobs]);

  const handleOpenDialog = (type: Job["type"]) => {
    switch (type) {
      case "scrape": setScrapeOpen(true); break;
      case "analyze": setAnalyzeOpen(true); break;
      case "report": setReportOpen(true); break;
      case "pipeline": setPipelineOpen(true); break;
    }
  };

  const handleSubmitJob = async (type: Job["type"], params: Record<string, unknown>) => {
    setScrapeOpen(false);
    setAnalyzeOpen(false);
    setReportOpen(false);
    setPipelineOpen(false);
    setRunningAction(type);
    try {
      await createJob(type, params);
      await fetchJobs();
    } catch {
      // handle error
    } finally {
      setRunningAction(null);
    }
  };

  const handleConfirmAction = async () => {
    if (!confirmAction) return;
    setActionLoading(true);
    try {
      if (confirmAction.type === "cancel") {
        await cancelJob(confirmAction.jobId);
      } else {
        await deleteJob(confirmAction.jobId);
        if (expandedJobId === confirmAction.jobId) setExpandedJobId(null);
      }
      setConfirmAction(null);
      await fetchJobs();
    } catch {
      // silently handle
    } finally {
      setActionLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setSaved(false);
    try {
      const updated = await updateConfig(config);
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  };

  const handleTestTelegram = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testTelegram();
      setTestResult(result);
    } catch {
      setTestResult({ ok: false, message: "发送失败，请检查配置" });
    } finally {
      setTesting(false);
    }
  };

  const addTag = (field: "custom_accounts" | "keywords", value: string) => {
    if (!config || !value.trim()) return;
    const list = config[field] as string[];
    if (!list.includes(value.trim())) {
      setConfig({ ...config, [field]: [...list, value.trim()] });
    }
    if (field === "custom_accounts") setNewAccount("");
    else setNewKeyword("");
  };

  const removeTag = (field: "custom_accounts" | "keywords", index: number) => {
    if (!config) return;
    const list = [...(config[field] as string[])];
    list.splice(index, 1);
    setConfig({ ...config, [field]: list });
  };

  const quickActions = [
    { type: "pipeline" as const, label: "完整流水线", desc: "采集 → 分析 → 报告", icon: Play, gradient: "from-blue-600 to-indigo-600" },
    { type: "scrape" as const, label: "数据采集", desc: "抓取最新推文", icon: Search, gradient: "from-emerald-500 to-teal-600" },
    { type: "analyze" as const, label: "分析推文", desc: "AI 智能筛选", icon: Brain, gradient: "from-violet-500 to-purple-600" },
    { type: "report" as const, label: "生成报告", desc: "输出分析报告", icon: FileText, gradient: "from-amber-500 to-orange-600" },
  ];

  const jobTotalPages = Math.ceil(jobTotal / 10);

  return (
    <div className="space-y-10">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">工作台</h2>
        <p className="text-sm text-muted-foreground mt-1">触发任务、管理执行、配置系统</p>
      </div>

      {/* ① Quick Actions */}
      <section>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {quickActions.map((action) => (
            <button
              key={action.type}
              onClick={() => handleOpenDialog(action.type)}
              disabled={runningAction !== null}
              className={`group relative flex flex-col items-center gap-2.5 rounded-2xl p-5 text-center text-white transition-all duration-200 bg-gradient-to-br ${action.gradient} hover:shadow-lg hover:shadow-black/10 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:hover:shadow-none disabled:hover:translate-y-0`}
            >
              {runningAction === action.type ? (
                <Loader2 className="h-7 w-7 animate-spin" />
              ) : (
                <action.icon className="h-7 w-7 transition-transform group-hover:scale-110" />
              )}
              <span className="text-sm font-semibold">{action.label}</span>
              <span className="text-[11px] opacity-75">{action.desc}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Dialogs */}
      <ScrapeDialog open={scrapeOpen} onOpenChange={setScrapeOpen} config={config} onSubmit={(params) => handleSubmitJob("scrape", params)} />
      <AnalyzeDialog open={analyzeOpen} onOpenChange={setAnalyzeOpen} config={config} onSubmit={(params) => handleSubmitJob("analyze", params)} />
      <ReportDialog open={reportOpen} onOpenChange={setReportOpen} onSubmit={(params) => handleSubmitJob("report", params)} />
      <PipelineDialog open={pipelineOpen} onOpenChange={setPipelineOpen} config={config} onSubmit={(params) => handleSubmitJob("pipeline", params)} />

      {/* ② Task Management */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            任务管理
          </h3>
          <Button variant="ghost" size="sm" onClick={fetchJobs} className="gap-1.5 text-xs text-muted-foreground hover:text-foreground">
            <RefreshCw className="h-3 w-3" />
            刷新
          </Button>
        </div>

        {jobsLoading && jobs.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="rounded-full bg-muted p-4 mb-3">
              <Terminal className="h-6 w-6 text-muted-foreground/50" />
            </div>
            <p className="text-sm text-muted-foreground">暂无任务记录</p>
            <p className="text-xs text-muted-foreground/60 mt-1">点击上方按钮开始</p>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {jobs.map((job) => {
                const status = statusConfig[job.status];
                const canCancel = job.status === "running" || job.status === "pending";
                const canDelete = job.status === "completed" || job.status === "failed" || job.status === "cancelled";
                const isExpanded = expandedJobId === job.id;

                return (
                  <div key={job.id} className="rounded-xl border overflow-hidden transition-all duration-200 hover:border-border/80">
                    <div className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <Badge variant="secondary" className={`gap-1 text-[11px] shrink-0 border ${status.className}`}>
                          {status.icon}
                          {status.label}
                        </Badge>
                        <span className="text-sm font-medium truncate">{jobTypeLabels[job.type]}</span>
                        <span className="text-xs text-muted-foreground/60 shrink-0">{formatTime(job.created_at)}</span>
                        {job.started_at && (
                          <span className="text-xs text-muted-foreground/50 hidden sm:inline shrink-0 tabular-nums">
                            {duration(job.started_at, job.finished_at)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-0.5 shrink-0">
                        {canCancel && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmAction({ type: "cancel", jobId: job.id, jobLabel: jobTypeLabels[job.type] });
                            }}
                          >
                            <StopCircle className="h-3 w-3 mr-1" />
                            取消
                          </Button>
                        )}
                        {canDelete && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs text-red-500 hover:text-red-600 hover:bg-red-500/10"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmAction({ type: "delete", jobId: job.id, jobLabel: jobTypeLabels[job.type] });
                            }}
                          >
                            <Trash2 className="h-3 w-3 mr-1" />
                            删除
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs"
                          onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
                        >
                          {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          <span className="ml-0.5">日志</span>
                        </Button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t px-4 py-3 bg-accent/20">
                        {expandedJob ? (
                          <>
                            {expandedJob.error && (
                              <div className="rounded-lg bg-red-500/5 border border-red-500/10 p-3 mb-3">
                                <div className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">错误信息</div>
                                <pre className="text-xs whitespace-pre-wrap font-mono text-red-600/70 dark:text-red-400/70">{expandedJob.error}</pre>
                              </div>
                            )}
                            <div className="flex items-center gap-2 mb-2">
                              <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
                              <span className="text-xs font-medium">运行日志</span>
                              {(expandedJob.status === "running" || expandedJob.status === "pending") && (
                                <span className="flex items-center gap-1 text-xs text-blue-500 ml-auto">
                                  <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                                  实时更新
                                </span>
                              )}
                            </div>
                            <div className="rounded-lg bg-muted/40 p-3 max-h-[40vh] overflow-auto font-mono text-xs leading-relaxed">
                              {expandedJob.log ? (
                                <>
                                  <pre className="whitespace-pre-wrap">{expandedJob.log}</pre>
                                  <div ref={logEndRef} />
                                </>
                              ) : (
                                <p className="text-muted-foreground">暂无日志</p>
                              )}
                            </div>
                          </>
                        ) : (
                          <div className="flex justify-center py-4">
                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {jobTotalPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <Button variant="ghost" size="icon" className="h-8 w-8" disabled={jobPage <= 1} onClick={() => setJobPage((p) => p - 1)}>
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-xs text-muted-foreground tabular-nums">{jobPage}/{jobTotalPages}</span>
                <Button variant="ghost" size="icon" className="h-8 w-8" disabled={jobPage >= jobTotalPages} onClick={() => setJobPage((p) => p + 1)}>
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </>
        )}
      </section>

      {/* Confirm Dialog */}
      <Dialog open={confirmAction !== null} onOpenChange={(v) => !v && setConfirmAction(null)}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>{confirmAction?.type === "cancel" ? "取消任务" : "删除任务"}</DialogTitle>
            <DialogDescription>
              {confirmAction?.type === "cancel"
                ? `确定要取消「${confirmAction?.jobLabel}」任务吗？`
                : `确定要删除「${confirmAction?.jobLabel}」记录吗？此操作不可撤销。`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmAction(null)} disabled={actionLoading}>返回</Button>
            <Button variant="destructive" onClick={handleConfirmAction} disabled={actionLoading}>
              {actionLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {confirmAction?.type === "cancel" ? "确认取消" : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ③ System Configuration */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            系统配置
          </h3>
          <Button
            onClick={handleSave}
            disabled={saving || configLoading}
            size="sm"
            className="gap-1.5 h-8"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : saved ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {saved ? "已保存" : "保存配置"}
          </Button>
        </div>

        {configLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : config ? (
          <div className="space-y-2">
            {/* Source section */}
            <div className="rounded-xl border overflow-hidden">
              <button
                className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-accent/30 transition-colors"
                onClick={() => setSourceOpen(!sourceOpen)}
              >
                <div className="text-left">
                  <CardTitle className="text-sm">信息源</CardTitle>
                  <CardDescription className="text-xs mt-0.5">Twitter 用户名 / 自定义账号 / 采集时间范围</CardDescription>
                </div>
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${sourceOpen ? "rotate-180" : ""}`} />
              </button>
              {sourceOpen && (
                <div className="px-5 pb-5 pt-1 border-t space-y-4">
                  <div className="space-y-2">
                    <Label>Twitter 用户名（主账号）</Label>
                    <p className="text-xs text-muted-foreground">你的 Twitter 用户名，用于获取关注列表</p>
                    <Input placeholder="输入用户名（不带 @）" value={config.twitter_username} onChange={(e) => setConfig({ ...config, twitter_username: e.target.value.replace(/^@/, "") })} className="w-64" />
                  </div>
                  <div className="space-y-2">
                    <Label>自定义账号</Label>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {config.custom_accounts.map((u, i) => (
                        <span key={i} className="inline-flex items-center gap-1 rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium">
                          @{u}
                          <button onClick={() => removeTag("custom_accounts", i)} className="ml-0.5 hover:text-destructive transition-colors"><X className="h-3 w-3" /></button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <Input placeholder="添加自定义账号" value={newAccount} onChange={(e) => setNewAccount(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag("custom_accounts", newAccount.replace(/^@/, "")); } }} />
                      <Button variant="outline" size="icon" onClick={() => addTag("custom_accounts", newAccount.replace(/^@/, ""))}><Plus className="h-4 w-4" /></Button>
                    </div>
                  </div>
                  <TimeRangeSelector value={config.hours_ago} onChange={(v) => setConfig({ ...config, hours_ago: v })} label="默认采集时间范围" />
                </div>
              )}
            </div>

            {/* Style section */}
            <div className="rounded-xl border overflow-hidden">
              <button
                className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-accent/30 transition-colors"
                onClick={() => setStyleOpen(!styleOpen)}
              >
                <div className="text-left">
                  <CardTitle className="text-sm">分析风格</CardTitle>
                  <CardDescription className="text-xs mt-0.5">精简/标准/深度 + 自定义提示词</CardDescription>
                </div>
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${styleOpen ? "rotate-180" : ""}`} />
              </button>
              {styleOpen && (
                <div className="px-5 pb-5 pt-1 border-t space-y-4">
                  <StyleSelector value={config.style as StyleValue} onChange={(v) => setConfig({ ...config, style: v })} />
                  <PromptEditor value={config.custom_prompt} onChange={(v) => setConfig({ ...config, custom_prompt: v })} />
                </div>
              )}
            </div>

            {/* Filter section */}
            <div className="rounded-xl border overflow-hidden">
              <button
                className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-accent/30 transition-colors"
                onClick={() => setFilterOpen(!filterOpen)}
              >
                <div className="text-left">
                  <CardTitle className="text-sm">过滤规则</CardTitle>
                  <CardDescription className="text-xs mt-0.5">关键词列表 + 最低互动量</CardDescription>
                </div>
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${filterOpen ? "rotate-180" : ""}`} />
              </button>
              {filterOpen && (
                <div className="px-5 pb-5 pt-1 border-t space-y-4">
                  <div className="space-y-2">
                    <Label>关键词列表</Label>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {config.keywords.map((kw, i) => (
                        <span key={i} className="inline-flex items-center gap-1 rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium">
                          {kw}
                          <button onClick={() => removeTag("keywords", i)} className="ml-0.5 hover:text-destructive transition-colors"><X className="h-3 w-3" /></button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <Input placeholder="输入关键词后回车添加" value={newKeyword} onChange={(e) => setNewKeyword(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag("keywords", newKeyword); } }} />
                      <Button variant="outline" size="icon" onClick={() => addTag("keywords", newKeyword)}><Plus className="h-4 w-4" /></Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>最低互动量</Label>
                      <span className="text-sm text-muted-foreground tabular-nums">{config.min_engagement}</span>
                    </div>
                    <Slider value={config.min_engagement} min={0} max={10000} step={10} onValueChange={(v) => setConfig({ ...config, min_engagement: v })} />
                    <div className="flex justify-between text-[11px] text-muted-foreground">
                      <span>0</span>
                      <span>10,000</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Telegram section */}
            <div className="rounded-xl border overflow-hidden">
              <button
                className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-accent/30 transition-colors"
                onClick={() => setTelegramOpen(!telegramOpen)}
              >
                <div className="text-left">
                  <CardTitle className="text-sm">Telegram 推送</CardTitle>
                  <CardDescription className="text-xs mt-0.5">Bot Token / Chat ID / 测试发送</CardDescription>
                </div>
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${telegramOpen ? "rotate-180" : ""}`} />
              </button>
              {telegramOpen && (
                <div className="px-5 pb-5 pt-1 border-t space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Bot Token</Label>
                      <Input type="password" placeholder="输入 Telegram Bot Token" value={config.telegram_bot_token} onChange={(e) => setConfig({ ...config, telegram_bot_token: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label>Chat ID</Label>
                      <Input placeholder="输入 Chat ID" value={config.telegram_chat_id} onChange={(e) => setConfig({ ...config, telegram_chat_id: e.target.value })} />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Button variant="outline" size="sm" onClick={handleTestTelegram} disabled={testing || !config.telegram_bot_token || !config.telegram_chat_id} className="gap-2">
                      {testing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                      测试推送
                    </Button>
                    {testResult && (
                      <span className={`flex items-center gap-1.5 text-xs font-medium ${testResult.ok ? "text-emerald-600" : "text-destructive"}`}>
                        {testResult.ok ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                        {testResult.ok ? "发送成功" : testResult.message || "发送失败"}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
