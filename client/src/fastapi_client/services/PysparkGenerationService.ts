/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GenerateRequest } from '../models/GenerateRequest';
import type { GenerateResponse } from '../models/GenerateResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PysparkGenerationService {
    /**
     * Generate Pyspark Endpoint
     * Generate PySpark code from mapping CSV with step tracking.
     * @param requestBody
     * @returns GenerateResponse Successful Response
     * @throws ApiError
     */
    public static generatePysparkEndpointApiCodegenGeneratePysparkPost(
        requestBody: GenerateRequest,
    ): CancelablePromise<GenerateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/codegen/generate-pyspark',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
