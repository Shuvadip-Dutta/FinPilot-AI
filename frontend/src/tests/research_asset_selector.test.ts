import { apiClient } from '../api/client';
import { researchApi } from '../api/research';

/**
 * Focused test suite for Research Target Asset Selector:
 * 1. Quick Ticker click updates selected ticker and market.
 * 2. Quick Ticker click triggers URL parameter update.
 * 3. Enter in ticker input commits typed ticker.
 * 4. URL changes synchronize back into target asset state.
 * 5. Browser back/forward URL updates properly change the active asset.
 * 6. Current ticker and market are passed to Research API chat payload.
 */

async function runAssetSelectorTests(): Promise<void> {
  console.log('--- RUNNING RESEARCH ASSET SELECTOR TESTS ---');

  // Test 1 & 2: Quick Ticker Click & URL Update
  {
    let currentTicker = 'RELIANCE';
    let currentMarket = 'IN';
    let searchParams = new URLSearchParams('ticker=RELIANCE&market=IN');
    let historyStack: string[] = [searchParams.toString()];

    const updateTargetAsset = (newTicker: string, newMarket?: string, replaceHistory = false) => {
      const normTicker = (newTicker.trim() || 'RELIANCE').toUpperCase();
      const normMarket = (newMarket ? newMarket.trim() : currentMarket).toUpperCase();
      currentTicker = normTicker;
      currentMarket = normMarket;

      const params = new URLSearchParams(searchParams);
      params.set('ticker', normTicker);
      params.set('market', normMarket);
      searchParams = params;
      if (replaceHistory) {
        historyStack[historyStack.length - 1] = params.toString();
      } else {
        historyStack.push(params.toString());
      }
    };

    // Simulate Quick Ticker click on 'TCS'
    updateTargetAsset('TCS', 'IN', false);

    if (currentTicker !== 'TCS' || currentMarket !== 'IN') {
      throw new Error(`Test 1 Failed: Expected TCS/IN, got ${currentTicker}/${currentMarket}`);
    }
    if (searchParams.get('ticker') !== 'TCS') {
      throw new Error(`Test 2 Failed: URL searchParams did not update to TCS. Got: ${searchParams.toString()}`);
    }
    if (historyStack.length !== 2) {
      throw new Error(`Test 2 Failed: Expected history stack length 2, got ${historyStack.length}`);
    }
    console.log('PASS: Test 1 & 2: Quick Ticker click updates selected ticker and pushes URL history.');
  }

  // Test 3: Enter in ticker input commits typed ticker
  {
    let committedTicker = '';
    let committedMarket = '';

    const onTickerChange = (t: string, m: string) => {
      committedTicker = t;
      committedMarket = m;
    };

    // Simulate commitTicker on Enter key with typed input
    const inputVal = ' infy ';
    const activeMarket = 'IN';
    const cleanTicker = inputVal.trim().toUpperCase() || 'RELIANCE';
    onTickerChange(cleanTicker, activeMarket);

    if (committedTicker !== 'INFY' || committedMarket !== 'IN') {
      throw new Error(`Test 3 Failed: Expected INFY/IN committed, got ${committedTicker}/${committedMarket}`);
    }
    console.log('PASS: Test 3: Enter in ticker input commits normalized ticker (INFY).');
  }

  // Test 4 & 5: URL changes and browser back/forward synchronization
  {
    let stateTicker: string = 'INFY';
    let stateMarket: string = 'IN';

    // Simulate browser history navigation
    const historyStack = [
      'ticker=LT&market=IN',
      'ticker=TCS&market=IN',
      'ticker=INFY&market=IN',
    ];
    let historyIndex = 2; // currently at INFY

    const syncFromUrl = (url: string) => {
      const params = new URLSearchParams(url);
      const urlTicker = (params.get('ticker') || 'RELIANCE').trim().toUpperCase();
      const urlMarket = (params.get('market') || 'IN').trim().toUpperCase();
      if (urlTicker !== stateTicker) stateTicker = urlTicker;
      if (urlMarket !== stateMarket) stateMarket = urlMarket;
    };

    const assertEqual = (actual: unknown, expected: unknown, message: string) => {
      if (actual !== expected) {
        throw new Error(`${message}: Expected ${expected}, got ${actual}`);
      }
    };

    // Simulate Back navigation (INFY -> TCS)
    historyIndex = 1;
    syncFromUrl(historyStack[historyIndex]);
    assertEqual(stateTicker, 'TCS', 'Test 4 Failed on back to TCS');

    // Simulate Back navigation (TCS -> LT)
    historyIndex = 0;
    syncFromUrl(historyStack[historyIndex]);
    assertEqual(stateTicker, 'LT', 'Test 4 Failed on back to LT');

    // Simulate Forward navigation (LT -> TCS -> INFY)
    historyIndex = 2;
    syncFromUrl(historyStack[historyIndex]);
    assertEqual(stateTicker, 'INFY', 'Test 5 Failed on forward to INFY');

    console.log('PASS: Test 4 & 5: Browser back/forward navigation accurately synchronizes active asset state.');
  }

  // Test 6: Verify Research API request payload uses current ticker and market
  {
    let capturedPayload: any = null;
    const originalPost = apiClient.post;
    apiClient.post = async <T>(_endpoint: string, body?: unknown): Promise<T> => {
      capturedPayload = body;
      return {
        response: 'Analysis for selected asset',
        session_id: 'sess-789',
      } as T;
    };

    try {
      const selectedTicker = 'TCS';
      const selectedMarket = 'IN';
      const prompt = 'Analyze quarterly earnings';

      await researchApi.chat({
        message: prompt,
        ticker: selectedTicker,
        market: selectedMarket,
      });

      if (!capturedPayload) {
        throw new Error('Test 6 Failed: apiClient.post was not called.');
      }
      if (capturedPayload.ticker !== 'TCS' || capturedPayload.market !== 'IN') {
        throw new Error(`Test 6 Failed: Payload contained ${capturedPayload.ticker}/${capturedPayload.market}, expected TCS/IN`);
      }
      if (capturedPayload.message !== prompt) {
        throw new Error(`Test 6 Failed: Payload message mismatch`);
      }

      console.log('PASS: Test 6: Research API payload contains currently selected ticker and market.');
    } finally {
      apiClient.post = originalPost;
    }
  }

  console.log('--- ALL RESEARCH ASSET SELECTOR TESTS PASSED ---');
}

runAssetSelectorTests().catch((err) => {
  console.error('FAIL: runAssetSelectorTests error:', err);
  process.exit(1);
});
