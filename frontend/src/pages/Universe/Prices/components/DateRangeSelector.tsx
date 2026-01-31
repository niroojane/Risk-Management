import { useState } from 'react';
import { format } from 'date-fns';
import { Calendar as CalendarIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

type DateRange = {
  from: Date | undefined;
  to?: Date | undefined;
};

const getDefaultDateRange = (): DateRange => {
  const today = new Date();
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(today.getFullYear() - 1);

  return {
    from: oneYearAgo,
    to: today,
  };
};

const QUICK_SELECTS = [
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
  { label: '1 year', days: 365 },
];

export const DateRangeSelector = () => {
  const [date, setDate] = useState<DateRange | undefined>(getDefaultDateRange());

  const handleQuickSelect = (days: number) => {
    const today = new Date();
    const pastDate = new Date();
    pastDate.setDate(today.getDate() - days);

    setDate({
      from: pastDate,
      to: today,
    });
  };

  const formatDateRange = (dateRange: DateRange | undefined): string => {
    if (!dateRange?.from) {
      return 'Pick a date range';
    }

    if (dateRange.to) {
      return `${format(dateRange.from, 'dd/MM/yyyy')} - ${format(dateRange.to, 'dd/MM/yyyy')}`;
    }

    return format(dateRange.from, 'dd/MM/yyyy');
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                'w-[300px] justify-start text-left font-normal',
                !date && 'text-muted-foreground'
              )}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {formatDateRange(date)}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="range"
              defaultMonth={date?.from}
              selected={date}
              onSelect={setDate}
              numberOfMonths={2}
              disabled={(date) => date > new Date()}
            />
          </PopoverContent>
        </Popover>
      </div>

      <div className="flex gap-2">
        {QUICK_SELECTS.map((preset) => (
          <Button
            key={preset.label}
            variant="outline"
            size="sm"
            onClick={() => handleQuickSelect(preset.days)}
            className="text-xs"
          >
            {preset.label}
          </Button>
        ))}
      </div>
    </div>
  );
};
