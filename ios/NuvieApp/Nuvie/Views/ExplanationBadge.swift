import SwiftUI

struct ExplanationBadge: View {
    let explanation: Explanation
    @Binding var showSheet: Bool
    
    init(explanation: Explanation, showSheet: Binding<Bool> = .constant(false)) {
        self.explanation = explanation
        self._showSheet = showSheet
    }
    
    var body: some View {
        if let reasonType = explanation.reason_type, !reasonType.isEmpty {
            Button(action: {
                showSheet = true
            }) {
                HStack(spacing: 4) {
                    Image(systemName: iconName)
                        .font(.system(size: 11))
                    Text(formattedReasonText)
                        .font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(iconColor)
                .padding(.horizontal, 6)
                .padding(.vertical, 4)
                .background(iconColor.opacity(0.2))
                .clipShape(RoundedRectangle(cornerRadius: 4))
            }
        } else {
            EmptyView()
        }
    }
    
    private var iconName: String {
        if let reasonType = explanation.reason_type {
            switch reasonType {
            case "genre_affinity":
                return "sparkles"
            case "item_similarity":
                return "film.fill"
            case "friend_activity":
                return "person.2.fill"
            case "popular":
                return "chart.bar.fill"
            default:
                return "questionmark.circle.fill"
            }
        }
        return "questionmark.circle.fill"
    }
    
    private var iconColor: Color {
        if let reasonType = explanation.reason_type {
            switch reasonType {
            case "genre_affinity":
                return Color(hex: "f59e0b")
            case "item_similarity":
                return Color(hex: "10b981")
            case "friend_activity":
                return Color(hex: "3b82f6")
            case "popular":
                return Color(hex: "f97316")
            default:
                return Color(hex: "94a3b8")
            }
        }
        return Color(hex: "94a3b8")
    }
    
    private var formattedReasonText: String {
        guard let reasonType = explanation.reason_type else {
            return "recommended for you"
        }
        
        switch reasonType {
        case "item_similarity":
            if let context = explanation.reason_context, !context.isEmpty {
                return "Because you watched \(context)"
            }
            return "Similar to your favorites"
            
        case "genre_affinity":
            if let context = explanation.reason_context, !context.isEmpty {
                let matchPercent = Int(explanation.confidence * 100)
                return "\(context) Fan (\(matchPercent)% Match)"
            }
            return "Genre Match"
            
        case "friend_activity":
            if let friendRatings = explanation.factors.first(where: { $0.type == "friend_activity" })?.payload?["count"] {
                return "\(friendRatings) friends loved this"
            }
            return "friends recommend"
            
        default:
            if let topFactor = explanation.factors.first {
                return topFactor.description
            }
            return "recommended for you"
        }
    }
}

struct ExplanationSheet: View {
    let explanation: Explanation
    let movieTitle: String
    @Binding var isPresented: Bool
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Why this movie?")
                            .font(.system(size: 24, weight: .bold))
                            .foregroundColor(.white)
                        
                        Text(movieTitle)
                            .font(.system(size: 18, weight: .medium))
                            .foregroundColor(Color(hex: "94a3b8"))
                    }
                    .padding(.bottom, 8)
                    
                    HStack {
                        Text("Confidence: \(Int(explanation.confidence * 100))%")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color(hex: "f59e0b").opacity(0.2))
                            .clipShape(Capsule())
                    }
                    
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Reasons")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)
                        
                        ForEach(Array(explanation.factors.enumerated()), id: \.offset) { index, factor in
                            ExplanationFactorCard(factor: factor, index: index + 1)
                        }
                    }
                }
                .padding(24)
            }
            .background(Color(hex: "0f172a"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        isPresented = false
                    }
                    .foregroundColor(Color(hex: "f59e0b"))
                }
            }
        }
    }
}

struct ExplanationFactorCard: View {
    let factor: ExplanationFactor
    let index: Int
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Text("\(index)")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.white)
                .frame(width: 28, height: 28)
                .background(factorColor.opacity(0.3))
                .clipShape(Circle())
            
            VStack(alignment: .leading, spacing: 4) {
                Text(factorTypeLabel)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(factorColor)
                
                Text(factor.description)
                    .font(.system(size: 14))
                    .foregroundColor(.white)
                    .fixedSize(horizontal: false, vertical: true)
                
                HStack(spacing: 4) {
                    Text("Weight: \(Int(factor.weight * 100))%")
                        .font(.system(size: 11))
                        .foregroundColor(Color(hex: "94a3b8"))
                }
                .padding(.top, 4)
            }
            
            Spacer()
        }
        .padding(16)
        .background(Color(hex: "1e293b"))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    
    private var factorTypeLabel: String {
        switch factor.type {
        case "genre_match", "genre_affinity":
            return "Genre Match"
        case "friend_activity":
            return "Friend Activity"
        case "similar_movies", "item_similarity":
            return "Similar Movies"
        case "popular":
            return "Popular"
        default:
            return factor.type.capitalized
        }
    }
    
    private var factorColor: Color {
        switch factor.type {
        case "genre_match", "genre_affinity":
            return Color(hex: "f59e0b")
        case "friend_activity":
            return Color(hex: "3b82f6")
        case "similar_movies", "item_similarity":
            return Color(hex: "10b981")
        case "popular":
            return Color(hex: "f97316")
        default:
            return Color(hex: "94a3b8")
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
