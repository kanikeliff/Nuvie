//
//  FeedView.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//
//  IMPROVEMENTS:
//  - Added smooth loading state transitions with animations
//  - Added pull-to-refresh with haptic feedback
//  - Uses NuvieColors design system
//  - Added accessibility support
//

import SwiftUI

struct FeedView: View {

    @StateObject private var viewModel = FeedViewModel()

    // Grid columns based on device size
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
            // Background
            NuvieColors.background
                .ignoresSafeArea()

            // Content with animated transitions
            Group {
                if viewModel.isLoading && viewModel.recommendations.isEmpty {
                    FeedSkeletonView()
                        .transition(.opacity.combined(with: .scale(scale: 0.98)))
                } else if viewModel.showError {
                    ErrorStateView(onRetry: viewModel.loadFeed)
                        .transition(.opacity.combined(with: .move(edge: .bottom)))
                } else {
                    feedContent
                        .transition(.opacity)
                }
            }
            .animation(.easeInOut(duration: 0.3), value: viewModel.isLoading)
            .animation(.easeInOut(duration: 0.3), value: viewModel.showError)
        }
        .onAppear {
            viewModel.loadFeed()
        }
        .refreshable {
            // Haptic feedback on pull
            let generator = UIImpactFeedbackGenerator(style: .medium)
            generator.impactOccurred()

            await viewModel.refreshFeed()
        }
    }

    // MARK: - Feed Content

    private var feedContent: some View {
        ScrollView {
            VStack(spacing: 32) {
                // Hero section
                HeroSection()
                    .padding(.horizontal, 16)
                    .padding(.top, 24)
                    .transition(.opacity.combined(with: .move(edge: .top)))

                // Recommended for you
                if viewModel.recommendations.isEmpty {
                    NoRecommendationsView(onDiscoverTap: {
                        // Navigate to discover
                    })
                    .padding(.horizontal, 16)
                    .transition(.opacity)
                } else {
                    RecommendedSection(recommendations: viewModel.recommendations)
                        .padding(.horizontal, 16)
                        .transition(.asymmetric(
                            insertion: .opacity.combined(with: .move(edge: .leading)),
                            removal: .opacity
                        ))
                }

                // Trending now
                if !viewModel.trendingMovies.isEmpty {
                    TrendingSection(movies: viewModel.trendingMovies)
                        .padding(.horizontal, 16)
                        .transition(.opacity.combined(with: .move(edge: .trailing)))
                }

                // Friend activity
                if viewModel.activities.isEmpty {
                    NoFriendActivityView(onFindFriendsTap: {
                        // Navigate to social
                    })
                    .padding(.horizontal, 16)
                    .transition(.opacity)
                } else {
                    ActivitySection(activities: viewModel.activities)
                        .padding(.horizontal, 16)
                        .transition(.opacity.combined(with: .move(edge: .bottom)))
                }
            }
            .padding(.bottom, 16)
        }
        .scrollIndicators(.hidden)
    }
}

// MARK: - Hero Section

struct HeroSection: View {
    @State private var isAnimating = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Image(systemName: "sparkles")
                    .font(.system(size: 24))
                    .foregroundColor(NuvieColors.primary)
                    .frame(width: 40, height: 40)
                    .background(NuvieColors.primary.opacity(0.2))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .scaleEffect(isAnimating ? 1.1 : 1.0)
                    .animation(
                        .easeInOut(duration: 1.5).repeatForever(autoreverses: true),
                        value: isAnimating
                    )

