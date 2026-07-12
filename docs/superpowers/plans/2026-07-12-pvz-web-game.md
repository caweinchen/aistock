# AI-10 Web Tower Defense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independently runnable one-level React web tower-defense game in `pvz-game/` without changing the existing stock application.

**Architecture:** A pure TypeScript reducer owns deterministic game state and fixed-step simulation; React dispatches actions and renders that state. Components, visual assets, and responsive styles remain replaceable without changing combat rules.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, Playwright, Lucide React.

## Global Constraints

- Create only the root-level `pvz-game/` application and documentation tracking updates; do not import or modify `frontend/` runtime code.
- Board size is exactly 5 rows by 9 columns; initial sun is exactly 150.
- Plant roster is sunflower (cost 50), pea shooter (cost 100), and wall nut (cost 75); enemy roster is walker and cone walker.
- Provide shovel, pause, sound toggle, win/loss, and restart controls in the first release.
- Use original generated bitmap art only; do not use game trademarks or extracted copyrighted assets.
- Use fixed simulation steps, pause on page blur, and never catch up elapsed background time.
- Every production behavior follows a witnessed red-green TDD cycle.
- Desktop and narrow mobile layouts must keep the complete board operable without control overlap.

---

## File Map

- `pvz-game/package.json`, `vite.config.ts`, `tsconfig*.json`, `index.html`: isolated toolchain and entry point.
- `pvz-game/src/game/types.ts`: public state, entity, configuration, and action types.
- `pvz-game/src/game/config.ts`: all balance values and default level configuration.
- `pvz-game/src/game/reducer.ts`: initialization, actions, and deterministic simulation.
- `pvz-game/src/game/reducer.test.ts`: rule-level tests with explicit fixtures.
- `pvz-game/src/hooks/useGameLoop.ts`: fixed-step browser loop and blur pause.
- `pvz-game/src/App.tsx`: game orchestration and result overlay.
- `pvz-game/src/components/{Toolbar,SeedBank,Board,Entity}.tsx`: focused controls and rendering.
- `pvz-game/src/styles/game.css`: stable board geometry, responsive layout, state animation, reduced motion.
- `pvz-game/src/assets/*.webp`: original background and entity bitmap assets.
- `pvz-game/e2e/game.spec.ts`, `playwright.config.ts`: desktop/mobile user-flow tests.
- `docs/superpowers/specs/2026-07-12-pvz-web-game-design.md`: implementation tracking checkboxes.

### Task 1: Isolated App and Placement Economy

**Files:**
- Create: `pvz-game/package.json`
- Create: `pvz-game/index.html`
- Create: `pvz-game/tsconfig.json`
- Create: `pvz-game/vite.config.ts`
- Create: `pvz-game/src/game/types.ts`
- Create: `pvz-game/src/game/config.ts`
- Create: `pvz-game/src/game/reducer.ts`
- Test: `pvz-game/src/game/reducer.test.ts`

**Interfaces:**
- Produces: `createInitialState(config?: GameConfig): GameState`
- Produces: `gameReducer(state: GameState, action: GameAction): GameState`
- Produces actions `select`, `place`, `shovel`, `collectSun`, `togglePause`, `restart`, and `tick`.

- [ ] **Step 1: Scaffold the test runner and write failing initialization/placement tests**

```ts
import { describe, expect, it } from 'vitest';
import { createInitialState, gameReducer } from './reducer';

describe('placement economy', () => {
  it('starts a 5x9 playing level with 150 sun', () => {
    const state = createInitialState();
    expect(state.phase).toBe('playing');
    expect(state.board).toEqual({ rows: 5, columns: 9 });
    expect(state.sun).toBe(150);
  });

  it('places one sunflower and deducts exactly 50 sun', () => {
    const selected = gameReducer(createInitialState(), { type: 'select', tool: 'sunflower' });
    const placed = gameReducer(selected, { type: 'place', row: 2, column: 3 });
    expect(placed.sun).toBe(100);
    expect(placed.plants).toMatchObject([{ kind: 'sunflower', row: 2, column: 3 }]);
  });

  it('does not charge for occupied, cooling, or unaffordable placement', () => {
    const base = { ...createInitialState(), sun: 49 };
    const result = gameReducer(gameReducer(base, { type: 'select', tool: 'sunflower' }), { type: 'place', row: 0, column: 0 });
    expect(result.sun).toBe(49);
    expect(result.plants).toHaveLength(0);
    expect(result.feedback).toBe('not-enough-sun');
  });
});
```

