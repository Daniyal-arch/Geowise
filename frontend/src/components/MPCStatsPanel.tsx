'use client';

import React from 'react';
import type { MPCNLPResponse, MPCImage } from '@/types/mpc';
import { 
  getCollectionColor, 
  getCloudCoverClass, 
  formatImageDate,
  getMPCExplorerURL 
} from '@/types/mpc';

/**
 * MPCStatsPanel - Satellite Imagery Search Results
 * =================================================
 * 
 * Displays:
 * - Search summary (location, collection, dates, images found)
 * - List of available images with metadata
 * - Links to MPC Explorer for viewing actual imagery
 */

interface MPCStatsPanelProps {
  data: MPCNLPResponse['data'] | null;
  loading?: boolean;
}

export const MPCStatsPanel: React.FC<MPCStatsPanelProps> = ({ 
  data, 
  loading = false 
}) => {
  // ─────────────────────────────────────────────────────────────────────
  // LOADING STATE
  // ─────────────────────────────────────────────────────────────────────
  
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

  // ─────────────────────────────────────────────────────────────────────
  // NO DATA STATE
  // ─────────────────────────────────────────────────────────────────────
  
  if (!data) {
    return null;
  }

  // ─────────────────────────────────────────────────────────────────────
  // EXTRACT DATA
  // ─────────────────────────────────────────────────────────────────────
  
  const {
    location,
    bbox,
    collection,
    images_found,
    images,
    query_params,
  } = data;

  const color = getCollectionColor(collection);
  
  // Calculate area
  const areaKm = bbox ? (
    (bbox[2] - bbox[0]) * 111 * (bbox[3] - bbox[1]) * 111
  ).toFixed(0) : 'N/A';

  // Find best image (lowest cloud cover)
  const bestImage = images && images.length > 0
    ? images.reduce((best, img) => {
        const bestCloud = best.cloud_cover ?? 100;
        const imgCloud = img.cloud_cover ?? 100;
        return imgCloud < bestCloud ? img : best;
      })
    : null;

  // Average cloud cover
  const avgCloudCover = images && images.length > 0
    ? images.reduce((sum, img) => sum + (img.cloud_cover ?? 0), 0) / images.length
    : 0;

  // ─────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────
  
  return (
    <aside className="w-[360px] bg-slate-900/95 backdrop-blur-sm border-l border-slate-800 overflow-y-auto">
      <div className="p-4 space-y-3.5">
        
        {/* ══════════════════════════════════════════════════════════════ */}
        {/* HEADER */}
        {/* ══════════════════════════════════════════════════════════════ */}
        
        <div className="pb-2.5 border-b border-slate-800">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🛰️</span>
              <div>
                <h2 className="text-xl font-bold text-gray-100">Satellite Imagery</h2>
                <p className="text-[11px] text-gray-500 mt-0.5">
                  {location}
                </p>
              </div>
            </div>
            <span 
              className="text-[10px] px-2 py-1 rounded font-medium border"
              style={{
                backgroundColor: `${color}20`,
                color: color,
                borderColor: `${color}50`,
              }}
            >
              {query_params?.collection_name || collection}
            </span>
          </div>
        </div>
  {/* After Best Image section, add: */}

{/* ══════════════════════════════════════════════════════════════ */}
{/* IMAGE LAYERS */}
{/* ══════════════════════════════════════════════════════════════ */}

{bestImage && bestImage.tile_urls && (
  <div>
    <h4 className="text-[11px] font-semibold text-gray-300 mb-2 uppercase tracking-wide">
      Available Layers
    </h4>
    
    <div className="space-y-2">
      {bestImage.tile_urls.natural_color && (
        <div className="flex items-center justify-between p-2 bg-slate-800 rounded">
          <span className="text-[11px] text-gray-300">🌍 Natural Color</span>
          <button className="text-[10px] px-2 py-1 bg-blue-600 text-white rounded">
            View
          </button>
        </div>
      )}
      
      {bestImage.tile_urls.false_color && (
        <div className="flex items-center justify-between p-2 bg-slate-800 rounded">
          <span className="text-[11px] text-gray-300">🌿 False Color (Vegetation)</span>
          <button className="text-[10px] px-2 py-1 bg-green-600 text-white rounded">
            View
          </button>
        </div>
      )}
      
      {bestImage.tile_urls.ndvi && (
        <div className="flex items-center justify-between p-2 bg-slate-800 rounded">
          <span className="text-[11px] text-gray-300">📊 NDVI</span>
          <button className="text-[10px] px-2 py-1 bg-emerald-600 text-white rounded">
            View
          </button>
        </div>
      )}
    </div>
  </div>
)}
        {/* ══════════════════════════════════════════════════════════════ */}
        {/* SUMMARY */}
        {/* ══════════════════════════════════════════════════════════════ */}
        
        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
          <div className="space-y-2 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Collection:</span>
              <span className="text-gray-200 font-medium">
                {query_params?.collection_name}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Period:</span>
              <span className="text-gray-200 font-medium">
                {query_params?.dates}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Area:</span>
              <span className="text-gray-200 font-medium">{areaKm} km²</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Images Found:</span>
              <span 
                className="font-bold text-base"
                style={{ color }}
              >
                {images_found}
              </span>
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* BEST IMAGE */}
        {/* ══════════════════════════════════════════════════════════════ */}
        
        {bestImage && (
          <div className="bg-emerald-950/20 rounded-lg p-3 border border-emerald-900/30">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">⭐</span>
              <span className="text-[11px] text-gray-500 uppercase font-semibold tracking-wide">
                Best Image
              </span>
            </div>
            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Date:</span>
                <span className="text-emerald-300 font-medium">
                  {formatImageDate(bestImage.datetime)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Cloud Cover:</span>
                <span className={getCloudCoverClass(bestImage.cloud_cover).bgClass + ' text-white px-2 py-0.5 rounded text-[10px] font-semibold'}>
                  {bestImage.cloud_cover !== null ? `${bestImage.cloud_cover.toFixed(1)}%` : 'N/A'}
                </span>
              </div>
              <a 
                href={getMPCExplorerURL(collection, bestImage.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="block mt-2 text-center py-2 rounded text-white font-medium text-[11px] hover:opacity-80 transition-opacity"
                style={{ backgroundColor: color }}
              >
                🔗 View in MPC Explorer
              </a>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* IMAGE LIST */}
        {/* ══════════════════════════════════════════════════════════════ */}
        
        <div>
          <h4 className="text-[11px] font-semibold text-gray-300 mb-2 uppercase tracking-wide">
            Available Images ({images_found})
          </h4>
          
          {images_found === 0 ? (
            <div className="bg-amber-950/30 rounded-lg p-4 border border-amber-900/50 text-center">
              <span className="text-2xl mb-2 block">📭</span>
              <p className="text-[11px] text-gray-400">
                No images found for this period.<br/>
                Try adjusting the date range or cloud cover threshold.
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {images.map((img, idx) => {
                const date = formatImageDate(img.datetime);
                const cloudCover = img.cloud_cover !== null ? img.cloud_cover.toFixed(1) : 'N/A';
                const cloudClass = getCloudCoverClass(img.cloud_cover);
                const explorerUrl = getMPCExplorerURL(collection, img.id);
                
                return (
                  <div 
                    key={idx}
                    className="bg-slate-800/50 border border-slate-700 rounded-lg p-3 hover:bg-slate-800 transition-colors"
                    style={{
                      borderLeftWidth: '4px',
                      borderLeftColor: color,
                    }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-semibold text-gray-200">
                        📅 {date}
                      </span>
                      <span 
                        className={`${cloudClass.bgClass} text-white px-2 py-0.5 rounded text-[10px] font-semibold`}
                      >
                        ☁️ {cloudCover}%
                      </span>
                    </div>
                    
                    <div className="text-[10px] text-gray-500 mb-2 font-mono break-all">
                      {img.id.substring(0, 40)}...
                    </div>
                    
                    <a 
                      href={explorerUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-center py-1.5 rounded text-white text-[10px] font-medium hover:opacity-80 transition-opacity"
                      style={{ backgroundColor: color }}
                    >
                      🔗 View in Explorer
                    </a>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* CLOUD COVER LEGEND */}
        {/* ══════════════════════════════════════════════════════════════ */}
        
        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
          <h4 className="text-[11px] font-semibold text-gray-300 mb-2 uppercase tracking-wide">
            Cloud Cover Legend
          </h4>
          <div className="flex gap-2 flex-wrap text-[10px]">
            <span className="bg-green-500 text-white px-2 py-1 rounded font-semibold">
              &lt; 10% Excellent
            </span>
            <span className="bg-orange-500 text-white px-2 py-1 rounded font-semibold">
              10-30% Good
            </span>
            <span className="bg-red-500 text-white px-2 py-1 rounded font-semibold">
              &gt; 30% Poor
            </span>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* DATA SOURCE */}
        {/* ══════════════════════════════════════════════════════════════ */}
        
        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800 text-[11px] text-gray-500">
          <div className="font-semibold text-gray-300 mb-1.5">Data Source</div>
          <div className="space-y-0.5">
            <div><strong className="text-gray-400">Platform:</strong> Microsoft Planetary Computer</div>
            <div><strong className="text-gray-400">API:</strong> STAC (SpatioTemporal Asset Catalog)</div>
            <div><strong className="text-gray-400">Cost:</strong> Free & Open Access</div>
          </div>
        </div>

      </div>
    </aside>
  );
};

export default MPCStatsPanel;