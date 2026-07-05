# Global Header and Search Navigation Design

## Goal

Keep the main top action buttons visible while the user is on stock detail pages, and make every stock search return the app to the main page before showing results.

## Current Behavior

The logged-in top bar lives inside `HomeScreen`, so it disappears when `App.tsx` switches to `StockDetailScreen`. Search state and search submission also live inside `HomeScreen`; submitting a search only calls `loadStocks(query)` and does not affect the global `currentScreen`.

## Design

Move the logged-in header controls to the authenticated layout in `App.tsx`. This global header owns the search visibility and query text, and it is rendered above whichever logged-in screen is active: home, stock detail, settings, or profile.

`HomeScreen` becomes the consumer of submitted searches. It receives a `pendingSearchQuery` value from `App.tsx`. When `pendingSearchQuery` changes while the home screen is mounted, `HomeScreen` runs `loadStocks(pendingSearchQuery)`.

Search submit behavior is centralized in `App.tsx`: submit stores the query into `pendingSearchQuery`, switches `currentScreen` to `home`, and leaves the search panel visible so the user can see or adjust the active query. Clearing search clears the query, returns to home, and loads the default stock list.

## Component Boundaries

- `App.tsx`: global authenticated layout, top action buttons, search state, screen switching.
- `HomeScreen`: stock list loading from the submitted query passed by `App.tsx`.
- `StockDetailScreen`: no duplicated top action buttons; its local back and refresh controls remain inside the detail content.

## Testing

Add a lightweight static regression check for this navigation behavior:

- top-level app imports/renders the header action icons instead of relying on `HomeScreen`;
- `HomeScreen` accepts `pendingSearchQuery` and reacts by loading matching stocks;
- search submit in `App.tsx` switches to `home`;
- detail screen still receives `stockCode` and renders under the global layout.

Existing verification remains:

- Metro web bundle should return HTTP 200.
- Backend health check should remain healthy.
- `npx tsc --noEmit` is attempted, but the known TypeScript 6.0.3 stack overflow may still block it.

## Out Of Scope

No route library migration, no redesign of the detail content, no changes to backend search APIs, and no changes to authentication behavior.
