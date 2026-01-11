//
//  DemoConfiguration.swift
//  Nuvie
//
//  Created for Presentation Demo.
//

import Foundation

class DemoConfig {
    static let shared = DemoConfig()
    private init() {}

    static let isDemoMode = true
    static let forceSocialData = true // Injects friends even if API returns null
    
    /// Returns a random latency between 0.5 and 1.5 seconds if demo mode is active
    static func getRandomLatency() -> UInt64 {
        return UInt64(Double.random(in: 0.5...1.5) * 1_000_000_000)
    }
}
