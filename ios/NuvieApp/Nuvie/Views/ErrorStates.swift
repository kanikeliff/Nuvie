//
//  ErrorStates.swift
//  Nuvie
//
//  created for phase 3. enhanced error states
//  handles different error types from backend/ai
//

import SwiftUI

enum AppError: Error {
    case networkError
    case authenticationRequired
    case movieNotFound
    case userNotFound
    case ratingInvalid
    case rateLimitExceeded
    case internalError
    case aiServiceError
    case unknown(String)
    
    var code: String {
        switch self {
        case .networkError:
            return "NETWORK_ERROR"
        case .authenticationRequired:
            return "AUTHENTICATION_REQUIRED"
        case .movieNotFound:
            return "MOVIE_NOT_FOUND"
        case .userNotFound:
            return "USER_NOT_FOUND"
        case .ratingInvalid:
            return "RATING_INVALID"
        case .rateLimitExceeded:
            return "RATE_LIMIT_EXCEEDED"
        case .internalError:
            return "INTERNAL_ERROR"
        case .aiServiceError:
            return "AI_SERVICE_ERROR"
        case .unknown(let code):
            return code
        }
    }
    
    var title: String {
        switch self {
        case .networkError:
            return "Connection Problem"
        case .authenticationRequired:
            return "Sign In Required"
        case .movieNotFound:
            return "Movie Not Found"
        case .userNotFound:
            return "User Not Found"
        case .ratingInvalid:
            return "Invalid Rating"
        case .rateLimitExceeded:
            return "Too Many Requests"
        case .internalError:
            return "Server Error"
        case .aiServiceError:
            return "AI Service Unavailable"
        case .unknown:
            return "Something Went Wrong"
        }
    }
    
    var message: String {
        switch self {
        case .networkError:
            return "Please check your internet connection and try again"
        case .authenticationRequired:
            return "Please sign in to continue"
        case .movieNotFound:
            return "This movie could not be found"
        case .userNotFound:
            return "User account not found"
        case .ratingInvalid:
            return "Please select a rating between 1 and 5"
        case .rateLimitExceeded:
            return "You've made too many requests. Please try again later"
        case .internalError:
            return "An internal error occurred. Our team has been notified"
        case .aiServiceError:
            return "Recommendation service is temporarily unavailable"
        case .unknown(let message):
            return message
        }
    }
    
    var icon: String {
        switch self {
        case .networkError:
            return "wifi.slash"
        case .authenticationRequired:
            return "person.crop.circle.badge.exclamationmark"
        case .movieNotFound:
            return "film.slash"
        case .userNotFound:
            return "person.slash"
        case .ratingInvalid:
            return "exclamationmark.triangle"
        case .rateLimitExceeded:
            return "clock.badge.exclamationmark"
        case .internalError:
            return "exclamationmark.octagon"
        case .aiServiceError:
            return "brain.head.profile"
        case .unknown:
            return "exclamationmark.triangle"
        }
    }
    
    var iconColor: Color {
        switch self {
        case .networkError:
            return Color(hex: "3b82f6")
        case .authenticationRequired:
            return Color(hex: "f59e0b")
        case .movieNotFound, .userNotFound:
            return Color(hex: "94a3b8")
        case .ratingInvalid:
            return Color(hex: "fbbf24")
        case .rateLimitExceeded:
            return Color(hex: "f97316")
        case .internalError, .aiServiceError:
            return Color(hex: "ef4444")
        case .unknown:
            return Color(hex: "ef4444")
        }
    }
}

struct EnhancedErrorView: View {
    let error: AppError
    let onRetry: (() -> Void)?
    let onDismiss: (() -> Void)?
    
    init(error: AppError, onRetry: (() -> Void)? = nil, onDismiss: (() -> Void)? = nil) {
        self.error = error
        self.onRetry = onRetry
        self.onDismiss = onDismiss
    }
    
    var body: some View {
        VStack(spacing: 20) {
            // icon
            Image(systemName: error.icon)
                .font(.system(size: 56))
                .foregroundColor(error.iconColor.opacity(0.6))
            
            // title
            Text(error.title)
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.white)
                .multilineTextAlignment(.center)
            
            // message
            Text(error.message)
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "94a3b8"))
                .multilineTextAlignment(.center)
                .lineSpacing(4)
                .padding(.horizontal, 32)
            
            // error code (for debugging)
            Text("Error: \(error.code)")
                .font(.system(size: 11))
                .foregroundColor(Color(hex: "64748b"))
                .padding(.top, 8)
            
            // actions
            VStack(spacing: 12) {
                if let onRetry = onRetry {
                    Button(action: onRetry) {
                        Text("Try Again")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(.white)
                            .frame(width: 200, height: 44)
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
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
                
                if let onDismiss = onDismiss {
                    Button(action: onDismiss) {
                        Text("Dismiss")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(Color(hex: "94a3b8"))
                    }
                }
            }
            .padding(.top, 24)
        }
        .padding(32)
        .frame(maxWidth: 320)
    }
}

// specific error views for common cases

struct NetworkErrorView: View {
    let onRetry: () -> Void
    
    var body: some View {
        EnhancedErrorView(
            error: .networkError,
            onRetry: onRetry
        )
    }
}

struct AuthenticationErrorView: View {
    let onSignIn: () -> Void
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "person.crop.circle.badge.exclamationmark")
                .font(.system(size: 56))
                .foregroundColor(Color(hex: "f59e0b").opacity(0.6))
            
            Text("Sign In Required")
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.white)
            
            Text("Please sign in to view recommendations and rate movies")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "94a3b8"))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            
            Button(action: onSignIn) {
                Text("Sign In")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(width: 200, height: 44)
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
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .padding(.top, 24)
        }
        .padding(32)
    }
}

struct AIServiceErrorView: View {
    let onRetry: () -> Void
    
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "cup.and.saucer.fill")
                .font(.system(size: 64))
                .foregroundColor(Color(hex: "f59e0b").opacity(0.6))
            
            VStack(spacing: 12) {
                Text("Our AI is having a coffee break")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
                
                Text("Showing trending movies instead")
                    .font(.system(size: 16))
                    .foregroundColor(Color(hex: "94a3b8"))
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 32)
            
            Button(action: onRetry) {
                Text("Retry")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(width: 200, height: 44)
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
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .padding(.top, 8)
        }
        .padding(32)
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
