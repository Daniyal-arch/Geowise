import React from 'react';
import { UrbanExpansionResponse } from '../../types/urban';
import { TrendingUp, Users, Map as MapIcon, AlertTriangle } from 'lucide-react';

interface UrbanStatsPanelProps {
    data: UrbanExpansionResponse;
    isLoading?: boolean;
}

export default function UrbanStatsPanel({ data, isLoading = false }: UrbanStatsPanelProps) {
    if (isLoading) {
        return (
            <aside className="w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-800 h-full p-8 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
                    <span className="text-gray-400 text-sm">Analyzing urban growth...</span>
                </div>
            </aside>
        );
    }

    if (!data) return null;

    const { location, statistics, un_sdg_11_3_1, distance_rings, epochs, growth_rates } = data;

    // v5.3 FIX: Handle both nested location object and flat backend response
    const locationName = location?.name || (data as any).location_name || 'Unknown Location';

    return (
        <aside className="w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-800 overflow-y-auto h-full text-white">
            <div className="p-5 space-y-6">

                {/* Header */}
                <div className="border-b border-gray-800 pb-4">
                    <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                        {locationName}
                    </h2>
                    <p className="text-sm text-gray-400 mt-1">Urban Expansion Analysis</p>
                    <div className="flex justify-between items-center mt-3 text-xs font-mono text-gray-500 bg-gray-800/50 p-2 rounded">
                        <span>{data.analysis_period?.start_year || (data as any).start_year || 1975}</span>
                        <span className="border-b border-gray-600 w-full mx-2 opacity-30"></span>
                        <span>{data.analysis_period?.end_year || (data as any).end_year || 2020}</span>
                    </div>
                </div>

                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-800/40 p-3 rounded-lg border border-gray-700/50">
                        <div className="flex items-center gap-2 text-gray-400 mb-1">
                            <MapIcon size={14} />
                            <span className="text-xs">Built-up Area</span>
                        </div>
                        <div className="text-lg font-bold text-white">
                            {statistics?.area_end_ha?.toLocaleString() || 0} <span className="text-xs font-normal text-gray-500">ha</span>
                        </div>
                        <div className="text-xs text-green-400 mt-1">
                            +{statistics?.absolute_growth_ha?.toLocaleString() || 0} ha
                        </div>
                    </div>

                    <div className="bg-gray-800/40 p-3 rounded-lg border border-gray-700/50">
                        <div className="flex items-center gap-2 text-gray-400 mb-1">
                            <TrendingUp size={14} />
                            <span className="text-xs">Growth Rate</span>
                        </div>
                        <div className="text-lg font-bold text-white">
                            {statistics?.growth_percent || 0}%
                        </div>
                        <div className="text-xs text-blue-400 mt-1">
                            {statistics?.annual_growth_rate || 0}% / yr
                        </div>
                    </div>
                </div>

                {/* SDG 11.3.1 Indicator */}
                <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 border border-indigo-500/20 rounded-lg p-4">
                    <div className="mb-3">
                        <h3 className="text-sm font-semibold text-indigo-300">SDG 11.3.1 Indicator</h3>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-center mb-3">
                        <div>
                            <div className="text-xs text-gray-400 mb-1">LCR</div>
                            <div className="font-mono text-sm">{un_sdg_11_3_1?.lcr?.toFixed(4) || 'N/A'}</div>
                        </div>
                        <div>
                            <div className="text-xs text-gray-400 mb-1">PGR</div>
                            <div className="font-mono text-sm">{un_sdg_11_3_1?.pgr?.toFixed(4) || 'N/A'}</div>
                        </div>
                    </div>

                    <div className="bg-gray-900/50 rounded p-2 flex justify-between items-center">
                        <span className="text-xs text-gray-400">LCR/PGR Ratio</span>
                        <span className="text-lg font-bold text-white">{un_sdg_11_3_1?.ratio || 'N/A'}</span>
                    </div>

                    <p className="text-[10px] text-gray-500 mt-2 text-center leading-tight">
                        Ratio of Land Consumption Rate to Population Growth Rate.
                        Target is ~1.0 for sustainable growth.
                    </p>
                </div>

                {/* Distance Ring Analysis */}
                <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                        <div className="w-1 h-4 bg-blue-500 rounded-full"></div>
                        Urban Sprawl by Distance
                    </h3>
                    <div className="space-y-2">
                        {Object.entries(distance_rings || {}).map(([range, ring]) => (
                            <div key={range} className="bg-gray-800/30 rounded p-2 flex items-center justify-between group hover:bg-gray-800/50 transition-colors">
                                <div className="text-xs font-mono text-gray-400 min-w-[60px]">{range.replace('_', '-')}</div>

                                <div className="flex-1 mx-3">
                                    <div className="h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                                            style={{ width: `${Math.min(ring.growth_pct, 100)}%` }}
                                        />
                                    </div>
                                </div>

                                <div className="text-xs font-semibold text-white min-w-[40px] text-right">
                                    +{ring.growth_pct.toFixed(0)}%
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Population vs Built-up Evolution */}
                <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                        <div className="w-1 h-4 bg-green-500 rounded-full"></div>
                        Evolution (1975-2020)
                    </h3>
                    <div className="space-y-3">
                        {Object.entries(epochs || {}).sort().map(([year, epoch]) => (
                            <div key={year} className="flex flex-col gap-1 border-b border-gray-800 pb-2 last:border-0">
                                <span className="text-xs font-bold text-gray-500">{year}</span>
                                <div className="flex justify-between items-center text-xs">
                                    <div className="flex items-center gap-1.5 text-gray-300">
                                        <MapIcon size={12} className="text-blue-500" />
                                        <span>{epoch.built_up_hectares.toLocaleString()}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 text-gray-300">
                                        <Users size={12} className="text-green-500" />
                                        <span>{epoch.population > 0 ? (epoch.population / 1000000).toFixed(2) + 'M' : 'N/A'}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Animation / Export */}
                {data.animation_url && (
                    <div className="pt-2 space-y-2">
                        {/* Preview Button */}
                        <button
                            onClick={() => window.open(data.animation_url, '_blank')}
                            className="block w-full py-2 text-center bg-purple-900/30 hover:bg-purple-900/50 border border-purple-500/30 rounded text-xs text-purple-300 transition-colors"
                        >
                            ▶️ View Time-Lapse Animation
                        </button>

                        {/* Download Link */}
                        <a
                            href={data.animation_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            download={`urban_timelapse_${locationName}.gif`}
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
