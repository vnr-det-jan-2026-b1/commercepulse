interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  accent?: 'default' | 'warning' | 'danger' | 'success';
}

const accentClass = {
  default: 'border-blue-500',
  warning: 'border-yellow-500',
  danger: 'border-red-500',
  success: 'border-green-500',
};

export default function KpiCard({ title, value, subtitle, accent = 'default' }: Props) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border-l-4 ${accentClass[accent]} p-5`}>
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}