- [ ] **Step 2: Run the focused test and witness the expected failure**

Run: `cd pvz-game && npm install && npm test -- src/game/reducer.test.ts`

Expected: FAIL because `./reducer` does not exist.

- [ ] **Step 3: Implement the minimal typed state and placement reducer**

```ts
export type PlantKind = 'sunflower' | 'peaShooter' | 'wallNut';
export type Tool = PlantKind | 'shovel' | null;
export type GamePhase = 'playing' | 'paused' | 'won' | 'lost';
export type GameAction =
  | { type: 'select'; tool: Tool }
  | { type: 'place'; row: number; column: number }
  | { type: 'shovel'; row: number; column: number }
  | { type: 'collectSun'; id: string }
  | { type: 'togglePause' }
  | { type: 'restart' }
  | { type: 'tick'; deltaMs: number };
```

Implement `createInitialState` with `phase: 'playing'`, `{ rows: 5, columns: 9 }`, `sun: 150`, empty entity arrays, and wave counters. In `gameReducer`, reject out-of-range, occupied, cooling, and unaffordable placement before deducting `PLANTS[kind].cost`; `shovel` removes only the addressed plant.

- [ ] **Step 4: Run tests and type checking**

Run: `cd pvz-game && npm test -- src/game/reducer.test.ts && npm run typecheck`

Expected: all placement tests PASS and TypeScript exits 0.

- [ ] **Step 5: Commit the independently testable economy slice**

```bash
git add pvz-game
git commit -m "feat: add AI-10 game state and placement economy"
```

### Task 2: Fixed-Step Combat, Production, Waves, and Outcomes

**Files:**
- Modify: `pvz-game/src/game/config.ts`
- Modify: `pvz-game/src/game/types.ts`
- Modify: `pvz-game/src/game/reducer.ts`
- Test: `pvz-game/src/game/reducer.test.ts`

**Interfaces:**
- Consumes: `gameReducer`, `createInitialState`, `GameState`, and `GameAction` from Task 1.
- Produces: deterministic `tick` behavior with `MAX_TICK_MS = 100`, projectile/sun-drop IDs, and wave state.

- [ ] **Step 1: Add failing tests for production, combat, pause, and terminal states**

```ts
it('caps long ticks and produces collectible sunflower sun', () => {
  const planted = placeFixture('sunflower', 1, 1);
  const advanced = advance(planted, 25_000);
  expect(advanced.sunDrops).toHaveLength(1);
  expect(advanced.elapsedMs).toBeLessThanOrEqual(25_000);
  const collected = gameReducer(advanced, { type: 'collectSun', id: advanced.sunDrops[0].id });
  expect(collected.sun).toBe(planted.sun + 25);
});

it('pea projectiles damage only the first zombie in their row', () => {
  const state = combatFixture({ shooterRow: 2, zombieXs: [5.2, 7.4] });
  const result = advance(state, 5_000);
  expect(result.zombies[0].health).toBeLessThan(result.zombies[0].maxHealth);
  expect(result.zombies[1].health).toBe(result.zombies[1].maxHealth);
});

it('does not advance while paused and detects loss and final-wave victory', () => {
  const paused = { ...createInitialState(), phase: 'paused' as const };
  expect(gameReducer(paused, { type: 'tick', deltaMs: 100 })).toEqual(paused);
  expect(advance(lossFixture(), 100).phase).toBe('lost');
  expect(advance(victoryFixture(), 100).phase).toBe('won');
});
```

- [ ] **Step 2: Run the focused test and witness missing simulation failures**

Run: `cd pvz-game && npm test -- src/game/reducer.test.ts`

Expected: FAIL on absent production, combat, and outcome transitions.

- [ ] **Step 3: Implement deterministic simulation in ordered phases**

Implement `tick` as repeated `Math.min(remaining, MAX_TICK_MS)` steps in this exact order: spawn due enemies, update plant cooldowns/production/fire, move projectiles and resolve first-row hits, move or bite enemies, remove dead entities, then evaluate loss before victory. Use monotonic `nextEntityId` from state; never use random IDs. Clamp incoming `deltaMs` to `0..1000` so background recovery cannot fast-forward.

- [ ] **Step 4: Run all rule tests and type checking**

Run: `cd pvz-game && npm test && npm run typecheck`

Expected: all Vitest tests PASS with no warnings; TypeScript exits 0.

- [ ] **Step 5: Commit the complete deterministic rule engine**

