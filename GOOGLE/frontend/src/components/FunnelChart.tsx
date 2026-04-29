import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { FunnelDataPoint } from '../types/index';

interface Props {
  data: FunnelDataPoint[];
}

export default function FunnelChart({ data }: Props) {
  const formatted = data.map(d => ({
    date: d.metric_date?.slice(5),
    Impressions: d.impressions,
    Clicks: d.clicks,
    'Add to Cart': d.add_to_cart,
    Purchases: d.purchases,
  }));

  return (
    <div className="bg-white rounded-xl shadow-sm p-5">
      <h2 className="text-sm font-semibold text-gray-600 mb-4">Traffic Funnel (7d)</h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={formatted}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="Impressions" fill="#93c5fd" radius={[3,3,0,0]} />
          <Bar dataKey="Clicks" fill="#3b82f6" radius={[3,3,0,0]} />
          <Bar dataKey="Add to Cart" fill="#1d4ed8" radius={[3,3,0,0]} />
          <Bar dataKey="Purchases" fill="#1e3a8a" radius={[3,3,0,0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
