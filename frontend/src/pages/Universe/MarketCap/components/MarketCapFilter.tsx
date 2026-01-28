import { Slider } from '../../../../components/ui/slider';

interface MarketCapFilterProps {
  topN: number;
  maxValue: number;
  onChange: (value: number) => void;
}

export const MarketCapFilter = ({ topN, maxValue, onChange }: MarketCapFilterProps) => {
  const handleSliderChange = (values: number[]) => {
    onChange(values[0]);
  };

  return (
    <div className="flex items-center gap-4 pr-4">
      <label className="text-sm text-muted-foreground">
        Top {topN} / {maxValue}
      </label>
      <Slider
        min={1}
        max={maxValue}
        step={1}
        value={[topN]}
        onValueChange={handleSliderChange}
        className="w-58"
      />
    </div>
  );
};
