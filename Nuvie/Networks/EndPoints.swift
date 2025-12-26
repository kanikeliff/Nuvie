//
//  EndPoints.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//
//  IMPROVEMENTS:
//  - Removed force-unwrap that could crash the app
//  - Added throwing URL construction for safe handling
//  - Added more endpoint cases
//  - Added URL encoding for path parameters
//

import Foundation

/// API Endpoints for the Nuvie backend
enum Endpoint {
    // MARK: - Authentication
    case login
    case register
    case logout
    case refreshToken

    // MARK: - Feed
    case feedHome
    case feedRecommendations
    case activityFeed

    // MARK: - Movies
    case movie(id: String)
    case movieSearch(query: String)
    case rateMovie(id: String)
    case movieWatchlist(id: String)

    // MARK: - User
    case userProfile
    case userPreferences
    case userWatchlist

    // MARK: - Friends
    case friends
    case friendActivity(userId: String)

    /// The path component of the endpoint
    var path: String {
        switch self {
        // Authentication
        case .login:
            return "/auth/login"
        case .register:
            return "/auth/register"
        case .logout:
            return "/auth/logout"
        case .refreshToken:
            return "/auth/refresh"

        // Feed
        case .feedHome:
            return "/feed/home"
        case .feedRecommendations:
            return "/feed/recommendations"
        case .activityFeed:
            return "/feed/activities"

        // Movies
        case .movie(let id):
            return "/movies/\(id.urlPathEncoded)"
        case .movieSearch(let query):
            return "/movies/search?q=\(query.urlQueryEncoded)"
        case .rateMovie(let id):
            return "/movies/\(id.urlPathEncoded)/rate"
        case .movieWatchlist(let id):
            return "/movies/\(id.urlPathEncoded)/watchlist"

        // User
        case .userProfile:
            return "/user/profile"
        case .userPreferences:
            return "/user/preferences"
        case .userWatchlist:
            return "/user/watchlist"

        // Friends
        case .friends:
            return "/friends"
        case .friendActivity(let userId):
            return "/friends/\(userId.urlPathEncoded)/activity"
        }
    }

    /// HTTP method for this endpoint (default: GET)
    var method: String {
        switch self {
        case .login, .register, .rateMovie, .movieWatchlist:
            return "POST"
        case .logout:
            return "DELETE"
        default:
            return "GET"
        }
    }

    /// Whether this endpoint requires authentication
    var requiresAuth: Bool {
        switch self {
        case .login, .register:
            return false
        default:
            return true
        }
    }
}

// MARK: - URL Construction

extension Endpoint {
    /// Construct the full URL for this endpoint
    /// - Parameter baseURL: The base URL of the API
    /// - Returns: The complete URL
    /// - Throws: APIError.invalidURL if URL construction fails
    func url(baseURL: String) throws -> URL {
        let urlString = baseURL + path

        guard let url = URL(string: urlString) else {
            throw APIError.invalidURL(urlString)
        }

        return url
    }

    /// Construct URL with additional query parameters
    /// - Parameters:
    ///   - baseURL: The base URL of the API
    ///   - queryParams: Additional query parameters to append
    /// - Returns: The complete URL with query parameters
    /// - Throws: APIError.invalidURL if URL construction fails
    func url(baseURL: String, queryParams: [String: String]) throws -> URL {
        var urlString = baseURL + path

        if !queryParams.isEmpty {
            let queryString = queryParams
                .map { "\($0.key.urlQueryEncoded)=\($0.value.urlQueryEncoded)" }
                .joined(separator: "&")

            // Check if path already has query params
            if path.contains("?") {
                urlString += "&\(queryString)"
            } else {
                urlString += "?\(queryString)"
            }
        }

        guard let url = URL(string: urlString) else {
            throw APIError.invalidURL(urlString)
        }

        return url
    }
}

// MARK: - String URL Encoding Extensions

private extension String {
    /// URL encode for use in path components
    var urlPathEncoded: String {
        self.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? self
    }

    /// URL encode for use in query parameters
    var urlQueryEncoded: String {
        self.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? self
    }
}
