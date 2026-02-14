"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface TimeRangeSelectorProps {
  value: number;
  onChange: (hours: number) => void;
  label?: string;
  id?: string;
}

const PRESETS = [
  { label: "1小时", hours: 1 },
  { label: "2小时", hours: 2 },
  { label: "4小时", hours: 4 },
  { label: "6小时", hours: 6 },
  { label: "8小时", hours: 8 },
  { label: "12小时", hours: 12 },
  { label: "1天", hours: 24 },
  { label: "3天", hours: 72 },
  { label: "1周", hours: 168 },
];

export function TimeRangeSelector({
  value,
  onChange,
  label = "采集时间范围",
  id,
}: TimeRangeSelectorProps) {
  const [customMode, setCustomMode] = useState(
    !PRESETS.some((p) => p.hours === value)
  );

  const handlePreset = (hours: number) => {
    setCustomMode(false);
    onChange(hours);
  };

  const handleCustom = () => {
    setCustomMode(true);
  };

  return (
    <div className="grid gap-2">
      {label && <Label htmlFor={id}>{label}</Label>}
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map((p) => (
          <Button
            key={p.hours}
            type="button"
            variant={!customMode && value === p.hours ? "default" : "outline"}
            size="sm"
            className="h-7 px-2.5 text-xs"
            onClick={() => handlePreset(p.hours)}
          >
            {p.label}
          </Button>
        ))}
        <Button
          type="button"
          variant={customMode ? "default" : "outline"}
          size="sm"
          className="h-7 px-2.5 text-xs"
          onClick={handleCustom}
        >
          自定义
        </Button>
      </div>
      {customMode && (
        <div className="flex items-center gap-2 mt-1">
          <Input
            id={id}
            type="number"
            min={1}
            max={720}
            value={value}
            onChange={(e) => onChange(Number(e.target.value) || 1)}
            className="w-24 h-8 text-sm"
          />
          <span className="text-sm text-muted-foreground">小时</span>
        </div>
      )}
    </div>
  );
}
