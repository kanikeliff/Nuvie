import SwiftUI

struct ProfileView: View {
    @StateObject private var viewModel = ProfileViewModel()
    @State private var showBlockConfirmation = false
    @State private var userToBlock: Friend?
    
    var body: some View {
        ZStack {
            Color(hex: "0f172a")
                .ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: 24) {
                    ProfileHeaderView()
                        .padding(.horizontal, 16)
                        .padding(.top, 16)
                    
                    FriendsSectionView(
                        friends: viewModel.friendsList,
                        onBlockUser: { friend in
                            userToBlock = friend
                            showBlockConfirmation = true
                        }
                    )
                    .padding(.horizontal, 16)
                }
            }
        }
        .navigationTitle("Profile")
        .navigationBarTitleDisplayMode(.large)
        .alert("Block User", isPresented: $showBlockConfirmation) {
            Button("Cancel", role: .cancel) {
                userToBlock = nil
            }
            Button("Block", role: .destructive) {
                if let friend = userToBlock {
                    viewModel.blockUser(friend)
                }
                userToBlock = nil
            }
        } message: {
            if let friend = userToBlock {
                Text("Blocking \(friend.name) will remove their data from your recommendations.")
            }
        }
        .onAppear {
            viewModel.loadFriends()
        }
    }
}

struct ProfileHeaderView: View {
    var body: some View {
        HStack(spacing: 16) {
            Circle()
                .fill(
                    LinearGradient(
                        gradient: Gradient(colors: [
                            Color(hex: "f59e0b"),
                            Color(hex: "d97706")
                        ]),
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(width: 80, height: 80)
                .overlay(
                    Image(systemName: "person.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.white)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                Text("Your Profile")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundColor(.white)
                
                Text("Manage your account and privacy")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "94a3b8"))
            }
            
            Spacer()
        }
        .padding(20)
        .background(Color(hex: "1e293b"))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

struct FriendsSectionView: View {
    let friends: [Friend]
    let onBlockUser: (Friend) -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Friends")
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.white)
            
            if friends.isEmpty {
                Text("No friends yet")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "94a3b8"))
                    .padding(.vertical, 20)
            } else {
                ForEach(friends) { friend in
                    FriendProfileRow(
                        friend: friend,
                        onBlockUser: onBlockUser
                    )
                }
            }
        }
        .padding(20)
        .background(Color(hex: "1e293b"))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

struct FriendProfileRow: View {
    let friend: Friend
    let onBlockUser: (Friend) -> Void
    @State private var showContextMenu = false
    
    var body: some View {
        HStack(spacing: 12) {
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
            .frame(width: 50, height: 50)
            .clipShape(Circle())
            
            VStack(alignment: .leading, spacing: 4) {
                Text(friend.name)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)
                
                Text("Friend")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "94a3b8"))
            }
            
            Spacer()
            
            Menu {
                Button(action: {
                }) {
                    Label("Mute Activity", systemImage: "bell.slash")
                }
                
                Button(role: .destructive, action: {
                    onBlockUser(friend)
                }) {
                    Label("Block User", systemImage: "person.crop.circle.badge.xmark")
                }
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 16))
                    .foregroundColor(Color(hex: "94a3b8"))
                    .frame(width: 32, height: 32)
                    .background(Color(hex: "334155"))
                    .clipShape(Circle())
            }
        }
        .padding(12)
        .background(Color(hex: "0f172a"))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct Friend: Identifiable {
    let id: Int
    let name: String
    let avatar_url: String?
}

struct AvatarPlaceholder: View {
    var body: some View {
        Circle()
            .fill(Color(hex: "334155"))
            .overlay(
                Image(systemName: "person.fill")
                    .font(.system(size: 24))
                    .foregroundColor(Color(hex: "64748b"))
            )
    }
}

@MainActor
class ProfileViewModel: ObservableObject {
    @Published var friendsList: [Friend] = []
    
    func loadFriends() {
        friendsList = [
            Friend(id: 1, name: "Alex", avatar_url: "https://i.pravatar.cc/150?img=1"),
            Friend(id: 2, name: "Sarah", avatar_url: "https://i.pravatar.cc/150?img=5"),
            Friend(id: 3, name: "Mike", avatar_url: "https://i.pravatar.cc/150?img=12"),
            Friend(id: 4, name: "Emma", avatar_url: "https://i.pravatar.cc/150?img=9")
        ]
    }
    
    func blockUser(_ friend: Friend) {
        friendsList.removeAll { $0.id == friend.id }
        NotificationCenter.default.post(name: NSNotification.Name("RefreshFeed"), object: nil)
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
