import React from 'react';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';
import clsx from 'clsx';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: any;
}

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({ messages, loading }) => {
  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-4xl mx-auto space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {loading && (
          <div className="flex items-center space-x-2 text-gray-500">
            <div className="animate-pulse">●</div>
            <div className="animate-pulse animation-delay-200">●</div>
            <div className="animate-pulse animation-delay-400">●</div>
          </div>
        )}
      </div>
    </div>
  );
};

const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'max-w-3xl rounded-lg px-4 py-3',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 shadow-md'
        )}
      >
        <div className="prose prose-sm dark:prose-invert max-w-none">
          {isUser ? (
            <p className="mb-0">{message.content}</p>
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}
        </div>
        
        <div className={clsx(
          'text-xs mt-2',
          isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'
        )}>
          {format(message.timestamp, 'HH:mm')}
          {message.metadata?.tools_used && (
            <span className="ml-2">
              • Used: {message.metadata.tools_used.join(', ')}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageList;