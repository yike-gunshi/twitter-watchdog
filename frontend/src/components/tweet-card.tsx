"use client";

import {
  Eye,
  Heart,
  Repeat2,
  MessageCircle,
  ExternalLink,
  Users,
  TrendingUp,
  Image as ImageIcon,
  Reply,
  Clock,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { RawTweet } from "@/lib/api";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) {
      const parsed = Date.parse(dateStr);
      if (!isNaN(parsed)) {
        return new Date(parsed).toLocaleString("zh-CN", {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      }
      return dateStr;
    }
    return d.toLocaleString("zh-CN", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export function TweetCard({ tweet }: { tweet: RawTweet }) {
  return (
    <div className="group relative rounded-2xl border border-border/40 bg-card/60 backdrop-blur-sm p-4 transition-all duration-300 hover:bg-card/80 hover:border-border/60 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-[2px] cursor-default dark:hover:shadow-primary/10">
      {/* Gradient accent line */}
      {tweet.is_ai_selected && (
        <div className="absolute top-0 left-4 right-4 h-[2px] rounded-full bg-gradient-to-r from-violet-500 via-blue-500 to-cyan-400 opacity-60" />
      )}

      {/* Author header */}
      <div className="flex items-start gap-3 mb-2.5">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm">
              {tweet.author.name || tweet.author.username}
            </span>
            <span className="text-xs text-muted-foreground/60">
              @{tweet.author.username}
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
            <Badge
              variant="secondary"
              className={`text-[10px] font-medium px-2 py-0 h-[20px] rounded-full border ${
                tweet.source_type === "trending"
                  ? "bg-gradient-to-r from-amber-500/10 to-orange-500/10 text-amber-500 dark:text-amber-400 border-amber-500/20"
                  : "bg-gradient-to-r from-blue-500/10 to-cyan-500/10 text-blue-500 dark:text-blue-400 border-blue-500/20"
              }`}
            >
              {tweet.source_type === "trending" ? (
                <>
                  <TrendingUp className="h-2.5 w-2.5 mr-0.5" />
                  热门
                </>
              ) : (
                <>
                  <Users className="h-2.5 w-2.5 mr-0.5" />
                  关注
                </>
              )}
            </Badge>
            {tweet.is_ai_selected && (
              <Badge
                variant="secondary"
                className="text-[10px] font-medium px-2 py-0 h-[20px] rounded-full border bg-gradient-to-r from-violet-500/10 to-purple-500/10 text-violet-500 dark:text-violet-400 border-violet-500/20"
              >
                <Sparkles className="h-2.5 w-2.5 mr-0.5" />
                AI筛选
              </Badge>
            )}
            {tweet.is_reply && (
              <Badge variant="secondary" className="text-[10px] px-2 py-0 h-[20px] rounded-full">
                <Reply className="h-2.5 w-2.5 mr-0.5" />
                回复
              </Badge>
            )}
            {tweet.has_media && (
              <Badge variant="secondary" className="text-[10px] px-2 py-0 h-[20px] rounded-full">
                <ImageIcon className="h-2.5 w-2.5 mr-0.5" />
                含图
              </Badge>
            )}
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground/50">
              <Clock className="h-2.5 w-2.5" />
              {formatDate(tweet.created_at)}
            </span>
          </div>
        </div>
        {tweet.url && (
          <a
            href={tweet.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground/30 hover:text-primary transition-all duration-200 shrink-0 mt-0.5 cursor-pointer hover:scale-110"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      {/* Tweet text */}
      <p className="text-[13px] leading-relaxed whitespace-pre-line text-foreground/85 mb-3.5">
        {tweet.text}
      </p>

      {/* Metrics bar */}
      <div className="flex items-center gap-5 text-xs text-muted-foreground/50">
        <span className="flex items-center gap-1.5 transition-colors duration-200 hover:text-foreground/70 cursor-default">
          <Eye className="h-3 w-3" />
          <span className="tabular-nums">{formatNumber(tweet.view_count)}</span>
        </span>
        <span className="flex items-center gap-1.5 transition-colors duration-200 hover:text-rose-400 cursor-default">
          <Heart className="h-3 w-3" />
          <span className="tabular-nums">{formatNumber(tweet.like_count)}</span>
        </span>
        <span className="flex items-center gap-1.5 transition-colors duration-200 hover:text-emerald-400 cursor-default">
          <Repeat2 className="h-3 w-3" />
          <span className="tabular-nums">{formatNumber(tweet.retweet_count)}</span>
        </span>
        <span className="flex items-center gap-1.5 transition-colors duration-200 hover:text-blue-400 cursor-default">
          <MessageCircle className="h-3 w-3" />
          <span className="tabular-nums">{formatNumber(tweet.reply_count)}</span>
        </span>
        {tweet.lang && (
          <span className="ml-auto uppercase text-[10px] tracking-wider font-medium text-muted-foreground/30">
            {tweet.lang}
          </span>
        )}
      </div>
    </div>
  );
}
