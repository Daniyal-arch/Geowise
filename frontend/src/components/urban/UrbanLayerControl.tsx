import React from 'react';
import { Layers, Eye, EyeOff } from 'lucide-react';

interface LayerConfig {
    id: string;
    label: string;
    visible: boolean;
}

interface UrbanLayerControlProps {
    layers: LayerConfig[];
    onToggle: (id: string) => void;
}

export default function UrbanLayerControl({ layers, onToggle }: UrbanLayerControlProps) {
    return (
        <div className="absolute top-4 left-4 bg-gray-900/90 backdrop-blur-md border border-gray-700 rounded-lg p-3 shadow-xl z-50 w-64 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-700">
                <Layers size={16} className="text-blue-400" />
                <h3 className="text-sm font-semibold text-white">Map Layers</h3>
            </div>

            <div className="space-y-2">
                {layers.map((layer) => (
                    <button
                        key={layer.id}
                        onClick={() => onToggle(layer.id)}
                        className={`w-full flex items-center justify-between p-2 rounded-md transition-all ${layer.visible
                                ? 'bg-blue-900/30 border border-blue-500/30 text-white'
                                : 'bg-gray-800/20 border border-transparent text-gray-400 hover:bg-gray-800/40'
                            }`}
                    >
                        <span className="text-xs font-medium">{layer.label}</span>
                        {layer.visible ? (
                            <Eye size={14} className="text-blue-400" />
                        ) : (
                            <EyeOff size={14} className="text-gray-500" />
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
}
