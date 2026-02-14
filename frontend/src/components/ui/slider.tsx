"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  value?: number;
  min?: number;
  max?: number;
  step?: number;
  onValueChange?: (value: number) => void;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ className, value = 0, min = 0, max = 100, step = 1, onValueChange, ...props }, ref) => {
    return (
      <input
        type="range"
        ref={ref}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onValueChange?.(Number(e.target.value))}
        className={cn(
          "w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary",
          className
        )}
        {...props}
      />
    );
  }
);
Slider.displayName = "Slider";

export { Slider };
