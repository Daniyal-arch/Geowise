/**
 * GEOWISE Layer Controls Component
 * Left sidebar for toggling data layers on/off
 */

'use client';

import type { LayerState } from '@/services/types';

interface LayerControlsProps {
  layers: LayerState[];
  onToggleLayer: (layerId: string) => void;
  onOpacityChange?: (layerId: string, opacity: number) => void;
}

export default function LayerControls({
  layers,
  onToggleLayer,
  onOpacityChange,
}: LayerControlsProps) {
  return (
    <aside className="w-80 bg-gray-900/95 backdrop-blur-md border-r border-gray-800 overflow-y-auto">
      <div className="p-4">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-lg font-bold text-white mb-1">Data Layers</h2>
          <p className="text-xs text-gray-400">Toggle layers on/off</p>
        </div>

        {/* Layer List */}
        <div className="space-y-3">
          {layers.map((layer) => (
            <div
              key={layer.id}
              className={`rounded-lg border transition-all ${
                layer.visible
                  ? 'bg-gray-800/80 border-blue-500/50'
                  : 'bg-gray-800/40 border-gray-700/50 hover:border-gray-600'
              }`}
            >
              {/* Layer Header */}
              <label className="flex items-center justify-between p-3 cursor-pointer">
                <div className="flex items-center gap-3 flex-1">
                  {/* Color Indicator */}
                  <div
                    className="h-4 w-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: layer.color }}
                  />

                  {/* Layer Name */}
                  <span className="text-sm font-medium text-white">
                    {layer.name}
                  </span>
                </div>

                {/* Toggle Switch */}
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={layer.visible}
                    onChange={() => onToggleLayer(layer.id)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </div>
              </label>

              {/* Opacity Slider (shown when layer is visible) */}
              {layer.visible && onOpacityChange && (
                <div className="px-3 pb-3">
                  <label className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">Opacity:</span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={layer.opacity}
                      onChange={(e) =>
                        onOpacityChange(layer.id, parseFloat(e.target.value))
                      }
                      className="flex-1 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xs text-gray-400 w-8 text-right">
                      {Math.round(layer.opacity * 100)}%
                    </span>
                  </label>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Info Box */}
        <div className="mt-6 p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg">
          <p className="text-xs text-blue-200">
            💡 <span className="font-semibold">Tip:</span> Click on map features
            for detailed information
          </p>
        </div>
      </div>
    </aside>
  );
}