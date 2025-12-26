//
//  NuvieApp.swift
//  Nuvie
//
//  Created by Can on 14.12.2025.
//
//  SECURITY FIX: Removed hardcoded API key (was exposed in source control)
//  API keys should be loaded from secure configuration, not committed to code
//

import SwiftUI

@main
struct NuvieApp: App {
    @StateObject private var feedViewModel = FeedViewModel()

    init() {
        // SECURITY: API keys are now loaded securely
        // In production, keys should come from:
        // 1. Backend after authentication
        // 2. Secure configuration files (not committed to git)
        // 3. Environment variables during build

        #if DEBUG
        // Development only: Load from Config-Debug.plist (add to .gitignore)
        if let path = Bundle.main.path(forResource: "Config-Debug", ofType: "plist"),
           let config = NSDictionary(contentsOfFile: path),
           let apiKey = config["TMDB_API_KEY"] as? String {
            // Store in Keychain for secure storage
            SecureConfig.shared.setAPIKey(apiKey)
        }
        #endif
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(feedViewModel)
        }
    }
}

// MARK: - Secure Configuration Helper

/// Manages secure storage of configuration values using Keychain
final class SecureConfig {
    static let shared = SecureConfig()
    private init() {}

    private let service = "com.nuvie.config"
    private let apiKeyAccount = "tmdb_api_key"

    func setAPIKey(_ key: String) {
        let data = Data(key.utf8)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: apiKeyAccount
        ]

        // Delete existing
        SecItemDelete(query as CFDictionary)

        // Add new
        let attributes = query.merging([
            kSecValueData as String: data
        ]) { $1 }

        SecItemAdd(attributes as CFDictionary, nil)
    }

    func getAPIKey() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: apiKeyAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let key = String(data: data, encoding: .utf8) else {
            return nil
        }

        return key
    }
}