                VStack(alignment: .leading, spacing: 4) {
                    Text("AI Recommendations")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(NuvieColors.textPrimary)

                    Text("Personalized picks based on your taste and social network")
                        .font(.system(size: 14))
                        .foregroundColor(NuvieColors.textSecondary)
                }
            }

            HStack(spacing: 8) {
                Badge(text: "ML Score: 94%", color: NuvieColors.primary)
                Badge(text: "Social Match: 89%", color: NuvieColors.error)
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
                .stroke(NuvieColors.primary.opacity(0.2), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .onAppear {
            isAnimating = true
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("AI Recommendations. Personalized picks based on your taste. ML Score 94%, Social Match 89%")
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
            .background(color.opacity(NuvieColors.badgeOpacity))
            .clipShape(Capsule())
    }
}

// MARK: - Recommended Section

struct RecommendedSection: View {
    let recommendations: [Recommendation]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Recommended For You")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(NuvieColors.textPrimary)

                Spacer()

                Button(action: {
                    // Navigate to see all
                }) {
                    Text("See all")
                        .font(.system(size: 14))
                        .foregroundColor(NuvieColors.primary)
                }
                .accessibilityLabel("See all recommendations")
            }

            LazyVGrid(columns: [
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16),
                GridItem(.flexible(), spacing: 16)
            ], spacing: 16) {
                ForEach(recommendations.prefix(6)) { movie in
                    MovieCard(movie: movie, compact: false)
                        .transition(.scale.combined(with: .opacity))
                }
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Recommended movies section")
    }
}

// MARK: - Trending Section

struct TrendingSection: View {
    let movies: [Recommendation]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 8) {
                Image(systemName: "chart.line.uptrend.xyaxis")
                    .font(.system(size: 20))
                    .foregroundColor(NuvieColors.warning)

                Text("Trending Now")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(NuvieColors.textPrimary)
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    ForEach(movies.prefix(10)) { movie in
                        MovieCard(movie: movie, compact: true)
                            .frame(width: 100)
                            .transition(.scale.combined(with: .opacity))
                    }
                }
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Trending movies section")
    }
}

// MARK: - Activity Section

struct ActivitySection: View {
    let activities: [Activity]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 8) {
                Image(systemName: "clock.fill")
                    .font(.system(size: 20))
                    .foregroundColor(NuvieColors.info)

                Text("Friend Activity")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(NuvieColors.textPrimary)
            }

            VStack(spacing: 12) {
                ForEach(activities.prefix(3)) { activity in
                    ActivityCard(activity: activity)
                        .transition(.opacity.combined(with: .move(edge: .leading)))
                }
            }

            Button(action: {
                // Navigate to view all activity
            }) {
                Text("View All Activity")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(NuvieColors.textPrimary)
                    .frame(maxWidth: .infinity)
                    .frame(height: 44)
                    .background(NuvieColors.surface)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .padding(.top, 8)
            .accessibilityLabel("View all friend activity")
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Friend activity section")
    }
}

// MARK: - Error State

struct ErrorStateView: View {
    let onRetry: () -> Void

    @State private var isShaking = false

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(NuvieColors.error.opacity(0.5))
                .rotationEffect(.degrees(isShaking ? -5 : 5))
                .animation(
                    .easeInOut(duration: 0.1).repeatCount(5, autoreverses: true),
                    value: isShaking
                )

            Text("Something went wrong")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(NuvieColors.textPrimary)

            Text("Please check your connection and try again")
                .font(.system(size: 14))
                .foregroundColor(NuvieColors.textSecondary)
                .multilineTextAlignment(.center)

            Button(action: {
                isShaking.toggle()
                let generator = UINotificationFeedbackGenerator()
                generator.notificationOccurred(.warning)
                onRetry()
            }) {
                Text("Try Again")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(NuvieColors.textPrimary)
                    .frame(width: 200, height: 44)
                    .background(NuvieColors.primaryGradient)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .padding(.top, 8)
            .accessibilityLabel("Retry loading feed")
            .accessibilityHint("Double tap to retry")
        }
        .padding(32)
        .accessibilityElement(children: .combine)
    }
}

// MARK: - Preview

#if DEBUG
struct FeedView_Previews: PreviewProvider {
    static var previews: some View {
        FeedView()
    }
}
#endif
