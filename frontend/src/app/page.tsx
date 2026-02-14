"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  Loader2,
  FileText,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Filter,
  Database,
  Layers,
  Clock,
  Users,
  Zap,
  BarChart3,
  Cpu,
  CalendarDays,
  Sparkles,
  Activity,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TweetCard } from "@/components/tweet-card";
import {
  listReports,
  getReportHtmlUrl,
  getReportContext,
  getAnalysisFileContent,
  getRawFileContentWithAnalysis,
  getRawFileContent,
  type Report,
  type ReportContext,
  type RawTweet,
} from "@/lib/api";

const typeFilters: { value: string; label: string }[] = [
  { value: "", label: "全部" },
  { value: "single", label: "单次" },
  { value: "daily", label: "日报" },
  { value: "weekly", label: "周报" },
  { value: "monthly", label: "月报" },
];

const typeLabels: Record<string, string> = {
  single: "单次",
  daily: "日报",
  weekly: "周报",
  monthly: "月报",
};

const typeGradients: Record<string, string> = {
  single: "from-blue-500 to-cyan-500",
  daily: "from-emerald-500 to-teal-500",
  weekly: "from-violet-500 to-purple-500",
  monthly: "from-amber-500 to-orange-500",
};

const typeBorders: Record<string, string> = {
  single: "border-blue-500/20 dark:border-blue-400/20",
  daily: "border-emerald-500/20 dark:border-emerald-400/20",
  weekly: "border-violet-500/20 dark:border-violet-400/20",
  monthly: "border-amber-500/20 dark:border-amber-400/20",
};

function formatShortDate(dateStr: string) {
  const d = new Date(dateStr);
  return `${(d.getMonth() + 1).toString().padStart(2, "0")}/${d.getDate().toString().padStart(2, "0")}`;
}

