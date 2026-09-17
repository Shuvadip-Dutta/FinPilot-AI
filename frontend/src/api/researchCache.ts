/**
 * In-Memory Client-Side Cache for FinPilot Research Data.
 *
 * Implements:
 * 1. 60-second freshness window (TTL = 60,000ms) for section/endpoint data.
 * 2. Request deduplication for identical concurrent in-flight requests.
 * 3. Structured cache keys: section:ticker:market[:extra].
 */

export interface CacheEntry<T = unknown> {
  data: T;
  timestamp: number;
}

export class ResearchDataCache {
  private cache = new Map<string, CacheEntry>();
  private inFlight = new Map<string, Promise<unknown>>();
  private readonly defaultTtlMs: number;
  private nowFn: () => number;

  constructor(defaultTtlMs = 60000, nowFn: () => number = () => Date.now()) {
    this.defaultTtlMs = defaultTtlMs;
    this.nowFn = nowFn;
  }

  /**
   * Generates a deterministic cache key for research section queries.
   */
  public createKey(section: string, ticker: string, market: string, extra?: string): string {
    const s = section.trim().toLowerCase();
    const t = ticker.trim().toUpperCase();
    const m = market.trim().toUpperCase();
    return extra ? `${s}:${t}:${m}:${extra}` : `${s}:${t}:${m}`;
  }

  /**
   * Retrieves an item from cache if present and fresh.
   */
  public get<T>(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;

    const age = this.nowFn() - entry.timestamp;
    if (age < this.defaultTtlMs) {
      return entry.data as T;
    }

    // Expired
    this.cache.delete(key);
    return undefined;
  }

  /**
   * Checks whether a valid, non-expired cache entry exists for the given key.
   */
  public has(key: string): boolean {
    return this.get(key) !== undefined;
  }

  /**
   * Stores an item in cache with the current timestamp.
   */
  public set<T>(key: string, data: T): void {
    this.cache.set(key, {
      data,
      timestamp: this.nowFn(),
    });
  }

  /**
   * Executes fetchFn or returns cached/in-flight result.
   * Ensures identical in-flight requests are deduplicated.
   */
  public async getOrFetch<T>(key: string, fetchFn: () => Promise<T>): Promise<T> {
    // 1. Check in-memory fresh cache
    const cached = this.get<T>(key);
    if (cached !== undefined) {
      return cached;
    }

    // 2. Check in-flight promise deduplication
    const existingInFlight = this.inFlight.get(key);
    if (existingInFlight) {
      return existingInFlight as Promise<T>;
    }

    // 3. Initiate request and register in-flight tracker
    const requestPromise = (async () => {
      try {
        const result = await fetchFn();
        this.set(key, result);
        return result;
      } finally {
        this.inFlight.delete(key);
      }
    })();

    this.inFlight.set(key, requestPromise);
    return requestPromise;
  }

  /**
   * Clears all cached entries and in-flight promises.
   */
  public clear(): void {
    this.cache.clear();
    this.inFlight.clear();
  }

  /**
   * Returns cache size for testing and monitoring.
   */
  public size(): number {
    return this.cache.size;
  }

  /**
   * Returns currently pending in-flight request count.
   */
  public inFlightCount(): number {
    return this.inFlight.size;
  }

  /**
   * Override time function (for deterministic testing of TTL expiration).
   */
  public setNowFn(fn: () => number): void {
    this.nowFn = fn;
  }
}

// Global singleton instance for Research API
export const researchDataCache = new ResearchDataCache(60000);
