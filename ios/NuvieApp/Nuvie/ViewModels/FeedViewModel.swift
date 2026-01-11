//
//  FeedViewModel.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//

import Foundation
import Combine

@MainActor
final class FeedViewModel: ObservableObject {

    @Published var recommendations: [Recommendation] = []
    @Published var trendingMovies: [Recommendation] = []
    @Published var activities: [Activity] = []

    @Published var isLoading: Bool = true
    @Published var showError: Bool = false
    @Published var error: AppError?
    
    @Published var debugSimulateError: Bool = false
    @Published var enableMockSocialData: Bool = false
    @Published var isColdStart: Bool = false
    @Published var ratingsCount: Int = 0
    
    init() {
        NotificationCenter.default.addObserver(
            forName: NSNotification.Name("RefreshFeed"),
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.loadFeed()
        }
    }

    func loadFeed() {
        isLoading = true
        showError = false

        Task {
            if debugSimulateError {
                try await Task.sleep(nanoseconds: 500_000_000)
                self.isLoading = false
                self.showError = true
                self.error = .aiServiceError
                return
            }
            
            do {
                let trending = try APIClient.shared.fetchMockTrending()
                let activity = try APIClient.shared.fetchMockActivities()
                
                if ratingsCount == 0 {
                    self.isColdStart = true
                    var processedTrending = MockDataGenerator.injectFriendActivity(into: trending.recommendations)
                    
                    if enableMockSocialData {
                        processedTrending = MockDataGenerator.injectWatchedBy(into: processedTrending)
                    }
                    
                    self.recommendations = processedTrending
                    self.trendingMovies = processedTrending
                } else {
                    self.isColdStart = false
                    let feed = try APIClient.shared.fetchMockFeed()
                    
                    var processedRecommendations = MockDataGenerator.injectFriendActivity(into: feed.recommendations)
                    var processedTrending = MockDataGenerator.injectFriendActivity(into: trending.recommendations)
                    
                    if enableMockSocialData {
                        processedRecommendations = MockDataGenerator.injectWatchedBy(into: processedRecommendations)
                        processedTrending = MockDataGenerator.injectWatchedBy(into: processedTrending)
                    }
                    
                    self.recommendations = processedRecommendations
                    self.trendingMovies = processedTrending
                }
                
                self.activities = activity.activities

                self.isLoading = false
                self.showError = false
                self.error = nil
            } catch {
                self.isLoading = false
                self.showError = true
                if let apiError = error as? APIError {
                    switch apiError {
                    case .fileNotFound:
                        self.error = .networkError
                    case .decoding:
                        self.error = .internalError
                    }
                } else {
                    self.error = .networkError
                }
            }
        }
    }

    func refreshFeed() async {
        loadFeed()
    }
    
    @Published var isRefreshingRecommendations: Bool = false
    
    func rateMovie(id: Int, rating: Int, movie: Recommendation) {
        if let index = recommendations.firstIndex(where: { $0.movie_id == id }) {
            let updatedRecommendation = Recommendation(
                movie_id: movie.movie_id,
                title: movie.title,
                poster_url: movie.poster_url,
                genres: movie.genres,
                release_date: movie.release_date,
                rating: movie.rating,
                ai_score: movie.ai_score,
                social_score: movie.social_score,
                explanation: movie.explanation,
                friend_ratings: movie.friend_ratings,
                friend_activity: movie.friend_activity,
                watchedBy: movie.watchedBy,
                user_rating: rating,
                overview: movie.overview
            )
            recommendations[index] = updatedRecommendation
        }
        
        let timestamp = ISO8601DateFormatter().string(from: Date())
        let newActivity = Activity(
            activity_id: Int.random(in: 10000...99999),
            user_id: 1,
            user_name: "You",
            user_avatar: nil,
            movie_id: id,
            movie_title: movie.title,
            movie_poster: movie.poster_url,
            type: .rating,
            rating: rating,
            comment: nil,
            timestamp: timestamp
        )
        activities.insert(newActivity, at: 0)
        
        Task {
            do {
                try await Task.sleep(nanoseconds: 500_000_000)
                
                isRefreshingRecommendations = true
                
                try await Task.sleep(nanoseconds: 1_000_000_000)
                
                let feed = try APIClient.shared.fetchMockFeed()
                var processedRecommendations = MockDataGenerator.injectFriendActivity(into: feed.recommendations)
                
                if enableMockSocialData {
                    processedRecommendations = MockDataGenerator.injectWatchedBy(into: processedRecommendations)
                }
                
                await MainActor.run {
                    self.recommendations = processedRecommendations
                    self.isRefreshingRecommendations = false
                }
            } catch {
                await MainActor.run {
                    self.isRefreshingRecommendations = false
                }
            }
        }
    }
}
