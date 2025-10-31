/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Step } from './Step';
/**
 * Response model for code generation.
 */
export type GenerateResponse = {
    /**
     * Generated PySpark code
     */
    code: string;
    /**
     * Progress steps
     */
    steps: Array<Step>;
    success: boolean;
};

