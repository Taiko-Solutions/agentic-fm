import type { FMContext } from '@/context/types';

interface ToolbarProps {
  context: FMContext | null;
  showXmlPreview: boolean;
  showChat: boolean;
  showLibrary: boolean;
  editorMode: 'script' | 'calc';
  onToggleXmlPreview: () => void;
  onToggleChat: () => void;
  onToggleLibrary: () => void;
  onRefreshContext: () => void;
  onClearChat: () => void;
  onNewScript: () => void;
  onValidate: () => void;
  onClipboard: () => void;
  onLoadScript: () => void;
  onOpenSettings: () => void;
  onSetEditorMode: (mode: 'script' | 'calc') => void;
}

export function Toolbar({
  context,
  showXmlPreview,
  showChat,
  showLibrary,
  editorMode,
  onToggleXmlPreview,
  onToggleChat,
  onToggleLibrary,
  onRefreshContext,
  onClearChat,
  onNewScript,
  onValidate,
  onClipboard,
  onLoadScript,
  onOpenSettings,
  onSetEditorMode,
}: ToolbarProps) {
  return (
    <div class="flex items-center gap-2 px-3 py-1.5 bg-neutral-800 border-b border-neutral-700 text-sm select-none">
      <span class="font-semibold text-neutral-200">agentic-fm</span>

      <div class="h-4 w-px bg-neutral-600 mx-1" />

      <ToolbarButton onClick={onNewScript} title="Create a new script">
        New
      </ToolbarButton>

      <ToolbarButton onClick={onValidate} title="Validate XML output">
        Validate
      </ToolbarButton>

      <ToolbarButton onClick={onClipboard} title="Convert to XML and copy to clipboard">
        Clipboard
      </ToolbarButton>

      <ToolbarButton onClick={onLoadScript} title="Search and load an existing script">
        Load Script
      </ToolbarButton>

      <div class="h-4 w-px bg-neutral-600 mx-1" />

      {/* Script / Calculation mode toggle */}
      <IconButton
        onClick={() => onSetEditorMode('script')}
        active={editorMode === 'script'}
        title="Script mode — step completions at line start, functions inside [ ]"
      >
        <ScriptIcon />
      </IconButton>
      <IconButton
        onClick={() => onSetEditorMode('calc')}
        active={editorMode === 'calc'}
        title="Calculation mode — function completions everywhere, no step suggestions"
      >
        <CalcIcon />
      </IconButton>

      <div class="h-4 w-px bg-neutral-600 mx-1" />

      <ToolbarButton
        onClick={onToggleXmlPreview}
        active={showXmlPreview}
        title="Toggle XML preview panel"
      >
        XML
      </ToolbarButton>

      <ToolbarButton
        onClick={onToggleChat}
        active={showChat}
        title="Toggle AI chat panel"
      >
        AI Chat
      </ToolbarButton>

      <ToolbarButton
        onClick={onToggleLibrary}
        active={showLibrary}
        title="Toggle library panel"
      >
        Library
      </ToolbarButton>

      {showChat && (
        <ToolbarButton onClick={onClearChat} title="Start a new AI chat (clears history)">
          New Chat
        </ToolbarButton>
      )}

      <div class="flex-1" />

      {context?.task && (
        <span class="text-neutral-400 text-xs truncate max-w-sm" title={context.task}>
          {context.task}
        </span>
      )}

      <ToolbarButton onClick={onOpenSettings} title="AI provider settings">
        Settings
      </ToolbarButton>

      <ToolbarButton onClick={onRefreshContext} title="Refresh context from CONTEXT.json">
        Refresh
      </ToolbarButton>
    </div>
  );
}

function ToolbarButton({
  onClick,
  title,
  active,
  children,
}: {
  onClick: () => void;
  title?: string;
  active?: boolean;
  children: preact.ComponentChildren;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      class={`px-2 py-0.5 rounded text-xs transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-neutral-700 hover:bg-neutral-600 text-neutral-300'
      }`}
    >
      {children}
    </button>
  );
}

function IconButton({
  onClick,
  title,
  active,
  children,
}: {
  onClick: () => void;
  title?: string;
  active?: boolean;
  children: preact.ComponentChildren;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      class={`flex items-center justify-center w-6 h-6 rounded transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-neutral-700 hover:bg-neutral-600 text-neutral-300'
      }`}
    >
      {children}
    </button>
  );
}

