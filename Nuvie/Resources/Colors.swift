//
//  Colors.swift
//  Nuvie
//
//  Design System: Centralized color definitions
//  Following Tailwind CSS color palette conventions
//

import SwiftUI

// MARK: - Design System Colors

/// Centralized color definitions for consistent UI styling.
/// Uses semantic naming for maintainability and dark mode support.
enum NuvieColors {

    // MARK: - Primary Brand Colors

    /// Primary amber accent color for CTAs and highlights
    static let primary = Color(hex: "f59e0b")

    /// Darker amber for hover/pressed states
    static let primaryDark = Color(hex: "d97706")

    /// Light amber for backgrounds and subtle accents
    static let primaryLight = Color(hex: "fbbf24")

    // MARK: - Background Colors

    /// Main app background (slate-900)
    static let background = Color(hex: "0f172a")

    /// Card and surface background (slate-800)
    static let surface = Color(hex: "1e293b")

    /// Elevated surface background (slate-700)
    static let surfaceElevated = Color(hex: "334155")

    // MARK: - Text Colors

    /// Primary text color (white)
    static let textPrimary = Color.white

    /// Secondary/muted text (slate-400)
    static let textSecondary = Color(hex: "94a3b8")

    /// Tertiary/disabled text (slate-500)
    static let textTertiary = Color(hex: "64748b")

    // MARK: - Semantic Colors

    /// Success/positive actions (emerald-500)
    static let success = Color(hex: "10b981")

    /// Warning/caution (amber-500)
    static let warning = Color(hex: "f59e0b")

    /// Error/destructive (red-500)
    static let error = Color(hex: "ef4444")

    /// Information (blue-500)
    static let info = Color(hex: "3b82f6")

    // MARK: - Rating Colors

    /// Star rating color (amber-400)
    static let rating = Color(hex: "fbbf24")

    /// AI score accent (amber-500)
    static let aiScore = Color(hex: "f59e0b")

    /// Social score accent (blue-500)
    static let socialScore = Color(hex: "3b82f6")

    /// User rating badge (emerald-500)
    static let userRating = Color(hex: "10b981")

    // MARK: - Gradient Definitions

    /// Primary gradient for buttons and accents
    static let primaryGradient = LinearGradient(
        gradient: Gradient(colors: [primary, primaryDark]),
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Background gradient for cards
    static let cardGradient = LinearGradient(
        gradient: Gradient(colors: [
            Color.black.opacity(0.8),
            Color.black.opacity(0.2),
            Color.clear
        ]),
        startPoint: .bottom,
        endPoint: .top
    )

    // MARK: - Opacity Variants

    /// Badge background opacity
    static let badgeOpacity: Double = 0.2

    /// Overlay opacity
    static let overlayOpacity: Double = 0.6

    /// Shadow opacity
    static let shadowOpacity: Double = 0.3
}

// MARK: - Color Extension for Hex Support

extension Color {
    /// Initialize Color from hex string.
    /// Supports formats: "RRGGBB" or "#RRGGBB"
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)

        let r, g, b, a: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (r, g, b, a) = ((int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17, 255)
        case 6: // RGB (24-bit)
            (r, g, b, a) = (int >> 16, int >> 8 & 0xFF, int & 0xFF, 255)
        case 8: // ARGB (32-bit)
            (r, g, b, a) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (r, g, b, a) = (0, 0, 0, 255)
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

// MARK: - Preview Provider

#if DEBUG
struct ColorsPreview: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Group {
                    Text("Brand Colors")
                        .font(.headline)
                    HStack(spacing: 8) {
                        ColorSwatch(color: NuvieColors.primary, name: "Primary")
                        ColorSwatch(color: NuvieColors.primaryDark, name: "Primary Dark")
                        ColorSwatch(color: NuvieColors.primaryLight, name: "Primary Light")
                    }
                }

                Group {
                    Text("Backgrounds")
                        .font(.headline)
                    HStack(spacing: 8) {
                        ColorSwatch(color: NuvieColors.background, name: "Background")
                        ColorSwatch(color: NuvieColors.surface, name: "Surface")
                        ColorSwatch(color: NuvieColors.surfaceElevated, name: "Elevated")
                    }
                }

                Group {
                    Text("Semantic")
                        .font(.headline)
                    HStack(spacing: 8) {
                        ColorSwatch(color: NuvieColors.success, name: "Success")
                        ColorSwatch(color: NuvieColors.warning, name: "Warning")
                        ColorSwatch(color: NuvieColors.error, name: "Error")
                        ColorSwatch(color: NuvieColors.info, name: "Info")
                    }
                }
            }
            .padding()
        }
        .background(NuvieColors.background)
    }
}

struct ColorSwatch: View {
    let color: Color
    let name: String

    var body: some View {
        VStack {
            RoundedRectangle(cornerRadius: 8)
                .fill(color)
                .frame(width: 60, height: 60)
            Text(name)
                .font(.caption2)
                .foregroundColor(.white)
        }
    }
}

#Preview {
    ColorsPreview()
}
#endif
