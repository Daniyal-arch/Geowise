/**
 * GEOWISE Map Legend Component
 * Shows color coding and scales for map layers
 */

'use client';

import type { LayerState } from '@/services/types';

interface LegendProps {
  activeLayers: LayerState[];
}

const LAYER_LEGENDS = {
  fires: {
    title: 'Fire Intensity (FRP)',
    items: [
      { color: '#FED976', label: '< 100 MW', range: '0-100' },
      { color: '#FEB24C', label: '100-750 MW', range: '100-750' },
      { color: '#FD8D3C', label: '750-1000 MW', range: '750-1000' },
      { color: '#FC4E2A', label: '1000-2000 MW', range: '1000-2000' },
      { color: '#E31A1C', label: '2000-5000 MW', range: '2000-5000' },
      { color: '#BD0026', label: '> 5000 MW', range: '5000+' },
    ],
  },
  'forest-loss': {
    title: 'Tree Cover Loss',
    items: [
      { color: '#DC143C', label: '2001-2024', range: 'Annual loss' },
    ],
  },
  'forest-gain': {
    title: 'Tree Cover Gain',
    items: [
      { color: '#228B22', label: '2000-2020', range: 'Forest gain' },
    ],
  },
  'mpc-land-use': {
    title: 'Land Use Classes',
    items: [
      { color: '#FFD700', label: 'Cropland', range: 'Class 1' },
      { color: '#228B22', label: 'Forest', range: 'Class 2' },
      { color: '#90EE90', label: 'Grassland', range: 'Class 3' },
      { color: '#87CEEB', label: 'Water', range: 'Class 4' },
      { color: '#808080', label: 'Built-up', range: 'Class 5' },
    ],
  },
  'fire-hexagons': {
    title: 'Fire Density (H3)',
    items: [
      { color: '#FFEDA0', label: 'Low', range: '1-10 fires' },
      { color: '#FEB24C', label: 'Medium', range: '10-50 fires' },
      { color: '#FC4E2A', label: 'High', range: '50-100 fires' },
      { color: '#BD0026', label: 'Very High', range: '100+ fires' },
    ],
  },
};

export default function Legend({ activeLayers }: LegendProps) {
  const visibleLayers = activeLayers.filter((layer) => layer.visible);

  if (visibleLayers.length === 0) {
    return null;
  }

  return (
    <div className="absolute bottom-20 left-4 bg-gray-900/95 backdrop-blur-md border border-gray-800 rounded-lg shadow-xl p-4 max-w-xs">
      <h3 className="text-sm font-bold text-white mb-3">Map Legend</h3>

      <div className="space-y-4">
        {visibleLayers.map((layer) => {
          const legend = LAYER_LEGENDS[layer.id as keyof typeof LAYER_LEGENDS];
          if (!legend) return null;

          return (
            <div key={layer.id} className="space-y-2">
              <h4 className="text-xs font-semibold text-gray-300">
                {legend.title}
              </h4>

              <div className="space-y-1">
                {legend.items.map((item, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <div
                      className="h-3 w-3 rounded-sm flex-shrink-0"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-xs text-gray-400">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Scale Bar */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>0 km</span>
          <div className="flex-1 mx-2 h-0.5 bg-white"></div>
          <span>100 km</span>
        </div>
      </div>
    </div>
  );
}