function formatTime(dateStr: string) {
  return new Date(dateStr).toLocaleString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getPeriodLabel(report: Report): string | null {
  if (report.type === "single") return null;

  if (report.period_start && report.period_end) {
    const start = new Date(report.period_start);
    const end = new Date(report.period_end);
    if (report.type === "daily") {
      return `${start.getFullYear()}/${(start.getMonth() + 1).toString().padStart(2, "0")}/${start.getDate().toString().padStart(2, "0")}`;
    }
    if (report.type === "weekly") {
      const fmt = (d: Date) =>
        `${(d.getMonth() + 1).toString().padStart(2, "0")}/${d.getDate().toString().padStart(2, "0")}`;
      return `${fmt(start)} ~ ${fmt(end)}`;
    }
    if (report.type === "monthly") {
      return `${start.getFullYear()}年${start.getMonth() + 1}月`;
    }
  }

  const d = new Date(report.created_at);
  if (report.type === "daily") {
    return `${d.getFullYear()}/${(d.getMonth() + 1).toString().padStart(2, "0")}/${d.getDate().toString().padStart(2, "0")}`;
  }
  if (report.type === "weekly") {
    const start = new Date(d);
    start.setDate(d.getDate() - 6);
    const fmt = (dt: Date) =>
      `${(dt.getMonth() + 1).toString().padStart(2, "0")}/${dt.getDate().toString().padStart(2, "0")}`;
    return `${fmt(start)} ~ ${fmt(d)}`;
  }
  if (report.type === "monthly") {
    return `${d.getFullYear()}年${d.getMonth() + 1}月`;
  }
  return null;
}

export default function InformationCenterPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [reportFilterType, setReportFilterType] = useState("");
  const [reportPage, setReportPage] = useState(1);
  const [reportTotal, setReportTotal] = useState(0);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);

  const [context, setContext] = useState<ReportContext | null>(null);
  const [contextLoading, setContextLoading] = useState(false);

  const [tweetMode, setTweetMode] = useState<"filtered" | "all">("filtered");
  const [tweets, setTweets] = useState<RawTweet[]>([]);
  const [tweetsLoading, setTweetsLoading] = useState(false);
  const [tweetPage, setTweetPage] = useState(1);
  const [tweetTotal, setTweetTotal] = useState(0);
  const [tweetFollowingCount, setTweetFollowingCount] = useState(0);
  const [tweetTrendingCount, setTweetTrendingCount] = useState(0);
  const [sourceFilter, setSourceFilter] = useState<"all" | "followings" | "trending">("all");
  const tweetPageSize = 20;

  const tweetSectionRef = useRef<HTMLDivElement>(null);

  const fetchReports = useCallback(async () => {
    setReportsLoading(true);
    try {
      const res = await listReports(
        reportFilterType ? (reportFilterType as Report["type"]) : undefined,
        reportPage,
        20
      );
      setReports(res.items);
      setReportTotal(res.total);
      if (res.items.length > 0 && !selectedReport) {
        setSelectedReport(res.items[0]);
      }
    } catch {
      setReports([]);
    } finally {
      setReportsLoading(false);
    }
  }, [reportFilterType, reportPage]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchReports(); }, [fetchReports]);

  useEffect(() => {
    if (!selectedReport) { setContext(null); return; }
    setContextLoading(true);
    getReportContext(selectedReport.id)
      .then((ctx) => { setContext(ctx); setTweetMode("filtered"); setTweetPage(1); setSourceFilter("all"); })
      .catch(() => setContext(null))
      .finally(() => setContextLoading(false));
  }, [selectedReport]);

  const fetchTweets = useCallback(async () => {
    if (!context) return;
    setTweetsLoading(true);
    try {
      if (tweetMode === "filtered" && context.analysis_file) {
        const data = await getAnalysisFileContent(context.analysis_file, tweetPage, tweetPageSize, sourceFilter);
        setTweets(data.tweets); setTweetTotal(data.total); setTweetFollowingCount(data.following_count); setTweetTrendingCount(data.trending_count);
      } else if (tweetMode === "all" && context.raw_file) {
        const data = context.analysis_file
          ? await getRawFileContentWithAnalysis(context.raw_file, context.analysis_file, tweetPage, tweetPageSize, sourceFilter)
          : await getRawFileContent(context.raw_file, tweetPage, tweetPageSize, sourceFilter);
        setTweets(data.tweets); setTweetTotal(data.total); setTweetFollowingCount(data.following_count); setTweetTrendingCount(data.trending_count);
      } else {
        setTweets([]); setTweetTotal(0); setTweetFollowingCount(0); setTweetTrendingCount(0);
      }
    } catch { setTweets([]); setTweetTotal(0); }
    finally { setTweetsLoading(false); }
  }, [context, tweetMode, tweetPage, sourceFilter]);

  useEffect(() => { fetchTweets(); }, [fetchTweets]);

  const tweetTotalPages = Math.ceil(tweetTotal / tweetPageSize);
  const reportTotalPages = Math.ceil(reportTotal / 20);

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="relative">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/20">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">信息中心</h2>
            <p className="text-sm text-muted-foreground/70 mt-0.5">
              浏览报告、推文记录与采集信息
            </p>
          </div>
        </div>
      </div>

      {/* ① Report Selector */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
              报告浏览
            </h3>
            <span className="text-[10px] text-muted-foreground/40 tabular-nums">{reportTotal} 份</span>
          </div>
          {reportTotalPages > 1 && (
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7 cursor-pointer rounded-lg" disabled={reportPage <= 1} onClick={() => setReportPage((p) => p - 1)}>
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <span className="text-[11px] text-muted-foreground/60 tabular-nums w-10 text-center">{reportPage}/{reportTotalPages}</span>
              <Button variant="ghost" size="icon" className="h-7 w-7 cursor-pointer rounded-lg" disabled={reportPage >= reportTotalPages} onClick={() => setReportPage((p) => p + 1)}>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </div>

        {/* Type filter */}
        <div className="flex gap-1 p-1 rounded-xl bg-muted/50 w-fit">
          {typeFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => { setReportFilterType(f.value); setReportPage(1); setSelectedReport(null); }}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-250 cursor-pointer ${
                reportFilterType === f.value
                  ? "bg-background text-foreground shadow-sm dark:bg-card dark:shadow-md dark:shadow-black/20"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Report cards */}
        {reportsLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-primary/60" />
              <span className="text-xs text-muted-foreground/50">加载报告...</span>
            </div>
          </div>
        ) : reports.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="rounded-2xl bg-muted/50 p-5 mb-4">
              <FileText className="h-8 w-8 text-muted-foreground/30" />
            </div>
            <p className="text-sm text-muted-foreground/60">暂无报告数据</p>
            <p className="text-xs text-muted-foreground/30 mt-1">前往工作台生成第一份报告</p>
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
            {reports.map((report) => {
              const isSelected = selectedReport?.id === report.id;
              const periodLabel = getPeriodLabel(report);
              const gradient = typeGradients[report.type] || "from-gray-500 to-gray-600";
              return (
                <button
                  key={report.id}
                  onClick={() => setSelectedReport(report)}
                  className={`group/card flex-shrink-0 w-[168px] rounded-2xl border p-4 text-left transition-all duration-300 cursor-pointer relative overflow-hidden ${
                    isSelected
                      ? `${typeBorders[report.type]} bg-card/80 shadow-lg dark:shadow-primary/5 ring-1 ring-primary/20`
                      : "border-border/30 bg-card/40 hover:bg-card/70 hover:border-border/50 hover:shadow-md dark:hover:shadow-black/20"
                  }`}
                >
                  {/* Top gradient bar */}
                  <div className={`absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r ${gradient} ${isSelected ? "opacity-80" : "opacity-0 group-hover/card:opacity-40"} transition-opacity duration-300`} />

                  <div className="flex items-center gap-1.5 mb-2.5">
                    <span className={`inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-md bg-gradient-to-r ${gradient} text-white`}>
                      {typeLabels[report.type] || report.type}
                    </span>
                  </div>

                  {periodLabel ? (
                    <div className="flex items-center gap-1.5 mb-2">
                      <CalendarDays className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />
                      <span className="text-sm font-bold tabular-nums leading-tight truncate">
                        {periodLabel}
                      </span>
                    </div>
                  ) : (
                    <div className="text-xl font-black tabular-nums leading-none mb-2 tracking-tight">
                      {formatShortDate(report.created_at)}
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground/50">
                    <Clock className="h-2.5 w-2.5" />
                    <span className="tabular-nums">{formatTime(report.created_at)}</span>
                    {report.tweet_count > 0 && (
                      <>
                        <span className="text-muted-foreground/20">|</span>
                        <span className="tabular-nums">{report.tweet_count} 条</span>
                      </>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* ② Report Content */}
      {selectedReport && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest flex items-center gap-2">
              <Layers className="h-3.5 w-3.5" />
              报告内容
            </h3>
            <a href={getReportHtmlUrl(selectedReport.id)} target="_blank" rel="noopener noreferrer">
              <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground/60 hover:text-foreground cursor-pointer h-8 rounded-lg">
                <ExternalLink className="h-3 w-3" />
                新窗口打开
              </Button>
            </a>
          </div>
          <div className="rounded-2xl border border-border/30 overflow-hidden bg-card/50 backdrop-blur-sm shadow-sm dark:shadow-black/10">
            <iframe
              src={getReportHtmlUrl(selectedReport.id)}
              className="w-full border-0"
              style={{ minHeight: "60vh" }}
              title="报告内容"
            />
          </div>
        </section>
      )}

      {/* ③ Tweet Records */}
      {selectedReport && (
        <section className="space-y-4" ref={tweetSectionRef}>
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest flex items-center gap-2">
            <Database className="h-3.5 w-3.5" />
            推文记录
          </h3>

          {contextLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-5 w-5 animate-spin text-primary/60" />
            </div>
          ) : !context ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="rounded-2xl bg-muted/50 p-4 mb-3">
                <Database className="h-6 w-6 text-muted-foreground/30" />
              </div>
              <p className="text-sm text-muted-foreground/60">无法加载推文数据</p>
            </div>
          ) : (
            <>
              {/* Controls bar */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="inline-flex rounded-xl bg-muted/50 p-1 gap-0.5">
                  <button
                    onClick={() => { setTweetMode("filtered"); setTweetPage(1); setSourceFilter("all"); }}
                    className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-250 cursor-pointer ${
                      tweetMode === "filtered"
                        ? "bg-background text-foreground shadow-sm dark:bg-card dark:shadow-md dark:shadow-black/20"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Sparkles className="h-3 w-3" />
                    筛选后
                    <span className="tabular-nums opacity-60">({context.analysis_metadata.filtered_count})</span>
                  </button>
                  <button
                    onClick={() => { setTweetMode("all"); setTweetPage(1); setSourceFilter("all"); }}
                    className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-250 cursor-pointer ${
                      tweetMode === "all"
                        ? "bg-background text-foreground shadow-sm dark:bg-card dark:shadow-md dark:shadow-black/20"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Database className="h-3 w-3" />
                    全部原始
                    <span className="tabular-nums opacity-60">({context.analysis_metadata.total_tweets})</span>
                  </button>
                </div>

                <div className="flex gap-0.5">
                  {([
                    { value: "all", label: "全部" },
                    { value: "followings", label: "关注" },
                    { value: "trending", label: "热门" },
                  ] as const).map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => { setSourceFilter(opt.value); setTweetPage(1); }}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
                        sourceFilter === opt.value
                          ? "bg-primary/10 text-primary dark:bg-primary/15"
                          : "text-muted-foreground/60 hover:bg-muted/50 hover:text-foreground"
                      }`}
                    >
                      {opt.label}
                      {opt.value === "followings" && tweetFollowingCount > 0 && (
                        <span className="ml-1 opacity-50 tabular-nums">({tweetFollowingCount})</span>
                      )}
                      {opt.value === "trending" && tweetTrendingCount > 0 && (
                        <span className="ml-1 opacity-50 tabular-nums">({tweetTrendingCount})</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tweet list */}
              <div className="relative min-h-[200px]">
                {tweetsLoading && (
                  <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/50 backdrop-blur-sm rounded-2xl">
                    <div className="flex items-center gap-2.5 bg-card/90 rounded-full px-5 py-2.5 shadow-lg shadow-black/5 border border-border/50">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                      <span className="text-xs text-muted-foreground">加载中</span>
                    </div>
                  </div>
                )}

                {tweets.length === 0 && !tweetsLoading ? (
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="rounded-2xl bg-muted/50 p-4 mb-3">
                      <Filter className="h-6 w-6 text-muted-foreground/30" />
                    </div>
                    <p className="text-sm text-muted-foreground/60">该条件下无推文</p>
                  </div>
                ) : (
                  <>
                    <div className={`space-y-3 transition-opacity duration-300 ${tweetsLoading ? "opacity-30" : "opacity-100"}`}>
                      {tweets.map((tweet) => (
                        <TweetCard key={tweet.id} tweet={tweet} />
                      ))}
                    </div>

                    {tweetTotalPages > 1 && (
                      <div className="flex items-center justify-between pt-5 mt-3">
                        <span className="text-xs text-muted-foreground/50 tabular-nums">
                          第 {tweetPage}/{tweetTotalPages} 页 · 共 {tweetTotal} 条
                        </span>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" className="h-8 text-xs cursor-pointer rounded-lg border-border/40" disabled={tweetPage <= 1} onClick={() => setTweetPage((p) => p - 1)}>
                            <ChevronLeft className="h-3.5 w-3.5 mr-1" />上一页
                          </Button>
                          <Button variant="outline" size="sm" className="h-8 text-xs cursor-pointer rounded-lg border-border/40" disabled={tweetPage >= tweetTotalPages} onClick={() => setTweetPage((p) => p + 1)}>
                            下一页<ChevronRight className="h-3.5 w-3.5 ml-1" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          )}
        </section>
      )}

      {/* ④ Collection Metadata */}
      {selectedReport && context && (
        <section className="pb-6">
          <div className="rounded-2xl border border-border/30 bg-card/40 backdrop-blur-sm p-6 dark:bg-card/30">
            <h3 className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest mb-5">
              采集元信息
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-6">
              {[
                { icon: Clock, label: "采集时间", value: context.raw_metadata.scraped_at ? new Date(context.raw_metadata.scraped_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "-", show: !!context.raw_metadata.scraped_at },
                { icon: Users, label: "关注账号", value: `${context.raw_metadata.followings_count} 个`, show: true },
                { icon: Zap, label: "API 调用", value: `${context.raw_metadata.api_calls} 次`, show: true },
                { icon: BarChart3, label: "原始 / 筛选", value: `${context.analysis_metadata.total_tweets} → ${context.analysis_metadata.filtered_count}`, show: true },
                { icon: Cpu, label: "分析模型", value: context.analysis_metadata.model || "-", show: !!context.analysis_metadata.model },
              ].filter(item => item.show).map((item) => (
                <div key={item.label} className="flex items-start gap-3">
                  <div className="rounded-xl bg-primary/5 p-2 dark:bg-primary/10">
                    <item.icon className="h-4 w-4 text-primary/60" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[11px] text-muted-foreground/50 font-medium">{item.label}</div>
                    <div className="text-sm font-semibold mt-0.5 tabular-nums truncate">{item.value}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
