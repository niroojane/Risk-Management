import { Link } from 'react-router-dom';
import { ReturnsTable } from '@/components/common/table/ReturnsTable';
import { RiskTable } from '@/components/common/table/RiskTable';
import { useMarketData } from '@/hooks/useMarketData';

const Strategy = () => {
  const { data: pricesData } = useMarketData();

  if (!pricesData) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <p className="text-muted-foreground text-center">
          No market data available. Please generate data from the Prices page first.
        </p>
        <Link
          to="/prices"
          className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Go to Prices
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Strategy & Portfolio Optimization</h1>
        <p className="text-muted-foreground mt-2">Portfolio optimization with constraints, allocation grid</p>
      </div>

      {pricesData.data.returns && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-foreground">Returns</h2>
          <ReturnsTable data={pricesData.data.returns.assets} />
        </section>
      )}

      {pricesData.data.risk && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-foreground">Risk Metrics</h2>
          <RiskTable data={pricesData.data.risk} />
        </section>
      )}
    </div>
  );
};

export default Strategy;
