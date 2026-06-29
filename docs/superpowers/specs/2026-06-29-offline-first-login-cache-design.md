# Offline-First Login and App Cache Design

## Goal

The app must open to the login page first. After login, all normal page navigation should render from data cached inside the app. The app should contact the server only when the user performs an explicit refresh or another explicit server action, such as login, search, watchlist updates, or backtest creation.

## Current Problems

- `App.tsx` initializes `currentScreen` as `home`, then conditionally renders login when unauthenticated. This makes the app state less explicit and causes logout/back paths to route through `home`.
- `localDb.ts` only persists data through `window.localStorage`. In native Expo builds there is no `window.localStorage`, so stock data is not actually persisted inside the app.
- `useStockData` loads stocks by calling the server on mount. `StockDetailScreen` also force-refreshes on entry. When the server is unavailable, pages cannot render complete cached data.
- Only stocks and stock detail have partial local fallback. Strategy detail, dividend, news, and institution holdings do not have app-cache persistence.

## Scope

In scope:

- Make login the explicit first unauthenticated screen.
- Make native and web cache reads/writes share the same storage API.
- Cache stock lists, stock details, strategy details, dividends, news, and institution holdings.
- Make normal page loads read cache first and avoid network fetches.
- Keep refresh buttons as the server-fetch path and update cache on success.
- Preserve cached UI when refresh fails.

Out of scope:

- Offline login.
- Offline watchlist mutation.
- Offline backtest creation.
- Background sync, conflict resolution, or queued writes.

## Architecture

The app will use three layers:

1. `storage.ts`
   Owns low-level persistence. It already supports native AsyncStorage and web localStorage for auth/config. The data cache should use the same platform split or expose helpers reusable by `localDb.ts`.

2. `localDb.ts`
   Owns typed cached app data. It will support native AsyncStorage and web localStorage. It will provide save/get helpers for:
   - stock list
   - stock search result by normalized query
   - stock detail by code
   - strategy detail by stock code and strategy id
   - dividend records by stock code
   - news by stock code
   - institution holdings by stock code
   - last update timestamps

3. `api.ts`
   Owns server calls and cache policy. Normal read methods should return cached data without fetching. Refresh methods or calls with `forceRefresh: true` should fetch from the server, write cache, and return fresh data. If a refresh fails, the method should return cached data when available and then surface enough information for the UI to show an error without clearing the page.

## Navigation Behavior

- App startup waits for `initStorage`.
- While storage initializes, show a minimal loading state.
- If no auth token exists, the visible screen is `login`.
- Login success sets authenticated state and navigates to `home`.
- Logout clears auth and navigates to `login`.
- Login-side settings, terms, and privacy remain available before login.

## Data Flow

Home load:

- `useStockData` calls a cache-only stock load on mount.
- If cached stocks exist, render them and select the first cached stock or previously selected stock.
- If no cached stocks exist, render the page with an empty watchlist and refresh control.
- The home refresh button calls server refresh, writes cache, and updates UI.

Detail load:

- `StockDetailScreen` loads stock detail and secondary sections from cache on mount.
- Refresh fetches stock detail, dividend, news, institution holdings, and writes cache.
- Strategy expansion reads cached strategy detail first. If no cached strategy detail exists, it may show a collapsed/no-detail state until the user refreshes or expands as an explicit server action. To match current user expectations, expanding a strategy is treated as an explicit server action and may fetch if cache is missing.

Search:

- Search submit is an explicit server action. It can fetch server results and cache them.
- If search fails, the app should keep the existing cached list visible and show an error.

Write actions:

- Login, watchlist add/remove, and backtest creation require the server.
- When these fail, cached read-only page data remains visible.

## Error Handling

- Cache misses should not be treated as fatal load failures.
- Network failures during refresh show an error panel or inline error while keeping old cached data.
- If there is no cached data and refresh fails, the page shows an empty state plus retry/refresh.
- Console warnings are acceptable for diagnostics, but UI state must remain usable.

## Testing

Use test-first changes for cache policy and persistence:

- `localDb` stores and reads app data through an injected or mocked storage surface.
- `api` default read paths do not call `fetch`.
- `api` refresh paths call `fetch`, save successful results, and return cached data on fetch failure when available.
- Navigation state routes unauthenticated startup and logout to login.

If the frontend lacks a test runner, add a small TypeScript-compatible test setup that can run in Node without requiring an Expo device.
