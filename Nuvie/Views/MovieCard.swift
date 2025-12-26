//
//  MovieCard.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//
//  IMPROVEMENTS:
//  - Added comprehensive accessibility labels and hints
//  - Added VoiceOver support with semantic descriptions
//  - Added accessibility traits for interactive elements
//  - Added accessibility identifiers for UI testing
//

import SwiftUI

struct MovieCard: View {
    let movie: Recommendation
    let compact: Bool
    @State private var isHovered = false

    init(movie: Recommendation, compact: Bool = false) {
        self.movie = movie
        self.compact = compact
    }

    // MARK: - Accessibility Helpers

    /// Generate comprehensive accessibility label for VoiceOver
    private var accessibilityLabel: String {
        var components: [String] = []

        // Movie title
        components.append(movie.title)

        // Year if available
        if let year = movie.year {
            components.append("from \(year)")
        }

        // Genres
        if !movie.genres.isEmpty {
            let genreList = movie.genres.prefix(2).joined(separator: " and ")
            components.append(genreList)
        }

        // Rating if available
        if let rating = movie.rating {
            components.append(String(format: "rated %.1f out of 10", rating))
        }

        // AI score if available
        if let aiScore = movie.ai_score {
            components.append("\(aiScore) percent AI match")
        }

        // User rating if available
        if let userRating = movie.user_rating {
            components.append("your rating: \(userRating) stars")
        }

        return components.joined(separator: ", ")
    }

    private var accessibilityHint: String {
        "Double tap to view movie details. Swipe right for quick actions."
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Poster image
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

                // Overlay with badges - shown on hover/press
                if isHovered {
                    OverlayView(movie: movie)
                        .transition(.opacity)
                }

                // User rating badge - top right, always visible if exists
                if let userRating = movie.user_rating {
                    UserRatingBadge(rating: userRating)
                        .padding(8)
                        .accessibilityHidden(true) // Included in parent label
                }

                // Quick recommend button - top left, shown on hover
                if isHovered {
                    QuickRecommendButton(movieTitle: movie.title)
                        .padding(8)
                        .transition(.opacity.combined(with: .scale))
                }
            }

            // Title and metadata - standard cards only
            if !compact {
                VStack(alignment: .leading, spacing: 4) {
                    Text(movie.title)
                        .font(.system(size: 14, weight: .regular))
                        .foregroundColor(NuvieColors.textPrimary)
                        .lineLimit(1)

                    HStack(spacing: 4) {
                        if let year = movie.year {
                            Text(year)
                                .font(.system(size: 12))
                                .foregroundColor(NuvieColors.textSecondary)
                            Text("•")
                                .font(.system(size: 12))
                                .foregroundColor(NuvieColors.textSecondary)
                        }
                        Text(movie.genres.prefix(2).joined(separator: ", "))
                            .font(.system(size: 12))
                            .foregroundColor(NuvieColors.textSecondary)
                            .lineLimit(1)
                    }
                }
                .padding(.top, 8)
                .accessibilityHidden(true) // Text is read by parent
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
            // Navigate to movie detail
        }
        // MARK: - Accessibility Configuration
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint(accessibilityHint)
        .accessibilityAddTraits(.isButton)
        .accessibilityIdentifier("movieCard_\(movie.movie_id)")
        .accessibilityAction(named: "Recommend to friend") {
            // Handle recommend action
        }
    }
}

// MARK: - Supporting Views

struct PosterPlaceholder: View {
    var body: some View {
        ZStack {
            NuvieColors.surface
            Image(systemName: "film")
                .font(.system(size: 32))
                .foregroundColor(NuvieColors.textSecondary)
        }
        .accessibilityLabel("Movie poster loading")
    }
}

struct OverlayView: View {
    let movie: Recommendation

    var body: some View {
        NuvieColors.cardGradient
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
                }
                .padding(12)
            }
            .accessibilityHidden(true) // Badges are described in parent
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
        .foregroundColor(NuvieColors.rating)
        .padding(.horizontal, 4)
        .padding(.vertical, 4)
        .background(NuvieColors.rating.opacity(NuvieColors.badgeOpacity))
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .accessibilityLabel("Rating: \(String(format: "%.1f", rating)) out of 10")
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
        .foregroundColor(NuvieColors.aiScore)
        .padding(.horizontal, 4)
        .padding(.vertical, 4)
        .background(NuvieColors.aiScore.opacity(NuvieColors.badgeOpacity))
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .accessibilityLabel("AI match: \(score) percent")
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
        .foregroundColor(NuvieColors.socialScore)
        .padding(.horizontal, 4)
        .padding(.vertical, 4)
        .background(NuvieColors.socialScore.opacity(NuvieColors.badgeOpacity))
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .accessibilityLabel("Friends match: \(score) percent")
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
        .foregroundColor(NuvieColors.textPrimary)
        .padding(.horizontal, 4)
        .padding(.vertical, 4)
        .background(NuvieColors.userRating)
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .accessibilityLabel("Your rating: \(rating) stars")
    }
}

struct QuickRecommendButton: View {
    let movieTitle: String

    var body: some View {
        Button(action: {
            // Handle recommend action
        }) {
            Image(systemName: "paperplane.fill")
                .font(.system(size: 12))
                .foregroundColor(NuvieColors.textPrimary)
                .frame(width: 32, height: 32)
                .background(NuvieColors.primaryGradient)
                .clipShape(Circle())
                .shadow(color: .black.opacity(NuvieColors.shadowOpacity), radius: 4, x: 0, y: 2)
        }
        .accessibilityLabel("Recommend \(movieTitle) to a friend")
        .accessibilityHint("Double tap to share this movie with friends")
        .accessibilityAddTraits(.isButton)
    }
}

// MARK: - Preview

#if DEBUG
struct MovieCard_Previews: PreviewProvider {
    static var previews: some View {
        let sampleMovie = Recommendation(
            movie_id: 1,
            title: "Inception",
            poster_url: nil,
            year: "2010",
            genres: ["Sci-Fi", "Action", "Thriller"],
            rating: 8.8,
            ai_score: 95,
            social_score: 87,
            user_rating: 5
        )

        VStack {
            MovieCard(movie: sampleMovie)
                .frame(width: 160)

            MovieCard(movie: sampleMovie, compact: true)
                .frame(width: 120)
        }
        .padding()
        .background(NuvieColors.background)
    }
}
#endif
