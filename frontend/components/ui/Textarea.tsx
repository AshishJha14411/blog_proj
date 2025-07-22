import React from "react";

type TextareaProps = React.ComponentPropsWithoutRef<'textarea'>

const Textarea =  React.forwardRef<HTMLTextAreaElement, TextareaProps>((props,ref) => {
    return (
        <textarea {...props} ref={ref} className="mt-1 block w-full rounded-md border-gray-300 text-text shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
      />
    )
})

Textarea.displayName = 'Textarea'
export default Textarea