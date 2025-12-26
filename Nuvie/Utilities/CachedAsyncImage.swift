//
//  CachedAsyncImage.swift
//  Nuvie
//
//  IMPROVEMENTS:
//  - Provides image caching using URLCache
//  - Supports placeholder and error views
//  - Includes fade-in animation
//  - Memory and disk caching
//  - Configurable cache policy
//

import SwiftUI

// MARK: - Image Cache Manager

/// Manages in-memory and disk caching for images.
final class ImageCacheManager {
    static let shared = ImageCacheManager()

    private let cache: URLCache
    private let memoryCache = NSCache<NSString, UIImage>()

    private init() {
        // Configure URLCache: 50 MB memory, 200 MB disk
        let memoryCapacity = 50 * 1024 * 1024  // 50 MB
        let diskCapacity = 200 * 1024 * 1024   // 200 MB

        cache = URLCache(
            memoryCapacity: memoryCapacity,
            diskCapacity: diskCapacity,
            diskPath: "nuvie_image_cache"
        )

        // Configure memory cache limits
        memoryCache.countLimit = 100
        memoryCache.totalCostLimit = memoryCapacity
    }

    func cachedResponse(for request: URLRequest) -> CachedURLResponse? {
        return cache.cachedResponse(for: request)
    }

    func storeCachedResponse(_ response: CachedURLResponse, for request: URLRequest) {
        cache.storeCachedResponse(response, for: request)
    }

    func image(for url: URL) -> UIImage? {
        return memoryCache.object(forKey: url.absoluteString as NSString)
    }

    func store(_ image: UIImage, for url: URL) {
        let cost = Int(image.size.width * image.size.height * 4)
        memoryCache.setObject(image, forKey: url.absoluteString as NSString, cost: cost)
    }

    func clearCache() {
        cache.removeAllCachedResponses()
        memoryCache.removeAllObjects()
    }
}

// MARK: - Cached Image Loader

/// Observable loader that fetches and caches images.
@MainActor
final class CachedImageLoader: ObservableObject {
    @Published var image: UIImage?
    @Published var isLoading = false
    @Published var error: Error?

    private let url: URL?
    private let cacheManager = ImageCacheManager.shared
    private var task: URLSessionDataTask?

    init(url: URL?) {
        self.url = url
    }

    func load() async {
        guard let url = url else {
            return
        }

        // Check memory cache first
        if let cached = cacheManager.image(for: url) {
            self.image = cached
            return
        }

        isLoading = true
        error = nil

        let request = URLRequest(url: url, cachePolicy: .returnCacheDataElseLoad)

        // Check disk cache
        if let cachedResponse = cacheManager.cachedResponse(for: request),
           let cached = UIImage(data: cachedResponse.data) {
            cacheManager.store(cached, for: url)
            self.image = cached
            self.isLoading = false
            return
        }

        // Fetch from network
        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200,
                  let loadedImage = UIImage(data: data) else {
                throw URLError(.badServerResponse)
            }

            // Cache the response
            let cachedResponse = CachedURLResponse(response: response, data: data)
            cacheManager.storeCachedResponse(cachedResponse, for: request)
            cacheManager.store(loadedImage, for: url)

            self.image = loadedImage
            self.isLoading = false
        } catch {
            self.error = error
            self.isLoading = false
        }
    }

    func cancel() {
        task?.cancel()
    }
}

// MARK: - Cached Async Image View

/// A SwiftUI view that loads and caches images with customizable placeholders.
struct CachedAsyncImage<Placeholder: View, ErrorView: View>: View {
    @StateObject private var loader: CachedImageLoader

    let placeholder: () -> Placeholder
    let errorView: (Error) -> ErrorView
    let contentMode: ContentMode

    init(
        url: URL?,
        contentMode: ContentMode = .fill,
        @ViewBuilder placeholder: @escaping () -> Placeholder,
        @ViewBuilder errorView: @escaping (Error) -> ErrorView
    ) {
        _loader = StateObject(wrappedValue: CachedImageLoader(url: url))
        self.placeholder = placeholder
        self.errorView = errorView
        self.contentMode = contentMode
    }

    var body: some View {
        ZStack {
            if let image = loader.image {
                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: contentMode)
                    .transition(.opacity.animation(.easeIn(duration: 0.25)))
            } else if loader.isLoading {
                placeholder()
            } else if let error = loader.error {
                errorView(error)
            } else {
                placeholder()
            }
        }
        .task {
            await loader.load()
        }
        .onDisappear {
            loader.cancel()
        }
    }
}

// MARK: - Convenience Initializer

extension CachedAsyncImage where Placeholder == ProgressView<EmptyView, EmptyView>, ErrorView == Image {
    /// Convenience initializer with default placeholder and error views.
    init(url: URL?, contentMode: ContentMode = .fill) {
        self.init(
            url: url,
            contentMode: contentMode,
            placeholder: { ProgressView() },
            errorView: { _ in Image(systemName: "photo") }
        )
    }
}

// MARK: - Movie Poster Image

/// Specialized cached image for movie posters with Nuvie styling.
struct MoviePosterImage: View {
    let url: URL?
    let cornerRadius: CGFloat

    init(url: URL?, cornerRadius: CGFloat = 8) {
        self.url = url
        self.cornerRadius = cornerRadius
    }

    init(urlString: String?, cornerRadius: CGFloat = 8) {
        if let urlString = urlString {
            self.url = URL(string: urlString)
        } else {
            self.url = nil
        }
        self.cornerRadius = cornerRadius
    }

    var body: some View {
        CachedAsyncImage(
            url: url,
            contentMode: .fill,
            placeholder: {
                ZStack {
                    NuvieColors.surface
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: NuvieColors.textSecondary))
                }
            },
            errorView: { _ in
                ZStack {
                    NuvieColors.surface
                    Image(systemName: "film")
                        .font(.system(size: 32))
                        .foregroundColor(NuvieColors.textSecondary)
                }
            }
        )
        .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
    }
}

// MARK: - Preview

#if DEBUG
struct CachedAsyncImage_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 20) {
            MoviePosterImage(
                urlString: "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
            )
            .frame(width: 150, height: 225)

            MoviePosterImage(urlString: nil)
                .frame(width: 150, height: 225)
        }
        .padding()
        .background(NuvieColors.background)
    }
}
#endif
