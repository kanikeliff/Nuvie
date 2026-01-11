import SwiftUI

struct SocialFeedView: View {
    @StateObject private var viewModel = SocialFeedViewModel()
    @State private var selectedMovie: Recommendation?
    
    var body: some View {
        ZStack {
            Color(hex: "0f172a")
                .ignoresSafeArea()
            
            if viewModel.isLoading {
                ProgressView()
                    .tint(Color(hex: "f59e0b"))
            } else if viewModel.activities.isEmpty {
                FindFriendsEmptyState(onFindFriendsTap: {
                })
            } else {
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(viewModel.activities) { activity in
                            FriendActivityCard(
                                activity: activity,
                                onMovieTap: {
                                }
                            )
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 16)
                }
            }
        }
        .navigationTitle("Friend Activity")
        .navigationBarTitleDisplayMode(.large)
        .refreshable {
            await viewModel.loadActivities()
        }
        .task {
            await viewModel.loadActivities()
        }
    }
}

struct FriendActivityCard: View {
    let activity: Activity
    let onMovieTap: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                AsyncImage(url: URL(string: activity.user_avatar ?? "")) { phase in
                    switch phase {
                    case .empty, .failure:
                        AvatarPlaceholder()
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    @unknown default:
                        AvatarPlaceholder()
                    }
                }
                .frame(width: 44, height: 44)
                .clipShape(Circle())
                
                VStack(alignment: .leading, spacing: 2) {
                    Text(activity.user_name)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.white)
                    
                    Text(relativeTimeString(from: activity.timestamp))
                        .font(.system(size: 13))
                        .foregroundColor(Color(hex: "94a3b8"))
                }
                
                Spacer()
            }
            
            HStack(spacing: 16) {
                Button(action: onMovieTap) {
                    AsyncImage(url: URL(string: activity.movie_poster ?? "")) { phase in
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
                    .frame(width: 80, height: 120)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
                
                VStack(alignment: .leading, spacing: 8) {
                    Text(activity.movie_title)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.white)
                        .lineLimit(2)
                    
                    if activity.type == .rating, let rating = activity.rating {
                        HStack(spacing: 4) {
                            ForEach(0..<5) { index in
                                Image(systemName: index < rating ? "star.fill" : "star")
                                    .font(.system(size: 16))
                                    .foregroundColor(index < rating ? Color(hex: "fbbf24") : Color(hex: "475569"))
                            }
                        }
                    }
                    
                    HStack(spacing: 6) {
                        Image(systemName: activityIcon)
                            .font(.system(size: 12))
                            .foregroundColor(activityIconColor)
                        
                        Text(activityTypeText)
                            .font(.system(size: 13))
                            .foregroundColor(Color(hex: "94a3b8"))
                    }
                    .padding(.top, 4)
                    
                    if let comment = activity.comment, !comment.isEmpty {
                        Text(comment)
                            .font(.system(size: 14))
                            .foregroundColor(Color(hex: "cbd5e1"))
                            .lineLimit(3)
                            .padding(.top, 8)
                    }
                }
                
                Spacer()
            }
        }
        .padding(16)
        .background(Color(hex: "1e293b"))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(hex: "334155").opacity(0.5), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    
    private var activityIcon: String {
        switch activity.type {
        case .rating:
            return "star.fill"
        case .review:
            return "message.fill"
        case .watched:
            return "checkmark.circle.fill"
        case .started:
            return "play.circle.fill"
        case .watchlist:
            return "bookmark.fill"
        }
    }
    
    private var activityIconColor: Color {
        switch activity.type {
        case .rating:
            return Color(hex: "fbbf24")
        case .review:
            return Color(hex: "3b82f6")
        case .watched:
            return Color(hex: "10b981")
        case .started:
            return Color(hex: "3b82f6")
        case .watchlist:
            return Color(hex: "a855f7")
        }
    }
    
    private var activityTypeText: String {
        switch activity.type {
        case .rating:
            return "Rated"
        case .review:
            return "Reviewed"
        case .watched:
            return "Watched"
        case .started:
            return "Started watching"
        case .watchlist:
            return "Added to watchlist"
        }
    }
    
    private func relativeTimeString(from timestamp: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: timestamp) else {
            return timestamp
        }
        
        let now = Date()
        let timeInterval = now.timeIntervalSince(date)
        
        if timeInterval < 60 {
            return "Just now"
        } else if timeInterval < 3600 {
            let minutes = Int(timeInterval / 60)
            return "\(minutes) minute\(minutes == 1 ? "" : "s") ago"
        } else if timeInterval < 86400 {
            let hours = Int(timeInterval / 3600)
            return "\(hours) hour\(hours == 1 ? "" : "s") ago"
        } else if timeInterval < 604800 {
            let days = Int(timeInterval / 86400)
            return "\(days) day\(days == 1 ? "" : "s") ago"
        } else {
            let dateFormatter = DateFormatter()
            dateFormatter.dateStyle = .medium
            return dateFormatter.string(from: date)
        }
    }
}

struct FindFriendsEmptyState: View {
    let onFindFriendsTap: () -> Void
    
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "person.2.circle.fill")
                .font(.system(size: 64))
                .foregroundColor(Color(hex: "3b82f6").opacity(0.6))
            
            VStack(spacing: 8) {
                Text("Find Friends")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundColor(.white)
                
                Text("Connect with friends to see their movie activity and get better recommendations")
                    .font(.system(size: 16))
                    .foregroundColor(Color(hex: "94a3b8"))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            
            Button(action: onFindFriendsTap) {
                Text("Find Friends")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(width: 200, height: 50)
                    .background(
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color(hex: "3b82f6"),
                                Color(hex: "2563eb")
                            ]),
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .padding(.top, 8)
        }
        .padding(32)
    }
}

struct AvatarPlaceholder: View {
    var body: some View {
        Circle()
            .fill(Color(hex: "334155"))
            .overlay(
                Image(systemName: "person.fill")
                    .font(.system(size: 20))
                    .foregroundColor(Color(hex: "64748b"))
            )
    }
}

struct PosterPlaceholder: View {
    var body: some View {
        RoundedRectangle(cornerRadius: 8)
            .fill(Color(hex: "334155"))
            .overlay(
                Image(systemName: "film")
                    .font(.system(size: 32))
                    .foregroundColor(Color(hex: "64748b"))
            )
    }
}

@MainActor
class SocialFeedViewModel: ObservableObject {
    @Published var activities: [Activity] = []
    @Published var isLoading: Bool = true
    
    func loadActivities() async {
        isLoading = true
        
        do {
            let response = try APIClient.shared.fetchMockActivities()
            self.activities = response.activities
            self.isLoading = false
        } catch {
            self.activities = []
            self.isLoading = false
        }
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