```bash
git add pvz-game/src/game
git commit -m "feat: add AI-10 combat and wave simulation"
```

### Task 3: Accessible React Game Surface

**Files:**
- Create: `pvz-game/src/main.tsx`
- Create: `pvz-game/src/App.tsx`
- Create: `pvz-game/src/hooks/useGameLoop.ts`
- Create: `pvz-game/src/components/Toolbar.tsx`
- Create: `pvz-game/src/components/SeedBank.tsx`
- Create: `pvz-game/src/components/Board.tsx`
- Create: `pvz-game/src/components/Entity.tsx`
- Create: `pvz-game/src/App.test.tsx`
- Modify: `pvz-game/package.json`

**Interfaces:**
- Consumes: `gameReducer(state, action)` and domain types from Tasks 1-2.
- Produces: `useGameLoop(dispatch, phase)`, accessible controls, `data-testid="cell-r-c"`, and status overlays.

- [ ] **Step 1: Write failing interaction tests**

```tsx
it('selects and places a plant with visible resource feedback', async () => {
  render(<App />);
  await user.click(screen.getByRole('button', { name: /向日葵/ }));
  await user.click(screen.getByTestId('cell-0-0'));
  expect(screen.getByTestId('cell-0-0')).toHaveAccessibleName(/向日葵/);
  expect(screen.getByText('100')).toBeVisible();
});

it('pauses and restarts from the result dialog', async () => {
  render(<App initialState={victoryFixture()} />);
  expect(screen.getByRole('dialog', { name: '庭院守住了' })).toBeVisible();
  await user.click(screen.getByRole('button', { name: '再来一局' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run component tests and witness missing UI failures**

Run: `cd pvz-game && npm test -- src/App.test.tsx`

Expected: FAIL because `App` and components do not exist.

- [ ] **Step 3: Implement the minimal complete React interaction surface**

Use `useReducer(gameReducer, initialState ?? createInitialState())`. `useGameLoop` schedules `requestAnimationFrame`, dispatches at most 1000 ms delta, and dispatches `togglePause` on `visibilitychange` only when playing. Render icon buttons with `aria-label` for pause, sound, and shovel; render seed buttons with cost and cooldown; render 45 stable cell buttons; place entities as absolutely positioned children with `pointer-events: none`. Result overlay uses `role="dialog"` and restart dispatch.

- [ ] **Step 4: Run component, rule, and type tests**

Run: `cd pvz-game && npm test && npm run typecheck`

Expected: all tests PASS and TypeScript exits 0.

- [ ] **Step 5: Commit the accessible UI slice**

```bash
git add pvz-game/src pvz-game/package.json pvz-game/package-lock.json
git commit -m "feat: add AI-10 accessible game interface"
```

### Task 4: Original Bitmap Art and Responsive Presentation

**Files:**
- Create: `pvz-game/src/assets/garden.webp`
- Create: `pvz-game/src/assets/sunflower.webp`
- Create: `pvz-game/src/assets/pea-shooter.webp`
- Create: `pvz-game/src/assets/wall-nut.webp`
- Create: `pvz-game/src/assets/walker.webp`
- Create: `pvz-game/src/assets/cone-walker.webp`
- Create: `pvz-game/src/assets/sun.webp`
- Create: `pvz-game/src/assets.test.ts`
- Create: `pvz-game/src/styles/game.css`
- Modify: `pvz-game/src/main.tsx`
- Modify: `pvz-game/src/components/Entity.tsx`

**Interfaces:**
- Consumes: entity `kind`, health ratio, and board coordinates from Task 3.
- Produces: nonblank original bitmap assets and layout breakpoints at 760 px.

- [ ] **Step 1: Add an asset manifest assertion and run it red**

```ts
import { readFile } from 'node:fs/promises';
import { expect, it } from 'vitest';

