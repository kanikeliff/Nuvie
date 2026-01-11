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
    @FlexibleDouble var rating: Double?
    let rating_count: Int?
    let user_rating: Int?
    let ai_score: Int?
    let social_score: Int?
    let in_watchlist: Bool
    let watch_status: String?
    let friend_activity: [FriendAction]?
    let explanation: Explanation?
    let friend_ratings: FriendRatings?
    
    var id: Int { movie_id }
    
    enum CodingKeys: String, CodingKey {
        case movie_id, title, genres, poster_url, overview, release_date, tmdb_id, rating, rating_count, user_rating, ai_score, social_score, in_watchlist, watch_status, friend_activity, explanation, friend_ratings
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        movie_id = try container.decode(Int.self, forKey: .movie_id)
        title = try container.decode(String.self, forKey: .title)
        
        // Safe decoding for arrays to prevent crash if backend sends null or wrong type
        genres = container.decodeSafe([String].self, forKey: .genres) ?? []
        
        poster_url = container.decodeSafe(String.self, forKey: .poster_url)
        overview = container.decodeSafe(String.self, forKey: .overview)
        
        // Release date might be tricky, default to empty string if fails
        release_date = container.decodeSafe(String.self, forKey: .release_date) ?? ""
        
        tmdb_id = container.decodeSafe(Int.self, forKey: .tmdb_id)
        
        // Flexible decoding for rating using the property wrapper approach directly or via wrapper
        _rating = try container.decode(FlexibleDouble.self, forKey: .rating)
        
        rating_count = container.decodeSafe(Int.self, forKey: .rating_count)
        user_rating = container.decodeSafe(Int.self, forKey: .user_rating)
        ai_score = container.decodeSafe(Int.self, forKey: .ai_score)
        social_score = container.decodeSafe(Int.self, forKey: .social_score)
        
        // Booleans
        in_watchlist = container.decodeSafe(Bool.self, forKey: .in_watchlist) ?? false
        
        watch_status = container.decodeSafe(String.self, forKey: .watch_status)
        friend_activity = container.decodeSafe([FriendAction].self, forKey: .friend_activity)
        explanation = container.decodeSafe(Explanation.self, forKey: .explanation)
        friend_ratings = container.decodeSafe(FriendRatings.self, forKey: .friend_ratings)
    }

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
    @FlexibleDouble var rating: Double?
    let ai_score: Int?
    let social_score: Int?
    let explanation: Explanation?
    let friend_ratings: FriendRatings?
    let friend_activity: [FriendAction]?
    let watchedBy: [User]?
    let user_rating: Int?
    let overview: String?
    
    var id: Int { movie_id }
    
    enum CodingKeys: String, CodingKey {
        case movie_id, title, poster_url, genres, release_date, rating, ai_score, social_score, explanation, friend_ratings, friend_activity, watchedBy, user_rating, overview
    }
    
    init(movie_id: Int, title: String, poster_url: String?, genres: [String], release_date: String, rating: Double?, ai_score: Int?, social_score: Int?, explanation: Explanation?, friend_ratings: FriendRatings?, friend_activity: [FriendAction]?, watchedBy: [User]?, user_rating: Int?, overview: String?) {
        self.movie_id = movie_id
        self.title = title
        self.poster_url = poster_url
        self.genres = genres
        self.release_date = release_date
        self.rating = rating
        self.ai_score = ai_score
        self.social_score = social_score
        self.explanation = explanation
        self.friend_ratings = friend_ratings
        self.friend_activity = friend_activity
        self.watchedBy = watchedBy
        self.user_rating = user_rating
        self.overview = overview
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        movie_id = try container.decode(Int.self, forKey: .movie_id)
        title = try container.decode(String.self, forKey: .title)
        poster_url = container.decodeSafe(String.self, forKey: .poster_url)
        genres = container.decodeSafe([String].self, forKey: .genres) ?? []
        release_date = container.decodeSafe(String.self, forKey: .release_date) ?? ""
        
        _rating = try container.decode(FlexibleDouble.self, forKey: .rating)
        
        ai_score = container.decodeSafe(Int.self, forKey: .ai_score)
        social_score = container.decodeSafe(Int.self, forKey: .social_score)
        explanation = container.decodeSafe(Explanation.self, forKey: .explanation)
        friend_ratings = container.decodeSafe(FriendRatings.self, forKey: .friend_ratings)
        friend_activity = container.decodeSafe([FriendAction].self, forKey: .friend_activity)
        watchedBy = container.decodeSafe([User].self, forKey: .watchedBy)
        user_rating = container.decodeSafe(Int.self, forKey: .user_rating)
        overview = container.decodeSafe(String.self, forKey: .overview)
    }

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
