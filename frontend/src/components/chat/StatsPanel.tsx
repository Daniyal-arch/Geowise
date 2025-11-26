/**
 * GEOWISE Statistics Panel
 * Right sidebar showing real-time analytics and insights
 */

'use client';

import type { ForestStats } from '@/services/types';

interface StatsPanelProps {
  country: string;
  year: number;
  forestStats?: ForestStats;
  fireCount?: number;
  isLoading?: boolean;
}

export default function StatsPanel({
  country,
  year,
  forestStats,
  fireCount = 0,
  isLoading = false,
}: StatsPanelProps) {
  return (
    <aside className="w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-800 overflow-y-auto">
      <div className="p-4">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-lg font-bold text-white mb-1">
            Analytics Dashboard
          </h2>
          <p className="text-xs text-gray-400">Real-time environmental data</p>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {/* Country Card */}
          <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/20 border border-blue-500/30 rounded-lg p-3">
            <div className="text-xs text-blue-300 mb-1">Country</div>
            <div className="text-lg font-bold text-white">{country}</div>
          </div>

          {/* Year Card */}
          <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/20 border border-purple-500/30 rounded-lg p-3">
            <div className="text-xs text-purple-300 mb-1">Year</div>
            <div className="text-lg font-bold text-white">{year}</div>
          </div>

          {/* Fire Count */}
          <div className="bg-gradient-to-br from-red-900/40 to-red-800/20 border border-red-500/30 rounded-lg p-3">
            <div className="text-xs text-red-300 mb-1">Active Fires</div>
            <div className="text-lg font-bold text-white">
              {fireCount.toLocaleString()}
            </div>
          </div>

          {/* Forest Loss */}
          <div className="bg-gradient-to-br from-pink-900/40 to-pink-800/20 border border-pink-500/30 rounded-lg p-3">
            <div className="text-xs text-pink-300 mb-1">Forest Loss</div>
            {forestStats ? (
              <div className="text-lg font-bold text-white">
                {(forestStats.total_loss_km2 / 1000).toFixed(1)}K km²
              </div>
            ) : (
              <div className="text-sm text-gray-400">Loading...</div>
            )}
          </div>
        </div>

        {/* Forest Statistics Section */}
        {forestStats && !isLoading && (
          <div className="space-y-4">
            {/* Overall Stats */}
            <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">
                Forest Statistics
              </h3>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-400">Total Loss</span>
                  <span className="text-sm font-medium text-white">
                    {forestStats.total_loss_hectares.toLocaleString()} ha
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-400">Data Range</span>
                  <span className="text-sm font-medium text-white">
                    {forestStats.data_range}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-400">Most Recent</span>
                  <span className="text-sm font-medium text-white">
                    {forestStats.most_recent_year}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-400">Recent Loss</span>
                  <span className="text-sm font-medium text-pink-400">
                    {forestStats.recent_loss_hectares.toLocaleString()} ha
                  </span>
                </div>
              </div>
            </div>

            {/* 5-Year Trend Chart */}
            <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">
                5-Year Trend
              </h3>

              <div className="h-32 flex items-end justify-between gap-2">
                {forestStats.yearly_data.slice(-5).map((yearData, index) => {
                  const maxLoss = Math.max(
                    ...forestStats.yearly_data.slice(-5).map((d) => d.loss_hectares)
                  );
                  const height = (yearData.loss_hectares / maxLoss) * 100;

                  return (
                    <div key={index} className="flex-1 flex flex-col items-center gap-1">
                      <div
                        className="w-full bg-gradient-to-t from-pink-600 to-pink-400 rounded-t transition-all hover:opacity-80"
                        style={{ height: `${height}%` }}
                        title={`${yearData.year}: ${yearData.loss_km2.toFixed(2)} km²`}
                      />
                      <span className="text-xs text-gray-500">
                        '{yearData.year.toString().slice(-2)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Data Source */}
            <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3">
                Data Source
              </h3>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-xs text-gray-400">Provider</span>
                  <span className="text-xs font-medium text-white">
                    {forestStats.source}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-gray-400">Resolution</span>
                  <span className="text-xs font-medium text-white">30m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-gray-400">Satellite</span>
                  <span className="text-xs font-medium text-white">
                    Landsat
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-8">
            <div className="flex flex-col items-center justify-center gap-3">
              <div className="animate-spin rounded-full h-10 w-10 border-4 border-gray-700 border-t-blue-500"></div>
              <p className="text-sm text-gray-400">Loading statistics...</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!forestStats && !isLoading && (
          <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-8">
            <div className="flex flex-col items-center justify-center gap-3 text-center">
              <div className="text-4xl">📊</div>
              <p className="text-sm text-gray-400">
                Select a country to view statistics
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}