import React from 'react';
import { SurfaceWaterResponse } from '@/types/water';
import { TrendingDown, TrendingUp, Droplet, AlertTriangle } from 'lucide-react';

interface WaterStatsPanelProps {
    data: SurfaceWaterResponse;
    isLoading?: boolean;
}

export default function WaterStatsPanel({ data, isLoading = false }: WaterStatsPanelProps) {
    if (isLoading) {
        return (
            <aside className="w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-800 h-full p-8 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
                    <span className="text-gray-400 text-sm">Analyzing water changes...</span>
                </div>
            </aside>
        );
    }

    if (!data) return null;

    const { location_name, country, water_body_type, description, statistics, time_series, methodology, animation, start_year, end_year } = data;

    // Check if required data exists
    if (!statistics) {
        return (
            <aside className="w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-800 h-full p-8 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-gray-400">No data available</p>
                </div>
            </aside>
        );
    }

    // Determine water status based on loss percentage
    const getWaterStatus = () => {
        const lossPercent = statistics.loss_percent;
        if (lossPercent > 50) return { label: 'CRITICAL', color: 'red' };
        if (lossPercent > 10) return { label: 'DECLINING', color: 'yellow' };
        if (statistics.net_change_km2 > 0 && Math.abs(statistics.net_change_km2) > statistics.max_extent_km2 * 0.1) {
            return { label: 'GROWING', color: 'blue' };
        }
        return { label: 'STABLE', color: 'green' };
    };

    const status = getWaterStatus();

    return (
        <aside className="w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-800 overflow-y-auto h-full text-white">
            <div className="p-5 space-y-6">

                {/* Header */}
                <div className="border-b border-gray-800 pb-4">
                    <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400">
                        {location_name}
                    </h2>
                    {country && (
                        <p className="text-sm text-gray-400 mt-1">{country}</p>
                    )}
                    {water_body_type && (
                        <p className="text-xs text-gray-500 mt-1 capitalize">{water_body_type}</p>
                    )}
                    {description && (
                        <p className="text-xs text-gray-400 mt-2 italic">{description}</p>
                    )}
                    <div className="flex justify-between items-center mt-3 text-xs font-mono text-gray-500 bg-gray-800/50 p-2 rounded">
                        <span>{start_year}</span>
                        <span className="border-b border-gray-600 w-full mx-2 opacity-30"></span>
                        <span>{end_year}</span>
                    </div>
                </div>

                {/* Water Status Badge */}
                <div className={`p-3 rounded-lg border flex items-center justify-between ${
                    status.color === 'red' ? 'bg-red-900/30 border-red-500/50' :
                    status.color === 'yellow' ? 'bg-yellow-900/30 border-yellow-500/50' :
                    status.color === 'blue' ? 'bg-blue-900/30 border-blue-500/50' :
                    'bg-green-900/30 border-green-500/50'
                }`}>
                    <div className="flex items-center gap-2">
                        {status.color === 'red' && <AlertTriangle size={16} className="text-red-400" />}
                        {status.color === 'yellow' && <TrendingDown size={16} className="text-yellow-400" />}
                        {status.color === 'blue' && <TrendingUp size={16} className="text-blue-400" />}
                        {status.color === 'green' && <Droplet size={16} className="text-green-400" />}
                        <span className="text-sm font-semibold">Water Status</span>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full border ${
                        status.color === 'red' ? 'bg-red-900/50 border-red-500/50 text-red-300' :
                        status.color === 'yellow' ? 'bg-yellow-900/50 border-yellow-500/50 text-yellow-300' :
                        status.color === 'blue' ? 'bg-blue-900/50 border-blue-500/50 text-blue-300' :
                        'bg-green-900/50 border-green-500/50 text-green-300'
                    }`}>
                        {status.label}
                    </span>
                </div>

                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-800/40 p-3 rounded-lg border border-gray-700/50">
                        <div className="flex items-center gap-2 text-gray-400 mb-1">
                            <Droplet size={14} />
                            <span className="text-xs">Current Area</span>
                        </div>
                        <div className="text-lg font-bold text-white">
                            {statistics.current_total_km2.toLocaleString()} <span className="text-xs font-normal text-gray-500">km²</span>
                        </div>
                        <div className={`text-xs mt-1 ${statistics.net_change_km2 < 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {statistics.net_change_km2 > 0 ? '+' : ''}{statistics.net_change_km2.toLocaleString()} km²
                        </div>
                    </div>

                    <div className="bg-gray-800/40 p-3 rounded-lg border border-gray-700/50">
                        <div className="flex items-center gap-2 text-gray-400 mb-1">
                            <TrendingDown size={14} />
                            <span className="text-xs">Water Loss</span>
                        </div>
                        <div className="text-lg font-bold text-white">
                            {statistics.loss_percent.toFixed(1)}%
                        </div>
                        <div className="text-xs text-red-400 mt-1">
                            {statistics.lost_water_km2.toLocaleString()} km² lost
                        </div>
                    </div>
                </div>

                {/* Permanent vs Seasonal Water */}
                {(statistics.current_permanent_km2 > 0 || statistics.current_seasonal_km2 > 0) && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                            <div className="w-1 h-4 bg-blue-500 rounded-full"></div>
                            Water Composition
                        </h3>
                        <div className="space-y-2">
                            <div className="bg-gray-800/30 rounded p-3">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-xs text-gray-400">Permanent Water</span>
                                    <span className="text-sm font-bold text-blue-400">{statistics.current_permanent_km2.toLocaleString()} km²</span>
                                </div>
                                <div className="h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-500"
                                        style={{ width: `${(statistics.current_permanent_km2 / statistics.current_total_km2) * 100}%` }}
                                    />
                                </div>
                            </div>
                            <div className="bg-gray-800/30 rounded p-3">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-xs text-gray-400">Seasonal Water</span>
                                    <span className="text-sm font-bold text-cyan-400">{statistics.current_seasonal_km2.toLocaleString()} km²</span>
                                </div>
                                <div className="h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-cyan-500"
                                        style={{ width: `${(statistics.current_seasonal_km2 / statistics.current_total_km2) * 100}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Max Extent Info */}
                <div className="bg-gray-800/30 p-3 rounded-lg border border-gray-700/50">
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">Maximum Historical Extent</span>
                        <span className="text-sm font-bold text-cyan-300">{statistics.max_extent_km2.toLocaleString()} km²</span>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                        Current area is {statistics.current_vs_max_percent.toFixed(1)}% of historical maximum
                    </div>
                </div>

                {/* Time Series Evolution - Graph */}
                {time_series && time_series.length > 0 && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                            <div className="w-1 h-4 bg-cyan-500 rounded-full"></div>
                            Area Evolution ({time_series.length} data points)
                        </h3>
                        <div className="bg-gray-800/30 p-3 rounded-lg">
                            {/* Simple SVG Line Graph */}
                            <svg width="100%" height="120" className="overflow-visible">
                                {/* Y-axis labels and grid lines */}
                                <line x1="30" y1="10" x2="30" y2="100" stroke="#4b5563" strokeWidth="1" />
                                <line x1="30" y1="100" x2="100%" y2="100" stroke="#4b5563" strokeWidth="1" />

                                {/* Calculate graph dimensions */}
                                {(() => {
                                    const minArea = Math.min(...time_series.map(p => p.water_area_km2));
                                    const maxArea = Math.max(...time_series.map(p => p.water_area_km2));
                                    const areaRange = maxArea - minArea || 1;
                                    const minYear = time_series[0].year;
                                    const maxYear = time_series[time_series.length - 1].year;
                                    const yearRange = maxYear - minYear || 1;

                                    const graphWidth = 280; // Approximate width available
                                    const graphHeight = 90;
                                    const padding = 30;

                                    // Generate path
                                    const points = time_series.map((point, i) => {
                                        const x = padding + ((point.year - minYear) / yearRange) * graphWidth;
                                        const y = 10 + graphHeight - ((point.water_area_km2 - minArea) / areaRange) * graphHeight;
                                        return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                                    }).join(' ');

                                    return (
                                        <>
                                            {/* Area fill */}
                                            <path
                                                d={`${points} L ${padding + graphWidth} 100 L ${padding} 100 Z`}
                                                fill="url(#waterGradient)"
                                                opacity="0.3"
                                            />

                                            {/* Line */}
                                            <path
                                                d={points}
                                                stroke="#22d3ee"
                                                strokeWidth="2"
                                                fill="none"
                                            />

                                            {/* Points */}
                                            {time_series.map((point) => {
                                                const x = padding + ((point.year - minYear) / yearRange) * graphWidth;
                                                const y = 10 + graphHeight - ((point.water_area_km2 - minArea) / areaRange) * graphHeight;
                                                return (
                                                    <circle
                                                        key={point.year}
                                                        cx={x}
                                                        cy={y}
                                                        r="3"
                                                        fill="#22d3ee"
                                                        className="cursor-pointer hover:r-4"
                                                    >
                                                        <title>{point.year}: {point.water_area_km2.toLocaleString()} km²</title>
                                                    </circle>
                                                );
                                            })}

                                            {/* Year labels */}
                                            <text x={padding} y="115" fontSize="9" fill="#9ca3af" textAnchor="middle">
                                                {minYear}
                                            </text>
                                            <text x={padding + graphWidth} y="115" fontSize="9" fill="#9ca3af" textAnchor="middle">
                                                {maxYear}
                                            </text>

                                            {/* Gradient definition */}
                                            <defs>
                                                <linearGradient id="waterGradient" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.5" />
                                                    <stop offset="100%" stopColor="#22d3ee" stopOpacity="0" />
                                                </linearGradient>
                                            </defs>
                                        </>
                                    );
                                })()}
                            </svg>

                            {/* Legend */}
                            <div className="mt-3 flex justify-between text-xs text-gray-400">
                                <span>Min: {Math.min(...time_series.map(p => p.water_area_km2)).toLocaleString()} km²</span>
                                <span>Max: {Math.max(...time_series.map(p => p.water_area_km2)).toLocaleString()} km²</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Methodology */}
                {methodology && (
                    <div className="bg-gray-800/30 p-3 rounded-lg border border-gray-700/50">
                        <h3 className="text-xs font-semibold text-gray-400 mb-2">Data Source</h3>
                        <div className="text-xs text-gray-300 space-y-1">
                            <div className="flex justify-between">
                                <span className="text-gray-500">Source:</span>
                                <span>{methodology.data_source}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Resolution:</span>
                                <span>{methodology.resolution}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Period:</span>
                                <span>{methodology.temporal_coverage}</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Animation Download */}
                {animation?.gif_url && (
                    <div className="pt-2 space-y-2">
                        <button
                            onClick={() => window.open(animation.gif_url, '_blank')}
                            className="block w-full py-2 text-center bg-cyan-900/30 hover:bg-cyan-900/50 border border-cyan-500/30 rounded text-xs text-cyan-300 transition-colors"
                        >
                            ▶️ View Time-Lapse Animation
                        </button>

                        <a
                            href={animation.gif_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            download={`water_timelapse_${location_name}.gif`}
                            className="block w-full py-2 text-center bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded text-xs text-white transition-colors"
                        >
                            ⬇️ Download GIF
                        </a>
                    </div>
                )}
            </div>
        </aside>
    );
}
