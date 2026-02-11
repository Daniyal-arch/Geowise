export interface UrbanExpansionResponse {
    location?: {
        name: string;
        lat: number;
        lng: number;
        center?: [number, number];
    };
    location_name?: string;
    start_year?: number;
    end_year?: number;
    analysis_period?: {
        start_year: number;
        end_year: number;
    };
    tile_urls?: Record<string, string>;
    tiles?: Record<string, string>;
    statistics?: {
        area_start_ha: number;
        area_end_ha: number;
        absolute_growth_ha: number;
        growth_percent: number;
        annual_growth_rate: number;
    };
    un_sdg_11_3_1?: {
        lcr: number;
        pgr: number;
        ratio: string | number;
    };
    distance_rings?: Record<string, {
        growth_pct: number;
        [key: string]: any;
    }>;
    epochs?: Record<string, {
        built_up_hectares: number;
        population: number;
        [key: string]: any;
    }>;
    growth_rates?: Record<string, any>;
    animation_url?: string;
    center?: [number, number];
    zoom?: number;
}
