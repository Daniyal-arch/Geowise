'use client';

import React from 'react';
import type { FloodNLPResponse, FloodStatistics } from '@/types/flood';

/**
 * FloodStatsPanel - v5.2 Updated for On-Demand Statistics
 * ========================================================
 * 
 * Response levels:
 * - 'overview': Large area - shows map, suggests sub-regions
 * - 'detailed': Small area - shows flood area, on-demand stats
 * 
 * v5.2 Changes:
 * - Initial response only shows flood_area_km2
 * - Population/cropland shown ONLY after "show statistics" follow-up
 * - Added hint for users to request detailed statistics
 * - Optical availability indicator
 */

interface FloodStatsPanelProps {
  data: FloodNLPResponse['data'] | null;
  locationName?: string;
  loading?: boolean;
  onSubRegionClick?: (regionName: string, regionType: string) => void;
}

// ============================================================================
// STAT CARD COMPONENT
// ============================================================================

interface StatCardProps {
  icon: string;
  label: string;
  value: number | string;
  unit?: string;
  colorClass: string;
  bgClass: string;
  borderClass: string;
  pending?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ 
  icon, 
  label, 
  value, 
  unit, 
  colorClass, 
  bgClass, 
  borderClass,
  pending = false
}) => (
  <div className={`${bgClass} rounded-lg p-3 border ${borderClass} ${pending ? 'opacity-60' : ''}`}>
    <div className="flex items-center gap-1.5 mb-1">
      <span className="text-sm">{icon}</span>
      <span className="text-[10px] text-gray-500 uppercase font-semibold tracking-wide">
        {label}
      </span>
    </div>
    <div className={`text-xl font-bold ${colorClass}`}>
      {pending ? (
        <span className="text-gray-500 text-sm">—</span>
      ) : (
        <>
          {typeof value === 'number' ? value.toLocaleString() : value}
          {unit && (
            <span className="text-xs text-gray-500 ml-1 font-normal">{unit}</span>
          )}
        </>
      )}
    </div>
  </div>
);

// ============================================================================
// SUB-REGION SUGGESTIONS COMPONENT
// ============================================================================

interface SubRegionSuggestionsProps {
  suggestion: {
    message?: string;
    sub_regions?: Array<{ name: string; type: string }>;
    next_level_type?: string;
    example_query?: string;
  } | null;
  onRegionClick?: (regionName: string, regionType: string) => void;
}

