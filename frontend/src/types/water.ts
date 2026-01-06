export interface WaterStatistics {
    max_extent_km2: number;
    current_permanent_km2: number;
    current_seasonal_km2: number;
    current_total_km2: number;
    lost_water_km2: number;
    new_water_km2: number;
    net_change_km2: number;
    loss_percent: number;
    current_vs_max_percent: number;
    // Additional statistics from valid time series data
    area_start_km2: number;
    area_end_km2: number;
    absolute_change_km2: number;
    change_percent: number;
    annual_change_rate: number;
    valid_data_points: number;
    data_gaps: number;
}

export interface WaterTimeSeriesPoint {
    year: number;
    water_area_km2: number;
}

export interface WaterTileEntry {
    url: string;
    name: string;
    description: string;
}

export interface WaterTiles {
    basemap?: WaterTileEntry;
    water_occurrence?: WaterTileEntry;
    current_water?: WaterTileEntry;
    max_extent?: WaterTileEntry;
    lost_water?: WaterTileEntry;
    new_water?: WaterTileEntry;
    [key: string]: WaterTileEntry | undefined;
}

export interface WaterMethodology {
    data_source: string;
    lake_detection: string;
    resolution: string;
    temporal_coverage: string;
}

export interface WaterAnalysisPeriod {
    start_year: number;
    end_year: number;
    data_source: string;
}

export interface WaterLocation {
    name: string;
    country: string;
    type: string;
    description?: string;
    bounds: number[];
    center: [number, number];
    source: string;
    hydrolakes_area_km2?: number;
}

export interface WaterAnimation {
    frames: { year: number; tile_url: string }[];
    gif_url: string;
    frame_count: number;
    years: number[];
    fps: number;
}

export interface WaterLayerState {
    waterOccurrence: boolean;
    waterChange: boolean;
    waterSeasonality: boolean;
    waterRecurrence: boolean;
    waterTransitions: boolean;
}

export interface WaterLayerOpacity {
    waterOccurrence: number;
    waterChange: number;
    waterSeasonality: number;
    waterRecurrence: number;
    waterTransitions: number;
}

export interface SurfaceWaterResponse {
    // Flat structure returned by backend
    location_name: string;
    country: string;
    water_body_type: string;
    description?: string;
    center: [number, number];
    zoom: number;
    bounds: number[];
    start_year: number;
    end_year: number;
    statistics: WaterStatistics;
    time_series: WaterTimeSeriesPoint[];
    tiles: WaterTiles;
    animation?: WaterAnimation;
    show_water: boolean;
    methodology: WaterMethodology;
    generated_at: string;
}

export const DEFAULT_WATER_LAYERS: WaterLayerState = {
    waterOccurrence: true,
    waterChange: false,
    waterSeasonality: false,
    waterRecurrence: false,
    waterTransitions: false
};

export const DEFAULT_WATER_OPACITY: WaterLayerOpacity = {
    waterOccurrence: 0.8,
    waterChange: 0.8,
    waterSeasonality: 0.7,
    waterRecurrence: 0.7,
    waterTransitions: 0.8
};

// Color schemes for water visualization
export const WATER_COLORS = {
    permanent: '#0066FF',      // Blue - permanent water
    seasonal: '#00CCFF',       // Cyan - seasonal water
    loss: '#FF4444',           // Red - water loss
    gain: '#00FF88',           // Green - water gain
    highOccurrence: '#000080', // Dark blue - high occurrence
    lowOccurrence: '#ADD8E6'   // Light blue - low occurrence
};