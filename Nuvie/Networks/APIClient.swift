//
//  APIClient.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//
//  SECURITY IMPROVEMENTS:
//  - Removed internal AI token (should only be used server-to-server)
//  - Removed UserDefaults API key access (use Keychain via SecureConfig)
//  - Added comprehensive error handling
//  - Added proper HTTP status code handling
//  - Added request timeout configuration
//

import Foundation

// MARK: - Error Types

/// Comprehensive error type for API operations
enum APIError: Error, LocalizedError {
    case fileNotFound(String)
    case decodingError(String)
    case networkError(Error)
    case httpError(statusCode: Int, message: String?)
    case invalidURL(String)
    case unauthorized
    case serverError(String)
    case timeout
    case noData

    var errorDescription: String? {
        switch self {
        case .fileNotFound(let filename):
            return "Resource not found: \(filename)"
        case .decodingError(let details):
            return "Failed to parse response: \(details)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .httpError(let statusCode, let message):
            return "HTTP \(statusCode): \(message ?? "Unknown error")"
        case .invalidURL(let url):
            return "Invalid URL: \(url)"
        case .unauthorized:
            return "Authentication required"
        case .serverError(let message):
            return "Server error: \(message)"
        case .timeout:
            return "Request timed out"
        case .noData:
            return "No data received"
        }
    }
}

// MARK: - API Environment

enum APIEnvironment {
    case dev
    case prod

    var baseURL: String {
        switch self {
        case .dev:
            return "https://api.dev.nuvie.com"
        case .prod:
            return "https://api.nuvie.com"
        }
    }
}

// MARK: - API Client

final class APIClient {

    static let shared = APIClient()
    private init() {
        configureURLSession()
    }

    // MARK: - Configuration

    private var urlSession: URLSession = .shared
    private let requestTimeout: TimeInterval = 30
    private let resourceTimeout: TimeInterval = 60

    private func configureURLSession() {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = requestTimeout
        configuration.timeoutIntervalForResource = resourceTimeout
        configuration.waitsForConnectivity = true
        urlSession = URLSession(configuration: configuration)
    }

    // MARK: - Environment

    var environment: APIEnvironment {
        #if DEBUG
        return .dev
        #else
        return .prod
        #endif
    }

    var baseURL: String {
        environment.baseURL
    }

    // MARK: - Authentication

    /// Get the stored auth token from Keychain
    private var authToken: String? {
        TokenStore.shared.load()
    }

    /// Check if user is authenticated
    var isAuthenticated: Bool {
        authToken != nil
    }

    // MARK: - Headers

    /// Build request headers (SECURITY: No internal tokens sent from client)
    private var defaultHeaders: [String: String] {
        var headers: [String: String] = [
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Client-Version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0",
            "X-Platform": "iOS"
        ]

        // Add auth token if available
        if let token = authToken {
            headers["Authorization"] = "Bearer \(token)"
        }

        return headers
    }

    // MARK: - Request Building

    private func buildRequest(
        url: URL,
        method: String,
        body: Data? = nil
    ) -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        request.timeoutInterval = requestTimeout

        defaultHeaders.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }

        return request
    }

    // MARK: - Response Handling

    private func handleResponse<T: Decodable>(
        data: Data,
        response: URLResponse,
        responseType: T.Type
    ) throws -> T {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.networkError(URLError(.badServerResponse))
        }

        // Handle different status codes
        switch httpResponse.statusCode {
        case 200..<300:
            // Success - decode response
            do {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                return try decoder.decode(T.self, from: data)
            } catch let decodingError as DecodingError {
                let details = describeDecodingError(decodingError)
                throw APIError.decodingError(details)
            }

        case 401:
            // Unauthorized - clear token and throw
            TokenStore.shared.clear()
            throw APIError.unauthorized

        case 403:
            throw APIError.httpError(statusCode: 403, message: "Access denied")

        case 404:
            throw APIError.httpError(statusCode: 404, message: "Resource not found")

        case 422:
            // Validation error - try to extract message
            let message = extractErrorMessage(from: data)
            throw APIError.httpError(statusCode: 422, message: message)

        case 429:
            throw APIError.httpError(statusCode: 429, message: "Too many requests")

        case 500..<600:
            let message = extractErrorMessage(from: data)
            throw APIError.serverError(message ?? "Internal server error")

        default:
            let message = extractErrorMessage(from: data)
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: message)
        }
    }

    private func extractErrorMessage(from data: Data) -> String? {
        struct ErrorResponse: Decodable {
            let detail: String?
            let message: String?
            let error: String?
        }

        if let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data) {
            return errorResponse.detail ?? errorResponse.message ?? errorResponse.error
        }
        return String(data: data, encoding: .utf8)
    }

    private func describeDecodingError(_ error: DecodingError) -> String {
        switch error {
        case .keyNotFound(let key, _):
            return "Missing key: \(key.stringValue)"
        case .typeMismatch(let type, let context):
            return "Type mismatch for \(type) at \(context.codingPath.map { $0.stringValue }.joined(separator: "."))"
        case .valueNotFound(let type, let context):
            return "Missing value of type \(type) at \(context.codingPath.map { $0.stringValue }.joined(separator: "."))"
        case .dataCorrupted(let context):
            return "Data corrupted: \(context.debugDescription)"
        @unknown default:
            return "Unknown decoding error"
        }
    }
}

