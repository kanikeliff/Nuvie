import SwiftUI

struct SocialBadgeView: View {
    let friendActivity: [FriendAction]
    
    var body: some View {
        if friendActivity.isEmpty {
            EmptyView()
        } else {
            HStack(spacing: 8) {
                if friendActivity.count == 1 {
                    AsyncImage(url: URL(string: friendActivity[0].avatar_url ?? "")) { phase in
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
                    .frame(width: 24, height: 24)
                    .clipShape(Circle())
                    .overlay(
                        Circle()
                            .stroke(Color.white, lineWidth: 1.5)
                    )
                } else {
                    ZStack {
                        ForEach(Array(friendActivity.prefix(3).enumerated()), id: \.element.id) { index, friend in
                            AsyncImage(url: URL(string: friend.avatar_url ?? "")) { phase in
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
                            .frame(width: 24, height: 24)
                            .clipShape(Circle())
                            .overlay(
                                Circle()
                                    .stroke(Color.white, lineWidth: 1.5)
                            )
                            .offset(x: CGFloat(index * 12))
                        }
                    }
                    .frame(width: CGFloat(min(3, friendActivity.count)) * 12 + 12, height: 24)
                }
                
                Text(friendActivityText)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.white)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color(hex: "3b82f6").opacity(0.9),
                        Color(hex: "2563eb").opacity(0.9)
                    ]),
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .clipShape(Capsule())
            .shadow(color: .black.opacity(0.3), radius: 4, x: 0, y: 2)
        }
    }
    
    private var friendActivityText: String {
        let firstFriend = friendActivity[0]
        let actionText = actionTypeText(for: firstFriend.action_type)
        
        if friendActivity.count == 1 {
            return "\(firstFriend.name) \(actionText)"
        } else {
            let remainingCount = friendActivity.count - 1
            if remainingCount == 1 {
                return "\(firstFriend.name) and 1 friend \(actionText)"
            } else {
                return "\(firstFriend.name) and \(remainingCount) friends \(actionText)"
            }
        }
    }
    
    private func actionTypeText(for type: FriendActionType) -> String {
        switch type {
        case .liked:
            return "liked this"
        case .watched:
            return "watched this"
        case .rated:
            return "rated this"
        }
    }
}

struct AvatarPlaceholder: View {
    var body: some View {
        Circle()
            .fill(Color(hex: "64748b"))
            .overlay(
                Image(systemName: "person.fill")
                    .font(.system(size: 12))
                    .foregroundColor(.white)
            )
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
