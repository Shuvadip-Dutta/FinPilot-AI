import { apiClient } from '../api/client';
import { researchApi } from '../api/research';
import { ResearchDataCache } from '../api/researchCache';

/**
 * Focused tests for Research Client-Side Cache (Issue #2B):
 * 14. First request for a cache key calls the API.
 * 15. Repeated request within 60s uses cache (no second API call).
 * 16. Request after 60s fetches again.
 * 17. Different ticker creates a separate cache entry.
 * 18. Different market creates a separate cache entry.
 * 19. Different section creates a separate cache entry.
 * 20. Simultaneous identical requests are deduplicated (single in-flight API call).
 */
function assertEqual(actual: unknown, expected: unknown, message: string): void {
  if (actual !== expected) {
    throw new Error(`${message}: Expected ${expected}, got ${actual}`);
  }
}

async function runCacheTests(): Promise<void> {
  console.log('--- RUNNING RESEARCH CACHE TESTS ---');

  // Test 14, 15, 16: Basic caching & 60s TTL
  {
    let currentTime = 1000000;
    const testCache = new ResearchDataCache(60000, () => currentTime);
    let fetchCount = 0;

    const mockFetch = async () => {
      fetchCount++;
      return { status: 'ok', count: fetchCount };
    };

    const key = testCache.createKey('financials', 'RELIANCE', 'IN');

    // 14. First request calls fetch
    const res1 = await testCache.getOrFetch(key, mockFetch);
    assertEqual(fetchCount, 1, 'Test 14 fetchCount mismatch');
    assertEqual(res1.count, 1, 'Test 14 res1.count mismatch');

    // 15. Repeated request within 60s (at +30s) uses cache without calling fetch
    currentTime += 30000;
    const res2 = await testCache.getOrFetch(key, mockFetch);
    assertEqual(fetchCount, 1, 'Test 15 cache hit fetchCount mismatch');
    assertEqual(res2.count, 1, 'Test 15 cache hit res2.count mismatch');

    // 16. Request after 60s (at +61s from origin) expires and fetches again
    currentTime += 31000; // Total 61s elapsed
    const res3 = await testCache.getOrFetch(key, mockFetch);
    assertEqual(fetchCount, 2, 'Test 16 expiration fetchCount mismatch');
    assertEqual(res3.count, 2, 'Test 16 expiration res3.count mismatch');

    console.log('PASS: Test 14, 15, 16: First call fetches, subsequent call within 60s caches, call after 60s refreshes.');
  }

  // Test 17, 18, 19: Cache key isolation (ticker, market, section)
  {
    const testCache = new ResearchDataCache(60000);
    const calls: string[] = [];

    const makeFetch = (label: string) => async () => {
      calls.push(label);
      return { label };
    };

    // 17. Different ticker creates separate cache entry
    const keyRel = testCache.createKey('financials', 'RELIANCE', 'IN');
    const keyTcs = testCache.createKey('financials', 'TCS', 'IN');
    await testCache.getOrFetch(keyRel, makeFetch('financials:RELIANCE:IN'));
    await testCache.getOrFetch(keyTcs, makeFetch('financials:TCS:IN'));
    assertEqual(calls.length, 2, 'Test 17 Failed: Tickers were not isolated in cache.');
    assertEqual(testCache.has(keyRel) && testCache.has(keyTcs), true, 'Test 17 keys missing');

    // 18. Different market creates separate cache entry
    const keyAaplUs = testCache.createKey('company', 'AAPL', 'US');
    const keyAaplIn = testCache.createKey('company', 'AAPL', 'IN');
    await testCache.getOrFetch(keyAaplUs, makeFetch('company:AAPL:US'));
    await testCache.getOrFetch(keyAaplIn, makeFetch('company:AAPL:IN'));
    assertEqual(calls.length, 4, 'Test 18 Failed: Markets were not isolated in cache.');

    // 19. Different section creates separate cache entry
    const keyNews = testCache.createKey('news', 'RELIANCE', 'IN');
    const keyMetrics = testCache.createKey('metrics', 'RELIANCE', 'IN');
    await testCache.getOrFetch(keyNews, makeFetch('news:RELIANCE:IN'));
    await testCache.getOrFetch(keyMetrics, makeFetch('metrics:RELIANCE:IN'));
    assertEqual(calls.length, 6, 'Test 19 Failed: Sections were not isolated in cache.');

    console.log('PASS: Test 17, 18, 19: Independent cache keys for ticker, market, and section properly isolated.');
  }

  // Test 20: Request deduplication for simultaneous identical requests
  {
    const testCache = new ResearchDataCache(60000);
    let apiCallCount = 0;

    const slowFetch = async () => {
      apiCallCount++;
      await new Promise((resolve) => setTimeout(resolve, 50));
      return { price: 2950.5 };
    };

    const key = testCache.createKey('company', 'RELIANCE', 'IN');

    // Launch 5 simultaneous identical requests
    const [r1, r2, r3, r4, r5] = await Promise.all([
      testCache.getOrFetch(key, slowFetch),
      testCache.getOrFetch(key, slowFetch),
      testCache.getOrFetch(key, slowFetch),
      testCache.getOrFetch(key, slowFetch),
      testCache.getOrFetch(key, slowFetch),
    ]);

    assertEqual(apiCallCount, 1, 'Test 20 Failed: Expected 1 deduplicated API call');
    assertEqual(r1.price, 2950.5, 'Test 20 Failed: r1.price mismatch');
    assertEqual(r5.price, 2950.5, 'Test 20 Failed: r5.price mismatch');

    console.log('PASS: Test 20: Concurrent identical requests deduplicated into a single provider call.');
  }

  // End-to-end integration test through researchApi
  {
    let getCallCount = 0;
    let requestedParams: Record<string, unknown> | undefined;

    const originalGet = apiClient.get;
    apiClient.get = async <T>(_endpoint: string, config?: { params?: Record<string, unknown> }): Promise<T> => {
      getCallCount++;
      requestedParams = config?.params;
      return {
        ticker: String(config?.params?.ticker || 'INFY'),
        market: String(config?.params?.market || 'IN'),
        name: 'Infosys Limited',
      } as T;
    };

    try {
      // First request -> network call
      const comp1 = await researchApi.getCompany('INFY', 'IN');
      assertEqual(getCallCount, 1, 'E2E Cache Failed on first getCompany');
      assertEqual(comp1.ticker, 'INFY', 'E2E Cache Failed ticker mismatch');

      // Second request within 60s -> cached, no network call
      await researchApi.getCompany('INFY', 'IN');
      assertEqual(getCallCount, 1, 'E2E Cache Failed: Expected cached response, API was called again.');

      // Different section (financials) -> new network call
      await researchApi.getFinancials('INFY', 'IN');
      assertEqual(getCallCount, 2, 'E2E Cache Failed: Expected new API call for different section');

      // Different ticker (TCS) -> new network call
      await researchApi.getCompany('TCS', 'IN');
      assertEqual(getCallCount, 3, 'E2E Cache Failed: Expected new API call for different ticker');

      console.log('PASS: E2E: researchApi section methods properly apply 60s cache and deduplication.');
    } finally {
      apiClient.get = originalGet;
    }
  }

  console.log('--- ALL RESEARCH CACHE TESTS PASSED ---');
}

runCacheTests().catch((err) => {
  console.error('FAIL: runCacheTests failed:', err);
  process.exit(1);
});
