import type { InventoryAlert } from '../types';

interface Props {
  alerts: InventoryAlert[];
}

const riskColor: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700',
  HIGH:     'bg-orange-100 text-orange-700',
  MEDIUM:   'bg-yellow-100 text-yellow-700',
  OK:       'bg-green-100 text-green-700',
};

export default function InventoryAlerts({ alerts }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-5">
      <h2 className="text-sm font-semibold text-gray-600 mb-4">Inventory Alerts</h2>
      {alerts.length === 0 ? (
        <p className="text-sm text-gray-400">No alerts</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b">
                <th className="pb-2 font-medium">SKU</th>
                <th className="pb-2 font-medium">Marketplace</th>
                <th className="pb-2 font-medium">Stock</th>
                <th className="pb-2 font-medium">Days Left</th>
                <th className="pb-2 font-medium">Risk</th>
                <th className="pb-2 font-medium">Reorder Qty</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a, i) => (
                <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="py-2 font-mono text-xs">{a.sku}</td>
                  <td className="py-2">{a.marketplace}</td>
                  <td className="py-2">{a.available_stock}</td>
                  <td className="py-2">{a.days_until_stockout?.toFixed(1) ?? '—'}</td>
                  <td className="py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${riskColor[a.risk_level] ?? ''}`}>
                      {a.risk_level}
                    </span>
                  </td>
                  <td className="py-2">{a.recommended_reorder_qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
