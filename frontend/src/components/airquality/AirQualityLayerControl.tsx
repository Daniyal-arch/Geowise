import React from 'react';
import { AQLayerState, AQLayerOpacity, POLLUTANT_INFO } from '@/types/airQuality';

interface AirQualityLayerControlProps {
    layers: AQLayerState;
    opacity: AQLayerOpacity;
    onLayerToggle: (pollutant: keyof AQLayerState) => void;
    onOpacityChange: (pollutant: keyof AQLayerOpacity, value: number) => void;
}

export default function AirQualityLayerControl({
    layers,
    opacity,
    onLayerToggle,
    onOpacityChange
}: AirQualityLayerControlProps) {
    const pollutants: (keyof AQLayerState)[] = ['NO2', 'SO2', 'CO', 'O3', 'CH4', 'HCHO', 'AEROSOL'];

    return (
        <div className="space-y-2">
            {pollutants.map((pollutant) => {
                const info = POLLUTANT_INFO[pollutant];

                return (
                    <label
                        key={pollutant}
                        className={`flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-all border ${
                            layers[pollutant]
                                ? 'bg-slate-800 border-slate-700'
                                : 'border-transparent hover:bg-slate-800/50'
                        }`}
                    >
                        <input
                            type="checkbox"
                            checked={layers[pollutant]}
                            onChange={() => onLayerToggle(pollutant)}
                            className="h-3.5 w-3.5 rounded accent-blue-500 bg-slate-800 border-slate-700"
                        />
                        <div className="text-lg">{info.icon}</div>
                        <div className="flex-1">
                            <div className="text-xs font-medium text-gray-200">{info.name}</div>
                            <div className="text-[10px] text-gray-500">{pollutant}</div>
                        </div>
                        <div
                            className="w-3.5 h-3.5 rounded-full"
                            style={{ backgroundColor: info.color }}
                        ></div>
                    </label>
                );
            })}
        </div>
    );
}