function ScriptIcon() {
  return (
    <svg viewBox="0 0 100 100" width="14" height="14" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="m82.812 6.25h-1.0312c-0.17578-0.015625-0.35547-0.015625-0.53125 0h-48.438c-6.0391 0-10.938 4.8984-10.938 10.938v51.562h-12.5c-1.7266 0-3.125 1.3984-3.125 3.125v10.938c0 6.0391 4.8984 10.938 10.938 10.938h48.438c0.17578 0.015625 0.35547 0.015625 0.53125 0h1.0312c6.0391 0 10.938-4.8984 10.938-10.938v-51.562h12.5c0.82812 0 1.625-0.32812 2.2109-0.91406 0.58594-0.58594 0.91406-1.3828 0.91406-2.2109v-10.938c0-2.9023-1.1523-5.6836-3.2031-7.7344s-4.832-3.2031-7.7344-3.2031zm-70.312 76.562v-7.8125h43.75v7.8125c0.007812 1.625 0.37891 3.2266 1.0938 4.6875h-40.156c-2.5898 0-4.6875-2.0977-4.6875-4.6875zm59.375 0c0 2.5898-2.0977 4.6875-4.6875 4.6875s-4.6875-2.0977-4.6875-4.6875v-10.938c0-0.82812-0.32812-1.625-0.91406-2.2109-0.58594-0.58594-1.3828-0.91406-2.2109-0.91406h-31.25v-51.562c0-2.5898 2.0977-4.6875 4.6875-4.6875h40.156c-0.71484 1.4609-1.0859 3.0625-1.0938 4.6875zm15.625-57.812h-9.375v-7.8125c0-2.5898 2.0977-4.6875 4.6875-4.6875s4.6875 2.0977 4.6875 4.6875zm-25 3.125c0 0.82812-0.32812 1.625-0.91406 2.2109-0.58594 0.58594-1.3828 0.91406-2.2109 0.91406h-18.75c-1.7266 0-3.125-1.3984-3.125-3.125s1.3984-3.125 3.125-3.125h18.75c0.82812 0 1.625 0.32812 2.2109 0.91406 0.58594 0.58594 0.91406 1.3828 0.91406 2.2109zm-9.375 18.75c0 0.82812-0.32812 1.625-0.91406 2.2109-0.58594 0.58594-1.3828 0.91406-2.2109 0.91406h-9.375c-1.7266 0-3.125-1.3984-3.125-3.125s1.3984-3.125 3.125-3.125h9.375c0.82812 0 1.625 0.32812 2.2109 0.91406 0.58594 0.58594 0.91406 1.3828 0.91406 2.2109z" />
    </svg>
  );
}

function CalcIcon() {
  return (
    <svg viewBox="0 0 100 100" width="14" height="14" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="m72.562 71.188c-1.2656-0.003906-2.3984-0.76953-2.8789-1.9414-0.48047-1.168-0.20703-2.5117 0.69141-3.4023l15.844-15.844-15.844-15.844c-1.0625-1.2383-0.99219-3.0898 0.16406-4.2422 1.1523-1.1562 3.0039-1.2266 4.2422-0.16406l18.062 18.031c0.58984 0.58594 0.92578 1.3867 0.92578 2.2188s-0.33594 1.6328-0.92578 2.2188l-18.062 18.031c-0.58594 0.59766-1.3828 0.93359-2.2188 0.9375zm-42.938-0.9375c1.2109-1.2188 1.2109-3.1875 0-4.4062l-15.844-15.844 15.844-15.844c1.0625-1.2383 0.99219-3.0898-0.16406-4.2422-1.1523-1.1562-3.0039-1.2266-4.2422-0.16406l-18.062 18.031c-0.58984 0.58594-0.92578 1.3867-0.92578 2.2188s0.33594 1.6328 0.92578 2.2188l18.062 18.031c0.58594 0.59766 1.3828 0.93359 2.2188 0.9375 0.82422-0.011719 1.6094-0.34766 2.1875-0.9375zm14.125-0.78125 18.031-36.125c0.77344-1.5352 0.15625-3.4062-1.375-4.1875-1.5273-0.75-3.3789-0.14062-4.1562 1.375l-18.062 36.125c-0.77344 1.5352-0.15625 3.4062 1.375 4.1875 0.4375 0.21875 0.91797 0.33594 1.4062 0.34375 1.1758-0.003906 2.25-0.66797 2.7812-1.7188z" />
    </svg>
  );
}