it.each(['garden', 'sunflower', 'pea-shooter', 'wall-nut', 'walker', 'cone-walker', 'sun'])(
  'ships non-empty %s art', async (name) => {
    const bytes = await readFile(new URL(`./assets/${name}.webp`, import.meta.url));
    expect(bytes.byteLength).toBeGreaterThan(1024);
  },
);
```

Run: `cd pvz-game && npm test -- src/assets.test.ts`

Expected: FAIL because the bitmap files do not exist.

- [ ] **Step 2: Generate and inspect original bitmap assets**

Use the `imagegen` skill with one consistent prompt family: bright original backyard tower-defense art, clean transparent silhouettes, no text, no logos, and no resemblance to copyrighted game characters. Save WebP outputs to the exact asset paths above and visually inspect every file before wiring it into components.

- [ ] **Step 3: Implement stable responsive styling**

Set `.board { aspect-ratio: 9 / 5; display: grid; grid-template-columns: repeat(9, 1fr); grid-template-rows: repeat(5, 1fr); }`. Desktop uses `grid-template-columns: minmax(112px, 148px) minmax(0, 1fr)` for seed bank and board. At `max-width: 760px`, switch to one column, horizontal seed cards, and an overflow-safe board width of `min(100%, 920px)`. Add visible focus, disabled, selected, hit, bite, cooldown, and low-health states. Under `prefers-reduced-motion: reduce`, remove nonessential transforms and transitions.

- [ ] **Step 4: Verify assets, tests, and production build**

Run: `cd pvz-game && npm test && npm run typecheck && npm run build`

Expected: asset assertions and all tests PASS; Vite build exits 0 and emits `dist/index.html`.

- [ ] **Step 5: Commit visual assets and responsive styles**

```bash
git add pvz-game/src/assets pvz-game/src/styles pvz-game/src/main.tsx pvz-game/src/components/Entity.tsx
git commit -m "feat: add AI-10 original game art and responsive styling"
```

### Task 5: End-to-End Flows and Final Tracking

**Files:**
- Create: `pvz-game/playwright.config.ts`
- Create: `pvz-game/e2e/game.spec.ts`
- Modify: `pvz-game/package.json`
- Modify: `docs/superpowers/specs/2026-07-12-pvz-web-game-design.md`

**Interfaces:**
- Consumes: accessible names and `data-testid` cell contract from Task 3.
- Produces: `npm run test:e2e` desktop/mobile verification and completed spec tracking.

- [ ] **Step 1: Write end-to-end tests before adding any e2e-specific fixes**

```ts
test('place, collect, shovel, pause, and restart remain operable', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /向日葵/ }).click();
  await page.getByTestId('cell-0-0').click();
  await expect(page.getByTestId('cell-0-0')).toHaveAccessibleName(/向日葵/);
  await page.getByRole('button', { name: '暂停' }).click();
  await expect(page.getByText('已暂停')).toBeVisible();
  await page.getByRole('button', { name: '继续' }).click();
  await page.getByRole('button', { name: '铲子' }).click();
  await page.getByTestId('cell-0-0').click();
  await expect(page.getByTestId('cell-0-0')).not.toHaveAccessibleName(/向日葵/);
});

test('board and controls do not overlap', async ({ page }) => {
  await page.goto('/');
  const board = await page.getByTestId('board').boundingBox();
  const toolbar = await page.getByRole('toolbar').boundingBox();
  expect(board && toolbar && board.y >= toolbar.y + toolbar.height).toBeTruthy();
});
```

- [ ] **Step 2: Run both configured Playwright projects and witness failures**

Run: `cd pvz-game && npm run test:e2e`

Expected: FAIL until Playwright configuration, stable labels, and any discovered layout defects are complete.

- [ ] **Step 3: Fix only observed accessibility/layout defects and complete tracking**

Configure Chromium projects at 1440×900 and 390×844. Add no test-only production APIs. Fix failures through public labels, stable geometry, and real interaction behavior. Update the design status checkboxes to mark implementation and verification complete only after all commands below succeed.

- [ ] **Step 4: Run the full fresh verification suite and inspect screenshots**

Run: `cd pvz-game && npm test && npm run typecheck && npm run build && npm run test:e2e`

Expected: zero failed tests, TypeScript exit 0, Vite build exit 0, and both Playwright projects PASS. Inspect desktop/mobile screenshots, verify the board canvas is nonblank, referenced art renders, and controls/text do not overlap.

- [ ] **Step 5: Commit final verification and tracking**

```bash
git add pvz-game docs/superpowers/specs/2026-07-12-pvz-web-game-design.md
git commit -m "test: verify AI-10 game flows and responsive layout"
```

## Final Publishing Gate

- [ ] Run `git status --short` and confirm no unintended files.
- [ ] Push the verified commit chain to Gitee `main` first and confirm `git ls-remote gitee refs/heads/main` matches local `HEAD`.
- [ ] Push the same `HEAD` to GitHub `origin/main`; if the remote is missing or push fails, record the exact error and an explicit follow-up item in the issue result.
- [ ] Post one concise AI-10 result comment containing verification evidence and the delivered directory.
