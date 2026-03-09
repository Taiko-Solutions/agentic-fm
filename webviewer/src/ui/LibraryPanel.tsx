import { useState, useEffect } from 'preact/hooks';
import { fetchLibrary, fetchLibraryItem, saveLibraryItem } from '@/api/client';
import type { LibraryItem } from '@/api/client';

interface LibraryPanelProps {
  onInsert: (content: string) => void;
  getEditorContent: () => string;
}

export function LibraryPanel({ onInsert, getEditorContent }: LibraryPanelProps) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [loading, setLoading] = useState(false);
  const [insertingPath, setInsertingPath] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    fetchLibrary()
      .then(fetched => {
        setItems(fetched);
        const cats = Array.from(new Set(fetched.map(i => i.category))).sort();
        setCategories(cats);
        setError('');
      })
      .catch(() => setError('Failed to load library'))
      .finally(() => setLoading(false));
  }, []);

  const filteredItems = selectedCategory === 'All'
    ? items
    : items.filter(i => i.category === selectedCategory);

  const handleInsert = async (item: LibraryItem) => {
    setInsertingPath(item.path);
    try {
      const content = await fetchLibraryItem(item.path);
      onInsert(content);
      setStatus(`Inserted: ${item.name}`);
    } catch {
      setStatus(`Failed to load: ${item.name}`);
    } finally {
      setInsertingPath(null);
    }
  };

  const handleSaveSelection = async () => {
    const content = getEditorContent();
    if (!content.trim()) {
      setStatus('Editor is empty');
      return;
    }

    const name = prompt('Name for this library item (e.g. "My Pattern"):');
    if (!name?.trim()) return;

    const category = prompt(
      `Category (existing: ${categories.join(', ')}):\nEnter one of the above or a new category name.`,
    );
    if (!category?.trim()) return;

    const safeName = name.trim().replace(/[/\\?%*:|"<>]/g, '-');
    const safeCategory = category.trim().replace(/[/\\?%*:|"<>]/g, '-');
    const ext = content.trim().startsWith('<') ? '.xml' : '.md';
    const itemPath = `${safeCategory}/${safeName}${ext}`;

    try {
      await saveLibraryItem(itemPath, content);
      setStatus(`Saved to library: ${itemPath}`);
      // Refresh the list
      const fetched = await fetchLibrary();
      setItems(fetched);
      const cats = Array.from(new Set(fetched.map(i => i.category))).sort();
      setCategories(cats);
    } catch {
      setStatus('Failed to save to library');
    }
  };

  return (
    <div class="flex flex-col h-full bg-neutral-900 text-neutral-300 text-xs">
      {/* Header */}
      <div class="flex items-center gap-2 px-3 py-2 border-b border-neutral-700 shrink-0">
        <span class="font-semibold text-neutral-200 text-sm">Library</span>
        <div class="flex-1" />
        <button
          onClick={handleSaveSelection}
          title="Save current editor content to library"
          class="px-2 py-0.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-300 transition-colors"
        >
          Save Selection
        </button>
      </div>

      {/* Category filter */}
      <div class="flex flex-wrap gap-1 px-3 py-2 border-b border-neutral-700 shrink-0">
        {['All', ...categories].map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            class={`px-2 py-0.5 rounded transition-colors ${
              selectedCategory === cat
                ? 'bg-blue-600 text-white'
                : 'bg-neutral-700 hover:bg-neutral-600 text-neutral-300'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Status / error */}
      {(status || error) && (
        <div class={`px-3 py-1 text-xs shrink-0 ${error ? 'text-red-400' : 'text-green-400'}`}>
          {error || status}
        </div>
      )}

      {/* Item list */}
      <div class="flex-1 overflow-y-auto min-h-0">
        {loading && (
          <div class="px-3 py-4 text-neutral-500">Loading...</div>
        )}
        {!loading && filteredItems.length === 0 && (
          <div class="px-3 py-4 text-neutral-500">
            {items.length === 0 ? 'No library items found' : 'No items in this category'}
          </div>
        )}
        {!loading && filteredItems.map(item => (
          <div
            key={item.path}
            class="flex items-center gap-2 px-3 py-1.5 border-b border-neutral-800 hover:bg-neutral-800 transition-colors"
          >
            <div class="flex-1 min-w-0">
              <span class="text-neutral-200 truncate block" title={item.path}>
                {item.name}
              </span>
              {selectedCategory === 'All' && (
                <span class="text-neutral-500">{item.category}</span>
              )}
            </div>
            <button
              onClick={() => handleInsert(item)}
              disabled={insertingPath === item.path}
              title={`Insert ${item.name} into editor`}
              class="shrink-0 px-2 py-0.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-300 transition-colors disabled:opacity-50"
            >
              {insertingPath === item.path ? '...' : 'Insert'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
