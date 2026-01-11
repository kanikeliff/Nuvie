//
//  RatingView.swift
//  Nuvie
//
//  created for phase 3. rating flow ux
//  allows users to rate movies and refresh feed
//

import SwiftUI

struct RatingView: View {
    let movie: Recommendation
    @Binding var isPresented: Bool
    @State private var selectedRating: Int = 0
    @State private var comment: String = ""
    @State private var isSubmitting: Bool = false
    @State private var showSuccess: Bool = false
    
    var onRatingSubmitted: ((Int) -> Void)?
    
    var body: some View {
        NavigationView {
            ZStack {
                Color(hex: "0f172a")
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: 24) {
                        // movie poster and title
                        VStack(spacing: 12) {
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
                            .frame(width: 120, height: 180)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            
                            Text(movie.title)
                                .font(.system(size: 20, weight: .bold))
                                .foregroundColor(.white)
                                .multilineTextAlignment(.center)
                        }
                        .padding(.top, 24)
                        
                        // star rating picker
                        VStack(spacing: 16) {
                            Text("Rate this movie")
                                .font(.system(size: 18, weight: .semibold))
                                .foregroundColor(.white)
                            
                            HStack(spacing: 12) {
                                ForEach(1...5, id: \.self) { rating in
                                    Button(action: {
                                        selectedRating = rating
                                    }) {
                                        Image(systemName: rating <= selectedRating ? "star.fill" : "star")
                                            .font(.system(size: 40))
                                            .foregroundColor(rating <= selectedRating ? Color(hex: "fbbf24") : Color(hex: "475569"))
                                    }
                                }
                            }
                            
                            if selectedRating > 0 {
                                Text(ratingText)
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundColor(Color(hex: "94a3b8"))
                            }
                        }
                        .padding(.vertical, 24)
                        
                        // comment section
                        if selectedRating > 0 {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Add a comment (optional)")
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundColor(.white)
                                
                                TextEditor(text: $comment)
                                    .frame(height: 120)
                                    .padding(12)
                                    .background(Color(hex: "1e293b"))
                                    .foregroundColor(.white)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 8)
                                            .stroke(Color(hex: "334155"), lineWidth: 1)
                                    )
                            }
                        }
                        
                        // submit button
                        if selectedRating > 0 {
                            Button(action: submitRating) {
                                HStack {
                                    if isSubmitting {
                                        ProgressView()
                                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                    } else {
                                        Text("Submit Rating")
                                            .font(.system(size: 16, weight: .semibold))
                                    }
                                }
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .frame(height: 50)
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
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                                .disabled(isSubmitting)
                            }
                            .padding(.top, 8)
                        }
                    }
                    .padding(24)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        isPresented = false
                    }
                    .foregroundColor(Color(hex: "94a3b8"))
                }
            }
            .alert("Rating Submitted", isPresented: $showSuccess) {
                Button("OK") {
                    isPresented = false
                    onRatingSubmitted?()
                }
            } message: {
                Text("Your rating has been saved. Recommendations will update.")
            }
        }
    }
    
    private var ratingText: String {
        switch selectedRating {
        case 1:
            return "Not for me"
        case 2:
            return "Not great"
        case 3:
            return "It's okay"
        case 4:
            return "Really good"
        case 5:
            return "Amazing!"
        default:
            return ""
        }
    }
    
    private func submitRating() {
        isSubmitting = true
        onRatingSubmitted?(selectedRating)
        
        Task {
            try? await Task.sleep(nanoseconds: 500_000_000)
            
            await MainActor.run {
                isSubmitting = false
                showSuccess = true
            }
        }
    }
}

struct PosterPlaceholder: View {
    var body: some View {
        ZStack {
            Color(hex: "1e293b")
            Image(systemName: "film")
                .font(.system(size: 48))
                .foregroundColor(Color(hex: "94a3b8"))
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
