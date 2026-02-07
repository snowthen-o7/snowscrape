/**
 * Base API Client
 * Handles authentication, request formatting, and error handling
 */

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class APIClient {
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

    if (!this.baseURL) {
      console.warn('NEXT_PUBLIC_API_BASE_URL is not set');
    }
  }

  /**
   * Make an authenticated API request (client-side)
   */
  async request<T>(
    endpoint: string,
    token: string,
    options: RequestInit = {}
  ): Promise<T> {
    try {
      if (!token) {
        throw new APIError(401, 'Not authenticated');
      }

      const url = `${this.baseURL}${endpoint}`;

      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          ...options.headers,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Request failed: ${response.status}`;

        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorMessage;
          throw new APIError(response.status, errorMessage, errorData);
        } catch (parseError) {
          throw new APIError(response.status, errorMessage, errorText);
        }
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }

      throw new APIError(
        0,
        error instanceof Error ? error.message : 'Unknown error occurred'
      );
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string, token: string): Promise<T> {
    return this.request<T>(endpoint, token, { method: 'GET' });
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, token: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, token, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, token: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, token, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string, token: string): Promise<T> {
    return this.request<T>(endpoint, token, { method: 'DELETE' });
  }
}

// Export singleton instance
export const apiClient = new APIClient();
