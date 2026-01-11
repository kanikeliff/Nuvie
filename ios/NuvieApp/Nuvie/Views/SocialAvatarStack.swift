import SwiftUI

struct SocialAvatarStack: View {
    let users: [User]
    
    var body: some View {
        if users.isEmpty {
            EmptyView()
        } else {
            HStack(spacing: 8) {
                ZStack {
                    ForEach(Array(users.prefix(3).enumerated()), id: \.element.id) { index, user in
                        AsyncImage(url: URL(string: user.avatar_url ?? "")) { phase in
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
                        .offset(x: CGFloat(index * 16))
                    }
                }
                .frame(width: CGFloat(min(3, users.count)) * 16 + 8, height: 24)
                
                Text(socialText)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
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
        }
    }
    
    private var socialText: String {
        if users.count == 1 {
            return "Watched by \(users[0].name)"
        } else {
            let remainingCount = users.count - 1
            if remainingCount == 1 {
                return "Watched by \(users[0].name) and 1 other"
            } else {
                return "Watched by \(users[0].name) and \(remainingCount) others"
            }
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
