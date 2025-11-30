import React from 'react';

const StatsCard = ({ title, value, icon: Icon, trend, color = 'teal' }) => {
  const colorClasses = {
    teal: 'bg-teal-50 text-teal-700',
    emerald: 'bg-emerald-50 text-emerald-700',
    blue: 'bg-blue-50 text-blue-700',
    amber: 'bg-amber-50 text-amber-700',
  };

  return (
    <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm hover:shadow-md transition-all group" data-testid={`stats-card-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-slate-500 mb-2" style={{ fontFamily: 'Inter, sans-serif' }}>
            {title}
          </p>
          <p className="text-3xl font-bold text-slate-900 mb-1" style={{ fontFamily: 'Manrope, sans-serif' }}>
            {value}
          </p>
          {trend && (
            <p className="text-sm text-emerald-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              {trend}
            </p>
          )}
        </div>
        {Icon && (
          <div className={`p-3 rounded-xl ${colorClasses[color]} group-hover:scale-110 transition-transform`}>
            <Icon className="w-6 h-6" strokeWidth={1.5} />
          </div>
        )}
      </div>
    </div>
  );
};

export default StatsCard;