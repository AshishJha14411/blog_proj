import React from "react";

import { cn } from "@/lib/cn";
import { inputBase } from "./Input";

type TextareaProps = React.ComponentPropsWithoutRef<'textarea'> & {
  className?: string;
};

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    // Shares Input's token set so a field never drifts from the field above it.
    return <textarea ref={ref} className={cn(inputBase, 'leading-relaxed', className)} {...props} />;
  }
);

Textarea.displayName = "Textarea";
export default Textarea;
