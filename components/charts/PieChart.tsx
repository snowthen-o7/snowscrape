/**
 * Pie Chart Component
 * Reusable pie chart using Recharts
 */

'use client';

import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface PieChartProps {
  data: any[];
  dataKey: string;
  nameKey: string;
  colors?: string[];
  height?: number;
  title?: string;
}

const DEFAULT_COLORS = ['#00D9FF', '#0A2540', '#22C55E', '#EF4444', '#F59E0B'];

export function PieChart({
  data,
  dataKey,
  nameKey,
  colors = DEFAULT_COLORS,
  height = 300,
  title,
}: PieChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="mb-4 text-lg font-semibold text-foreground">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsPieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={(entry: any) => `${entry[nameKey]}: ${entry[dataKey]}`}
            outerRadius={80}
            fill="#8884d8"
            dataKey={dataKey}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
}
