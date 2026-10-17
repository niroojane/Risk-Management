import { Slider } from '@/components/ui/slider';

// TODO: Implements props: showTotal (boolean) for visibility and totalPosition ('left' | 'right') for placement
interface MarketCapFilterProps {
  displayCount: number;
  maxValue: number;
  onChange: (value: number) => void;
}

// TODO: Make this filter component reusable/common across the app
export const MarketCapFilter = ({ displayCount, maxValue, onChange }: MarketCapFilterProps) => {
  const handleSliderChange = (values: number[]) => {
    onChange(values[0]);
  };

  return (
    <div className="flex items-center gap-4 pr-4">
      <span className="text-sm text-muted-foreground" aria-label="Asset count display">
        {displayCount} / {maxValue}
      </span>
      <Slider
        min={1}
        max={maxValue}
        step={1}
        value={[displayCount]}
        onValueChange={handleSliderChange}
        className="w-58"
        aria-label="Select number of assets to display"
      />
    </div>
  );
};
