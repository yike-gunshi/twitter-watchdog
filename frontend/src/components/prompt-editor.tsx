"use client";

import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  id?: string;
}

const PROMPT_TEMPLATES = [
  {
    label: "AI Agent & MCP",
    text: "重点关注 AI Agent 框架、MCP 协议、以及 AI 工具链方向的动态",
  },
  {
    label: "忽略营销",
    text: "忽略纯营销推广和广告内容，只保留有实质技术信息的推文",
  },
  {
    label: "关注中文",
    text: "增加对中文推文的关注度，中文 AI 社区的动态同样重要",
  },
  {
    label: "开源 & 技术突破",
    text: "重点关注开源项目发布、技术论文、以及重大技术突破",
  },
  {
    label: "AI 安全 & 治理",
    text: "关注 AI 安全、对齐研究、以及各国 AI 政策和治理方面的讨论",
  },
  {
    label: "产品 & 商业化",
    text: "关注 AI 产品发布、商业化落地案例、以及融资动态",
  },
];

export function PromptEditor({ value, onChange, id }: PromptEditorProps) {
  const handleTemplate = (text: string) => {
    if (value.trim()) {
      // Append to existing, separated by newline
      onChange(value.trimEnd() + "\n" + text);
    } else {
      onChange(text);
    }
  };

  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>自定义提示词</Label>
      <Textarea
        id={id}
        rows={3}
        placeholder="可选，自定义 AI 分析提示词..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="space-y-1.5">
        <p className="text-xs text-muted-foreground">点击添加预设模板：</p>
        <div className="flex flex-wrap gap-1.5">
          {PROMPT_TEMPLATES.map((t) => (
            <button
              key={t.label}
              type="button"
              onClick={() => handleTemplate(t.text)}
              className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
