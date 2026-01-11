//
//  FeedView.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//

import SwiftUI

struct FeedView: View {
    @StateObject private var viewModel = FeedViewModel()
    @State private var showUpdateBanner = false
        
        // grid columns. based on device size
        private var recommendedColumns: [GridItem] {
            [
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16)
            ]
        }
        
        private var trendingColumns: [GridItem] {
            [
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16)
            ]
        }
    var body: some View {
        ZStack {
                    // background
                    Color(hex: "0f172a")
                        .ignoresSafeArea()
                    
            if viewModel.isLoading {
                        FeedSkeletonView()
            } else if viewModel.showError {
                if let error = viewModel.error, error == .aiServiceError {
                    AIServiceErrorView(onRetry: viewModel.loadFeed)
                } else if let error = viewModel.error {
                    EnhancedErrorView(error: error, onRetry: viewModel.loadFeed)
                } else {
                    ErrorStateView(onRetry: viewModel.loadFeed)
                }
                    } else {
                        ZStack(alignment: .top) {
                            ScrollView {
                                VStack(spacing: 32) {
                                    // hero section
                                    HeroSection()
                                        .padding(.horizontal, 16)
                                        .padding(.top, 24)
                                
                                // recommended for you
                                if viewModel.recommendations.isEmpty {
                                    NoRecommendationsView(onDiscoverTap: {
                                        // Navigate to discover
                                    })
                                    .padding(.horizontal, 16)
                                } else {
                                    RecommendedSection(recommendations: viewModel.recommendations, isColdStart: viewModel.isColdStart, viewModel: viewModel)
                                        .padding(.horizontal, 16)
                                }
                                
                                // trending now
                                if !viewModel.trendingMovies.isEmpty {
                                    TrendingSection(movies: viewModel.trendingMovies)
                                        .padding(.horizontal, 16)
                                }
                                
                                // friend activity
                                if viewModel.activities.isEmpty {
                                    NoFriendActivityView(onFindFriendsTap: {
                                        // navigate to social
                                    })
                                    .padding(.horizontal, 16)
                                } else {
                                    ActivitySection(activities: viewModel.activities)
                                        .padding(.horizontal, 16)
                                }
                            }
                            .padding(.bottom, 16)
                            }
                            .padding(.top, showUpdateBanner ? 60 : 0)
                        }
                        
                        if showUpdateBanner {
                            ModelUpdateBanner()
                                .transition(.move(edge: .top).combined(with: .opacity))
                                .zIndex(1)
                        }
                    }
                }
                .onAppear {
                    viewModel.loadFeed()
                }
                .refreshable {
                    await viewModel.refreshFeed()
                    withAnimation {
                        showUpdateBanner = true
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                        withAnimation {
                            showUpdateBanner = false
                        }
                    }
                }
                .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("RefreshFeed"))) { _ in
                    withAnimation {
                        showUpdateBanner = true
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                        withAnimation {
                            showUpdateBanner = false
                        }
                    }
                }
                .onLongPressGesture(minimumDuration: 2.0) {
                    viewModel.debugSimulateError.toggle()
                    viewModel.loadFeed()
                }
            }
   
   }
    
// MARK: - hero section

