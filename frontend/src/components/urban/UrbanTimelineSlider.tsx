// components/urban/UrbanTimelineSlider.tsx

import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, SkipBack, SkipForward, Film } from 'lucide-react';

interface UrbanTimelineSliderProps {
    years: number[];
    currentYear: number;
    onYearChange: (year: number, previousYear?: number) => void;  // Added previousYear
    isPlaying?: boolean;
    onPlayToggle?: (playing: boolean) => void;
    onShowGif?: () => void;  // Optional GIF button
}

export default function UrbanTimelineSlider({
    years,
    currentYear,
    onYearChange,
    isPlaying = false,
    onPlayToggle,
    onShowGif
}: UrbanTimelineSliderProps) {
    const [localPlaying, setLocalPlaying] = useState(isPlaying);
    const [isMinimized, setIsMinimized] = useState(true);
    const previousYearRef = useRef(currentYear);

    useEffect(() => {
        setLocalPlaying(isPlaying);
    }, [isPlaying]);

    useEffect(() => {
        let interval: NodeJS.Timeout;
        
        if (localPlaying) {
            interval = setInterval(() => {
                const currentIndex = years.indexOf(currentYear);
                const nextIndex = (currentIndex + 1) % years.length;
                const previousYear = currentYear;
                const nextYear = years[nextIndex];

                // Pass both current and previous year for smooth transition
                onYearChange(nextYear, previousYear);
                previousYearRef.current = nextYear;
            }, 3500); // 3.5 seconds per frame to allow tiles to load
        }
        
        return () => clearInterval(interval);
    }, [localPlaying, currentYear, years, onYearChange]);

    const handlePlayClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        const newPlaying = !localPlaying;
        setLocalPlaying(newPlaying);
        onPlayToggle?.(newPlaying);
    };

    const handleStep = (direction: 'prev' | 'next') => {
        const currentIndex = years.indexOf(currentYear);
        const previousYear = currentYear;
        let nextIndex;
        
        if (direction === 'prev') {
            nextIndex = currentIndex - 1;
            if (nextIndex < 0) nextIndex = years.length - 1;
        } else {
            nextIndex = currentIndex + 1;
            if (nextIndex >= years.length) nextIndex = 0;
        }
        
        onYearChange(years[nextIndex], previousYear);
        setLocalPlaying(false);
        onPlayToggle?.(false);
    };

    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const previousYear = currentYear;
        const newYear = years[parseInt(e.target.value)];
        onYearChange(newYear, previousYear);
        setLocalPlaying(false);
        onPlayToggle?.(false);
    };

    // Progress indicator
    const progress = ((years.indexOf(currentYear)) / (years.length - 1)) * 100;

    return (
        <div className="absolute top-20 left-4 z-[60]">
            {isMinimized ? (
                <button
                    onClick={() => setIsMinimized(false)}
                    className="flex items-center gap-2 bg-gray-900/95 backdrop-blur-md border border-gray-700/50 rounded-lg px-2 py-1 shadow-lg hover:bg-gray-800 transition-all text-white"
                >
                    {localPlaying ? (
                        <Pause size={14} className="text-purple-400 animate-pulse" />
                    ) : (
                        <Play size={14} className="text-purple-400" />
                    )}
                    <span className="text-sm font-mono font-bold">{currentYear}</span>
                </button>
            ) : (
                <div className="bg-gray-900/95 backdrop-blur-md border border-gray-700/50 rounded-lg p-2 shadow-lg w-auto">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => handleStep('prev')}
                            className="p-1 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-all"
                        >
                            <SkipBack size={16} />
                        </button>

                        <button
                            onClick={handlePlayClick}
                            className={`p-2 rounded shadow transition-all ${
                                localPlaying
                                    ? 'bg-purple-600 hover:bg-purple-500'
                                    : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500'
                            }`}
                        >
                            {localPlaying ? (
                                <Pause size={16} className="text-white" fill="currentColor" />
                            ) : (
                                <Play size={16} className="text-white ml-0.5" fill="currentColor" />
                            )}
                        </button>

                        <button
                            onClick={() => handleStep('next')}
                            className="p-1 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-all"
                        >
                            <SkipForward size={16} />
                        </button>

                        <span className="text-lg font-mono font-bold text-white px-2">{currentYear}</span>

                        <button
                            onClick={() => setIsMinimized(true)}
                            className="p-1 rounded hover:bg-gray-800 text-gray-500 hover:text-white transition-all ml-1"
                        >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}