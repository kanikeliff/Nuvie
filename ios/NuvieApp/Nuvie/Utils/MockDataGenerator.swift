import Foundation

struct MockDataGenerator {
    private static let sampleFriends: [(name: String, avatar: String?)] = [
        ("Alex", "https://i.pravatar.cc/150?img=1"),
        ("Sarah", "https://i.pravatar.cc/150?img=5"),
        ("Mike", "https://i.pravatar.cc/150?img=12"),
        ("Emma", "https://i.pravatar.cc/150?img=9"),
        ("David", "https://i.pravatar.cc/150?img=15"),
        ("Lisa", "https://i.pravatar.cc/150?img=20"),
        ("Chris", "https://i.pravatar.cc/150?img=33"),
        ("Jessica", "https://i.pravatar.cc/150?img=47")
    ]
    
    private static let actionTypes: [FriendActionType] = [.liked, .watched, .rated]
    
    static func injectFriendActivity(into recommendations: [Recommendation]) -> [Recommendation] {
        let targetCount = Int(Double(recommendations.count) * 0.3)
        var indices = Set<Int>()
        
        while indices.count < targetCount && indices.count < recommendations.count {
            indices.insert(Int.random(in: 0..<recommendations.count))
        }
        
        return recommendations.enumerated().map { index, recommendation in
            if indices.contains(index) {
                let friendCount = Int.random(in: 1...4)
                let selectedFriends = Array(sampleFriends.shuffled().prefix(friendCount))
                let friendActivity = selectedFriends.map { friend in
                    FriendAction(
                        user_id: Int.random(in: 1000...9999),
                        name: friend.name,
                        avatar_url: friend.avatar,
                        action_type: actionTypes.randomElement() ?? .watched
                    )
                }
                
                return Recommendation(
                    movie_id: recommendation.movie_id,
                    title: recommendation.title,
                    poster_url: recommendation.poster_url,
                    genres: recommendation.genres,
                    release_date: recommendation.release_date,
                    rating: recommendation.rating,
                    ai_score: recommendation.ai_score,
                    social_score: recommendation.social_score,
                    explanation: recommendation.explanation,
                    friend_ratings: recommendation.friend_ratings,
                    friend_activity: friendActivity,
                    user_rating: recommendation.user_rating,
                    overview: recommendation.overview
                )
            } else {
                return recommendation
            }
        }
    }
    
    private static let sampleUsers: [(name: String, avatar: String?)] = [
        ("Alex", "https://i.pravatar.cc/150?img=1"),
        ("Sarah", "https://i.pravatar.cc/150?img=5"),
        ("Mike", "https://i.pravatar.cc/150?img=12"),
        ("Emma", "https://i.pravatar.cc/150?img=9"),
        ("David", "https://i.pravatar.cc/150?img=15")
    ]
    
    static func injectWatchedBy(into recommendations: [Recommendation]) -> [Recommendation] {
        let topThreeCount = min(3, recommendations.count)
        
        return recommendations.enumerated().map { index, recommendation in
            if index < topThreeCount {
                let userCount = Int.random(in: 1...3)
                let selectedUsers = Array(sampleUsers.shuffled().prefix(userCount))
                let watchedBy = selectedUsers.map { user in
                    User(
                        user_id: Int.random(in: 1000...9999),
                        name: user.name,
                        avatar_url: user.avatar
                    )
                }
                
                return Recommendation(
                    movie_id: recommendation.movie_id,
                    title: recommendation.title,
                    poster_url: recommendation.poster_url,
                    genres: recommendation.genres,
                    release_date: recommendation.release_date,
                    rating: recommendation.rating,
                    ai_score: recommendation.ai_score,
                    social_score: recommendation.social_score,
                    explanation: recommendation.explanation,
                    friend_ratings: recommendation.friend_ratings,
                    friend_activity: recommendation.friend_activity,
                    watchedBy: watchedBy,
                    user_rating: recommendation.user_rating,
                    overview: recommendation.overview
                )
            } else {
                return recommendation
            }
        }
    }
}
