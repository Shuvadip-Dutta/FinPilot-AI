import { researchApi } from './research';
import { apiClient } from './client';

/**
 * Unit verification test for Research API timeout configuration.
 * Validates that researchApi.chat configures a 360,000 ms (6 minute) timeout.
 */
async function testResearchApiTimeout(): Promise<void> {
  let capturedEndpoint = '';
  let capturedOptions: { timeoutMs?: number } | undefined = undefined;

  // Intercept apiClient.post
  const originalPost = apiClient.post;
  apiClient.post = async <T>(endpoint: string, _body?: unknown, options?: { timeoutMs?: number }): Promise<T> => {
    capturedEndpoint = endpoint;
    capturedOptions = options;
    return {
      response: 'test synthesis',
      tools_used: [],
      session_id: 'test-session-123',
      thread_id: 'test-thread-456',
      route: 'financial',
    } as T;
  };

  try {
    const payload = { message: 'Analyze financials', ticker: 'RELIANCE', market: 'IN' };
    const response = await researchApi.chat(payload);

    if (capturedEndpoint !== 'ai/chat/') {
      throw new Error(`Expected endpoint 'ai/chat/', received '${capturedEndpoint}'`);
    }

    if (!capturedOptions || capturedOptions.timeoutMs !== 360000) {
      throw new Error(
        `Expected timeoutMs 360000, received ${capturedOptions?.timeoutMs}`
      );
    }

    if (!response || response.response !== 'test synthesis') {
      throw new Error(`Unexpected response returned from mock`);
    }

    console.log('PASS: researchApi.chat correctly configures 360000ms timeout budget.');
  } finally {
    apiClient.post = originalPost;
  }
}

testResearchApiTimeout().catch((err) => {
  console.error('FAIL: testResearchApiTimeout failed:', err);
  process.exit(1);
});
