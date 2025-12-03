/**
 * Fire Statistics Panel
 * Displays real-time fire detection statistics from NASA FIRMS
 */

import React from 'react';
import type { FireStatistics } from '@/types/fires';
import { getSatelliteName } from '@/services/fireService';

interface FireStatsPanelProps {
  statistics: FireStatistics;
  countryName: string;
}

export function FireStatsPanel({ statistics, countryName }: FireStatsPanelProps) {
  const {
    total_fires,
    date_range,
    high_confidence_count,
    nominal_confidence_count,
    low_confidence_count,
    frp_statistics,
    brightness_statistics,
    fires_by_date,
    day_fires,
    night_fires,
    satellite_breakdown
  } = statistics;

  // Calculate percentages
  const highPercent = total_fires > 0 ? (high_confidence_count / total_fires * 100).toFixed(0) : 0;
  const nominalPercent = total_fires > 0 ? (nominal_confidence_count / total_fires * 100).toFixed(0) : 0;
  const lowPercent = total_fires > 0 ? (low_confidence_count / total_fires * 100).toFixed(0) : 0;

  const dayPercent = total_fires > 0 ? (day_fires / total_fires * 100).toFixed(0) : 0;
  const nightPercent = total_fires > 0 ? (night_fires / total_fires * 100).toFixed(0) : 0;

  return (
    <aside className="w-[360px] bg-slate-900/95 backdrop-blur-sm border-l border-slate-800 overflow-y-auto">
      <div className="p-4 space-y-3.5">
        
        {/* Header */}
        <div className="pb-2.5 border-b border-slate-800">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-100">{countryName}</h2>
              <p className="text-[11px] text-gray-500 mt-1">
                Active Fire Detection • {date_range}
              </p>
            </div>
            <span className="text-[10px] px-2 py-1 bg-orange-950/50 text-orange-400 rounded font-medium border border-orange-900/50">
              FIRMS
            </span>
          </div>
        </div>

        {/* Summary */}
        {total_fires > 0 ? (
          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
            <p className="text-xs text-gray-300 leading-relaxed">
              Detected <strong className="text-orange-400">{total_fires} active fires</strong> in{' '}
              {countryName} over the {date_range.toLowerCase()}.
            </p>
          </div>
        ) : (
          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
            <p className="text-xs text-gray-300 leading-relaxed">
              ✅ No active fires detected in {countryName} over the {date_range.toLowerCase()}.
            </p>
          </div>
        )}

        {/* Total Fires */}
        <div className="bg-gradient-to-br from-orange-950/30 to-red-950/30 rounded-lg p-4 border border-orange-900/30">
          <div className="text-[10px] text-gray-400 mb-1 uppercase font-semibold tracking-wide">
            Total Active Fires
          </div>
          <div className="text-4xl font-bold text-orange-400">
            {total_fires}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">{date_range}</div>
        </div>

        {/* Confidence Breakdown */}
        {total_fires > 0 && (
          <div className="bg-slate-800/50 rounded-lg border border-slate-800 overflow-hidden">
            <div className="p-3 border-b border-slate-800">
              <h3 className="text-xs font-bold text-gray-100">CONFIDENCE LEVELS</h3>
              <p className="text-[10px] text-gray-500 mt-0.5">Detection reliability</p>
            </div>
            
            <div className="p-3 space-y-2.5">
              {/* High Confidence */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500"></div>
                    <span className="text-xs text-gray-300">High</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-100">
                    {high_confidence_count} ({highPercent}%)
                  </span>
                </div>
                <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-red-500 rounded-full transition-all"
                    style={{ width: `${highPercent}%` }}
                  />
                </div>
              </div>

              {/* Nominal Confidence */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-orange-500"></div>
                    <span className="text-xs text-gray-300">Nominal</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-100">
                    {nominal_confidence_count} ({nominalPercent}%)
                  </span>
                </div>
                <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-orange-500 rounded-full transition-all"
                    style={{ width: `${nominalPercent}%` }}
                  />
                </div>
              </div>

              {/* Low Confidence */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500"></div>
                    <span className="text-xs text-gray-300">Low</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-100">
                    {low_confidence_count} ({lowPercent}%)
                  </span>
                </div>
                <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-yellow-500 rounded-full transition-all"
                    style={{ width: `${lowPercent}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Fire Intensity */}
        {total_fires > 0 && (
          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
              <div className="text-[10px] text-gray-500 mb-1 uppercase font-semibold tracking-wide">
                Avg FRP
              </div>
              <div className="text-xl font-bold text-orange-400">
                {frp_statistics.avg.toFixed(1)} MW
              </div>
              <div className="text-[10px] text-gray-600 mt-0.5">Fire power</div>
            </div>
            
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
              <div className="text-[10px] text-gray-500 mb-1 uppercase font-semibold tracking-wide">
                Max FRP
              </div>
              <div className="text-xl font-bold text-red-400">
                {frp_statistics.max.toFixed(1)} MW
              </div>
              <div className="text-[10px] text-gray-600 mt-0.5">Peak intensity</div>
            </div>
          </div>
        )}

        {/* Temperature */}
        {total_fires > 0 && (
          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
              <div className="text-[10px] text-gray-500 mb-1 uppercase font-semibold tracking-wide">
                Avg Temp
              </div>
              <div className="text-xl font-bold text-yellow-400">
                {brightness_statistics.avg.toFixed(0)} K
              </div>
              <div className="text-[10px] text-gray-600 mt-0.5">Brightness</div>
            </div>
            
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
              <div className="text-[10px] text-gray-500 mb-1 uppercase font-semibold tracking-wide">
                Max Temp
              </div>
              <div className="text-xl font-bold text-red-400">
                {brightness_statistics.max.toFixed(0)} K
              </div>
              <div className="text-[10px] text-gray-600 mt-0.5">Hottest fire</div>
            </div>
          </div>
        )}

        {/* Day/Night Split */}
        {total_fires > 0 && (
          <div className="bg-slate-800/50 rounded-lg border border-slate-800 overflow-hidden">
            <div className="p-3 border-b border-slate-800">
              <h3 className="text-xs font-bold text-gray-100">DAY / NIGHT DETECTION</h3>
            </div>
            
            <div className="p-3 space-y-2.5">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">☀️</span>
                    <span className="text-xs text-gray-300">Day Fires</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-100">
                    {day_fires} ({dayPercent}%)
                  </span>
                </div>
                <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-yellow-500 rounded-full transition-all"
                    style={{ width: `${dayPercent}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🌙</span>
                    <span className="text-xs text-gray-300">Night Fires</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-100">
                    {night_fires} ({nightPercent}%)
                  </span>
                </div>
                <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${nightPercent}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Daily Fires Chart */}
        {total_fires > 0 && fires_by_date.length > 0 && (
          <div className="bg-slate-800/50 rounded-lg border border-slate-800 overflow-hidden">
            <div className="p-3 border-b border-slate-800">
              <h3 className="text-xs font-bold text-gray-100">DAILY FIRE COUNT</h3>
              <p className="text-[10px] text-gray-500 mt-0.5">Fires detected per day</p>
            </div>
            
            <div className="p-3">
              {(() => {
                const maxCount = Math.max(...fires_by_date.map(d => d.count));
                
                return (
                  <div className="space-y-2">
                    {fires_by_date.map((dayData, idx) => {
                      const heightPercent = maxCount > 0 ? (dayData.count / maxCount * 100) : 0;
                      const date = new Date(dayData.date);
                      const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
                      const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                      
                      return (
                        <div key={idx} className="flex items-center gap-2">
                          <div className="text-[10px] text-gray-500 w-16 text-right">
                            {dayName}<br />{dateStr}
                          </div>
                          <div className="flex-1 h-6 bg-slate-900 rounded-full overflow-hidden relative">
                            <div 
                              className="h-full bg-gradient-to-r from-orange-500 to-red-600 transition-all rounded-full"
                              style={{ width: `${heightPercent}%` }}
                            />
                            <span className="absolute inset-0 flex items-center px-2 text-[10px] font-semibold text-white">
                              {dayData.count} fires
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {/* Satellite Coverage */}
        {total_fires > 0 && (
          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
            <h3 className="text-xs font-bold text-gray-100 mb-2">SATELLITE COVERAGE</h3>
            <div className="space-y-1.5">
              {Object.entries(satellite_breakdown).map(([code, count]) => {
                const percent = total_fires > 0 ? (count / total_fires * 100).toFixed(0) : 0;
                return (
                  <div key={code} className="flex items-center justify-between text-[11px]">
                    <span className="text-gray-300">{getSatelliteName(code)}</span>
                    <span className="font-semibold text-gray-100">
                      {count} ({percent}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Data Source */}
        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800 text-[11px] text-gray-500">
          <div className="font-semibold text-gray-300 mb-1.5">Data Source</div>
          <div className="space-y-0.5">
            <div><strong className="text-gray-400">Source:</strong> NASA FIRMS</div>
            <div><strong className="text-gray-400">Satellites:</strong> VIIRS/MODIS</div>
            <div><strong className="text-gray-400">Resolution:</strong> 375m (VIIRS)</div>
            <div><strong className="text-gray-400">Updated:</strong> Real-time (NRT)</div>
          </div>
        </div>
      </div>
    </aside>
  );
}