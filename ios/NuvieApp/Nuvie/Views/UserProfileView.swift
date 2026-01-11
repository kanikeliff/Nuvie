import SwiftUI

struct UserProfileView: View {
    let user: User
    @State private var isBlocked = false
    @State private var isMuted = false
    @State private var showToast = false
    @State private var toastMessage = ""
    
    var body: some View {
        ZStack {
            Color(hex: "0f172a")
                .ignoresSafeArea()
            
            VStack(spacing: 32) {
                // Avatar and Name
                VStack(spacing: 16) {
                    AsyncImage(url: URL(string: user.avatar_url ?? "")) { phase in
                        switch phase {
                        case .empty, .failure:
                            AvatarPlaceholder()
                                .frame(width: 120, height: 120)
                        case .success(let image):
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                                .frame(width: 120, height: 120)
                                .clipShape(Circle())
                        @unknown default:
                            AvatarPlaceholder()
                                .frame(width: 120, height: 120)
                        }
                    }
                    .overlay(
                        Circle()
                            .stroke(Color(hex: "334155"), lineWidth: 2)
                    )
                    
                    Text(user.name)
                        .font(.system(size: 24, weight: .bold))
                        .foregroundColor(.white)
                }
                .padding(.top, 48)
                
                // Privacy Controls
                VStack(spacing: 16) {
                    Text("Privacy Controls")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(Color(hex: "94a3b8"))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal)
                    
                    Button(action: {
                        isMuted.toggle()
                        toastMessage = isMuted ? "Muted \(user.name)" : "Unmuted \(user.name)"
                        showToast = true
                    }) {
                        HStack {
                            Image(systemName: isMuted ? "speaker.slash.fill" : "speaker.wave.2.fill")
                            Text(isMuted ? "Unmute" : "Mute")
                            Spacer()
                        }
                        .padding()
                        .background(Color(hex: "1e293b"))
                        .foregroundColor(isMuted ? Color(hex: "f59e0b") : .white)
                        .cornerRadius(12)
                    }
                    .padding(.horizontal)
                    
                    Button(action: {
                        isBlocked.toggle()
                        toastMessage = isBlocked ? "Blocked \(user.name)" : "Unblocked \(user.name)"
                        showToast = true
                    }) {
                        HStack {
                            Image(systemName: isBlocked ? "hand.raised.fill" : "hand.raised")
                            Text(isBlocked ? "Unblock" : "Block")
                            Spacer()
                        }
                        .padding()
                        .background(Color(hex: "1e293b"))
                        .foregroundColor(isBlocked ? Color(hex: "ef4444") : .white)
                        .cornerRadius(12)
                    }
                    .padding(.horizontal)
                }
                
                Spacer()
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toast(message: toastMessage, isShowing: $showToast)
    }
}
