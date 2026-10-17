import { useState } from 'react';
import { Filter } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { FilterComponent } from './FilterComponent';
import type { DateRange } from '../types/filters';

interface FilterDialogProps {
  symbols: string[];
  onSymbolsChange: (symbols: string[]) => void;
  dateRange: DateRange | undefined;
  onDateRangeChange: (dateRange: DateRange | undefined) => void;
  onGenerateTable: () => void;
}

export const FilterDialog = ({
  symbols,
  onSymbolsChange,
  dateRange,
  onDateRangeChange,
  onGenerateTable,
}: FilterDialogProps) => {
  const [open, setOpen] = useState(false);

  const handleGenerate = () => {
    onGenerateTable();
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="cursor-pointer">
          <Filter className="h-4 w-4 mr-2 cursor" />
          View Filters
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto w-[95vw]">
        <DialogHeader>
          <DialogTitle>Price Data Filters</DialogTitle>
        </DialogHeader>
        <FilterComponent
          symbols={symbols}
          onSymbolsChange={onSymbolsChange}
          dateRange={dateRange}
          onDateRangeChange={onDateRangeChange}
          onGenerateTable={handleGenerate}
        />
      </DialogContent>
    </Dialog>
  );
};
