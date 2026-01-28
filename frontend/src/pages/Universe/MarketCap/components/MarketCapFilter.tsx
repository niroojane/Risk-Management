import { Slider } from '../../../../components/ui/slider';

interface MarketCapFilterProps {
  topN: number;
  maxValue: number;
  onChange: (value: number[]) => void;
}

export const MarketCapFilter = ({ topN, maxValue, onChange }: MarketCapFilterProps) => {
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
        onValueChange={onChange}
        className="w-58"
      />
    </div>
  );
};
