import { useRef, useEffect } from 'preact/hooks';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

interface MessageListProps {
  messages: Message[];
  onInsertScript?: (script: string) => void;
}

export function MessageList({ messages, onInsertScript }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div class="flex-1 flex items-center justify-center text-neutral-500 text-sm p-4">
        <div class="text-center">
          <p>Ask the AI to help write FileMaker scripts.</p>
          <p class="text-xs mt-2 text-neutral-600">
            The AI can see your current editor content and CONTEXT.json.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div class="flex-1 overflow-y-auto p-3 space-y-3">
      {messages.map((msg, i) => (
        <div key={i} class={`text-sm ${msg.role === 'user' ? 'text-blue-300' : 'text-neutral-300'}`}>
          <div class="text-xs text-neutral-500 mb-0.5 select-none">
            {msg.role === 'user' ? 'You' : 'AI'}
            {msg.streaming && ' (streaming...)'}
          </div>
          <div class="whitespace-pre-wrap leading-relaxed">
            {renderContent(msg.content, onInsertScript)}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

/**
 * Render message content with code block detection.
 * Code blocks between ``` markers get an "Insert" button.
 */
function renderContent(
  content: string,
  onInsertScript?: (script: string) => void,
): preact.ComponentChildren {
  const parts: preact.ComponentChildren[] = [];
  const codeBlockRegex = /```(?:\w*\n)?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    // Text before code block
    if (match.index > lastIndex) {
      parts.push(<span>{content.slice(lastIndex, match.index)}</span>);
    }

    const code = match[1].trim();
    parts.push(
      <div class="my-2 rounded bg-neutral-800 border border-neutral-700 min-w-0 overflow-hidden">
        <div class="flex items-center justify-between px-2 py-1 border-b border-neutral-700">
          <span class="text-xs text-neutral-500">Script</span>
          {onInsertScript && (
            <button
              onClick={() => onInsertScript(code)}
              class="text-xs px-2 py-0.5 rounded bg-blue-700 hover:bg-blue-600 text-white"
            >
              Insert
            </button>
          )}
        </div>
        <pre class="p-2 text-xs overflow-x-auto whitespace-pre-wrap">{code}</pre>
      </div>,
    );

    lastIndex = match.index + match[0].length;
  }

  // Remaining text
  if (lastIndex < content.length) {
    parts.push(<span>{content.slice(lastIndex)}</span>);
  }

  return parts.length > 0 ? parts : content;
}
