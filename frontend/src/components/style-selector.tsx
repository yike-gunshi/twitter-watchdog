"use client";

import { Label } from "@/components/ui/label";

export type StyleValue = "concise" | "standard" | "advanced";

interface StyleSelectorProps {
  value: StyleValue;
  onChange: (style: StyleValue) => void;
  showExamples?: boolean;
}

const STYLE_OPTIONS: {
  value: StyleValue;
  label: string;
  desc: string;
  example: string;
}[] = [
  {
    value: "concise",
    label: "精简",
    desc: "每条一句话，快速浏览",
    example:
      "OpenAI 发布 GPT-5，支持实时视频理解和高级代码生成，多模态推理能力大幅提升。",
  },
  {
    value: "standard",
    label: "标准",
    desc: "1-2 句说明 + 来源",
    example:
      "OpenAI 正式发布 GPT-5 模型，在多模态推理方面能力大幅提升，新增实时视频理解与高级代码生成功能。新模型已向 Plus 用户开放。来源：@OpenAI 官方公告",
  },
  {
    value: "advanced",
    label: "深度",
    desc: "完整分析 + 为什么重要",
    example:
      "OpenAI 正式发布 GPT-5 模型，在多模态推理方面能力大幅提升，新增实时视频理解与高级代码生成功能。来源：@OpenAI 官方公告\n\n为什么重要：这标志着 LLM 从文本为主向真正多模态的转变，将直接影响 AI Agent 和开发者工具链的生态格局。",
  },
];

export function StyleSelector({
  value,
  onChange,
  showExamples = true,
}: StyleSelectorProps) {
  return (
    <div className="grid gap-2">
      <Label>分析风格</Label>
      <div className="grid grid-cols-1 gap-2">
        {STYLE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`rounded-lg border-2 p-3 text-left transition-all ${
              value === opt.value
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/30"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{opt.label}</span>
              <span className="text-xs text-muted-foreground">{opt.desc}</span>
            </div>
            {showExamples && (
              <div className="mt-2 rounded-md bg-muted/50 px-3 py-2">
                <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-line">
                  {opt.example}
                </p>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
