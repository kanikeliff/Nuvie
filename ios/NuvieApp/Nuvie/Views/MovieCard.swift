//
//  MovieCard.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//

import SwiftUI

struct MovieCard: View {
    let movie: Recommendation
    let compact: Bool
    @State private var isHovered = false
    @State private var showExplanationSheet = false
    @State private var showRatingView = false
    var onRateMovie: ((Int, Int, Recommendation) -> Void)?
      
    init(movie: Recommendation, compact: Bool = false, onRateMovie: ((Int, Int, Recommendation) -> Void)? = nil) {
        self.movie = movie
        self.compact = compact
        self.onRateMovie = onRateMovie
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
                    // poster image
                    ZStack(alignment: .bottomLeading) {
                        AsyncImage(url: URL(string: movie.poster_url ?? "")) { phase in
                            switch phase {
                            case .empty:
                                PosterPlaceholder()
                            case .success(let image):
                                image
                                    .resizable()
                                    .aspectRatio(contentMode: .fill)
                            case .failure:
                                PosterPlaceholder()
                            @unknown default:
                                PosterPlaceholder()
                            }
                        }
                        .frame(width: nil, height: nil)
                        .aspectRatio(2/3, contentMode: .fit)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .scaleEffect(isHovered ? 1.05 : 1.0)
                        .animation(.easeOut(duration: 0.2), value: isHovered)
                        
                        // overlay with badges. shown on hover/press
                        if isHovered {
                            OverlayView(movie: movie, showExplanationSheet: $showExplanationSheet)
                                .transition(.opacity)
                        }
                        
                        // user rating badge. top right. always visible if exists
                        if let userRating = movie.user_rating {
                            UserRatingBadge(rating: userRating)
                                .padding(8)
                        }
                        
                        // quick recommend button. top left. shown on hover
                        if isHovered {
                            QuickRecommendButton(showRating: $showRatingView)
                                .padding(8)
                                .transition(.opacity.combined(with: .scale))
                        }
                    }
                    
                    if !compact {
                        VStack(alignment: .leading, spacing: 4) {
                            if let friendActivity = movie.friend_activity, !friendActivity.isEmpty {
                                SocialBadgeView(friendActivity: friendActivity)
                                    .padding(.bottom, 4)
                            }
                            
                            if let watchedBy = movie.watchedBy, !watchedBy.isEmpty {
                                SocialAvatarStack(users: watchedBy)
                                    .padding(.bottom, 4)
                            }
                            
                            Text(movie.title)
                                .font(.system(size: 14, weight: .regular))
                                .foregroundColor(.white)
                                .lineLimit(1)
                            
                            HStack(spacing: 4) {
                                if let year = movie.year {
                                    Text(year)
                                        .font(.system(size: 12))
                                        .foregroundColor(Color(hex: "94a3b8"))
                                    Text("•")
                                        .font(.system(size: 12))
                                        .foregroundColor(Color(hex: "94a3b8"))
                                }
                                Text(movie.genres.prefix(2).joined(separator: ", "))
                                    .font(.system(size: 12))
                                    .foregroundColor(Color(hex: "94a3b8"))
                                    .lineLimit(1)
                            }
                        }
                        .padding(.top, 8)
                    }
                }
                .simultaneousGesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { _ in
                            withAnimation(.easeInOut(duration: 0.3)) {
                                isHovered = true
                            }
                        }
                        .onEnded { _ in
                            withAnimation(.easeInOut(duration: 0.3)) {
                                isHovered = false
                            }
                        }
                )
                .onTapGesture {
                }
                .sheet(isPresented: $showExplanationSheet) {
                    if let explanation = movie.explanation {
                        ExplanationSheet(
                            explanation: explanation,
                            movieTitle: movie.title,
                            isPresented: $showExplanationSheet
                        )
                    }
                }
                .sheet(isPresented: $showRatingView) {
                    RatingView(
                        movie: movie,
                        isPresented: $showRatingView,
                        onRatingSubmitted: { newRating in
                            if let onRate = onRateMovie {
                                onRate(movie.movie_id, newRating, movie)
                            }
                            NotificationCenter.default.post(name: NSNotification.Name("RefreshFeed"), object: nil)
                        }
                    )
                }
            }
        }

        // MARK: - supporting views

        struct PosterPlaceholder: View {
            var body: some View {
                ZStack {
                    Color(hex: "1e293b")
                    Image(systemName: "film")
                        .font(.system(size: 32))
                        .foregroundColor(Color(hex: "94a3b8"))
                }
            }
        }

        struct OverlayView: View {
            let movie: Recommendation
            @Binding var showExplanationSheet: Bool
            
            var body: some View {
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color.black.opacity(0.8),
                        Color.black.opacity(0.2),
                        Color.clear
                    ]),
                    startPoint: .bottom,
                    endPoint: .top
                )
                .overlay(alignment: .bottom) {
                    HStack(spacing: 8) {
                        if let rating = movie.rating {
                            RatingBadge(rating: rating)
                        }
                        if let aiScore = movie.ai_score {
                            AIScoreBadge(score: aiScore)
                        }
                        if let socialScore = movie.social_score {
                            SocialScoreBadge(score: socialScore)
                        }
                        if let explanation = movie.explanation, let reasonType = explanation.reason_type, !reasonType.isEmpty {
                            ExplanationBadge(explanation: explanation, showSheet: $showExplanationSheet)
                        }
                    }
                    .padding(12)
                }
            }
        }

        struct RatingBadge: View {
            let rating: Double
            
            var body: some View {
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 11))
                    Text(String(format: "%.1f", rating))
                        .font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(Color(hex: "fbbf24"))
                .padding(.horizontal, 4)
                .padding(.vertical, 4)
                .background(Color(hex: "fbbf24").opacity(0.2))
                .clipShape(RoundedRectangle(cornerRadius: 4))
            }
        }

        struct AIScoreBadge: View {
            let score: Int
            
            var body: some View {
                HStack(spacing: 4) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 11))
                    Text("\(score)%")
                        .font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(Color(hex: "f59e0b"))
                .padding(.horizontal, 4)
                .padding(.vertical, 4)
                .background(Color(hex: "f59e0b").opacity(0.2))
                .clipShape(RoundedRectangle(cornerRadius: 4))
            }
        }

        struct SocialScoreBadge: View {
            let score: Int
            
            var body: some View {
                HStack(spacing: 4) {
                    Image(systemName: "person.2.fill")
                        .font(.system(size: 11))
                    Text("\(score)%")
                        .font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(Color(hex: "3b82f6"))
                .padding(.horizontal, 4)
                .padding(.vertical, 4)
                .background(Color(hex: "3b82f6").opacity(0.2))
                .clipShape(RoundedRectangle(cornerRadius: 4))
            }
        }

        struct UserRatingBadge: View {
            let rating: Int
            
            var body: some View {
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 11))
                    Text("\(rating)")
                        .font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(.white)
                .padding(.horizontal, 4)
                .padding(.vertical, 4)
                .background(Color(hex: "10b981"))
                .clipShape(RoundedRectangle(cornerRadius: 4))
            }
        }

        struct QuickRecommendButton: View {
            @Binding var showRating: Bool
            
            var body: some View {
                Button(action: {
                    showRating = true
                }) {
                    Image(systemName: "paperplane.fill")
                        .font(.system(size: 12))
                        .foregroundColor(.white)
                        .frame(width: 32, height: 32)
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
                        .clipShape(Circle())
                        .shadow(color: .black.opacity(0.3), radius: 4, x: 0, y: 2)
                }
            }
        }

        // MARK: - color extension

        extension Color {
            init(hex: String) {
                let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
                var int: UInt64 = 0
                Scanner(string: hex).scanHexInt64(&int)
                let a, r, g, b: UInt64
                switch hex.count {
                case 3: // rgb 12-bit
                    (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
                case 6: // rgb 24-bit
                    (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
                case 8: // argb 32-bit
                    (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
                default:
                    (a, r, g, b) = (255, 0, 0, 0)
                }
                self.init(
                    .sRGB,
                    red: Double(r) / 255,
                    green: Double(g) / 255,
                    blue: Double(b) / 255,
                    opacity: Double(a) / 255
                )
            }
        }
        

