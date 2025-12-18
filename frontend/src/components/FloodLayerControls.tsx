'use client';

import React from 'react';
import type { FloodLayerState, FloodLayerOpacity, FloodTiles } from '@/types/flood';

interface FloodLayerControlsProps {
  tiles: FloodTiles | null;
  layers: FloodLayerState;
  opacity: FloodLayerOpacity;
  onToggleLayer: (layer: keyof FloodLayerState) => void;
  onOpacityChange: (layer: keyof FloodLayerOpacity, value: number) => void;
}

// ============================================================================
// LAYER CONFIGURATION
// ============================================================================

interface LayerConfig {
  key: keyof FloodLayerState;
  tileKey: keyof FloodTiles;
  name: string;
  color: string;
  icon: string;
}

const SAR_LAYERS: LayerConfig[] = [
  { key: 'floodExtent', tileKey: 'flood_extent', name: 'Flood Extent', color: '#FF0000', icon: '🌊' },
  { key: 'changeDetection', tileKey: 'change_detection', name: 'SAR Change', color: '#0066FF', icon: '📊' },
  { key: 'sarBefore', tileKey: 'sar_before', name: 'SAR Before', color: '#666666', icon: '📡' },
  { key: 'sarAfter', tileKey: 'sar_after', name: 'SAR After', color: '#444444', icon: '📡' },
  { key: 'permanentWater', tileKey: 'permanent_water', name: 'Permanent Water', color: '#00FFFF', icon: '💧' },
];

const OPTICAL_LAYERS: LayerConfig[] = [
  { key: 'opticalBefore', tileKey: 'optical_before', name: 'Optical Before', color: '#88CC88', icon: '🛰️' },
  { key: 'opticalAfter', tileKey: 'optical_after', name: 'Optical After', color: '#44AA44', icon: '🛰️' },
  { key: 'falseColor', tileKey: 'false_color_after', name: 'False Color', color: '#FF6688', icon: '🎨' },
  { key: 'ndwi', tileKey: 'ndwi_after', name: 'NDWI Water', color: '#0088FF', icon: '💧' },
];

// ============================================================================
// LAYER TOGGLE COMPONENT
// ============================================================================

interface LayerToggleProps {
  config: LayerConfig;
  isAvailable: boolean;
  isVisible: boolean;
  opacity: number;
  onToggle: () => void;
  onOpacityChange: (value: number) => void;
}

const LayerToggle: React.FC<LayerToggleProps> = ({
  config,
  isAvailable,
  isVisible,
  opacity,
  onToggle,
  onOpacityChange,
}) => {
  if (!isAvailable) return null;

  return (
    <div className={`rounded-md border transition-all ${
      isVisible 
        ? 'bg-slate-800 border-slate-600' 
        : 'bg-slate-800/40 border-slate-700/50 hover:border-slate-600'
    }`}>
      {/* Layer Header */}
      <label className="flex items-center gap-2 p-2 cursor-pointer">
        {/* Color dot */}
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: config.color }}
        />
        
        {/* Name */}
        <span className="text-xs font-medium text-gray-200 flex-1 truncate">
          {config.icon} {config.name}
        </span>

        {/* Toggle Switch */}
        <div 
          className="relative flex-shrink-0 cursor-pointer"
          onClick={(e) => {
            e.preventDefault();
            onToggle();
          }}
        >
          <div className={`w-8 h-4 rounded-full transition-colors ${
            isVisible ? 'bg-blue-600' : 'bg-gray-600'
          }`}>
            <div className={`absolute top-[2px] w-3 h-3 bg-white rounded-full transition-transform ${
              isVisible ? 'translate-x-[18px]' : 'translate-x-[2px]'
            }`} />
          </div>
        </div>
      </label>

      {/* Opacity Slider */}
      {isVisible && (
        <div className="px-2 pb-2">
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="100"
              value={Math.round(opacity * 100)}
              onChange={(e) => onOpacityChange(parseInt(e.target.value) / 100)}
              className="flex-1 h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${opacity * 100}%, #4b5563 ${opacity * 100}%, #4b5563 100%)`
              }}
            />
            <span className="text-[10px] text-gray-500 w-8 text-right">
              {Math.round(opacity * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function FloodLayerControls({
  tiles,
  layers,
  opacity,
  onToggleLayer,
  onOpacityChange,
}: FloodLayerControlsProps) {
  if (!tiles) {
    return (
      <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
        <p className="text-xs text-gray-400 text-center">No flood layers</p>
      </div>
    );
  }

  // Check which layers are available
  const hasAnySarLayers = SAR_LAYERS.some(l => !!tiles[l.tileKey]);
  const hasAnyOpticalLayers = OPTICAL_LAYERS.some(l => !!tiles[l.tileKey]);

  return (
    <div className="space-y-3">
      {/* SAR Layers Section */}
      {hasAnySarLayers && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <span className="text-sm">📡</span>
            <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide">
              SAR Layers
            </h3>
          </div>
          
          <div className="space-y-1.5">
            {SAR_LAYERS.map((config) => (
              <LayerToggle
                key={config.key}
                config={config}
                isAvailable={!!tiles[config.tileKey]}
                isVisible={layers[config.key]}
                opacity={opacity[config.key]}
                onToggle={() => onToggleLayer(config.key)}
                onOpacityChange={(value) => onOpacityChange(config.key, value)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Optical Layers Section */}
      {hasAnyOpticalLayers && (
        <div className={hasAnySarLayers ? 'pt-3 border-t border-slate-700' : ''}>
          <div className="flex items-center gap-1.5 mb-2">
            <span className="text-sm">🛰️</span>
            <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide">
              Optical Layers
            </h3>
            <span className="text-[9px] bg-emerald-900/50 text-emerald-400 px-1.5 py-0.5 rounded">
              NEW
            </span>
          </div>
          
          <div className="space-y-1.5">
            {OPTICAL_LAYERS.map((config) => (
              <LayerToggle
                key={config.key}
                config={config}
                isAvailable={!!tiles[config.tileKey]}
                isVisible={layers[config.key]}
                opacity={opacity[config.key]}
                onToggle={() => onToggleLayer(config.key)}
                onOpacityChange={(value) => onOpacityChange(config.key, value)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Compact Legend */}
      <div className="pt-3 border-t border-slate-700">
        <h4 className="text-[10px] font-semibold text-gray-500 mb-1.5 uppercase">Legend</h4>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[9px] text-gray-500">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-sm bg-red-500"></div>
            <span>Flood extent</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-sm bg-cyan-400"></div>
            <span>Permanent water</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-gradient-to-r from-blue-500 to-red-500 rounded"></div>
            <span>SAR change</span>
          </div>
          {hasAnyOpticalLayers && (
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-sm bg-green-500"></div>
              <span>Optical RGB</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export { FloodLayerControls as default };