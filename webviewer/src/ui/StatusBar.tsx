interface StatusBarProps {
  status: string;
  solution?: string;
  layout?: string;
}

export function StatusBar({ status, solution, layout }: StatusBarProps) {
  return (
    <div class="flex items-center gap-3 px-3 py-1 bg-blue-900 text-xs text-blue-200 select-none">
      <span>{status}</span>
      <div class="flex-1" />
      {solution && <span class="text-blue-300">{solution}</span>}
      {layout && (
        <>
          <span class="text-blue-500">|</span>
          <span class="text-blue-300">{layout}</span>
        </>
      )}
    </div>
  );
}
