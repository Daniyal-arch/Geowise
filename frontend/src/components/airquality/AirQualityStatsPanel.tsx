import React from 'react';
import {
    AirQualityResponse,
    POLLUTANT_INFO
} from '@/types/airQuality';
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from 'recharts';

interface AirQualityStatsPanelProps {
    data: AirQualityResponse;
}

export default function AirQualityStatsPanel({ data }: AirQualityStatsPanelProps) {
    const { location, air_quality_level, pollutant_statistics, monthly_trend, yearly_trend } = data;

    return (
        <div className="h-full overflow-y-auto bg-slate-900/95 backdrop-blur-sm">
            <div className="p-5 space-y-5">
                {/* Location Info */}
                <div>
                    <h2 className="text-xl font-bold text-white mb-1">{location.name}</h2>
                    <p className="text-sm text-gray-400">{location.country}</p>
                </div>

                {/* Air Quality Level */}
                {air_quality_level && (
                    <div
                        className="rounded-xl p-4 border-2"
                        style={{
                            backgroundColor: `${air_quality_level.color}15`,
                            borderColor: air_quality_level.color
                        }}
                    >
                        <div className="flex items-center gap-3 mb-2">
                            <span className="text-3xl">{air_quality_level.emoji}</span>
                            <div>
                                <h3 className="text-lg font-bold text-white">{air_quality_level.level}</h3>
                                <p className="text-xs text-gray-300">Air Quality Index</p>
                            </div>
                        </div>
                        <p className="text-sm text-gray-200 leading-relaxed">{air_quality_level.health_advice}</p>
                    </div>
                )}

                {/* Pollutant Statistics */}
                <div>
                    <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
                        Pollutant Levels
                    </h3>
                    <div className="space-y-2">
                        {Object.entries(pollutant_statistics).map(([key, stat]) => {
                            if (stat.error) return null;
                            const info = POLLUTANT_INFO[key];

                            return (
                                <div
                                    key={key}
                                    className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50"
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xl">{info?.icon || '📊'}</span>
                                            <div>
                                                <p className="text-sm font-semibold text-white">{stat.name}</p>
                                                <p className="text-[10px] text-gray-500">{key}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-lg font-bold" style={{ color: info?.color || '#fff' }}>
                                                {stat.mean.toFixed(1)}
                                            </p>
                                            <p className="text-[10px] text-gray-400">{stat.unit}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4 text-[10px] text-gray-500">
                                        <span>Min: {stat.min.toFixed(1)}</span>
                                        <span>Max: {stat.max.toFixed(1)}</span>
                                    </div>
                                    <p className="text-[11px] text-gray-400 mt-2 leading-relaxed">
                                        {stat.health_impact}
                                    </p>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Monthly Trend Graph */}
                {monthly_trend && monthly_trend.data.length > 0 && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
                            Monthly Trend ({monthly_trend.year})
                        </h3>
                        <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/50">
                            <ResponsiveContainer width="100%" height={200}>
                                <LineChart data={monthly_trend.data}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis
                                        dataKey="month_name"
                                        stroke="#9ca3af"
                                        style={{ fontSize: '11px' }}
                                    />
                                    <YAxis
                                        stroke="#9ca3af"
                                        style={{ fontSize: '11px' }}
                                        label={{
                                            value: monthly_trend.unit,
                                            angle: -90,
                                            position: 'insideLeft',
                                            style: { fontSize: '10px', fill: '#9ca3af' }
                                        }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: '#1e293b',
                                            border: '1px solid #475569',
                                            borderRadius: '8px',
                                            fontSize: '12px'
                                        }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        dot={{ fill: '#3b82f6', r: 3 }}
                                        activeDot={{ r: 5 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Yearly Trend Graph */}
                {yearly_trend && yearly_trend.data.length > 0 && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wider">
                            Yearly Trend
                        </h3>
                        <div className="bg-slate-800/50 rounded-lg p-3 mb-3 border border-slate-700/50">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Total Change</p>
                                    <p className={`text-xl font-bold ${yearly_trend.total_change >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                                        {yearly_trend.total_change >= 0 ? '+' : ''}{yearly_trend.total_change}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Change %</p>
                                    <p className={`text-xl font-bold ${yearly_trend.change_percent >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                                        {yearly_trend.change_percent >= 0 ? '+' : ''}{yearly_trend.change_percent}%
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/50">
                            <ResponsiveContainer width="100%" height={200}>
                                <BarChart data={yearly_trend.data}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis
                                        dataKey="year"
                                        stroke="#9ca3af"
                                        style={{ fontSize: '11px' }}
                                    />
                                    <YAxis
                                        stroke="#9ca3af"
                                        style={{ fontSize: '11px' }}
                                        label={{
                                            value: yearly_trend.unit,
                                            angle: -90,
                                            position: 'insideLeft',
                                            style: { fontSize: '10px', fill: '#9ca3af' }
                                        }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: '#1e293b',
                                            border: '1px solid #475569',
                                            borderRadius: '8px',
                                            fontSize: '12px'
                                        }}
                                    />
                                    <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Data Source */}
                <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50 text-[11px] text-gray-400">
                    <div className="font-semibold text-gray-300 mb-2">Data Source</div>
                    <div className="space-y-1">
                        <div><strong className="text-gray-400">Source:</strong> {data.methodology.data_source}</div>
                        <div><strong className="text-gray-400">Resolution:</strong> {data.methodology.resolution}</div>
                        <div><strong className="text-gray-400">Coverage:</strong> {data.methodology.temporal_coverage}</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
