# Global Header Search Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the authenticated top action buttons visible on detail pages and make stock search return to the home page before loading results.

**Architecture:** Move the authenticated header and search panel from `HomeScreen` into `App.tsx`. `HomeScreen` receives submitted search queries and executes searches when `pendingSearchQuery` changes.

**Tech Stack:** Expo SDK 56, React Native, TypeScript, lightweight Node static regression scripts.

## Global Constraints

- Read `https://docs.expo.dev/versions/v56.0.0/` before editing app code.
- Do not introduce a route library or new dependencies.
- Do not change backend search APIs.
- Preserve `StockDetailScreen` local back and refresh controls.
- Keep changes scoped to navigation/search behavior.

---

### Task 1: Navigation Regression Check

**Files:**
- Create: `scripts/check-global-header-navigation.js`

**Interfaces:**
- Consumes: `App.tsx`, `src/pages/HomeScreen.tsx`, `src/pages/StockDetailScreen.tsx`
- Produces: `node scripts/check-global-header-navigation.js`

- [ ] **Step 1: Write the failing test**

Create `scripts/check-global-header-navigation.js` with this content:

```javascript
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function assertIncludes(file, needle) {
  const source = read(file);
  if (!source.includes(needle)) {
    throw new Error(`${file} must include ${needle}`);
  }
}

function assertNotIncludes(file, needle) {
  const source = read(file);
  if (source.includes(needle)) {
    throw new Error(`${file} must not include ${needle}`);
  }
}

assertIncludes('App.tsx', "function AppHeader");
assertIncludes('App.tsx', "function SearchPanel");
assertIncludes('App.tsx', "const handleSubmitSearch");
assertIncludes('App.tsx', "setCurrentScreen('home')");
assertIncludes('App.tsx', "pendingSearchQuery");
assertIncludes('App.tsx', "<AppHeader");
assertIncludes('App.tsx', "<SearchPanel");
assertIncludes('App.tsx', "currentScreen !== 'login-settings'");

assertIncludes('src/pages/HomeScreen.tsx', "pendingSearchQuery?: string | null");
assertIncludes('src/pages/HomeScreen.tsx', "useEffect(() =>");
assertIncludes('src/pages/HomeScreen.tsx', "void loadStocks(pendingSearchQuery)");
assertNotIncludes('src/pages/HomeScreen.tsx', "const [isSearchVisible, setIsSearchVisible]");
assertNotIncludes('src/pages/HomeScreen.tsx', "const [searchQuery, setSearchQuery]");
assertNotIncludes('src/pages/HomeScreen.tsx', "style={styles.searchPanel}");

assertIncludes('src/pages/StockDetailScreen.tsx', "onBack");
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node scripts\check-global-header-navigation.js`

Expected: FAIL with `App.tsx must include function AppHeader`.

- [ ] **Step 3: Commit test only if this task is executed independently**

Run only if committing is desired:

```bash
git add scripts/check-global-header-navigation.js
git commit -m "test: add global header navigation check"
```

### Task 2: Global Header and Search State

**Files:**
- Modify: `App.tsx`
- Modify: `src/pages/HomeScreen.tsx`

**Interfaces:**
- Consumes: `HomeScreen` props `onOpenSettings`, `onOpenProfile`, `onLogout`, `onOpenStockDetail`
- Produces:
  - `HomeScreenProps.pendingSearchQuery?: string | null`

- [ ] **Step 1: Read Expo SDK 56 docs**

Open: `https://docs.expo.dev/versions/v56.0.0/`

Confirm no new Expo APIs are needed.

- [ ] **Step 2: Move authenticated header state and controls into App**

In `App.tsx`, import React Native components and icons used by the header:

```typescript
import { Pressable, SafeAreaView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Bell, Globe, LogOut, Search, Settings, User, X } from 'lucide-react-native';
import { useTranslation, type Locale } from './src/i18n';
```

Add state in `App`:

```typescript
const [isSearchVisible, setIsSearchVisible] = useState(false);
const [searchQuery, setSearchQuery] = useState('');
const [pendingSearchQuery, setPendingSearchQuery] = useState<string | null>(null);
```

Add handlers:

```typescript
const handleSubmitSearch = () => {
  setPendingSearchQuery(searchQuery);
  setCurrentScreen('home');
};

const handleClearSearch = () => {
  setSearchQuery('');
  setPendingSearchQuery('');
  setCurrentScreen('home');
};
```

- [ ] **Step 3: Add AppHeader and SearchPanel**

Create `AppHeader` and `SearchPanel` in `App.tsx` below `App`:

