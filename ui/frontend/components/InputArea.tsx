import React from 'react';

interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onKeyPress?: (e: React.KeyboardEvent) => void;
  disabled?: boolean;
  placeholder?: string;
}

const InputArea: React.FC<InputAreaProps> = ({
  value,
  onChange,
  onSubmit,
  onKeyPress,
  disabled,
  placeholder
}) => {
  return (
    <div className="border-t dark:border-gray-700 px-4 py-4 bg-white dark:bg-gray-800">
      <div className="max-w-4xl mx-auto flex space-x-4">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={onKeyPress}
          disabled={disabled}
          placeholder={placeholder}
          className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-600 
                     bg-gray-50 dark:bg-gray-700 px-4 py-3 text-gray-900 dark:text-gray-100
                     focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
                     disabled:opacity-50 disabled:cursor-not-allowed"
          rows={3}
        />
        
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium
                     hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default InputArea;