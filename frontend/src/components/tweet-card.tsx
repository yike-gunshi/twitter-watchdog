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
    <div className="group relative rounded-xl border bg-card p-4 transition-all duration-200 hover:shadow-md hover:border-border/80 hover:-translate-y-[1px]">
      {/* Author header */}
      <div className="flex items-start gap-3 mb-2.5">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm">
              {tweet.author.name || tweet.author.username}
            </span>
            <span className="text-xs text-muted-foreground/70">
              @{tweet.author.username}
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <Badge
              variant="secondary"
              className={`text-[10px] font-medium px-1.5 py-0 h-[18px] ${
                tweet.source_type === "trending"
                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
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
                className="text-[10px] font-medium px-1.5 py-0 h-[18px] bg-violet-500/10 text-violet-600 dark:text-violet-400"
              >
                <Sparkles className="h-2.5 w-2.5 mr-0.5" />
                AI筛选
              </Badge>
            )}
            {tweet.is_reply && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-[18px]">
                <Reply className="h-2.5 w-2.5 mr-0.5" />
                回复
              </Badge>
            )}
            {tweet.has_media && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-[18px]">
                <ImageIcon className="h-2.5 w-2.5 mr-0.5" />
                含图
              </Badge>
            )}
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground/60">
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
            className="text-muted-foreground/40 hover:text-primary transition-colors shrink-0 mt-0.5"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      {/* Tweet text */}
      <p className="text-[13px] leading-relaxed whitespace-pre-line text-foreground/90 mb-3">
        {tweet.text}
      </p>

      {/* Metrics bar */}
      <div className="flex items-center gap-5 text-xs text-muted-foreground/60">
        <span className="flex items-center gap-1 hover:text-foreground/80 transition-colors">
          <Eye className="h-3 w-3" />
          {formatNumber(tweet.view_count)}
        </span>
        <span className="flex items-center gap-1 hover:text-red-500 transition-colors">
          <Heart className="h-3 w-3" />
          {formatNumber(tweet.like_count)}
        </span>
        <span className="flex items-center gap-1 hover:text-emerald-500 transition-colors">
          <Repeat2 className="h-3 w-3" />
          {formatNumber(tweet.retweet_count)}
        </span>
        <span className="flex items-center gap-1 hover:text-blue-500 transition-colors">
          <MessageCircle className="h-3 w-3" />
          {formatNumber(tweet.reply_count)}
        </span>
        {tweet.lang && (
          <span className="ml-auto uppercase text-[10px] tracking-wider font-medium opacity-50">{tweet.lang}</span>
        )}
      </div>
    </div>
  );
}