```typescript
function AppHeader({
  onOpenSettings,
  onOpenProfile,
  onLogout,
  onToggleSearch,
}: {
  onOpenSettings: () => void;
  onOpenProfile: () => void;
  onLogout: () => void;
  onToggleSearch: () => void;
}) {
  const { t, locale, setLocale } = useTranslation();
  const localeLabel = locale === 'zh' ? '中' : locale === 'zh-Hant' ? '繁' : 'EN';

  return (
    <View style={styles.header}>
      <View style={styles.headerTitleBlock}>
        <Text style={styles.appName}>AIStock</Text>
        <Text style={styles.subtleText}>{t.home.subtitle}</Text>
      </View>
      <View style={styles.headerActions}>
        <Pressable onPress={onToggleSearch}>
          <Search size={20} color="#162033" />
        </Pressable>
        <Pressable>
          <Bell size={20} color="#162033" />
        </Pressable>
        <Pressable onPress={onOpenSettings}>
          <Settings size={20} color="#162033" />
        </Pressable>
        <Pressable onPress={onOpenProfile}>
          <User size={20} color="#162033" />
        </Pressable>
        <Pressable onPress={onLogout}>
          <LogOut size={20} color="#162033" />
        </Pressable>
        <Pressable
          accessibilityLabel={t.common.switchLanguage}
          accessibilityRole="button"
          style={styles.langButton}
          onPress={() => {
            const locales: Locale[] = ['zh', 'zh-Hant', 'en'];
            const currentIndex = locales.indexOf(locale);
            const nextLocale = locales[(currentIndex + 1) % locales.length];
            setLocale(nextLocale);
          }}
        >
          <Globe size={15} color="#FFFFFF" />
          <Text style={styles.langButtonText}>{localeLabel}</Text>
        </Pressable>
      </View>
    </View>
  );
}

function SearchPanel({
  searchQuery,
  onChangeSearchQuery,
  onSubmitSearch,
  onClearSearch,
}: {
  searchQuery: string;
  onChangeSearchQuery: (query: string) => void;
  onSubmitSearch: () => void;
  onClearSearch: () => void;
}) {
  const { t } = useTranslation();

  return (
    <View style={styles.searchPanel}>
      <Search size={18} color="#6B7280" />
      <TextInput
        style={styles.searchInput}
        value={searchQuery}
        onChangeText={onChangeSearchQuery}
        onSubmitEditing={onSubmitSearch}
        placeholder={t.stock.search}
        placeholderTextColor="#9CA3AF"
      />
      {searchQuery ? (
        <Pressable onPress={onClearSearch}>
          <X size={16} color="#6B7280" />
        </Pressable>
      ) : null}
      <Pressable style={styles.searchButton} onPress={onSubmitSearch}>
        <Text style={styles.searchButtonText}>{t.common.ok}</Text>
      </Pressable>
    </View>
  );
}
```

- [ ] **Step 4: Render global header and search panel**

In the authenticated return block of `App.tsx`, render:

```typescript
<View style={styles.appShell}>
  {currentScreen !== 'login-settings' && (
    <AppHeader
      onOpenSettings={goToSettings}
      onOpenProfile={goToProfile}
      onLogout={handleLogout}
      onToggleSearch={() => setIsSearchVisible((visible) => !visible)}
    />
  )}
  {isSearchVisible && currentScreen !== 'login-settings' && (
    <SearchPanel
      searchQuery={searchQuery}
      onChangeSearchQuery={setSearchQuery}
      onSubmitSearch={handleSubmitSearch}
      onClearSearch={handleClearSearch}
    />
  )}
  <View style={styles.screenSlot}>{renderScreen()}</View>
</View>
```

- [ ] **Step 5: Pass search props to HomeScreen**

In the home case:

```typescript
<HomeScreen
  key={refreshKey}
  pendingSearchQuery={pendingSearchQuery}
  onOpenSettings={goToSettings}
  onOpenProfile={goToProfile}
  onLogout={handleLogout}
  onOpenStockDetail={goToStockDetail}
/>
```

- [ ] **Step 6: Remove local header state from HomeScreen**

In `src/pages/HomeScreen.tsx`, remove local `isSearchVisible` and `searchQuery` state. Add prop:

```typescript
pendingSearchQuery?: string | null;
```

Destructure default:

```typescript
pendingSearchQuery = null,
```

Add effect:

```typescript
useEffect(() => {
  if (pendingSearchQuery !== null) {
    void loadStocks(pendingSearchQuery);
  }
}, [pendingSearchQuery, loadStocks]);
```

- [ ] **Step 7: Remove the HomeScreen header and search panel blocks**

Delete the `<View style={styles.header}>...</View>` block from `HomeScreen`.

Delete the `{isSearchVisible && (...)}` search panel block from `HomeScreen`. Search panel rendering is owned only by `App.tsx`.

Remove unused imports from `HomeScreen`: `Bell`, `Globe`, `LogOut`, `Search`, `Settings`, `User`, `X`, `TextInput`, and `Locale` when they are no longer referenced.

- [ ] **Step 8: Run regression check**

Run: `node scripts\check-global-header-navigation.js`

Expected: PASS.

- [ ] **Step 9: Run existing i18n regression check**

Run: `node scripts\check-detail-i18n.js`

Expected: PASS.

- [ ] **Step 10: Trigger Metro web bundle**

Run:

```powershell
$html = (Invoke-WebRequest -Uri 'http://127.0.0.1:8081?global-header-search=1' -UseBasicParsing -TimeoutSec 10).Content
$src = [regex]::Match($html, 'src="([^"]+)"').Groups[1].Value
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8081$src" -UseBasicParsing -TimeoutSec 30
"bundle status=$($r.StatusCode); length=$($r.Content.Length)"
```

Expected: `bundle status=200`.

- [ ] **Step 11: Run backend health check**

Run:

```powershell
(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 5).Content
```

Expected: JSON containing `"status":"healthy"`.

- [ ] **Step 12: Attempt TypeScript check**

Run: `npx tsc --noEmit`

Expected: either PASS or the known TypeScript 6.0.3 `RangeError: Maximum call stack size exceeded`. If the known stack overflow appears, report it as an existing verification blocker.

- [ ] **Step 13: Commit only if requested**

Do not commit automatically in this dirty workspace unless the user asks.
