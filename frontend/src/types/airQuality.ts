export interface PollutantStatistic {
    name: string;
    mean: number;
    max: number;
    min: number;
    unit: string;
    sources: string;
    health_impact: string;
    error?: string;
}

export interface AirQualityLevel {
    level: string;
    color: string;
    emoji: string;
    health_advice: string;
}

export interface MonthlyDataPoint {
    month: number;
    month_name: string;
    value: number | null;
}

export interface YearlyDataPoint {
    year: number;
    value: number | null;
}

export interface MonthlyTrend {
    pollutant: string;
    unit: string;
    year: number;
    data: MonthlyDataPoint[];
}

export interface YearlyTrend {
    pollutant: string;
    unit: string;
    start_year: number;
    end_year: number;
    data: YearlyDataPoint[];
    total_change: number;
    change_percent: number;
}

export interface AQTileEntry {
    url: string;
    name: string;
    description: string;
    unit: string;
    vis_params: {
        min: number;
        max: number;
        palette: string[];
    };
}

export interface AQLocation {
    name: string;
    country: string;
    center: [number, number];
    buffer_km: number;
    source: string;
}

export interface AQAnalysisPeriod {
    year: number;
    start_date: string;
    end_date: string;
}

export interface AQMethodology {
    data_source: string;
    resolution: string;
    temporal_coverage: string;
    pollutants_analyzed: string[];
}

export interface AQMapConfig {
    center: [number, number];
    zoom: number;
}

export interface AirQualityResponse {
    success: boolean;
    location: AQLocation;
    analysis_period: AQAnalysisPeriod;
    air_quality_level: AirQualityLevel | null;
    pollutant_statistics: Record<string, PollutantStatistic>;
    monthly_trend: MonthlyTrend | null;
    yearly_trend: YearlyTrend | null;
    tiles: Record<string, AQTileEntry>;
    map_config: AQMapConfig;
    methodology: AQMethodology;
    generated_at: string;
    error?: string;
}

export interface AQLayerState {
    NO2: boolean;
    SO2: boolean;
    CO: boolean;
    O3: boolean;
    CH4: boolean;
    HCHO: boolean;
    AEROSOL: boolean;
}

export interface AQLayerOpacity {
    NO2: number;
    SO2: number;
    CO: number;
    O3: number;
    CH4: number;
    HCHO: number;
    AEROSOL: number;
}

export const DEFAULT_AQ_LAYERS: AQLayerState = {
    NO2: true,
    SO2: false,
    CO: false,
    O3: false,
    CH4: false,
    HCHO: false,
    AEROSOL: false
};

export const DEFAULT_AQ_OPACITY: AQLayerOpacity = {
    NO2: 0.7,
    SO2: 0.7,
    CO: 0.7,
    O3: 0.7,
    CH4: 0.7,
    HCHO: 0.7,
    AEROSOL: 0.7
};

// Pollutant info for UI
export const POLLUTANT_INFO: Record<string, { name: string; icon: string; color: string }> = {
    NO2: { name: 'Nitrogen Dioxide', icon: '🏭', color: '#ff4500' },
    SO2: { name: 'Sulfur Dioxide', icon: '⚡', color: '#00bfff' },
    CO: { name: 'Carbon Monoxide', icon: '🚗', color: '#228b22' },
    O3: { name: 'Ozone', icon: '☀️', color: '#0000ff' },
    CH4: { name: 'Methane', icon: '🐄', color: '#ff8c00' },
    HCHO: { name: 'Formaldehyde', icon: '🏭', color: '#1aa3ff' },
    AEROSOL: { name: 'Aerosol Index', icon: '💨', color: '#808080' }
};
