import React from 'react';
import { WaterLayerState, WaterLayerOpacity } from '@/types/water';
import { Droplet, TrendingUp, Waves } from 'lucide-react';

interface WaterLayerControlProps {
    layers: WaterLayerState;
    opacity: WaterLayerOpacity;
    onLayerToggle: (layer: keyof WaterLayerState) => void;
    onOpacityChange: (layer: keyof WaterLayerOpacity, value: number) => void;
}

export default function WaterLayerControl({
    layers,
    opacity,
    onLayerToggle,
    onOpacityChange
}: WaterLayerControlProps) {
    const layerConfig = [
        {
            key: 'waterOccurrence' as keyof WaterLayerState,
            label: 'Water Occurrence',
            description: 'Where water occurred',
            color: '#0066FF'
        },
        {
            key: 'waterChange' as keyof WaterLayerState,
            label: 'Current Water',
            description: '>50% of time',
            color: '#00a8ff'
        },
        {
            key: 'waterSeasonality' as keyof WaterLayerState,
            label: 'Lost Water',
            description: 'Was water, now dry',
            color: '#ff3333'
        },
        {
            key: 'waterRecurrence' as keyof WaterLayerState,
            label: 'New Water',
            description: 'Was dry, now water',
            color: '#33ff33'
        },
        {
            key: 'waterTransitions' as keyof WaterLayerState,
            label: 'Max Extent',
            description: 'Historical maximum',
            color: '#ffcccc'
        }
    ];

    return (
        <div className="space-y-2">
            {layerConfig.map(({ key, label, description, color }) => (
                <label
                    key={key}
                    className={`flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-all border ${
                        layers[key]
                            ? 'bg-slate-800 border-slate-700'
                            : 'border-transparent hover:bg-slate-800/50'
                    }`}
                >
                    <input
                        type="checkbox"
                        checked={layers[key]}
                        onChange={() => onLayerToggle(key)}
                        className="h-3.5 w-3.5 rounded accent-blue-500 bg-slate-800 border-slate-700"
                    />
                    <div className="w-3.5 h-3.5 rounded-sm" style={{ backgroundColor: color }}></div>
                    <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">{label}</div>
                        <div className="text-[10px] text-gray-500">{description}</div>
                    </div>
                </label>
            ))}
        </div>
    );
}
