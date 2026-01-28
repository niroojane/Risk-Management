import { useState, useEffect } from 'react';
import { Search } from 'lucide-react';
import { Input } from '../ui/input';

export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  debounceMs?: number;
  showResultCount?: boolean;
  resultCount?: number;
  className?: string;
}

export const SearchBar = ({
  value,
  onChange,
  placeholder = 'Search...',
  debounceMs = 300,
  showResultCount = false,
  resultCount = 0,
  className = '',
}: SearchBarProps) => {
  const [localValue, setLocalValue] = useState(value);

  // Debounce effect
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [localValue, debounceMs, onChange]);

  // Sync with external value changes
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalValue(e.target.value);
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="relative flex-1 max-w-sm">
        <Search
          className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          placeholder={placeholder}
          value={localValue}
          onChange={handleChange}
          className="pl-9"
        />
      </div>
      {showResultCount && localValue && (
        <span className="text-sm text-muted-foreground">
          {resultCount} result{resultCount !== 1 ? 's' : ''}
        </span>
      )}
    </div>
  );
};
