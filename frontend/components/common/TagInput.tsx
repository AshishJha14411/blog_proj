'use client';

import React, { useState } from 'react';
import Input from '../ui/Input';

interface TagInputProps {
  tags: string[];
  setTags: (tags: string[]) => void;
}

export default function TagInput({ tags, setTags }: TagInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      const newTag = inputValue.trim();

      if (newTag && !tags.includes(newTag)) {
        setTags([...tags, newTag]);
      }
      setInputValue('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter((tag) => tag !== tagToRemove));
  };

  return (
    <div>
      {tags.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {tags.map((tag, index) => (
            <div
              key={index}
              className="flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/12 px-3 py-1 text-sm font-medium text-primary-strong"
            >
              {/* The remove button must remain the tag span's IMMEDIATE next
                  sibling — TagInput.test.tsx reaches it via nextElementSibling. */}
              <span>{tag}</span>
              <button
                type="button"
                onClick={() => removeTag(tag)}
                aria-label={`Remove tag ${tag}`}
                className="leading-none text-primary-strong/70 transition-colors hover:text-red-500"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
      <Input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Add tags (press Enter to add)"
      />
    </div>
  );
}
