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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
  { value: "", label: "最新" },
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

export default function InformationCenterPage() {
  // Report selection
  const [reports, setReports] = useState<Report[]>([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [reportFilterType, setReportFilterType] = useState("");
  const [reportPage, setReportPage] = useState(1);
  const [reportTotal, setReportTotal] = useState(0);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);

  // Report context
  const [context, setContext] = useState<ReportContext | null>(null);
  const [contextLoading, setContextLoading] = useState(false);

  // Tweet display — keep old data visible during loading
  const [tweetMode, setTweetMode] = useState<"filtered" | "all">("filtered");
  const [tweets, setTweets] = useState<RawTweet[]>([]);
  const [tweetsLoading, setTweetsLoading] = useState(false);
  const [tweetPage, setTweetPage] = useState(1);
  const [tweetTotal, setTweetTotal] = useState(0);
  const [tweetFollowingCount, setTweetFollowingCount] = useState(0);
  const [tweetTrendingCount, setTweetTrendingCount] = useState(0);
  const [sourceFilter, setSourceFilter] = useState<"all" | "followings" | "trending">("all");
  const tweetPageSize = 20;

  // Scroll ref for tweet section
  const tweetSectionRef = useRef<HTMLDivElement>(null);

  // Fetch reports
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

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Fetch report context when report is selected
  useEffect(() => {
    if (!selectedReport) {
      setContext(null);
      return;
    }
    setContextLoading(true);
    getReportContext(selectedReport.id)
      .then((ctx) => {
        setContext(ctx);
        setTweetMode("filtered");
        setTweetPage(1);
        setSourceFilter("all");
      })
      .catch(() => setContext(null))
      .finally(() => setContextLoading(false));
  }, [selectedReport]);

  // Fetch tweets — keep old data during loading to prevent layout jump
  const fetchTweets = useCallback(async () => {
    if (!context) return;

    setTweetsLoading(true);
    try {
      if (tweetMode === "filtered" && context.analysis_file) {
        const data = await getAnalysisFileContent(
          context.analysis_file,
          tweetPage,
          tweetPageSize,
          sourceFilter
        );
        setTweets(data.tweets);
        setTweetTotal(data.total);
        setTweetFollowingCount(data.following_count);
        setTweetTrendingCount(data.trending_count);
      } else if (tweetMode === "all" && context.raw_file) {
        const data = context.analysis_file
          ? await getRawFileContentWithAnalysis(
              context.raw_file,
              context.analysis_file,
              tweetPage,
              tweetPageSize,
              sourceFilter
            )
          : await getRawFileContent(
              context.raw_file,
              tweetPage,
              tweetPageSize,
              sourceFilter
            );
        setTweets(data.tweets);
        setTweetTotal(data.total);
        setTweetFollowingCount(data.following_count);
        setTweetTrendingCount(data.trending_count);
      } else {
        setTweets([]);
        setTweetTotal(0);
        setTweetFollowingCount(0);
        setTweetTrendingCount(0);
      }
    } catch {
      setTweets([]);
      setTweetTotal(0);
    } finally {
      setTweetsLoading(false);
    }
  }, [context, tweetMode, tweetPage, sourceFilter]);

  useEffect(() => {
    fetchTweets();
  }, [fetchTweets]);

  const tweetTotalPages = Math.ceil(tweetTotal / tweetPageSize);
  const reportTotalPages = Math.ceil(reportTotal / 20);

  return (
    <div className="space-y-10">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">信息中心</h2>
        <p className="text-sm text-muted-foreground mt-1">
          浏览报告、推文记录与采集信息
        </p>
      </div>

      {/* ① Report Selector */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            报告浏览
          </h3>
          {reportTotalPages > 1 && (
            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                disabled={reportPage <= 1}
                onClick={() => setReportPage((p) => p - 1)}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <span className="text-xs text-muted-foreground tabular-nums">
                {reportPage}/{reportTotalPages}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                disabled={reportPage >= reportTotalPages}
                onClick={() => setReportPage((p) => p + 1)}
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </div>

        {/* Type filter pills */}
        <div className="flex gap-1.5">
          {typeFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => {
                setReportFilterType(f.value);
                setReportPage(1);
                setSelectedReport(null);
              }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-200 ${
                reportFilterType === f.value
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Report cards */}
        {reportsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : reports.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="rounded-full bg-muted p-4 mb-3">
              <FileText className="h-6 w-6 text-muted-foreground/50" />
            </div>
            <p className="text-sm text-muted-foreground">暂无报告数据</p>
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-hide">
            {reports.map((report) => {
              const isSelected = selectedReport?.id === report.id;
              return (
                <button
                  key={report.id}
                  onClick={() => setSelectedReport(report)}
                  className={`flex-shrink-0 w-[140px] rounded-xl border p-3.5 text-left transition-all duration-200 ${
                    isSelected
                      ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary/20"
                      : "border-transparent bg-accent/40 hover:bg-accent hover:shadow-sm"
                  }`}
                >
                  <div className="text-xl font-bold tabular-nums leading-none">
                    {formatShortDate(report.created_at)}
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-1">
                    {formatTime(report.created_at)}
                  </div>
                  <div className="flex items-center gap-1.5 mt-2.5">
                    <Badge
                      variant="secondary"
                      className="text-[10px] px-1.5 py-0 h-[18px] font-medium"
                    >
                      {typeLabels[report.type] || report.type}
                    </Badge>
                    {report.tweet_count > 0 && (
                      <span className="text-[10px] text-muted-foreground">
                        {report.tweet_count} 条
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* ② Report Content (iframe) */}
      {selectedReport && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Layers className="h-3.5 w-3.5" />
              报告内容
            </h3>
            <a
              href={getReportHtmlUrl(selectedReport.id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground hover:text-foreground">
                <ExternalLink className="h-3 w-3" />
                新窗口打开
              </Button>
            </a>
          </div>
          <div className="rounded-xl border overflow-hidden bg-card shadow-sm">
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
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <Database className="h-3.5 w-3.5" />
            推文记录
          </h3>

          {contextLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : !context ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="rounded-full bg-muted p-3 mb-2">
                <Database className="h-5 w-5 text-muted-foreground/50" />
              </div>
              <p className="text-sm text-muted-foreground">无法加载推文数据</p>
            </div>
          ) : (
            <>
              {/* Controls bar */}
              <div className="flex flex-wrap items-center gap-3">
                {/* Mode toggle */}
                <div className="inline-flex rounded-lg bg-muted p-0.5">
                  <button
                    onClick={() => {
                      setTweetMode("filtered");
                      setTweetPage(1);
                      setSourceFilter("all");
                    }}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
                      tweetMode === "filtered"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Filter className="h-3 w-3" />
                    筛选后
                    <span className="tabular-nums opacity-70">({context.analysis_metadata.filtered_count})</span>
                  </button>
                  <button
                    onClick={() => {
                      setTweetMode("all");
                      setTweetPage(1);
                      setSourceFilter("all");
                    }}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
                      tweetMode === "all"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Database className="h-3 w-3" />
                    全部原始
                    <span className="tabular-nums opacity-70">({context.analysis_metadata.total_tweets})</span>
                  </button>
                </div>

                {/* Source filter pills */}
                <div className="flex gap-1">
                  {(
                    [
                      { value: "all", label: "全部" },
                      { value: "followings", label: "关注列表" },
                      { value: "trending", label: "热门搜索" },
                    ] as const
                  ).map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => {
                        setSourceFilter(opt.value);
                        setTweetPage(1);
                      }}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200 ${
                        sourceFilter === opt.value
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-accent hover:text-foreground"
                      }`}
                    >
                      {opt.label}
                      {opt.value === "followings" && tweetFollowingCount > 0 && (
                        <span className="ml-0.5 opacity-60 tabular-nums">({tweetFollowingCount})</span>
                      )}
                      {opt.value === "trending" && tweetTrendingCount > 0 && (
                        <span className="ml-0.5 opacity-60 tabular-nums">({tweetTrendingCount})</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tweet list — keep old content visible with opacity during loading */}
              <div className="relative min-h-[200px]">
                {/* Loading overlay — sits on top of old content */}
                {tweetsLoading && (
                  <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60 backdrop-blur-[2px] rounded-xl">
                    <div className="flex items-center gap-2 bg-background/90 rounded-full px-4 py-2 shadow-sm border">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                      <span className="text-xs text-muted-foreground">加载中</span>
                    </div>
                  </div>
                )}

                {tweets.length === 0 && !tweetsLoading ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="rounded-full bg-muted p-3 mb-2">
                      <Filter className="h-5 w-5 text-muted-foreground/50" />
                    </div>
                    <p className="text-sm text-muted-foreground">该条件下无推文</p>
                  </div>
                ) : (
                  <>
                    <div className={`space-y-2.5 transition-opacity duration-200 ${tweetsLoading ? "opacity-40" : "opacity-100"}`}>
                      {tweets.map((tweet) => (
                        <TweetCard key={tweet.id} tweet={tweet} />
                      ))}
                    </div>

                    {/* Pagination */}
                    {tweetTotalPages > 1 && (
                      <div className="flex items-center justify-between pt-4 mt-2 border-t">
                        <span className="text-xs text-muted-foreground tabular-nums">
                          第 {tweetPage}/{tweetTotalPages} 页 · 共 {tweetTotal} 条
                        </span>
                        <div className="flex gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 text-xs"
                            disabled={tweetPage <= 1}
                            onClick={() => setTweetPage((p) => p - 1)}
                          >
                            <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                            上一页
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 text-xs"
                            disabled={tweetPage >= tweetTotalPages}
                            onClick={() => setTweetPage((p) => p + 1)}
                          >
                            下一页
                            <ChevronRight className="h-3.5 w-3.5 ml-1" />
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
        <section className="pb-4">
          <div className="rounded-xl border bg-accent/30 p-5">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
              采集元信息
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-5">
              {context.raw_metadata.scraped_at && (
                <div className="flex items-start gap-2.5">
                  <div className="rounded-lg bg-background p-1.5 shadow-sm">
                    <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div>
                    <div className="text-[11px] text-muted-foreground">采集时间</div>
                    <div className="text-sm font-medium mt-0.5 tabular-nums">
                      {new Date(context.raw_metadata.scraped_at).toLocaleString("zh-CN", {
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>
              )}
              <div className="flex items-start gap-2.5">
                <div className="rounded-lg bg-background p-1.5 shadow-sm">
                  <Users className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div>
                  <div className="text-[11px] text-muted-foreground">关注账号</div>
                  <div className="text-sm font-medium mt-0.5 tabular-nums">
                    {context.raw_metadata.followings_count} 个
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <div className="rounded-lg bg-background p-1.5 shadow-sm">
                  <Zap className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div>
                  <div className="text-[11px] text-muted-foreground">API 调用</div>
                  <div className="text-sm font-medium mt-0.5 tabular-nums">
                    {context.raw_metadata.api_calls} 次
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <div className="rounded-lg bg-background p-1.5 shadow-sm">
                  <BarChart3 className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div>
                  <div className="text-[11px] text-muted-foreground">原始 / 筛选</div>
                  <div className="text-sm font-medium mt-0.5 tabular-nums">
                    {context.analysis_metadata.total_tweets} → {context.analysis_metadata.filtered_count}
                  </div>
                </div>
              </div>
              {context.analysis_metadata.model && (
                <div className="flex items-start gap-2.5">
                  <div className="rounded-lg bg-background p-1.5 shadow-sm">
                    <Cpu className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[11px] text-muted-foreground">分析模型</div>
                    <div className="text-sm font-medium mt-0.5 truncate">
                      {context.analysis_metadata.model}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
