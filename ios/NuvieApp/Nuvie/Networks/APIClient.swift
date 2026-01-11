//
//  APIClient.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//

import Foundation

enum APIError: Error {
    case fileNotFound(String)
    case decoding
}

final class APIClient {

    static let shared = APIClient()
    private init() {}

    // MARK: - Tokens
    private var authToken: String? {
        // Keep it simple
        UserDefaults.standard.string(forKey: "auth_token")
    }

    private let internalToken = "INTERNAL_AI_TOKEN"

    // MARK: - Headers
    var defaultHeaders: [String: String] {
        var headers: [String: String] = [
            "Content-Type": "application/json",
            "X-Internal-Token": internalToken
        ]

        if let token = authToken {
            headers["Authorization"] = "Bearer \(token)"
        }

        return headers
    }
}
extension APIClient {

    private func loadJSON<T: Decodable>(_ filename: String, as type: T.Type) throws -> T {
        guard let url = Bundle.main.url(forResource: filename, withExtension: "json") else {
            throw APIError.fileNotFound(filename)
        }

        let data = try Data(contentsOf: url)

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIError.decoding
        }
    }

    // MARK: - Mock fetchers (Phase 2)

    // MARK: - Mock fetchers
    
    func fetchMockFeed() async throws -> FeedResponse {
        if DemoConfig.isDemoMode {
            try? await Task.sleep(nanoseconds: DemoConfig.getRandomLatency())
        }
        return try loadJSON("mock_feed", as: FeedResponse.self)
    }

    func fetchMockTrending() async throws -> FeedResponse {
        if DemoConfig.isDemoMode {
            try? await Task.sleep(nanoseconds: DemoConfig.getRandomLatency())
        }
        return try loadJSON("mock_trending", as: FeedResponse.self)
    }

    func fetchMockActivities() async throws -> ActivityFeedResponse {
        if DemoConfig.isDemoMode {
            try? await Task.sleep(nanoseconds: DemoConfig.getRandomLatency())
        }
        return try loadJSON("mock_activities", as: ActivityFeedResponse.self)
    }
}

enum APIEnvironment {
    case dev
    case prod
}

extension APIClient {

    var environment: APIEnvironment {
        return .dev
    }

    var baseURL: String {
        switch environment {
        case .dev:
            return "https://api.dev.nuvie.com"
        case .prod:
            return "https://api.nuvie.com"
        }
    }
}

