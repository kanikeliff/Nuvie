//
//  FlexibleDecoding.swift
//  Nuvie
//
//  Created for Backend Compatibility.
//

import Foundation

@propertyWrapper
struct FlexibleInt: Codable {
    var wrappedValue: Int?
    
    init(wrappedValue: Int?) {
        self.wrappedValue = wrappedValue
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let intValue = try? container.decode(Int.self) {
            wrappedValue = intValue
        } else if let stringValue = try? container.decode(String.self), let intValue = Int(stringValue) {
            wrappedValue = intValue
        } else if let doubleValue = try? container.decode(Double.self) {
            wrappedValue = Int(doubleValue)
        } else {
            wrappedValue = nil
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(wrappedValue)
    }
}

@propertyWrapper
struct FlexibleDouble: Codable {
    var wrappedValue: Double?
    
    init(wrappedValue: Double?) {
        self.wrappedValue = wrappedValue
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let doubleValue = try? container.decode(Double.self) {
            wrappedValue = doubleValue
        } else if let stringValue = try? container.decode(String.self), let doubleValue = Double(stringValue) {
            wrappedValue = doubleValue
        } else if let intValue = try? container.decode(Int.self) {
            wrappedValue = Double(intValue)
        } else {
            wrappedValue = nil
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(wrappedValue)
    }
}

extension KeyedDecodingContainer {
    /// Safely decodes a value, returning nil if decoding fails instead of throwing
    func decodeSafe<T: Decodable>(_ type: T.Type, forKey key: Key) -> T? {
        do {
            return try decodeIfPresent(T.self, forKey: key)
        } catch {
            print("⚠️ Safe decoding failed for key: \(key.stringValue) error: \(error)")
            return nil
        }
    }
}
