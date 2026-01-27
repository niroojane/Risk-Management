function Universe() {
  const data = [
    { symbol: 'BTC', price: 45230, marketCap: 885000000000, change24h: 2.5 },
    { symbol: 'ETH', price: 2340, marketCap: 281000000000, change24h: -1.2 },
    { symbol: 'BNB', price: 320, marketCap: 49000000000, change24h: 0.8 },
    { symbol: 'SOL', price: 98, marketCap: 42000000000, change24h: 5.3 },
    { symbol: 'XRP', price: 0.62, marketCap: 33000000000, change24h: -0.5 },
  ];

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Risk Management - Market Cap</h1>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Symbol
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price (USD)
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Market Cap
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  24h Change
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.map((row) => (
                <tr key={row.symbol} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {row.symbol}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    ${row.price.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    ${(row.marketCap / 1e9).toFixed(1)}B
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${
                    row.change24h >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {row.change24h >= 0 ? '+' : ''}{row.change24h}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Universe;
