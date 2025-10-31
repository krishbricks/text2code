/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for code generation.
 */
export type GenerateRequest = {
    /**
     * 'volume' or 'jira'
     */
    source_type: string;
    /**
     * Path to mapping CSV in UC Volume (optional if mapping_csv_content provided)
     */
    input_volume_path?: (string | null);
    /**
     * Path where generated code will be saved
     */
    output_volume_path: string;
    /**
     * ETL pattern (only 'pyspark' supported)
     */
    pattern?: string;
    /**
     * CSV content as string (optional - provide this OR input_volume_path)
     */
    mapping_csv_content?: (string | null);
};

