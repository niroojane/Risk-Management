import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

export interface SortIconProps {
  sortDirection: false | 'asc' | 'desc';
  className?: string;
}

//Reusable sort icon component for table columns
export const SortIcon = ({ sortDirection, className = '' }: SortIconProps) => {
  const iconClass = 'h-4 w-4';
  const unsortedClass = `${iconClass} opacity-50`;

  return (
    <span className={`text-muted-foreground ${className}`} aria-hidden="true">
      {sortDirection === 'asc' && <ChevronUp className={iconClass} />}
      {sortDirection === 'desc' && <ChevronDown className={iconClass} />}
      {!sortDirection && <ChevronsUpDown className={unsortedClass} />}
    </span>
  );
};