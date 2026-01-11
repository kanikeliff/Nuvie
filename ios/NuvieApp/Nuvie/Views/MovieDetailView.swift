import SwiftUI

struct MovieDetailView: View {
    let movie: Recommendation
    @State private var feedbackState: FeedbackState = .none
    @State private var showToast = false
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        ZStack {
            Color(hex: "0f172a")
                .ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: 24) {
                    AsyncImage(url: URL(string: movie.poster_url ?? "")) { phase in
                        switch phase {
                        case .empty, .failure:
                            PosterPlaceholder()
                        case .success(let image):
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                        @unknown default:
                            PosterPlaceholder()
                        }
                    }
                    .frame(height: 400)
                    .clipped()
                    
                    VStack(alignment: .leading, spacing: 16) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(movie.title)
                                .font(.system(size: 28, weight: .bold))
                                .foregroundColor(.white)
                            
                            HStack(spacing: 8) {
                                if let year = movie.year {
                                    Text(year)
                                        .font(.system(size: 14))
                                        .foregroundColor(Color(hex: "94a3b8"))
                                    Text("•")
                                        .font(.system(size: 14))
                                        .foregroundColor(Color(hex: "94a3b8"))
                                }
                                Text(movie.genres.joined(separator: ", "))
                                    .font(.system(size: 14))
                                    .foregroundColor(Color(hex: "94a3b8"))
                            }
                            
                            if let rating = movie.rating {
                                HStack(spacing: 4) {
                                    Image(systemName: "star.fill")
                                        .font(.system(size: 14))
                                        .foregroundColor(Color(hex: "fbbf24"))
                                    Text(String(format: "%.1f", rating))
                                        .font(.system(size: 16, weight: .medium))
                                        .foregroundColor(.white)
                                }
                            }
                        }
                        
                        if let overview = movie.overview {
                            Text(overview)
                                .font(.system(size: 16))
                                .foregroundColor(Color(hex: "cbd5e1"))
                                .lineSpacing(4)
                        }
                        
                        RecommendationFeedbackSection(
                            feedbackState: $feedbackState,
                            onFeedbackSubmitted: {
                                showToast = true
                                NotificationCenter.default.post(name: NSNotification.Name("RefreshFeed"), object: nil)
                            }
                        )
                    }
                    .padding(20)
                }
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toast(message: "Thanks! We will show more movies like this.", isShowing: $showToast)
    }
}

struct RecommendationFeedbackSection: View {
    @Binding var feedbackState: FeedbackState
    let onFeedbackSubmitted: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Was this a good recommendation?")
                .font(.system(size: 18, weight: .semibold))
                .foregroundColor(.white)
            
            HStack(spacing: 20) {
                Button(action: {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
                        feedbackState = .liked
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        onFeedbackSubmitted()
                    }
                }) {
                    VStack(spacing: 8) {
                        Image(systemName: feedbackState == .liked ? "hand.thumbsup.fill" : "hand.thumbsup")
                            .font(.system(size: 32))
                            .foregroundColor(feedbackState == .liked ? Color(hex: "10b981") : Color(hex: "94a3b8"))
                            .scaleEffect(feedbackState == .liked ? 1.2 : 1.0)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 80)
                    .background(
                        feedbackState == .liked ?
                        Color(hex: "10b981").opacity(0.2) :
                        Color(hex: "1e293b")
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(
                                feedbackState == .liked ?
                                Color(hex: "10b981") :
                                Color(hex: "334155"),
                                lineWidth: feedbackState == .liked ? 2 : 1
                            )
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(feedbackState != .none)
                
                Button(action: {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
                        feedbackState = .disliked
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        onFeedbackSubmitted()
                    }
                }) {
                    VStack(spacing: 8) {
                        Image(systemName: feedbackState == .disliked ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                            .font(.system(size: 32))
                            .foregroundColor(feedbackState == .disliked ? Color(hex: "ef4444") : Color(hex: "94a3b8"))
                            .scaleEffect(feedbackState == .disliked ? 1.2 : 1.0)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 80)
                    .background(
                        feedbackState == .disliked ?
                        Color(hex: "ef4444").opacity(0.2) :
                        Color(hex: "1e293b")
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(
                                feedbackState == .disliked ?
                                Color(hex: "ef4444") :
                                Color(hex: "334155"),
                                lineWidth: feedbackState == .disliked ? 2 : 1
                            )
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(feedbackState != .none)
            }
        }
        .padding(16)
        .background(Color(hex: "1e293b"))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

enum FeedbackState {
    case none
    case liked
    case disliked
}

struct PosterPlaceholder: View {
    var body: some View {
        ZStack {
            Color(hex: "1e293b")
            Image(systemName: "film")
                .font(.system(size: 64))
                .foregroundColor(Color(hex: "94a3b8"))
        }
    }
}

struct ToastModifier: ViewModifier {
    @Binding var isShowing: Bool
    let message: String
    
    func body(content: Content) -> some View {
        ZStack {
            content
            
            if isShowing {
                VStack {
                    Spacer()
                    Text(message)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.white)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 12)
                        .background(Color(hex: "1e293b"))
                        .clipShape(Capsule())
                        .shadow(color: .black.opacity(0.3), radius: 8, x: 0, y: 4)
                        .padding(.bottom, 40)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
                .animation(.spring(response: 0.4, dampingFraction: 0.8), value: isShowing)
                .onAppear {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                        withAnimation {
                            isShowing = false
                        }
                    }
                }
            }
        }
    }
}

extension View {
    func toast(message: String, isShowing: Binding<Bool>) -> some View {
        modifier(ToastModifier(isShowing: isShowing, message: message))
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255)
    }
}