const SubRegionSuggestions: React.FC<SubRegionSuggestionsProps> = ({ 
  suggestion, 
  onRegionClick 
}) => {
  if (!suggestion || !suggestion.sub_regions?.length) return null;

  const { message, sub_regions, next_level_type, example_query } = suggestion;

  return (
    <div className="bg-blue-950/30 rounded-lg p-3 border border-blue-900/50 mb-3">
      <div className="flex items-start gap-2 mb-3">
        <span className="text-lg">🗺️</span>
        <div>
          <h4 className="text-sm font-semibold text-blue-300">Large Area Detected</h4>
          <p className="text-[11px] text-gray-400 mt-0.5 leading-relaxed">
            {message}
          </p>
        </div>
      </div>

      <div className="border-t border-blue-900/50 my-3"></div>

      <p className="text-[10px] text-gray-500 mb-2 flex items-center gap-1">
        <span>👆</span>
        <span>Click a {next_level_type} for detailed analysis:</span>
      </p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {sub_regions.slice(0, 10).map((region, index) => (
          <button
            key={index}
            onClick={() => onRegionClick?.(region.name, region.type)}
            className="px-2.5 py-1 text-[11px] font-medium bg-slate-800 hover:bg-blue-900/50 
                       text-gray-300 hover:text-blue-300 rounded-md border border-slate-700 
                       hover:border-blue-700 transition-all cursor-pointer flex items-center gap-1"
          >
            <span>→</span>
            <span>{region.name}</span>
          </button>
        ))}
        {sub_regions.length > 10 && (
          <span className="px-2.5 py-1 text-[11px] text-gray-500 bg-slate-800/50 rounded-md border border-slate-700">
            +{sub_regions.length - 10} more
          </span>
        )}
      </div>

      {example_query && (
        <div className="bg-slate-800/50 rounded-md p-2 border border-slate-700">
          <p className="text-[10px] text-gray-500 mb-1">💡 Example query:</p>
          <p className="text-[11px] text-blue-300 font-mono">"{example_query}"</p>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const FloodStatsPanel: React.FC<FloodStatsPanelProps> = ({ 
  data, 
  locationName,
  loading = false,
  onSubRegionClick 
}) => {
  // Loading state
  if (loading) {
    return (
      <aside className="w-[360px] bg-slate-900/95 backdrop-blur-sm border-l border-slate-800 overflow-y-auto">
        <div className="p-4 space-y-3">
          <div className="animate-pulse">
            <div className="h-6 bg-slate-800 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-slate-800 rounded w-1/2 mb-4"></div>
            <div className="h-24 bg-slate-800 rounded mb-3"></div>
            <div className="h-24 bg-slate-800 rounded"></div>
          </div>
        </div>
      </aside>
    );
  }

  // No data state
  if (!data) {
    return (
      <aside className="w-[360px] bg-slate-900/95 backdrop-blur-sm border-l border-slate-800 overflow-y-auto">
        <div className="p-4">
          <div className="bg-blue-950/30 rounded-lg p-4 border border-blue-900/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🌊</span>
              <h4 className="text-sm font-semibold text-blue-300">No Flood Data</h4>
            </div>
            <p className="text-[11px] text-gray-400">
              Query a location to see flood analysis.<br/>
              Example: "Show floods in Dadu district August 2022"
            </p>
          </div>
        </div>
      </aside>
    );
  }

  // Extract data
  const {
    location_name,
    location_type,
    country,
    province,
    area_km2,
    dates,
    images_used,
    statistics,
    suggestion,
    optical_availability,
    methodology,
  } = data;

  // Determine response level
  const isOverview = !statistics || (data as any).level === 'overview';
  const displayName = location_name || locationName || 'Unknown Location';
  
  // v5.2: Check if detailed stats are loaded (population > 0 means "show statistics" was called)
  const hasDetailedStats = statistics && (
    (statistics.exposed_population && statistics.exposed_population > 0) ||
    (statistics.flooded_cropland_ha && statistics.flooded_cropland_ha > 0) ||
    (statistics.flooded_urban_ha && statistics.flooded_urban_ha > 0)
  );

  // Check if optical tiles are available
  const hasOpticalTiles = data.tiles && (
    data.tiles.optical_before || 
    data.tiles.optical_after || 
    data.tiles.false_color_after ||
    data.tiles.ndwi_after
  );

  return (
    <aside className="w-[360px] bg-slate-900/95 backdrop-blur-sm border-l border-slate-800 overflow-y-auto">
      <div className="p-4 space-y-3.5">
        
        {/* ─────────────────────────────────────────────────────────────────── */}
        {/* HEADER */}
        {/* ─────────────────────────────────────────────────────────────────── */}
        
        <div className="pb-2.5 border-b border-slate-800">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🌊</span>
              <div>
                <h2 className="text-xl font-bold text-gray-100">{displayName}</h2>
                <p className="text-[11px] text-gray-500 mt-0.5">
                  {[province, country].filter(Boolean).join(', ')}
                  {area_km2 && ` • ${area_km2.toLocaleString()} km²`}
                </p>
              </div>
            </div>
            <span className={`text-[10px] px-2 py-1 rounded font-medium border ${
              isOverview 
                ? 'bg-blue-950/50 text-blue-400 border-blue-900/50' 
                : 'bg-emerald-950/50 text-emerald-400 border-emerald-900/50'
            }`}>
              {isOverview ? 'Overview' : 'Detailed'}
            </span>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────────── */}
        {/* DATE INFO */}
        {/* ─────────────────────────────────────────────────────────────────── */}
        
        {dates && (
          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm">📅</span>
                <div className="text-[11px]">
                  <div className="text-gray-400">
                    <span className="text-gray-500">Before:</span> {dates.before?.start} → {dates.before?.end}
                  </div>
                  <div className="text-gray-400">
                    <span className="text-gray-500">After:</span> {dates.after?.start} → {dates.after?.end}
                  </div>
                </div>
              </div>
              {images_used && (
                <div className="flex items-center gap-1 text-[10px] text-gray-500 bg-slate-700/50 px-2 py-1 rounded">
                  <span>📡</span>
                  <span>{images_used.before || 0} / {images_used.after || 0}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────────── */}
        {/* CASE 1: OVERVIEW - Large Area - No Stats */}
        {/* ─────────────────────────────────────────────────────────────────── */}
        
        {isOverview && (
          <>
            <div className="bg-amber-950/30 rounded-lg p-3 border border-amber-900/50">
              <div className="flex items-start gap-2">
                <span className="text-lg">⚠️</span>
                <div>
                  <h4 className="text-sm font-semibold text-amber-300">Map View Only</h4>
                  <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">
                    This area is too large for detailed statistics. The flood extent map is displayed,
                    but population and cropland data require analysis at a smaller scale.
                  </p>
                </div>
              </div>
            </div>

            <SubRegionSuggestions
              suggestion={suggestion}
              onRegionClick={onSubRegionClick}
            />

            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
              <h4 className="text-[11px] font-semibold text-gray-300 mb-2 uppercase tracking-wide">
                Available Layers
              </h4>
              <div className="space-y-1.5 text-[11px]">
                <div className="flex items-center gap-2 text-gray-400">
                  <div className="w-3 h-3 rounded-sm bg-red-500"></div>
                  <span>Flood Extent (detected flooded areas)</span>
                </div>
                <div className="flex items-center gap-2 text-gray-400">
                  <div className="w-3 h-1 bg-gradient-to-r from-blue-500 via-white to-red-500 rounded"></div>
                  <span>SAR Change Detection</span>
                </div>
                <div className="flex items-center gap-2 text-gray-400">
                  <div className="w-3 h-3 rounded-sm bg-cyan-400"></div>
                  <span>Permanent Water Bodies</span>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ─────────────────────────────────────────────────────────────────── */}
        {/* CASE 2: DETAILED - Small Area - v5.2 On-Demand Stats */}
        {/* ─────────────────────────────────────────────────────────────────── */}
        
        {!isOverview && statistics && (
          <>
            {/* Primary Stat: Flood Area (Always shown) */}
            <div className="bg-red-950/20 rounded-lg p-4 border border-red-900/30">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🌊</span>
                <span className="text-[11px] text-gray-500 uppercase font-semibold tracking-wide">
                  Flood Extent
                </span>
              </div>
              <div className="text-3xl font-bold text-red-400">
                {(statistics.flood_area_km2 || 0).toLocaleString()}
                <span className="text-sm text-gray-500 ml-2 font-normal">km²</span>
              </div>
              {statistics.flood_area_ha && (
                <div className="text-[11px] text-gray-500 mt-1">
                  {(statistics.flood_area_ha || 0).toLocaleString()} hectares
                </div>
              )}
            </div>

            {/* v5.2: Show detailed stats grid ONLY if loaded */}
            {hasDetailedStats ? (
              <>
                {/* Impact Stats Grid */}
                <div className="grid grid-cols-2 gap-2.5">
                  <StatCard
                    icon="👥"
                    label="Population"
                    value={statistics.exposed_population || 0}
                    colorClass="text-amber-400"
                    bgClass="bg-amber-950/20"
                    borderClass="border-amber-900/30"
                  />
                  <StatCard
                    icon="🌾"
                    label="Cropland"
                    value={statistics.flooded_cropland_ha || 0}
                    unit="ha"
                    colorClass="text-emerald-400"
                    bgClass="bg-emerald-950/20"
                    borderClass="border-emerald-900/30"
                  />
                  <StatCard
                    icon="🏘️"
                    label="Urban Area"
                    value={statistics.flooded_urban_ha || 0}
                    unit="ha"
                    colorClass="text-blue-400"
                    bgClass="bg-blue-950/20"
                    borderClass="border-blue-900/30"
                  />
                  {area_km2 && statistics.flood_area_km2 && (
                    <StatCard
                      icon="📊"
                      label="% Flooded"
                      value={((statistics.flood_area_km2 / area_km2) * 100).toFixed(1)}
                      unit="%"
                      colorClass="text-purple-400"
                      bgClass="bg-purple-950/20"
                      borderClass="border-purple-900/30"
                    />
                  )}
                </div>

                {/* Impact Highlights */}
                <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
                  <h4 className="text-[11px] font-semibold text-gray-300 mb-2 uppercase tracking-wide">
                    Key Impacts
                  </h4>
                  <div className="space-y-1.5 text-[11px]">
                    {statistics.exposed_population > 100000 && (
                      <div className="flex items-center gap-2 text-red-400">
                        <span>⚠️</span>
                        <span>High population exposure: {statistics.exposed_population.toLocaleString()} people</span>
                      </div>
                    )}
                    {statistics.exposed_population > 0 && statistics.exposed_population <= 100000 && (
                      <div className="flex items-center gap-2 text-amber-400">
                        <span>👥</span>
                        <span>Population at risk: {statistics.exposed_population.toLocaleString()} people</span>
                      </div>
                    )}
                    {statistics.flooded_cropland_ha > 10000 && (
                      <div className="flex items-center gap-2 text-red-400">
                        <span>🌾</span>
                        <span>Severe agricultural impact: {statistics.flooded_cropland_ha.toLocaleString()} ha</span>
                      </div>
                    )}
                    {statistics.flooded_cropland_ha > 0 && statistics.flooded_cropland_ha <= 10000 && (
                      <div className="flex items-center gap-2 text-amber-400">
                        <span>🌾</span>
                        <span>Cropland affected: {statistics.flooded_cropland_ha.toLocaleString()} ha</span>
                      </div>
                    )}
                    {statistics.flooded_urban_ha > 100 && (
                      <div className="flex items-center gap-2 text-blue-400">
                        <span>🏘️</span>
                        <span>Urban flooding: {statistics.flooded_urban_ha.toLocaleString()} ha</span>
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              /* v5.2: Hint to request detailed statistics */
              <div className="bg-blue-950/30 rounded-lg p-3 border border-blue-900/50">
                <div className="flex items-start gap-2">
                  <span className="text-lg">💡</span>
                  <div>
                    <h4 className="text-sm font-semibold text-blue-300">Get Detailed Statistics</h4>
                    <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">
                      Type <span className="text-blue-300 font-mono bg-slate-800/50 px-1.5 py-0.5 rounded">"show statistics"</span> to load:
                    </p>
                    <ul className="text-[11px] text-gray-500 mt-2 space-y-1">
                      <li className="flex items-center gap-1.5">
                        <span>👥</span> Population exposed
                      </li>
                      <li className="flex items-center gap-1.5">
                        <span>🌾</span> Flooded cropland
                      </li>
                      <li className="flex items-center gap-1.5">
                        <span>🏘️</span> Urban areas affected
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* v5.2: Optical imagery hint */}
            {!hasOpticalTiles && (
              <div className="bg-purple-950/30 rounded-lg p-3 border border-purple-900/50">
                <div className="flex items-start gap-2">
                  <span className="text-lg">🛰️</span>
                  <div>
                    <h4 className="text-sm font-semibold text-purple-300">Optical Imagery Available</h4>
                    <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">
                      Type <span className="text-purple-300 font-mono bg-slate-800/50 px-1.5 py-0.5 rounded">"show optical"</span> to add:
                    </p>
                    <ul className="text-[11px] text-gray-500 mt-2 space-y-1">
                      <li className="flex items-center gap-1.5">
                        <span>📷</span> Before/after satellite photos
                      </li>
                      <li className="flex items-center gap-1.5">
                        <span>🎨</span> False color visualization
                      </li>
                      <li className="flex items-center gap-1.5">
                        <span>💧</span> NDWI water index
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Optical tiles loaded indicator */}
            {hasOpticalTiles && (
              <div className="bg-emerald-950/30 rounded-lg p-3 border border-emerald-900/50">
                <div className="flex items-center gap-2">
                  <span className="text-lg">✅</span>
                  <div>
                    <h4 className="text-sm font-semibold text-emerald-300">Optical Imagery Loaded</h4>
                    <p className="text-[11px] text-gray-400 mt-1">
                      Sentinel-2 layers available in sidebar controls
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Severity Assessment */}
            {statistics.flood_area_km2 > 0 && area_km2 && hasDetailedStats && (
              <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
                <h4 className="text-[11px] font-semibold text-gray-300 mb-2 uppercase tracking-wide">
                  Impact Assessment
                </h4>
                {(() => {
                  const floodPercent = (statistics.flood_area_km2 / area_km2) * 100;
                  let severity: { label: string; color: string; desc: string };
                  
                  if (floodPercent > 30) {
                    severity = { label: 'SEVERE', color: 'text-red-400', desc: 'Major flooding detected' };
                  } else if (floodPercent > 15) {
                    severity = { label: 'SIGNIFICANT', color: 'text-orange-400', desc: 'Significant flooding across multiple zones' };
                  } else if (floodPercent > 5) {
                    severity = { label: 'MODERATE', color: 'text-amber-400', desc: 'Moderate flooding in low-lying areas' };
                  } else {
                    severity = { label: 'LIMITED', color: 'text-emerald-400', desc: 'Limited flooding in flood-prone zones' };
                  }
                  
                  return (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-gray-500">Severity</span>
                        <span className={`text-sm font-bold ${severity.color}`}>{severity.label}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-gray-500">Area Flooded</span>
                        <span className="text-sm font-semibold text-gray-200">{floodPercent.toFixed(1)}%</span>
                      </div>
                      <p className="text-[10px] text-gray-500 mt-1">{severity.desc}</p>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Methodology */}
            {methodology && (
              <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
                <h4 className="text-[11px] font-semibold text-gray-300 mb-2 uppercase tracking-wide">
                  Methodology
                </h4>
                <div className="space-y-1 text-[11px] text-gray-500">
                  <div><strong className="text-gray-400">Sensor:</strong> {methodology.sensor}</div>
                  <div><strong className="text-gray-400">Technique:</strong> {methodology.technique}</div>
                  <div><strong className="text-gray-400">Resolution:</strong> {methodology.resolution}</div>
                  <div><strong className="text-gray-400">Threshold:</strong> {methodology.threshold}</div>
                </div>
              </div>
            )}
          </>
        )}

        {/* ─────────────────────────────────────────────────────────────────── */}
        {/* DATA SOURCE (Always shown) */}
        {/* ─────────────────────────────────────────────────────────────────── */}
        
        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800 text-[11px] text-gray-500">
          <div className="font-semibold text-gray-300 mb-1.5">Data Sources</div>
          <div className="space-y-0.5">
            <div><strong className="text-gray-400">SAR:</strong> Sentinel-1 GRD</div>
            <div><strong className="text-gray-400">Population:</strong> WorldPop 2020</div>
            <div><strong className="text-gray-400">Land Cover:</strong> ESA WorldCover 2021</div>
            <div><strong className="text-gray-400">Water:</strong> JRC Global Surface Water</div>
          </div>
        </div>

      </div>
    </aside>
  );
};

export default FloodStatsPanel;