import { SelectField } from '@/components/workspace';

interface PairSelectProps {
  names: string[];
  fund: string;
  benchmark: string;
  onFund: (name: string) => void;
  onBenchmark: (name: string) => void;
  fundLabel?: string;
}

/** Fund / Benchmark series pickers */
export const PairSelect = ({
  names,
  fund,
  benchmark,
  onFund,
  onBenchmark,
  fundLabel = 'Fund',
}: PairSelectProps) => (
  <>
    <SelectField
      label={fundLabel}
      value={fund}
      options={names}
      onChange={onFund}
      selectClassName="w-60"
    />
    <SelectField
      label="Benchmark"
      value={benchmark}
      options={names}
      onChange={onBenchmark}
      selectClassName="w-60"
    />
  </>
);
