import React from "react";

type TextareaProps = React.ComponentPropsWithoutRef<'textarea'> & {
  className?: string;
};

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    const base =
      "mt-1 block w-full rounded-md border-gray-300 text-text shadow-sm focus:border-primary focus:ring-primary sm:text-sm";
    const merged = [base, className].filter(Boolean).join(" ");

    return <textarea ref={ref} className={merged} {...props} />;
  }
);

Textarea.displayName = "Textarea";
export default Textarea;
