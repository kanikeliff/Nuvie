//
//  Movie.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//

import Foundation

struct Movie: Codable, Identifiable {
    let movie_id: Int
    let title: String
    let genres: [String]
    let poster_url: String?
    let overview: String?
    let release_date: String
    let tmdb_id: Int?
    let rating: Double?
    let rating_count: Int?
    let user_rating: Int?
    let ai_score: Int?
    let social_score: Int?
    let in_watchlist: Bool
    let watch_status: String?
    
    var id: Int { movie_id }
    
    var year: String? {
        guard let date = ISO8601DateFormatter().date(from: release_date) else {
            return nil
        }
        let calendar = Calendar.current
        return String(calendar.component(.year, from: date))
    }
    
    var genresString: String {
        genres.joined(separator: ", ")
    }
}

struct Recommendation: Codable, Identifiable {
    let movie_id: Int
    let title: String
    let poster_url: String?
    let genres: [String]
    let release_date: String
    let rating: Double?
    let ai_score: Int?
    let social_score: Int?
    let explanation: Explanation?
    let friend_ratings: FriendRatings?
    let friend_activity: [FriendAction]?
    let watchedBy: [User]?
    let user_rating: Int?
    let overview: String?
    
    var id: Int { movie_id }
    
    var year: String? {
        guard let date = ISO8601DateFormatter().date(from: release_date) else {
            return nil
        }
        let calendar = Calendar.current
        return String(calendar.component(.year, from: date))
    }
}

struct Explanation: Codable {
    let primary_reason: String
    let reason_type: String?
    let reason_context: String?
    let confidence: Double
    let factors: [ExplanationFactor]
}

struct ExplanationFactor: Codable {
    let type: String
    let weight: Double
    let value: Double
    let payload: [String: String]?
    let description: String
}

struct FriendRatings: Codable {
    let count: Int
    let average: Double
    let friends: [FriendRating]?
}

struct FriendRating: Codable {
    let user_id: Int
    let name: String
    let avatar_url: String?
    let rating: Int
}

struct FriendAction: Codable, Identifiable {
    let user_id: Int
    let name: String
    let avatar_url: String?
    let action_type: FriendActionType
    
    var id: Int { user_id }
}

enum FriendActionType: String, Codable {
    case liked
    case watched
    case rated
}

struct User: Codable, Identifiable {
    let user_id: Int
    let name: String
    let avatar_url: String?
    
    var id: Int { user_id }
}
