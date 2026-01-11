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
    
    // Demo Mode Flags
    var useMockData: Bool { DemoConfig.shared.useMockData }
    var forceSocialData: Bool { DemoConfig.shared.forceSocialData }
    var simulateLatency: Bool { DemoConfig.shared.simulateNetworkLatency }

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
            do {
                // APIClient now handles Demo Mode & Latency internally
                // We just need to call the appropriate methods
                
                let trending: FeedResponse
                let activity: ActivityFeedResponse
                let feed: FeedResponse
                
                if DemoConfig.isDemoMode {
                    // Force mock data path
                    trending = try await APIClient.shared.fetchMockTrending()
                    activity = try await APIClient.shared.fetchMockActivities()
                    feed = try await APIClient.shared.fetchMockFeed()
                } else {
                    // Real API path (currently falls back to mocks in APIClient if not implemented)
                    trending = try await APIClient.shared.fetchMockTrending()
                    activity = try await APIClient.shared.fetchMockActivities()
                    feed = try await APIClient.shared.fetchMockFeed()
                }
                
                if ratingsCount == 0 {
                    self.isColdStart = true
                    var processedTrending = MockDataGenerator.injectFriendActivity(into: trending.recommendations)
                    
                    if forceSocialData {
                        processedTrending = MockDataGenerator.injectWatchedBy(into: processedTrending)
                    }
                    
                    self.recommendations = processedTrending
                    self.trendingMovies = processedTrending
                } else {
                    self.isColdStart = false
                    
                    var processedRecommendations = MockDataGenerator.injectFriendActivity(into: feed.recommendations)
                    var processedTrending = MockDataGenerator.injectFriendActivity(into: trending.recommendations)
                    
                    if forceSocialData {
                        processedRecommendations = MockDataGenerator.injectWatchedBy(into: processedRecommendations)
                        processedTrending = MockDataGenerator.injectWatchedBy(into: processedTrending)
                    }
                    
                    self.recommendations = processedRecommendations
                    self.trendingMovies = processedTrending
                }
                
                self.activities = activity.activities

                self.isLoading = false
            } catch {
                self.isLoading = false
                self.showError = true
                self.error = .networkError
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
                // Simulate processing time
                try await Task.sleep(nanoseconds: 500_000_000)
                
                isRefreshingRecommendations = true
                
                // Fetch new feed with natural latency
                let feed = try await APIClient.shared.fetchMockFeed()
                var processedRecommendations = MockDataGenerator.injectFriendActivity(into: feed.recommendations)
                
                if forceSocialData {
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