// MARK: - Mock Data (Phase 2)

extension APIClient {

    private func loadJSON<T: Decodable>(_ filename: String, as type: T.Type) throws -> T {
        guard let url = Bundle.main.url(forResource: filename, withExtension: "json") else {
            throw APIError.fileNotFound(filename)
        }

        let data = try Data(contentsOf: url)

        do {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(T.self, from: data)
        } catch let decodingError as DecodingError {
            throw APIError.decodingError(describeDecodingError(decodingError))
        }
    }

    func fetchMockFeed() throws -> FeedResponse {
        try loadJSON("mock_feed", as: FeedResponse.self)
    }

    func fetchMockTrending() throws -> FeedResponse {
        try loadJSON("mock_trending", as: FeedResponse.self)
    }

    func fetchMockActivities() throws -> ActivityFeedResponse {
        try loadJSON("mock_activities", as: ActivityFeedResponse.self)
    }
}

// MARK: - Network Requests

extension APIClient {

    /// Perform a GET request
    func get<T: Decodable>(
        endpoint: Endpoint,
        responseType: T.Type
    ) async throws -> T {
        let url = try endpoint.url(baseURL: baseURL)

        let request = buildRequest(url: url, method: "GET")

        do {
            let (data, response) = try await urlSession.data(for: request)
            return try handleResponse(data: data, response: response, responseType: responseType)
        } catch let error as APIError {
            throw error
        } catch let error as URLError where error.code == .timedOut {
            throw APIError.timeout
        } catch {
            throw APIError.networkError(error)
        }
    }

    /// Perform a POST request
    func post<T: Decodable, Body: Encodable>(
        endpoint: Endpoint,
        body: Body,
        responseType: T.Type
    ) async throws -> T {
        let url = try endpoint.url(baseURL: baseURL)

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let bodyData = try encoder.encode(body)

        let request = buildRequest(url: url, method: "POST", body: bodyData)

        do {
            let (data, response) = try await urlSession.data(for: request)
            return try handleResponse(data: data, response: response, responseType: responseType)
        } catch let error as APIError {
            throw error
        } catch let error as URLError where error.code == .timedOut {
            throw APIError.timeout
        } catch {
            throw APIError.networkError(error)
        }
    }

    /// Perform a PUT request
    func put<T: Decodable, Body: Encodable>(
        endpoint: Endpoint,
        body: Body,
        responseType: T.Type
    ) async throws -> T {
        let url = try endpoint.url(baseURL: baseURL)

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let bodyData = try encoder.encode(body)

        let request = buildRequest(url: url, method: "PUT", body: bodyData)

        do {
            let (data, response) = try await urlSession.data(for: request)
            return try handleResponse(data: data, response: response, responseType: responseType)
        } catch let error as APIError {
            throw error
        } catch let error as URLError where error.code == .timedOut {
            throw APIError.timeout
        } catch {
            throw APIError.networkError(error)
        }
    }

    /// Perform a DELETE request
    func delete<T: Decodable>(
        endpoint: Endpoint,
        responseType: T.Type
    ) async throws -> T {
        let url = try endpoint.url(baseURL: baseURL)

        let request = buildRequest(url: url, method: "DELETE")

        do {
            let (data, response) = try await urlSession.data(for: request)
            return try handleResponse(data: data, response: response, responseType: responseType)
        } catch let error as APIError {
            throw error
        } catch let error as URLError where error.code == .timedOut {
            throw APIError.timeout
        } catch {
            throw APIError.networkError(error)
        }
    }
}