struct HeroSection: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Image(systemName: "sparkles")
                    .font(.system(size: 24))
                    .foregroundColor(Color(hex: "f59e0b"))
                    .frame(width: 40, height: 40)
                    .background(Color(hex: "f59e0b").opacity(0.2))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("🎬 AI Recommendations")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(.white)
                    
                    Text("Personalized picks based on your taste and social network")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "94a3b8"))
                }
            }
            
            HStack(spacing: 8) {
                Badge(text: "🎯 ML Score: 94%", color: Color(hex: "f59e0b"))
                Badge(text: "🎪 Social Match: 89%", color: Color(hex: "ef4444"))
            }
        }
        .padding(24)
        .background(
            LinearGradient(
                gradient: Gradient(colors: [
                    Color(hex: "92400e").opacity(0.4),
                    Color(hex: "78350f").opacity(0.3),
                    Color(hex: "7f1d1d").opacity(0.4)
                ]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color(hex: "f59e0b").opacity(0.2), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(alignment: .topTrailing) {
            Text("🍿")
                .font(.system(size: 32))
                .opacity(0.2)
                .padding(.trailing, 16)
                .padding(.top, 16)
        }
    }
}

struct Badge: View {
    let text: String
    let color: Color
    
    var body: some View {
        Text(text)
            .font(.system(size: 11, weight: .medium))
            .foregroundColor(color)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(color.opacity(0.2))
            .clipShape(Capsule())
    }
}

// MARK: - recommended section

struct RecommendedSection: View {
    let recommendations: [Recommendation]
    let isColdStart: Bool
    let viewModel: FeedViewModel
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text(isColdStart ? "🍿 Popular on Nuvie" : "🍿 Recommended For You")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(.white)
                
                Spacer()
                
                Button(action: {
                }) {
                    Text("See all")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "f59e0b"))
                }
            }
            
            LazyVGrid(columns: [
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16)
            ], spacing: 16) {
                ForEach(Array(recommendations.prefix(6).enumerated()), id: \.element.id) { index, movie in
                    ZStack {
                        MovieCard(
                            movie: movie,
                            compact: false,
                            onRateMovie: { movieId, rating, movie in
                                viewModel.rateMovie(id: movieId, rating: rating, movie: movie)
                            }
                        )
                        
                        if viewModel.isRefreshingRecommendations && index == recommendations.prefix(6).count - 1 {
                            Color.black.opacity(0.3)
                                .overlay(
                                    ProgressView()
                                        .tint(Color(hex: "f59e0b"))
                                )
                        }
                    }
                }
            }
        }
    }
}

// MARK: - trending section

struct TrendingSection: View {
    let movies: [Recommendation]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 8) {
                Image(systemName: "chart.line.uptrend.xyaxis")
                    .font(.system(size: 20))
                    .foregroundColor(Color(hex: "f97316"))
                
                Text("Trending Now")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(.white)
            }
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    ForEach(movies.prefix(10)) { movie in
                        MovieCard(movie: movie, compact: true)
                            .frame(width: 100)
                    }
                }
            }
        }
    }
}

// MARK: - activity section

struct ActivitySection: View {
    let activities: [Activity]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 8) {
                Image(systemName: "clock.fill")
                    .font(.system(size: 20))
                    .foregroundColor(Color(hex: "3b82f6"))
                
                Text("Friend Activity")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(.white)
            }
            
            VStack(spacing: 12) {
                ForEach(activities.prefix(3)) { activity in
                    ActivityCard(activity: activity)
                }
            }
            
            Button(action: {
                // navigate to view all activity
            }) {
                Text("View All Activity")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 44)
                    .background(Color(hex: "1e293b"))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .padding(.top, 8)
        }
    }
}

// MARK: - error state

struct ModelUpdateBanner: View {
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "sparkles")
                .font(.system(size: 16))
                .foregroundColor(Color(hex: "f59e0b"))
            
            Text("Feed Updated based on your recent activity")
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity)
        .background(
            LinearGradient(
                gradient: Gradient(colors: [
                    Color(hex: "f59e0b").opacity(0.9),
                    Color(hex: "d97706").opacity(0.9)
                ]),
                startPoint: .leading,
                endPoint: .trailing
            )
        )
        .shadow(color: .black.opacity(0.2), radius: 8, x: 0, y: 4)
    }
}

struct ErrorStateView: View {
    let onRetry: () -> Void
    
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(Color(hex: "ef4444").opacity(0.5))
            
            Text("Something went wrong")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(.white)
            
            Text("Please check your connection and try again")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "94a3b8"))
                .multilineTextAlignment(.center)
            
            Button(action: onRetry) {
                Text("Try Again")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(.white)
                    .frame(width: 200, height: 44)
                    .background(
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color(hex: "f59e0b"),
                                Color(hex: "d97706")
                            ]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .padding(.top, 8)
        }
        .padding(32)
    }
}


